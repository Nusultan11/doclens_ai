from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from doclens_ai.storage.config import StorageSettings

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://doclens:doclens-local@localhost:5432/doclens_test",
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    return database_url


async def _execute_admin_sql(database_url: str, statement: str) -> None:
    admin_url = make_url(database_url).set(database="postgres")
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


@pytest.fixture
def disposable_database_url(test_database_url: str) -> Iterator[str]:
    database_name = f"doclens_test_{uuid4().hex}"
    database_url = make_url(test_database_url).set(database=database_name)
    rendered_url = database_url.render_as_string(hide_password=False)

    asyncio.run(_execute_admin_sql(test_database_url, f'CREATE DATABASE "{database_name}"'))
    try:
        yield rendered_url
    finally:
        asyncio.run(
            _execute_admin_sql(
                test_database_url,
                f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)',
            )
        )


@pytest.fixture
def alembic_runner() -> Callable[..., None]:
    repository_root = Path(__file__).resolve().parents[1]

    def run(database_url: str, *arguments: str) -> None:
        environment = os.environ.copy()
        environment["DATABASE_URL"] = database_url
        subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=repository_root,
            env=environment,
            check=True,
        )

    return run


@pytest.fixture
def migrated_database_url(
    disposable_database_url: str,
    alembic_runner: Callable[..., None],
) -> str:
    alembic_runner(disposable_database_url, "upgrade", "head")
    return disposable_database_url


@pytest.fixture
def test_storage_settings() -> StorageSettings:
    endpoint_url = os.getenv("TEST_S3_ENDPOINT_URL")
    access_key = os.getenv("TEST_S3_ACCESS_KEY")
    secret_key = os.getenv("TEST_S3_SECRET_KEY")
    bucket_name = os.getenv("TEST_S3_BUCKET_NAME")
    if not all((endpoint_url, access_key, secret_key, bucket_name)):
        pytest.skip("TEST_S3_ENDPOINT_URL/access key/secret key/bucket name are not configured")
    return StorageSettings(
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=bucket_name,
        region=os.getenv("TEST_S3_REGION") or None,
        secure=os.getenv("TEST_S3_SECURE", "false"),
        connect_timeout_seconds=1,
        read_timeout_seconds=5,
    )
