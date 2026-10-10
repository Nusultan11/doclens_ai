from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from sqlalchemy import text
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


@pytest.mark.integration
def test_document_domain_migration_upgrade_check_and_downgrade(
    disposable_database_url: str,
    alembic_runner: Callable[..., None],
) -> None:
    expected_tables = {"workspaces", "documents", "document_versions"}

    alembic_runner(disposable_database_url, "upgrade", "head")
    assert asyncio.run(_domain_tables(disposable_database_url)) == expected_tables

    alembic_runner(disposable_database_url, "check")

    alembic_runner(disposable_database_url, "downgrade", "base")
    assert asyncio.run(_domain_tables(disposable_database_url)) == set()
