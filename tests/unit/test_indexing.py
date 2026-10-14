from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from doclens_ai.dense_baseline.embeddings import (
    MODEL_FILE_HASHES,
    EmbeddingBatch,
    EmbeddingConfig,
)
from doclens_ai.models import CanonicalChunk, ProcessingStage
from doclens_ai.services.index_worker import IndexWorker
from doclens_ai.services.indexing import (
    Candidate,
    IndexingFailure,
    IndexingFailureCategory,
    IndexingResult,
    candidate_points,
    collection_name,
    embedding_identity,
)
from doclens_ai.services.processing import ClaimedProcessingJob, LeaseOwnershipError
from doclens_ai.services.worker import WorkerSettings
from doclens_ai.vector.qdrant import ProductionQdrant, VectorFailure, point_id


class FakeEmbedder:
    """Protocol fixture only; it is never evidence of real model inference."""

    dimensions = 384
    load_ms = 0

    def __init__(self):
        self.metadata = {
            "configuration": EmbeddingConfig().to_dict(),
            "dimensions": 384,
            "tokenizer_class": "XLMRobertaTokenizerFast",
            "tokenizer_identity": dict(MODEL_FILE_HASHES),
            "libraries": {
                "torch": "2.8.0+cpu",
                "transformers": "4.57.6",
                "huggingface-hub": "0.36.0",
                "tokenizers": "0.22.2",
                "safetensors": "0.8.0",
                "numpy": "2.5.4",
            },
        }

    def encode(self, texts, *, kind):
        assert kind == "passage"
        vectors = []
        for text in texts:
            index = int(hashlib.sha256(text.encode()).hexdigest(), 16) % self.dimensions
            vectors.append(tuple(1.0 if n == index else 0.0 for n in range(self.dimensions)))
        return EmbeddingBatch(tuple(vectors), tuple(1 for _ in texts), 0)


def _candidate(count=2):
    chunks = tuple(
        CanonicalChunk(
            id=uuid4(),
            ordinal=n,
            chunk_identity="chunk-" + f"{n:064x}",
            chunk_text="Sensitive fixture paragraph",
            content_sha256="a" * 64,
        )
        for n in range(count)
    )
    return Candidate(uuid4(), uuid4(), uuid4(), uuid4(), uuid4(), "b" * 64, chunks)


def _points(candidate):
    provider = FakeEmbedder()
    _, fp = embedding_identity(provider)
    return candidate_points(
        candidate,
        provider.encode([c.chunk_text for c in candidate.chunks], kind="passage").vectors,
        fp,
    )


def test_model_configuration_identity_and_safe_payload():
    provider = FakeEmbedder()
    metadata, fingerprint = embedding_identity(provider)
    assert metadata["provider"] == provider.metadata
    assert embedding_identity(FakeEmbedder())[1] == fingerprint
    candidate = _candidate()
    points = _points(candidate)
    assert len({p.id for p in points}) == len(points)
    assert (
        point_id(candidate.revision_id, candidate.chunks[0].id, candidate.chunks[0].chunk_identity)
        == points[0].id
    )
    assert (
        point_id(uuid4(), candidate.chunks[0].id, candidate.chunks[0].chunk_identity)
        != points[0].id
    )
    serialized = json.dumps([p.payload for p in points])
    assert (
        "Sensitive" not in serialized
        and "chunk_text" not in serialized
        and "filename" not in serialized
    )
    assert points[0].payload["workspace_id"] == str(candidate.workspace_id)
    provider.metadata["configuration"]["cpu_threads"] = 2
    assert embedding_identity(provider)[1] != fingerprint
    assert collection_name(fingerprint).endswith(fingerprint)


@pytest.mark.parametrize(
    "mutation", ["revision", "prefix", "normalization", "files", "dimensions", "extra", "libraries"]
)
def test_configuration_mismatch_fails_closed(mutation):
    provider = FakeEmbedder()
    if mutation == "revision":
        provider.metadata["configuration"]["revision"] = "0" * 40
    elif mutation == "prefix":
        provider.metadata["configuration"]["passage_prefix"] = "query: "
    elif mutation == "normalization":
        provider.metadata["configuration"]["normalization"] = "none"
    elif mutation == "files":
        provider.metadata["tokenizer_identity"]["model.safetensors"] = "0" * 64
    elif mutation == "dimensions":
        provider.dimensions = 383
    elif mutation == "extra":
        provider.metadata["private_document"] = "secret"
    else:
        provider.metadata["libraries"] = {"torch": "secret credential"}
    with pytest.raises(IndexingFailure) as error:
        embedding_identity(provider)
    assert error.value.category is IndexingFailureCategory.CONFIGURATION_MISMATCH
    assert not error.value.retryable and "secret" not in str(error.value)


