from __future__ import annotations

import asyncio
import base64
import io
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from doclens_ai.core.config import Settings
from doclens_ai.db.session import Database
from doclens_ai.main import create_app
from doclens_ai.models import (
    DocumentVersion,
    ProcessingJob,
    ProcessingRun,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)
from doclens_ai.security import JwtVerifier
from doclens_ai.services.upload import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    UploadService,
)
from doclens_ai.storage.config import StorageSettings
from doclens_ai.storage.s3 import ObjectStorageError, S3ObjectStorage

ISSUER = "https://issuer.test/"
AUDIENCE = "doclens-api"
JWKS_URL = "https://issuer.test/.well-known/jwks.json"
REQUIRED_SCOPE = "doclens:documents"
KEY_ID = "integration-key"


def _base64url(number: int) -> str:
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _package(required_member: str) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(required_member, "<root/>")
    return output.getvalue()


FILES = [
    ("source.pdf", b"%PDF-1.4\n%%EOF", PDF_CONTENT_TYPE),
    ("source.docx", _package("word/document.xml"), DOCX_CONTENT_TYPE),
    ("source.xlsx", _package("xl/workbook.xml"), XLSX_CONTENT_TYPE),
]


class UnavailableStorage:
    async def put_stream(self, *args: object, **kwargs: object) -> None:
        raise ObjectStorageError("simulated storage outage")

    async def inspect(self, key: str) -> object:
        raise AssertionError("inspect must not run after failed upload")

    async def sha256(self, key: str, *, chunk_size: int = 1024 * 1024) -> str:
        raise AssertionError("sha256 must not run after failed upload")


@dataclass
class ApiContext:
    client: AsyncClient
    database: Database
    storage: S3ObjectStorage
    private_key: rsa.RSAPrivateKey
    workspace_id: UUID
    other_workspace_id: UUID
    owner_subject: str
    editor_subject: str
    viewer_subject: str
    outsider_subject: str
    application: Any

    def authorization(self, subject: str) -> dict[str, str]:
        token = jwt.encode(
            {
                "iss": ISSUER,
                "aud": AUDIENCE,
                "sub": subject,
                "scope": REQUIRED_SCOPE,
                "exp": datetime.now(UTC) + timedelta(minutes=5),
            },
            self.private_key,
            algorithm="RS256",
            headers={"kid": KEY_ID},
        )
        return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _api_context(
    database_url: str,
    storage_settings: StorageSettings,
) -> AsyncIterator[ApiContext]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": KEY_ID,
        "use": "sig",
        "alg": "RS256",
        "n": _base64url(public_numbers.n),
        "e": _base64url(public_numbers.e),
    }
    jwks_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"keys": [jwk]})
        )
    )
    verifier = JwtVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url=JWKS_URL,
        required_scope=REQUIRED_SCOPE,
        timeout_seconds=1,
        cache_ttl_seconds=300,
        client=jwks_client,
    )
    database = Database(database_url)
    storage = S3ObjectStorage(storage_settings)
    await storage.ensure_private_bucket()
    settings = Settings(
        database_url=database_url,
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_jwks_url=JWKS_URL,
        _env_file=None,
    )
    application = create_app(
        settings=settings,
        database=database,
        jwt_verifier=verifier,
    )
    application.state.upload_service = UploadService(
        database.session_factory,
        storage,
        max_upload_size_bytes=storage_settings.max_upload_size_bytes,
    )

    workspace = Workspace(name="Primary")
    other_workspace = Workspace(name="Other")
    identities = {
        "owner": User(issuer=ISSUER, subject="owner-subject"),
        "editor": User(issuer=ISSUER, subject="editor-subject"),
        "viewer": User(issuer=ISSUER, subject="viewer-subject"),
        "outsider": User(issuer=ISSUER, subject="outsider-subject"),
    }
    async with database.session_factory() as session, session.begin():
        session.add_all([workspace, other_workspace, *identities.values()])
        await session.flush()
        session.add_all(
            [
                WorkspaceMembership(
                    user_id=identities["owner"].id,
                    workspace_id=workspace.id,
                    role=WorkspaceRole.OWNER,
                ),
                WorkspaceMembership(
                    user_id=identities["editor"].id,
                    workspace_id=workspace.id,
                    role=WorkspaceRole.EDITOR,
                ),
                WorkspaceMembership(
                    user_id=identities["viewer"].id,
                    workspace_id=workspace.id,
                    role=WorkspaceRole.VIEWER,
                ),
                WorkspaceMembership(
                    user_id=identities["owner"].id,
                    workspace_id=other_workspace.id,
                    role=WorkspaceRole.OWNER,
                ),
                WorkspaceMembership(
                    user_id=identities["outsider"].id,
                    workspace_id=other_workspace.id,
                    role=WorkspaceRole.VIEWER,
                ),
            ]
        )

    transport = ASGITransport(app=application)
    try:
        async with application.router.lifespan_context(application):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield ApiContext(
                    client=client,
                    database=database,
                    storage=storage,
                    private_key=private_key,
                    workspace_id=workspace.id,
                    other_workspace_id=other_workspace.id,
                    owner_subject=identities["owner"].subject,
                    editor_subject=identities["editor"].subject,
                    viewer_subject=identities["viewer"].subject,
                    outsider_subject=identities["outsider"].subject,
                    application=application,
                )
    finally:
        await jwks_client.aclose()


