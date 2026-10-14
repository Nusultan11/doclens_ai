from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text

from doclens_ai.models import (
    CanonicalChunk,
    DocumentVersion,
    IndexRevision,
    User,
    WorkspaceMembership,
)
from doclens_ai.services.retrieval import (
    QueryEncoder,
    RetrievalService,
    SearchForbidden,
    SearchInput,
    SearchUnavailable,
)
from doclens_ai.vector.qdrant import ProductionQdrant, SearchHit, point_id
from tests.integration.test_production_indexing import (
    _claim,
    _complete,
    _extraction_worker,
    _index,
    _index_environment,
    _next_version_or_run,
    _ready,
)
from tests.unit.test_retrieval import QueryFixtureEmbedder

pytestmark = [pytest.mark.integration, pytest.mark.storage]


@asynccontextmanager
async def _retrieval_context(url, settings):
    async with _index_environment(url, settings) as env:
        factory, storage, keys, worker, vector, _ = env
        first = await _ready(factory, storage, keys)
        second = await _ready(factory, storage, keys)
        assert await worker.run_once() and await worker.run_once()
        async with factory() as session, session.begin():
            versions = [
                await session.get(DocumentVersion, r.document_version_id) for r in (first, second)
            ]
            revisions = [
                await session.scalar(
                    select(IndexRevision).where(IndexRevision.document_version_id == v.id)
                )
                for v in versions
            ]
            user = User(issuer="https://retrieval.fixture/", subject=uuid4().hex)
            other = User(issuer=user.issuer, subject=uuid4().hex)
            session.add_all([user, other])
            await session.flush()
            session.add_all(
                [
                    WorkspaceMembership(
                        user_id=user.id, workspace_id=revisions[0].workspace_id, role="viewer"
                    ),
                    WorkspaceMembership(
                        user_id=other.id, workspace_id=revisions[1].workspace_id, role="viewer"
                    ),
                ]
            )
        provider = QueryFixtureEmbedder()
        service = RetrievalService(factory, QueryEncoder(provider), vector)
        yield env, service, user, other, first, second, revisions


def _request(revision, **kwargs):
    return SearchInput(
        workspace_id=revision.workspace_id, query="Controlled fixture query", **kwargs
    )


