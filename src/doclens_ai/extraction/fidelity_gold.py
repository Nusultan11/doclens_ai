"""Strict private Fidelity Gold v1; never export validation inputs in diagnostics."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

OpaqueID = Annotated[str, Field(pattern=r"^c1-[0-9]{4}$")]
AnchorID = Annotated[str, Field(pattern=r"^a[0-9]{1,5}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Index = Annotated[int, Field(ge=0)]
Positive = Annotated[int, Field(gt=0)]
Text = Annotated[str, Field(min_length=1, max_length=10_000)]


class GoldError(ValueError):
    """A deliberately content-free annotation validation error."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Locator(StrictModel):
    """Page numbers are one-based; all other indices are zero-based."""

    region: Literal["body", "header", "footer", "footnote", "endnote", "comment", "drawing"]
    page_number: Positive | None = None
    block_index: Index | None = None
    table_index: Index | None = None
    row_index: Index | None = None
    column_index: Index | None = None
    sheet_index: Index | None = None
    cell_coordinate: Annotated[str, Field(pattern=r"^[A-Z]{1,3}[1-9][0-9]{0,6}$")] | None = None
    part_index: Index | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if (self.row_index is None) != (self.column_index is None):
            raise ValueError("paired row/column required")
        if self.table_index is not None and self.block_index is None:
            raise ValueError("table block required")
        if self.cell_coordinate is not None:
            from openpyxl.utils.cell import coordinate_to_tuple

            row, column = coordinate_to_tuple(self.cell_coordinate)
            if row > 1_048_576 or column > 16_384:
                raise ValueError("cell out of bounds")
            if self.row_index is not None and (row - 1, column - 1) != (
                self.row_index,
                self.column_index,
            ):
                raise ValueError("inconsistent cell indices")
        return self


class TextAnchor(StrictModel):
    anchor_id: AnchorID
    text: Text
    source: Locator
    occurrence: Positive = 1

    @model_validator(mode="after")
    def nonblank(self) -> Self:
        if not self.text.strip():
            raise ValueError("blank anchor")
        return self


class OrderPair(StrictModel):
    before: AnchorID
    after: AnchorID


class TableCellCheck(StrictModel):
    anchor_id: AnchorID
    row_span: Positive = 1
    column_span: Positive = 1


class TableRelationship(StrictModel):
    left: AnchorID
    right: AnchorID
    relationship: Literal["same_row", "same_column"]


class CellCheck(StrictModel):
    source: Locator
    # Null is a reviewed expectation, not an omitted check.
    value: str | None = Field(max_length=10_000)
    formula: str | None = Field(max_length=10_000)
    cached_value: str | None = Field(max_length=10_000)
    check_display: bool = False
    displayed_value: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def display_intent(self) -> Self:
        if self.check_display != (self.displayed_value is not None):
            raise ValueError("explicit display expectation required")
        return self


