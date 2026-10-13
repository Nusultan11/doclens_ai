from __future__ import annotations

from pathlib import Path

import pytest

from doclens_ai.chunking import (
    ChunkingConfig,
    ChunkingReason,
    ChunkingStatus,
    ChunkingStrategy,
    chunk_document,
    chunk_documents,
    evaluate_corpus,
)
from doclens_ai.extraction.models import (
    DocumentFormat,
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    SpreadsheetCell,
    SpreadsheetSheet,
    SpreadsheetTable,
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
)


def _result(
    document_format: DocumentFormat,
    *,
    status: ExtractionStatus = ExtractionStatus.SUCCESS,
    blocks: tuple[TextBlock | TableBlock, ...] = (),
    sheets: tuple[SpreadsheetSheet, ...] = (),
    sha256: str = "a" * 64,
) -> ExtractionResult:
    return ExtractionResult(
        schema_version="1.0",
        document_format=document_format,
        status=status,
        source_sha256=sha256,
        source_size_bytes=100,
        blocks=blocks,
        sheets=sheets,
        error_category=(
            ErrorCategory.CORRUPT_DOCUMENT
            if status is ExtractionStatus.FAILED
            else None
        ),
    )


def _config(
    strategy: ChunkingStrategy,
    *,
    maximum: int = 40,
    overlap: int = 5,
    allow_needs_review: bool = False,
) -> ChunkingConfig:
    return ChunkingConfig(
        strategy=strategy,
        max_characters=maximum,
        overlap_characters=overlap,
        allow_needs_review=allow_needs_review,
    )


def test_pdf_fixed_and_structure_aware_strategies_preserve_provenance() -> None:
    extraction = _result(
        DocumentFormat.PDF,
        blocks=(
            TextBlock(
                order=0,
                text="A" * 20,
                source=SourceLocation(page_number=1, block_index=0),
            ),
            TextBlock(
                order=1,
                text="B" * 20,
                source=SourceLocation(page_number=2, block_index=1),
            ),
        ),
    )

    fixed = chunk_document(
        extraction,
        document_id="document-pdf",
        config=_config(ChunkingStrategy.FIXED_SIZE, maximum=30, overlap=5),
    )
    structured = chunk_document(
        extraction,
        document_id="document-pdf",
        config=_config(ChunkingStrategy.STRUCTURE_AWARE, maximum=30, overlap=5),
    )

    assert fixed.status is ChunkingStatus.CHUNKED
    assert structured.status is ChunkingStatus.CHUNKED
    assert any(
        {span.source.page_number for span in chunk.provenance} == {1, 2}
        for chunk in fixed.chunks
    )
    assert len(structured.chunks) == 2
    assert [
        {span.source.page_number for span in chunk.provenance}
        for chunk in structured.chunks
    ] == [{1}, {2}]
    assert fixed.covered_source_characters == fixed.normalized_source_characters == 40
    assert structured.covered_source_characters == structured.normalized_source_characters == 40


def test_docx_structure_aware_chunks_keep_body_and_table_boundaries() -> None:
    paragraph = TextBlock(
        order=0,
        text="introductory paragraph",
        source=SourceLocation(block_index=0),
    )
    cells = (
        TableCell(
            row_index=0,
            column_index=0,
            text="merged heading",
            row_span=1,
            column_span=2,
            source=SourceLocation(block_index=1, table_index=0, row_index=0, column_index=0),
        ),
        TableCell(
            row_index=1,
            column_index=0,
            text="value",
            source=SourceLocation(block_index=1, table_index=0, row_index=1, column_index=0),
        ),
    )
    table = TableBlock(
        order=1,
        table_index=0,
        rows=(
            TableRow(row_index=0, cells=(cells[0],)),
            TableRow(row_index=1, cells=(cells[1],)),
        ),
        source=SourceLocation(block_index=1, table_index=0),
    )
    extraction = _result(DocumentFormat.DOCX, blocks=(paragraph, table))

    outcome = chunk_document(
        extraction,
        document_id="document-docx",
        config=_config(ChunkingStrategy.STRUCTURE_AWARE, maximum=100, overlap=10),
    )

    assert outcome.status is ChunkingStatus.CHUNKED
    assert len(outcome.chunks) == 2
    assert outcome.chunks[0].provenance[0].source.block_index == 0
    assert {span.source.table_index for span in outcome.chunks[1].provenance} == {0}
    assert "r1c1[1x2]" in outcome.chunks[1].text
    assert outcome.covered_source_characters == outcome.normalized_source_characters


