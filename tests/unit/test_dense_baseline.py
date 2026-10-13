from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from doclens_ai.chunking.models import Chunk, ChunkSourceSpan
from doclens_ai.dense_baseline.embeddings import (
    DenseError,
    E5Embedder,
    EmbeddingBatch,
    EmbeddingConfig,
    format_input,
    validate_vectors,
)
from doclens_ai.dense_baseline.qdrant import QdrantIndex, point_id, point_payload
from doclens_ai.dense_baseline.runner import rank_diagnostics, rank_queries, verify_reference
from doclens_ai.evaluation.gold import (
    AdjudicationState,
    DatasetSplit,
    EvidenceAnchor,
    EvidenceLocator,
    GoldExample,
    Language,
    QuestionCategory,
    ReviewStatus,
    validate_gold_dataset,
)
from doclens_ai.evaluation.metrics import evaluate_retrieval, load_ranked_results_jsonl
from doclens_ai.extraction.models import DocumentFormat, SourceLocation
from doclens_ai.retrieval_baseline.bm25 import BM25Document, BM25Index
from doclens_ai.retrieval_baseline.runner import FROZEN_CHUNKING, RetrievalCorpus, results_jsonl


def fixture_chunks() -> tuple[Chunk, ...]:
    return tuple(
        Chunk(
            f"fixture-chunk-{number}",
            f"fixture-doc-{number}",
            str(number) * 64,
            DocumentFormat.PDF,
            FROZEN_CHUNKING.strategy,
            "1.0",
            FROZEN_CHUNKING.fingerprint(),
            number,
            "synthetic orchard " + str(number),
            (
                ChunkSourceSpan(
                    "fixture-unit", SourceLocation(page_number=1, block_index=0), 0, 12, 20
                ),
            ),
        )
        for number in (1, 2, 3)
    )


class FakeQdrant:
    def __init__(self) -> None:
        self.created = False
        self.points = {}
        self.dimensions = 2
        self.requests: list[httpx.Request] = []
        self.upsert_status = "completed"

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        if path == "/":
            return httpx.Response(200, json={"version": "1.15.4"})
        if request.method == "DELETE":
            self.created = False
            self.points.clear()
            result = True
        elif path.endswith("/points"):
            for point in body["points"]:
                self.points[point["id"]] = point
            result = {"status": self.upsert_status}
        elif path.endswith("/count"):
            result = {"count": len(self.points)}
        elif path.endswith("/scroll"):
            result = {"points": list(self.points.values()), "next_page_offset": None}
        elif path.endswith("/query"):
            assert "filter" not in body and body["params"] == {"exact": True}
            result = {
                "points": [
                    {
                        "id": identity,
                        "payload": point["payload"],
                        "score": sum(
                            a * b for a, b in zip(body["query"], point["vector"], strict=True)
                        ),
                    }
                    for identity, point in reversed(list(self.points.items()))
                ]
            }
        elif request.method == "PUT":
            self.created = True
            self.dimensions = body["vectors"]["size"]
            result = True
        elif not self.created:
            return httpx.Response(404, json={"status": "not found"})
        else:
            result = {
                "config": {"params": {"vectors": {"size": self.dimensions, "distance": "Cosine"}}}
            }
        return httpx.Response(200, json={"status": "ok", "result": result})


@pytest.fixture
def fake_index():
    server = FakeQdrant()
    with httpx.Client(
        base_url="http://qdrant:6333", transport=httpx.MockTransport(server)
    ) as client:
        index = QdrantIndex("http://qdrant:6333", "dense_v1_fixture", dimensions=2, client=client)
        index.create()
        chunks = fixture_chunks()
        index.upsert(chunks, ((1.0, 0.0), (0.0, 1.0), (1.0, 0.0)))
        index.verify()
        yield index, server, chunks
        index.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"model_id": "other"},
        {"revision": "main"},
        {"revision": "a" * 40},
        {"device": "cuda"},
        {"batch_size": 0},
        {"batch_size": 9},
        {"batch_size": True},
        {"max_tokens": 256},
        {"cpu_threads": 0},
        {"cpu_threads": 9},
    ],
)
def test_embedding_config_validation(kwargs) -> None:
    with pytest.raises(DenseError):
        EmbeddingConfig(**kwargs)


