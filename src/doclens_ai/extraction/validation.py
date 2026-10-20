"""Fail-closed evidence checks, separate from a parser's processing outcome."""

from dataclasses import fields

from doclens_ai.extraction.models import (
    DocumentFormat,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TableBlock,
    TextBlock,
    WarningCode,
    WarningSeverity,
)


def evidence_is_indexable(result: ExtractionResult) -> bool:
    """Eligibility is a bounded structural check, never a fidelity certification.

    Native PDF plain text lacks verified table topology/reading order. Keep it
    available for offline inspection, but do not publish it as trusted evidence.
    """
    if result.status is not ExtractionStatus.SUCCESS or result.error_category is not None:
        return False
    if any(
        warning.severity is WarningSeverity.REVIEW
        or warning.code is WarningCode.PDF_TABLE_STRUCTURE_NOT_PRESERVED
        for warning in result.warnings
    ):
        return False
    if result.document_format is DocumentFormat.PDF:
        return False  # No reviewed runtime PDF topology/order mechanism exists yet.
    identities = set()
    for block in result.blocks:
        if not _located(block.source, result.document_format):
            return False
        identity = tuple(getattr(block.source, item.name) for item in fields(block.source))
        if identity in identities:
            return False
        identities.add(identity)
        if isinstance(block, TextBlock):
            if _corrupted(block.text):
                return False
        elif isinstance(block, TableBlock):
            if block.table_index != block.source.table_index:
                return False
            positions = set()
            for row in block.rows:
                for cell in row.cells:
                    if (
                        cell.row_index != row.row_index
                        or cell.row_index != cell.source.row_index
                        or cell.column_index != cell.source.column_index
                        or cell.row_span < 1
                        or cell.column_span < 1
                        or _corrupted(cell.text)
                        or any(
                            getattr(cell.source, key) != getattr(block.source, key)
                            for key in ("part_uri", "page_number", "block_index", "table_index")
                        )
                    ):
                        return False
                    for r in range(cell.row_index, cell.row_index + cell.row_span):
                        for c in range(cell.column_index, cell.column_index + cell.column_span):
                            if (r, c) in positions:
                                return False
                            positions.add((r, c))
    for sheet in result.sheets:
        seen = set()
        for cell in sheet.cells:
            if (
                cell.coordinate in seen
                or cell.source.sheet_index != sheet.index
                or cell.source.sheet_name != sheet.name
                or cell.source.cell_coordinate != cell.coordinate
                or cell.source.row_index != cell.row_index
                or cell.source.column_index != cell.column_index
                or any(_corrupted(value) for value in (cell.value, cell.formula, cell.cached_value))
                or (
                    (cell.has_formula or cell.formula is not None)
                    and (cell.formula is None or cell.cached_value is None)
                )
                or cell.data_type == "e"
            ):
                return False
            seen.add(cell.coordinate)
    return result.document_format is not None


def _located(source: SourceLocation, document_format: DocumentFormat | None) -> bool:
    if document_format is DocumentFormat.PDF:
        return source.page_number is not None and source.page_number >= 1
    if document_format is DocumentFormat.DOCX:
        return (
            source.block_index is not None
            and source.block_index >= 0
            and source.part_uri is not None
            and source.part_uri.startswith("/")
            and source.xml_path is not None
        )
    return False


def _corrupted(value: str | None) -> bool:
    return value is not None and any(
        character == "\ufffd" or 0xD800 <= ord(character) <= 0xDFFF for character in value
    )