def test_xlsx_chunking_keeps_rows_cells_tables_and_formula_policy() -> None:
    cells = (
        SpreadsheetCell(
            coordinate="A1",
            row_index=0,
            column_index=0,
            value="2",
            formula=None,
            cached_value=None,
            data_type="n",
            source=SourceLocation(
                sheet_index=0,
                sheet_name="Sensitive Sheet",
                cell_coordinate="A1",
            ),
        ),
        SpreadsheetCell(
            coordinate="B1",
            row_index=0,
            column_index=1,
            value="2",
            formula="1+1",
            cached_value="2",
            data_type="n",
            source=SourceLocation(
                sheet_index=0,
                sheet_name="Sensitive Sheet",
                cell_coordinate="B1",
            ),
        ),
        SpreadsheetCell(
            coordinate="C1",
            row_index=0,
            column_index=2,
            value="3",
            formula=None,
            cached_value="3",
            data_type="n",
            source=SourceLocation(
                sheet_index=0,
                sheet_name="Sensitive Sheet",
                cell_coordinate="C1",
            ),
        ),
        SpreadsheetCell(
            coordinate="D1",
            row_index=0,
            column_index=3,
            value=None,
            formula="1/0",
            cached_value=None,
            data_type="e",
            source=SourceLocation(
                sheet_index=0,
                sheet_name="Sensitive Sheet",
                cell_coordinate="D1",
            ),
        ),
    )
    sheet = SpreadsheetSheet(
        index=0,
        name="Sensitive Sheet",
        state="visible",
        cells=cells,
        merged_ranges=("A2:B2",),
        tables=(
            SpreadsheetTable(
                name="Table1",
                display_name="MetricsTable",
                reference="A1:D1",
                columns=("a", "b", "c", "d"),
            ),
        ),
    )
    second_sheet = SpreadsheetSheet(
        index=1,
        name="Second",
        state="hidden",
        cells=(
            SpreadsheetCell(
                coordinate="A1",
                row_index=0,
                column_index=0,
                value="separate",
                formula=None,
                cached_value=None,
                data_type="inlineStr",
                source=SourceLocation(
                    sheet_index=1,
                    sheet_name="Second",
                    cell_coordinate="A1",
                ),
            ),
        ),
        merged_ranges=(),
        tables=(),
    )
    extraction = _result(DocumentFormat.XLSX, sheets=(sheet, second_sheet))

    outcome = chunk_document(
        extraction,
        document_id="document-xlsx",
        config=_config(ChunkingStrategy.STRUCTURE_AWARE, maximum=500, overlap=20),
    )

    assert outcome.status is ChunkingStatus.CHUNKED
    combined = "\n".join(chunk.text for chunk in outcome.chunks)
    assert "formula=1+1" in combined
    assert "formula=<unavailable-shared>" in combined
    assert "value=<missing>\tformula=1/0" in combined
    assert "table=MetricsTable" in combined
    assert "merged_range=A2:B2" in combined
    assert all(
        len({span.source.sheet_index for span in chunk.provenance}) == 1
        for chunk in outcome.chunks
    )