@pytest.mark.parametrize(
    "vectors",
    [
        [],
        [(1.0,)],
        [tuple(float("nan") for _ in range(384))],
        [tuple(float("inf") for _ in range(384))],
        [tuple(0.0 for _ in range(384))],
        [tuple(True for _ in range(384))],
        None,
    ],
)
def test_invalid_embeddings(vectors):
    with pytest.raises(IndexingFailure) as error:
        candidate_points(_candidate(1), vectors, "a" * 64)
    assert error.value.category is IndexingFailureCategory.EMBEDDING_INVALID
    assert not error.value.retryable


class QdrantTransport:
    def __init__(self):
        self.points = {}
        self.created = False
        self.configuration = {"size": 384, "distance": "Cosine"}
        self.requests = []
        self.failure = None

    def __call__(self, request):
        self.requests.append(request)
        path, method = request.url.path, request.method
        if self.failure is not None:
            raise self.failure
        if path == "/":
            return httpx.Response(200, json={"version": "1.15.4"})
        data = json.loads(request.content or b"{}")
        if path.endswith("/points") and method == "PUT":
            assert request.url.params["wait"] == "true"
            for point in data["points"]:
                self.points[point["id"]] = copy.deepcopy(point)
            result = {"status": "completed"}
        elif path.endswith("/points/count"):
            revision = data["filter"]["must"][0]["match"]["value"]
            result = {
                "count": sum(
                    p["payload"].get("index_revision_id") == revision for p in self.points.values()
                )
            }
        elif path.endswith("/points/scroll"):
            revision = data["filter"]["must"][0]["match"]["value"]
            points = sorted(
                (
                    p
                    for p in self.points.values()
                    if p["payload"].get("index_revision_id") == revision
                ),
                key=lambda p: p["id"],
            )
            offset = data.get("offset")
            start = next((n for n, p in enumerate(points) if p["id"] == offset), 0)
            page = points[start : start + data["limit"]]
            next_offset = (
                points[start + len(page)]["id"] if start + len(page) < len(points) else None
            )
            result = {"points": page, "next_page_offset": next_offset}
        elif method == "PUT":
            self.created = True
            result = True
        elif self.created:
            result = {"config": {"params": {"vectors": self.configuration}}}
        else:
            return httpx.Response(404, json={"status": "error"})
        return httpx.Response(
            200,
            content=json.dumps({"status": "ok", "result": result}).encode(),
            headers={"content-type": "application/json"},
        )


def test_idempotent_batched_upsert_full_verification_and_no_delete():
    async def exercise():
        transport = QdrantTransport()
        async with httpx.AsyncClient(
            base_url="http://qdrant", transport=httpx.MockTransport(transport)
        ) as client:
            adapter = ProductionQdrant("http://qdrant", "doclens_unit", batch_size=1, client=client)
            first, second = _candidate(), _candidate()
            await adapter.ensure_collection()
            await adapter.upsert(first.revision_id, _points(first))
            await adapter.upsert(second.revision_id, _points(second))
            await adapter.upsert(first.revision_id, _points(first))
            assert await adapter.verify(first.revision_id, _points(first)) == 2
            assert len(transport.points) == 4
            await adapter.close()
            assert not any(r.method == "DELETE" for r in transport.requests)

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "corruption", ["missing", "payload", "dimension", "nan", "vector", "extra"]
)
def test_complete_expected_candidate_is_verified(corruption):
    async def exercise():
        transport = QdrantTransport()
        async with httpx.AsyncClient(
            base_url="http://qdrant", transport=httpx.MockTransport(transport)
        ) as client:
            adapter = ProductionQdrant("http://qdrant", "doclens_unit", client=client)
            candidate = _candidate()
            points = _points(candidate)
            await adapter.ensure_collection()
            await adapter.upsert(candidate.revision_id, points)
            point = transport.points[points[0].id]
            if corruption == "missing":
                del transport.points[points[0].id]
            elif corruption == "payload":
                point["payload"]["workspace_id"] = str(uuid4())
            elif corruption == "dimension":
                point["vector"] = [1.0]
            elif corruption == "nan":
                point["vector"] = [float("nan")] * 384
            elif corruption == "vector":
                point["vector"] = [1.0 if n == 383 else 0.0 for n in range(384)]
            else:
                transport.points[str(uuid4())] = copy.deepcopy(point)
            with pytest.raises(VectorFailure) as error:
                await adapter.verify(candidate.revision_id, points)
            assert not error.value.retryable

    asyncio.run(exercise())


