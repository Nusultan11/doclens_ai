from __future__ import annotations

import asyncio
import copy
import json
import threading
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from pydantic import ValidationError

from doclens_ai.core.search_config import SearchSettings
from doclens_ai.services.retrieval import (
    QueryEncoder,
    SearchInput,
    SearchUnavailable,
    source_locator,
)
from doclens_ai.vector.qdrant import ProductionQdrant, VectorFailure
from tests.unit.test_indexing import FakeEmbedder


class QueryFixtureEmbedder(FakeEmbedder):
    """Protocol/security fixture, not a real-model quality measurement."""

    def encode(self, texts, *, kind):
        assert kind == "query"
        return super().encode(texts, kind="passage")


@pytest.mark.parametrize(
    "change",
    [
        {"query": ""},
        {"query": " \t"},
        {"query": "x" * 2001},
        {"query": 1},
        {"query": "x\x00y"},
        {"top_k": 21},
        {"limit": 21},
        {"top_k": True},
        {"top_k": 5, "limit": 10},
        {"document_ids": []},
        {"document_ids": [str(uuid4()) for _ in range(51)]},
        {"qdrant_filter": {}},
    ],
)
def test_strict_input_bounds(change):
    with pytest.raises(ValidationError):
        SearchInput.model_validate({"workspace_id": str(uuid4()), "query": "valid", **change})


def test_duplicate_scope_and_settings_bounds():
    doc = uuid4()
    with pytest.raises(ValidationError):
        SearchInput(workspace_id=uuid4(), query="valid", document_ids=[doc, doc])
    with pytest.raises(ValidationError):
        SearchSettings(_env_file=None, inference_concurrency=3)
    with pytest.raises(ValidationError):
        SearchSettings(_env_file=None, db_timeout_seconds=float("nan"))
    assert not SearchSettings(_env_file=None).enabled


@pytest.mark.parametrize(
    "format,location",
    [
        ("pdf", {"page_number": 3}),
        ("docx", {"block_index": 2, "table_index": 0, "row_index": 1}),
        ("xlsx", {"sheet_index": 0, "sheet_name": "Authorized sheet", "cell_coordinate": "A1:B2"}),
    ],
)
def test_source_locator_preserves_only_contract_fields(format, location):
    chunk = SimpleNamespace(
        document_format=format,
        source_provenance=[
            {
                "source": location,
                "source_start": 0,
                "source_end": 5,
                "source_length": 8,
                "unit_id": "opaque-internal",
                "object_storage_key": "never-return",
            }
        ],
    )
    result = source_locator(chunk).model_dump(exclude_none=True)
    assert result["spans"][0]["source"] == location
    assert "never-return" not in json.dumps(result) and "unit_id" not in json.dumps(result)
    chunk.source_provenance[0]["source"]["private_path"] = "not-allowed"
    with pytest.raises(ValueError):
        source_locator(chunk)


def test_query_prefix_contract_and_invalid_vector():
    async def exercise():
        encoder = QueryEncoder(QueryFixtureEmbedder())
        assert len(await encoder.encode("Controlled query")) == 384
        encoder.provider.encode = lambda *a, **k: SimpleNamespace(vectors=((float("nan"),) * 384,))
        with pytest.raises(SearchUnavailable, match="search service is unavailable"):
            await encoder.encode("private query")

    asyncio.run(exercise())


@pytest.mark.parametrize("cancellations", [1, 2])
def test_inference_cancellation_keeps_slot_until_cpu_thread_drains(cancellations):
    async def exercise():
        provider = QueryFixtureEmbedder()
        original = provider.encode
        entered, release = threading.Event(), threading.Event()

        def blocked(*args, **kwargs):
            entered.set()
            assert release.wait(5)
            return original(*args, **kwargs)

        provider.encode = blocked
        encoder = QueryEncoder(provider, queue_timeout_seconds=0.02)
        task = asyncio.create_task(encoder.encode("private"))
        try:
            assert await asyncio.to_thread(entered.wait, 1)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            if cancellations == 2:
                task.cancel()
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                assert not task.done()
            with pytest.raises(SearchUnavailable):
                await encoder.encode("second")
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert len(await encoder.encode("after cancellation")) == 384
            assert len(asyncio.all_tasks()) == 1
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())