class FidelityRecord(StrictModel):
    schema_version: Literal["1.0"]
    dataset_revision: Literal["corpus-v1-fidelity-v1"]
    dataset_kind: Literal["real", "synthetic"]
    document_id: OpaqueID
    source_sha256: Digest
    source_size_bytes: Positive
    document_format: Literal["pdf", "docx", "xlsx"]
    review_status: Literal["reviewed"]
    review_basis: Literal["original_document", "synthetic_fixture"]
    reviewer_count: Annotated[int, Field(ge=1, le=10)]
    reviewed_on: date
    anchors: Annotated[list[TextAnchor], Field(max_length=500)]
    order_pairs: Annotated[list[OrderPair], Field(max_length=500)]
    table_cells: Annotated[list[TableCellCheck], Field(max_length=500)]
    table_relationships: Annotated[list[TableRelationship], Field(max_length=500)]
    cells: Annotated[list[CellCheck], Field(max_length=500)]

    @model_validator(mode="after")
    def relationships(self) -> Self:
        if (self.dataset_kind == "real") != (self.review_basis == "original_document"):
            raise ValueError("review basis mismatch")
        if self.reviewed_on > date.today():
            raise ValueError("future review")
        ids = {anchor.anchor_id for anchor in self.anchors}
        if len(ids) != len(self.anchors) or not (self.anchors or self.cells):
            raise ValueError("unique evidence required")
        anchors = {anchor.anchor_id: anchor for anchor in self.anchors}
        for collection in (self.order_pairs, self.table_cells, self.table_relationships):
            keys = [item.model_dump_json() for item in collection]
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate assertions")
        edges: dict[str, set[str]] = {key: set() for key in ids}
        for pair in self.order_pairs:
            if pair.before not in ids or pair.after not in ids or pair.before == pair.after:
                raise ValueError("invalid order references")
            edges[pair.before].add(pair.after)
        pending = set(ids)
        while pending:
            roots = {key for key in pending if not any(key in edges[k] for k in pending)}
            if not roots:
                raise ValueError("cyclic order")
            pending -= roots
        for check in self.table_cells:
            if check.anchor_id not in ids:
                raise ValueError("invalid table reference")
            if anchors[check.anchor_id].source.row_index is None:
                raise ValueError("table cell needs grid locator")
            if self.document_format != "xlsx" and (
                anchors[check.anchor_id].source.table_index is None
            ):
                raise ValueError("explicit table scope required")
        for pair in self.table_relationships:
            if pair.left not in ids or pair.right not in ids or pair.left == pair.right:
                raise ValueError("invalid table references")
            left, right = anchors[pair.left].source, anchors[pair.right].source
            if left.row_index is None or right.row_index is None:
                raise ValueError("relationship needs grid locators")
            if self.document_format != "xlsx" and left.table_index is None:
                raise ValueError("explicit table scope required")
            scope = (
                "page_number",
                "block_index",
                "table_index",
                "sheet_index",
                "region",
                "part_index",
            )
            if any(getattr(left, key) != getattr(right, key) for key in scope):
                raise ValueError("different table scopes")
            key = "row_index" if pair.relationship == "same_row" else "column_index"
            if getattr(left, key) != getattr(right, key):
                raise ValueError("contradictory relationship")
        if self.cells and self.document_format != "xlsx":
            raise ValueError("cell checks require XLSX")
        locators = [anchor.source for anchor in self.anchors] + [cell.source for cell in self.cells]
        for locator in locators:
            self._validate_locator(locator)
        for cell in self.cells:
            if cell.source.region != "body" or cell.source.cell_coordinate is None:
                raise ValueError("cell checks require cell locator")
        signatures = [cell.source.model_dump_json() for cell in self.cells]
        if len(signatures) != len(set(signatures)):
            raise ValueError("duplicate cell checks")
        return self

    def _validate_locator(self, source: Locator) -> None:
        if self.document_format == "pdf":
            if source.page_number is None or source.region not in {"body", "drawing"}:
                raise ValueError("PDF page required")
            forbidden = (source.sheet_index, source.cell_coordinate, source.part_index)
        elif self.document_format == "docx":
            if source.region == "body" and source.block_index is None:
                raise ValueError("DOCX block required")
            if source.region != "body" and source.part_index is None:
                raise ValueError("DOCX part required")
            forbidden = (source.page_number, source.sheet_index, source.cell_coordinate)
        else:
            if source.sheet_index is None or source.region != "body":
                raise ValueError("XLSX sheet required")
            if source.cell_coordinate is None:
                raise ValueError("XLSX cell required")
            forbidden = (
                source.page_number,
                source.block_index,
                source.table_index,
                source.part_index,
            )
        if any(value is not None for value in forbidden):
            raise ValueError("cross-format locator")


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise GoldError("Duplicate Gold field")
    return value


def load_gold(
    path: Path,
    sources: dict[str, tuple[str, int, str]],
    *,
    allow_synthetic: bool = False,
) -> tuple[FidelityRecord, ...]:
    """Validate a bounded JSONL file, including frozen source identities."""

    try:
        if path.is_symlink() or path.stat().st_size > 20 * 1024 * 1024:
            raise GoldError("Gold file rejected")
        parsed = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                # Pydantic's JSON parser accepts duplicate keys using the last value.
                # Check decoded keys first, retaining strict JSON-mode model validation.
                json.loads(line, object_pairs_hook=_unique_fields)
                parsed.append(FidelityRecord.model_validate_json(line))
        records = tuple(parsed)
        if not records or len(records) > 90:
            raise GoldError("Gold coverage rejected")
        ids = {record.document_id for record in records}
        if len(ids) != len(records) or len({record.dataset_kind for record in records}) != 1:
            raise GoldError("Gold identities rejected")
        for record in records:
            if record.dataset_kind == "synthetic" and not allow_synthetic:
                raise GoldError("Synthetic Gold requires explicit opt-in")
            if sources.get(record.document_id) != (
                record.source_sha256,
                record.source_size_bytes,
                record.document_format,
            ):
                raise GoldError("Gold source mismatch")
        return tuple(sorted(records, key=lambda record: record.document_id))
    except Exception:
        # Pydantic's ordinary error representation includes excerpts and input values.
        raise GoldError("Invalid Fidelity Gold; inspect annotations privately") from None
