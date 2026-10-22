"""Native extraction to DocumentIR, without upgrading parser success to trust."""

from __future__ import annotations

from doclens_ai.extraction.ir import (
    CellElement,
    DocumentElement,
    DocumentIR,
    Issue,
    Provenance,
    Relation,
    SourceIdentity,
    TableElement,
    TextElement,
)
from doclens_ai.extraction.models import ExtractionResult, ExtractionStatus, TableBlock


def adapt_native(result: ExtractionResult, *, provenance: Provenance) -> DocumentIR:
    """Keep exact native strings/locators and full v1 metadata as observations.

    No bbox, section, header, unit or cached value is inferred. A SUCCESS native
    result is still unverified. Only declared table containment is translated.
    """
    elements: list[DocumentElement] = []
    relations: list[Relation] = []
    for index, block in enumerate(result.blocks):
        identity = f"block:{index}"
        common = {"id": identity, "source": block.source, "provenance": provenance}
        if not isinstance(block, TableBlock):
            elements.append(TextElement(**common, text=block.text))
            continue
        elements.append(TableElement(**common, name=block.name, reference=block.reference))
        for row_index, row in enumerate(block.rows):
            for cell_index, cell in enumerate(row.cells):
                cell_id = f"{identity}:row:{row_index}:cell:{cell_index}"
                elements.append(
                    CellElement(
                        id=cell_id,
                        source=cell.source,
                        provenance=provenance,
                        text=cell.text,
                        row_index=cell.row_index,
                        column_index=cell.column_index,
                        row_span=cell.row_span,
                        column_span=cell.column_span,
                    )
                )
                relations.append(
                    Relation(
                        id=f"contains:{cell_id}",
                        kind="contains",
                        source_id=identity,
                        target_id=cell_id,
                        provenance=provenance,
                    )
                )
    for sheet_index, sheet in enumerate(result.sheets):
        for index, cell in enumerate(sheet.cells):
            elements.append(
                CellElement(
                    id=f"sheet:{sheet_index}:cell:{index}",
                    source=cell.source,
                    provenance=provenance,
                    text=cell.value,
                    row_index=cell.row_index,
                    column_index=cell.column_index,
                    raw_value=cell.raw_value,
                    data_type=cell.data_type,
                    number_format=cell.number_format,
                    formula=cell.formula,
                    cached_value=cell.cached_value,
                )
            )
    states = {
        ExtractionStatus.SUCCESS: "complete",
        ExtractionStatus.NEEDS_REVIEW: "partial",
        ExtractionStatus.FAILED: "failed",
    }
    issues = tuple(
        Issue(
            code=warning.code.value,
            state="warning",
            source=warning.source,
            reason=warning.severity.value,
        )
        for warning in result.warnings
    )
    if result.error_category is not None:
        issues += (Issue(code=result.error_category.value, state="failed"),)
    return DocumentIR(
        source=SourceIdentity(
            sha256=result.source_sha256,
            size_bytes=result.source_size_bytes,
            document_format=result.document_format,
        ),
        state=states[result.status],
        elements=tuple(elements),
        relations=tuple(relations),
        issues=issues,
        native=result,
    )
