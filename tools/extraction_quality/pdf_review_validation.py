"""Validate completed ML-27 worksheets locally; never prepare human attestations.

Extended worksheet fields are documented in the ML-28 report. Supplied human
identity is an attestation, not an authenticated signature. Private outputs must
remain ignored; no frozen input is modified.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import date
from pathlib import Path

from pydantic import ValidationError
from pypdf import PdfReader

from doclens_ai.extraction.evidence_v2 import (
    Cell,
    HumanReview,
    Locator,
    Page,
    Relation,
    ReviewedDocument,
    Scope,
    Table,
    TextAnchor,
    valid_bbox,
)
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality.pdf_table_review_packet import (
    ROOT,
    Expected,
    PacketError,
    aggregate,
    fresh_output,
    no_links,
    preflight,
    worksheets,
    write_json,
)


def read_json(path: Path) -> dict:
    no_links(path)
    if path.stat().st_size > 20 * 1024**2:
        raise PacketError("Review input limit")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PacketError("Review object required")
    return value


def draft_fingerprint(draft: dict) -> str:
    value = copy.deepcopy(draft)
    value["completion"]["signed_review_fingerprint"] = None
    return fingerprint(value)


def original_pages(path: Path) -> list[dict]:
    reader = PdfReader(path)
    if reader.is_encrypted or not 0 < len(reader.pages) <= 100:
        raise PacketError("Page inventory rejected")
    return [
        {
            "page_number": i + 1,
            "media_box_pdf_user_space": list(map(float, p.mediabox)),
            "crop_box_pdf_user_space": list(map(float, p.cropbox)),
            "rotation": p.rotation,
        }
        for i, p in enumerate(reader.pages)
    ]


def _review(draft: dict, *, allow_synthetic: bool) -> HumanReview:
    r = draft["reviewer"]
    completion = draft["completion"]
    signature = draft_fingerprint(draft)
    if (
        draft["state"] != "REVIEWED"
        or completion["all_pages_inspected"] is not True
        or completion["all_tables_inventoried"] is not True
        or completion["signed_review_fingerprint"] != signature
    ):
        raise PacketError("Independent draft incomplete")
    review = HumanReview(
        reviewer_id=r["id"],
        reviewed_on=date.fromisoformat(r["reviewed_on"]),
        kind=r.get("kind", "independent_human"),
        independent_of_annotator=r["independent_of_original_annotator"],
        original_pages_inspected=completion["all_pages_inspected"],
        parser_outputs_seen=r["parser_outputs_seen"],
        legacy_seen_before_draft=r["legacy_assertions_seen_before_draft"],
        prior_exposure=r["prior_exposure_description"],
        viewer=r["viewer_tool"],
        viewer_version=r["viewer_version"],
        render_settings=r["render_settings"],
        draft_sha256=signature,
        annotation_authorized=r["annotation_authorized"],
        annotation_permission_reference=r["annotation_permission_reference"],
    )
    if review.kind != "independent_human" and not allow_synthetic:
        raise PacketError("Synthetic Gold rejected")
    return review


def _tables(draft: dict) -> tuple[Table, ...]:
    tables = []
    for table in draft["tables"]:
        cells = tuple(
            Cell(
                cell_id=c["review_cell_id"],
                literal=c["literal_text"],
                locator=Locator(
                    page=c.get("page_number", table["page_number"]),
                    bbox=tuple(c["bbox_pdf_user_space_points"]),
                    coordinate_basis=table["coordinate_basis"],
                ),
                row=c["row"],
                column=c["column"],
                row_span=c["row_span"],
                column_span=c["column_span"],
                role=c["header_role"],
            )
            for c in table["cells"]
        )
        if any(
            c.get("uncertain") is not False or not c.get("evidence_reference")
            for c in table["cells"]
        ):
            raise PacketError("Uncertain cell")
        relations = []
        for r in table["relationships"]:
            if r.get("uncertain") is not False:
                raise PacketError("Uncertain relationship")
            relations.append(
                Relation(
                    left=r["left_review_cell_id"],
                    right=r["right_review_cell_id"],
                    kind=r["relationship"],
                    evidence_note=r["visual_basis"],
                )
            )
        if (
            (
                table["merged_or_ambiguous"] is not False
                and table.get("merge_decisions_complete") is not True
            )
            or not table["evidence_reference"]
            or type(table["row_count"]) is not int
            or table["row_count"] <= 0
            or type(table["column_count"]) is not int
            or table["column_count"] <= 0
        ):
            raise PacketError("Unresolved table")
        # Explicit spans can represent merged headers; ambiguous geometry stays blocked.
        regions = {
            r["page_number"]: tuple(r["bbox_pdf_user_space_points"])
            for r in table.get(
                "source_regions",
                [
                    {
                        "page_number": table["page_number"],
                        "bbox_pdf_user_space_points": table["bbox_pdf_user_space_points"],
                    }
                ],
            )
        }
        for c, raw in zip(cells, table["cells"], strict=True):
            if (
                c.row is None
                or c.column is None
                or c.row_span is None
                or c.column_span is None
                or c.row + c.row_span > table["row_count"]
                or c.column + c.column_span > table["column_count"]
            ):
                raise PacketError("Cell outside reviewed grid")
            if (
                c.locator.page not in regions
                or not valid_bbox(regions[c.locator.page])
                or not valid_bbox(c.locator.bbox, regions[c.locator.page])
            ):
                raise PacketError("Cell outside reviewed source region")
            links = {(r.right, r.kind) for r in relations if r.left == c.cell_id}
            if set(map(tuple, raw["value_unit_period_links"])) != {
                (right, kind) for right, kind in links if kind in {"unit", "period"}
            }:
                raise PacketError("Semantic link mismatch")
        tables.append(
            Table(
                table_id=table["review_table_id"],
                section_id=table.get("section_id"),
                cells=cells,
                relations=tuple(relations),
                complete=table["structure_complete"],
                unresolved=tuple(table["unresolved"]),
            )
        )
    return tuple(tables)


def _decisions(
    adjudication: dict, template: dict, pages: list[dict], review: HumanReview, draft: dict
) -> None:
    if (
        adjudication["state"] != "ADJUDICATED"
        or adjudication["ready_for_separate_gold_revision"] is not True
        or adjudication["independent_draft_fingerprint_before_legacy_comparison"]
        != review.draft_sha256
    ):
        raise PacketError("Adjudication pending")
    crops = {p["page_number"]: tuple(p["crop_box_pdf_user_space"]) for p in pages}
    region_ids = {r["region_id"] for p in draft["pages"] for r in p["regions"]}
    for name, key in (
        ("assertion_decisions", "legacy_assertion_ref"),
        ("source_region_decisions", "legacy_region_ref"),
    ):
        actual = adjudication[name]
        expected = [x[key] for x in template[name]]
        if len(actual) != len(expected) or sorted(x[key] for x in actual) != sorted(expected):
            raise PacketError("Decision population mismatch")
        for item in actual:
            if (
                item["state"] != "RESOLVED"
                or item["decision"] not in {"confirm", "reject", "revise", "not_applicable"}
                or item["reviewer_id"] != review.reviewer_id
                or not item["rationale"]
                or item["ambiguity"] not in (None, False, "none")
                or not item["original_page_evidence"]
            ):
                raise PacketError("Unresolved assertion")
            reviewed_on = date.fromisoformat(item["reviewed_on"])
            if reviewed_on < review.reviewed_on or reviewed_on > date.today():
                raise PacketError("Invalid decision date")
            if item["decision"] != "confirm" and not item["proposed_correction"]:
                raise PacketError("Correction rationale required")
            if (
                name == "source_region_decisions"
                and item["independent_region_ref"] not in region_ids
            ):
                raise PacketError("Unmapped source region")
            for evidence in item["original_page_evidence"]:
                page = evidence["page_number"]
                if (
                    evidence["source_sha256"] != draft["source"]["sha256"]
                    or page not in crops
                    or evidence["coordinate_basis"] != "pdf_user_space_unrotated"
                    or not evidence["review_evidence_revision"]
                    or not valid_bbox(tuple(evidence["bbox_pdf_user_space_points"]), crops[page])
                ):
                    raise PacketError("Invalid original evidence")
    for entry in (
        adjudication["reviewer_disagreements"] + adjudication["missing_or_extra_assertions"]
    ):
        if (
            entry.get("state") != "RESOLVED"
            or not entry.get("resolution")
            or not entry.get("adjudicator_id")
            or entry["adjudicator_id"] == review.reviewer_id
            or re.search(
                r"\b(codex|llm|extractor|chatgpt|gpt|assistant)\b", entry["adjudicator_id"], re.I
            )
            or entry.get("original_pages_inspected") is not True
            or date.fromisoformat(entry["adjudicated_on"]) < review.reviewed_on
            or date.fromisoformat(entry["adjudicated_on"]) > date.today()
        ):
            raise PacketError("Disagreement pending")


def validate_document(
    draft: dict,
    adjudication: dict,
    record,
    pages: list[dict],
    scope: Scope,
    revision: str,
    *,
    allow_synthetic: bool = False,
    independent_only: bool = False,
):
    """Validate a worksheet; independent-only mode validates but never returns Gold.

    The workbench uses this before revealing legacy assertions. The default path
    still requires every adjudication decision and assertion mapping.
    """
    blind, legacy, template = worksheets(record, pages)
    if (
        draft["version"] != blind["version"]
        or adjudication["version"] != template["version"]
        or draft["source"] != blind["source"]
        or adjudication["source"] != template["source"]
    ):
        raise PacketError("Review source mismatch")
    actual_pages = [{k: p[k] for k in pages[0]} for p in draft["pages"]]
    if actual_pages != pages:
        raise PacketError("Review page identity mismatch")
    if any(
        table.get("assisted_grid_proposals")
        or any(cell.get("proposal_origin") for cell in table["cells"])
        for table in draft["tables"]
    ):
        raise PacketError("Assisted annotations require separate independent review before Gold")
    review = _review(draft, allow_synthetic=allow_synthetic)
    if not independent_only:
        _decisions(adjudication, template, pages, review, draft)
    region_pages = {r["region_id"]: p["page_number"] for p in draft["pages"] for r in p["regions"]}
    for mapping in () if independent_only else adjudication["source_region_decisions"]:
        old = legacy["source_regions"][mapping["legacy_region_ref"]]
        if (
            mapping["decision"] == "confirm"
            and region_pages[mapping["independent_region_ref"]] != old["page_number"]
        ):
            raise PacketError("Confirmed region page mismatch")
    tables = _tables(draft)
    if not independent_only:
        _assertion_links(draft, adjudication, record, tables)
    crops = {p["page_number"]: tuple(p["crop_box_pdf_user_space"]) for p in pages}
    for table in draft["tables"]:
        for region in table.get(
            "source_regions",
            [
                {
                    "page_number": table["page_number"],
                    "bbox_pdf_user_space_points": table["bbox_pdf_user_space_points"],
                }
            ],
        ):
            if region["page_number"] not in crops or not valid_bbox(
                tuple(region["bbox_pdf_user_space_points"]), crops[region["page_number"]]
            ):
                raise PacketError("Table region outside source")
    ids = {t.table_id for t in tables}
    region_ids = []
    for page in draft["pages"]:
        present = any(c.locator.page == page["page_number"] for t in tables for c in t.cells)
        if page["table_presence"] is not present:
            raise PacketError("Table inventory incomplete")
        for region in page["regions"]:
            if (
                region["table_id"] is not None
                and region["table_id"] not in ids
                or not valid_bbox(
                    tuple(region["bbox_pdf_user_space_points"]),
                    tuple(page["crop_box_pdf_user_space"]),
                )
            ):
                raise PacketError("Invalid reviewed region")
            region_ids.append(region["region_id"])
    if len(set(region_ids)) != len(region_ids):
        raise PacketError("Duplicate region identity")
    family = draft["family_language"]
    if not family["basis"] or scope.raw_sha256 != record.source_sha256:
        raise PacketError("Missing family provenance")
    document = ReviewedDocument(
        revision=revision,
        scope=scope,
        review=review,
        pages=tuple(
            Page(
                number=p["page_number"],
                media_box=tuple(p["media_box_pdf_user_space"]),
                crop_box=tuple(p["crop_box_pdf_user_space"]),
                rotation=p["rotation"],
            )
            for p in pages
        ),
        family_id=family["family_id"],
        languages=tuple(family["languages"]),
        split=family["split"],
        tables=tables,
        decisions_sha256=fingerprint(adjudication),
        text_anchors=tuple(
            TextAnchor.model_validate_json(json.dumps(a)) for a in draft.get("text_anchors", [])
        ),
        order_pairs=tuple(map(tuple, draft.get("order_pairs", []))),
    )
    return None if independent_only else document


def _assertion_links(draft: dict, adjudication: dict, record, tables: tuple[Table, ...]) -> None:
    """All retained assertions map to the independently frozen draft, without relabelling it."""
    anchors = {a["anchor_id"]: a for a in draft["text_anchors"]}
    cells = {(t.table_id, c.cell_id): c for t in tables for c in t.cells}
    relations = {t.table_id: t.relations for t in tables}
    cell_sets = {t.table_id: {c.cell_id: c for c in t.cells} for t in tables}
    old_anchors = {a.anchor_id: a for a in record.anchors}
    for decision in adjudication["assertion_decisions"]:
        if decision["decision"] in {"reject", "not_applicable"}:
            continue  # Explicit removal remains in adjudication, never edits legacy Gold.
        kind, index = decision["legacy_assertion_ref"].split(":")
        index = int(index)
        confirm = decision["decision"] == "confirm"
        if kind == "anchor":
            new = anchors[decision["independent_anchor_id"]]
            old = record.anchors[index]
            matches = (
                new["literal"] == old.text
                and new["locator"]["page"] == old.source.page_number
                and new["occurrence"] == old.occurrence
            )
        elif kind == "cell_span":
            ref = decision["independent_cell_ref"]
            cell = cells[(ref["table_id"], ref["cell_id"])]
            old = record.table_cells[index]
            anchor = old_anchors[old.anchor_id]
            matches = (
                cell.literal == anchor.text
                and cell.row_span == old.row_span
                and cell.column_span == old.column_span
                and cell.locator.page == anchor.source.page_number
                and cell.row == anchor.source.row_index
                and cell.column == anchor.source.column_index
            )
        elif kind == "relationship":
            ref = decision["independent_relation_ref"]
            relation = relations[ref["table_id"]][ref["index"]]
            cell_map = cell_sets[ref["table_id"]]
            old = record.table_relationships[index]
            matches = (
                relation.kind == old.relationship
                and cell_map[relation.left].literal == old_anchors[old.left].text
                and cell_map[relation.right].literal == old_anchors[old.right].text
            )
        else:
            left, right = draft["order_pairs"][decision["independent_order_index"]]
            old = record.order_pairs[index]
            matches = (
                anchors[left]["literal"] == old_anchors[old.before].text
                and anchors[right]["literal"] == old_anchors[old.after].text
            )
        if confirm and not matches:
            raise PacketError("Confirmed assertion conflicts with independent draft")


def pending_discrepancies(adjudication: dict) -> list[dict]:
    result = []
    for group in ("assertion_decisions", "source_region_decisions"):
        # Report only bounded indices, never untrusted text masquerading as an ID.
        for i, item in enumerate(adjudication.get(group, [])[:1000]):
            if item.get("state") != "RESOLVED" or item.get("decision") in (None, "unresolved"):
                result.append({"group": group, "index": i, "code": "DECISION_PENDING"})
    return result


def validate_workflow(
    manifest: Path,
    corpus: Path,
    gold: Path,
    review_dir: Path,
    scopes: dict[str, Scope],
    revision: str,
    *,
    expected: Expected | None = None,
    allow_synthetic: bool = False,
) -> tuple[dict, tuple[ReviewedDocument, ...]]:
    identity, paths, records, _ = preflight(
        manifest, corpus, gold, expected or Expected(), allow_synthetic=allow_synthetic
    )
    if set(scopes) != {r.document_id for r in records}:
        raise PacketError("Scope population mismatch")
    documents, discrepancies, coverage = [], [], []
    page_counts = {}
    for record in records:
        pages = original_pages(paths[record.document_id])
        page_counts[record.document_id] = len(pages)
        directory = review_dir / record.document_id
        try:
            draft = read_json(directory / "independent.json")
            adjudication = read_json(directory / "adjudication.json")
            pending = pending_discrepancies(adjudication)
            coverage.append(
                {
                    "document_id": record.document_id,
                    "pending_decisions": len(pending),
                    "decisions": pending,
                }
            )
            scope = scopes[record.document_id]
            if scope.document_id != record.document_id or scope.raw_sha256 != record.source_sha256:
                raise PacketError("Scope source mismatch")
            documents.append(
                validate_document(
                    draft,
                    adjudication,
                    record,
                    pages,
                    scope,
                    revision,
                    allow_synthetic=allow_synthetic,
                )
            )
        except (PacketError, ValidationError, ValueError, KeyError, TypeError, OSError, IndexError):
            discrepancies.append(
                {
                    "document_id": record.document_id,
                    "code": "INCOMPLETE_OR_INVALID_INDEPENDENT_REVIEW",
                }
            )
    after = preflight(
        manifest, corpus, gold, expected or Expected(), allow_synthetic=allow_synthetic
    )[0]
    if after != identity:
        raise PacketError("Frozen inputs changed")
    summary = aggregate(records, page_counts)
    family_splits: dict[str, set[str]] = {}
    for document in documents:
        family_splits.setdefault(document.family_id, set()).add(document.split)
    if any(len(splits) != 1 for splits in family_splits.values()):
        discrepancies.append({"code": "FAMILY_SPLIT_CONFLICT"})
    if not allow_synthetic and (
        summary["totals"]["unresolved_assertions"] != 110
        or summary["totals"]["legacy_source_regions"] != 19
    ):
        raise PacketError("Frozen assertion population mismatch")
    summary.update(
        execution="BLOCKED" if discrepancies else "PASS",
        independent_reviews_completed=len(documents),
        independent_assertions_verified=sum(
            len(r.anchors) + len(r.table_cells) + len(r.table_relationships) + len(r.order_pairs)
            for r in records
            if r.document_id in {d.scope.document_id for d in documents}
        ),
        discrepancies=discrepancies,
        export_ready=not discrepancies,
        review_readiness="BLOCKED" if discrepancies else "ATTESTATIONS_VALIDATED",
        input_identity_fingerprint=fingerprint(identity),
        decision_coverage=coverage,
    )
    # Readiness validation alone does not establish coverage thresholds or fidelity PASS.
    return summary, tuple(documents) if not discrepancies else ()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "corpus", "gold", "review-dir", "scopes", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()
    try:
        fresh_output(args.output, args.corpus, root=ROOT)
        scopes = {k: Scope.model_validate(v) for k, v in read_json(args.scopes).items()}
        summary, documents = validate_workflow(
            args.manifest, args.corpus, args.gold, args.review_dir, scopes, args.revision
        )
        args.output.mkdir(parents=True)
        write_json(args.output / "validation.json", summary)
        if args.export and not summary["export_ready"]:
            print("BLOCKED: independent review incomplete; no Gold exported")
            return 2
        if args.export:
            write_json(
                args.output / "reviewed-gold-v2.json",
                {
                    "schema_version": "reviewed-pdf-population-2.0",
                    "revision": args.revision,
                    "documents": [d.model_dump(mode="json") for d in documents],
                },
            )
        print(
            json.dumps(
                {
                    k: summary[k]
                    for k in ("execution", "export_ready", "independent_reviews_completed")
                }
            )
        )
        return 0 if summary["export_ready"] else 2
    except Exception:
        print("BLOCKED: review inputs or private output rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
