"""Freeze existing source-checked fields for local dev; never independent Gold.

No proposal generation or extraction comparison is performed. Reproduction needs
the existing private accepted package, rights evidence, geometry plan and QA Gold.
"""

from __future__ import annotations

import argparse
import copy
import csv
import importlib.metadata
import json
import os
import shutil
import stat
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.evaluation.gold import load_gold_jsonl
from doclens_ai.evaluation.rag_gold import load_rag_gold
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import dataset_readiness as isolation
from tools.extraction_quality import pdf_assisted_review as assisted
from tools.extraction_quality import pdf_table_review_packet as packet

ROOT = Path(__file__).resolve().parents[2]
VERSION = "pdf-dev-reference-1.0"
PACKAGE_MANIFEST_SHA256 = "9795da962c25dca20144de7e252143bc0ce1b0911dd2ceedbec9012ccb0659cc"
UNRESOLVED = (
    "semantic_roles",
    "header_and_period_relationships",
    "semantic_reading_order",
    "exact_border_fidelity",
    "ambiguous_and_unruled_boundaries",
    "currency_code_interpretation",
    "language_review",
    "family_completeness",
    "reviewer_independence",
)
ADMITTED = {"cell", "text_anchor", "printed_unit", "table"}


@dataclass(frozen=True)
class Counts:
    proposal_ids: int = 1154
    cell_texts: int = 536
    text_anchors: int = 62
    printed_symbols: int = 115
    logical_grid_occupancies: int = 6

    def to_dict(self) -> dict:
        return vars(self).copy()


COUNTS = Counts()


def validate_confirmation(value: dict, expected: Counts = COUNTS) -> None:
    fields = {
        "confirmation_source",
        "confirmed_on",
        "scope",
        "report_level_confirmed",
        "report_artifact_identity",
        "reviewer_id",
        "per_item_decisions_supplied",
        "independent_review",
        "reported_counts",
        "unresolved_dimensions",
    }
    if (
        set(value) != fields
        or value["confirmation_source"] != "explicit_user_message"
        or value["scope"] != "source_comparison_report_only"
        or value["report_level_confirmed"] is not True
        or value["reviewer_id"] is not None
        or value["per_item_decisions_supplied"] is not False
        or value["independent_review"] is not False
        or value["reported_counts"] != expected.to_dict()
        or value["unresolved_dimensions"] != list(UNRESOLVED)
        or value["report_artifact_identity"] != "NOT_SEPARATELY_SUPPLIED"
    ):
        raise ValueError("Report confirmation scope rejected")
    date.fromisoformat(value["confirmed_on"])


