from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from doclens_ai.core.config import Settings
from doclens_ai.main import create_app
from doclens_ai.models import User, WorkspaceMembership, WorkspaceRole
from doclens_ai.security import JwtIdentity


class StaticVerifier:
    def __init__(self, identity: JwtIdentity) -> None:
        self.identity = identity

    async def verify(self, token: str) -> JwtIdentity:
        assert token == "test-token"
        return self.identity

    async def aclose(self) -> None:
        return None


class FakeSession:
    def __init__(self, results: list[Any]) -> None:
        self.results = results
        self.added: list[Any] = []

    async def scalar(self, statement: Any) -> Any:
        return self.results.pop(0)

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        for value in self.added:
            if value.id is None:
                value.id = uuid4()
            now = datetime.now(UTC)
            if value.created_at is None:
                value.created_at = now
            if value.updated_at is None:
                value.updated_at = now

    async def refresh(self, value: Any) -> None:
        return None


class FakeSessionContext:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeDatabase:
    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def session_factory(self) -> FakeSessionContext:
        return FakeSessionContext(self.session)

    async def dispose(self) -> None:
        return None


def _user() -> User:
    return User(id=uuid4(), issuer="https://issuer.test/", subject="subject-123")


def _membership(user: User, workspace_id: UUID, role: WorkspaceRole) -> WorkspaceMembership:
    return WorkspaceMembership(
        id=uuid4(),
        user_id=user.id,
        workspace_id=workspace_id,
        role=role,
    )


@asynccontextmanager
async def _client(results: list[Any]) -> AsyncIterator[AsyncClient]:
    session = FakeSession(results)
    settings = Settings(
        database_url="postgresql+asyncpg://doclens:local@localhost/doclens",
        _env_file=None,
    )
    verifier = StaticVerifier(JwtIdentity("https://issuer.test/", "subject-123"))
    application = create_app(
        settings=settings,
        database=FakeDatabase(session),  # type: ignore[arg-type]
        jwt_verifier=verifier,  # type: ignore[arg-type]
    )
    transport = ASGITransport(app=application)
    async with application.router.lifespan_context(application):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.anyio
async def test_document_api_requires_bearer_token() -> None:
    workspace_id = uuid4()

    async with _client([]) as client:
        response = await client.post(f"/api/v1/workspaces/{workspace_id}/documents")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.anyio
async def test_missing_oidc_configuration_fails_closed_without_breaking_health() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://doclens:local@localhost/doclens",
        oidc_issuer="https://issuer.test/",
        oidc_audience="doclens-api",
        oidc_jwks_url="https://issuer.test/jwks.json",
        oidc_jwks_timeout_seconds="not-a-number",
        _env_file=None,
    )
    application = create_app(
        settings=settings,
        database=FakeDatabase(FakeSession([])),  # type: ignore[arg-type]
    )
    transport = ASGITransport(app=application)

    async with application.router.lifespan_context(application):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            health = await client.get("/api/v1/health/live")
            protected = await client.post(
                f"/api/v1/workspaces/{uuid4()}/documents",
                headers={"Authorization": "Bearer test-token"},
            )

    assert health.status_code == 200
    assert protected.status_code == 503


@pytest.mark.anyio
async def test_authenticated_nonmember_is_denied() -> None:
    user = _user()
    workspace_id = uuid4()

    async with _client([user, None]) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/documents",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "workspace access denied"}


@pytest.mark.anyio
async def test_viewer_cannot_create_document() -> None:
    user = _user()
    workspace_id = uuid4()
    membership = _membership(user, workspace_id, WorkspaceRole.VIEWER)

    async with _client([user, membership]) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/documents",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 403


@pytest.mark.anyio
@pytest.mark.parametrize("role", [WorkspaceRole.OWNER, WorkspaceRole.EDITOR])
async def test_owner_and_editor_can_create_document(role: WorkspaceRole) -> None:
    user = _user()
    workspace_id = uuid4()
    membership = _membership(user, workspace_id, role)

    async with _client([user, membership]) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/documents",
            headers={"Authorization": "Bearer test-token"},
        )

    assert response.status_code == 201
    assert response.json()["workspace_id"] == str(workspace_id)
    assert response.json()["versions"] == []
