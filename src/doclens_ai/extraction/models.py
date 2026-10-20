"""Typed contracts for standalone document extraction."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import StrEnum
from typing import Any


class DocumentFormat(StrEnum):
    """Document formats supported by the extraction baseline."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"


class ExtractionStatus(StrEnum):
    """Top-level extraction outcomes."""

    SUCCESS = "success"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class WarningSeverity(StrEnum):
    """Whether a warning changes the extraction outcome."""

    INFO = "info"
    REVIEW = "review"


class WarningCode(StrEnum):
    """Sanitized, machine-readable extraction warnings."""

    INSUFFICIENT_TEXT = "insufficient_text"
    PAGE_EXTRACTION_FAILED = "page_extraction_failed"
    PDF_TABLE_STRUCTURE_NOT_PRESERVED = "pdf_table_structure_not_preserved"
    HEADERS_NOT_EXTRACTED = "headers_not_extracted"
    FOOTERS_NOT_EXTRACTED = "footers_not_extracted"
    FOOTNOTES_NOT_EXTRACTED = "footnotes_not_extracted"
    ENDNOTES_NOT_EXTRACTED = "endnotes_not_extracted"
    COMMENTS_NOT_EXTRACTED = "comments_not_extracted"
    DRAWINGS_NOT_EXTRACTED = "drawings_not_extracted"
    TEXT_BOXES_NOT_EXTRACTED = "text_boxes_not_extracted"
    NESTED_TABLES_NOT_EXTRACTED = "nested_tables_not_extracted"
    UNSUPPORTED_BODY_CONTENT_NOT_EXTRACTED = "unsupported_body_content_not_extracted"
    FORMULA_CACHED_VALUE_MISSING = "formula_cached_value_missing"
    FORMULA_DEFINITION_UNAVAILABLE = "formula_definition_unavailable"
    SPREADSHEET_DRAWINGS_NOT_EXTRACTED = "spreadsheet_drawings_not_extracted"
    SPREADSHEET_COMMENTS_NOT_EXTRACTED = "spreadsheet_comments_not_extracted"
    FOOTNOTE_PROVENANCE_UNREVIEWED = "footnote_provenance_unreviewed"
    CORRUPTED_UNICODE = "corrupted_unicode"
    SPREADSHEET_ERROR_VALUE = "spreadsheet_error_value"
    AMBIGUOUS_SPREADSHEET_STRUCTURE = "ambiguous_spreadsheet_structure"
    ANCILLARY_PROVENANCE_UNREVIEWED = "ancillary_provenance_unreviewed"
    NUMBER_FORMAT_UNAVAILABLE = "number_format_unavailable"


class ErrorCategory(StrEnum):
    """Sanitized extraction failure categories."""

    EMPTY_FILE = "empty_file"
    UNSUPPORTED_FORMAT = "unsupported_format"
    FILE_UNREADABLE = "file_unreadable"
    CORRUPT_DOCUMENT = "corrupt_document"
    ENCRYPTED_DOCUMENT = "encrypted_document"
    LIMIT_EXCEEDED = "limit_exceeded"
    MISSING_DEPENDENCY = "missing_dependency"
    EXTRACTION_FAILED = "extraction_failed"
    SYMLINK_NOT_ALLOWED = "symlink_not_allowed"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Format-specific provenance without exposing source content."""

    page_number: int | None = None
    block_index: int | None = None
    sheet_index: int | None = None
    sheet_name: str | None = None
    cell_coordinate: str | None = None
    table_index: int | None = None
    row_index: int | None = None
    column_index: int | None = None
    part_uri: str | None = None
    xml_path: tuple[int, ...] | None = None  # Child ordinals from the named part's XML root.
    note_id: str | None = None
    relationship_id: str | None = None


@dataclass(frozen=True, slots=True)
class TextBlock:
    """An ordered block of extracted text."""

    order: int
    text: str
    source: SourceLocation
    kind: str = field(default="text", init=False)


@dataclass(frozen=True, slots=True)
class TableCell:
    """A logical table cell, emitted once even when it spans grid positions."""

    row_index: int
    column_index: int
    text: str
    source: SourceLocation
    row_span: int = 1
    column_span: int = 1


@dataclass(frozen=True, slots=True)
class TableRow:
    """Logical table cells anchored in one row."""

    row_index: int
    cells: tuple[TableCell, ...]


@dataclass(frozen=True, slots=True)
class TableBlock:
    """A structured table in document body order."""

    order: int
    table_index: int
    rows: tuple[TableRow, ...]
    source: SourceLocation
    name: str | None = None
    reference: str | None = None
    header_row_indices: tuple[int, ...] = ()
    kind: str = field(default="table", init=False)


DocumentBlock = TextBlock | TableBlock


@dataclass(frozen=True, slots=True)
class SpreadsheetCell:
    """A meaningful stored spreadsheet cell."""

    coordinate: str
    row_index: int
    column_index: int
    value: str | None
    formula: str | None
    cached_value: str | None
    data_type: str | None
    source: SourceLocation
    raw_value: str | None = None
    number_format: str | None = None
    style_index: int | None = None
    has_formula: bool = False
    formula_attributes: tuple[tuple[str, str], ...] = ()
    number_format_id: int | None = None


@dataclass(frozen=True, slots=True)
class SpreadsheetTable:
    """Relevant metadata for an XLSX table definition."""

    name: str | None
    display_name: str | None
    reference: str
    columns: tuple[str, ...]
    header_row_count: int = 1
    totals_row_count: int = 0


@dataclass(frozen=True, slots=True)
class SpreadsheetSheet:
    """Sparse, ordered worksheet representation."""

    index: int
    name: str
    state: str
    cells: tuple[SpreadsheetCell, ...]
    merged_ranges: tuple[str, ...]
    tables: tuple[SpreadsheetTable, ...]
    date_system: str = "1900"


@dataclass(frozen=True, slots=True)
class NoteReference:
    """An actual OOXML reference to a note, including repeated references."""

    source: SourceLocation
    target_part_uri: str | None
    note_id: str


@dataclass(frozen=True, slots=True)
class ExtractionWarning:
    """Sanitized warning suitable for metrics and persisted summaries."""

    code: WarningCode
    severity: WarningSeverity
    count: int = 1
    source: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Complete in-memory result for one isolated document extraction."""

    schema_version: str
    document_format: DocumentFormat | None
    status: ExtractionStatus
    source_sha256: str | None
    source_size_bytes: int | None
    blocks: tuple[DocumentBlock, ...] = ()
    sheets: tuple[SpreadsheetSheet, ...] = ()
    warnings: tuple[ExtractionWarning, ...] = ()
    error_category: ErrorCategory | None = None
    note_references: tuple[NoteReference, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible representation."""

        value = _to_primitive(self)
        if not isinstance(value, dict):  # pragma: no cover - type invariant
            raise TypeError("ExtractionResult serialization did not produce a mapping")
        return value


def _to_primitive(value: Any) -> Any:
    if isinstance(value, StrEnum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, tuple | list):
        return [_to_primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_primitive(item) for key, item in value.items()}
    return value