def validate_decisions(path: Path, proposals: dict) -> None:
    """Bind all original columns and reject invented per-item approval/corrections."""
    assisted.load_decisions(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != assisted.FIELDS:
            raise ValueError("Decision CSV fields rejected")
        rows = list(reader)
    expected = {i["item_id"]: assisted.csv_row(i) for i in proposals["items"]}
    if len(rows) != len(expected) or {r["item_id"] for r in rows} != set(expected):
        raise ValueError("Decision CSV population rejected")
    for row in rows:
        target = {k: "" if v is None else str(v) for k, v in expected[row["item_id"]].items()}
        if row != target:
            raise ValueError("Decision identity or per-item approval rejected")


def project(proposals: dict, confirmation: dict, expected: Counts = COUNTS) -> tuple[dict, list]:
    """Copy a field whitelist, preserving every original proposal as unresolved context."""
    validate_confirmation(confirmation, expected)
    assisted.validate_items(proposals["documents"], proposals["items"])
    if proposals["approved"] is not None or proposals["human_review_completed"] is not False:
        raise ValueError("Machine package review status rejected")
    counts = Counter(i["kind"] for i in proposals["items"])
    actual = Counts(
        len(proposals["items"]),
        counts["cell"],
        counts["text_anchor"],
        counts["printed_unit"],
        counts["table"],
    )
    if actual != expected:
        raise ValueError("Reference population mismatch")
    items = {i["item_id"]: i for i in proposals["items"]}
    documents = []
    for doc in proposals["documents"]:
        anchor_items = [
            i
            for i in proposals["items"]
            if i["source_id"] == doc["document_id"] and i["kind"] == "text_anchor"
        ]
        if [i["proposed_value"] for i in anchor_items] != doc["text_anchors"]:
            raise ValueError("Anchor/item binding rejected")
        cells, anchors, symbols, grids = [], [], [], []
        for table in doc["tables"]:
            cell_ids, occupied = [], set()
            for cell in table["cells"]:
                item = items[cell["item_id"]]
                if (
                    item["kind"] != "cell"
                    or item["source_id"] != doc["document_id"]
                    or item["table_id"] != table["table_id"]
                    or item["proposed_text"] != cell["literal_text"]
                    or item["bbox"] != cell["bbox_pdf_user_space_points"]
                    or any(item[k] != cell[k] for k in ("row", "column", "row_span", "column_span"))
                ):
                    raise ValueError("Literal/item binding rejected")
                slots = {
                    (r, c)
                    for r in range(cell["row"], cell["row"] + cell["row_span"])
                    for c in range(cell["column"], cell["column"] + cell["column_span"])
                }
                if not slots or occupied & slots:
                    raise ValueError("Grid occupancy rejected")
                occupied |= slots
                cell_ids.append(cell["item_id"])
                cells.append(
                    {
                        "item_id": cell["item_id"],
                        "table_id": table["table_id"],
                        "literal_text": cell["literal_text"],
                        "logical_grid_assignment": {
                            k: cell[k] for k in ("row", "column", "row_span", "column_span")
                        },
                        "locator_context": {
                            "page": 1,
                            "proposed_bbox": cell["bbox_pdf_user_space_points"],
                            "exact_border_fidelity": "UNRESOLVED",
                        },
                        "source_text_evidence": {
                            k: copy.deepcopy(cell[k])
                            for k in (
                                "text_engine",
                                "text_status",
                                "source_glyph_indices",
                                "alternate_text",
                                "uncertainty",
                            )
                        },
                        "boundary_context": {
                            "physical_boundary_objects": cell["physical_boundary_objects"],
                            "segmentation_evidence": cell.get("segmentation_evidence"),
                            "boundary_status": cell.get("boundary_status"),
                            "semantic_interpretation": None,
                        },
                    }
                )
            if occupied != {
                (r, c) for r in range(table["row_count"]) for c in range(table["column_count"])
            }:
                raise ValueError("Incomplete grid occupancy")
            grids.append(
                {
                    "table_id": table["table_id"],
                    "row_count": table["row_count"],
                    "column_count": table["column_count"],
                    "cell_ids": cell_ids,
                    "logical_slot_coverage_complete": True,
                    "physical_table_completeness": "NOT_EVALUATED",
                    "proposed_bbox_context": table["bbox"],
                }
            )
        for item in proposals["items"]:
            if item["source_id"] != doc["document_id"]:
                continue
            value = item["proposed_value"]
            if item["kind"] == "text_anchor":
                anchors.append(
                    {
                        "item_id": item["item_id"],
                        "literal_text": value["literal_text"],
                        "locator_context": {
                            k: value[k]
                            for k in (
                                "bbox",
                                "character_range",
                                "source_glyph_indices",
                                "generated_separator_indices",
                            )
                        },
                        "uncertainty": item["uncertainty"],
                    }
                )
            elif item["kind"] == "printed_unit":
                if value["printed_symbol"] != "£" or value["currency_code"] is not None:
                    raise ValueError("Unverified symbol/currency interpretation")
                symbols.append(
                    {
                        "item_id": item["item_id"],
                        "cell_id": value["cell_id"],
                        "printed_symbol": value["printed_symbol"],
                        "currency_code": None,
                        "uncertainty": item["uncertainty"],
                    }
                )
        documents.append(
            {
                "document_id": doc["document_id"],
                "source_sha256": doc["sha256"],
                "source_size_bytes": doc["size_bytes"],
                "pages": doc["pages"],
                "coordinate_basis": doc["coordinate_basis"],
                "cells": cells,
                "text_anchors": anchors,
                "printed_symbols": symbols,
                "logical_grids": grids,
            }
        )
    if (
        sum(len(d["cells"]) for d in documents) != expected.cell_texts
        or sum(len(d["text_anchors"]) for d in documents) != expected.text_anchors
        or sum(len(d["printed_symbols"]) for d in documents) != expected.printed_symbols
        or sum(len(d["logical_grids"]) for d in documents) != expected.logical_grid_occupancies
    ):
        raise ValueError("Projected field population mismatch")
    inventory = [
        {
            "item_id": i["item_id"],
            "source_id": i["source_id"],
            "field_admission": "PARTIAL_DEV_FIELDS" if i["kind"] in ADMITTED else "UNRESOLVED",
            "per_item_human_decision": None,
            "original_proposal": copy.deepcopy(i),
        }
        for i in proposals["items"]
    ]
    reference = {
        "schema_version": VERSION,
        "revision": "pdf-dev-reference-20261022-v1",
        "evidence_class": "AI_ASSISTED_SOURCE_CHECKED_DEV_REFERENCE",
        "split": "dev",
        "independent_gold": False,
        "sealed_test": False,
        "per_item_human_approval": False,
        "qg_00": "NOT_EVALUATED",
        "qg_01": "NOT_EVALUATED",
        "unresolved_dimensions": list(UNRESOLVED),
        "counts": actual.to_dict(),
        "documents": documents,
        "proposal_inventory_fingerprint": fingerprint(inventory),
        "report_confirmation_fingerprint": fingerprint(confirmation),
    }
    return reference, inventory


def verify_package(package: Path, manifest_sha256: str = PACKAGE_MANIFEST_SHA256) -> dict:
    for path in package.rglob("*"):
        corpus.no_links(path)
    manifest = corpus.read_json(package / "artifact-manifest.json")
    complete = corpus.read_json(package / "COMPLETE.json")
    if corpus.sha256(package / "artifact-manifest.json") != manifest_sha256:
        raise ValueError("Accepted manifest pin drift")
    if complete["manifest_sha256"] != corpus.sha256(package / "artifact-manifest.json") or complete[
        "artifact_fingerprint"
    ] != fingerprint(manifest):
        raise ValueError("Accepted package manifest rejected")
    verified = corpus.read_json(package / "VERIFIED.json")["files"]
    names = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file()}
    if names != set(verified) | {"VERIFIED.json"}:
        raise ValueError("Accepted file population drift")
    for name, digest in list(manifest.items()) + list(verified.items()):
        target = package / name
        corpus.no_links(target)
        if (
            not target.resolve().is_relative_to(package.resolve())
            or corpus.sha256(target) != digest
        ):
            raise ValueError("Accepted package drift")
    proposals = corpus.read_json(package / "proposals.json")
    validate_decisions(package / "review_decisions.csv", proposals)
    for doc in proposals["documents"]:
        source = package / "sources" / (doc["document_id"] + ".pdf")
        if corpus.sha256(source) != doc["sha256"] or source.stat().st_size != doc["size_bytes"]:
            raise ValueError("Source drift")
    return proposals


