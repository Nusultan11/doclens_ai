from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine


async def _domain_tables(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT tablename FROM pg_catalog.pg_tables "
                    "WHERE schemaname = 'public' AND tablename IN "
                    "('workspaces', 'documents', 'document_versions')"
                )
            )
            return set(result.scalars())
    finally:
        await engine.dispose()


async def _insert_document_version(database_url: str) -> UUID:
    workspace_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("INSERT INTO workspaces (id, name) VALUES (:id, :name)"),
                {"id": workspace_id, "name": "Migration test"},
            )
            await connection.execute(
                text("INSERT INTO documents (id, workspace_id) VALUES (:id, :workspace_id)"),
                {"id": document_id, "workspace_id": workspace_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO document_versions "
                    "(id, document_id, version_number, original_filename, content_type, "
                    "file_size, sha256_checksum, object_storage_key) VALUES "
                    "(:id, :document_id, 1, 'original.pdf', 'application/pdf', 10, "
                    ":checksum, 'migration/original.pdf')"
                ),
                {"id": version_id, "document_id": document_id, "checksum": "c" * 64},
            )
        return version_id
    finally:
        await engine.dispose()


async def _update_filename(database_url: str, version_id: UUID, filename: str) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE document_versions SET original_filename = :filename "
                    "WHERE id = :version_id"
                ),
                {"filename": filename, "version_id": version_id},
            )
    finally:
        await engine.dispose()


async def _version_filename(database_url: str, version_id: UUID) -> str:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            filename = await connection.scalar(
                text(
                    "SELECT original_filename FROM document_versions WHERE id = :version_id"
                ),
                {"version_id": version_id},
            )
            assert isinstance(filename, str)
            return filename
    finally:
        await engine.dispose()


async def _immutability_trigger_exists(database_url: str) -> bool:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_trigger "
                    "WHERE tgname = 'trg_document_versions_immutable' "
                    "AND tgrelid = 'document_versions'::regclass)"
                )
            )
            return bool(exists)
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_document_domain_migration_upgrade_check_and_downgrade(
    disposable_database_url: str,
    alembic_runner: Callable[..., None],
) -> None:
    expected_tables = {"workspaces", "documents", "document_versions"}

    alembic_runner(disposable_database_url, "upgrade", "0001_document_domain")
    assert asyncio.run(_domain_tables(disposable_database_url)) == expected_tables
    version_id = asyncio.run(_insert_document_version(disposable_database_url))
    asyncio.run(_update_filename(disposable_database_url, version_id, "before-trigger.pdf"))

    alembic_runner(disposable_database_url, "upgrade", "head")
    assert asyncio.run(_immutability_trigger_exists(disposable_database_url)) is True
    with pytest.raises(IntegrityError, match="immutable"):
        asyncio.run(_update_filename(disposable_database_url, version_id, "blocked.pdf"))
    assert (
        asyncio.run(_version_filename(disposable_database_url, version_id))
        == "before-trigger.pdf"
    )

    alembic_runner(disposable_database_url, "check")

    alembic_runner(disposable_database_url, "downgrade", "0001_document_domain")
    assert asyncio.run(_immutability_trigger_exists(disposable_database_url)) is False
    asyncio.run(_update_filename(disposable_database_url, version_id, "after-downgrade.pdf"))
    assert (
        asyncio.run(_version_filename(disposable_database_url, version_id))
        == "after-downgrade.pdf"
    )

    alembic_runner(disposable_database_url, "downgrade", "base")
    assert asyncio.run(_domain_tables(disposable_database_url)) == set()
