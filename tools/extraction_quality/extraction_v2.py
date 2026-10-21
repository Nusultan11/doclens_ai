"""Corpus v2 CLI: prepare controls, validate and run bounded native observations twice.

No production routing, package installation, dataset download or implicit Gold
generation. Populated manifests, raw captures and runtime journals stay ignored.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import importlib.metadata
import io
import json
import logging
import math
import platform
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from pydantic import TypeAdapter

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_eval import _observations, score_record, verify_corpus
from doclens_ai.extraction.fidelity_gold import fingerprint, load_gold
from doclens_ai.extraction.models import ExtractionResult
from doclens_ai.extraction.parsers import ExtractionLimits
from tools.pdf_ocr_candidate import benchmark as bounded

ROOT = Path(__file__).resolve().parents[2]


def private_destination(path: Path) -> None:
    corpus.no_links(path)
    if not path.resolve().is_relative_to((ROOT / "evaluation-output").resolve()):
        raise ValueError("ignored evaluation-output destination required")
    if path.exists():
        raise ValueError("fresh destination required")


def write(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n")


def prepare_controls(template: Path, manifest: Path, raw: Path, output: Path) -> dict:
    """Reference immutable v1 bytes, without modifying or counting them as new v2 pilot data."""
    private_destination(output)
    template_value = corpus.load(template)
    corpus.no_links(manifest)
    rows = list(csv.DictReader(manifest.open(encoding="utf-8", newline="")))
    expected = {r["document_id"]: (r["sha256"], int(r["size_bytes"]), r["format"]) for r in rows}
    if len(expected) != len(rows):
        raise ValueError("duplicate legacy identity")
    paths = verify_corpus(raw, expected, ExtractionLimits())
    samples = []
    for row in rows:
        identity = row["document_id"]
        samples.append(
            corpus.Sample(
                sample_id="e2-" + identity,
                dataset="corpus-v1-controls",
                release="corpus-v1",
                revision=corpus.sha256(manifest),
                source_record_id=identity,
                cohort="legacy_control",
                disposition="admitted",
                original=corpus.Asset(
                    path=paths[identity].relative_to(raw).as_posix(),
                    sha256=row["sha256"],
                    size_bytes=int(row["size_bytes"]),
                    format=row["format"],
                ),
                rights=corpus.Rights(
                    dataset_license=row["license"],
                    original_license=row["license"],
                    local_evaluation=True,
                    annotation_use=None,
                    redistribution=None,
                    references=("docs/eda/corpus_v1_protocol.md", row["license_basis_url"]),
                    sensitivity="public",
                ),
                languages=(row["document_language"],),
                document_type="legacy_public_sector",
                difficulty=("not_relabelled",),
                # Group by source page; translation/family completeness remains unknown.
                family_id="f-" + fingerprint(row["source_page_url"])[:24],
                family_review="unknown",
                split="dev",
                publicly_exposed=True,
                unsupported=("new_pilot_quota", "independent_review", "family_completeness"),
            )
        )
    result = corpus.Corpus(
        revision=template_value.revision + "-legacy-controls",
        selection_seed=template_value.selection_seed,
        split_revision=template_value.split_revision,
        targets=template_value.targets,
        samples=tuple(samples),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, result.model_dump(mode="json"))
    return {
        "legacy_controls": len(samples),
        "new_pilot_samples": 0,
        "manifest_fingerprint": fingerprint(result.model_dump(mode="json")),
    }


def exact_positions(text: str, literal: str) -> list[int]:
    """Exact Unicode, including numeric token boundaries. No sign/zero/unit normalization."""
    if not literal:
        return []
    return [
        m.start()
        for m in re.finditer(r"(?<![\w+−.,/:\-])" + re.escape(literal) + r"(?![\w.,/:\-])", text)
    ]


def historical_scores(record, result: ExtractionResult) -> dict:
    values = score_record(record, result)
    texts = [o.text for o in _observations(result)]
    numeric = [a for a in record.anchors if any(c.isdecimal() for c in a.text)]
    values["metrics"]["exact_numeric_anchors"] = {
        "passed": sum(any(exact_positions(t, a.text) for t in texts) for a in numeric),
        "total": len(numeric),
        "unsupported": 0,
    }
    values["evidence_class"] = "legacy_review_attestation_not_new_independent_gold"
    return values


def expected_metrics(record) -> dict[str, int]:
    return {
        "required_text_recall": len(record.anchors),
        "reading_order": len(record.order_pairs),
        "table_cells": len(record.table_cells),
        "table_relationships": len(record.table_relationships),
        "provenance": len(record.anchors) + len(record.cells),
        "displayed_values": 0,
        "stored_values": len(record.cells),
        "formulas": len(record.cells),
        "cached_values": len(record.cells),
        "exact_numeric_anchors": sum(any(c.isdecimal() for c in a.text) for a in record.anchors),
    }


def frozen_identity(manifest: Path, gold: Path | None, limits: bounded.Limits) -> dict:
    source_paths = [
        ROOT / "src/doclens_ai/eda/corpus_v2.py",
        ROOT / "src/doclens_ai/eda/dataset_adapters_v2.py",
        ROOT / "src/doclens_ai/extraction/models.py",
        ROOT / "src/doclens_ai/extraction/parsers.py",
        ROOT / "src/doclens_ai/extraction/fidelity_eval.py",
        ROOT / "src/doclens_ai/extraction/fidelity_gold.py",
        ROOT / "tools/extraction_quality/extraction_v2.py",
        ROOT / "tools/pdf_ocr_candidate/benchmark.py",
    ]
    inventory = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    return {
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "manifest_sha256": corpus.sha256(manifest),
        "legacy_gold_sha256": corpus.sha256(gold) if gold else None,
        "code": {p.relative_to(ROOT).as_posix(): corpus.sha256(p) for p in source_paths},
        "configuration": asdict(limits),
        "python": platform.python_version(),
        "dependencies": dict(sorted(inventory.items())),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": __import__("os").cpu_count(),
        "concurrency": 1,
        "executable_sha256": corpus.sha256(Path(sys.executable)),
        "scoring": "legacy-score_record-plus-exact-numeric-token-v2",
        "resource_scope": "fresh worker startup+native extraction; sampled process-tree RSS bytes",
        "percentiles": "nearest_rank",
        "cache": "OS cache not reset",
        "gpu": "NOT_USED",
        "approved_thresholds": "TBD",
    }


def percentile(values: list[float], fraction: float):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def summarize(rows: list[dict]) -> dict:
    statuses = Counter(r["status"] for r in rows)
    times = [r["runtime"]["seconds"] for r in rows if r.get("runtime")]
    peaks = [r["runtime"]["peak_tree_rss_bytes"] for r in rows if r.get("runtime")]
    scores: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        for key, value in (row.get("legacy_scores") or {}).get("metrics", {}).items():
            for index, field in enumerate(("passed", "total", "unsupported")):
                scores[key][index] += (
                    value.get("evaluated", value.get("total", 0))
                    if field == "total"
                    else value.get(field, 0)
                )
    reference_totals = Counter()
    for row in rows:
        reference_totals.update(row.get("legacy_expected") or {})
    return {
        "attempted": len(rows),
        "eligible": sum(r["eligible"] for r in rows),
        "states": dict(sorted(statuses.items())),
        "latency_p50_seconds": percentile(times, 0.5),
        "latency_p95_seconds": percentile(times, 0.95),
        "peak_sampled_tree_rss_bytes": max(peaks) if peaks else None,
        "legacy_attested_metrics": {
            k: {
                "passed": scores[k][0],
                "total": scores[k][1],
                "unsupported": scores[k][2],
                "expected_total": reference_totals[k],
                "unobserved": reference_totals[k] - scores[k][1],
            }
            for k in sorted(reference_totals)
        },
        "legacy_labelled_documents": sum(bool(r.get("legacy_expected")) for r in rows),
        "legacy_unscored_documents": sum(
            bool(r.get("legacy_expected")) and r.get("legacy_scores") is None for r in rows
        ),
        "independent_gold_metrics": "NOT_EVALUATED",
    }


def non_runtime(value):
    """Compare all report fields recursively except actual measured resources and fingerprint."""
    if isinstance(value, dict):
        return {
            k: non_runtime(v)
            for k, v in value.items()
            if k
            not in {
                "runtime",
                "latency_p50_seconds",
                "latency_p95_seconds",
                "peak_sampled_tree_rss_bytes",
                "deterministic_fingerprint",
            }
        }
    if isinstance(value, list):
        return [non_runtime(v) for v in value]
    return value


def result_leaves(value, path: str = "") -> list[dict[str, str]]:
    """Canonical lossless JSON/CSV projection, including nulls and empty containers."""
    if isinstance(value, dict) and value:
        return [
            row
            for key, child in sorted(value.items())
            for row in result_leaves(child, f"{path}/{key}")
        ]
    if isinstance(value, list) and value:
        return [
            row
            for index, child in enumerate(value)
            for row in result_leaves(child, f"{path}/{index}")
        ]
    return [{"metric_path": path, "value_json": json.dumps(value, ensure_ascii=True)}]


def verify_results(results: Path, csv_path: Path) -> dict:
    """Reconcile delivered reports without rerunning extraction or upgrading evidence."""
    value = corpus.read_json(results)
    digest = value["consolidated_fingerprint"]
    if digest != fingerprint({k: v for k, v in value.items() if k != "consolidated_fingerprint"}):
        raise ValueError("consolidated fingerprint mismatch")
    corpus.no_links(csv_path)
    if csv_path.stat().st_size > 20 * 1024**2:
        raise ValueError("CSV limit")
    with csv_path.open(encoding="utf-8", newline="") as stream:
        if list(csv.DictReader(stream)) != result_leaves(value):
            raise ValueError("JSON/CSV mismatch")
    identities = set()
    for cohort in value["native"].values():
        expected = [r["sample_id"] for r in cohort["integrity"]["rows"]]
        runs = cohort["runs"]
        if len(runs) != 2 or len(set(expected)) != len(expected) or identities & set(expected):
            raise ValueError("incomplete or duplicate native cohort")
        identities.update(expected)
        for run in runs:
            rows = run["rows"]
            if (
                [r["sample_id"] for r in rows] != expected
                or run["summary"] != summarize(rows)
                or run["deterministic_fingerprint"] != fingerprint(non_runtime(run))
                or run["pins_fingerprint"] != fingerprint(cohort["pins"])
                or run["integrity_fingerprint"] != fingerprint(cohort["integrity"])
            ):
                raise ValueError("native report mismatch")
            for field, slices in run["slices"].items():
                groups = defaultdict(list)
                for row in rows:
                    keys = row[field] if isinstance(row[field], list) else [row[field]]
                    for key in keys:
                        groups[key].append(row)
                if slices != {k: summarize(v) for k, v in sorted(groups.items())}:
                    raise ValueError("native slice mismatch")
            if set(run["slices"]) != {"format", "languages", "family", "difficulty", "cohort"}:
                raise ValueError("missing native slices")
        repeated = cohort["reproducibility"]
        if (
            non_runtime(runs[0]) != non_runtime(runs[1])
            or repeated["summaries"] != [run["summary"] for run in runs]
            or repeated["deterministic_fingerprints"]
            != [run["deterministic_fingerprint"] for run in runs]
            or repeated["pins_fingerprint"] != fingerprint(cohort["pins"])
        ):
            raise ValueError("native repetition mismatch")
    cells = value["alignment"]["sanitized_cells"]
    summary = value["alignment"]["summary"]
    if (
        len(cells) != summary["cells_attempted"]
        or dict(Counter(c["status"] for c in cells)) != summary["states"]
        or sum(c["candidate_agrees"] is not None for c in cells)
        != summary["candidate_literals_compared"]
    ):
        raise ValueError("alignment accounting mismatch")
    documents = value["ocr"]["quality"]["documents"]
    recovered = sum(len(d["comparison"]["recovered"]) for d in documents)
    if recovered != value["ocr"]["recovered_anchors"]:
        raise ValueError("OCR recovery accounting mismatch")
    return {
        "execution": "PASS",
        "documents": len(identities),
        "consolidated_fingerprint": digest,
        "scope": "report reconciliation only; source captures require separate local audit",
    }


def evaluate(
    manifest: Path,
    root: Path,
    output: Path,
    *,
    gold: Path | None = None,
    limits: bounded.Limits | None = None,
) -> dict:
    private_destination(output)
    value = corpus.load(manifest)
    integrity = corpus.audit(value, root)
    limits = limits or bounded.Limits(max_pages=2000, max_process_bytes=1024**3, timeout_seconds=60)
    pins = frozen_identity(manifest, gold, limits)
    pin_id = fingerprint(pins)
    controls = [s for s in value.samples if s.cohort == "legacy_control"]
    if len({s.source_record_id for s in controls}) != len(controls):
        raise ValueError("ambiguous legacy control identity")
    expected = {
        s.source_record_id: (s.original.sha256, s.original.size_bytes, s.original.format)
        for s in controls
        if s.original
    }
    labels = {r.document_id: r for r in load_gold(gold, expected)} if gold else {}
    output.mkdir(parents=True)
    write(output / "pins.json", pins)
    write(output / "integrity.json", integrity)
    reports = []
    by_id = {r["sample_id"]: r for r in integrity["rows"]}
    for repetition in (1, 2):
        run = output / f"run-{repetition}"
        run.mkdir()
        rows, texts = [], {}
        for sample in value.samples:
            eligible = by_id[sample.sample_id]["native_eligible"]
            label = (
                labels.get(sample.source_record_id) if sample.cohort == "legacy_control" else None
            )
            row = {
                "sample_id": sample.sample_id,
                "cohort": sample.cohort,
                "format": sample.original.format if sample.original else "unknown",
                "languages": list(sample.languages),
                "family": sample.family_id,
                "difficulty": list(sample.difficulty),
                "split": sample.split,
                "eligible": eligible,
                "status": "ineligible",
                "runtime": None,
                "failure": None,
                "legacy_scores": None,
                "legacy_expected": expected_metrics(label) if label else None,
            }
            if eligible:
                try:
                    source = corpus.asset_path(root, sample.original)
                except (OSError, ValueError):
                    row.update(status="failed", failure="source_changed_before_capture")
                    rows.append(row)
                    continue
                capture = bounded.isolated(
                    source,
                    bounded.Runtime("", "", ""),
                    limits,
                    run / sample.sample_id,
                    candidate=False,
                )
                row.update(runtime=capture["runtime"], failure=capture["failure"])
                raw = capture.get("result")
                if raw is None:
                    row["status"] = "failed"
                else:
                    try:
                        result = TypeAdapter(ExtractionResult).validate_json(json.dumps(raw))
                        if (
                            result.source_sha256 != sample.original.sha256
                            or result.source_size_bytes != sample.original.size_bytes
                            or result.document_format != sample.original.format
                        ):
                            raise ValueError("capture source mismatch")
                        corpus.asset_path(root, sample.original)  # Detect changes during execution.
                        row["status"] = result.status.value
                        row["extraction_fingerprint"] = fingerprint(result.to_dict())
                        row["warnings"] = dict(
                            sorted(Counter(w.code.value for w in result.warnings).items())
                        )
                        observations = _observations(result)
                        row["observations"] = len(observations)
                        row["page_numbers"] = sorted(
                            {
                                o.source.page_number
                                for o in observations
                                if o.source.page_number is not None
                            }
                        )
                        # Text stays local; shingles only diagnose leakage.
                        texts[sample.sample_id] = "\n".join(o.text for o in observations)
                        if label and result.status.value != "failed":
                            row["legacy_scores"] = historical_scores(label, result)
                    except (ValueError, OSError):
                        row.update(status="failed", failure="invalid_or_changed_capture")
            rows.append(row)
        pairs = corpus.near_duplicate_pairs(texts)
        cross_split = [
            (a, b)
            for a, b in pairs
            if next(s.split for s in value.samples if s.sample_id == a)
            != next(s.split for s in value.samples if s.sample_id == b)
        ]
        slices = {}
        for field in ("format", "languages", "family", "difficulty", "cohort"):
            groups = defaultdict(list)
            for row in rows:
                keys = row[field] if isinstance(row[field], list) else [row[field]]
                for key in keys:
                    groups[key].append(row)
            slices[field] = {k: summarize(v) for k, v in sorted(groups.items())}
        report = {
            "schema_version": "extraction-v2-results-1",
            "pins_fingerprint": pin_id,
            "integrity_fingerprint": fingerprint(integrity),
            "rows": rows,
            "summary": summarize(rows),
            "slices": slices,
            "near_duplicate_pairs": pairs,
            "near_duplicate_cross_split": cross_split,
            "quality": "FAIL" if integrity["qg_00"] == "FAIL" or cross_split else "NOT_EVALUATED",
            "experiment": "INCONCLUSIVE",
            "production_authorized": False,
        }
        report["deterministic_fingerprint"] = fingerprint(non_runtime(report))
        write(run / "results.json", report)
        with (run / "results.csv").open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "sample_id",
                    "cohort",
                    "format",
                    "split",
                    "eligible",
                    "status",
                    "failure",
                ],
            )
            writer.writeheader()
            writer.writerows({k: r[k] for k in writer.fieldnames} for r in rows)
        reports.append(report)
    stable = non_runtime(reports[0]) == non_runtime(reports[1])
    pins_unchanged = pins == frozen_identity(manifest, gold, limits)
    integrity_unchanged = integrity == corpus.audit(corpus.load(manifest), root)
    result = {
        "execution": "PASS"
        if stable
        and value.samples
        and integrity["native_eligible"] == len(value.samples)
        and pins_unchanged
        and integrity_unchanged
        and all(
            r["failure"] is None and r.get("extraction_fingerprint") for r in reports[0]["rows"]
        )
        else "BLOCKED",
        "quality": reports[0]["quality"],
        "experiment": "INCONCLUSIVE",
        "deterministic_equal": stable,
        "pins_unchanged": pins_unchanged,
        "integrity_unchanged": integrity_unchanged,
        "pins_fingerprint": pin_id,
        "deterministic_fingerprints": [r["deterministic_fingerprint"] for r in reports],
        "summaries": [r["summary"] for r in reports],
        "production_authorized": False,
    }
    write(output / "reproducibility.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-controls")
    prepare.add_argument("--template", type=Path, required=True)
    prepare.add_argument("--legacy-manifest", type=Path, required=True)
    prepare.add_argument("--root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify-results")
    verify.add_argument("--results", type=Path, required=True)
    verify.add_argument("--csv", type=Path, required=True)
    for name in ("validate", "baseline"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "baseline":
            command.add_argument("--legacy-gold", type=Path)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            if args.command == "verify-results":
                result = verify_results(args.results, args.csv)
            elif args.command == "prepare-controls":
                result = prepare_controls(
                    args.template, args.legacy_manifest, args.root, args.output
                )
            elif args.command == "validate":
                private_destination(args.output)
                result = corpus.audit(corpus.load(args.manifest), args.root)
                result["execution"] = (
                    "PASS"
                    if result["sample_attempts"] and all(not r["issues"] for r in result["rows"])
                    else "BLOCKED"
                )
                write(args.output, result)
            else:
                result = evaluate(args.manifest, args.root, args.output, gold=args.legacy_gold)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("execution", "PASS") == "PASS" else 2
    except Exception:  # noqa: BLE001 - never print source paths, annotation literals or errors
        print("BLOCKED: corpus, source binding, runtime or fresh private destination rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
