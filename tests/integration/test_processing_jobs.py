from __future__ import annotations

import asyncio
import hashlib
import io
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from doclens_ai.models import (
    Document,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingOperationKind,
    ProcessingRun,
    ProcessingStage,
    ProcessingStatus,
    Workspace,
)
from doclens_ai.services.processing import (
    InvalidProcessingTransition,
    LeaseOwnershipError,
    ProcessingCoordinator,
    ProcessingPolicy,
)
from doclens_ai.services.upload import PDF_CONTENT_TYPE, UploadService
from doclens_ai.storage.s3 import ObjectMetadata


def _pdf(label: str) -> bytes:
    return f"%PDF-1.7\n{label}\n%%EOF\n".encode()


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str, str]] = {}

    async def put_stream(
        self,
        key: str,
        stream: io.BytesIO,
        *,
        content_type: str,
        sha256_checksum: str,
    ) -> None:
        stream.seek(0)
        self.objects[key] = (stream.read(), content_type, sha256_checksum)

    async def inspect(self, key: str) -> ObjectMetadata:
        content, content_type, checksum = self.objects[key]
        return ObjectMetadata(
            size=len(content),
            content_type=content_type,
            metadata={"sha256": checksum},
        )

    async def sha256(self, key: str, *, chunk_size: int = 1024 * 1024) -> str:
        return hashlib.sha256(self.objects[key][0]).hexdigest()


async def _uploaded_job(
    database_url: str,
    *,
    max_attempts: int = 3,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession], UUID]:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session, session.begin():
        workspace = Workspace(name=f"Processing workspace {uuid4()}")
        document = Document(workspace=workspace)
        session.add(document)
        await session.flush()
        workspace_id = workspace.id
        document_id = document.id

    result = await UploadService(
        session_factory,
        MemoryStorage(),
        max_upload_size_bytes=1024 * 1024,
        processing_max_attempts=max_attempts,
    ).upload_and_confirm(
        workspace_id=workspace_id,
        document_id=document_id,
        idempotency_key="processing-job",
        original_filename="source.pdf",
        content_type=PDF_CONTENT_TYPE,
        stream=io.BytesIO(_pdf("processing")),
    )
    return engine, session_factory, result.processing_job_id


