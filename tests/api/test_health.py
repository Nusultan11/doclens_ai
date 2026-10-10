from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from doclens_ai.core.config import Settings
from doclens_ai.main import create_app


class FakeDatabase:
    def __init__(self, probe_error: Exception | None = None) -> None:
        self.probe_error = probe_error
        self.probe_calls = 0
        self.disposed = False

    async def probe(self) -> None:
        self.probe_calls += 1
        if self.probe_error is not None:
            raise self.probe_error

    async def dispose(self) -> None:
        self.disposed = True


@asynccontextmanager
async def build_client(database: FakeDatabase) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        database_url="postgresql+asyncpg://doclens:local@localhost/doclens",
        _env_file=None,
    )
    application = create_app(settings=settings, database=database)  # type: ignore[arg-type]
    transport = ASGITransport(app=application)

    async with application.router.lifespan_context(application):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.anyio
async def test_liveness_does_not_probe_database() -> None:
    database = FakeDatabase(probe_error=RuntimeError("database unavailable"))

    async with build_client(database) as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert database.probe_calls == 0
    assert database.disposed is True


@pytest.mark.anyio
async def test_readiness_is_healthy_when_database_probe_succeeds() -> None:
    database = FakeDatabase()

    async with build_client(database) as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "healthy"}
    assert database.probe_calls == 1


@pytest.mark.anyio
async def test_readiness_is_safe_when_database_probe_fails() -> None:
    secret_error = RuntimeError(
        "connection failed for postgresql://admin:supersecret@database/internal"
    )
    database = FakeDatabase(probe_error=secret_error)

    async with build_client(database) as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "unavailable"}
    assert "supersecret" not in response.text
    assert "postgresql" not in response.text