def test_connection_failure_retry_and_incompatible_collection_not_recreated():
    async def exercise():
        transport = QdrantTransport()
        async with httpx.AsyncClient(
            base_url="http://qdrant", transport=httpx.MockTransport(transport)
        ) as client:
            adapter = ProductionQdrant("http://qdrant", "doclens_unit", client=client)
            transport.failure = httpx.ConnectError("private endpoint credential")
            with pytest.raises(VectorFailure) as error:
                await adapter.ensure_collection()
            assert error.value.retryable and "private" not in str(error.value)
            transport.failure = None
            transport.created, transport.configuration = True, {"size": 2, "distance": "Dot"}
            with pytest.raises(VectorFailure) as error:
                await adapter.ensure_collection()
            assert not error.value.retryable
            assert not any(r.method in {"PUT", "DELETE"} for r in transport.requests)

    asyncio.run(exercise())


def _index_worker(error=None, heartbeat_error=None):
    settings = WorkerSettings(
        _env_file=None,
        lease_seconds=1,
        heartbeat_interval_seconds=0.01,
        db_timeout_seconds=0.1,
        poll_interval_seconds=0.01,
    )
    claim = ClaimedProcessingJob(
        uuid4(),
        uuid4(),
        uuid4(),
        ProcessingStage.EMBEDDING,
        uuid4(),
        datetime.now(UTC) + timedelta(seconds=1),
        1,
        3,
    )
    coordinator = SimpleNamespace(
        lease_duration=timedelta(seconds=1),
        claim_next=AsyncMock(return_value=claim),
        heartbeat=AsyncMock(side_effect=heartbeat_error),
        fail_attempt=AsyncMock(),
        complete=AsyncMock(),
    )
    service = SimpleNamespace(
        index=AsyncMock(side_effect=error, return_value=IndexingResult(uuid4(), 2, 10, 5))
    )
    return IndexWorker(coordinator, service, settings=settings, worker_id="unit-index"), claim


@pytest.mark.parametrize(
    "error",
    [
        IndexingFailure(IndexingFailureCategory.EMBEDDING_UNAVAILABLE, retryable=True),
        IndexingFailure(IndexingFailureCategory.EMBEDDING_INVALID, retryable=False),
        IndexingFailure(IndexingFailureCategory.OWNERSHIP_LOST, retryable=False),
        RuntimeError("private secret text"),
        None,
    ],
)
def test_worker_failure_routing_and_verified_completion(error, caplog):
    async def exercise():
        worker, claim = _index_worker(error)
        await worker.run_once()
        worker.coordinator.claim_next.assert_awaited_once_with(
            worker_id="unit-index", stages=(ProcessingStage.EMBEDDING, ProcessingStage.INDEXING)
        )
        if error is None:
            worker.coordinator.complete.assert_awaited_once()
            assert worker.coordinator.complete.await_args.kwargs["index_revision_id"]
        elif (
            isinstance(error, IndexingFailure)
            and error.category is IndexingFailureCategory.OWNERSHIP_LOST
        ):
            worker.coordinator.fail_attempt.assert_not_awaited()
            worker.coordinator.complete.assert_not_awaited()
        else:
            worker.coordinator.fail_attempt.assert_awaited_once()
            assert worker.coordinator.fail_attempt.await_args.kwargs["retryable"] == (
                error.retryable if isinstance(error, IndexingFailure) else True
            )
            worker.coordinator.complete.assert_not_awaited()
        assert len(asyncio.all_tasks()) == 1

    asyncio.run(exercise())
    assert "private secret" not in caplog.text


@pytest.mark.parametrize("cancel", [False, True])
def test_worker_heartbeat_loss_and_cancellation_do_not_activate(cancel):
    async def exercise():
        worker, _ = _index_worker(heartbeat_error=LeaseOwnershipError("private"))
        entered, release, heartbeat_seen = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def index(*args, **kwargs):
            entered.set()
            await release.wait()
            return IndexingResult(uuid4(), 1, 0, 0)

        async def heartbeat(**kwargs):
            heartbeat_seen.set()
            raise LeaseOwnershipError("private")

        worker.indexing.index.side_effect = index
        worker.coordinator.heartbeat.side_effect = heartbeat
        task = asyncio.create_task(worker.run_once())
        try:
            await asyncio.wait_for(entered.wait(), 1)
            await asyncio.wait_for(heartbeat_seen.wait(), 1)
            if cancel:
                task.cancel()
                await asyncio.sleep(0)
                assert not task.done()
            release.set()
            if cancel:
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                await task
            worker.coordinator.complete.assert_not_awaited()
            worker.coordinator.fail_attempt.assert_not_awaited()
            assert len(asyncio.all_tasks()) == 1
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())