async def _create_document(context: ApiContext, subject: str | None = None) -> UUID:
    response = await context.client.post(
        f"/api/v1/workspaces/{context.workspace_id}/documents",
        headers=context.authorization(subject or context.owner_subject),
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["id"])


@pytest.mark.integration
@pytest.mark.storage
@pytest.mark.anyio
async def test_authenticated_document_access_is_workspace_scoped(
    migrated_database_url: str,
    test_storage_settings: StorageSettings,
) -> None:
    async with _api_context(migrated_database_url, test_storage_settings) as context:
        path = f"/api/v1/workspaces/{context.workspace_id}/documents"
        assert (await context.client.post(path)).status_code == 401

        outsider = await context.client.post(
            path,
            headers=context.authorization(context.outsider_subject),
        )
        assert outsider.status_code == 403

        viewer = await context.client.post(
            path,
            headers=context.authorization(context.viewer_subject),
        )
        assert viewer.status_code == 403

        document_id = await _create_document(context, context.editor_subject)
        read = await context.client.get(
            f"{path}/{document_id}",
            headers=context.authorization(context.viewer_subject),
        )
        assert read.status_code == 200
        assert read.json()["id"] == str(document_id)
        assert "object_storage_key" not in read.text

        cross_workspace = await context.client.get(
            f"/api/v1/workspaces/{context.other_workspace_id}/documents/{document_id}",
            headers=context.authorization(context.owner_subject),
        )
        assert cross_workspace.status_code == 404


@pytest.mark.integration
@pytest.mark.storage
@pytest.mark.anyio
async def test_supported_uploads_and_idempotency(
    migrated_database_url: str,
    test_storage_settings: StorageSettings,
) -> None:
    async with _api_context(migrated_database_url, test_storage_settings) as context:
        document_id = await _create_document(context)
        path = (
            f"/api/v1/workspaces/{context.workspace_id}/documents/"
            f"{document_id}/versions"
        )
        for index, (filename, content, content_type) in enumerate(FILES, start=1):
            headers = context.authorization(context.owner_subject) | {
                "Idempotency-Key": f"format-{index}"
            }
            response = await context.client.post(
                path,
                headers=headers,
                files={"file": (filename, content, content_type)},
            )
            assert response.status_code == 201, response.text
            assert response.json()["version_number"] == index
            assert response.json()["processing_job_id"]

            retry = await context.client.post(
                path,
                headers=headers,
                files={"file": (filename, content, content_type)},
            )
            assert retry.status_code == 201
            assert retry.json()["document_version_id"] == response.json()[
                "document_version_id"
            ]
            assert retry.json()["processing_job_id"] == response.json()[
                "processing_job_id"
            ]

            if index == 1:
                job_id = response.json()["processing_job_id"]
                job = await context.client.get(
                    f"/api/v1/jobs/{job_id}",
                    headers=context.authorization(context.viewer_subject),
                )
                assert job.status_code == 200
                assert job.json()["status"] == "queued"
                assert job.json()["stage"] == "extraction"
                assert job.json()["attempt_count"] == 0
                assert "worker_id" not in job.text
                assert "lease_token" not in job.text
                assert "object_storage_key" not in job.text

                cross_workspace = await context.client.get(
                    f"/api/v1/jobs/{job_id}",
                    headers=context.authorization(context.outsider_subject),
                )
                assert cross_workspace.status_code == 404

        conflict = await context.client.post(
            path,
            headers=context.authorization(context.owner_subject)
            | {"Idempotency-Key": "format-1"},
            files={"file": ("different.pdf", b"%PDF-1.7\n%%EOF", PDF_CONTENT_TYPE)},
        )
        assert conflict.status_code == 409

        metadata = await context.client.get(
            f"/api/v1/workspaces/{context.workspace_id}/documents/{document_id}",
            headers=context.authorization(context.viewer_subject),
        )
        assert metadata.status_code == 200
        assert len(metadata.json()["versions"]) == 3
        assert "object_storage_key" not in metadata.text


