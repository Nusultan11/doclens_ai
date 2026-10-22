"""Bounded source-only paired probe; dev-reference scoring starts after capture seal."""

from __future__ import annotations

import argparse
import contextlib
import importlib.metadata
import io
import json
import logging
import os
import platform
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.parsers import extract_file
from tools.docx_footnote_candidate.benchmark import GUARDS, monitor, sha
from tools.docx_footnote_candidate.locator_review_packet import fresh_output, write_json
from tools.extraction_quality import pdf_source_only_faces as candidate

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SHA = {
    "c1-0033": "081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd",
    "c1-0040": "18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344",
}
NATIVE_FINGERPRINTS = {
    "c1-0033": "332aa3f7c032b0ca4bb3d7ebf44166686758ed23615f4002f0943e3c48bf64cf",
    "c1-0040": "7a5c30d77b9b3ca0933d5a39fc699d4fdf5af9ed4b839ca525355a6ee990898c",
}
CODE = (
    "tools/extraction_quality/pdf_source_only_faces.py",
    "tools/extraction_quality/pdf_table_source_only_probe.py",
    "tools/extraction_quality/pdf_cell_recovery.py",
    "src/doclens_ai/extraction/parsers.py",
    "src/doclens_ai/extraction/models.py",
    "tools/docx_footnote_candidate/benchmark.py",
    "tools/extraction_quality/pdf_native_dev_diagnostic.py",
    "tools/extraction_quality/pdf_dev_reference.py",
)


def guarded_infer(data: bytes) -> tuple[dict, list[str]]:
    """Audit/deny inference file access outside installed Python/runtime packages."""
    allowed = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
    reads, active = [], [True]

    def audit(event, args):
        if active[0] and event == "open" and isinstance(args[0], (str, bytes)):
            path = Path(os.fsdecode(args[0])).resolve()
            if not any(path.is_relative_to(root) for root in allowed):
                raise ValueError("Forbidden inference file access")
            reads.append(str(path))

    sys.addaudithook(audit)
    try:
        return candidate.infer(data), sorted(set(reads))
    finally:
        active[0] = False


def worker(source: Path, output: Path) -> int:
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            before_time = time.perf_counter()
            baseline = extract_file(source).to_dict()
            before_seconds = time.perf_counter() - before_time
            data = source.read_bytes()
            start = time.perf_counter()
            probe, reads = guarded_infer(data)
            candidate_seconds = time.perf_counter() - start
            start = time.perf_counter()
            after = extract_file(source).to_dict()
            after_seconds = time.perf_counter() - start
        # Stable filenames while monitored; do not rename/delete files mid-sampling.
        with (output / "result.json").open("x", encoding="utf-8") as stream:
            json.dump(
                dict(
                    baseline=baseline,
                    probe=probe,
                    baseline_after_fingerprint=fingerprint(after),
                    inference_inputs="PDF_BYTES_AND_FROZEN_CONFIG_ONLY",
                    inference_nonruntime_file_reads=0,
                ),
                stream,
                sort_keys=True,
            )
        with (output / "timing.json").open("x", encoding="utf-8") as stream:
            json.dump(
                dict(
                    native_before_seconds=before_seconds,
                    candidate_seconds=candidate_seconds,
                    native_after_seconds=after_seconds,
                ),
                stream,
                sort_keys=True,
            )
        with (output / "inference-file-audit.json").open("x", encoding="utf-8") as stream:
            json.dump(dict(allowed_library_file_reads=reads, forbidden_reads=0), stream)
        return 0
    except Exception:
        return 2


def registration(sources: dict[str, Path]) -> dict:
    return dict(
        method=candidate.METHOD,
        hypothesis=(
            "Local four-bar rectangular faces avoid global lattice "
            "oversegmentation without seeded regions"
        ),
        source_sha256={key: sha(path) for key, path in sources.items()},
        config=asdict(candidate.Config()),
        guards=GUARDS,
        code={p: sha(ROOT / p) for p in CODE},
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        packages={
            n: importlib.metadata.version(n)
            for n in ("pypdf", "pdfplumber", "pdfminer.six", "pypdfium2", "psutil")
        },
        python=platform.python_version(),
        platform=platform.platform(),
        cpu_count=os.cpu_count(),
        machine=platform.machine(),
        concurrency=1,
        gpu="NOT_USED",
        repetitions=2,
        cache="OS cache not reset",
        quality_gate="NOT_EVALUATED",
        promotion_criteria=[
            "at least one unique source-glyph-set cell correspondence",
            "all emitted geometry tied to four original bar inner edges",
            "zero duplicate nonspace glyph ownership",
            "zero non-whitespace mismatch in mapped cell literals",
            "all native baseline bytes/fingerprints/statuses unchanged",
            "two identical non-runtime captures; no resource or inference-access failure",
        ],
        reject_criteria=(
            "critical guardrail violation or complete measurements "
            "with zero structural correspondence"
        ),
        inconclusive_criteria="missing capture or inconsistent evidence",
        scope=(
            "further offline evaluation only; physical face proposals, "
            "no semantic/span/border correctness"
        ),
    )