def test_oversized_table_cell_is_split_without_losing_table_provenance() -> None:
    cell = TableCell(
        row_index=0,
        column_index=0,
        text="table-value-" * 12,
        source=SourceLocation(block_index=0, table_index=0, row_index=0, column_index=0),
    )
    extraction = _result(
        DocumentFormat.DOCX,
        blocks=(
            TableBlock(
                order=0,
                table_index=0,
                rows=(TableRow(row_index=0, cells=(cell,)),),
                source=SourceLocation(block_index=0, table_index=0),
            ),
        ),
    )

    outcome = chunk_document(
        extraction,
        document_id="long-table",
        config=_config(ChunkingStrategy.STRUCTURE_AWARE, maximum=25, overlap=5),
    )

    assert outcome.status is ChunkingStatus.CHUNKED
    assert all(len(chunk.text) <= 25 for chunk in outcome.chunks)
    assert all(chunk.split_oversized_element for chunk in outcome.chunks)
    assert all(
        span.source.table_index == 0
        for chunk in outcome.chunks
        for span in chunk.provenance
    )
    assert outcome.covered_source_characters == outcome.normalized_source_characters


@pytest.mark.parametrize(
    "strategy",
    [ChunkingStrategy.FIXED_SIZE, ChunkingStrategy.STRUCTURE_AWARE],
)
def test_long_elements_are_split_with_bounded_overlap_and_full_coverage(
    strategy: ChunkingStrategy,
) -> None:
    extraction = _result(
        DocumentFormat.PDF,
        blocks=(
            TextBlock(
                order=0,
                text="0123456789" * 10,
                source=SourceLocation(page_number=1, block_index=0),
            ),
        ),
    )

    outcome = chunk_document(
        extraction,
        document_id="document-long",
        config=_config(strategy, maximum=25, overlap=5),
    )

    assert outcome.status is ChunkingStatus.CHUNKED
    assert len(outcome.chunks) == 5
    assert all(len(chunk.text) <= 25 for chunk in outcome.chunks)
    assert outcome.covered_source_characters == outcome.normalized_source_characters == 100
    assert outcome.emitted_source_characters == 120
    if strategy is ChunkingStrategy.STRUCTURE_AWARE:
        assert all(chunk.split_oversized_element for chunk in outcome.chunks)


def test_empty_content_and_extraction_statuses_are_gated() -> None:
    empty = _result(
        DocumentFormat.DOCX,
        blocks=(
            TextBlock(order=0, text=" \n ", source=SourceLocation(block_index=0)),
        ),
    )
    needs_review = _result(
        DocumentFormat.PDF,
        status=ExtractionStatus.NEEDS_REVIEW,
        blocks=(
            TextBlock(order=0, text="review me", source=SourceLocation(page_number=1)),
        ),
    )
    failed = _result(DocumentFormat.PDF, status=ExtractionStatus.FAILED)

    empty_outcome = chunk_document(
        empty,
        document_id="empty",
        config=_config(ChunkingStrategy.FIXED_SIZE),
    )
    review_outcome = chunk_document(
        needs_review,
        document_id="review",
        config=_config(ChunkingStrategy.FIXED_SIZE),
    )
    allowed_review = chunk_document(
        needs_review,
        document_id="review",
        config=_config(
            ChunkingStrategy.FIXED_SIZE,
            allow_needs_review=True,
        ),
    )
    failed_outcome = chunk_document(
        failed,
        document_id="failed",
        config=_config(ChunkingStrategy.FIXED_SIZE),
    )

    assert (empty_outcome.status, empty_outcome.reason) == (
        ChunkingStatus.SKIPPED,
        ChunkingReason.EMPTY_CONTENT,
    )
    assert (review_outcome.status, review_outcome.reason) == (
        ChunkingStatus.SKIPPED,
        ChunkingReason.EXTRACTION_NEEDS_REVIEW,
    )
    assert allowed_review.status is ChunkingStatus.CHUNKED
    assert (failed_outcome.status, failed_outcome.reason) == (
        ChunkingStatus.SKIPPED,
        ChunkingReason.EXTRACTION_FAILED,
    )


