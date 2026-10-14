from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from doclens_ai.core.config import Settings
from doclens_ai.db.session import Database
from doclens_ai.main import create_app
from doclens_ai.models import (
    Document,
    DocumentVersion,
    IndexRevision,
    ProcessingJob,
    ProcessingRun,
    User,
    Workspace,
    WorkspaceMembership,
)
from doclens_ai.security import JwtIdentity
from doclens_ai.services.processing import create_initial_processing_records
from doclens_ai.vector.qdrant import VectorFailure
from tests.api.test_documents_api import StaticVerifier
from tests.integration.test_production_indexing import (
    _claim,
    _complete,
    _extraction_worker,
    _index,
    _index_environment,
    _next_version_or_run,
    _ready,
)

pytestmark = pytest.mark.integration


@asynccontextmanager
async def _api(url, *, document_id=None):
    database = Database(url)
    async with database.session_factory() as session, session.begin():
        if document_id is None:
            workspace = Workspace(name="Readiness")
            session.add(workspace)
            await session.flush()
            document = Document(workspace_id=workspace.id)
            session.add(document)
            await session.flush()
        else:
            document = await session.get(Document, document_id)
        other_workspace = Workspace(name="Other")
        user = User(issuer="https://issuer.test/", subject=uuid4().hex)
        outsider = User(issuer=user.issuer, subject=uuid4().hex)
        session.add_all([other_workspace, user, outsider])
        await session.flush()
        session.add(
            WorkspaceMembership(
                user_id=user.id,
                workspace_id=document.workspace_id,
                role="viewer",
            )
        )
    verifier = StaticVerifier(JwtIdentity(user.issuer, user.subject))
    application = create_app(
        settings=Settings(database_url=url, _env_file=None),
        database=database,
        jwt_verifier=verifier,
    )
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(database.engine.sync_engine, "before_cursor_execute", record)
    try:
        async with application.router.lifespan_context(application):
            async with AsyncClient(
                transport=ASGITransport(app=application), base_url="http://test"
            ) as client:
                yield SimpleNamespace(
                    database=database,
                    client=client,
                    document=document,
                    user=user,
                    outsider=outsider,
                    other_workspace=other_workspace,
                    verifier=verifier,
                    statements=statements,
                )
    finally:
        event.remove(database.engine.sync_engine, "before_cursor_execute", record)
        await database.dispose()


async def _read(ctx, *, workspace_id=None, document_id=None):
    return await ctx.client.get(
        f"/api/v1/workspaces/{workspace_id or ctx.document.workspace_id}"
        f"/documents/{document_id or ctx.document.id}",
        headers={"Authorization": "Bearer test-token"},
    )


async def _flags(ctx):
    response = await _read(ctx)
    assert response.status_code == 200
    assert "private-object-key" not in response.text
    return [v["is_searchable"] for v in response.json()["versions"]]


async def _version(ctx, number=1):
    async with ctx.database.session_factory() as session, session.begin():
        version = DocumentVersion(
            document_id=ctx.document.id,
            version_number=number,
            original_filename="fixture.pdf",
            content_type="application/pdf",
            file_size=20,
            sha256_checksum="a" * 64,
            object_storage_key="private-object-key",
        )
        session.add(version)
        await session.flush()
        run, job = await create_initial_processing_records(session, document_version_id=version.id)
        return SimpleNamespace(id=version.id, number=number, run_id=run.id, job_id=job.id)


async def _state(ctx, version, run_status, job_status, *, stage="indexing"):
    # Persist explicit contract test states under the real database constraints;
    # the separate pipeline test below uses the unchanged coordinator/worker.
    now = datetime.now(UTC)
    async with ctx.database.session_factory() as session, session.begin():
        run = await session.get(ProcessingRun, version.run_id)
        job = await session.get(ProcessingJob, version.job_id)
        run.status, run.stage = run_status, stage
        job.status = job_status
        job.worker_id = "fixture-worker" if job_status == "leased" else None
        job.lease_token = uuid4() if job_status == "leased" else None
        job.leased_at = now if job_status == "leased" else None
        job.lease_expires_at = now + timedelta(minutes=5) if job_status == "leased" else None
        job.next_retry_at = now + timedelta(seconds=1) if job_status == "retry_wait" else None
        job.failure_reason = "fixture_failure" if job_status in {"failed", "retry_wait"} else None
        job.finished_at = now if job_status in {"failed", "completed"} else None