def score(doc: dict, capture: dict) -> dict:
    """Source glyph ownership, not reference boxes or text-only substring matching."""
    probe = capture["probe"]
    if probe["source_sha256"] != doc["source_sha256"]:
        raise ValueError("Scoring source mismatch")
    pages = probe["pages"]
    cells = [(p, c) for p in pages for c in p["cells"]]
    reference_by_glyphs = {}
    for ref in doc["cells"]:
        indices = ref["source_text_evidence"]["source_glyph_indices"]["pdfplumber"]
        chars = next((p.get("source_characters", []) for p in pages if p["page"] == 1), [])
        key = tuple(i for i in indices if chars and chars[i]["text"].strip())
        if key:
            reference_by_glyphs.setdefault(key, []).append(ref)
    mapped, findings, owned = [], [], []
    violations = []
    for page, cell in cells:
        bars = {r["source_object_index"]: r for r in page["source_rules"]}
        left, bottom, right, top = [bars[i]["bbox"] for i in cell["boundary_objects"]]
        if cell["bbox"] != [left[2], bottom[3], right[0], top[1]]:
            violations.append("UNSUPPORTED_COORDINATE")
        chars = page["source_characters"]
        key = tuple(i for i in cell["glyph_indices"] if chars[i]["text"].strip())
        owned.extend((page["page"], i) for i in key)
        refs = reference_by_glyphs.get(key, []) if key else []
        match = refs[0] if len(refs) == 1 and cell["literal_text"] is not None else None
        observation = "NO_UNIQUE_GLYPH_CORRESPONDENCE"
        if match:
            mapped.append((cell["face_index"], match["item_id"], match["table_id"]))
            observation = (
                "EXACT_LITERAL"
                if cell["literal_text"] == match["literal_text"]
                else "WHITESPACE_DIFFERENCE"
            )
            if "".join(cell["literal_text"].split()) != "".join(match["literal_text"].split()):
                violations.append("MAPPED_NONSPACE_TEXT_MISMATCH")
                observation = "NONSPACE_MISMATCH"
        findings.append(
            dict(
                candidate_id=cell["cell_id"],
                reference_item_id=match["item_id"] if match else None,
                observation=observation,
                glyph_correspondence=bool(match),
            )
        )
    if len(owned) != len(set(owned)):
        violations.append("DUPLICATE_GLYPH_OWNERSHIP")
    if len({m[1] for m in mapped}) != len(mapped):
        violations.append("DUPLICATE_REFERENCE_ASSIGNMENT")
    region_findings = []
    for page in pages:
        for region in page["regions"]:
            members = [m for m in mapped if m[0] in region["face_indices"]]
            targets = sorted({m[2] for m in members})
            region_findings.append(
                dict(
                    candidate_region_id=region["region_id"],
                    mapped_cells=len(members),
                    reference_grid_ids=targets,
                    membership_coherent=len(targets) == 1 and len(members) >= 2,
                )
            )
    return dict(
        source_id=doc["document_id"],
        candidate_status=probe["status"],
        baseline_status=capture["baseline"]["status"],
        baseline_warnings=capture["baseline"]["warnings"],
        baseline_fingerprint=fingerprint(capture["baseline"]),
        baseline_unchanged=fingerprint(capture["baseline"])
        == capture["baseline_after_fingerprint"]
        == NATIVE_FINGERPRINTS[doc["document_id"]],
        discovered_regions=sum(len(p["regions"]) for p in pages),
        discovered_faces=len(cells),
        closed_faces=sum(p.get("closed_faces", 0) for p in pages),
        supported_nonempty_literals=sum(c["literal_text"] is not None for _, c in cells),
        unresolved_text=sum(c["literal_text"] is None for _, c in cells),
        source_characters=sum(len(p.get("source_characters", [])) for p in pages),
        unassigned_nonspace_glyphs=sum(len(p.get("unassigned_nonspace_glyphs", [])) for p in pages),
        page_issues=[dict(page=p["page"], issues=p["issues"]) for p in pages],
        cell_denominator=len(doc["cells"]),
        empty_cell_denominator=sum(c["literal_text"] == "" for c in doc["cells"]),
        glyph_correspondences=len(mapped),
        literal_observations=dict(Counter(f["observation"] for f in findings)),
        grid_denominator=len(doc["logical_grids"]),
        coherent_region_memberships=sum(r["membership_coherent"] for r in region_findings),
        region_findings=region_findings,
        cell_findings=findings,
        violations=violations,
        verified_semantics="NOT_EVALUATED",
        exact_border_fidelity="NOT_EVALUATED",
    )