def context(args, proposals: dict) -> dict:
    identity, sources, records, _ = packet.preflight(
        args.manifest, args.corpus, args.gold, packet.Expected(), eligibility=args.eligibility
    )
    selected = {r.document_id for r in records}
    if selected != {"c1-0033", "c1-0040"} or selected != {
        d["document_id"] for d in proposals["documents"]
    }:
        raise ValueError("Authorized source population mismatch")
    recipes = assisted.load_plan(args.plan, args.plan_sha256, selected)
    checks = {}
    for doc in proposals["documents"]:
        checks[doc["document_id"]] = assisted.validate_document(
            doc, sources[doc["document_id"]], recipes[doc["document_id"]]
        )
        if checks[doc["document_id"]]["unassigned_glyph_diagnostics"]:
            raise ValueError("Unresolved source glyph coverage")
        if doc["text_anchors"] != assisted.anchors(doc["observations"]):
            raise ValueError("Source anchor text/locator mismatch")
    reference = corpus.load(args.reference_manifest)
    candidates = corpus.load(args.office_manifest)
    isolation.validate_reference(reference, args.manifest)
    retrieval = load_gold_jsonl(args.retrieval_gold, corpus_manifest_path=args.manifest)
    answers = load_rag_gold(args.answer_gold, manifest_path=args.manifest)
    guarded = isolation.isolation_report(
        reference, candidates, isolation.held_out_sources(retrieval, answers)
    )
    selected_samples = {s.sample_id for s in reference.samples if s.source_record_id in selected}
    if (
        len(selected_samples) != 2
        or isolation.selection(guarded, selected_samples)["status"] != "PASS"
    ):
        raise ValueError("Reserved test-family overlap")
    input_paths = [
        args.manifest,
        args.gold,
        args.eligibility,
        args.plan,
        args.reference_manifest,
        args.office_manifest,
        args.retrieval_gold,
        args.answer_gold,
        args.confirmation,
    ]
    package_hashes = {
        p.relative_to(args.package).as_posix(): corpus.sha256(p)
        for p in sorted(args.package.rglob("*"))
        if p.is_file()
    }
    return {
        "machine_checks": checks,
        "machine_scope": "source_consistency_not_semantic_or_human_review",
        "eligibility": identity["eligibility"],
        "selected_sample_ids": sorted(selected_samples),
        "test_family_isolation": "PASS",
        "reserved_test_sources": guarded["reserved_source_sha256"],
        "gold_fingerprints": {"retrieval": retrieval.fingerprint, "answer": answers.fingerprint},
        "input_sha256": {str(p): corpus.sha256(p) for p in input_paths},
        "accepted_package_sha256": package_hashes,
        "validator_sha256": corpus.sha256(Path(__file__)),
        "validation_code_sha256": {
            str(Path(module.__file__).relative_to(ROOT)): corpus.sha256(Path(module.__file__))
            for module in (
                assisted,
                packet,
                corpus,
                isolation,
                assisted.recovery,
                assisted.review,
                assisted.grids,
            )
        },
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("pypdf", "pdfplumber", "pypdfium2", "Pillow", "pydantic")
        },
    }


