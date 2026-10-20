"""Offline additive evidence contract. V1 remains the production wire contract.

Human attestations are supplied inputs, never a claim made by this module. They
are not cryptographic identity authentication or runtime workspace authorization.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.models import DocumentFormat, ExtractionResult, TextBlock

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Name = Annotated[str, Field(min_length=1, max_length=200, pattern=r"\S")]
Index = Annotated[int, Field(ge=0, le=100_000)]
Positive = Annotated[int, Field(gt=0, le=100_000)]
BBox = tuple[float, float, float, float]
RelationKind = Literal[
    "same_row",
    "same_column",
    "row_header",
    "column_header",
    "unit",
    "period",
    "merged_header",
    "continues",
    "before",
]


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, revalidate_instances="always"
    )


class Scope(Contract):
    workspace_id: Name
    document_id: Name
    version_id: Name
    raw_sha256: Digest


def valid_bbox(box: BBox, outer: BBox | None = None) -> bool:
    import math

    return (
        all(math.isfinite(x) for x in box)
        and box[0] < box[2]
        and box[1] < box[3]
        and (
            outer is None
            or (outer[0] <= box[0] < box[2] <= outer[2] and outer[1] <= box[1] < box[3] <= outer[3])
        )
    )


class Page(Contract):
    number: Positive
    media_box: BBox
    crop_box: BBox
    rotation: Literal[0, 90, 180, 270]

    @model_validator(mode="after")
    def geometry(self) -> Self:
        if not valid_bbox(self.media_box) or not valid_bbox(self.crop_box, self.media_box):
            raise ValueError("invalid page geometry")
        return self


class Locator(Contract):
    page: Positive
    bbox: BBox | None  # None means unknown, never synthesized from text proximity.
    coordinate_basis: Literal["pdf_user_space_unrotated"] | None

    @model_validator(mode="after")
    def geometry(self) -> Self:
        if (self.bbox is None) != (self.coordinate_basis is None):
            raise ValueError("coordinate basis required")
        if self.bbox is not None and not valid_bbox(self.bbox):
            raise ValueError("invalid bbox")
        return self


class Cell(Contract):
    cell_id: Name
    literal: Annotated[str, Field(max_length=100_000)]
    locator: Locator
    row: Index | None
    column: Index | None
    row_span: Positive | None
    column_span: Positive | None
    role: Literal["value", "row_header", "column_header", "unit", "period", "other"] | None


class TextAnchor(Contract):
    anchor_id: Name
    literal: Annotated[str, Field(min_length=1, max_length=100_000)]
    locator: Locator
    occurrence: Positive
    category: Literal["text", "numeric", "sign", "date", "period", "unit"]


class Relation(Contract):
    left: Name
    right: Name
    kind: RelationKind
    evidence_note: Name | None


class Table(Contract):
    table_id: Name
    section_id: Name | None
    cells: Annotated[tuple[Cell, ...], Field(min_length=1, max_length=10_000)]
    relations: Annotated[tuple[Relation, ...], Field(max_length=20_000)]
    complete: bool
    unresolved: tuple[Name, ...] = ()

    @model_validator(mode="after")
    def references(self) -> Self:
        ids = [c.cell_id for c in self.cells]
        keys = [(r.left, r.right, r.kind) for r in self.relations]
        if len(set(ids)) != len(ids) or len(set(keys)) != len(keys):
            raise ValueError("duplicate identity")
        if any(
            r.left not in ids or r.right not in ids or r.left == r.right for r in self.relations
        ):
            raise ValueError("invalid relation reference")
        return self


class HumanReview(Contract):
    reviewer_id: Name
    reviewed_on: date
    kind: Literal["independent_human", "synthetic_fixture"]
    independent_of_annotator: Literal[True]
    original_pages_inspected: Literal[True]
    parser_outputs_seen: Literal[False]
    legacy_seen_before_draft: Literal[False]
    prior_exposure: Name
    viewer: Name
    viewer_version: Name
    render_settings: Name
    draft_sha256: Digest
    annotation_authorized: Literal[True]
    annotation_permission_reference: Name

    @model_validator(mode="after")
    def identity(self) -> Self:
        if re.search(r"\b(codex|llm|extractor|chatgpt|gpt|assistant)\b", self.reviewer_id, re.I):
            raise ValueError("machine review is not independent Gold")
        if self.reviewed_on > date.today():
            raise ValueError("future review date")
        return self


class ReviewedDocument(Contract):
    schema_version: Literal["reviewed-pdf-gold-2.0"] = "reviewed-pdf-gold-2.0"
    revision: Name
    scope: Scope
    pages: Annotated[tuple[Page, ...], Field(min_length=1, max_length=100)]
    review: HumanReview
    family_id: Name
    languages: Annotated[tuple[Literal["ru", "kk", "en", "other"], ...], Field(min_length=1)]
    split: Literal["dev", "sealed_test", "train"]
    tables: tuple[Table, ...]
    decisions_sha256: Digest
    text_anchors: tuple[TextAnchor, ...] = ()
    order_pairs: tuple[tuple[Name, Name], ...] = ()

    @model_validator(mode="after")
    def source_geometry(self) -> Self:
        pages = {p.number: p for p in self.pages}
        if sorted(pages) != list(range(1, len(self.pages) + 1)):
            raise ValueError("page inventory mismatch")
        if len({t.table_id for t in self.tables}) != len(self.tables):
            raise ValueError("duplicate table")
        anchors = {a.anchor_id: a for a in self.text_anchors}
        if len(anchors) != len(self.text_anchors) or any(
            left not in anchors or right not in anchors or left == right
            for left, right in self.order_pairs
        ):
            raise ValueError("invalid anchor references")
        for anchor in self.text_anchors:
            if (
                anchor.locator.page not in pages
                or anchor.locator.bbox is None
                or not valid_bbox(anchor.locator.bbox, pages[anchor.locator.page].crop_box)
            ):
                raise ValueError("unverified anchor locator")
        for table in self.tables:
            if not table.complete or table.unresolved:
                raise ValueError("unresolved table")
            occupied: set[tuple[int, int, int]] = set()
            for cell in table.cells:
                loc = cell.locator
                if (
                    loc.page not in pages
                    or loc.bbox is None
                    or not valid_bbox(loc.bbox, pages[loc.page].crop_box)
                    or any(
                        x is None for x in (cell.row, cell.column, cell.row_span, cell.column_span)
                    )
                    or cell.role is None
                ):
                    raise ValueError("incomplete source evidence")
                # Bounded footprint; reject overlapping logical spans and ambiguous duplicates.
                if cell.row_span * cell.column_span > 10_000:
                    raise ValueError("span limit")
                for row in range(cell.row, cell.row + cell.row_span):
                    for col in range(cell.column, cell.column + cell.column_span):
                        key = (loc.page, row, col)
                        if key in occupied:
                            raise ValueError("overlapping cells")
                        occupied.add(key)
            if any(r.evidence_note is None for r in table.relations):
                raise ValueError("missing relationship evidence")
            cells = {c.cell_id: c for c in table.cells}
            for rel in table.relations:
                target_role = {
                    "unit": "unit",
                    "period": "period",
                    "row_header": "row_header",
                    "column_header": "column_header",
                }.get(rel.kind)
                if target_role is not None and cells[rel.right].role != target_role:
                    raise ValueError("semantic role mismatch")
        return self


class Proposal(Contract):
    scope: Scope
    engine: Name
    candidate_revision: Name
    config_sha256: Digest
    tables: Annotated[tuple[Table, ...], Field(max_length=1000)]

    @model_validator(mode="after")
    def bounds(self) -> Self:
        if sum(len(t.cells) for t in self.tables) > 20_000:
            raise ValueError("candidate cell limit")
        if sum(len(c.literal) for t in self.tables for c in t.cells) > 5_000_000:
            raise ValueError("candidate literal limit")
        return self


class MergeDecision(Contract):
    table_id: Name
    state: Literal["accepted", "needs_review", "rejected"]
    reason: Literal["independent_match", "unreviewed", "conflict", "source_mismatch", "invalid"]
    table_sha256: Digest
    review_revision: Name | None
    evidence_ids: tuple[Digest, ...]


def cell_evidence_id(scope: Scope, table_id: str, cell: Cell) -> str:
    return fingerprint(
        {
            "scope": scope.model_dump(mode="json"),
            "table_id": table_id,
            "cell": cell.model_dump(mode="json"),
        }
    )


def table_digest(table: Table) -> str:
    return fingerprint(table.model_dump(mode="json"))


def verify_proposal(
    proposal: Proposal,
    scope: Scope,
    reviewed: ReviewedDocument | None,
    *,
    allow_synthetic: bool = False,
) -> tuple[MergeDecision, ...]:
    """Exact independently authored evidence matching, without inference or correction."""
    proposal = Proposal.model_validate(proposal)
    if reviewed is not None:
        reviewed = ReviewedDocument.model_validate(reviewed)
        if reviewed.review.kind != "independent_human" and not allow_synthetic:
            raise ValueError("synthetic review rejected")
    labels = (
        {t.table_id: t for t in reviewed.tables} if reviewed and reviewed.scope == scope else {}
    )
    decisions = []
    seen = set()
    for table in proposal.tables:
        state, reason = "needs_review", "unreviewed"
        if proposal.scope != scope or (reviewed is not None and reviewed.scope != scope):
            state, reason = "rejected", "source_mismatch"
        elif table.table_id in seen:
            state, reason = "rejected", "invalid"
        elif table.table_id in labels:
            state, reason = (
                ("accepted", "independent_match")
                if table == labels[table.table_id]
                else ("needs_review", "conflict")
            )
        seen.add(table.table_id)
        decisions.append(
            MergeDecision(
                table_id=table.table_id,
                state=state,
                reason=reason,
                table_sha256=table_digest(table),
                review_revision=reviewed.revision if state == "accepted" else None,
                evidence_ids=tuple(cell_evidence_id(scope, table.table_id, c) for c in table.cells)
                if state == "accepted"
                else (),
            )
        )
    # Duplicated table identity invalidates every occurrence, including the first.
    duplicates = {
        t.table_id
        for t in proposal.tables
        if sum(x.table_id == t.table_id for x in proposal.tables) > 1
    }
    return tuple(
        d.model_copy(
            update={
                "state": "rejected",
                "reason": "invalid",
                "review_revision": None,
                "evidence_ids": (),
            }
        )
        if d.table_id in duplicates
        else d
        for d in decisions
    )


class EvidenceEnvelope(Contract):
    schema_version: Literal["2.0"] = "2.0"
    scope: Scope
    native_v1: dict  # A lossless snapshot; never flatten proposals into v1 blocks.
    native_sha256: Digest
    parser_revision: Name
    proposal: Proposal | None
    decisions: tuple[MergeDecision, ...]
    warnings: tuple[Name, ...]
    production_authorized: Literal[False] = False

    @model_validator(mode="after")
    def immutable_native(self) -> Self:
        if (
            fingerprint(self.native_v1) != self.native_sha256
            or self.native_v1.get("source_sha256") != self.scope.raw_sha256
            or self.native_v1.get("schema_version") != "1.0"
        ):
            raise ValueError("native identity mismatch")
        return self


def envelope(
    native: ExtractionResult,
    scope: Scope,
    *,
    parser_revision: str,
    proposal: Proposal | None = None,
    reviewed: ReviewedDocument | None = None,
    warnings: tuple[str, ...] = (),
    allow_synthetic: bool = False,
) -> EvidenceEnvelope:
    if native.document_format != DocumentFormat.PDF:
        raise ValueError("PDF enrichment only")
    value = native.to_dict()
    return EvidenceEnvelope(
        scope=scope,
        native_v1=value,
        native_sha256=fingerprint(value),
        parser_revision=parser_revision,
        proposal=proposal,
        decisions=verify_proposal(proposal, scope, reviewed, allow_synthetic=allow_synthetic)
        if proposal
        else (),
        warnings=warnings,
    )


def native_text_evidence(native: ExtractionResult, scope: Scope) -> tuple[dict, ...]:
    """Page/block text identities retain exact literals; no invented bbox."""
    if native.source_sha256 != scope.raw_sha256:
        raise ValueError("source mismatch")
    return tuple(
        {
            "evidence_id": fingerprint(
                {
                    "scope": scope.model_dump(mode="json"),
                    "order": b.order,
                    "source": native.to_dict()["blocks"][i]["source"],
                    "literal": b.text,
                }
            ),
            "literal": b.text,
            "page": b.source.page_number,
            "bbox": None,
        }
        for i, b in enumerate(native.blocks)
        if isinstance(b, TextBlock)
    )