def test_documented_prefixes_and_frozen_configuration() -> None:
    assert format_input("example", "query") == "query: example"
    assert format_input("қазақ", "passage") == "passage: қазақ"
    assert EmbeddingConfig().to_dict()["truncation"] == "right"
    assert EmbeddingConfig().to_dict()["normalization"] == "L2"
    with pytest.raises(DenseError):
        format_input("text", "unknown")


@pytest.mark.parametrize(
    "vectors,count,dimensions",
    [
        ([], 1, 2),
        ([[1.0]], 1, 2),
        ([[1.0, 0.0], [1.0]], 2, 2),
        ([[float("nan"), 0.0]], 1, 2),
        ([[float("inf"), 0.0]], 1, 2),
        ([[0.0, 0.0]], 1, 2),
        ([[1.0, 1.0]], 1, 2),
        ([[True, 0.0]], 1, 2),
        ([["private", 0.0]], 1, 2),
    ],
)
def test_vector_shape_finiteness_and_normalization(vectors, count, dimensions) -> None:
    with pytest.raises(DenseError):
        validate_vectors(vectors, count=count, dimensions=dimensions)
    assert validate_vectors([[1.0, 0.0]], count=1, dimensions=2) == ((1.0, 0.0),)
    assert validate_vectors([], count=0, dimensions=2) == ()


