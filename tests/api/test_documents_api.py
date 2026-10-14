from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from doclens_ai.core.config import Settings
from doclens_ai.main import create_app
from doclens_ai.models import Document, DocumentVersion, User, WorkspaceMembership, WorkspaceRole
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
    def __init__(self, results: list[Any], *, searchable_ids: set[UUID] | None = None) -> None:
        self.results = results
        self.added: list[Any] = []
        self.statements: list[Any] = []
        self.searchable_ids = searchable_ids or set()

    async def scalar(self, statement: Any) -> Any:
        self.statements.append(statement)
        return self.results.pop(0)

    async def execute(self, statement: Any) -> Any:
        self.statements.append(statement)
        document = self.results.pop(0)
        if isinstance(document, Exception):
            raise document
        rows = (
            []
            if document is None
            else [
                (document, version, version.id in self.searchable_ids)
                for version in document.versions
            ]
        )
        if document is not None and not document.versions:
            rows = [(document, None, False)]
        return SimpleNamespace(all=lambda: rows)

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
async def _client(results: list[Any] | FakeSession) -> AsyncIterator[AsyncClient]:
    session = results if isinstance(results, FakeSession) else FakeSession(results)
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


def _document(workspace_id: UUID, version_count: int = 2) -> Document:
    now = datetime.now(UTC)
    document = Document(id=uuid4(), workspace_id=workspace_id, created_at=now, updated_at=now)
    document.versions = [
        DocumentVersion(
            id=uuid4(),
            document_id=document.id,
            version_number=number,
            original_filename=f"source-{number}.pdf",
            content_type="application/pdf",
            file_size=20,
            sha256_checksum="a" * 64,
            object_storage_key="private-object-key",
            created_at=now,
        )
        for number in range(1, version_count + 1)
    ]
    return document


@pytest.mark.anyio
@pytest.mark.parametrize("role", list(WorkspaceRole))
@pytest.mark.parametrize("version_count", [0, 2, 20])
async def test_get_document_readiness_schema_and_bounded_query(role, version_count) -> None:
    user, workspace_id = _user(), uuid4()
    document = _document(workspace_id, version_count)
    active = {document.versions[-1].id} if version_count else set()
    session = FakeSession(
        [user, _membership(user, workspace_id, role), document], searchable_ids=active
    )
    async with _client(session) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/documents/{document.id}",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"id", "workspace_id", "created_at", "updated_at", "versions"}
    assert len(data["versions"]) == version_count
    for version in data["versions"]:
        assert set(version) == {
            "id",
            "version_number",
            "original_filename",
            "content_type",
            "file_size",
            "sha256_checksum",
            "created_at",
            "is_searchable",
        }
        assert type(version["is_searchable"]) is bool
        assert version["is_searchable"] == (UUID(version["id"]) in active)
    assert "private-object-key" not in response.text
    assert len(session.statements) == 3  # Identity, membership, one metadata/readiness SELECT.
    sql = str(session.statements[-1])
    assert "EXISTS" in sql and "processing_jobs" in sql and "index_revisions" in sql
    assert not session.added


@pytest.mark.anyio
@pytest.mark.parametrize("outcome", ["nonmember", "missing", "unavailable"])
async def test_get_document_preserves_authorization_and_sanitized_errors(outcome) -> None:
    user, workspace_id = _user(), uuid4()
    results = (
        [user, None]
        if outcome == "nonmember"
        else [
            user,
            _membership(user, workspace_id, WorkspaceRole.VIEWER),
            None if outcome == "missing" else SQLAlchemyError("private database detail"),
        ]
    )
    async with _client(results) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/documents/{uuid4()}",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == {"nonmember": 403, "missing": 404, "unavailable": 503}[outcome]
    assert "private database detail" not in response.text


@pytest.mark.anyio
async def test_document_version_openapi_requires_searchable_boolean() -> None:
    async with _client([]) as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()["components"]["schemas"]["DocumentVersionResponse"]
    assert "is_searchable" in schema["required"]
    assert schema["properties"]["is_searchable"]["type"] == "boolean"
    assert "object_storage_key" not in schema["properties"]