def test_real_qdrant_filters_and_postgres_authorization(
    migrated_database_url, test_storage_settings, monkeypatch
):
    async def exercise():
        async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
            _, service, user, other, _, _, revisions = ctx
            for identity, revision in zip((user, other), revisions, strict=True):
                outcome = await service.search(user_id=identity.id, request=_request(revision))
                assert len(outcome.results) == 2
                assert all(
                    h.workspace_id == revision.workspace_id
                    and h.index_revision_id == revision.id
                    and h.document_version_id == revision.document_version_id
                    for h in outcome.results
                )
                assert all(h.locator.document_format == "docx" for h in outcome.results)
                assert any(h.locator.spans[0].source.table_index == 0 for h in outcome.results)
            with pytest.raises(SearchForbidden):
                await service.search(user_id=user.id, request=_request(revisions[1]))
            foreign = await service.search(
                user_id=user.id,
                request=_request(revisions[0], document_ids=[revisions[1].document_id]),
            )
            assert not foreign.results
            original_search = service.vector.search

            async def authorized_filter(*args, **kwargs):
                assert kwargs["document_ids"] == (revisions[0].document_id,)
                return await original_search(*args, **kwargs)

            with monkeypatch.context() as patch:
                patch.setattr(service.vector, "search", authorized_filter)
                mixed = await service.search(
                    user_id=user.id,
                    request=_request(revisions[0], document_ids=[r.document_id for r in revisions]),
                )
            assert len(mixed.results) == 2 and all(
                h.document_id == revisions[0].document_id for h in mixed.results
            )
            concurrent = await asyncio.gather(
                *(service.search(user_id=user.id, request=_request(revisions[0])) for _ in range(6))
            )
            assert all(len(r.results) == 2 for r in concurrent)

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "mutation",
    ["foreign", "forged_foreign", "missing", "point_id", "payload", "duplicate", "deleted"],
)
def test_untrusted_candidates_never_release_unauthorized_text(
    migrated_database_url, test_storage_settings, monkeypatch, mutation
):
    async def exercise():
        async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
            env, service, user, _, _, _, revisions = ctx
            factory, _, _, _, vector, _ = env
            original = vector.search

            async def injected(*args, **kwargs):
                hits = await original(*args, **kwargs)
                assert len(hits) == 2
                if mutation == "duplicate":
                    return (hits[0], replace(hits[0], score=hits[0].score - 0.01), hits[1])
                if mutation == "deleted":
                    async with factory() as session, session.begin():
                        await session.execute(
                            delete(CanonicalChunk).where(
                                CanonicalChunk.id == hits[0].payload["chunk_id"]
                            )
                        )
                    return hits
                payload = dict(hits[0].payload)
                identity = hits[0].id
                if mutation in {"foreign", "forged_foreign"}:
                    async with factory() as session:
                        chunk = await session.scalar(
                            select(CanonicalChunk).where(
                                CanonicalChunk.processing_run_id == revisions[1].processing_run_id
                            )
                        )
                    payload["chunk_id"] = str(chunk.id)
                    identity = point_id(revisions[1].id, chunk.id, chunk.chunk_identity)
                    if mutation == "foreign":
                        payload["workspace_id"] = str(revisions[1].workspace_id)
                elif mutation == "missing":
                    payload["chunk_id"] = str(uuid4())
                elif mutation == "point_id":
                    identity = str(uuid4())
                else:
                    payload["embedding_revision"] = "a" * 40
                return (SearchHit(identity, 1.0, payload), hits[1])

            monkeypatch.setattr(vector, "search", injected)
            outcome = await service.search(user_id=user.id, request=_request(revisions[0]))
            assert len(outcome.results) == (2 if mutation == "duplicate" else 1)
            assert all(h.workspace_id == revisions[0].workspace_id for h in outcome.results)
            assert outcome.rejected_candidates >= 1

    asyncio.run(exercise())


@pytest.mark.parametrize("mutation", ["extra_payload", "model_revision", "high_score_foreign"])
def test_real_qdrant_payload_corruption_and_foreign_point(
    migrated_database_url, test_storage_settings, mutation
):
    async def exercise():
        async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
            env, service, user, _, _, _, revisions = ctx
            factory, _, _, _, vector, _ = env
            response = await vector._client.post(
                vector.path + "/points/scroll",
                json={
                    "filter": {
                        "must": [
                            {"key": "index_revision_id", "match": {"value": str(revisions[0].id)}}
                        ]
                    },
                    "limit": 20,
                    "with_payload": True,
                    "with_vector": True,
                },
            )
            response.raise_for_status()
            point = response.json()["result"]["points"][0]
            if mutation == "extra_payload":
                point["payload"]["text"] = "Private untrusted Qdrant payload"
            elif mutation == "model_revision":
                point["payload"]["embedding_revision"] = "a" * 40
            else:
                async with factory() as session:
                    foreign = await session.scalar(
                        select(CanonicalChunk).where(
                            CanonicalChunk.processing_run_id == revisions[1].processing_run_id
                        )
                    )
                point["id"] = point_id(revisions[0].id, foreign.id, foreign.chunk_identity)
                point["payload"]["chunk_id"] = str(foreign.id)
                point["vector"] = await service.encoder.encode("Controlled fixture query")
            response = await vector._client.put(
                vector.path + "/points",
                params={"wait": "true"},
                json={"points": [{key: point[key] for key in ("id", "payload", "vector")}]},
            )
            response.raise_for_status()
            outcome = await service.search(user_id=user.id, request=_request(revisions[0]))
            assert len(outcome.results) == (2 if mutation == "high_score_foreign" else 1)
            assert all(h.workspace_id == revisions[0].workspace_id for h in outcome.results)
            assert "Private untrusted" not in "".join(h.text for h in outcome.results)
            if mutation == "high_score_foreign":
                assert outcome.rejected_candidates == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("phase", ["qdrant", "final"])
