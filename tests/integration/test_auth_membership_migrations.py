from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine


async def _tables(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT tablename FROM pg_catalog.pg_tables "
                    "WHERE schemaname = 'public' AND tablename IN "
                    "('users', 'workspace_memberships')"
                )
            )
            return set(result.scalars())
    finally:
        await engine.dispose()


async def _insert_workspace(database_url: str) -> tuple[object, object, object]:
    workspace_id = uuid4()
    user_id = uuid4()
    membership_id = uuid4()
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text("INSERT INTO workspaces (id, name) VALUES (:id, 'Auth migration')"),
                {"id": workspace_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO users (id, issuer, subject) "
                    "VALUES (:id, 'https://issuer.test/', 'subject-1')"
                ),
                {"id": user_id},
            )
            await connection.execute(
                text(
                    "INSERT INTO workspace_memberships "
                    "(id, user_id, workspace_id, role) "
                    "VALUES (:id, :user_id, :workspace_id, 'owner')"
                ),
                {
                    "id": membership_id,
                    "user_id": user_id,
                    "workspace_id": workspace_id,
                },
            )
        return workspace_id, user_id, membership_id
    finally:
        await engine.dispose()


async def _workspace_exists(database_url: str, workspace_id: object) -> bool:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            return bool(
                await connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM workspaces WHERE id = :id)"),
                    {"id": workspace_id},
                )
            )
    finally:
        await engine.dispose()


async def _insert_invalid_role(database_url: str, user_id: object, workspace_id: object) -> None:
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO workspace_memberships "
                    "(id, user_id, workspace_id, role) "
                    "VALUES (:id, :user_id, :workspace_id, 'administrator')"
                ),
                {"id": uuid4(), "user_id": user_id, "workspace_id": workspace_id},
            )
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_auth_membership_migration_upgrade_downgrade_and_constraints(
    disposable_database_url: str,
    alembic_runner: Callable[..., None],
) -> None:
    alembic_runner(disposable_database_url, "upgrade", "0003_upload_sessions")
    assert asyncio.run(_tables(disposable_database_url)) == set()

    alembic_runner(disposable_database_url, "upgrade", "head")
    assert asyncio.run(_tables(disposable_database_url)) == {
        "users",
        "workspace_memberships",
    }
    workspace_id, user_id, _ = asyncio.run(_insert_workspace(disposable_database_url))
    with pytest.raises(IntegrityError, match="ck_workspace_memberships_role"):
        asyncio.run(_insert_invalid_role(disposable_database_url, user_id, workspace_id))

    alembic_runner(disposable_database_url, "check")
    alembic_runner(disposable_database_url, "downgrade", "0003_upload_sessions")
    assert asyncio.run(_tables(disposable_database_url)) == set()
    assert asyncio.run(_workspace_exists(disposable_database_url, workspace_id)) is True

    alembic_runner(disposable_database_url, "upgrade", "head")
    assert asyncio.run(_tables(disposable_database_url)) == {
        "users",
        "workspace_memberships",
    }
