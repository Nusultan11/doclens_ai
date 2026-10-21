"""Local-only independent review preparation; never extraction, scoring or Gold edits."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from doclens_ai.extraction.fidelity_eval import _read_sources, verify_corpus
from doclens_ai.extraction.fidelity_gold import FidelityRecord, fingerprint, load_gold
from doclens_ai.extraction.parsers import ExtractionLimits
from tools.docx_footnote_candidate.locator_review_packet import (
    ROOT,
    fresh_output,
    no_links,
    require_unoptimized,
    write_json,
)

VERSION = "pdf-table-independent-review-v1"
MAX_SECONDS = 60.0
MAX_PAGES = 100
CODE = (
    "tools/extraction_quality/pdf_table_review_packet.py",
    "tests/unit/test_pdf_table_review_packet.py",
    "src/doclens_ai/extraction/fidelity_gold.py",
    "src/doclens_ai/extraction/fidelity_eval.py",
    "tools/docx_footnote_candidate/locator_review_packet.py",
)
BLOCKERS = (
    "INDEPENDENT_REVIEW_PENDING",
    "VISUAL_REGION_MAPPING_MISSING",
    "CELL_SPANS_AND_RELATIONSHIPS_UNVERIFIED",
    "HEADER_VALUE_UNIT_PERIOD_ROLES_UNLABELLED",
    "REVIEWER_IDENTITY_AND_INDEPENDENCE_UNATTESTED",
    "FAMILY_SPLIT_AND_LANGUAGE_COVERAGE_UNATTESTED",
)


class PacketError(ValueError):
    """Fixed diagnostics only; never echo private validation inputs."""


def sha(path: Path) -> str:
    import hashlib

    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            value.update(chunk)
    return value.hexdigest()


@dataclass(frozen=True, slots=True)
class Expected:
    manifest_sha256: str = "c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0"
    gold_sha256: str = "f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf"
    documents: int = 90
    reviewed_records: int = 19
    table_documents: int = 5


def preflight(
    manifest: Path,
    corpus: Path,
    gold: Path,
    expected: Expected,
    *,
    allow_synthetic: bool = False,
    eligibility: Path | None = None,
) -> tuple[dict, dict[str, Path], tuple[FidelityRecord, ...], dict]:
    for path in (manifest, corpus, gold):
        no_links(path)
    if manifest.stat().st_size > 1024**2 or gold.stat().st_size > 20 * 1024**2:
        raise PacketError("Input bound exceeded")
    if sha(manifest) != expected.manifest_sha256 or sha(gold) != expected.gold_sha256:
        raise PacketError("Frozen identity mismatch")
    for path in corpus.rglob("*"):
        no_links(path)
    sources = _read_sources(manifest)
    paths = verify_corpus(corpus, sources, ExtractionLimits())
    records = load_gold(gold, sources, allow_synthetic=allow_synthetic)
    with manifest.open(encoding="utf-8", newline="") as stream:
        metadata = {row["document_id"]: row for row in csv.DictReader(stream)}
    if any(
        not row.get(key)
        for row in metadata.values()
        for key in ("license", "license_url", "license_basis_url")
    ):
        raise PacketError("Missing rights provenance")
    selected = tuple(
        r
        for r in records
        if r.document_format == "pdf" and (r.table_cells or r.table_relationships)
    )
    if (len(sources), len(records), len(selected)) != (
        expected.documents,
        expected.reviewed_records,
        expected.table_documents,
    ) or not selected:
        raise PacketError("Frozen population mismatch")
    identity = {
        "expected": asdict(expected),
        "source_map_fingerprint": fingerprint(sources),
        "gold_normalized_fingerprint": fingerprint([r.model_dump(mode="json") for r in records]),
        "selected_ids": [r.document_id for r in selected],
    }
    if eligibility is not None:
        from tools.extraction_quality.pdf_review_eligibility import validate

        if not allow_synthetic:
            totals = aggregate(selected, {r.document_id: 0 for r in selected})["totals"]
            if (totals["unresolved_assertions"], totals["legacy_source_regions"]) != (110, 19):
                raise PacketError("Frozen assertion population mismatch")
        selected, authorization = validate(eligibility, manifest, gold, selected, paths, metadata)
        identity.update(selected_ids=[r.document_id for r in selected], eligibility=authorization)
    return identity, paths, selected, metadata


def review_fields() -> dict:
    return {
        "state": "UNRESOLVED",
        "decision": None,
        "reviewer_id": None,
        "reviewed_on": None,
        "original_page_evidence": [],
        "rationale": None,
        "ambiguity": None,
        "proposed_correction": None,
        "adjudicator_id": None,
        "adjudicated_on": None,
    }


def worksheets(record: FidelityRecord, pages: list[dict]) -> tuple[dict, dict, dict]:
    """Independent sheet has no legacy text, table positions, spans or labels."""
    if record.document_format != "pdf" or not (record.table_cells or record.table_relationships):
        raise PacketError("Table-labelled PDF required")
    page_numbers = {p["page_number"] for p in pages}
    if any(a.source.page_number not in page_numbers for a in record.anchors):
        raise PacketError("Legacy page outside original")
    source = {
        "document_id": record.document_id,
        "sha256": record.source_sha256,
        "size_bytes": record.source_size_bytes,
        "local_pdf": f"../../sources/{record.document_id}.pdf",
    }
    blind = {
        "version": VERSION,
        "source": source,
        "state": "DRAFT_NOT_REVIEWED",
        "reviewer": {
            "id": None,
            "reviewed_on": None,
            "independent_of_original_annotator": None,
            "parser_outputs_seen": None,
            "legacy_assertions_seen_before_draft": None,
            "prior_exposure_description": None,
            "viewer_tool": None,
            "viewer_version": None,
            "render_settings": None,
        },
        "pages": [{**page, "table_presence": None, "regions": [], "notes": None} for page in pages],
        "tables": [],
        "table_template": {
            "review_table_id": None,
            "page_number": None,
            "bbox_pdf_user_space_points": None,
            "coordinate_basis": None,
            "row_count": None,
            "column_count": None,
            "structure_complete": None,
            "merged_or_ambiguous": None,
            "cells": [],
            "relationships": [],
            "unresolved": [],
            "evidence_reference": None,
        },
        "cell_template": {
            "review_cell_id": None,
            "row": None,
            "column": None,
            "row_span": None,
            "column_span": None,
            "literal_text": None,
            "bbox_pdf_user_space_points": None,
            "header_role": None,
            "value_unit_period_links": [],
            "evidence_reference": None,
            "uncertain": None,
            "notes": None,
        },
        "relationship_template": {
            "left_review_cell_id": None,
            "right_review_cell_id": None,
            "relationship": None,
            "visual_basis": None,
            "uncertain": None,
        },
        "family_language": {"family_id": None, "languages": [], "split": None, "basis": None},
        "completion": {
            "all_pages_inspected": None,
            "all_tables_inventoried": None,
            "signed_review_fingerprint": None,
        },
    }
    scopes: dict[tuple, list[str]] = {}
    for anchor in record.anchors:
        key = (anchor.source.page_number, anchor.source.table_index)
        scopes.setdefault(key, []).append(anchor.anchor_id)
    legacy = {
        "version": VERSION,
        "source": source,
        "status": "LEGACY_ASSERTIONS_NOT_NEW_INDEPENDENT_EVIDENCE",
        "frozen_record": record.model_dump(mode="json"),
        "source_regions": [
            {
                "page_number": key[0],
                "asserted_table_index": key[1],
                "anchor_ids": ids,
                "independent_bbox": None,
                "mapping_state": "UNRESOLVED",
            }
            for key, ids in sorted(scopes.items(), key=lambda item: (item[0][0], str(item[0][1])))
        ],
        "schema_gaps": list(BLOCKERS),
    }
    decisions = []
    for kind, items in (
        ("anchor", record.anchors),
        ("cell_span", record.table_cells),
        ("relationship", record.table_relationships),
        ("order", record.order_pairs),
    ):
        for index, _ in enumerate(items):
            decisions.append({"legacy_assertion_ref": f"{kind}:{index}", **review_fields()})
    adjudication = {
        "version": VERSION,
        "source": source,
        "state": "UNRESOLVED",
        "decision_options": ["confirm", "reject", "revise", "unresolved", "not_applicable"],
        "evidence_template": {
            "source_sha256": None,
            "page_number": None,
            "bbox_pdf_user_space_points": None,
            "coordinate_basis": None,
            "review_evidence_revision": None,
        },
        "independent_draft_fingerprint_before_legacy_comparison": None,
        "source_region_decisions": [
            {"legacy_region_ref": i, "independent_region_ref": None, **review_fields()}
            for i in range(len(legacy["source_regions"]))
        ],
        "assertion_decisions": decisions,
        "missing_or_extra_assertions": [],
        "reviewer_disagreements": [],
        "ready_for_separate_gold_revision": False,
    }
    return blind, legacy, adjudication


def aggregate(records: tuple[FidelityRecord, ...], page_counts: dict[str, int]) -> dict:
    """Whitelist counters/fixed states only; no text, locators, filenames or rights URLs."""
    documents = []
    for record in records:
        documents.append(
            {
                "document_id": record.document_id,
                "pages": page_counts[record.document_id],
                "anchors": len(record.anchors),
                "order_pairs": len(record.order_pairs),
                "cell_spans": len(record.table_cells),
                "same_row": sum(r.relationship == "same_row" for r in record.table_relationships),
                "same_column": sum(
                    r.relationship == "same_column" for r in record.table_relationships
                ),
                "legacy_source_regions": len(
                    {(a.source.page_number, a.source.table_index) for a in record.anchors}
                ),
                "legacy_table_regions": len(
                    {
                        (a.source.page_number, a.source.table_index)
                        for a in record.anchors
                        if a.source.table_index is not None
                    }
                ),
                "relationships": len(record.table_relationships),
                "unresolved_assertions": len(record.anchors)
                + len(record.order_pairs)
                + len(record.table_cells)
                + len(record.table_relationships),
                "legacy_spanning_cells": sum(
                    c.row_span > 1 or c.column_span > 1 for c in record.table_cells
                ),
                "legacy_reviewer_count": record.reviewer_count,
            }
        )
    keys = (
        "pages",
        "anchors",
        "order_pairs",
        "cell_spans",
        "same_row",
        "same_column",
        "legacy_source_regions",
        "legacy_table_regions",
        "relationships",
        "unresolved_assertions",
    )
    return {
        "version": VERSION,
        "execution": "PASS",
        "selected_documents": len(records),
        "prepared_documents": len(documents),
        "excluded_documents": 0,
        "totals": {key: sum(d[key] for d in documents) for key in keys},
        "independent_reviews_completed": 0,
        "independent_assertions_verified": 0,
        "review_readiness": "AWAITING_INDEPENDENT_HUMAN_REVIEW",
        "evaluation_readiness": "NOT_ESTABLISHED",
        "qg_00": "NOT_EVALUATED",
        "qg_01": "NOT_EVALUATED",
        "production_authorized": False,
        "blockers": list(BLOCKERS),
        "documents": documents,
    }


def generate(
    manifest: Path,
    corpus: Path,
    gold: Path,
    output: Path,
    *,
    expected: Expected | None = None,
    allow_synthetic: bool = False,
    root: Path = ROOT,
    eligibility: Path | None = None,
) -> dict:
    from pypdf import PdfReader

    require_unoptimized()
    fresh_output(output, corpus, root=root)
    start = time.monotonic()
    expected = expected or Expected()
    before, paths, records, metadata = preflight(
        manifest, corpus, gold, expected, allow_synthetic=allow_synthetic, eligibility=eligibility
    )
    provenance = {
        "version": VERSION,
        "inputs": before,
        "code": {p: sha(ROOT / p) for p in CODE},
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "packages": {name: importlib.metadata.version(name) for name in ("pydantic", "pypdf")},
        "max_seconds": MAX_SECONDS,
        "max_pages_per_source": MAX_PAGES,
    }
    if eligibility is not None:
        for name in (
            "tools/extraction_quality/pdf_review_eligibility.py",
            "tools/extraction_quality/pdf_review_validation.py",
            "src/doclens_ai/eda/corpus_v2.py",
            "tests/unit/test_pdf_review_eligibility.py",
        ):
            provenance["code"][name] = sha(ROOT / name)
    output.mkdir(parents=True)
    (output / "sources").mkdir()
    write_json(output / "inputs.json", provenance)
    counts = {}
    for record in records:
        if time.monotonic() - start >= MAX_SECONDS:
            raise PacketError("Packet preparation timeout")
        reader = PdfReader(paths[record.document_id])
        if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PAGES:
            raise PacketError("Original page inventory rejected")
        pages = [
            {
                "page_number": i + 1,
                "media_box_pdf_user_space": list(map(float, page.mediabox)),
                "crop_box_pdf_user_space": list(map(float, page.cropbox)),
                "rotation": page.rotation,
            }
            for i, page in enumerate(reader.pages)
        ]
        counts[record.document_id] = len(pages)
        blind, legacy, adjudication = worksheets(record, pages)
        legacy["frozen_manifest_provenance"] = metadata[record.document_id]
        stage = output / "review" / record.document_id
        stage.mkdir(parents=True)
        for name, value in (
            ("independent.json", blind),
            ("legacy-assertions.json", legacy),
            ("adjudication.json", adjudication),
        ):
            write_json(stage / name, value)
        copy = output / "sources" / f"{record.document_id}.pdf"
        with paths[record.document_id].open("rb") as source, copy.open("xb") as destination:
            shutil.copyfileobj(source, destination, length=1024**2)
        if copy.stat().st_size != record.source_size_bytes or sha(copy) != record.source_sha256:
            raise PacketError("Review copy identity mismatch")
    after, _, _, _ = preflight(
        manifest, corpus, gold, expected, allow_synthetic=allow_synthetic, eligibility=eligibility
    )
    if before != after or provenance["code"] != {p: sha(ROOT / p) for p in provenance["code"]}:
        raise PacketError("Frozen input or code drift")
    if time.monotonic() - start >= MAX_SECONDS:
        raise PacketError("Packet preparation timeout")
    summary = aggregate(records, counts)
    if eligibility is not None:
        summary["eligibility"] = before["eligibility"]
        summary["excluded_documents"] = before["eligibility"]["pool"] - len(records)
    summary["input_identity_fingerprint"] = fingerprint(before)
    write_json(output / "summary.json", summary)
    (output / "REVIEW.md").write_text(
        "LOCAL PRIVATE PACKET — DO NOT COMMIT OR TRANSFER\n\n"
        "1. Inspect every original page in sources; do not run PDF actions or external links.\n"
        "2. Complete independent.json before legacy-assertions.json; record prior exposure.\n"
        "3. Freeze/sign that draft and record its fingerprint before comparing legacy assertions.\n"
        "4. Adjudicate each region, anchor, cell/span, order and relationship; keep ambiguity.\n"
        "5. Retain disagreements, provenance and missing/extra labels; no automatic correction.\n"
        "6. A separately approved Gold revision is required; this packet never edits frozen Gold.\n"
        "Legacy table indices are assertions, not independently observed visual table identities.\n"
        "Only COMPLETE.json plus matching artifact hashes identifies a complete preparation.\n",
        encoding="utf-8",
        newline="\n",
    )
    artifacts = {
        p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    write_json(output / "artifact-manifest.json", artifacts)
    write_json(
        output / "COMPLETE.json",
        {
            "artifact_manifest_sha256": sha(output / "artifact-manifest.json"),
            "packet_fingerprint": fingerprint(artifacts),
        },
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--eligibility", type=Path)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                generate(
                    args.manifest, args.corpus, args.gold, args.output, eligibility=args.eligibility
                ),
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        print("BLOCKED: frozen review inputs or private output boundary rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
