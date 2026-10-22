"""Real PG/S3/Qdrant and HTTP authorization; synthetic engines, embeddings and JWKS."""

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pypdf import PdfWriter
from sqlalchemy import delete, select, text

from doclens_ai.extraction.engines import EngineRegistry, EngineRoute
from doclens_ai.models import (
    CanonicalChunk,
    ExtractionArtifact,
    IndexRevision,
    IndexRevisionStatus,
    ProcessingJob,
    ProcessingRun,
    User,
    WorkspaceMembership,
)
from doclens_ai.services.index_worker import IndexWorker
from doclens_ai.services.indexing import IndexingService
from doclens_ai.services.processing import (
    PROCESSING_CONFIGURATION_VERSION,
    ProcessingCoordinator,
    ProcessingPolicy,
    default_processing_configuration_fingerprint,
)
from doclens_ai.services.retrieval import QueryEncoder, RetrievalService
from doclens_ai.services.worker import IngestionWorker, WorkerSettings
from doclens_ai.vector.qdrant import VectorFailure
from tests.integration.test_engine_ingestion import prepare_engine_run
from tests.integration.test_production_indexing import _claim, _complete, _index
from tests.integration.test_search_api import _search_api_context
from tests.unit.test_extraction_engines import FakeRegionsIR, FakeWordsIR
from tests.unit.test_indexing import FakeEmbedder
from tests.unit.test_retrieval import QueryFixtureEmbedder

pytestmark = [pytest.mark.integration, pytest.mark.storage]


def two_pages(ir):
    first = ir.elements[0]
    second = first.model_copy(
        update={
            "id": first.id + "-page2",
            "text": "-20 kg",
            "source": replace(first.source, page_number=2),
        }
    )
    return ir.model_copy(update={"elements": (first, second)})


class TwoPageWordsIR(FakeWordsIR):
    descriptor = replace(
        FakeWordsIR.descriptor,
        name="two-page-words",
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )

    def extract(self, source, *, options_json):
        return two_pages(super().extract(source, options_json=options_json))


class TwoPageRegionsIR(FakeRegionsIR):
    descriptor = replace(TwoPageWordsIR.descriptor, name="two-page-regions")

    def extract(self, source, *, options_json):
        return two_pages(super().extract(source, options_json=options_json))


async def rechunk_run(factory, uploaded, original_run_id):
    async with factory() as session, session.begin():
        original = await session.get(ProcessingRun, original_run_id)
        route = EngineRoute.model_validate(original.extraction_route).model_copy(
            update={
                "ir_chunk_options_json": json.dumps(
                    {"max_characters": 900, "max_chunks": 100000, "max_source_characters": 5000000},
                    sort_keys=True,
                    separators=(",", ":"),
                )
            }
        )
        run = ProcessingRun(
            id=uuid4(),
            operation_id=uuid4(),
            operation_kind="reprocess",
            document_version_id=uploaded.document_version_id,
            extraction_route=route.model_dump(mode="json"),
            configuration_version=PROCESSING_CONFIGURATION_VERSION,
            configuration_fingerprint=default_processing_configuration_fingerprint(route),
            stage="extraction",
            status="queued",
        )
        job = ProcessingJob(
            id=uuid4(), processing_run_id=run.id, status="queued", attempt_count=0, max_attempts=3
        )
        session.add_all([run, job])
        return run.id, job.id, route.fingerprint()


