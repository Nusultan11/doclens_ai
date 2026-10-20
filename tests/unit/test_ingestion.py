from __future__ import annotations

import hashlib
import json
from uuid import uuid4

import pytest

from doclens_ai.chunking.models import (
    Chunk,
    ChunkingStrategy,
    ChunkSourceSpan,
)
from doclens_ai.extraction.models import DocumentFormat, SourceLocation
from doclens_ai.services.ingestion import (
    IngestionFailure,
    IngestionFailureCategory,
    IngestionService,
    canonical_chunk_uuid,
    canonicalize_chunk,
)


@pytest.mark.parametrize(
    "source",
    [
        SourceLocation(page_number=2, block_index=1),
        SourceLocation(block_index=3, table_index=1, row_index=2, column_index=4),
        SourceLocation(block_index=0, part_uri="/word/document.xml", xml_path=(0, 1)),
        SourceLocation(
            sheet_index=0,
            sheet_name="Metrics",
            cell_coordinate="B7",
            row_index=6,
            column_index=1,
        ),
    ],
)
def test_canonicalization_is_deterministic_and_preserves_provenance(
    source: SourceLocation,
) -> None:
    run_id = uuid4()
    chunk = Chunk(
        chunk_id=f"chunk-{'a' * 64}",
        document_id=str(uuid4()),
        source_sha256="b" * 64,
        document_format=DocumentFormat.PDF,
        strategy=ChunkingStrategy.STRUCTURE_AWARE,
        config_version="1.0",
        config_fingerprint="c" * 64,
        ordinal=0,
        text="canonical text",
        provenance=(
            ChunkSourceSpan(
                unit_id="unit-1",
                source=source,
                source_start=1,
                source_end=8,
                source_length=14,
            ),
        ),
    )

    first = canonicalize_chunk(run_id, chunk)
    second = canonicalize_chunk(run_id, chunk)

    assert first == second
    assert first.id == canonical_chunk_uuid(run_id, chunk.chunk_id)
    assert first.id != canonical_chunk_uuid(uuid4(), chunk.chunk_id)
    assert first.content_sha256 == hashlib.sha256(chunk.text.encode()).hexdigest()
    assert first.character_count == len(chunk.text)
    assert first.token_count is None
    assert json.loads(json.dumps(first.source_provenance)) == first.source_provenance
    assert first.source_provenance == [
        {
            "unit_id": "unit-1",
            "source": {
                key: value
                for key, value in {
                    "page_number": source.page_number,
                    "block_index": source.block_index,
                    "sheet_index": source.sheet_index,
                    "sheet_name": source.sheet_name,
                    "cell_coordinate": source.cell_coordinate,
                    "table_index": source.table_index,
                    "row_index": source.row_index,
                    "column_index": source.column_index,
                    "part_uri": source.part_uri,
                    "xml_path": list(source.xml_path) if source.xml_path is not None else None,
                }.items()
                if value is not None
            },
            "source_start": 1,
            "source_end": 8,
            "source_length": 14,
            "offset_basis": "rendered_source_unit",
        }
    ]


def test_ingestion_failures_are_sanitized_and_classified() -> None:
    failure = IngestionFailure(
        IngestionFailureCategory.EXTRACTION_FAILED,
        retryable=False,
        document_error_category="corrupt_document",
    )

    assert str(failure) == "extraction_failed"
    assert failure.retryable is False
    assert failure.document_error_category == "corrupt_document"
    assert "document content" not in str(failure)


def test_ingestion_rejects_invalid_download_chunk_size() -> None:
    with pytest.raises(ValueError, match="download chunk size"):
        IngestionService(object(), object(), download_chunk_size=0)  # type: ignore[arg-type]
