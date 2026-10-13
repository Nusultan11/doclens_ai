from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest

from doclens_ai.chunking.models import Chunk, ChunkSourceSpan
from doclens_ai.dense_baseline.embeddings import DenseError
from doclens_ai.dense_baseline.qdrant import QdrantIndex, point_id
from doclens_ai.extraction.models import DocumentFormat, SourceLocation
from doclens_ai.retrieval_baseline.runner import FROZEN_CHUNKING

pytestmark = pytest.mark.integration


@pytest.fixture
def real_index():
    url = os.getenv("TEST_QDRANT_URL")
    if not url:
        pytest.skip("TEST_QDRANT_URL is not configured for a disposable Qdrant")
    index = QdrantIndex(url, "dense_v1_test_" + uuid4().hex, dimensions=2)
    index.create()
    chunks = tuple(
        Chunk(
            f"fixture-chunk-{n}",
            f"fixture-doc-{n}",
            str(n) * 64,
            DocumentFormat.PDF,
            FROZEN_CHUNKING.strategy,
            "1.0",
            FROZEN_CHUNKING.fingerprint(),
            n,
            "synthetic",
            (ChunkSourceSpan("unit", SourceLocation(page_number=1, block_index=0), 0, 9, 9),),
        )
        for n in (1, 2, 3)
    )
    index.upsert(chunks, ((1.0, 0.0), (0.0, 1.0), (1.0, 0.0)))
    try:
        yield index, chunks, url
    finally:
        index.close()


def test_real_qdrant_exact_search_idempotence_and_ties(real_index) -> None:
    index, chunks, _ = real_index
    assert index.verify() == 3
    assert [hit.chunk_id for hit in index.search((1.0, 0.0))] == [
        chunks[0].chunk_id,
        chunks[2].chunk_id,
        chunks[1].chunk_id,
    ]
    index.upsert(chunks, ((1.0, 0.0), (0.0, 1.0), (1.0, 0.0)))
    assert index.verify() == 3
    with pytest.raises(DenseError, match="dimension"):
        index.search((1.0,))


def test_real_qdrant_detects_metadata_corruption(real_index) -> None:
    index, chunks, url = real_index
    response = httpx.post(
        url + f"/collections/{index.collection}/points/payload",
        params={"wait": "true"},
        json={"payload": {"ordinal": 99}, "points": [point_id(chunks[0])]},
    )
    response.raise_for_status()
    with pytest.raises(DenseError, match="metadata"):
        index.verify()


def test_real_qdrant_detects_incomplete_index(real_index) -> None:
    index, chunks, url = real_index
    response = httpx.post(
        url + f"/collections/{index.collection}/points/delete",
        params={"wait": "true"},
        json={"points": [point_id(chunks[0])]},
    )
    response.raise_for_status()
    with pytest.raises(DenseError, match="point count"):
        index.verify()