@pytest.mark.parametrize("engine_class", [TwoPageWordsIR, TwoPageRegionsIR])
def test_fake_pdf_search_acl_partial_index_retry_and_atomic_cutover(
    migrated_database_url, test_storage_settings, tmp_path, monkeypatch, engine_class
):
    path = tmp_path / "source.pdf"
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=100, height=100)
    writer.write(path)

    async def exercise():
        async with _search_api_context(
            migrated_database_url, test_storage_settings, initialize=False
        ) as (ctx, vector):
            factory, keys = ctx.database.session_factory, []
            try:
                (
                    uploaded,
                    ingestion,
                    _,
                    expected,
                    document_id,
                    workspace_id,
                ) = await prepare_engine_run(factory, ctx.storage, keys, engine_class(), path)
                async with factory() as session, session.begin():
                    viewer = await session.scalar(
                        select(User).where(User.subject == ctx.viewer_subject)
                    )
                    viewer_id = viewer.id
                    session.add(
                        WorkspaceMembership(
                            user_id=viewer_id, workspace_id=workspace_id, role="viewer"
                        )
                    )
                ctx.application.state.retrieval_service = RetrievalService(
                    factory, QueryEncoder(QueryFixtureEmbedder()), vector
                )
                body = {"workspace_id": str(workspace_id), "query": "-10 kg"}

                async def search(**changes):
                    response = await ctx.client.post(
                        "/api/v1/search",
                        json=body | changes,
                        headers=ctx.authorization(ctx.viewer_subject),
                    )
                    assert response.status_code == 200, response.text
                    return response.json()["results"]

                assert (await ctx.client.post("/api/v1/search", json=body)).status_code == 401
                for subject, ws in (
                    (ctx.outsider_subject, workspace_id),
                    (ctx.viewer_subject, ctx.other_workspace_id),
                ):
                    denied = await ctx.client.post(
                        "/api/v1/search",
                        json=body | {"workspace_id": str(ws)},
                        headers=ctx.authorization(subject),
                    )
                    assert denied.status_code == 403 and "-10 kg" not in denied.text

                settings = WorkerSettings(
                    _env_file=None,
                    lease_seconds=8,
                    heartbeat_interval_seconds=0.03,
                    db_timeout_seconds=2,
                    poll_interval_seconds=0.01,
                )
                coordinator = ProcessingCoordinator(
                    factory, policy=ProcessingPolicy(lease_duration=timedelta(seconds=8))
                )
                extractor = IngestionWorker(
                    coordinator, ingestion, settings=settings, worker_id="engine-search-extraction"
                )
                assert await extractor.run_once()
                async with factory() as session:
                    artifact = await session.scalar(select(ExtractionArtifact))
                    chunks = tuple(await session.scalars(select(CanonicalChunk)))
                    assert len(chunks) == 2 and artifact.state == "available"
                    original_ids = {str(c.id) for c in chunks}
                    original_chunks = {c.id: c.source_provenance for c in chunks}
                    assert all(
                        span["extraction_artifact_id"] == str(artifact.id)
                        and span["artifact_checksum"] == artifact.checksum
                        for chunk in chunks
                        for span in chunk.source_provenance
                    )
                _, snapshot = await ingestion.artifacts.load(artifact.id, expected=expected)
                assert snapshot.observations[0].elements[0].geometry.coordinate_system == (
                    "top_left_points" if engine_class is TwoPageWordsIR else "bottom_left_points"
                )
                # No ACTIVE revision: canonical chunks alone must be invisible.
                assert await search() == []
                indexer = IndexWorker(
                    coordinator,
                    IndexingService(factory, FakeEmbedder(), vector),
                    settings=settings,
                    worker_id="engine-search-index",
                )
                claim = await _claim(indexer)
                result = await _index(indexer, claim)
                assert await search() == []  # Verified candidate still invisible.
                assert await _complete(indexer, claim, result) is IndexRevisionStatus.ACTIVE
                hits = await search()
                assert {h["chunk_id"] for h in hits} == original_ids
                assert {h["text"] for h in hits} == {"-10 kg", "-20 kg"}
                assert all(h["document_id"] == str(document_id) for h in hits)
                assert all(
                    h["document_version_id"] == str(uploaded.document_version_id) for h in hits
                )
                assert {h["source_locator"]["spans"][0]["source"]["page_number"] for h in hits} == {
                    1,
                    2,
                }
                assert "object_storage_key" not in json.dumps(hits)
                assert "artifact_checksum" not in json.dumps(hits)
                assert await search(document_ids=[str(uuid4())]) == []

                run_id, job_id, route_fingerprint = await rechunk_run(
                    factory, uploaded, artifact.processing_run_id
                )
                ingestion._registry = EngineRegistry()  # Replay cannot invoke either engine.
                replay = await coordinator.claim_next(worker_id="engine-search-rechunk")
                assert replay.processing_run_id == run_id
                await ingestion.ingest_from_artifact(
                    run_id,
                    artifact.id,
                    worker_id="engine-search-rechunk",
                    lease_token=replay.lease_token,
                )
                await coordinator.handoff_extraction(
                    job_id=job_id, worker_id="engine-search-rechunk", lease_token=replay.lease_token
                )
                original_upsert = vector.upsert

                async def partial(revision, points):
                    assert len(points) == 2
                    await original_upsert(revision, points[:1])
                    raise VectorFailure("vector_unavailable", retryable=True)

                with monkeypatch.context() as patch:
                    patch.setattr(vector, "upsert", partial)
                    assert await indexer.run_once()
                async with factory() as session:
                    job = await session.get(ProcessingJob, job_id)
                    assert job.status == "retry_wait" and job.attempt_count == 1
                    assert job.failure_reason == "vector_unavailable"
                    assert (
                        EngineRoute.model_validate(
                            (await session.get(ProcessingRun, run_id)).extraction_route
                        ).fingerprint()
                        == route_fingerprint
                    )
                    active = tuple(
                        await session.scalars(
                            select(IndexRevision).where(IndexRevision.status == "active")
                        )
                    )
                    assert len(active) == 1 and active[0].id == result.revision_id
                assert {h["chunk_id"] for h in await search()} == original_ids
                async with factory() as session, session.begin():
                    await session.execute(
                        text(
                            "UPDATE processing_jobs SET next_retry_at = "
                            "clock_timestamp() - INTERVAL '1 second' "
                            "WHERE id = :id"
                        ),
                        {"id": job_id},
                    )
                retry = await _claim(indexer)
                assert retry.attempt_count == 2 and retry.processing_run_id == run_id
                replacement = await _index(indexer, retry)
                assert {h["chunk_id"] for h in await search()} == original_ids
                assert await _complete(indexer, retry, replacement) is IndexRevisionStatus.ACTIVE
                final_hits = await search()
                assert len(final_hits) == 2
                assert {h["chunk_id"] for h in final_hits}.isdisjoint(original_ids)
                async with factory() as session:
                    assert (await session.get(IndexRevision, result.revision_id)).status != "active"
                    assert (await session.get(ProcessingJob, job_id)).status == "completed"
                    assert {
                        c.id: c.source_provenance
                        for c in await session.scalars(
                            select(CanonicalChunk).where(
                                CanonicalChunk.processing_run_id == artifact.processing_run_id
                            )
                        )
                    } == original_chunks
                async with factory() as session, session.begin():
                    await session.execute(
                        delete(WorkspaceMembership).where(
                            WorkspaceMembership.user_id == viewer_id,
                            WorkspaceMembership.workspace_id == workspace_id,
                        )
                    )
                revoked = await ctx.client.post(
                    "/api/v1/search", json=body, headers=ctx.authorization(ctx.viewer_subject)
                )
                assert revoked.status_code == 403 and "-10 kg" not in revoked.text
            finally:
                for key in keys:
                    await ctx.storage.delete(key)

    asyncio.run(exercise())