@pytest.mark.integration
@pytest.mark.storage
@pytest.mark.anyio
async def test_upload_enforces_actual_size_and_type(
    migrated_database_url: str,
    test_storage_settings: StorageSettings,
) -> None:
    async with _api_context(migrated_database_url, test_storage_settings) as context:
        document_id = await _create_document(context)
        context.application.state.upload_service = UploadService(
            context.database.session_factory,
            context.storage,
            max_upload_size_bytes=16,
        )
        path = (
            f"/api/v1/workspaces/{context.workspace_id}/documents/"
            f"{document_id}/versions"
        )
        oversized = await context.client.post(
            path,
            headers=context.authorization(context.owner_subject)
            | {"Idempotency-Key": "oversized", "Content-Length": "1"},
            files={"file": ("large.pdf", b"%PDF-" + b"x" * 32 + b"%%EOF", PDF_CONTENT_TYPE)},
        )
        assert oversized.status_code == 413

        unsupported = await context.client.post(
            path,
            headers=context.authorization(context.owner_subject)
            | {"Idempotency-Key": "unsupported"},
            files={"file": ("notes.txt", b"plain text", "text/plain")},
        )
        assert unsupported.status_code == 415


@pytest.mark.integration
@pytest.mark.storage
@pytest.mark.anyio
async def test_concurrent_same_key_returns_one_version(
    migrated_database_url: str,
    test_storage_settings: StorageSettings,
) -> None:
    async with _api_context(migrated_database_url, test_storage_settings) as context:
        document_id = await _create_document(context)
        path = (
            f"/api/v1/workspaces/{context.workspace_id}/documents/"
            f"{document_id}/versions"
        )
        headers = context.authorization(context.owner_subject) | {
            "Idempotency-Key": "concurrent"
        }

        async def upload() -> httpx.Response:
            return await context.client.post(
                path,
                headers=headers,
                files={"file": FILES[0]},
            )

        first, second = await asyncio.gather(upload(), upload())
        assert first.status_code == second.status_code == 201
        assert first.json()["document_version_id"] == second.json()[
            "document_version_id"
        ]


@pytest.mark.integration
@pytest.mark.storage
@pytest.mark.anyio
async def test_storage_outage_is_sanitized_and_does_not_create_version(
    migrated_database_url: str,
    test_storage_settings: StorageSettings,
) -> None:
    async with _api_context(migrated_database_url, test_storage_settings) as context:
        document_id = await _create_document(context)
        context.application.state.upload_service = UploadService(
            context.database.session_factory,
            UnavailableStorage(),  # type: ignore[arg-type]
            max_upload_size_bytes=1024,
        )
        path = (
            f"/api/v1/workspaces/{context.workspace_id}/documents/"
            f"{document_id}/versions"
        )
        response = await context.client.post(
            path,
            headers=context.authorization(context.owner_subject)
            | {"Idempotency-Key": "storage-down"},
            files={"file": FILES[0]},
        )
        assert response.status_code == 503
        assert response.json() == {"detail": "upload dependency is unavailable"}

        metadata = await context.client.get(
            f"/api/v1/workspaces/{context.workspace_id}/documents/{document_id}",
            headers=context.authorization(context.owner_subject),
        )
        assert metadata.status_code == 200
        assert metadata.json()["versions"] == []
        async with context.database.session_factory() as session:
            assert await session.scalar(select(func.count(DocumentVersion.id))) == 0
            assert await session.scalar(select(func.count(ProcessingRun.id))) == 0
            assert await session.scalar(select(func.count(ProcessingJob.id))) == 0
