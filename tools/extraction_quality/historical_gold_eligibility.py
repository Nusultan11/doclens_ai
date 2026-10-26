"""Qualify frozen historical labels for local DEV diagnostics, never independent Gold.

No model, extraction or new source annotation is run. Saved parser agreement is
informational; eligibility uses historical attestations and known source issues.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_eval import _read_sources, verify_corpus
from doclens_ai.extraction.fidelity_gold import FidelityRecord, fingerprint, load_gold
from doclens_ai.extraction.parsers import ExtractionLimits
from tools.extraction_quality import readiness_release as release
from tools.extraction_quality.blind_review_batch import family_map
from tools.extraction_quality.readiness_io import ROOT, atomic, confined

VERSION = "historical-extraction-dev-eligibility-1"
DEFAULT_RELEASE = "evaluation-output/extraction-readiness-continuation-20261023-v2"
MANIFEST = "docs/eda/corpus_v1_manifest.csv"
ELIGIBLE = "DEV_DIAGNOSTIC_ELIGIBLE"
REVIEW = "REVIEW_REQUIRED"
EXCLUDED = "EXCLUDED"
GROUPS = ("anchors", "order_pairs", "table_cells", "table_relationships", "cells")
METRICS = (
    "required_text_recall",
    "provenance",
    "reading_order",
    "table_cells",
    "table_relationships",
    "stored_values",
    "formulas",
    "cached_values",
    "displayed_values",
)
RESOLVED = {
    "SOURCE_LITERAL_AND_REGION_SUPPORTED",
    "SOURCE_LITERAL_AND_PHYSICAL_CELL_SUPPORTED",
    "SOURCE_LITERAL_AT_GENUINE_PAGE_BBOX",
}
UNRESOLVED = {
    "SEMANTIC_READING_ORDER_REQUIRES_JUDGMENT",
    "SOURCE_NATIVE_NOT_FOUND",
    "SOURCE_AMBIGUOUS",
    "LOGICAL_GRID_OR_SPAN_REQUIRES_REVIEW",
    "SEMANTIC_OR_AMBIGUOUS_CELL_RELATION_REQUIRES_REVIEW",
    "PHYSICAL_EXTENT_SUPPORTED_LOGICAL_SPAN_REQUIRES_REVIEW",
    "PHYSICAL_ALIGNMENT_SUPPORTED_LOGICAL_RELATION_REQUIRES_REVIEW",
}


@dataclass(frozen=True)
class Population:
    documents: int = 19
    assertions: int = 282
    previous_issues: int = 95
    technically_resolved: int = 13


FROZEN_POPULATION = Population()


def indexed(items: list[dict], key: str) -> dict[str, dict]:
    result = {item[key]: item for item in items}
    if len(result) != len(items):
        raise ValueError("duplicate qualification identity")
    return result


def assertions(records: tuple[FidelityRecord, ...]) -> dict[str, tuple]:
    result = {}
    for record in records:
        for group in GROUPS:
            for index, value in enumerate(getattr(record, group)):
                result[f"{record.document_id}/{group}/{index}"] = (record, group, value)
    return result


def anchor_ids(record: FidelityRecord, group: str, value) -> list[str]:
    if group == "anchors":
        return [value.anchor_id]
    if group == "order_pairs":
        return [value.before, value.after]
    if group == "table_cells":
        return [value.anchor_id]
    if group == "table_relationships":
        return [value.left, value.right]
    return []


def metric_plan(record: FidelityRecord, group: str, value) -> dict[str, list[str]]:
    """Unsupported means the frozen scorer cannot represent the requested check.

    A native parser's inability to emit a PDF table is a possible failure, not an
    unsupported metric: another structured candidate can be measured by this scorer.
    """
    names = {
        "anchors": ("required_text_recall", "provenance"),
        "order_pairs": ("reading_order",),
        "table_cells": ("table_cells",),
        "table_relationships": ("table_relationships",),
        "cells": ("provenance", "stored_values", "formulas", "cached_values"),
    }[group]
    plan = {name: [] for name in names}
    anchors = {a.anchor_id: a for a in record.anchors}
    if any(anchors[key].source.region != "body" for key in anchor_ids(record, group, value)):
        for name in plan:
            if name != "required_text_recall":
                plan[name].append("ANCILLARY_LOCATOR_UNSUPPORTED_BY_FROZEN_SCORER")
    if group == "cells" and value.check_display:
        plan["displayed_values"] = ["DISPLAY_VALUES_UNSUPPORTED_BY_FROZEN_SCORER"]
    return plan


def qualify(
    records: tuple[FidelityRecord, ...],
    population: list[dict],
    historical: dict,
    technical: dict,
    reserved_sha256: set[str],
    *,
    expected: Population = FROZEN_POPULATION,
    allow_synthetic: bool = False,
) -> dict:
    """Reconcile all identities before assigning any eligibility; retain every row."""
    synthetic = all(record.dataset_kind == "synthetic" for record in records)
    if (
        not records
        or synthetic != allow_synthetic
        or len({r.dataset_kind for r in records}) != 1
        or len({r.document_id for r in records}) != len(records)
        or (not synthetic and expected != FROZEN_POPULATION)
    ):
        raise ValueError("real frozen population or explicit synthetic fixture required")
    by_assertion = assertions(records)
    if len(records) != expected.documents or len(by_assertion) != expected.assertions:
        raise ValueError("historical Gold denominator mismatch")
    saved = indexed(historical["assertions"], "assertion_id")
    evidence = indexed(technical["items"], "assertion_id")
    rows = indexed(population, "id")
    if set(saved) != set(by_assertion) or historical["records"] != len(records):
        raise ValueError("historical assertion omission or foreign identity")
    prior = {key for key, row in saved.items() if row["needs_review"] is True}
    if (
        set(evidence) != prior
        or len(prior) != expected.previous_issues
        or technical["input_assertions"] != expected.previous_issues
        or sum(row["technical_source_resolved"] is True for row in evidence.values())
        != expected.technically_resolved
    ):
        raise ValueError("previous issue/source evidence reconciliation mismatch")
    components = family_map(population)
    if not reserved_sha256 or not reserved_sha256 <= {r["sha256"] for r in population}:
        raise ValueError("reserved QA source binding required")
    reserved = {
        components[row["id"]]
        for row in population
        if row["sha256"] in reserved_sha256
        or row.get("reserved_qa_family") is not False
        or row["split"] != "dev"
    }
    output = []
    for key, (record, group, value) in sorted(by_assertion.items()):
        source = rows[record.document_id]
        reference = source["source_reference"]
        if (
            source["sha256"],
            reference["sha256"],
            reference["size_bytes"],
            reference["format"],
        ) != (
            record.source_sha256,
            record.source_sha256,
            record.source_size_bytes,
            record.document_format,
        ) or source.get("independent_gold") is not False:
            raise ValueError("Gold/source binding or independent review claim rejected")
        old = saved[key]
        if (
            old["source_id"] != record.document_id
            or old["source_sha256"] != record.source_sha256
            or old["group"] != group
            or old["assertion"] != value.model_dump(mode="json")
            or type(old["needs_review"]) is not bool
            or old["reviewer"] is not None
        ):
            raise ValueError("saved assertion payload/source/review mismatch")
        item = evidence.get(key)
        if item is not None and (
            item["source_id"] != record.document_id
            or item["source_sha256"] != record.source_sha256
            or item["source_reference"] != reference
            or item["group"] != group
            or item["assertion"] != old["assertion"]
            or item["original_verified"] is not True
            or item["human_reviewed"] is not False
            or item["independent_gold"] is not False
            or item["reviewer"] is not None
            or item["tier"] != "SOURCE_NATIVE_DIAGNOSTIC"
            or item["method"] != "readiness-source-checks-1.0"
            or item["source_state"] not in RESOLVED | UNRESOLVED
            or (item["technical_source_resolved"] and group != "anchors")
            or type(item["technical_source_resolved"]) is not bool
            or item["technical_source_resolved"] != (item["source_state"] in RESOLVED)
            or not item["source_evidence"]
        ):
            raise ValueError("technical source binding or fabricated review rejected")
        reasons, state = [], ELIGIBLE
        permission = source["rights"].get("local_evaluation")
        if permission is not True:
            reasons.append(
                "LOCAL_EVALUATION_DENIED" if permission is False else "LOCAL_EVALUATION_UNRESOLVED"
            )
            state = EXCLUDED
        if components[record.document_id] in reserved:
            reasons.append("RESERVED_QA_OR_NON_DEV_CONNECTED_FAMILY")
            state = EXCLUDED
        if item is not None and not item["technical_source_resolved"]:
            reasons.extend(["KNOWN_SOURCE_ISSUE_UNRESOLVED", item["source_state"]])
            if state != EXCLUDED:
                state = REVIEW
        else:
            reasons.append(
                "TECHNICAL_SOURCE_LITERAL_SUPPORTED"
                if item
                else "HISTORICAL_ATTESTATION_ONLY_NOT_SOURCE_REINSPECTED"
            )
        dependencies = []
        anchors = {a.anchor_id: (i, a) for i, a in enumerate(record.anchors)}
        for anchor in anchor_ids(record, group, value):
            index, _ = anchors[anchor]
            anchor_key = f"{record.document_id}/anchors/{index}"
            dependencies.append(anchor_key)
            linked = evidence.get(anchor_key)
            if linked and not linked["technical_source_resolved"]:
                if state != EXCLUDED:
                    state = REVIEW
                reasons.append("ANCHOR_DEPENDENCY_SOURCE_UNRESOLVED")
        metrics = {}
        for name, unsupported in metric_plan(record, group, value).items():
            metric_state = EXCLUDED if unsupported else state
            metric_reasons = list(unsupported)
            if (
                item
                and item["technical_source_resolved"]
                and name == "provenance"
                and record.document_format == "pdf"
                and value.source.table_index is not None
            ):
                metric_reasons.append("LOGICAL_GRID_MAPPING_NOT_TECHNICALLY_CONFIRMED")
                if metric_state != EXCLUDED:
                    metric_state = REVIEW
            metrics[name] = {
                "eligibility": metric_state,
                "supported": not unsupported,
                "reason_codes": metric_reasons,
            }
        if state == ELIGIBLE and not any(m["eligibility"] == ELIGIBLE for m in metrics.values()):
            state = (
                REVIEW if any(m["eligibility"] == REVIEW for m in metrics.values()) else EXCLUDED
            )
            reasons.append("NO_ELIGIBLE_SUPPORTED_METRIC")
        output.append(
            {
                "assertion_id": key,
                "source_id": record.document_id,
                "assertion_sha256": fingerprint(value.model_dump(mode="json")),
                "format": record.document_format,
                "group": group,
                "source_sha256": record.source_sha256,
                "source_reference": reference,
                "original_integrity": "VERIFIED_AT_BUILD",
                "rights": {
                    "local_evaluation": permission,
                    "new_annotation": source["rights"].get("new_annotation"),
                    "annotation_use_at_technical_capture": item["annotation_rights"]
                    if item
                    else None,
                    "basis": copy.deepcopy(source["rights"]),
                    "scope": "existing_project_historical_labels_local_dev_only",
                },
                "split_family": {
                    "split": source["split"],
                    "declared_family": source["family"],
                    "component": components[record.document_id],
                    "family_completeness": "NOT_EVALUATED",
                },
                "historical_review": {
                    "status": record.review_status,
                    "basis": record.review_basis,
                    "reviewer_count": record.reviewer_count,
                    "reviewed_on": record.reviewed_on.isoformat(),
                    "identity_authenticated": False,
                    "tier": "HISTORICAL_ATTESTATION",
                },
                "technical_support": {
                    "state": item["source_state"] if item else "NOT_REINSPECTED",
                    "technically_resolved": item["technical_source_resolved"] if item else None,
                    "evidence_sha256": fingerprint(item) if item else None,
                    "limitations": item["confidence_limitations"]
                    if item
                    else ["historical_attestation_only"],
                    "locator_correction_proposed": bool(item and item["correction"]),
                    "correction_applied_to_gold": False,
                },
                "parser_agreement": {
                    "classification": old["classification"],
                    "previous_issue": old["needs_review"],
                    "metrics": old["metrics"],
                    "capture": old["capture"],
                    "capture_sha256": old["capture_sha256"],
                    "role": "saved_diagnostic_not_source_truth_or_eligibility_test",
                },
                "independent_review": {
                    "status": "NOT_EVALUATED",
                    "reviewer": None,
                    "independent_gold": False,
                },
                "eligibility": state,
                "reason_codes": sorted(set(reasons)),
                "metrics": metrics,
                "anchor_dependencies": dependencies,
            }
        )
    return {
        "version": VERSION,
        "scope": "LOCAL_DEV_DIAGNOSTIC_ONLY",
        "dataset_kind": "synthetic" if synthetic else "real",
        "population_contract": asdict(expected),
        "assertions": output,
        "independent_gold": False,
        "QG-00": "NOT_EVALUATED",
        "QG-01": "NOT_EVALUATED",
    }


def summarize(ledger: dict) -> dict:
    rows = ledger["assertions"]

    def counts(selected):
        return {
            "assertions": len(selected),
            **{
                s: sum(r["eligibility"] == s for r in selected)
                for s in (ELIGIBLE, REVIEW, EXCLUDED)
            },
        }

    metrics = {}
    for name in METRICS:
        selected = [r["metrics"][name] for r in rows if name in r["metrics"]]
        metrics[name] = {
            "requested": len(selected),
            "unsupported": sum(not m["supported"] for m in selected),
            **{
                s: sum(m["eligibility"] == s for m in selected)
                for s in (ELIGIBLE, REVIEW, EXCLUDED)
            },
        }
    return {
        "version": VERSION,
        "scope": ledger["scope"],
        "documents": len({r["source_id"] for r in rows}),
        **counts(rows),
        "formats": {
            fmt: counts([r for r in rows if r["format"] == fmt]) for fmt in ("pdf", "docx", "xlsx")
        },
        "groups": {g: counts([r for r in rows if r["group"] == g]) for g in GROUPS},
        "previous_issues": sum(r["parser_agreement"]["previous_issue"] for r in rows),
        "technical_resolved": sum(
            r["technical_support"]["technically_resolved"] is True for r in rows
        ),
        "technical_unresolved": sum(
            r["technical_support"]["technically_resolved"] is False for r in rows
        ),
        "not_source_reinspected": sum(
            r["technical_support"]["technically_resolved"] is None for r in rows
        ),
        "reason_counts_overlapping": dict(
            sorted(Counter(c for r in rows for c in r["reason_codes"]).items())
        ),
        "metric_denominators": metrics,
        "new_human_reviews": 0,
        "independent_gold": "NOT_EVALUATED",
        "QG-00": "NOT_EVALUATED",
        "QG-01": "NOT_EVALUATED",
        "source_integrity": "VERIFIED",
        "family_completeness": "NOT_EVALUATED",
        "comparison_run": False,
        "quality_scores": None,
    }


def reconstruct(release_root: Path) -> dict:
    proof = release.verify(release_root)
    paths = [
        ROOT / MANIFEST,
        ROOT / release.GOLD,
        ROOT / release.ISOLATION,
        release_root / "RELEASE.json",
        release_root / "effective-matrix.json",
        release_root / "incremental-ledger.json",
        release_root / "historical-assertions-v2.json",
    ]
    before = {p.relative_to(ROOT).as_posix(): corpus.sha256(p) for p in paths}
    sources = _read_sources(ROOT / MANIFEST)
    raw = verify_corpus(ROOT / "local-corpus", sources, ExtractionLimits())
    records = load_gold(ROOT / release.GOLD, sources)
    population = corpus.read_json(release_root / "effective-matrix.json")["population"]
    historical = corpus.read_json(release_root / "incremental-ledger.json", max_bytes=64 * 1024**2)[
        "historical_assertions"
    ]
    technical = corpus.read_json(release_root / "historical-assertions-v2.json")
    for row in historical["assertions"]:
        capture = confined(ROOT, row["capture"])
        if corpus.sha256(capture) != row["capture_sha256"]:
            raise ValueError("saved diagnostic capture drift")
        before[row["capture"]] = row["capture_sha256"]
    for row in population:
        corpus.asset_path(ROOT, corpus.Asset.model_validate(row["source_reference"]))
    ledger = qualify(
        records,
        population,
        historical,
        technical,
        set(corpus.read_json(ROOT / release.ISOLATION)["reserved_source_sha256"]),
    )
    before.update({p.relative_to(ROOT).as_posix(): sources[key][0] for key, p in raw.items()})
    if any(corpus.sha256(confined(ROOT, path)) != digest for path, digest in before.items()):
        raise ValueError("protected input changed during qualification")
    code = {
        path: corpus.sha256(ROOT / path)
        for path in (
            "tools/extraction_quality/historical_gold_eligibility.py",
            "tools/extraction_quality/blind_review_batch.py",
            "tools/extraction_quality/readiness_release.py",
            "tools/extraction_quality/readiness_io.py",
            "src/doclens_ai/eda/corpus_v2.py",
            "src/doclens_ai/extraction/fidelity_gold.py",
            "src/doclens_ai/extraction/fidelity_eval.py",
        )
    }
    ledger["binding"] = {
        "release_root": release_root.relative_to(ROOT).as_posix(),
        "release_fingerprint": proof["fingerprint"],
        "gold_fingerprint": fingerprint([r.model_dump(mode="json") for r in records]),
        "input_sha256": before,
        "code_sha256": code,
    }
    ledger["fingerprint"] = fingerprint(ledger)
    return ledger


def build(output: Path, release_root: Path) -> dict:
    corpus.no_links(output)
    if output.exists() or not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("fresh private output required")
    ledger = reconstruct(release_root)
    summary = {**summarize(ledger), "ledger_fingerprint": ledger["fingerprint"]}
    output.mkdir(parents=True)
    atomic(output / "eligibility.json", ledger)
    atomic(output / "summary.json", summary)
    atomic(
        output / "COMPLETE.json",
        {name: corpus.sha256(output / name) for name in ("eligibility.json", "summary.json")},
    )
    return summary


def verify(output: Path) -> dict:
    corpus.no_links(output)
    if not output.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("private output required")
    files = set()
    for path in output.rglob("*"):
        corpus.no_links(path)
        if path.is_file():
            files.add(path.relative_to(output).as_posix())
    if files != {"eligibility.json", "summary.json", "COMPLETE.json"}:
        raise ValueError("eligibility artifact inventory mismatch")
    marker = corpus.read_json(output / "COMPLETE.json")
    if marker != {
        name: corpus.sha256(output / name) for name in ("eligibility.json", "summary.json")
    }:
        raise ValueError("eligibility artifact drift")
    ledger = corpus.read_json(output / "eligibility.json")
    expected = reconstruct(confined(ROOT, ledger["binding"]["release_root"]))
    if ledger != expected or corpus.read_json(output / "summary.json") != {
        **summarize(expected),
        "ledger_fingerprint": expected["fingerprint"],
    }:
        raise ValueError("eligibility/source/review reconstruction mismatch")
    return {"status": "PASS", "ledger_fingerprint": ledger["fingerprint"], **summarize(ledger)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release", type=Path, default=Path(DEFAULT_RELEASE))
    args = parser.parse_args()
    try:
        result = (
            build(args.output.resolve(), args.release.resolve())
            if args.mode == "build"
            else verify(args.output.resolve())
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print(
            json.dumps({"status": "BLOCKED", "reason": "historical_eligibility_validation_failed"})
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