def test_evaluation_percentiles_and_disposable_preparation_guard(monkeypatch):
    from doclens_ai.evaluation.metrics import EvaluationError
    from doclens_ai.retrieval_eval import percentiles, prepare_corpus

    assert percentiles([]) == {"sample_count": 0, "p50_ms": None, "p95_ms": None}
    assert percentiles([0, 10, 20])["p50_ms"] == 10
    assert percentiles([0, 10, 20])["p95_ms"] == 19
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example:unused@localhost/business")
    with pytest.raises(EvaluationError, match="disposable"):
        asyncio.run(prepare_corpus(None, None, None, ()))


def _search_fixture():
    workspace, revision, document = uuid4(), uuid4(), uuid4()
    payload = {
        "workspace_id": str(workspace),
        "index_revision_id": str(revision),
        "document_id": str(document),
        "document_version_id": str(uuid4()),
        "processing_run_id": str(uuid4()),
        "chunk_id": str(uuid4()),
        "embedding_revision": "a" * 40,
        "embedding_configuration_fingerprint": "b" * 64,
    }
    return workspace, revision, document, payload


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "foreign",
        "extra_payload",
        "missing_payload",
        "bad_id",
        "nan",
        "oversized",
        "malformed",
        "timeout",
        "duplicate",
    ],
)
def test_qdrant_bounded_server_filters_ordering_and_validation(mutation):
    async def exercise():
        workspace, revision, document, payload = _search_fixture()
        low_id, high_id = UUID(int=1), UUID(int=2)
        points = [
            {"id": str(high_id), "score": 0.5, "payload": copy.deepcopy(payload)},
            {"id": str(low_id), "score": 0.5, "payload": copy.deepcopy(payload)},
        ]
        requests = []

        def handle(request):
            requests.append(request)
            if request.url.path == "/":
                return httpx.Response(200, json={"version": "1.15.4"})
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "status": "ok",
                        "result": {
                            "config": {"params": {"vectors": {"size": 384, "distance": "Cosine"}}}
                        },
                    },
                )
            data = json.loads(request.content)
            assert data["limit"] == 2 and not data["with_vector"]
            assert data["filter"]["must"] == [
                {"key": "workspace_id", "match": {"value": str(workspace)}},
                {"key": "index_revision_id", "match": {"any": [str(revision)]}},
                {"key": "document_id", "match": {"any": [str(document)]}},
            ]
            if mutation == "timeout":
                raise httpx.ReadTimeout("private endpoint/query")
            if mutation == "foreign":
                points[0]["payload"]["workspace_id"] = str(uuid4())
            elif mutation == "extra_payload":
                points[0]["payload"]["text"] = "private"
            elif mutation == "missing_payload":
                points[0].pop("payload")
            elif mutation == "bad_id":
                points[0]["id"] = "not-uuid"
            elif mutation == "nan":
                points[0]["score"] = float("nan")
            elif mutation == "oversized":
                points.append(points[0])
            elif mutation == "duplicate":
                points[0] = copy.deepcopy(points[1])
                points[0]["score"] = 0.6
            result = {"points": points} if mutation != "malformed" else []
            return httpx.Response(
                200, content=json.dumps({"status": "ok", "result": result}).encode()
            )

        async with httpx.AsyncClient(
            base_url="http://qdrant", transport=httpx.MockTransport(handle)
        ) as client:
            adapter = ProductionQdrant("http://qdrant", "doclens_test", client=client)
            args = {
                "workspace_id": workspace,
                "revision_ids": (revision,),
                "document_ids": (document,),
                "limit": 2,
            }
            if mutation in {"nan", "oversized", "malformed", "timeout"}:
                with pytest.raises(VectorFailure):
                    await adapter.search((1.0,) + (0.0,) * 383, **args)
            else:
                hits = await adapter.search((1.0,) + (0.0,) * 383, **args)
                assert hits[0].id == str(low_id)
                assert len(hits) == (2 if mutation is None else 1)
                if mutation == "duplicate":
                    assert hits[0].score == 0.6
            assert not any(r.method in {"PUT", "DELETE"} for r in requests)

    asyncio.run(exercise())