@pytest.mark.integration
def test_competing_claims_expired_lease_recovery_and_stale_fencing(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine, session_factory, job_id = await _uploaded_job(migrated_database_url)
        policy = ProcessingPolicy(lease_duration=timedelta(seconds=30))
        first_coordinator = ProcessingCoordinator(session_factory, policy=policy)
        second_coordinator = ProcessingCoordinator(session_factory, policy=policy)
        started_at = datetime(2026, 1, 1, tzinfo=UTC)
        try:
            claims = await asyncio.gather(
                first_coordinator.claim_next(worker_id="worker-a", now=started_at),
                second_coordinator.claim_next(worker_id="worker-b", now=started_at),
            )
            claimed = next(item for item in claims if item is not None)
            assert sum(item is not None for item in claims) == 1
            assert claimed.job_id == job_id
            first_worker = "worker-a" if claims[0] is not None else "worker-b"

            renewed_until = await (
                first_coordinator if first_worker == "worker-a" else second_coordinator
            ).heartbeat(
                job_id=job_id,
                worker_id=first_worker,
                lease_token=claimed.lease_token,
                now=started_at + timedelta(seconds=10),
            )
            assert renewed_until == started_at + timedelta(seconds=40)

            recovered = await second_coordinator.claim_next(
                worker_id="worker-recovery",
                now=started_at + timedelta(seconds=41),
            )
            assert recovered is not None
            assert recovered.job_id == job_id
            assert recovered.attempt_count == 2
            assert recovered.lease_token != claimed.lease_token

            with pytest.raises(LeaseOwnershipError):
                await first_coordinator.heartbeat(
                    job_id=job_id,
                    worker_id=first_worker,
                    lease_token=claimed.lease_token,
                    now=started_at + timedelta(seconds=42),
                )
            assert (
                await second_coordinator.heartbeat(
                    job_id=job_id,
                    worker_id="worker-recovery",
                    lease_token=recovered.lease_token,
                    now=started_at + timedelta(seconds=42),
                )
                == started_at + timedelta(seconds=72)
            )
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_retry_backoff_attempt_limit_and_terminal_jobs(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine, session_factory, job_id = await _uploaded_job(
            migrated_database_url,
            max_attempts=2,
        )
        policy = ProcessingPolicy(
            lease_duration=timedelta(seconds=30),
            retry_base_delay=timedelta(seconds=10),
            retry_max_delay=timedelta(seconds=20),
        )
        coordinator = ProcessingCoordinator(session_factory, policy=policy)
        started_at = datetime(2026, 2, 1, tzinfo=UTC)
        try:
            first = await coordinator.claim_next(worker_id="worker-a", now=started_at)
            assert first is not None
            with pytest.raises(InvalidProcessingTransition, match="indexing"):
                await coordinator.complete(
                    job_id=job_id,
                    worker_id="worker-a",
                    lease_token=first.lease_token,
                    now=started_at + timedelta(milliseconds=500),
                )
            assert (
                await coordinator.fail_attempt(
                    job_id=job_id,
                    worker_id="worker-a",
                    lease_token=first.lease_token,
                    failure_reason="parser_unavailable",
                    now=started_at + timedelta(seconds=1),
                )
                == ProcessingJobStatus.RETRY_WAIT
            )
            assert (
                await coordinator.claim_next(
                    worker_id="worker-b",
                    now=started_at + timedelta(seconds=10),
                )
                is None
            )
            second = await coordinator.claim_next(
                worker_id="worker-b",
                now=started_at + timedelta(seconds=11),
            )
            assert second is not None
            assert second.attempt_count == 2
            assert (
                await coordinator.fail_attempt(
                    job_id=job_id,
                    worker_id="worker-b",
                    lease_token=second.lease_token,
                    failure_reason="parser_unavailable",
                    now=started_at + timedelta(seconds=12),
                )
                == ProcessingJobStatus.FAILED
            )
            assert (
                await coordinator.claim_next(
                    worker_id="worker-c",
                    now=started_at + timedelta(days=1),
                )
                is None
            )

            async with session_factory() as session:
                job = await session.get(ProcessingJob, job_id)
                assert job is not None
                run = await session.get(ProcessingRun, job.processing_run_id)
                assert run is not None
                assert job.status == ProcessingJobStatus.FAILED
                assert job.failure_reason == "parser_unavailable"
                assert job.attempt_count == job.max_attempts == 2
                assert run.status == ProcessingStatus.FAILED
                assert await session.scalar(select(func.count(ProcessingJob.id))) == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


async def _processing_tables(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT tablename FROM pg_catalog.pg_tables "
                    "WHERE schemaname = 'public' "
                    "AND tablename IN ('processing_runs', 'processing_jobs')"
                )
            )
            return set(result.scalars())
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_processing_migration_backfills_and_downgrades_without_losing_versions(
    disposable_database_url: str,
    alembic_runner: Callable[..., None],
) -> None:
    alembic_runner(disposable_database_url, "upgrade", "0004_auth_memberships")
    version_id = uuid4()

    async def seed_version() -> None:
        engine = create_async_engine(disposable_database_url)
        try:
            async with engine.begin() as connection:
                workspace_id = uuid4()
                document_id = uuid4()
                await connection.execute(
                    text("INSERT INTO workspaces (id, name) VALUES (:id, 'Preserved')"),
                    {"id": workspace_id},
                )
                await connection.execute(
                    text(
                        "INSERT INTO documents (id, workspace_id) "
                        "VALUES (:id, :workspace_id)"
                    ),
                    {"id": document_id, "workspace_id": workspace_id},
                )
                await connection.execute(
                    text(
                        "INSERT INTO document_versions "
                        "(id, document_id, version_number, original_filename, content_type, "
                        "file_size, sha256_checksum, object_storage_key) VALUES "
                        "(:id, :document_id, 1, 'source.pdf', 'application/pdf', 10, "
                        ":checksum, 'preserved/source.pdf')"
                    ),
                    {
                        "id": version_id,
                        "document_id": document_id,
                        "checksum": "a" * 64,
                    },
                )
        finally:
            await engine.dispose()

    asyncio.run(seed_version())
    alembic_runner(disposable_database_url, "upgrade", "head")
    assert asyncio.run(_processing_tables(disposable_database_url)) == {
        "processing_runs",
        "processing_jobs",
    }

    async def verify_backfill_and_constraints() -> None:
        engine = create_async_engine(disposable_database_url)
        try:
            async with engine.connect() as connection:
                run = (
                    await connection.execute(
                        text(
                            "SELECT id, operation_id, operation_kind, stage, status, "
                            "configuration_fingerprint FROM processing_runs "
                            "WHERE document_version_id = :version_id"
                        ),
                        {"version_id": version_id},
                    )
                ).one()
                assert run.operation_id == version_id
                assert run.operation_kind == ProcessingOperationKind.INITIAL
                assert run.stage == ProcessingStage.EXTRACTION
                assert run.status == ProcessingStatus.QUEUED
                assert len(run.configuration_fingerprint) == 64
                assert (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM processing_jobs "
                            "WHERE processing_run_id = :run_id"
                        ),
                        {"run_id": run.id},
                    )
                    == 1
                )
                await connection.commit()

                transaction = await connection.begin()
                with pytest.raises(IntegrityError, match="immutable"):
                    await connection.execute(
                        text(
                            "UPDATE processing_runs SET configuration_version = 'changed' "
                            "WHERE id = :run_id"
                        ),
                        {"run_id": run.id},
                    )
                await transaction.rollback()

                transaction = await connection.begin()
                with pytest.raises(IntegrityError):
                    await connection.execute(
                        text(
                            "INSERT INTO processing_runs "
                            "(id, document_version_id, operation_id, operation_kind, "
                            "configuration_version, configuration_fingerprint, stage, status) "
                            "VALUES (:id, :version_id, :operation_id, 'initial', '1.0', "
                            ":fingerprint, 'extraction', 'queued')"
                        ),
                        {
                            "id": uuid4(),
                            "version_id": version_id,
                            "operation_id": uuid4(),
                            "fingerprint": "b" * 64,
                        },
                    )
                await transaction.rollback()

                async with connection.begin():
                    await connection.execute(
                        text(
                            "INSERT INTO processing_runs "
                            "(id, document_version_id, operation_id, operation_kind, "
                            "configuration_version, configuration_fingerprint, stage, status) "
                            "VALUES (:id, :version_id, :operation_id, 'reprocess', '1.0', "
                            ":fingerprint, 'extraction', 'queued')"
                        ),
                        {
                            "id": uuid4(),
                            "version_id": version_id,
                            "operation_id": uuid4(),
                            "fingerprint": "c" * 64,
                        },
                    )
        finally:
            await engine.dispose()

    asyncio.run(verify_backfill_and_constraints())
    alembic_runner(disposable_database_url, "check")
    alembic_runner(disposable_database_url, "downgrade", "0004_auth_memberships")
    assert asyncio.run(_processing_tables(disposable_database_url)) == set()

    async def version_remains() -> bool:
        engine = create_async_engine(disposable_database_url)
        try:
            async with engine.connect() as connection:
                return bool(
                    await connection.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM document_versions "
                            "WHERE id = :version_id)"
                        ),
                        {"version_id": version_id},
                    )
                )
        finally:
            await engine.dispose()

    assert asyncio.run(version_remains()) is True
