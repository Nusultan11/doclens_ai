"""Synthetic, independently checked TextBlock code-point provenance."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace

import pytest

from doclens_ai.chunking import (
    CHUNKING_SCHEMA_VERSION,
    ChunkingConfig,
    ChunkingOutcome,
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
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
)


def _extraction(document_format: DocumentFormat, texts: tuple[str, ...]) -> ExtractionResult:
    fixture = json.dumps(texts, ensure_ascii=False).encode()
    return ExtractionResult(
        schema_version="1.0",
        document_format=document_format,
        status=ExtractionStatus.SUCCESS,
        source_sha256=hashlib.sha256(fixture).hexdigest(),
        source_size_bytes=len(fixture),
        blocks=tuple(
            TextBlock(
                order=i,
                text=text,
                source=SourceLocation(page_number=1, block_index=i)
                if document_format is DocumentFormat.PDF
                else SourceLocation(block_index=i, part_uri="/word/document.xml", xml_path=(0, i)),
            )
            for i, text in enumerate(texts)
        ),
    )


def _oracle(original: str) -> tuple[str, list[tuple[int, int]]]:
    # Independent token-based oracle: no production normalization/map helpers.
    tokens = [
        ("\n" if m.group() in {"\r", "\r\n"} else m.group(), m.span())
        for m in re.finditer(r"\r\n|[\s\S]", original)
    ]
    while tokens and tokens[0][0].isspace():
        tokens.pop(0)
    while tokens and tokens[-1][0].isspace():
        tokens.pop()
    return "".join(char for char, _ in tokens), [bounds for _, bounds in tokens]


def _verify(outcome: ChunkingOutcome, extraction: ExtractionResult) -> None:
    covered = {i: set() for i, block in enumerate(extraction.blocks) if _oracle(block.text)[0]}
    for chunk in outcome.chunks:
        emitted: set[int] = set()
        assert chunk.source_sha256 == extraction.source_sha256
        for span in chunk.provenance:
            mapping = getattr(span, "text_block_map", None)
            assert mapping is not None, "TextBlock original-offset mapping is missing"
            block = extraction.blocks[span.source.block_index]
            assert span.source == block.source
            normalized, expected = _oracle(block.text)
            assert mapping.offset_basis == "text_block_code_points"
            assert mapping.original_text_length == len(block.text)
            assert mapping.original_text_sha256 == hashlib.sha256(block.text.encode()).hexdigest()
            assert 0 <= mapping.chunk_start < mapping.chunk_end <= len(chunk.text)
            assert mapping.chunk_end - mapping.chunk_start == span.source_end - span.source_start
            assert (
                chunk.text[mapping.chunk_start : mapping.chunk_end]
                == normalized[span.source_start : span.source_end]
            )
            cursor = span.source_start
            for part in mapping.ranges:
                assert part.normalized_start == cursor
                assert cursor < part.normalized_end <= span.source_end <= len(normalized)
                assert 0 <= part.original_start < part.original_end <= len(block.text)
                width = part.normalized_end - part.normalized_start
                original_width = part.original_end - part.original_start
                assert original_width == width or (width, original_width) == (1, 2)
                for index in range(part.normalized_start, part.normalized_end):
                    bounds = (
                        part.original_start + index - part.normalized_start,
                        part.original_start + index - part.normalized_start + 1,
                    )
                    if original_width != width:
                        bounds = (part.original_start, part.original_end)
                    assert bounds == expected[index]
                    position = mapping.chunk_start + index - span.source_start
                    assert position not in emitted
                    emitted.add(position)
                    covered[span.source.block_index].add(index)
                cursor = part.normalized_end
            assert cursor == span.source_end
        # Rendering separators are not represented as original TextBlock characters.
        assert all(char.isspace() for i, char in enumerate(chunk.text) if i not in emitted)
    assert all(
        indices == set(range(len(_oracle(extraction.blocks[i].text)[0])))
        for i, indices in covered.items()
    )


@pytest.mark.parametrize("strategy", list(ChunkingStrategy))
@pytest.mark.parametrize("document_format", [DocumentFormat.PDF, DocumentFormat.DOCX])
def test_original_offsets_are_recoverable_after_trimming_and_crlf(
    strategy: ChunkingStrategy,
    document_format: DocumentFormat,
) -> None:
    extraction = _extraction(document_format, (" \tA\r\nB\rC  ",))
    outcome = chunk_document(
        extraction,
        document_id="synthetic",
        config=ChunkingConfig(
            strategy=strategy,
            max_characters=4,
            overlap_characters=1,
        ),
    )
    assert outcome.status is ChunkingStatus.CHUNKED
    assert [chunk.text for chunk in outcome.chunks] == ["A\nB\n", "\nC"]
    assert [
        (span.source_start, span.source_end)
        for chunk in outcome.chunks
        for span in chunk.provenance
    ] == [(0, 4), (3, 5)]
    if strategy is ChunkingStrategy.STRUCTURE_AWARE:
        assert all(chunk.split_oversized_element for chunk in outcome.chunks)
    _verify(outcome, extraction)


@pytest.mark.parametrize("strategy", list(ChunkingStrategy))
@pytest.mark.parametrize("document_format", [DocumentFormat.PDF, DocumentFormat.DOCX])
@pytest.mark.parametrize("maximum,overlap", [(1, 0), (7, 2), (120, 0)])
@pytest.mark.parametrize(
    "original",
    [
        "plain −001.2300 0007 5% kg",
        "\r\n\tҚазақ емес\rРусский не\r\nEN not\n \u2003",
        " \u00a0😀е\u0301\r\n𐐀\rZ\t",
        "\n\r\r\nA\r\n\rB\rC\r\n\r\n",
    ],
)
def test_every_emitted_character_has_exact_original_bounds(
    strategy: ChunkingStrategy,
    document_format: DocumentFormat,
    maximum: int,
    overlap: int,
    original: str,
) -> None:
    extraction = _extraction(document_format, (original,))
    before = repr(extraction)
    config = ChunkingConfig(strategy=strategy, max_characters=maximum, overlap_characters=overlap)
    first = chunk_document(extraction, document_id="synthetic", config=config)
    assert first.status is ChunkingStatus.CHUNKED
    _verify(first, extraction)
    assert first == chunk_document(extraction, document_id="synthetic", config=config)
    assert repr(extraction) == before


@pytest.mark.parametrize("strategy", list(ChunkingStrategy))
@pytest.mark.parametrize("document_format", [DocumentFormat.PDF, DocumentFormat.DOCX])
def test_empty_blocks_and_rendering_separators_have_no_invented_mapping(
    strategy: ChunkingStrategy,
    document_format: DocumentFormat,
) -> None:
    config = ChunkingConfig(strategy=strategy, max_characters=100, overlap_characters=0)
    extraction = _extraction(document_format, ("", " \r\n\t\u2003", " A\r\nB ", "\rC "))
    outcome = chunk_document(extraction, document_id="synthetic", config=config)
    assert outcome.status is ChunkingStatus.CHUNKED
    assert {span.source.block_index for chunk in outcome.chunks for span in chunk.provenance} == {
        2,
        3,
    }
    _verify(outcome, extraction)
    empty = chunk_document(
        _extraction(document_format, ("", " \r\n\t")), document_id="empty", config=config
    )
    assert (empty.status, empty.reason, empty.chunks) == (
        ChunkingStatus.SKIPPED,
        ChunkingReason.EMPTY_CONTENT,
        (),
    )


def test_original_text_identity_rejects_wrong_original_and_affects_chunk_identity() -> None:
    extraction = _extraction(DocumentFormat.PDF, (" A\r\nB ",))
    config = ChunkingConfig(strategy=ChunkingStrategy.FIXED_SIZE)
    first = chunk_document(extraction, document_id="synthetic", config=config)
    _verify(first, extraction)
    wrong = replace(extraction, blocks=(replace(extraction.blocks[0], text=" A\nB  "),))
    with pytest.raises(AssertionError):
        _verify(first, wrong)
    changed = chunk_document(wrong, document_id="synthetic", config=config)
    assert changed.chunks[0].text == first.chunks[0].text
    assert changed.chunks[0].chunk_id != first.chunks[0].chunk_id
    missing = chunk_document(
        replace(extraction, source_sha256=None), document_id="synthetic", config=config
    )
    assert (missing.status, missing.reason, missing.chunks) == (
        ChunkingStatus.SKIPPED,
        ChunkingReason.MISSING_DOCUMENT_IDENTITY,
        (),
    )


def test_mapping_is_compressed_and_public_identity_is_versioned() -> None:
    assert CHUNKING_SCHEMA_VERSION == "1.3"
    extraction = _extraction(DocumentFormat.PDF, (" " + "A" * 20_000 + " ",))
    config = ChunkingConfig(strategy=ChunkingStrategy.FIXED_SIZE)
    assert config.fingerprint() != replace(config, version="1.2").fingerprint()
    outcome = chunk_document(extraction, document_id="synthetic", config=config)
    assert outcome.status is ChunkingStatus.CHUNKED
    assert all(
        len(span.text_block_map.ranges) == 1
        for chunk in outcome.chunks
        for span in chunk.provenance
    )


@pytest.mark.parametrize("strategy", list(ChunkingStrategy))
def test_table_and_legacy_spans_explicitly_have_no_textblock_map(
    strategy: ChunkingStrategy,
) -> None:
    from doclens_ai.chunking import ChunkSourceSpan

    source = SourceLocation(block_index=0, table_index=0, row_index=0, column_index=0)
    block = TableBlock(
        order=0,
        table_index=0,
        source=SourceLocation(block_index=0, table_index=0),
        rows=(
            TableRow(
                row_index=0,
                cells=(
                    TableCell(
                        row_index=0,
                        column_index=0,
                        text=" A\r\nB ",
                        source=source,
                    ),
                ),
            ),
        ),
    )
    extraction = replace(_extraction(DocumentFormat.DOCX, ()), blocks=(block,))
    outcome = chunk_document(
        extraction, document_id="synthetic-table", config=ChunkingConfig(strategy=strategy)
    )
    assert outcome.status is ChunkingStatus.CHUNKED
    assert outcome.chunks[0].text == "r1c1[1x1]\tA\nB"
    assert all(span.text_block_map is None for chunk in outcome.chunks for span in chunk.provenance)
    assert ChunkSourceSpan("legacy", source, 0, 1, 1).text_block_map is None


def test_unencodable_original_fails_without_fabricating_mapping() -> None:
    # An invalid Unicode surrogate has no UTF-8 text identity. No chunks escape.
    valid = _extraction(DocumentFormat.PDF, ("valid",))
    extraction = replace(valid, blocks=(replace(valid.blocks[0], text="bad\ud800text"),))
    outcome = chunk_document(
        extraction,
        document_id="synthetic",
        config=ChunkingConfig(strategy=ChunkingStrategy.FIXED_SIZE),
    )
    assert (outcome.status, outcome.reason, outcome.chunks) == (
        ChunkingStatus.FAILED,
        ChunkingReason.CHUNKING_FAILED,
        (),
    )
