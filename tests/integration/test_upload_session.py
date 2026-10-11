from __future__ import annotations

import asyncio
import hashlib
import io
from collections.abc import Callable
from itertools import chain
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from doclens_ai.models import Document, DocumentVersion, UploadSession, UploadStatus, Workspace
from doclens_ai.services.upload import (
    PDF_CONTENT_TYPE,
    UploadConflictError,
    UploadNotFoundError,
    UploadService,
)
from doclens_ai.storage.s3 import ObjectMetadata, ObjectStorageError


def _pdf(label: str) -> bytes:
    return f"%PDF-1.7\n{label}\n%%EOF\n".encode()


class MemoryStorage:
    def __init__(self) -> None:
        self.available = True
        self.objects: dict[str, tuple[bytes, str, str]] = {}

    async def put_stream(
        self,
        key: str,
        stream: io.BytesIO,
        *,
        content_type: str,
        sha256_checksum: str,
    ) -> None:
        if not self.available:
            raise ObjectStorageError("storage unavailable")
        stream.seek(0)
        self.objects[key] = (stream.read(), content_type, sha256_checksum)

    async def inspect(self, key: str) -> ObjectMetadata:
        if not self.available:
            raise ObjectStorageError("storage unavailable")
        content, content_type, checksum = self.objects[key]
        return ObjectMetadata(
            size=len(content),
            content_type=content_type,
            metadata={"sha256": checksum},
        )

    async def sha256(self, key: str, *, chunk_size: int = 1024 * 1024) -> str:
        if not self.available:
            raise ObjectStorageError("storage unavailable")
        return hashlib.sha256(self.objects[key][0]).hexdigest()


async def _create_document(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID]:
    async with session_factory() as session, session.begin():
        workspace = Workspace(name=f"Upload workspace {uuid4()}")
        document = Document(workspace=workspace)
        session.add(document)
        await session.flush()
        return workspace.id, document.id


def _service(
    database_url: str,
) -> tuple[object, async_sessionmaker[AsyncSession], MemoryStorage, UploadService]:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    storage = MemoryStorage()
    service = UploadService(session_factory, storage, max_upload_size_bytes=1024 * 1024)
    return engine, session_factory, storage, service