def test_revocation_during_retrieval_is_freshly_enforced(
    migrated_database_url, test_storage_settings, monkeypatch, phase
):
    async def exercise():
        async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
            env, service, user, _, _, _, revisions = ctx
            factory, _, _, _, vector, _ = env

            async def revoke():
                async with factory() as session, session.begin():
                    await session.execute(
                        delete(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id)
                    )

            if phase == "qdrant":
                original = vector.search

                async def network(*args, **kwargs):
                    hits = await original(*args, **kwargs)
                    await revoke()
                    return hits

                monkeypatch.setattr(vector, "search", network)
            else:
                original = service._resolve
                calls = 0

                async def resolve(*args, **kwargs):
                    nonlocal calls
                    result = await original(*args, **kwargs)
                    calls += 1
                    if calls == 1:
                        assert result
                        await revoke()
                    return result

                monkeypatch.setattr(service, "_resolve", resolve)
            with pytest.raises(SearchForbidden):
                await service.search(user_id=user.id, request=_request(revisions[0]))

    asyncio.run(exercise())


@pytest.mark.parametrize("phase", ["qdrant", "final"])
def test_real_active_cutover_invalidates_old_hits(
    migrated_database_url, test_storage_settings, monkeypatch, phase
):
    async def exercise():
        async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
            env, service, user, _, first, _, revisions = ctx
            factory, storage, _, worker, vector, _ = env
            await _next_version_or_run(factory, first, reprocess=False)
            assert await _extraction_worker(factory, storage).run_once()
            claim = await _claim(worker)
            verified = await _index(worker, claim)

            async def cutover():
                await _complete(worker, claim, verified)

            if phase == "qdrant":
                original = vector.search

                async def network(*args, **kwargs):
                    hits = await original(*args, **kwargs)
                    await cutover()
                    return hits

                monkeypatch.setattr(vector, "search", network)
            else:
                original = service._resolve
                calls = 0

                async def resolve(*args, **kwargs):
                    nonlocal calls
                    result = await original(*args, **kwargs)
                    calls += 1
                    if calls == 1:
                        assert result
                        await cutover()
                    return result

                monkeypatch.setattr(service, "_resolve", resolve)
            outcome = await service.search(user_id=user.id, request=_request(revisions[0]))
            assert not outcome.results
            async with factory() as session:
                assert (await session.get(IndexRevision, verified.revision_id)).status == "active"
                assert (await session.get(IndexRevision, revisions[0].id)).status == "superseded"

    asyncio.run(exercise())


def test_model_mismatch_no_active_and_dependency_failure(
    migrated_database_url, test_storage_settings, monkeypatch
):
    async def exercise():
        async with _retrieval_context(migrated_database_url, test_storage_settings) as ctx:
            env, service, user, _, _, _, revisions = ctx
            factory, _, _, _, vector, _ = env
            provider = QueryFixtureEmbedder()
            provider.metadata["configuration"]["cpu_threads"] = 2
            encoder = QueryEncoder(provider)
            incompatible = ProductionQdrant("http://127.0.0.1:1", "test_" + encoder.fingerprint)
            try:
                different = RetrievalService(factory, encoder, incompatible)
                with pytest.raises(SearchUnavailable):
                    await different.search(user_id=user.id, request=_request(revisions[0]))
            finally:
                await incompatible.close()

            def failed(*args, **kwargs):
                raise RuntimeError("private query/model path")

            monkeypatch.setattr(service.encoder.provider, "encode", failed)
            with pytest.raises(SearchUnavailable, match="search service is unavailable"):
                await service.search(user_id=user.id, request=_request(revisions[0]))
            async with factory() as session, session.begin():
                await session.execute(
                    text(
                        "UPDATE index_revisions SET status='superseded', "
                        "superseded_at=clock_timestamp() WHERE id=:id"
                    ),
                    {"id": revisions[0].id},
                )
            # No active index returns empty without attempting inference or contacting Qdrant.
            outcome = await service.search(user_id=user.id, request=_request(revisions[0]))
            assert not outcome.results and outcome.embedding_ms == 0 and outcome.qdrant_ms == 0

    asyncio.run(exercise())
