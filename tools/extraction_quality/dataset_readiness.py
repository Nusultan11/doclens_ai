"""Metadata-only dev admission against existing QA test families; never parse RAW.

Source-manifest native eligibility is intentionally separate: exposed regression
controls remain measurable, while a combined dev selection must reserve test families.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from doclens_ai.eda import corpus_v2 as v2
from doclens_ai.evaluation.gold import GoldDataset, load_gold_jsonl
from doclens_ai.evaluation.rag_gold import RagGoldDataset, load_rag_gold
from doclens_ai.extraction.fidelity_eval import _read_sources
from doclens_ai.extraction.fidelity_gold import fingerprint

ROOT = Path(__file__).resolve().parents[2]


def isolation_report(
    reference: v2.Corpus, candidates: v2.Corpus, held_out_sha256: frozenset[str]
) -> dict:
    """Retain the complete population and exclude connected test-source families.

    Eligibility here concerns declared dev isolation and existing local-use scope
    only. It never attests human family completeness or independent Gold readiness.
    """
    samples = reference.samples + candidates.samples
    if len({s.sample_id for s in samples}) != len(samples):
        raise ValueError("Duplicate sample identity")
    known = {s.original.sha256 for s in samples if s.original}
    if not held_out_sha256 or not held_out_sha256 <= known:
        raise ValueError("Held-out source binding required")
    components = v2.family_components(samples)
    reserved = {
        components[s.sample_id]
        for s in samples
        if s.original and s.original.sha256 in held_out_sha256
    }
    rows = []
    candidate_ids = {s.sample_id for s in candidates.samples}
    for sample in sorted(samples, key=lambda s: s.sample_id):
        reasons = []
        if components[sample.sample_id] in reserved:
            reasons.append("held_out_test_family")
        if sample.split != "dev":
            reasons.append("not_dev")
        if sample.disposition != "admitted":
            reasons.append("not_admitted")
        if sample.original is None:
            reasons.append("original_unavailable")
        if sample.rights.local_evaluation is not True:
            reasons.append("local_evaluation_unresolved")
        rows.append(
            {
                "sample_id": sample.sample_id,
                "source_sha256": sample.original.sha256 if sample.original else None,
                "family_id": sample.family_id,
                "component": components[sample.sample_id],
                "candidate": sample.sample_id in candidate_ids,
                "development_eligible_against_test_families": not reasons,
                "exclusion_reasons": reasons,
            }
        )
    eligible = [r["sample_id"] for r in rows if r["development_eligible_against_test_families"]]
    excluded = [r["sample_id"] for r in rows if not r["development_eligible_against_test_families"]]
    return {
        "version": "dataset-dev-isolation-v1",
        "scope": "declared_family_isolation_not_independent_review_or_source_integrity",
        "reference_fingerprint": fingerprint(reference.model_dump(mode="json")),
        "candidate_fingerprint": fingerprint(candidates.model_dump(mode="json")),
        "reserved_source_sha256": sorted(held_out_sha256),
        "population": len(rows),
        "eligible_ids": eligible,
        "excluded_ids": excluded,
        "candidate_population": len(candidate_ids),
        "candidate_eligible": len(candidate_ids & set(eligible)),
        "candidate_excluded": len(candidate_ids & set(excluded)),
        "independent_gold": "NOT_EVALUATED",
        "rows": rows,
    }


def selection(report: dict, requested: set[str]) -> dict:
    """Reject the entire proposed selection if any member is unknown or excluded."""
    rejected = requested - set(report["eligible_ids"])
    return {
        "status": "BLOCKED" if rejected else "PASS",
        "requested": sorted(requested),
        "rejected": sorted(rejected),
    }


def held_out_sources(retrieval: GoldDataset, answers: RagGoldDataset) -> frozenset[str]:
    reserved = set()
    for example in retrieval.examples:
        if example.split == "test":
            reserved.add(example.source_document_sha256)
            reserved.update(a.document_sha256 for a in example.evidence)
    for example in answers.examples:
        if example.split == "test":
            reserved.update(example.source_document_sha256)
            reserved.update(a.document_sha256 for a in example.evidence)
    return frozenset(reserved)


def validate_reference(reference: v2.Corpus, manifest: Path) -> None:
    """Bind reference families to authoritative legacy SHA/size/format and source page."""
    sources = _read_sources(manifest)
    with manifest.open(encoding="utf-8", newline="") as stream:
        rows = {r["document_id"]: r for r in csv.DictReader(stream)}
    if len(reference.samples) != len(sources):
        raise ValueError("Reference population mismatch")
    identities = set()
    for sample in reference.samples:
        key = sample.source_record_id
        asset = sample.original
        if (
            key in identities
            or key not in sources
            or asset is None
            or (asset.sha256, asset.size_bytes, asset.format) != sources[key]
            or sample.family_id != "f-" + fingerprint(rows[key]["source_page_url"])[:24]
        ):
            raise ValueError("Reference source/family mismatch")
        identities.add(key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "reference", "candidates", "retrieval-gold", "answer-gold", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--select-id", action="append", default=[])
    args = parser.parse_args()
    try:
        paths = (
            args.manifest,
            args.reference,
            args.candidates,
            args.retrieval_gold,
            args.answer_gold,
        )
        for path in paths:
            v2.no_links(path)
        if any(not re.fullmatch(r"e2-[a-z0-9-]{1,80}", key) for key in args.select_id):
            raise ValueError("Selection identity rejected")
        v2.no_links(args.output)
        if (
            args.output.exists()
            or not args.output.resolve().is_relative_to(ROOT / "evaluation-output")
            or not args.output.parent.is_dir()
        ):
            raise ValueError("Private fresh output required")
        before = {str(p): v2.sha256(p) for p in paths}
        reference, candidates = v2.load(args.reference), v2.load(args.candidates)
        validate_reference(reference, args.manifest)
        retrieval = load_gold_jsonl(args.retrieval_gold, corpus_manifest_path=args.manifest)
        answers = load_rag_gold(args.answer_gold, manifest_path=args.manifest)
        report = isolation_report(reference, candidates, held_out_sources(retrieval, answers))
        report["gold_fingerprints"] = {
            "retrieval": retrieval.fingerprint,
            "answer": answers.fingerprint,
        }
        report["selection"] = selection(report, set(args.select_id))
        report["inputs_sha256"] = before
        if before != {str(p): v2.sha256(p) for p in paths}:
            raise ValueError("Inputs changed during audit")
        report["fingerprint"] = fingerprint(report)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in (
                        "population",
                        "candidate_population",
                        "candidate_eligible",
                        "candidate_excluded",
                        "selection",
                    )
                }
            )
        )
        return 2 if report["selection"]["status"] == "BLOCKED" else 0
    except Exception:
        print("BLOCKED: dataset isolation inputs or selection rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
