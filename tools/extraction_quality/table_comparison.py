"""Offline paired comparison of frozen, normalized engine captures.

No engine is installed or model downloaded. A separately pinned local runner may
produce Capture JSON in an isolated process. The runner receives only RAW and an
output path, never Gold. Unsupported output dimensions must be None, not empty.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
import platform
import statistics
import subprocess
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from doclens_ai.extraction.evidence_v2 import (
    Contract,
    Digest,
    Name,
    Proposal,
    ReviewedDocument,
    Scope,
    cell_evidence_id,
)
from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.parsers import ExtractionLimits, extract_file
from tools.extraction_quality.pdf_review_validation import read_json
from tools.extraction_quality.pdf_table_review_packet import ROOT, fresh_output, no_links, sha
from tools.pdf_ocr_candidate import benchmark as bounded

ARMS = ("pypdf", "mineru_basic", "pp_structure_v3")


class Pin(Contract):
    engine: Literal["pypdf", "mineru_basic", "pp_structure_v3"]
    package_version: Name
    config_sha256: Digest
    code_sha256: Digest
    model_revisions: tuple[Name, ...]
    model_artifacts: tuple[Digest, ...]
    license_review_reference: Name
    dependencies_sha256: Digest


class Capture(Contract):
    scope: Scope
    pin: Pin
    status: Literal["success", "needs_review", "failed", "unknown"]
    failure: (
        Literal[
            "unavailable",
            "timeout",
            "memory_limit",
            "output_limit",
            "worker_failed",
            "invalid_output",
            "source_mismatch",
            "cleanup_failed",
        ]
        | None
    )
    # Text order is per page, offsets count exact Unicode codepoints.
    page_text: dict[int, str] | None
    proposal: Proposal | None
    seconds: float | None = Field(ge=0, allow_inf_nan=False)
    peak_rss_bytes: int | None = Field(ge=0)
    peak_gpu_bytes: int | None = Field(ge=0)

    @model_validator(mode="after")
    def consistency(self):
        if self.status in {"success", "needs_review"} and self.failure is not None:
            raise ValueError("successful capture has failure")
        if self.status in {"failed", "unknown"} and (
            self.page_text is not None or self.proposal is not None
        ):
            raise ValueError("failed capture has observations")
        if self.page_text is not None and (
            any(p < 1 for p in self.page_text)
            or sum(len(t) for t in self.page_text.values()) > 5_000_000
        ):
            raise ValueError("text capture limit")
        if self.proposal is not None and (
            self.proposal.scope != self.scope
            or self.proposal.engine != self.pin.engine
            or self.proposal.candidate_revision != self.pin.package_version
            or self.proposal.config_sha256 != self.pin.config_sha256
        ):
            raise ValueError("proposal fingerprint mismatch")
        return self


class Budgets(Contract):
    seconds: float = Field(default=60, gt=0, le=600, allow_inf_nan=False)
    rss_bytes: int = Field(default=1024**3, gt=0)
    output_bytes: int = Field(default=16 * 1024**2, gt=0, le=100 * 1024**2)
    poll_seconds: float = Field(default=0.02, gt=0, le=1, allow_inf_nan=False)


def unavailable(scope: Scope, pin: Pin, failure="unavailable", **runtime) -> Capture:
    return Capture(
        scope=scope,
        pin=pin,
        status="unknown" if failure == "unavailable" else "failed",
        failure=failure,
        page_text=None,
        proposal=None,
        seconds=runtime.get("seconds"),
        peak_rss_bytes=runtime.get("peak_rss_bytes"),
        peak_gpu_bytes=None,
    )


def isolated_capture(
    source: Path,
    scope: Scope,
    pin: Pin,
    *,
    executable: Path,
    executable_sha256: str,
    runner: Path,
    output: Path,
    budgets: Budgets,
    runtime_ready: bool = False,
    request: dict | None = None,
    model_files: tuple[Path, ...] = (),
) -> Capture:
    """Approved local adapter protocol: python runner RAW OUTPUT_JSON.

    runtime_ready is a deployment attestation that all hashed models are local,
    license-reviewed and egress is blocked externally. This is not an OS sandbox.
    Missing process-tree monitoring fails closed before starting any child.
    """
    for path in (source, executable, runner, output):
        no_links(path)
    if output.exists():
        raise ValueError("fresh capture directory required")
    if not runtime_ready:
        return unavailable(scope, pin)
    if not executable.is_file() or not runner.is_file():
        return unavailable(scope, pin)
    if source.stat().st_size > 50 * 1024**2 or sha(source) != scope.raw_sha256:
        return unavailable(scope, pin, "source_mismatch")
    if sha(runner) != pin.code_sha256 or sha(executable) != executable_sha256:
        return unavailable(scope, pin, "invalid_output")
    if pin.engine != "pypdf":
        for path in model_files:
            no_links(path)
        if (
            not model_files
            or any(not p.is_file() for p in model_files)
            or sorted(sha(p) for p in model_files) != sorted(pin.model_artifacts)
        ):
            return unavailable(scope, pin, "unavailable")
    try:
        import psutil  # noqa: F401 - required before spawning, offline optional runtime
    except ImportError:
        return unavailable(scope, pin)
    output.mkdir(parents=True)
    if request is not None:
        (output / "request.json").write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
    destination = output / "capture.json"
    env = dict(
        os.environ,
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        OMP_NUM_THREADS="1",
        OMP_THREAD_LIMIT="1",
    )
    started = time.monotonic()
    peak = 0
    failure = None
    cleanup = True
    try:
        process = subprocess.Popen(
            [str(executable), "-B", str(runner), str(source.resolve()), str(destination.resolve())],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
    except OSError:
        return unavailable(scope, pin)
    try:
        while True:
            peak = max(peak, bounded.tree_rss(process.pid))
            elapsed = time.monotonic() - started
            disk = bounded.disk_bytes(output)
            if peak > budgets.rss_bytes:
                failure = "memory_limit"
            elif disk > budgets.output_bytes:
                failure = "output_limit"
            elif elapsed > budgets.seconds:
                failure = "timeout"
            if failure or process.poll() is not None:
                break
            time.sleep(budgets.poll_seconds)
    finally:
        if process.poll() is None:
            cleanup = bounded.stop_tree(process.pid)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            cleanup = False
    runtime = {"seconds": time.monotonic() - started, "peak_rss_bytes": peak}
    if not cleanup:
        return unavailable(scope, pin, "cleanup_failed", **runtime)
    if failure:
        return unavailable(scope, pin, failure, **runtime)
    if process.returncode != 0:
        return unavailable(scope, pin, "worker_failed", **runtime)
    try:
        no_links(destination)
        if destination.stat().st_size > budgets.output_bytes:
            return unavailable(scope, pin, "output_limit", **runtime)
        capture = Capture.model_validate_json(destination.read_text(encoding="utf-8"))
        if capture.scope != scope or sha(source) != scope.raw_sha256:
            return unavailable(scope, pin, "source_mismatch", **runtime)
        if capture.pin != pin or (
            capture.proposal
            and (
                capture.proposal.scope != scope
                or capture.proposal.config_sha256 != pin.config_sha256
                or capture.proposal.candidate_revision != pin.package_version
            )
        ):
            raise ValueError("capture pin mismatch")
        return capture.model_copy(update=runtime)
    except (OSError, ValueError, TypeError):
        return unavailable(scope, pin, "invalid_output", **runtime)


def native_capture(path: Path, scope: Scope, pin: Pin) -> Capture:
    """Unmodified pypdf baseline; no table structure is inferred from plain text."""
    start = time.monotonic()
    result = extract_file(path)
    if result.source_sha256 != scope.raw_sha256:
        return unavailable(scope, pin, "source_mismatch")
    return Capture(
        scope=scope,
        pin=pin,
        status=result.status.value,
        failure="worker_failed" if result.status.value == "failed" else None,
        page_text={b.source.page_number: b.text for b in result.blocks}
        if result.status.value != "failed"
        else None,
        proposal=None,
        seconds=time.monotonic() - start,
        peak_rss_bytes=None,
        peak_gpu_bytes=None,
    )


def capture_population(
    population: tuple[Scope, ...],
    sources: dict[str, Path],
    output: Path,
    *,
    candidates: dict | None = None,
    budgets: Budgets | None = None,
) -> dict:
    """Run the native arm and approved local adapters, retaining unavailable arms.

    Configuration supplies pins/paths, never labels. Dependency inventory and
    runner/model bytes must be frozen by the local engine operator. No SDK is
    imported without an explicitly ready, license-reviewed isolated runner.
    """
    import sys

    if set(sources) != {s.document_id for s in population}:
        raise ValueError("source population mismatch")
    candidates = candidates or {}
    if not set(candidates) <= set(ARMS[1:]):
        raise ValueError("unknown engine")
    native_runner = Path(__file__).with_name("native_table_runner.py")
    inventory = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    dependency_hash = fingerprint(inventory)
    (output / "runtime-inventory.json").write_text(
        json.dumps(inventory, sort_keys=True), encoding="utf-8"
    )
    native_pin = Pin(
        engine="pypdf",
        package_version=importlib.metadata.version("pypdf"),
        config_sha256=fingerprint(
            {
                "limits": asdict(ExtractionLimits()),
                "code": {
                    p: sha(ROOT / "src/doclens_ai/extraction" / p)
                    for p in ("models.py", "parsers.py")
                },
            }
        ),
        code_sha256=sha(native_runner),
        model_revisions=(),
        model_artifacts=(),
        license_review_reference="pypdf-BSD-3-Clause-local-baseline",
        dependencies_sha256=dependency_hash,
    )
    result = {arm: {} for arm in ARMS}
    for scope in population:
        source = sources[scope.document_id]
        result["pypdf"][scope.document_id] = isolated_capture(
            source,
            scope,
            native_pin,
            executable=Path(sys.executable),
            executable_sha256=sha(Path(sys.executable)),
            runner=native_runner,
            output=output / scope.document_id / "pypdf",
            budgets=budgets or Budgets(),
            runtime_ready=True,
            request={
                "scope": scope.model_dump(mode="json"),
                "pin": native_pin.model_dump(mode="json"),
            },
        )
        for arm in ARMS[1:]:
            settings = candidates.get(arm)
            if settings is None:
                missing_pin = Pin(
                    engine=arm,
                    package_version="UNAVAILABLE",
                    config_sha256=fingerprint({"state": "unavailable", "arm": arm}),
                    code_sha256=fingerprint({"runner": None}),
                    model_revisions=(),
                    model_artifacts=(),
                    license_review_reference="NOT_EVALUATED",
                    dependencies_sha256=fingerprint({"dependencies": None}),
                )
                result[arm][scope.document_id] = unavailable(scope, missing_pin)
                continue
            frozen_pin = Pin.model_validate_json(json.dumps(settings["pin"]))
            if frozen_pin.engine != arm:
                raise ValueError("engine pin mismatch")
            result[arm][scope.document_id] = isolated_capture(
                source,
                scope,
                frozen_pin,
                executable=Path(settings["executable"]),
                executable_sha256=settings["executable_sha256"],
                runner=Path(settings["runner"]),
                output=output / scope.document_id / arm,
                budgets=budgets or Budgets(),
                runtime_ready=settings.get("runtime_ready") is True,
                model_files=tuple(Path(p) for p in settings.get("model_files", [])),
                request={
                    "scope": scope.model_dump(mode="json"),
                    "pin": frozen_pin.model_dump(mode="json"),
                },
            )
    if any(sha(sources[s.document_id]) != s.raw_sha256 for s in population):
        raise ValueError("source drift")
    return result


def _pr(expected: list[str], observed: list[str]) -> dict:
    gold, candidate = Counter(expected), Counter(observed)
    tp = sum((gold & candidate).values())
    return {
        "matched": tp,
        "expected": len(expected),
        "observed": len(observed),
        "precision": tp / len(observed) if observed else None,
        "recall": tp / len(expected) if expected else None,
        "false": sum((candidate - gold).values()),
        "duplicates": sum(max(0, n - gold.get(k, 0)) for k, n in candidate.items() if k in gold),
    }


def _keys(tables, *, dimension: str) -> list[str]:
    keys = []
    for table in tables:
        cells = {c.cell_id: c for c in table.cells}
        for cell in table.cells:
            # Reviewer and engine IDs are independently assigned. Match physical
            # source identities, never require an engine to see Gold IDs.
            base = [cell.locator.page, cell.row, cell.column]
            if dimension == "cell_span":
                base += [cell.literal, cell.row, cell.column, cell.row_span, cell.column_span]
            elif dimension == "locator":
                base += [cell.locator.model_dump(mode="json")]
            elif dimension == "literal":
                base += [cell.literal]
            elif dimension == "role":
                base += [cell.literal, cell.role]
            else:
                continue
            keys.append(fingerprint(base))
        if dimension == "relationship":
            keys += [
                fingerprint(
                    [
                        cells[r.left].model_dump(mode="json", exclude={"cell_id"}),
                        cells[r.right].model_dump(mode="json", exclude={"cell_id"}),
                        r.kind,
                    ]
                )
                for r in table.relations
            ]
    return keys


def score(capture: Capture, gold: ReviewedDocument | None) -> dict:
    capture = Capture.model_validate(capture)
    dimensions = ("cell_span", "relationship", "locator", "literal", "role")
    empty = {
        k: None
        for k in (
            *dimensions,
            "anchor_recall",
            "reading_order",
            "numeric",
            "sign",
            "date",
            "period",
            "unit",
        )
    }
    if gold is None or capture.status not in {"success", "needs_review"}:
        return empty
    gold = ReviewedDocument.model_validate(gold)
    if capture.scope != gold.scope or (capture.proposal and capture.proposal.scope != gold.scope):
        raise ValueError("cross-source capture")
    result = dict(empty)
    if capture.proposal is not None:
        result.update(
            {
                d: _pr(_keys(gold.tables, dimension=d), _keys(capture.proposal.tables, dimension=d))
                for d in dimensions
            }
        )
    if capture.page_text is not None:
        anchors, order = [], []
        categories = {k: [] for k in ("numeric", "sign", "date", "period", "unit")}
        if gold.text_anchors:
            offsets = {}
            for anchor in gold.text_anchors:
                text = capture.page_text.get(anchor.locator.page, "")
                count = text.count(anchor.literal)
                hit = True if count == 1 else False if count == 0 else None
                anchors.append(hit)
                if anchor.category in categories:
                    categories[anchor.category].append(hit)
                if count == 1:
                    offsets[anchor.anchor_id] = (anchor.locator.page, text.index(anchor.literal))
            order = [
                offsets[left] < offsets[right] if left in offsets and right in offsets else None
                for left, right in gold.order_pairs
            ]
        for table in gold.tables:
            offsets = {}
            for cell in table.cells:
                text = capture.page_text.get(cell.locator.page, "")
                if not cell.literal:
                    continue
                count = text.count(cell.literal)
                # Repeated literals without a verified region mapping are UNKNOWN.
                if not gold.text_anchors:
                    anchors.append(True if count == 1 else False if count == 0 else None)
                if count == 1:
                    offsets[cell.cell_id] = (cell.locator.page, text.index(cell.literal))
            for rel in table.relations:
                if rel.kind == "before" and not gold.text_anchors:
                    order.append(
                        offsets[rel.left] < offsets[rel.right]
                        if rel.left in offsets and rel.right in offsets
                        else None
                    )
        result["anchor_recall"] = {
            "matched": anchors.count(True),
            "expected": len(anchors),
            "unknown": anchors.count(None),
            "recall": anchors.count(True) / len(anchors)
            if anchors and None not in anchors
            else None,
        }
        result["reading_order"] = {
            "matched": order.count(True),
            "expected": len(order),
            "unknown": order.count(None),
        }
        for category, hits in categories.items():
            result[category] = {
                "matched": hits.count(True),
                "expected": len(hits),
                "unknown": hits.count(None),
                "recall": hits.count(True) / len(hits) if hits and None not in hits else None,
            }
    return result


def compare(
    population: tuple[Scope, ...],
    captures: dict[str, dict[str, Capture]],
    gold: dict[str, ReviewedDocument] | None = None,
    *,
    allow_synthetic=False,
) -> dict:
    if not population or len({s.document_id for s in population}) != len(population):
        raise ValueError("unique population required")
    if set(captures) != set(ARMS):
        raise ValueError("all arms required")
    ids = {s.document_id for s in population}
    if any(set(values) != ids for values in captures.values()) or (gold and set(gold) != ids):
        raise ValueError("full paired denominator required")
    if gold:
        for label in gold.values():
            ReviewedDocument.model_validate(label)
            if label.review.kind != "independent_human" and not allow_synthetic:
                raise ValueError("independent Gold required")
    documents, runtime, statuses = [], {}, {}
    for arm in ARMS:
        runtime[arm] = []
        statuses[arm] = Counter()
    for scope in population:
        paired = {}
        for arm in ARMS:
            c = captures[arm][scope.document_id]
            if c.scope != scope or c.pin.engine != arm:
                raise ValueError("capture identity mismatch")
            paired[arm] = {
                "status": c.status,
                "failure": c.failure,
                "pin": fingerprint(c.pin.model_dump(mode="json")),
                "capture": fingerprint(
                    c.model_dump(
                        mode="json", exclude={"seconds", "peak_rss_bytes", "peak_gpu_bytes"}
                    )
                ),
                "scores": score(c, gold.get(scope.document_id) if gold else None),
            }
            runtime[arm].append(
                {
                    "document_id": scope.document_id,
                    "seconds": c.seconds,
                    "peak_rss_bytes": c.peak_rss_bytes,
                    "peak_gpu_bytes": c.peak_gpu_bytes,
                }
            )
            statuses[arm][c.status] += 1
        deltas = {}
        baseline = paired["pypdf"]["scores"]["anchor_recall"]
        for arm in ARMS[1:]:
            value = paired[arm]["scores"]["anchor_recall"]
            btext, ctext = (
                captures["pypdf"][scope.document_id].page_text,
                captures[arm][scope.document_id].page_text,
            )
            lost = recovered = None
            if (
                gold
                and btext is not None
                and ctext is not None
                and paired[arm]["status"] in {"success", "needs_review"}
            ):
                lost, recovered = [], []
                for t in gold[scope.document_id].tables:
                    for cell in t.cells:
                        if not cell.literal:
                            continue
                        b = cell.literal in btext.get(cell.locator.page, "")
                        c = cell.literal in ctext.get(cell.locator.page, "")
                        eid = cell_evidence_id(scope, t.table_id, cell)
                        if b and not c:
                            lost.append(eid)
                        if c and not b:
                            recovered.append(eid)
                for anchor in gold[scope.document_id].text_anchors:
                    b = anchor.literal in btext.get(anchor.locator.page, "")
                    c = anchor.literal in ctext.get(anchor.locator.page, "")
                    eid = fingerprint(anchor.model_dump(mode="json"))
                    if b and not c:
                        lost.append(eid)
                    if c and not b:
                        recovered.append(eid)
            metric_deltas = {}
            for dimension in ("cell_span", "relationship", "locator", "literal", "role"):
                bscore, cscore = (paired[a]["scores"][dimension] for a in ("pypdf", arm))
                metric_deltas[dimension] = (
                    cscore["matched"] - bscore["matched"]
                    if (bscore is not None and cscore is not None)
                    else None
                )
            new_failure = (
                paired["pypdf"]["status"] in {"success", "needs_review"}
                and paired[arm]["status"] == "failed"
            )
            deltas[arm] = {
                "anchor_delta": value["matched"] - baseline["matched"]
                if baseline and value
                else None,
                "new_losses": lost,
                "recovered": recovered,
                "metric_deltas": metric_deltas,
                "new_failure": new_failure,
                "regression": True if new_failure or lost else False if lost is not None else None,
            }
        documents.append({"document_id": scope.document_id, "arms": paired, "deltas": deltas})
    quality = {
        "population": len(population),
        "documents": documents,
        "status_counts": {a: dict(c) for a, c in statuses.items()},
        "quality": "NOT_EVALUATED" if not gold else "MEASURED_NOT_QUALIFIED",
        "experiment": "REJECT"
        if any(d["regression"] for row in documents for d in row["deltas"].values())
        else "INCONCLUSIVE",
        "production_authorized": False,
    }
    timings = {}
    for arm, rows in runtime.items():
        seconds = sorted(x["seconds"] for x in rows if x["seconds"] is not None)
        timings[arm] = {
            "observed": len(seconds),
            "denominator": len(population),
            "p50_seconds": statistics.median(seconds) if seconds else None,
            "p95_seconds": seconds[math.ceil(0.95 * len(seconds)) - 1] if seconds else None,
        }
    return {
        "quality": quality,
        "fingerprint": fingerprint(quality),
        "runtime": runtime,
        "latency": timings,
        "resource_method": "sampled process-tree RSS bytes; GPU unknown",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=Path, required=True)
    intake = parser.add_mutually_exclusive_group(required=True)
    intake.add_argument("--captures", type=Path)
    intake.add_argument("--sources", type=Path)
    parser.add_argument("--candidate-runners", type=Path)
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        fresh_output(args.output, ROOT / "local-corpus", root=ROOT)
        population = tuple(Scope.model_validate(s) for s in read_json(args.population)["scopes"])
        args.output.mkdir(parents=True)
        if args.sources:
            sources = {k: Path(v) for k, v in read_json(args.sources).items()}
            captures = capture_population(
                population,
                sources,
                args.output,
                candidates=read_json(args.candidate_runners) if args.candidate_runners else None,
            )
            (args.output / "captures.json").write_text(
                json.dumps(
                    {
                        a: {k: c.model_dump(mode="json") for k, c in rows.items()}
                        for a, rows in captures.items()
                    },
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
        else:
            raw = read_json(args.captures)
            captures = {
                arm: {k: Capture.model_validate_json(json.dumps(v)) for k, v in rows.items()}
                for arm, rows in raw.items()
            }
        gold = (
            {
                d["scope"]["document_id"]: ReviewedDocument.model_validate_json(json.dumps(d))
                for d in read_json(args.gold)["documents"]
            }
            if args.gold
            else None
        )
        result = compare(population, captures, gold)
        result["provenance"] = {
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "python": platform.python_version(),
            "pypdf": importlib.metadata.version("pypdf"),
            "code": sha(Path(__file__)),
            "population": sha(args.population),
            "captures": sha(args.captures or args.output / "captures.json"),
            "sources": sha(args.sources) if args.sources else None,
            "gold": sha(args.gold) if args.gold else None,
        }
        (args.output / "metrics.json").write_text(
            json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
        )
        print(json.dumps({"fingerprint": result["fingerprint"], "population": len(population)}))
        return 0
    except Exception:
        print("BLOCKED: comparison inputs or private output rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