def test_results_and_chunk_identities_are_deterministic_and_config_scoped() -> None:
    extraction = _result(
        DocumentFormat.DOCX,
        blocks=(
            TextBlock(
                order=0,
                text="deterministic content " * 8,
                source=SourceLocation(block_index=0),
            ),
        ),
    )
    config = _config(ChunkingStrategy.FIXED_SIZE, maximum=50, overlap=10)

    first = chunk_document(extraction, document_id="stable-document", config=config)
    second = chunk_document(extraction, document_id="stable-document", config=config)
    changed = chunk_document(
        extraction,
        document_id="stable-document",
        config=_config(ChunkingStrategy.FIXED_SIZE, maximum=51, overlap=10),
    )

    assert first == second
    assert first.deterministic_fingerprint() == second.deterministic_fingerprint()
    assert [chunk.chunk_id for chunk in first.chunks] != [
        chunk.chunk_id for chunk in changed.chunks
    ]
    assert all(chunk.document_id == "stable-document" for chunk in first.chunks)
    assert all(chunk.config_fingerprint == config.fingerprint() for chunk in first.chunks)


def test_document_failure_is_isolated_from_following_document() -> None:
    malformed = _result(DocumentFormat.PDF)
    object.__setattr__(malformed, "blocks", (object(),))
    valid = _result(
        DocumentFormat.PDF,
        blocks=(
            TextBlock(order=0, text="valid text", source=SourceLocation(page_number=1)),
        ),
        sha256="b" * 64,
    )

    outcomes = chunk_documents(
        (("bad-document", malformed), ("good-document", valid)),
        config=_config(ChunkingStrategy.FIXED_SIZE),
    )

    assert (outcomes[0].status, outcomes[0].reason) == (
        ChunkingStatus.FAILED,
        ChunkingReason.CHUNKING_FAILED,
    )
    assert outcomes[1].status is ChunkingStatus.CHUNKED
    assert {chunk.document_id for chunk in outcomes[1].chunks} == {"good-document"}


def test_offline_evaluation_is_deterministic_private_and_isolates_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "identifying-name.pdf").write_bytes(b"placeholder")
    (corpus / "broken-sensitive.docx").write_bytes(b"placeholder")
    valid = _result(
        DocumentFormat.PDF,
        blocks=(
            TextBlock(
                order=0,
                text="TOP_SECRET_CHUNK_CONTENT",
                source=SourceLocation(page_number=1),
            ),
        ),
    )
    calls: list[str] = []

    def fake_extract(path: Path, *, limits: object) -> ExtractionResult:
        calls.append(path.suffix)
        if path.suffix == ".docx":
            raise RuntimeError("PRIVATE_EXTRACTOR_DETAIL")
        return valid

    monkeypatch.setattr("doclens_ai.chunking.core.extract_file", fake_extract)
    first_output = tmp_path / "output-one"
    second_output = tmp_path / "output-two"

    first = evaluate_corpus(corpus, first_output, measure_latency=False)
    second = evaluate_corpus(corpus, second_output, measure_latency=False)

    assert first == second
    assert calls == [".docx", ".pdf", ".docx", ".pdf"]
    assert first["deterministic_report_fingerprint"] == second[
        "deterministic_report_fingerprint"
    ]
    for strategy in ChunkingStrategy:
        aggregate = first["strategies"][strategy.value]
        assert aggregate["document_status_counts"] == {"chunked": 1, "skipped": 1}
        assert aggregate["normalized_content_coverage"] == 1.0
        assert aggregate["provenance_coverage"] == 1.0
        assert aggregate["oversized_chunk_count"] == 0

    persisted = "\n".join(
        path.read_text(encoding="utf-8") for path in first_output.iterdir()
    )
    for forbidden in (
        "TOP_SECRET_CHUNK_CONTENT",
        "identifying-name",
        "broken-sensitive",
        "Sensitive Sheet",
        "PRIVATE_EXTRACTOR_DETAIL",
    ):
        assert forbidden not in persisted


@pytest.mark.parametrize(
    ("maximum", "overlap"),
    [(0, 0), (10, -1), (10, 10), (10, 11)],
)
def test_invalid_chunking_configuration_is_rejected(maximum: int, overlap: int) -> None:
    with pytest.raises(ValueError):
        _config(
            ChunkingStrategy.FIXED_SIZE,
            maximum=maximum,
            overlap=overlap,
        )