async def _revision(ctx, version, state):
    async with ctx.database.session_factory() as session, session.begin():
        revision = IndexRevision(
            id=uuid4(),
            processing_run_id=version.run_id,
            document_version_id=version.id,
            document_id=ctx.document.id,
            workspace_id=ctx.document.workspace_id,
            document_version_number=version.number,
            lease_token=uuid4(),
            embedding_model_id="fixture-model",
            embedding_model_revision="b" * 40,
            embedding_configuration={"fixture": True},
            embedding_configuration_fingerprint="c" * 64,
            canonical_chunk_set_fingerprint="d" * 64,
            vector_dimension=384,
            collection_name="fixture_collection",
            expected_point_count=2,
        )
        session.add(revision)
        await session.flush()  # The real guard permits INSERT only as CANDIDATE.
        if state in {"verified", "active"}:
            revision.status, revision.verified_point_count = "verified", 2
            revision.verified_at = datetime.now(UTC)
            await session.flush()
        if state == "active":
            revision.status, revision.activated_at = "active", datetime.now(UTC)
        return revision.id


@pytest.mark.parametrize(
    ("run", "job", "revision", "stage", "expected"),
    [
        ("queued", "queued", None, "extraction", False),
        ("queued", "queued", "candidate", "embedding", False),
        ("processing", "leased", "candidate", "indexing", False),
        ("retry_wait", "retry_wait", "candidate", "indexing", False),
        ("failed", "failed", "candidate", "indexing", False),
        ("completed", "completed", None, "indexing", False),
        ("completed", "completed", "candidate", "indexing", False),
        ("completed", "completed", "verified", "indexing", False),
        ("completed", "completed", "active", "indexing", True),
        ("failed", "completed", "active", "indexing", False),
        ("completed", "failed", "active", "indexing", False),
        ("completed", "queued", "active", "indexing", False),
        ("completed", "completed", "active", "embedding", False),
    ],
)
def test_postgresql_readiness_predicate(migrated_database_url, run, job, revision, stage, expected):
    async def exercise():
        async with _api(migrated_database_url) as ctx:
            version = await _version(ctx)
            await _state(ctx, version, run, job, stage=stage)
            if revision:
                await _revision(ctx, version, revision)
            assert await _flags(ctx) == [expected]

    asyncio.run(exercise())


def test_reprocessing_preserves_active_and_reads_are_bounded(migrated_database_url):
    async def exercise():
        async with _api(migrated_database_url) as ctx:
            version = await _version(ctx)
            await _state(ctx, version, "completed", "completed")
            await _revision(ctx, version, "active")
            async with ctx.database.session_factory() as session, session.begin():
                baseline = await session.get(ProcessingRun, version.run_id)
                run = ProcessingRun(
                    document_version_id=version.id,
                    operation_id=uuid4(),
                    operation_kind="reprocess",
                    configuration_version=baseline.configuration_version,
                    configuration_fingerprint=baseline.configuration_fingerprint,
                    stage="embedding",
                    status="queued",
                )
                session.add(run)
                await session.flush()
                job = ProcessingJob(processing_run_id=run.id, status="queued", max_attempts=3)
                session.add(job)
                await session.flush()
                replacement = SimpleNamespace(id=version.id, number=1, run_id=run.id, job_id=job.id)
            await _revision(ctx, replacement, "verified")
            for run_status, job_status in [
                ("queued", "queued"),
                ("processing", "leased"),
                ("retry_wait", "retry_wait"),
                ("failed", "failed"),
            ]:
                await _state(ctx, replacement, run_status, job_status)
                assert await _flags(ctx) == [True]
            for number in range(2, 21):
                await _version(ctx, number)
            ctx.statements.clear()
            first, second = await _read(ctx), await _read(ctx)
            assert first.status_code == second.status_code == 200
            assert first.json() == second.json()
            assert [v["is_searchable"] for v in first.json()["versions"]] == [True] + [False] * 19
            assert len(ctx.statements) == 6  # Three SELECTs per read, independent of version count.
            assert all(s.lstrip().upper().startswith("SELECT") for s in ctx.statements)

    asyncio.run(exercise())