@pytest.mark.integration
def test_upload_lifecycle_is_idempotent_scoped_and_keeps_versions_immutable(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine, session_factory, _storage, service = _service(migrated_database_url)
        try:
            workspace_id, document_id = await _create_document(session_factory)
            other_workspace_id, _ = await _create_document(session_factory)
            first_content = _pdf("first")

            first = await service.upload_and_confirm(
                workspace_id=workspace_id,
                document_id=document_id,
                idempotency_key="stable-request-1",
                original_filename="first.pdf",
                content_type=PDF_CONTENT_TYPE,
                stream=io.BytesIO(first_content),
                expected_file_size=len(first_content),
                expected_sha256_checksum=hashlib.sha256(first_content).hexdigest(),
            )
            repeated = await service.upload_and_confirm(
                workspace_id=workspace_id,
                document_id=document_id,
                idempotency_key="stable-request-1",
                original_filename="first.pdf",
                content_type=PDF_CONTENT_TYPE,
                stream=io.BytesIO(first_content),
            )
            with pytest.raises(UploadConflictError, match="different content"):
                await service.upload_and_confirm(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    idempotency_key="stable-request-1",
                    original_filename="first.pdf",
                    content_type=PDF_CONTENT_TYPE,
                    stream=io.BytesIO(_pdf("different")),
                )
            second = await service.upload_and_confirm(
                workspace_id=workspace_id,
                document_id=document_id,
                idempotency_key="stable-request-2",
                original_filename="second.pdf",
                content_type=PDF_CONTENT_TYPE,
                stream=io.BytesIO(_pdf("second")),
            )

            assert repeated == first
            assert first.version_number == 1
            assert second.version_number == 2
            assert first.object_storage_key.startswith(
                f"workspaces/{workspace_id}/documents/{document_id}/uploads/"
            )

            with pytest.raises(UploadNotFoundError):
                await service.upload_and_confirm(
                    workspace_id=other_workspace_id,
                    document_id=document_id,
                    idempotency_key="wrong-workspace",
                    original_filename="scope.pdf",
                    content_type=PDF_CONTENT_TYPE,
                    stream=io.BytesIO(_pdf("scope")),
                )

            async with session_factory() as session:
                assert await session.scalar(select(func.count(UploadSession.id))) == 2
                assert await session.scalar(select(func.count(DocumentVersion.id))) == 2
                persisted = await session.get(DocumentVersion, first.document_version_id)
                assert persisted is not None
                persisted.original_filename = "mutated.pdf"
                with pytest.raises(IntegrityError, match="immutable"):
                    await session.commit()
                await session.rollback()

            async with session_factory() as session:
                persisted = await session.get(DocumentVersion, first.document_version_id)
                assert persisted is not None
                assert persisted.original_filename == "first.pdf"
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_storage_failure_creates_no_version_and_retry_completes(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine, session_factory, storage, service = _service(migrated_database_url)
        try:
            workspace_id, document_id = await _create_document(session_factory)
            storage.available = False
            with pytest.raises(ObjectStorageError, match="unavailable"):
                await service.upload_and_confirm(
                    workspace_id=workspace_id,
                    document_id=document_id,
                    idempotency_key="retryable",
                    original_filename="retry.pdf",
                    content_type=PDF_CONTENT_TYPE,
                    stream=io.BytesIO(_pdf("retry")),
                )

            async with session_factory() as session:
                attempt = await session.scalar(select(UploadSession))
                assert attempt is not None
                assert attempt.status == UploadStatus.FAILED
                assert attempt.failure_code == "storage_or_verification_failed"
                assert await session.scalar(select(func.count(DocumentVersion.id))) == 0

            storage.available = True
            result = await service.upload_and_confirm(
                workspace_id=workspace_id,
                document_id=document_id,
                idempotency_key="retryable",
                original_filename="retry.pdf",
                content_type=PDF_CONTENT_TYPE,
                stream=io.BytesIO(_pdf("retry")),
            )
            assert result.version_number == 1
            async with session_factory() as session:
                assert await session.scalar(select(func.count(UploadSession.id))) == 1
                assert await session.scalar(select(func.count(DocumentVersion.id))) == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_concurrent_confirmation_does_not_duplicate_versions(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine, session_factory, _storage, service = _service(migrated_database_url)
        try:
            workspace_id, document_id = await _create_document(session_factory)
            content = _pdf("same concurrent content")

            same_results = await asyncio.gather(
                *[
                    service.upload_and_confirm(
                        workspace_id=workspace_id,
                        document_id=document_id,
                        idempotency_key="same-request",
                        original_filename="same.pdf",
                        content_type=PDF_CONTENT_TYPE,
                        stream=io.BytesIO(content),
                    )
                    for _ in range(2)
                ]
            )
            assert same_results[0].document_version_id == same_results[1].document_version_id

            distinct_results = await asyncio.gather(
                *[
                    service.upload_and_confirm(
                        workspace_id=workspace_id,
                        document_id=document_id,
                        idempotency_key=f"distinct-{number}",
                        original_filename=f"distinct-{number}.pdf",
                        content_type=PDF_CONTENT_TYPE,
                        stream=io.BytesIO(_pdf(f"distinct {number}")),
                    )
                    for number in (1, 2)
                ]
            )
            assert {result.version_number for result in distinct_results} == {2, 3}
            async with session_factory() as session:
                assert await session.scalar(select(func.count(DocumentVersion.id))) == 3
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_database_commit_failure_returns_no_false_success_and_can_retry(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine, session_factory, storage, service = _service(migrated_database_url)
        try:
            workspace_id, document_id = await _create_document(session_factory)

            def fail_version_commit(session: Session) -> None:
                instances = chain(session.new, session.identity_map.values())
                if any(isinstance(instance, DocumentVersion) for instance in instances):
                    raise RuntimeError("injected database commit failure")

            event.listen(Session, "before_commit", fail_version_commit)
            try:
                with pytest.raises(RuntimeError, match="injected database commit failure"):
                    await service.upload_and_confirm(
                        workspace_id=workspace_id,
                        document_id=document_id,
                        idempotency_key="database-retry",
                        original_filename="database.pdf",
                        content_type=PDF_CONTENT_TYPE,
                        stream=io.BytesIO(_pdf("database")),
                    )
            finally:
                event.remove(Session, "before_commit", fail_version_commit)

            async with session_factory() as session:
                attempt = await session.scalar(select(UploadSession))
                assert attempt is not None
                assert attempt.status == UploadStatus.UPLOADED
                assert await session.scalar(select(func.count(DocumentVersion.id))) == 0
                assert attempt.object_storage_key in storage.objects

            result = await service.upload_and_confirm(
                workspace_id=workspace_id,
                document_id=document_id,
                idempotency_key="database-retry",
                original_filename="database.pdf",
                content_type=PDF_CONTENT_TYPE,
                stream=io.BytesIO(_pdf("database")),
            )
            assert result.version_number == 1
        finally:
            await engine.dispose()

    asyncio.run(exercise())


async def _table_exists(database_url: str, table_name: str) -> bool:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return bool(
                await connection.scalar(
                    text("SELECT to_regclass(:table_name) IS NOT NULL"),
                    {"table_name": f"public.{table_name}"},
                )
            )
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_upload_session_migration_upgrade_check_and_downgrade_preserves_domain_data(
    disposable_database_url: str,
    alembic_runner: Callable[..., None],
) -> None:
    async def seed_and_check_constraints() -> None:
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
            alembic_runner(disposable_database_url, "upgrade", "head")
            async with engine.connect() as connection:
                transaction = await connection.begin()
                with pytest.raises(IntegrityError):
                    await connection.execute(
                        text(
                            "INSERT INTO upload_sessions "
                            "(id, document_id, idempotency_key, object_storage_key, status, "
                            "original_filename, content_type, file_size, sha256_checksum) "
                            "VALUES (:id, :document_id, 'key', 'object', 'invalid', "
                            "'file.pdf', 'application/pdf', 1, :checksum)"
                        ),
                        {
                            "id": uuid4(),
                            "document_id": document_id,
                            "checksum": "a" * 64,
                        },
                    )
                await transaction.rollback()
        finally:
            await engine.dispose()

    alembic_runner(disposable_database_url, "upgrade", "0002_version_immutability")
    asyncio.run(seed_and_check_constraints())
    assert asyncio.run(_table_exists(disposable_database_url, "upload_sessions"))
    alembic_runner(disposable_database_url, "check")

    alembic_runner(disposable_database_url, "downgrade", "0002_version_immutability")
    assert not asyncio.run(_table_exists(disposable_database_url, "upload_sessions"))

    async def assert_domain_data_remains() -> None:
        engine = create_async_engine(disposable_database_url)
        try:
            async with engine.connect() as connection:
                assert await connection.scalar(text("SELECT count(*) FROM documents")) == 1
                assert bool(
                    await connection.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_trigger "
                            "WHERE tgname = 'trg_document_versions_immutable')"
                        )
                    )
                )
        finally:
            await engine.dispose()

    asyncio.run(assert_domain_data_remains())
