"""Synthetic QG-02 probes, not independent multilingual quality evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from doclens_ai.chunking import (
    CHUNKING_SCHEMA_VERSION,
    ChunkingConfig,
    ChunkingReason,
    ChunkingStatus,
    ChunkingStrategy,
    chunk_document,
)
from doclens_ai.extraction.models import (
    DocumentFormat,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    SpreadsheetCell,
    SpreadsheetSheet,
    TextBlock,
)


def _spreadsheet(literal: str, field: str) -> tuple[ExtractionResult, str, SourceLocation]:
    # This digest identifies synthetic fixture bytes, not a claimed XLSX archive.
    fixture = json.dumps({field: literal}, ensure_ascii=False).encode()
    source = SourceLocation(
        sheet_index=0, sheet_name="Synthetic", cell_coordinate="A1", row_index=0, column_index=0
    )
    cell = SpreadsheetCell(
        coordinate="A1",
        row_index=0,
        column_index=0,
        value=literal if field == "value" else None,
        formula=literal if field == "formula" else None,
        cached_value=literal if field == "cached_value" else None,
        data_type=None,
        source=source,
    )
    if field == "formula":
        rendered = f"A1\tvalue=<missing>\tformula={literal}"
    elif field == "cached_value":
        rendered = f"A1\tvalue={literal}\tformula=<unavailable-shared>"
    else:
        rendered = f"A1\tvalue={literal}"
    return (
        ExtractionResult(
            schema_version="1.0",
            document_format=DocumentFormat.XLSX,
            status=ExtractionStatus.SUCCESS,
            source_sha256=hashlib.sha256(fixture).hexdigest(),
            source_size_bytes=len(fixture),
            sheets=(
                SpreadsheetSheet(
                    index=0,
                    name="Synthetic",
                    state="visible",
                    cells=(cell,),
                    merged_ranges=(),
                    tables=(),
                ),
            ),
        ),
        rendered,
        source,
    )


@pytest.mark.parametrize("strategy", list(ChunkingStrategy))
@pytest.mark.parametrize("field", ["value", "formula", "cached_value"])
@pytest.mark.parametrize("literal", ['"not\r\nне\rжоқ"', " 0007\t\r\n "])
def test_xlsx_cleaning_preserves_literal_line_endings_and_whitespace(
    strategy: ChunkingStrategy,
    field: str,
    literal: str,
) -> None:
    extraction, rendered, source = _spreadsheet(literal, field)
    before = repr(extraction)
    config = ChunkingConfig(strategy=strategy, max_characters=512, overlap_characters=0)
    outcome = chunk_document(extraction, document_id="synthetic", config=config)
    assert outcome.status is ChunkingStatus.CHUNKED
    assert len(outcome.chunks) == 1
    assert outcome.chunks[0].text == rendered
    (span,) = outcome.chunks[0].provenance
    assert span.text_block_map is None
    assert span.source == source
    assert (span.source_start, span.source_end, span.source_length) == (
        0,
        len(rendered),
        len(rendered),
    )
    assert repr(extraction) == before
    assert outcome == chunk_document(extraction, document_id="synthetic", config=config)


FACTUAL_LITERALS = (
    "-001.2300 +0.0500 −12,3400",
    "0000123 ID-00/007 AB_001",
    "2026-10-21 01.02.2026 02/03/2026",
    "-0.50% +12,00 % 003.00 kg 5 м² ₸ USD",
    "не разрешено; нет; нельзя",
    "рұқсат жоқ; емес; болмайды",
    "not allowed; no; never",
    '=IF(A1<>0,"not","no")',
    "https://example.invalid/0007?q=-0.0500#ID-01",
)


@pytest.mark.parametrize("strategy", list(ChunkingStrategy))
@pytest.mark.parametrize("field", ["value", "formula", "cached_value"])
@pytest.mark.parametrize("literal", FACTUAL_LITERALS)
def test_xlsx_literal_offsets_survive_overlapping_chunks(
    strategy: ChunkingStrategy,
    field: str,
    literal: str,
) -> None:
    # Include CRLF so following offsets must count both original characters.
    extraction, rendered, source = _spreadsheet("\r\n" + literal + "\r", field)
    config = ChunkingConfig(strategy=strategy, max_characters=13, overlap_characters=3)
    outcome = chunk_document(extraction, document_id="synthetic", config=config)
    assert outcome.status is ChunkingStatus.CHUNKED
    restored: dict[int, str] = {}
    for chunk in outcome.chunks:
        (span,) = chunk.provenance
        assert span.text_block_map is None
        assert span.unit_id == "sheet:0:cell:A1"
        assert span.source == source
        assert chunk.source_sha256 == extraction.source_sha256
        assert 0 <= span.source_start < span.source_end <= span.source_length == len(rendered)
        assert chunk.text == rendered[span.source_start : span.source_end]
        for position, character in enumerate(chunk.text, span.source_start):
            assert restored.setdefault(position, character) == character
    assert "".join(restored[i] for i in range(len(rendered))) == rendered
    assert outcome.covered_source_characters == len(rendered)
    assert outcome == chunk_document(extraction, document_id="synthetic", config=config)


@pytest.mark.parametrize("document_format", [DocumentFormat.PDF, DocumentFormat.DOCX])
@pytest.mark.parametrize("literal", FACTUAL_LITERALS)
def test_existing_prose_cleaning_preserves_factual_tokens(
    document_format: DocumentFormat,
    literal: str,
) -> None:
    original = " \r\n" + literal + "\r\n "
    source = (
        SourceLocation(page_number=1, block_index=0)
        if document_format is DocumentFormat.PDF
        else SourceLocation(block_index=0, part_uri="/word/document.xml")
    )
    extraction = ExtractionResult(
        schema_version="1.0",
        document_format=document_format,
        status=ExtractionStatus.SUCCESS,
        source_sha256=hashlib.sha256(original.encode()).hexdigest(),
        source_size_bytes=len(original.encode()),
        blocks=(TextBlock(order=0, text=original, source=source),),
    )
    outcome = chunk_document(
        extraction,
        document_id="synthetic-prose",
        config=ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE),
    )
    assert outcome.status is ChunkingStatus.CHUNKED
    assert outcome.chunks[0].text == literal
    (span,) = outcome.chunks[0].provenance
    # These existing offsets address the normalized source unit, not RAW bytes.
    assert (span.source_start, span.source_end, span.source_length) == (
        0,
        len(literal),
        len(literal),
    )
    assert span.source == source
    assert extraction.blocks[0].text == original


def test_cleaned_identity_is_source_scoped_and_missing_identity_emits_no_references() -> None:
    extraction, _, _ = _spreadsheet('"0001\r\nnot"', "formula")
    config = ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE)
    first = chunk_document(extraction, document_id="synthetic", config=config)
    changed = chunk_document(
        replace(extraction, source_sha256="b" * 64),
        document_id="synthetic",
        config=config,
    )
    assert first.status is changed.status is ChunkingStatus.CHUNKED
    assert first.chunks[0].text == changed.chunks[0].text
    assert first.chunks[0].chunk_id != changed.chunks[0].chunk_id
    assert changed.chunks[0].source_sha256 == "b" * 64
    for missing, document_id in (
        (replace(extraction, source_sha256=None), "synthetic"),
        (extraction, " "),
    ):
        outcome = chunk_document(missing, document_id=document_id, config=config)
        assert outcome.status is ChunkingStatus.SKIPPED
        assert outcome.reason is ChunkingReason.MISSING_DOCUMENT_IDENTITY
        assert outcome.chunks == ()


def test_literal_preservation_changes_the_default_configuration_identity() -> None:
    current = ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE)
    assert current.version == CHUNKING_SCHEMA_VERSION
    assert current.fingerprint() != replace(current, version="1.1").fingerprint()