def test_readiness_authorization_and_empty_document(migrated_database_url):
    async def exercise():
        async with _api(migrated_database_url) as ctx:
            assert await _flags(ctx) == []
            version = await _version(ctx)
            await _state(ctx, version, "completed", "completed")
            await _revision(ctx, version, "active")
            assert await _flags(ctx) == [True]  # Viewer is allowed.
            async with ctx.database.session_factory() as session, session.begin():
                foreign = Document(workspace_id=ctx.other_workspace.id)
                session.add(foreign)
                await session.flush()
            assert (await _read(ctx, document_id=foreign.id)).status_code == 404
            assert (await _read(ctx, document_id=uuid4())).status_code == 404
            assert (await _read(ctx, workspace_id=ctx.other_workspace.id)).status_code == 403
            ctx.verifier.identity = JwtIdentity(ctx.outsider.issuer, ctx.outsider.subject)
            response = await _read(ctx)
            assert response.status_code == 403 and "is_searchable" not in response.text
            assert (
                await ctx.client.get(
                    f"/api/v1/workspaces/{ctx.document.workspace_id}/documents/{ctx.document.id}"
                )
            ).status_code == 401

    asyncio.run(exercise())


def test_unverified_or_unactivated_revision_cannot_be_published(migrated_database_url):
    async def exercise():
        async with _api(migrated_database_url) as ctx:
            version = await _version(ctx)
            await _state(ctx, version, "completed", "completed")
            revision_id = await _revision(ctx, version, "candidate")
            async with ctx.database.session_factory() as session:
                revision = await session.get(IndexRevision, revision_id)
                revision.status = "verified"
                revision.verified_at = datetime.now(UTC)
                revision.verified_point_count = 1  # Expected count is two.
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
            assert await _flags(ctx) == [False]
            async with ctx.database.session_factory() as session, session.begin():
                revision = await session.get(IndexRevision, revision_id)
                revision.status, revision.verified_point_count = "verified", 2
                revision.verified_at = datetime.now(UTC)
            assert await _flags(ctx) == [False]
            async with ctx.database.session_factory() as session:
                revision = await session.get(IndexRevision, revision_id)
                revision.status = "active"  # Missing activation timestamp is rejected.
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
            assert await _flags(ctx) == [False]

    asyncio.run(exercise())


@pytest.mark.storage
def test_real_indexing_failed_replacement_and_version_cutover(
    migrated_database_url,
    test_storage_settings,
    monkeypatch,
):
    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as env:
            factory, storage, keys, worker, vector, _ = env
            first = await _ready(factory, storage, keys)
            async with _api(migrated_database_url, document_id=first.document_id) as ctx:
                assert await _flags(ctx) == [False]
                claim = await _claim(worker)
                assert await _flags(ctx) == [False]
                result = await _index(worker, claim)
                assert await _flags(ctx) == [False]  # Verified is not activated.
                await _complete(worker, claim, result)
                assert await _flags(ctx) == [True]
                await _next_version_or_run(factory, first, reprocess=False)
                assert await _flags(ctx) == [True, False]
                assert await _extraction_worker(factory, storage).run_once()
                original = vector.verify

                async def fail(*args):
                    raise VectorFailure("unavailable", retryable=False)

                monkeypatch.setattr(vector, "verify", fail)
                assert await worker.run_once()
                assert await _flags(ctx) == [True, False]
                async with factory() as session:
                    second = await session.scalar(
                        select(DocumentVersion).where(
                            DocumentVersion.document_id == first.document_id,
                            DocumentVersion.version_number == 2,
                        )
                    )
                    failed_run = await session.scalar(
                        select(ProcessingRun).where(
                            ProcessingRun.document_version_id == second.id,
                        )
                    )
                    assert failed_run.status == "failed"
                monkeypatch.setattr(vector, "verify", original)
                await _next_version_or_run(
                    factory,
                    SimpleNamespace(
                        document_version_id=second.id,
                    ),
                    reprocess=True,
                )
                assert await _extraction_worker(factory, storage).run_once()
                claim = await _claim(worker)
                result = await _index(worker, claim)
                assert await _flags(ctx) == [True, False]
                await _complete(worker, claim, result)
                assert await _flags(ctx) == [False, True]
                assert (await _read(ctx)).json() == (await _read(ctx)).json()

    asyncio.run(exercise())
