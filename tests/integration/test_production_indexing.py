from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

import doclens_ai.services.processing as processing_module
from doclens_ai.models import (
    CanonicalChunk,
    DocumentVersion,
    IndexRevision,
    IndexRevisionStatus,
    ProcessingJob,
    ProcessingRun,
    ProcessingStage,
)
from doclens_ai.services.index_worker import IndexWorker
from doclens_ai.services.indexing import (
    IndexingFailure,
    IndexingFailureCategory,
    IndexingService,
    candidate_points,
    collection_name,
    embedding_identity,
)
from doclens_ai.services.ingestion import IngestionService
from doclens_ai.services.processing import (
    InvalidProcessingTransition,
    LeaseOwnershipError,
    ProcessingCoordinator,
    ProcessingPolicy,
    create_initial_processing_records,
    default_processing_configuration_fingerprint,
)
from doclens_ai.services.worker import IngestionWorker, WorkerSettings
from doclens_ai.vector.qdrant import ProductionQdrant, VectorFailure
from tests.integration.test_worker import _environment, _upload
from tests.unit.test_indexing import FakeEmbedder

pytestmark = [pytest.mark.integration, pytest.mark.storage]


@asynccontextmanager
async def _index_environment(url, storage_settings):
    endpoint = os.getenv("TEST_QDRANT_URL")
    if not endpoint:
        pytest.skip("TEST_QDRANT_URL is not configured")
    provider = FakeEmbedder()
    name = collection_name(embedding_identity(provider)[1], "test_" + uuid4().hex)
    vector = ProductionQdrant(endpoint, name, batch_size=1)
    async with _environment(url, storage_settings) as (factory, storage, keys):
        coordinator = ProcessingCoordinator(
            factory,
            policy=ProcessingPolicy(
                lease_duration=timedelta(seconds=8), retry_base_delay=timedelta(milliseconds=1)
            ),
        )
        service = IndexingService(factory, provider, vector)
        settings = WorkerSettings(
            _env_file=None,
            lease_seconds=8,
            heartbeat_interval_seconds=0.03,
            db_timeout_seconds=2,
            poll_interval_seconds=0.01,
        )
        worker = IndexWorker(coordinator, service, settings=settings, worker_id="index-a")
        try:
            yield factory, storage, keys, worker, vector, provider
        finally:
            await vector.close()
            # Only the unique test-owned collection is removed, never by production code.
            async with httpx.AsyncClient(base_url=endpoint, timeout=5) as client:
                response = await client.delete("/collections/" + name)
                assert response.status_code in {200, 404}


async def _ready(factory, storage, keys):
    uploaded = await _upload(factory, storage, keys)
    assert await _extraction_worker(factory, storage).run_once()
    return uploaded


def _extraction_worker(factory, storage):
    # Real DB/MinIO setup is not a subsecond-heartbeat fault test. Allow Docker load
    # without changing production policy or weakening ownership/completion assertions.
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
    return IngestionWorker(
        coordinator,
        IngestionService(factory, storage),
        settings=settings,
        worker_id="index-test-extraction",
    )


async def _claim(worker):
    claim = await worker.coordinator.claim_next(
        worker_id=worker.worker_id, stages=(ProcessingStage.EMBEDDING, ProcessingStage.INDEXING)
    )
    assert claim is not None
    return claim


async def _index(worker, claim):
    return await worker.indexing.index(
        claim.processing_run_id, worker_id=worker.worker_id, lease_token=claim.lease_token
    )


async def _complete(worker, claim, result):
    return await worker.coordinator.complete(
        job_id=claim.job_id,
        worker_id=worker.worker_id,
        lease_token=claim.lease_token,
        index_revision_id=result.revision_id,
    )


async def _expire(factory, claim):
    async with factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE processing_jobs SET lease_expires_at = "
                "clock_timestamp() - INTERVAL '1 second' WHERE id = :id"
            ),
            {"id": claim.job_id},
        )