def validate_payload(
    actual: dict, proposals: dict, confirmation: dict, counts: Counts = COUNTS
) -> None:
    expected, _ = project(proposals, confirmation, counts)
    if fingerprint(actual) != fingerprint(expected):
        raise ValueError("Reference fields or promotion rejected")


def validate_snapshot(folder: Path, args) -> dict:
    complete = corpus.read_json(folder / "COMPLETE.json")
    manifest = corpus.read_json(folder / "artifact-manifest.json")
    names = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if names != set(manifest) | {"artifact-manifest.json", "COMPLETE.json"}:
        raise ValueError("Snapshot file population rejected")
    if complete["manifest_sha256"] != corpus.sha256(folder / "artifact-manifest.json"):
        raise ValueError("Snapshot manifest drift")
    for name, digest in manifest.items():
        target = folder / name
        corpus.no_links(target)
        if not target.resolve().is_relative_to(folder.resolve()) or corpus.sha256(target) != digest:
            raise ValueError("Snapshot/source drift")
    proposals = verify_package(args.package)
    confirmation = corpus.read_json(folder / "user-report-confirmation.json")
    if confirmation != corpus.read_json(args.confirmation):
        raise ValueError("User report confirmation drift")
    validate_payload(corpus.read_json(folder / "reference.json"), proposals, confirmation)
    expected, inventory = project(proposals, confirmation)
    if fingerprint(corpus.read_json(folder / "proposal-inventory.json")) != fingerprint(inventory):
        raise ValueError("Proposal inventory drift")
    proof = context(args, proposals)
    if fingerprint(corpus.read_json(folder / "verification-context.json")) != fingerprint(proof):
        raise ValueError("Verification context drift")
    for doc in expected["documents"]:
        if (
            corpus.sha256(folder / "sources" / (doc["document_id"] + ".pdf"))
            != doc["source_sha256"]
        ):
            raise ValueError("Snapshot source drift")
    value = fingerprint(
        {
            "reference": expected,
            "confirmation": confirmation,
            "inventory": inventory,
            "verification_context": proof,
        }
    )
    if value != complete["snapshot_fingerprint"]:
        raise ValueError("Snapshot fingerprint rejected")
    return {
        "execution": "PASS",
        "snapshot_fingerprint": value,
        "counts": expected["counts"],
        "independent_gold": False,
        "qg_00": "NOT_EVALUATED",
        "qg_01": "NOT_EVALUATED",
    }


