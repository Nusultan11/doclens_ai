"""Bounded, offline selective OCR experiment. Never imported by production routing.

Private extraction captures stay in a git-ignored output directory. Metrics contain
only opaque identities/counts. Selection and OCR receive neither Gold nor corpus IDs.
RSS/disk guards are sampled, not a hostile-input OS sandbox.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import logging
import math
import multiprocessing
import os
import platform
import re
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from pypdf import PdfReader

from doclens_ai.extraction.fidelity_eval import (
    _located,
    _observations,
    _read_sources,
    normalize,
    score_record,
    verify_corpus,
)
from doclens_ai.extraction.fidelity_gold import fingerprint, load_gold
from doclens_ai.extraction.models import (
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TextBlock,
)
from doclens_ai.extraction.parsers import ExtractionLimits, extract_file


@dataclass(frozen=True)
class Limits:
    max_file_bytes: int = 50 * 1024 * 1024
    max_pages: int = 40
    max_ocr_pages: int = 10
    min_native_characters: int = 20
    dpi: int = 300
    max_pixels: int = 20_000_000
    min_ink_fraction: float = 0.001
    max_characters: int = 5_000_000
    max_scratch_bytes: int = 256 * 1024 * 1024
    max_process_bytes: int = 3 * 1024**3
    timeout_seconds: float = 600
    tool_timeout_seconds: float = 60
    poll_seconds: float = 0.02


@dataclass(frozen=True)
class Runtime:
    tesseract: str
    renderer: str
    tessdata: str


class BoundedFailure(Exception):
    """Only fixed categories, never third-party exception details."""

    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def eligible(native: str, limits: Limits) -> bool:
    return len("".join(native.split())) < limits.min_native_characters


def guard_reason(rss: int, elapsed: float, disk: int, limits: Limits) -> str | None:
    # Fixed memory -> timeout -> disk precedence, shared by both monitors.
    if rss > limits.max_process_bytes:
        return "memory_limit"
    if elapsed > limits.timeout_seconds:
        return "timeout"
    if disk > limits.max_scratch_bytes:
        return "output_limit"
    return None


def disk_bytes(root: Path) -> int:
    total = 0
    for path in root.rglob("*"):
        # Page scratch may be removed between enumeration and stat by the worker.
        with contextlib.suppress(FileNotFoundError):
            if path.is_file():
                total += path.stat().st_size
    return total


def tree_rss(pid: int) -> int:
    import psutil

    try:
        processes = [psutil.Process(pid)]
        processes += processes[0].children(recursive=True)
    except psutil.NoSuchProcess:
        return 0
    total = 0
    for process in processes:
        with contextlib.suppress(psutil.NoSuchProcess):
            total += process.memory_info().rss
    return total


def stop_tree(pid: int, *, reap_root: bool = True) -> bool:
    import psutil

    try:
        root = psutil.Process(pid)
        processes = root.children(recursive=True) + [root]
    except psutil.NoSuchProcess:
        return True
    for process in reversed(processes):
        with contextlib.suppress(psutil.NoSuchProcess):
            process.kill()
    # multiprocessing must reap its own child to retain the exit status on POSIX.
    _, alive = psutil.wait_procs(processes if reap_root else processes[:-1], timeout=5)
    return not alive


def command(args: list[str], work: Path, limits: Limits) -> dict:
    """No shell, inherited one-thread policy, no third-party stdout/stderr logging."""
    env = dict(os.environ, OMP_THREAD_LIMIT="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    started = time.monotonic()
    try:
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    except OSError:
        raise BoundedFailure("missing_runtime") from None
    peak = 0
    try:
        while True:
            peak = max(peak, tree_rss(proc.pid))
            reason = guard_reason(
                peak,
                time.monotonic() - started,
                disk_bytes(work),
                replace(limits, timeout_seconds=limits.tool_timeout_seconds),
            )
            if reason:
                raise BoundedFailure(reason)
            code = proc.poll()
            if code is not None:
                if code:
                    raise BoundedFailure("tool_failed")
                return {"exit_code": code, "seconds": time.monotonic() - started, "peak_rss": peak}
            time.sleep(limits.poll_seconds)
    finally:
        if proc.poll() is None:
            stop_tree(proc.pid)
        proc.wait(timeout=5)


def pgm_ink(path: Path, limits: Limits) -> float:
    """Parse only Poppler P5/8-bit grayscale; validate dimensions before reading pixels."""
    try:
        with path.open("rb") as stream:
            tokens = []
            while len(tokens) < 4:
                line = stream.readline(256)
                if not line or len(line) >= 256:
                    raise BoundedFailure("invalid_render")
                tokens.extend(line.split(b"#", 1)[0].split())
            if len(tokens) != 4 or tokens[0] != b"P5" or tokens[3] != b"255":
                raise BoundedFailure("invalid_render")
            width, height = int(tokens[1]), int(tokens[2])
            pixels = width * height
            if min(width, height) <= 0 or pixels > limits.max_pixels:
                raise BoundedFailure("pixel_limit")
            data = stream.read(pixels + 1)
            if len(data) != pixels:
                raise BoundedFailure("invalid_render")
            return sum(value < 245 for value in data) / pixels
    except (OSError, ValueError):
        raise BoundedFailure("invalid_render") from None


def ocr_page(
    path: Path, page: int, runtime: Runtime, limits: Limits, work: Path
) -> tuple[str, dict]:
    rendered = work / "page.pgm"
    output = work / "ocr.txt"
    record = {"page": page, "state": "selected"}
    with tempfile.TemporaryDirectory(dir=work, prefix="page-") as temp:
        directory = Path(temp)
        rendered = directory / rendered.name
        output = directory / output.name
        render = command(
            [
                runtime.renderer,
                "-f",
                str(page),
                "-l",
                str(page),
                "-singlefile",
                "-r",
                str(limits.dpi),
                "-gray",
                str(path),
                str(rendered.with_suffix("")),
            ],
            work,
            limits,
        )
        ink = pgm_ink(rendered, limits)
        record.update(ink_fraction=ink, render=render)
        if ink < limits.min_ink_fraction:
            return "", dict(record, state="blank_render")
        ocr = command(
            [
                runtime.tesseract,
                str(rendered),
                str(output.with_suffix("")),
                "--tessdata-dir",
                runtime.tessdata,
                "-l",
                "eng",
                "--oem",
                "1",
                "--psm",
                "3",
                "--dpi",
                str(limits.dpi),
            ],
            work,
            limits,
        )
        if not output.is_file():
            raise BoundedFailure("missing_ocr")
        if output.stat().st_size > limits.max_characters * 4:
            raise BoundedFailure("output_limit")
        try:
            text = output.read_text(encoding="utf-8")
        except UnicodeError:
            raise BoundedFailure("invalid_ocr") from None
        if len(text) > limits.max_characters:
            raise BoundedFailure("output_limit")
        return text, dict(record, state="ocr" if text.strip() else "empty_ocr", ocr=ocr)


def selective_extract(
    path: Path, runtime: Runtime, limits: Limits, work: Path
) -> tuple[ExtractionResult, list]:
    baseline = extract_file(
        path,
        limits=ExtractionLimits(
            max_file_bytes=limits.max_file_bytes,
            max_pdf_pages=limits.max_pages,
            max_extracted_characters=limits.max_characters,
        ),
    )
    if baseline.status is ExtractionStatus.FAILED:
        return baseline, []
    reader = PdfReader(path, strict=False)
    blocks = []
    pages = []
    selected = 0
    # Reserve the complete native document before adding any OCR, including pages
    # still to be visited. Never spend future native text's output budget.
    characters = sum(len(block.text) for block in baseline.blocks)
    review = baseline.status is ExtractionStatus.NEEDS_REVIEW
    for original, page in zip(baseline.blocks, reader.pages, strict=True):
        blocks.append(replace(original, order=len(blocks)))
        number = original.source.page_number
        if not eligible(original.text, limits):
            pages.append({"page": number, "state": "native"})
            continue
        review = True
        # A page number is observed from traversal, never supplied by OCR or Gold.
        width = math.ceil(float(page.mediabox.width) * limits.dpi / 72)
        height = math.ceil(float(page.mediabox.height) * limits.dpi / 72)
        if width <= 0 or height <= 0 or width * height > limits.max_pixels:
            pages.append({"page": number, "state": "pixel_limit"})
            continue
        if selected >= limits.max_ocr_pages:
            pages.append({"page": number, "state": "page_limit"})
            continue
        selected += 1
        try:
            text, observation = ocr_page(path, number, runtime, limits, work)
            if characters + len(text) > limits.max_characters:
                raise BoundedFailure("output_limit")
            # Suppress only an exact whitespace-normalized whole-page duplicate.
            # No cross-page deduplication, digit correction, fuzzy matching or repair.
            if text.strip() and normalize(text) != normalize(original.text):
                blocks.append(TextBlock(len(blocks), text, SourceLocation(page_number=number)))
                characters += len(text)
            elif text.strip():
                observation["state"] = "duplicate_ocr"
            pages.append(observation)
        except BoundedFailure as exc:
            pages.append({"page": number, "state": exc.category})
    return replace(
        baseline,
        blocks=tuple(blocks),
        status=ExtractionStatus.NEEDS_REVIEW if review else baseline.status,
    ), pages


def _worker(path: str, runtime: Runtime, limits: Limits, output: str, candidate: bool) -> None:
    root = Path(output)
    # Silence parser diagnostics including paths/content; retain only sanitized states.
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            if candidate:
                result, pages = selective_extract(Path(path), runtime, limits, root)
            else:
                result = extract_file(
                    Path(path),
                    limits=ExtractionLimits(
                        max_file_bytes=limits.max_file_bytes,
                        max_pdf_pages=limits.max_pages,
                        max_extracted_characters=limits.max_characters,
                    ),
                )
                pages = []
        payload = {"result": result.to_dict(), "pages": pages}
    except Exception:  # noqa: BLE001 - never serialize native exception text
        payload = {"result": None, "pages": [], "failure": "worker_failed"}
    (root / "result.json").write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")


def isolated(
    path: Path, runtime: Runtime, limits: Limits, output: Path, *, candidate: bool
) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    child = multiprocessing.get_context("spawn").Process(
        target=_worker,
        args=(str(path), runtime, limits, str(output), candidate),
    )
    started = time.monotonic()
    child.start()
    peak = disk_peak = 0
    failure = None
    cleanup = True
    try:
        with (output / "resources.jsonl").open("w", encoding="utf-8") as journal:
            while True:
                elapsed = time.monotonic() - started
                rss, disk = tree_rss(child.pid), disk_bytes(output)
                peak, disk_peak = max(peak, rss), max(disk_peak, disk)
                journal.write(
                    json.dumps({"elapsed": elapsed, "tree_rss": rss, "disk": disk}) + "\n"
                )
                journal.flush()
                failure = guard_reason(rss, elapsed, disk, limits)
                if failure or not child.is_alive():
                    break
                time.sleep(limits.poll_seconds)
    finally:
        if child.is_alive():
            cleanup = stop_tree(child.pid, reap_root=False)
        child.join(timeout=5)
        if child.is_alive():
            child.kill()
            child.join(timeout=5)
        if child.is_alive():
            cleanup = False
        else:
            child.close()
        if not cleanup:
            failure = "cleanup_failed"
    result_path = output / "result.json"
    payload = {"result": None, "pages": []}
    if (
        not failure
        and result_path.is_file()
        and result_path.stat().st_size <= limits.max_scratch_bytes
    ):
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    elif not failure:
        failure = "worker_failed"
    payload.update(
        failure=failure or payload.get("failure"),
        runtime={
            "seconds": time.monotonic() - started,
            "peak_tree_rss_bytes": peak,
            "peak_sampled_disk_bytes": disk_peak,
            "cleanup": cleanup,
        },
    )
    return payload


def restore(raw: dict) -> ExtractionResult:
    from doclens_ai.extraction.models import (
        DocumentFormat,
        ErrorCategory,
        ExtractionWarning,
        WarningCode,
        WarningSeverity,
    )

    return ExtractionResult(
        schema_version=raw["schema_version"],
        document_format=DocumentFormat(raw["document_format"]),
        status=ExtractionStatus(raw["status"]),
        source_sha256=raw["source_sha256"],
        source_size_bytes=raw["source_size_bytes"],
        blocks=tuple(
            TextBlock(b["order"], b["text"], SourceLocation(**b["source"])) for b in raw["blocks"]
        ),
        warnings=tuple(
            ExtractionWarning(
                WarningCode(w["code"]),
                WarningSeverity(w["severity"]),
                w["count"],
                SourceLocation(**w["source"]) if w["source"] else None,
            )
            for w in raw["warnings"]
        ),
        error_category=ErrorCategory(raw["error_category"]) if raw["error_category"] else None,
    )


def summarize(record, capture: dict) -> dict:
    if capture["result"] is None:
        return {
            "status": "failed",
            "failure": capture["failure"],
            "scores": None,
            "hits": None,
            "located": None,
            "extraction_fingerprint": None,
        }
    result = restore(capture["result"])
    observations = _observations(result)
    hits, located = {}, {}
    for anchor in record.anchors:
        needle = normalize(anchor.text)
        hits[anchor.anchor_id] = any(needle in normalize(o.text) for o in observations)
        count = sum(
            normalize(o.text).count(needle)
            for o in observations
            if _located(o.source, anchor.source)
        )
        located[anchor.anchor_id] = count >= anchor.occurrence
    numeric = [a.anchor_id for a in record.anchors if re.search(r"[0-9]", a.text)]
    return {
        "status": result.status.value,
        "failure": capture["failure"],
        "scores": score_record(record, result),
        "hits": hits,
        "located": located,
        "numeric_anchor_ids": numeric,
        "numeric_hits": sum(hits[a] for a in numeric),
        "numeric_denominator": len(numeric),
        "extraction_fingerprint": fingerprint(result.to_dict()),
    }


def pins(runtime: Runtime) -> dict:
    import psutil

    root = Path(runtime.tesseract).parent
    return {
        "tesseract": digest(Path(runtime.tesseract)),
        "renderer": digest(Path(runtime.renderer)),
        "eng": digest(Path(runtime.tessdata) / "eng.traineddata"),
        "tesseract_dlls": {p.name: digest(p) for p in sorted(root.glob("*.dll"))},
        "renderer_dlls": {
            p.name: digest(p) for p in sorted(Path(runtime.renderer).parent.glob("*.dll"))
        },
        "python": {
            name: importlib.metadata.version(name) for name in ("pypdf", "pydantic", "psutil")
        },
        "python_executable": digest(Path(os.sys.executable)),
        "host": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
            "physical_ram_bytes": psutil.virtual_memory().total,
        },
    }


def registration(args, runtime: Runtime, limits: Limits) -> tuple[dict, dict, tuple]:
    manifest, gold = Path(args.manifest), Path(args.gold)
    sources = _read_sources(manifest)
    paths = verify_corpus(Path(args.corpus), sources, ExtractionLimits())
    records = load_gold(gold, sources)
    cohort = sorted(set(args.documents))
    assert len(cohort) == len(args.documents) and set(cohort) <= {r.document_id for r in records}
    assert all(sources[c][2] == "pdf" for c in cohort)
    files = [
        Path(__file__),
        *(
            Path("src/doclens_ai/extraction") / n
            for n in ("parsers.py", "models.py", "fidelity_eval.py", "fidelity_gold.py")
        ),
    ]
    frozen = {
        "version": "ML-18-v1",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "manifest": digest(manifest),
        "gold_bytes": digest(gold),
        "gold_normalized": fingerprint([r.model_dump(mode="json") for r in records]),
        "cohort": {c: sources[c] for c in cohort},
        "limits": asdict(limits),
        "pins": pins(runtime),
        "code": {p.name: digest(p) for p in files},
        "ocr": {
            "language": "eng",
            "oem": 1,
            "psm": 3,
            "threads": 1,
            "seed": None,
            "ink_pixel_below": 245,
            "dedup": "whole_page_whitespace_only",
        },
        "gate": (
            "primary>=1_with_page;no_baseline_loss;no_control_numeric_provenance_regression;"
            "no_new_failure;repeat_equal;all_resource_privacy_guards"
        ),
    }
    return frozen, paths, tuple(r for r in records if r.document_id in cohort)


def ignored(path: Path, *, corpus: Path = Path("local-corpus")) -> None:
    if path.resolve().is_relative_to(corpus.resolve()):
        raise ValueError("Output inside RAW rejected")
    check = subprocess.run(["git", "check-ignore", "-q", str(path)], check=False)
    if check.returncode != 0:
        raise ValueError("Output must be ignored")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="docs/eda/corpus_v1_manifest.csv")
    parser.add_argument(
        "--gold", default="local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl"
    )
    parser.add_argument("--corpus", default="local-corpus")
    parser.add_argument("--documents", nargs="+", required=True)
    parser.add_argument("--tesseract", required=True)
    parser.add_argument("--renderer", required=True)
    parser.add_argument("--tessdata", required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    runtime, limits = Runtime(args.tesseract, args.renderer, args.tessdata), Limits()
    frozen, paths, records = registration(args, runtime, limits)
    ignored(args.registration, corpus=Path(args.corpus))
    if args.freeze:
        args.registration.parent.mkdir(parents=True, exist_ok=True)
        with args.registration.open("x", encoding="utf-8") as stream:
            json.dump(frozen, stream, sort_keys=True, indent=2)
        print(
            json.dumps({"registration_fingerprint": fingerprint(frozen), "documents": len(records)})
        )
        return
    assert json.loads(args.registration.read_text()) == json.loads(json.dumps(frozen))
    if args.output is None:
        parser.error("--output required")
    ignored(args.output, corpus=Path(args.corpus))
    args.output.mkdir(parents=True, exist_ok=False)
    documents = []
    runtimes = []
    for record in records:
        baseline = isolated(
            paths[record.document_id],
            runtime,
            limits,
            args.output / record.document_id / "baseline",
            candidate=False,
        )
        candidate = isolated(
            paths[record.document_id],
            runtime,
            limits,
            args.output / record.document_id / "candidate",
            candidate=True,
        )
        b, c = summarize(record, baseline), summarize(record, candidate)
        comparison = {"recovered": None, "lost": None, "native_preserved": None}
        if b["hits"] is not None and c["hits"] is not None:
            comparison.update(
                recovered=[a for a in b["hits"] if c["hits"][a] and not b["hits"][a]],
                lost=[a for a in b["hits"] if b["hits"][a] and not c["hits"][a]],
            )
            native = baseline["result"]["blocks"]
            proposed = candidate["result"]["blocks"]
            comparison["native_preserved"] = all(
                any(x["text"] == n["text"] and x["source"] == n["source"] for x in proposed)
                for n in native
            )
        # Timing is excluded from quality; page states and observed provenance remain deterministic.
        pages = [
            {k: v for k, v in p.items() if k not in {"render", "ocr"}} for p in candidate["pages"]
        ]
        documents.append(
            {
                "document_id": record.document_id,
                "baseline": b,
                "candidate": c,
                "comparison": comparison,
                "pages": pages,
            }
        )
        runtimes.append(
            {
                "document_id": record.document_id,
                "baseline": baseline["runtime"],
                "candidate": candidate["runtime"],
                "page_tools": candidate["pages"],
            }
        )
    assert registration(args, runtime, limits)[0] == frozen
    quality = {
        "registration_fingerprint": fingerprint(frozen),
        "documents": documents,
        "population": {"documents": len(records), "anchors": sum(len(r.anchors) for r in records)},
        "diagram_relationships": "NOT_EVALUATED",
        "production_authorization": False,
    }
    report = {
        "quality": quality,
        "deterministic_fingerprint": fingerprint(quality),
        "runtime": runtimes,
    }
    (args.output / "metrics.json").write_text(
        json.dumps(report, sort_keys=True, indent=2), encoding="utf-8"
    )
    print(
        json.dumps({"documents": len(records), "fingerprint": report["deterministic_fingerprint"]})
    )


if __name__ == "__main__":
    main()