def test_model_load_and_inference_failure_are_sanitized(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("doclens_ai.dense_baseline.embeddings.MODEL_FILE_HASHES", {})

    def failing(*args, **kwargs):
        raise RuntimeError("synthetic private input")

    monkeypatch.setattr("doclens_ai.dense_baseline.embeddings._load_local", failing)
    with pytest.raises(DenseError, match="local model load failed") as exc:
        E5Embedder(tmp_path)
    assert "private" not in str(exc.value)
    embedder = object.__new__(E5Embedder)
    embedder.config = EmbeddingConfig()
    embedder.dimensions = 2
    embedder._tokenizer = failing
    with pytest.raises(DenseError, match="embedding inference") as exc:
        embedder.encode(["private"], kind="query")
    assert "private" not in str(exc.value)


def test_point_identity_and_payload_preserve_source_not_content() -> None:
    chunk = fixture_chunks()[0]
    assert point_id(chunk) == point_id(replace(chunk))
    assert point_id(chunk) != point_id(replace(chunk, source_sha256="a" * 64))
    assert point_id(chunk) != point_id(replace(chunk, chunk_id="different"))
    assert point_payload(chunk)["source_sha256"] == chunk.source_sha256
    assert point_payload(chunk)["chunking_fingerprint"] == chunk.config_fingerprint
    assert "synthetic orchard" not in json.dumps(point_payload(chunk))
    assert "text" not in point_payload(chunk)


def test_qdrant_failure_safety_and_ownership() -> None:
    def unavailable(request):
        raise httpx.ConnectError("private", request=request)

    with httpx.Client(
        base_url="http://qdrant:6333", transport=httpx.MockTransport(unavailable)
    ) as client:
        index = QdrantIndex(
            "http://qdrant:6333", "dense_v1_unavailable", dimensions=2, client=client
        )
        with pytest.raises(DenseError, match="unavailable"):
            index.create()
        index.close()
    server = FakeQdrant()
    server.created = True
    with httpx.Client(
        base_url="http://qdrant:6333", transport=httpx.MockTransport(server)
    ) as client:
        index = QdrantIndex("http://qdrant:6333", "dense_v1_existing", dimensions=2, client=client)
        with pytest.raises(DenseError, match="existing"):
            index.create()
        index.close()
    assert not any(request.method == "DELETE" for request in server.requests)
    with pytest.raises(DenseError, match="local"):
        QdrantIndex("https://remote.example", "dense_v1_fixture", dimensions=2)


def test_upserts_are_idempotent_and_ties_stable(fake_index) -> None:
    index, server, chunks = fake_index
    first = index.search((1.0, 0.0))
    assert [item.chunk_id for item in first] == [
        chunks[0].chunk_id,
        chunks[2].chunk_id,
        chunks[1].chunk_id,
    ]
    index.upsert(chunks, ((1.0, 0.0), (0.0, 1.0), (1.0, 0.0)))
    with pytest.raises(DenseError, match="verified"):
        index.search((1.0, 0.0))
    assert index.verify() == 3
    assert first == index.search((1.0, 0.0))
    with pytest.raises(DenseError, match="dimension"):
        index.search((1.0,))


@pytest.mark.parametrize("corruption", ["missing", "payload", "vector", "dimensions", "unknown"])
def test_incomplete_or_corrupt_index_is_not_evaluated(fake_index, corruption) -> None:
    index, server, chunks = fake_index
    identity = point_id(chunks[0])
    if corruption == "missing":
        del server.points[identity]
    elif corruption == "payload":
        server.points[identity]["payload"]["ordinal"] = 99
    elif corruption == "vector":
        server.points[identity]["vector"] = (0.0, 1.0)
    elif corruption == "dimensions":
        server.dimensions = 3
    else:
        point = server.points.pop(identity)
        point["id"] = "unknown"
        server.points["unknown"] = point
    with pytest.raises(DenseError):
        index.verify()
    with pytest.raises(DenseError, match="verified"):
        index.search((1.0, 0.0))


def test_incomplete_upsert_and_unknown_retrieved_metadata(fake_index) -> None:
    index, server, chunks = fake_index
    server.upsert_status = "acknowledged"
    with pytest.raises(DenseError, match="incomplete"):
        index.upsert(chunks, ((1.0, 0.0), (0.0, 1.0), (1.0, 0.0)))
    server.upsert_status = "completed"
    index.upsert(chunks, ((1.0, 0.0), (0.0, 1.0), (1.0, 0.0)))
    index.verify()
    server.points[point_id(chunks[0])]["payload"]["chunk_id"] = "changed"
    with pytest.raises(DenseError, match="metadata"):
        index.search((1.0, 0.0))


class FakeEmbedder:
    dimensions = 2
    metadata = {"synthetic_fixture": True}
    load_ms = 0.0

    def encode(self, texts, *, kind):
        assert kind == "query"
        return EmbeddingBatch(tuple((1.0, 0.0) for text in texts), tuple(3 for text in texts), 0)


def test_synthetic_end_to_end_no_gold_leakage_provenance_and_parser(
    fake_index, tmp_path: Path
) -> None:
    index, _, chunks = fake_index
    questions = [("fixture-q-1", "example"), ("fixture-q-2", "example")]
    first, timings = rank_queries(
        index,
        FakeEmbedder(),
        {c.chunk_id: c for c in chunks},
        questions,
        dataset_revision="synthetic-retrieval-gold-v1",
    )
    assert first[0].results == first[1].results  # One full corpus, both dev/test queries.
    path = tmp_path / "ranked.jsonl"
    path.write_text(results_jsonl(first), encoding="utf-8")
    parsed = load_ranked_results_jsonl(path)
    assert parsed == first
    assert parsed[0].results[0].evidence[0].document_sha256 == chunks[0].source_sha256
    assert parsed[0].results[0].evidence[0].source_end == chunks[0].provenance[0].source_end
    examples = tuple(
        GoldExample(
            "1.0",
            question_id,
            "synthetic-retrieval-gold-v1",
            True,
            f"fixture-family-{n}",
            Language.EN,
            text,
            QuestionCategory.FACT,
            True,
            chunks[n].source_sha256,
            (
                EvidenceAnchor(
                    f"fixture-e-{n}",
                    chunks[n].source_sha256,
                    DocumentFormat.PDF,
                    EvidenceLocator(page_number=1, block_index=0),
                    0,
                    12,
                ),
            ),
            DatasetSplit.DEV if n == 0 else DatasetSplit.TEST,
            ReviewStatus.REVIEWED,
            1,
            AdjudicationState.NOT_REQUIRED,
        )
        for n, (question_id, text) in enumerate(questions)
    )
    gold = validate_gold_dataset(examples)
    report = evaluate_retrieval(gold, parsed).to_dict()
    assert report["security"]["passed"] is None
    changed = validate_gold_dataset(
        tuple(
            replace(
                item,
                answerable=False,
                evidence=(),
                category=QuestionCategory.UNANSWERABLE,
                source_document_sha256=chunks[1 - n].source_sha256,
                split=DatasetSplit.TEST if n == 0 else DatasetSplit.DEV,
            )
            for n, item in enumerate(examples)
        )
    )
    repeated, _ = rank_queries(
        index,
        FakeEmbedder(),
        {c.chunk_id: c for c in chunks},
        ((item.question_id, item.question) for item in changed.examples),
        dataset_revision=changed.dataset_revision,
    )
    assert results_jsonl(repeated) == results_jsonl(first)
    assert evaluate_retrieval(gold, repeated).to_dict() == report
    assert rank_diagnostics(gold, first, first)["hit_at_1"]["overall"]["dense"]["numerator"] == 1
    assert timings["truncated_query_count"] == 0


def test_empty_results_and_missing_local_identity(fake_index) -> None:
    index, _, chunks = fake_index
    result, _ = rank_queries(
        index, FakeEmbedder(), {}, [("fixture-q-1", "")], dataset_revision="revision"
    )
    assert result[0].results == ()
    with pytest.raises(DenseError, match="canonical"):
        rank_queries(
            index, FakeEmbedder(), {}, [("fixture-q-1", "text")], dataset_revision="revision"
        )
    corpus = RetrievalCorpus(chunks, {"fixture": True})
    reference = {
        "corpus": corpus.metadata,
        "index_fingerprint": BM25Index(
            BM25Document(c.chunk_id, c.text) for c in chunks
        ).fingerprint,
    }
    verify_reference(corpus, reference)
    with pytest.raises(DenseError, match="identities"):
        verify_reference(corpus, {})
    with pytest.raises(DenseError, match="texts"):
        verify_reference(
            replace(corpus, chunks=(replace(chunks[0], text="changed"), *chunks[1:])), reference
        )


def test_ties_at_top_ten_boundary_use_all_stable_candidates(fake_index) -> None:
    index, _, chunks = fake_index
    tied = tuple(replace(chunks[0], chunk_id=f"fixture-tie-{n:03d}", ordinal=n) for n in range(13))
    # Remove the original fixture points only from this test's own collection.
    index.close()
    index.create()
    index.upsert(tied, tuple((1.0, 0.0) for _ in tied))
    assert index.verify() == 13
    assert [hit.chunk_id for hit in index.search((1.0, 0.0))] == [
        chunk.chunk_id for chunk in tied[:10]
    ]


def test_malformed_protocol_and_non_string_revision_fail_safely() -> None:
    with pytest.raises(DenseError):
        EmbeddingConfig(revision=None)

    def malformed(request):
        if request.url.path == "/":
            return httpx.Response(200, json={"version": "1.15.4"})
        return httpx.Response(200, json=[])

    with httpx.Client(
        base_url="http://qdrant:6333", transport=httpx.MockTransport(malformed)
    ) as client:
        index = QdrantIndex("http://qdrant:6333", "dense_v1_bad_json", dimensions=2, client=client)
        with pytest.raises(DenseError, match="invalid response"):
            index.create()
        index.close()