def freeze(folder: Path, args) -> dict:
    packet.fresh_output(folder, args.corpus, root=ROOT)
    if not folder.resolve().is_relative_to(
        ROOT / "local-evaluation"
    ) and not folder.resolve().is_relative_to(ROOT / "evaluation-output"):
        raise ValueError("Private output required")
    proposals = verify_package(args.package)
    confirmation = corpus.read_json(args.confirmation)
    reference, inventory = project(proposals, confirmation)
    proof = context(args, proposals)
    value = fingerprint(
        {
            "reference": reference,
            "confirmation": confirmation,
            "inventory": inventory,
            "verification_context": proof,
        }
    )
    folder.mkdir()
    (folder / "sources").mkdir()
    for name, data in {
        "reference.json": reference,
        "proposal-inventory.json": inventory,
        "user-report-confirmation.json": confirmation,
        "verification-context.json": proof,
    }.items():
        packet.write_json(folder / name, data)
    for doc in reference["documents"]:
        shutil.copyfile(
            args.package / "sources" / (doc["document_id"] + ".pdf"),
            folder / "sources" / (doc["document_id"] + ".pdf"),
        )
    (folder / "README.md").write_text(
        f"# Development-only PDF literal reference v1\n\nFingerprint: `{value}`\n\n"
        "AI-assisted; user confirmation covers the source-comparison report only.\n"
        "No per-item human decisions, reviewer identity or blind-review attestations.\n"
        "536 cell literals, 62 anchors, 115 printed symbols and 6 logical grid occupancies.\n"
        "All 1,154 proposal IDs are retained; semantic proposals remain unresolved context.\n"
        "719 items contribute limited dev fields; 435 contribute only unresolved context.\n"
        "Coordinates are proposed locator context, not confirmed exact borders.\n"
        "Currency code, semantic roles/links/order, ambiguous borders, family completeness\n"
        "and independence remain unresolved. This is neither independent Gold nor sealed test.\n"
        "QG-00/QG-01: NOT_EVALUATED. No parser comparison performed.\n\n"
        "Revalidation requires the original accepted package, rights/geometry-plan evidence\n"
        "and unchanged manifest/QA Gold pins in verification-context.json, plus this validator.\n"
        "Files are read-only to prevent accidental edits; content fingerprints detect drift.\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        p.relative_to(folder).as_posix(): corpus.sha256(p)
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }
    packet.write_json(folder / "artifact-manifest.json", manifest)
    packet.write_json(
        folder / "COMPLETE.json",
        {
            "snapshot_fingerprint": value,
            "manifest_sha256": corpus.sha256(folder / "artifact-manifest.json"),
        },
    )
    result = validate_snapshot(folder, args)
    for path in folder.rglob("*"):
        if path.is_file():
            os.chmod(path, stat.S_IREAD)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "validate"))
    for name in (
        "package",
        "manifest",
        "corpus",
        "gold",
        "eligibility",
        "plan",
        "reference-manifest",
        "office-manifest",
        "retrieval-gold",
        "answer-gold",
        "snapshot",
        "confirmation",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args()
    try:
        result = (
            freeze(args.snapshot, args)
            if args.mode == "freeze"
            else validate_snapshot(args.snapshot, args)
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print("BLOCKED: dev reference inputs, decisions, fields or promotion rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