def decision(rows: list[dict], complete: bool, deterministic: bool) -> str:
    if any(r["violations"] or r["baseline_unchanged"] is False for r in rows):
        return "REJECT"
    if not complete or not deterministic:
        return "INCONCLUSIVE"
    return (
        "PROMOTE_FOR_FURTHER_OFFLINE_EVALUATION"
        if sum(r["glyph_correspondences"] or 0 for r in rows)
        else "REJECT"
    )


def run(sources: dict[str, Path], output: Path, snapshot: Path, validation_config: Path) -> dict:
    fresh_output(output, Path("local-corpus"), root=ROOT)
    if not output.resolve().is_relative_to(ROOT / "evaluation-output") or set(sources) != set(
        SOURCE_SHA
    ):
        raise ValueError("Probe scope rejected")
    if any(sha(path) != SOURCE_SHA[key] for key, path in sources.items()):
        raise ValueError("Pinned source drift")
    from tools.extraction_quality.pdf_dev_reference import validate_snapshot
    from tools.extraction_quality.pdf_native_dev_diagnostic import (
        REFERENCE_FINGERPRINT,
        validation_args,
    )

    args = validation_args(validation_config)
    validation = validate_snapshot(snapshot, args)
    if validation["snapshot_fingerprint"] != REFERENCE_FINGERPRINT:
        raise ValueError("Pinned reference drift")
    output.mkdir(parents=True)
    pins = registration(sources)
    write_json(output / "registration.json", pins)
    captures, runtimes = {}, []
    for repetition in (1, 2):
        run_dir = output / f"run-{repetition}"
        run_dir.mkdir()
        for key, path in sources.items():
            destination = run_dir / key
            destination.mkdir()
            runtime = monitor(
                [
                    sys.executable,
                    "-m",
                    "tools.extraction_quality.pdf_table_source_only_probe",
                    "--worker",
                    str(path),
                    "--output",
                    str(destination),
                ],
                destination,
            )
            runtimes.append(dict(repetition=repetition, source_id=key, **runtime))
            if not runtime["failure"]:
                captures[(repetition, key)] = json.loads(
                    (destination / "result.json").read_text(encoding="utf-8")
                )
    # Freeze all inference outputs before opening any reference field for scoring.
    sealed = {
        f"run-{n}/{key}/result.json": sha(output / f"run-{n}" / key / "result.json")
        for n, key in captures
    }
    write_json(output / "inference-seal.json", dict(files=sealed, fingerprint=fingerprint(sealed)))
    deterministic = len(captures) == 4 and all(
        captures[(1, k)] == captures[(2, k)] for k in sources
    )
    frozen = json.loads((snapshot / "reference.json").read_text(encoding="utf-8"))
    rows = [
        score(d, captures[(1, d["document_id"])])
        if (1, d["document_id"]) in captures
        else dict(
            source_id=d["document_id"],
            candidate_status="unknown",
            baseline_unchanged=None,
            glyph_correspondences=None,
            violations=[],
            cell_denominator=len(d["cells"]),
            grid_denominator=len(d["logical_grids"]),
            issue="MISSING_CAPTURE",
        )
        for d in frozen["documents"]
    ]
    if registration(sources) != pins or validate_snapshot(snapshot, args) != validation:
        raise ValueError("Frozen input/config/code drift")
    if any(sha(output / name) != digest for name, digest in sealed.items()):
        raise ValueError("Sealed inference drift")
    result = dict(
        engineering_execution="PASS" if len(captures) == 4 and deterministic else "BLOCKED",
        candidate_verdict=decision(rows, len(captures) == 4, deterministic),
        quality_gate="NOT_EVALUATED",
        documents=rows,
        attempted_sources=2,
        paired_source_executions=4,
        completed_captures=len(captures),
        reference_fingerprint=REFERENCE_FINGERPRINT,
        deterministic=deterministic,
        registration_fingerprint=fingerprint(pins),
        unresolved_dimensions=frozen["unresolved_dimensions"],
    )
    result["fingerprint"] = fingerprint(result)
    write_json(output / "evaluation.json", result)
    write_json(output / "runtime.json", dict(observations=runtimes))
    write_json(
        output / "COMPLETE.json",
        {
            p.relative_to(output).as_posix(): sha(p)
            for p in sorted(output.rglob("*"))
            if p.is_file()
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--validation-config", type=Path)
    args = parser.parse_args()
    try:
        if args.worker:
            return worker(args.worker, args.output)
        sources = {key: Path(path) for key, path in (value.split("=", 1) for value in args.source)}
        result = run(sources, args.output, args.snapshot, args.validation_config)
        print(
            json.dumps(
                {
                    k: result[k]
                    for k in ("engineering_execution", "candidate_verdict", "fingerprint")
                },
                sort_keys=True,
            )
        )
        return 0 if result["engineering_execution"] == "PASS" else 2
    except Exception:
        print("BLOCKED: probe source/config/capture/reference integrity rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