async def _snapshot(factory):
    async with factory() as session:
        versions = (
            await session.execute(text("SELECT * FROM document_versions ORDER BY id"))
        ).all()
        chunks = (await session.execute(text("SELECT * FROM canonical_chunks ORDER BY id"))).all()
        return versions, chunks


def test_real_upload_index_complete_idempotency_and_scope(
    migrated_database_url, test_storage_settings
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, provider = env
            first = await _ready(factory, storage, keys)
            second = await _ready(factory, storage, keys)
            before = await _snapshot(factory)
            a = await _claim(worker)
            with pytest.raises(InvalidProcessingTransition):
                await worker.coordinator.complete(
                    job_id=a.job_id, worker_id=worker.worker_id, lease_token=a.lease_token
                )
            result = await _index(worker, a)
            repeated = await _index(worker, a)
            assert repeated.revision_id == result.revision_id
            assert result.indexed_chunks >= 2
            assert await _complete(worker, a, result) is IndexRevisionStatus.ACTIVE
            assert await worker.run_once()
            assert not await worker.run_once()
            assert await _snapshot(factory) == before
            async with factory() as session:
                revisions = list(await session.scalars(select(IndexRevision)))
                assert len(revisions) == 2 and all(r.status == "active" for r in revisions)
                assert len({r.workspace_id for r in revisions}) == 2
                assert {r.document_version_id for r in revisions} == {
                    first.document_version_id,
                    second.document_version_id,
                }
                for revision in revisions:
                    assert revision.expected_point_count == revision.verified_point_count
                    assert revision.verified_at and revision.activated_at
                    job = await session.scalar(
                        select(ProcessingJob).where(
                            ProcessingJob.processing_run_id == revision.processing_run_id
                        )
                    )
                    assert job.status == "completed" and job.attempt_count == 1
                    assert job.lease_token is None
            assert len(asyncio.all_tasks()) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("cut", ["partial", "upsert", "verified"])
def test_crash_recovery_and_late_stale_external_writes(
    migrated_database_url, test_storage_settings, cut
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, provider = env
            await _ready(factory, storage, keys)
            before = await _snapshot(factory)
            a = await _claim(worker)
            candidate = await worker.indexing._prepare(
                a.processing_run_id, worker.worker_id, a.lease_token
            )
            points = candidate_points(
                candidate,
                provider.encode([c.chunk_text for c in candidate.chunks], kind="passage").vectors,
                worker.indexing.fingerprint,
            )
            await vector.ensure_collection()
            await vector.upsert(candidate.revision_id, points[:1] if cut == "partial" else points)
            if cut == "verified":
                await _index(worker, a)
            await _expire(factory, a)
            with pytest.raises(IndexingFailure) as error:
                await _index(worker, a)
            assert error.value.category is IndexingFailureCategory.OWNERSHIP_LOST
            b = await _claim(worker)
            assert b.lease_token != a.lease_token and b.attempt_count == 2
            result = await _index(worker, b)
            assert result.revision_id != candidate.revision_id
            assert await _complete(worker, b, result) is IndexRevisionStatus.ACTIVE
            # An expired process can still reach Qdrant, but only its own UUID namespace.
            await vector.upsert(candidate.revision_id, points)
            with pytest.raises(LeaseOwnershipError):
                await _complete(worker, a, result)
            async with factory() as session:
                active = await session.get(IndexRevision, result.revision_id)
                stale = await session.get(IndexRevision, candidate.revision_id)
                assert active.status == "active" and stale.status != "active"
                assert (await session.get(ProcessingJob, b.job_id)).status == "completed"
            current = await worker.indexing._vector._request(
                "POST",
                "/collections/" + vector.collection + "/points/count",
                json={
                    "exact": True,
                    "filter": {
                        "must": [
                            {
                                "key": "index_revision_id",
                                "match": {"value": str(result.revision_id)},
                            }
                        ]
                    },
                },
            )
            assert current["result"]["count"] == result.indexed_chunks
            assert await _snapshot(factory) == before

    asyncio.run(exercise())


@pytest.mark.parametrize("failure", ["embedding", "invalid", "ensure", "partial", "verify"])
def test_failure_never_completes_and_retry_is_isolated(
    migrated_database_url, test_storage_settings, monkeypatch, failure
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, provider = env
            uploaded = await _ready(factory, storage, keys)
            original_encode, original_upsert = provider.encode, vector.upsert

            async def unavailable(*args, **kwargs):
                raise VectorFailure("vector_unavailable", retryable=True)

            def embedding_failure(*args, **kwargs):
                raise RuntimeError("private document failure")

            async def partial(revision, points):
                await original_upsert(revision, points[:1])
                raise VectorFailure("vector_unavailable", retryable=True)

            with monkeypatch.context() as patch:
                if failure == "embedding":
                    patch.setattr(provider, "encode", embedding_failure)
                elif failure == "invalid":
                    patch.setattr(
                        provider,
                        "encode",
                        lambda *a, **k: type("Batch", (), {"vectors": ((float("nan"),) * 384,)})(),
                    )
                else:
                    patch.setattr(
                        vector,
                        {"ensure": "ensure_collection", "partial": "upsert", "verify": "verify"}[
                            failure
                        ],
                        partial if failure == "partial" else unavailable,
                    )
                assert await worker.run_once()
            async with factory() as session:
                job = await session.get(ProcessingJob, uploaded.processing_job_id)
                assert job.status == ("failed" if failure == "invalid" else "retry_wait")
                assert job.failure_reason and job.lease_token is None
                assert not list(
                    await session.scalars(
                        select(IndexRevision).where(
                            IndexRevision.status.in_(["active", "verified"])
                        )
                    )
                )
            if failure != "invalid":
                assert provider.encode == original_encode
                assert await worker.run_once()
                async with factory() as session:
                    assert (
                        await session.get(ProcessingJob, uploaded.processing_job_id)
                    ).status == "completed"
                    revisions = list(await session.scalars(select(IndexRevision)))
                    assert len(revisions) == 2 and sum(r.status == "active" for r in revisions) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize("corruption", ["missing", "payload", "extra", "dimension"])
def test_real_qdrant_verification_rejects_corruption(
    migrated_database_url, test_storage_settings, monkeypatch, corruption
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, _ = env
            uploaded = await _ready(factory, storage, keys)
            original = vector.verify

            async def corrupt(revision, points):
                path = "/collections/" + vector.collection + "/points"
                if corruption == "missing":
                    await vector._request(
                        "POST", path + "/delete?wait=true", json={"points": [points[0].id]}
                    )
                else:
                    payload = dict(points[0].payload)
                    if corruption == "payload":
                        payload["workspace_id"] = str(uuid4())
                    response = await vector._client.put(
                        path,
                        params={"wait": "true"},
                        json={
                            "points": [
                                {
                                    "id": str(uuid4()) if corruption == "extra" else points[0].id,
                                    "vector": [1.0]
                                    if corruption == "dimension"
                                    else list(points[0].vector),
                                    "payload": payload,
                                }
                            ]
                        },
                    )
                    if corruption == "dimension":
                        assert response.status_code == 400
                        raise VectorFailure("invalid_vector", retryable=False)
                    response.raise_for_status()
                return await original(revision, points)

            monkeypatch.setattr(vector, "verify", corrupt)
            assert await worker.run_once()
            async with factory() as session:
                assert (
                    await session.get(ProcessingJob, uploaded.processing_job_id)
                ).status == "failed"
                revision = await session.scalar(select(IndexRevision))
                assert revision.status == "candidate" and revision.verified_point_count == 0

    asyncio.run(exercise())


async def _next_version_or_run(factory, first, *, reprocess):
    async with factory() as session, session.begin():
        version = await session.get(DocumentVersion, first.document_version_id)
        if reprocess:
            run = ProcessingRun(
                id=uuid4(),
                document_version_id=version.id,
                operation_id=uuid4(),
                operation_kind="reprocess",
                configuration_version="1.0",
                configuration_fingerprint=default_processing_configuration_fingerprint(),
                stage="extraction",
                status="queued",
            )
            session.add(run)
            await session.flush()
            session.add(
                ProcessingJob(
                    processing_run_id=run.id, status="queued", attempt_count=0, max_attempts=3
                )
            )
        else:
            new = DocumentVersion(
                document_id=version.document_id,
                version_number=2,
                original_filename=version.original_filename,
                content_type=version.content_type,
                file_size=version.file_size,
                sha256_checksum=version.sha256_checksum,
                object_storage_key=version.object_storage_key,
            )
            session.add(new)
            await session.flush()
            await create_initial_processing_records(session, document_version_id=new.id)


@pytest.mark.parametrize("reprocess", [False, True])
@pytest.mark.parametrize("newer_first", [False, True])
def test_competing_cutover_never_displaces_newer(
    migrated_database_url, test_storage_settings, reprocess, newer_first
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, _, _ = env
            first = await _ready(factory, storage, keys)
            a = await _claim(worker)
            ra = await _index(worker, a)
            await _next_version_or_run(factory, first, reprocess=reprocess)
            assert await _extraction_worker(factory, storage).run_once()
            b = await _claim(worker)
            rb = await _index(worker, b)
            if newer_first:
                assert await _complete(worker, b, rb) is IndexRevisionStatus.ACTIVE
                assert await _complete(worker, a, ra) is IndexRevisionStatus.SUPERSEDED
            else:
                assert await _complete(worker, a, ra) is IndexRevisionStatus.ACTIVE
                assert await _complete(worker, b, rb) is IndexRevisionStatus.ACTIVE
            async with factory() as session:
                old, new = (
                    await session.get(IndexRevision, ra.revision_id),
                    await session.get(IndexRevision, rb.revision_id),
                )
                assert old.status == "superseded" and new.status == "active"
                assert (old.activated_at is None) == newer_first
                assert (await session.get(ProcessingJob, a.job_id)).status == (
                    "failed" if newer_first else "completed"
                )
                assert (await session.get(ProcessingJob, b.job_id)).status == "completed"

    asyncio.run(exercise())


def test_failed_newer_candidate_preserves_active(
    migrated_database_url, test_storage_settings, monkeypatch
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, _ = env
            first = await _ready(factory, storage, keys)
            assert await worker.run_once()
            async with factory() as session:
                old = await session.scalar(select(IndexRevision))
                active_id = old.id
            await _next_version_or_run(factory, first, reprocess=False)
            assert await _extraction_worker(factory, storage).run_once()

            async def failed(*args):
                raise VectorFailure("unavailable", retryable=True)

            monkeypatch.setattr(vector, "verify", failed)
            assert await worker.run_once()
            async with factory() as session:
                old = await session.get(IndexRevision, active_id)
                assert old.status == "active" and old.superseded_at is None
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(IndexRevision)
                        .where(IndexRevision.status == "active")
                    )
                    == 1
                )

    asyncio.run(exercise())


def test_simultaneous_cutover_and_unique_active_constraint(
    migrated_database_url, test_storage_settings
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, _, _ = env
            first = await _ready(factory, storage, keys)
            a = await _claim(worker)
            ra = await _index(worker, a)
            await _next_version_or_run(factory, first, reprocess=False)
            assert await _extraction_worker(factory, storage).run_once()
            b = await _claim(worker)
            rb = await _index(worker, b)
            await asyncio.wait_for(
                asyncio.gather(_complete(worker, a, ra), _complete(worker, b, rb)), 5
            )
            async with factory() as session:
                revisions = list(await session.scalars(select(IndexRevision)))
                assert sum(r.status == "active" for r in revisions) == 1
                assert (await session.get(IndexRevision, rb.revision_id)).status == "active"
                index = await session.scalar(
                    text(
                        "SELECT indexdef FROM pg_indexes "
                        "WHERE indexname = 'uq_index_revisions_active_document'"
                    )
                )
                assert "UNIQUE" in index and "status" in index and "active" in index

    asyncio.run(exercise())


def test_actual_connection_failure_and_unrelated_document_progress(
    migrated_database_url, test_storage_settings
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, provider = env
            first = await _ready(factory, storage, keys)
            unavailable = ProductionQdrant(
                "http://127.0.0.1:1", vector.collection, timeout_seconds=0.1
            )
            try:
                worker.indexing = IndexingService(factory, provider, unavailable)
                assert await worker.run_once()
            finally:
                await unavailable.close()
            worker.indexing = IndexingService(factory, provider, vector)
            # Keep the failed job in backoff while another document completes.
            async with factory() as session, session.begin():
                await session.execute(
                    text(
                        "UPDATE processing_jobs SET next_retry_at = "
                        "clock_timestamp() + INTERVAL '1 hour' WHERE id = :id"
                    ),
                    {"id": first.processing_job_id},
                )
            second = await _ready(factory, storage, keys)
            assert await worker.run_once()
            async with factory() as session:
                assert (
                    await session.get(ProcessingJob, first.processing_job_id)
                ).status == "retry_wait"
                assert (
                    await session.get(ProcessingJob, second.processing_job_id)
                ).status == "completed"

    asyncio.run(exercise())


def test_reclaim_during_external_verification_fences_final_checkpoint(
    migrated_database_url, test_storage_settings, monkeypatch
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, _ = env
            await _ready(factory, storage, keys)
            a = await _claim(worker)
            original = vector.verify
            replacement_id = None

            async def reclaim(revision, points):
                nonlocal replacement_id
                verified = await original(revision, points)
                await _expire(factory, a)
                b = await _claim(worker)
                with monkeypatch.context() as patch:
                    patch.setattr(vector, "verify", original)
                    result = await _index(worker, b)
                replacement_id = result.revision_id
                await _complete(worker, b, result)
                return verified

            monkeypatch.setattr(vector, "verify", reclaim)
            with pytest.raises(IndexingFailure) as error:
                await _index(worker, a)
            assert error.value.category is IndexingFailureCategory.OWNERSHIP_LOST
            async with factory() as session:
                assert (await session.get(IndexRevision, replacement_id)).status == "active"
                stale = await session.scalar(
                    select(IndexRevision).where(IndexRevision.lease_token == a.lease_token)
                )
                assert stale.status == "candidate" and stale.verified_point_count == 0

    asyncio.run(exercise())


@pytest.mark.parametrize("reclaim", [False, True])
def test_heartbeat_loss_does_not_activate_verified_candidate(
    migrated_database_url, test_storage_settings, monkeypatch, reclaim
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, _, _ = env
            await _ready(factory, storage, keys)
            verified, release, lost = asyncio.Event(), asyncio.Event(), asyncio.Event()
            original = worker.indexing.index

            async def paused(*args, **kwargs):
                result = await original(*args, **kwargs)
                verified.set()
                await release.wait()
                return result

            async def broken(**kwargs):
                lost.set()
                raise RuntimeError("uncertain ownership")

            monkeypatch.setattr(worker.indexing, "index", paused)
            monkeypatch.setattr(worker.coordinator, "heartbeat", broken)
            task = asyncio.create_task(worker.run_once())
            try:
                await asyncio.wait_for(verified.wait(), 10)
                await asyncio.wait_for(lost.wait(), 5)
                async with factory() as session:
                    revision = await session.scalar(select(IndexRevision))
                    assert revision.status == "verified"
                    job = await session.scalar(select(ProcessingJob))
                    claim = type("Claim", (), {"job_id": job.id})()
                if reclaim:
                    await _expire(factory, claim)
                    monkeypatch.setattr(worker.indexing, "index", original)
                    replacement = await _claim(worker)
                    result = await _index(worker, replacement)
                    await _complete(worker, replacement, result)
                release.set()
                await task
                async with factory() as session:
                    assert (await session.get(IndexRevision, revision.id)).status == "verified"
                    assert (await session.get(ProcessingJob, job.id)).status == (
                        "completed" if reclaim else "leased"
                    )
                assert len(asyncio.all_tasks()) == 1
            finally:
                release.set()
                await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())


def test_long_index_network_wait_has_no_locks_and_heartbeat_renews(
    migrated_database_url, test_storage_settings, monkeypatch
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, _ = env
            await _ready(factory, storage, keys)
            original = vector.verify

            async def slow(revision, points):
                async with factory() as session:
                    job = await session.scalar(select(ProcessingJob))
                    expiry = job.lease_expires_at
                    await session.scalar(
                        select(func.pg_sleep_until(expiry + timedelta(milliseconds=100)))
                    )
                    job = await session.get(ProcessingJob, job.id, populate_existing=True)
                    assert job.lease_expires_at > await session.scalar(
                        select(func.clock_timestamp())
                    )
                    # This lock succeeds while inference/network holds no business-row locks.
                    assert await session.scalar(
                        select(ProcessingRun.id).with_for_update(nowait=True)
                    )
                return await original(revision, points)

            monkeypatch.setattr(vector, "verify", slow)
            assert await worker.run_once()
            async with factory() as session:
                assert (await session.scalar(select(ProcessingJob))).status == "completed"

    asyncio.run(exercise())


def test_activation_expiry_after_flush_rolls_back(
    migrated_database_url, test_storage_settings, monkeypatch
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, _, _ = env
            await _ready(factory, storage, keys)
            claim = await _claim(worker)
            result = await _index(worker, claim)
            original = processing_module._processing_now

            async def expire(session, value=None):
                revision = await session.get(IndexRevision, result.revision_id)
                if revision.status == "active":
                    return claim.lease_expires_at
                return await original(session, value)

            monkeypatch.setattr(processing_module, "_processing_now", expire)
            with pytest.raises(LeaseOwnershipError):
                await _complete(worker, claim, result)
            async with factory() as session:
                assert (await session.get(IndexRevision, result.revision_id)).status == "verified"
                assert (await session.get(ProcessingJob, claim.job_id)).status == "leased"

    asyncio.run(exercise())


def test_index_revision_migration_and_guards(
    disposable_database_url, alembic_runner, test_storage_settings
):
    alembic_runner(disposable_database_url, "upgrade", "head")

    async def exercise():
        async with _index_environment(disposable_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, _, _ = env
            await _ready(factory, storage, keys)
            assert await worker.run_once()
            async with factory() as session:
                revision_id = await session.scalar(select(IndexRevision.id))
                count = await session.scalar(select(func.count()).select_from(CanonicalChunk))
            for assignment in [
                "workspace_id = gen_random_uuid()",
                "expected_point_count = 9",
                "embedding_model_revision = repeat('a', 40)",
                "status = 'candidate'",
                "activated_at = clock_timestamp()",
            ]:
                async with factory() as session:
                    with pytest.raises(IntegrityError):
                        await session.execute(
                            text("UPDATE index_revisions SET " + assignment + " WHERE id = :id"),
                            {"id": revision_id},
                        )
                    await session.rollback()
            return count

    count = asyncio.run(exercise())
    alembic_runner(disposable_database_url, "check")
    alembic_runner(disposable_database_url, "downgrade", "0006_canonical_chunks")

    async def preserved():
        engine = create_async_engine(disposable_database_url)
        try:
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(text("SELECT to_regclass('index_revisions')")) is None
                )
                assert (
                    await connection.scalar(text("SELECT count(*) FROM canonical_chunks")) == count
                )
                assert await connection.scalar(text("SELECT count(*) FROM document_versions")) == 1
        finally:
            await engine.dispose()

    asyncio.run(preserved())
    alembic_runner(disposable_database_url, "upgrade", "head")
    alembic_runner(disposable_database_url, "check")
