"""Score qualified historical DEV dimensions from frozen captures; no extraction."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_eval import _metric, _read_sources, score_record
from doclens_ai.extraction.fidelity_gold import FidelityRecord, fingerprint, load_gold
from doclens_ai.extraction.models import ExtractionResult
from tools.extraction_quality import historical_gold_eligibility as eligibility
from tools.extraction_quality.readiness_io import ROOT, atomic, confined

VERSION = "historical-dev-saved-baseline-1"
DEFAULT_ELIGIBILITY = "evaluation-output/historical-gold-dev-20261026/run-1"
FILES = {"scores.json", "summary.json", "COMPLETE.json"}
HISTORICAL = "HISTORICAL_ATTESTATION_ONLY"
TECHNICAL = "TECHNICALLY_SUPPORTED_LITERAL"
UNRESOLVED = "UNRESOLVED_SOURCE_EVIDENCE"


def tier(row: dict) -> str:
    resolved = row["technical_support"]["technically_resolved"]
    return HISTORICAL if resolved is None else TECHNICAL if resolved else UNRESOLVED


def dimension(record: FidelityRecord, capture: ExtractionResult, row: dict, name: str) -> dict:
    """Use an in-memory view, never write/relabel Gold or change anchor locators."""
    group = row["group"]
    index = int(row["assertion_id"].rsplit("/", 1)[1])
    assertion = getattr(record, group)[index]
    plan = eligibility.metric_plan(record, group, assertion)
    admission = row["metrics"].get(name)
    if (
        row["eligibility"] != eligibility.ELIGIBLE
        or admission is None
        or admission["eligibility"] != eligibility.ELIGIBLE
        or admission["supported"] is not True
        or name not in plan
        or plan[name]
    ):
        raise ValueError("ineligible or unsupported scoring dimension")
    dependencies = set(eligibility.anchor_ids(record, group, assertion))
    view = {key: () for key in eligibility.GROUPS}
    view[group] = (assertion,)
    if group != "anchors":
        view["anchors"] = tuple(a for a in record.anchors if a.anchor_id in dependencies)
    # Structural dimensions keep their dependency anchors; cell provenance has none.
    metric = score_record(record.model_copy(update=view), capture)["metrics"][name]
    if metric["evaluated"] != 1 or metric["unsupported"] or metric["passed"] not in (0, 1):
        raise ValueError("scorer denominator or support drift")
    return metric


def score(
    ledger: dict, records: tuple[FidelityRecord, ...], captures: dict[str, ExtractionResult]
) -> dict:
    """Caller verifies the frozen eligibility first; reconcile all rows and captures."""
    expected = eligibility.assertions(records)
    rows = eligibility.indexed(ledger["assertions"], "assertion_id")
    if set(rows) != set(expected) or len({r.document_id for r in records}) != len(records):
        raise ValueError("assertion denominator drift")
    needed = {
        row["source_id"] for row in rows.values() if row["eligibility"] == eligibility.ELIGIBLE
    }
    if set(captures) != needed:
        raise ValueError("missing or foreign saved capture")
    for record in records:
        if record.document_id in needed:
            capture = captures[record.document_id]
            if (capture.source_sha256, capture.source_size_bytes, capture.document_format) != (
                record.source_sha256,
                record.source_size_bytes,
                record.document_format,
            ):
                raise ValueError("saved capture source identity drift")
    output = []
    for key, row in sorted(rows.items()):
        record, group, assertion = expected[key]
        plan = eligibility.metric_plan(record, group, assertion)
        dependencies = [
            f"{record.document_id}/anchors/{i}"
            for anchor in eligibility.anchor_ids(record, group, assertion)
            for i, a in enumerate(record.anchors)
            if a.anchor_id == anchor
        ]
        if (
            row["source_id"] != record.document_id
            or row["source_sha256"] != record.source_sha256
            or row["format"] != record.document_format
            or row["group"] != group
            or row["assertion_sha256"] != fingerprint(assertion.model_dump(mode="json"))
            or set(row["metrics"]) != set(plan)
            or row["anchor_dependencies"] != dependencies
        ):
            raise ValueError("assertion binding or metric plan drift")
        metrics = {}
        for name, admission in row["metrics"].items():
            measured = admission["eligibility"] == eligibility.ELIGIBLE
            if measured and any(
                rows[d]["eligibility"] != eligibility.ELIGIBLE for d in dependencies
            ):
                raise ValueError("ineligible anchor dependency")
            metrics[name] = {
                **admission,
                "measurement": dimension(record, captures[row["source_id"]], row, name)
                if measured
                else None,
            }
        output.append(
            {
                "assertion_id": key,
                "source_id": row["source_id"],
                "format": row["format"],
                "group": group,
                "evidence_tier": tier(row),
                "eligibility": row["eligibility"],
                "reason_codes": row["reason_codes"],
                "assertion_sha256": row["assertion_sha256"],
                "anchor_dependencies": dependencies,
                "metrics": metrics,
            }
        )
    result = {
        "version": VERSION,
        "scope": "LOCAL_DEV_HISTORICAL_SAVED_BASELINE_ONLY",
        "eligibility_fingerprint": ledger["fingerprint"],
        "assertions": output,
        "captures": {
            key: {"status": c.status.value, "fingerprint": fingerprint(c.to_dict())}
            for key, c in sorted(captures.items())
        },
        "quality_gate": "NOT_EVALUATED",
        "independent_gold": False,
        "new_extraction_or_inference": False,
    }
    denominators = eligibility.summarize(ledger)["metric_denominators"]
    measured = summarize(result)["metrics"]
    if any(measured[n]["evaluated"] != denominators[n][eligibility.ELIGIBLE] for n in denominators):
        raise ValueError("eligible metric denominator drift")
    return result


def summarize(result: dict) -> dict:
    rows = result["assertions"]

    def aggregate(selected: list[dict]) -> dict:
        metrics = {}
        for name in eligibility.METRICS:
            values = [r["metrics"][name] for r in selected if name in r["metrics"]]
            measurements = [v["measurement"] for v in values if v["measurement"] is not None]
            metrics[name] = {
                **_metric(
                    sum(m["passed"] for m in measurements),
                    sum(m["evaluated"] for m in measurements),
                ),
                "requested": len(values),
                "review_required": sum(v["eligibility"] == eligibility.REVIEW for v in values),
                "excluded": sum(v["eligibility"] == eligibility.EXCLUDED for v in values),
                "unsupported": sum(not v["supported"] for v in values),
            }
        return {
            "assertions": len(selected),
            "eligible_assertions": sum(r["eligibility"] == eligibility.ELIGIBLE for r in selected),
            "metrics": metrics,
        }

    return {
        "version": VERSION,
        "scope": result["scope"],
        **aggregate(rows),
        "by_format": {
            f: aggregate([r for r in rows if r["format"] == f]) for f in ("pdf", "docx", "xlsx")
        },
        "by_group": {
            g: aggregate([r for r in rows if r["group"] == g]) for g in eligibility.GROUPS
        },
        "by_evidence_tier": {
            t: aggregate([r for r in rows if r["evidence_tier"] == t])
            for t in (HISTORICAL, TECHNICAL, UNRESOLVED)
        },
        "by_document": {
            key: aggregate([r for r in rows if r["source_id"] == key])
            for key in sorted({r["source_id"] for r in rows})
        },
        "saved_capture_statuses": {
            s: sum(c["status"] == s for c in result["captures"].values())
            for s in ("success", "needs_review", "failed")
        },
        "quality_gate": "NOT_EVALUATED",
        "independent_gold": False,
        "new_extraction_or_inference": False,
    }


def load_capture(row: dict) -> ExtractionResult:
    binding = row["parser_agreement"]
    path = confined(ROOT, binding["capture"])
    before = corpus.sha256(path)
    if before != binding["capture_sha256"]:
        raise ValueError("saved capture SHA drift")
    capture = TypeAdapter(ExtractionResult).validate_python(
        corpus.read_json(path, max_bytes=256 * 1024**2)
    )
    if corpus.sha256(path) != before:
        raise ValueError("saved capture changed during read")
    return capture


def reconstruct(eligibility_root: Path) -> dict:
    proof = eligibility.verify(eligibility_root)
    ledger_path = eligibility_root / "eligibility.json"
    ledger_sha = corpus.sha256(ledger_path)
    ledger = corpus.read_json(ledger_path)
    if (
        ledger["fingerprint"] != proof["ledger_fingerprint"]
        or fingerprint({k: v for k, v in ledger.items() if k != "fingerprint"})
        != proof["ledger_fingerprint"]
    ):
        raise ValueError("eligibility changed during read")
    records = load_gold(ROOT / eligibility.release.GOLD, _read_sources(ROOT / eligibility.MANIFEST))
    captures, pins = {}, {}
    for row in ledger["assertions"]:
        if row["eligibility"] == eligibility.ELIGIBLE:
            key = row["source_id"]
            binding = row["parser_agreement"]
            pin = (binding["capture"], binding["capture_sha256"])
            if key in pins and pins[key] != pin:
                raise ValueError("conflicting saved captures")
            if key not in captures:
                captures[key], pins[key] = load_capture(row), pin
    result = score(ledger, records, captures)
    inputs = {
        **ledger["binding"]["input_sha256"],
        ledger_path.relative_to(ROOT).as_posix(): ledger_sha,
    }
    if any(corpus.sha256(confined(ROOT, p)) != sha for p, sha in inputs.items()):
        raise ValueError("frozen input changed during scoring")
    code = (
        "tools/extraction_quality/historical_dev_baseline.py",
        "tools/extraction_quality/readiness_io.py",
        "src/doclens_ai/extraction/models.py",
    )
    result["binding"] = {
        "eligibility_root": eligibility_root.relative_to(ROOT).as_posix(),
        "eligibility_sha256": ledger_sha,
        "release_fingerprint": ledger["binding"]["release_fingerprint"],
        "gold_fingerprint": ledger["binding"]["gold_fingerprint"],
        "input_sha256": inputs,
        "code_sha256": {
            **ledger["binding"]["code_sha256"],
            **{p: corpus.sha256(ROOT / p) for p in code},
        },
        "python": sys.version.split()[0],
        "dependencies": {n: importlib.metadata.version(n) for n in ("pydantic", "openpyxl")},
        "scorer": "fidelity_eval.score_record unchanged; whitespace-only literal normalization",
    }
    result["fingerprint"] = fingerprint(result)
    return result


def private(path: Path) -> None:
    corpus.no_links(path)
    if not path.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("private output required")


def build(output: Path, eligibility_root: Path) -> dict:
    private(output)
    if output.exists():
        raise ValueError("fresh output required")
    result = reconstruct(eligibility_root)
    summary = {**summarize(result), "fingerprint": result["fingerprint"]}
    output.mkdir(parents=True)
    atomic(output / "scores.json", result)
    atomic(output / "summary.json", summary)
    atomic(
        output / "COMPLETE.json",
        {n: corpus.sha256(output / n) for n in sorted(FILES - {"COMPLETE.json"})},
    )
    return summary


def verify(output: Path) -> dict:
    private(output)
    files = set()
    for path in output.rglob("*"):
        corpus.no_links(path)
        if path.is_file():
            files.add(path.relative_to(output).as_posix())
    if files != FILES:
        raise ValueError("baseline artifact inventory mismatch")
    if corpus.read_json(output / "COMPLETE.json") != {
        n: corpus.sha256(output / n) for n in sorted(FILES - {"COMPLETE.json"})
    }:
        raise ValueError("baseline artifact drift")
    result = corpus.read_json(output / "scores.json")
    expected = reconstruct(confined(ROOT, result["binding"]["eligibility_root"]))
    if result != expected or corpus.read_json(output / "summary.json") != {
        **summarize(expected),
        "fingerprint": expected["fingerprint"],
    }:
        raise ValueError("baseline reconstruction mismatch")
    return {"status": "PASS", "fingerprint": expected["fingerprint"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--eligibility", type=Path, default=Path(DEFAULT_ELIGIBILITY))
    args = parser.parse_args()
    try:
        result = (
            build(args.output.resolve(), args.eligibility.resolve())
            if args.mode == "build"
            else verify(args.output.resolve())
        )
        print(
            json.dumps(
                {
                    k: v
                    for k, v in result.items()
                    if k in {"status", "fingerprint", "metrics", "eligible_assertions"}
                },
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        print(
            json.dumps(
                {"status": "BLOCKED", "reason": "historical_saved_baseline_validation_failed"}
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
