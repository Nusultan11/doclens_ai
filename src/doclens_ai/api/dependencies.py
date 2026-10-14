from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from botocore.exceptions import BotoCoreError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from doclens_ai.models import User, WorkspaceMembership, WorkspaceRole
from doclens_ai.security import IdentityProviderUnavailable, InvalidAccessToken, JwtVerifier
from doclens_ai.services.upload import UploadService
from doclens_ai.storage.config import get_storage_settings
from doclens_ai.storage.s3 import S3ObjectStorage

bearer_scheme = HTTPBearer(auto_error=False)


def _authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.database.session_factory() as session:
        yield session


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _authentication_error()

    verifier: JwtVerifier | None = request.app.state.jwt_verifier
    if verifier is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication service is unavailable",
        )
    try:
        identity = await verifier.verify(credentials.credentials)
    except InvalidAccessToken as error:
        raise _authentication_error() from error
    except IdentityProviderUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="authentication service is unavailable",
        ) from error

    try:
        user = await session.scalar(
            select(User).where(
                User.issuer == identity.issuer,
                User.subject == identity.subject,
            )
        )
    except (SQLAlchemyError, OSError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        ) from error
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="workspace access denied",
        )
    return user


def role_allows(role: str, *, write: bool) -> bool:
    if write:
        return role in {WorkspaceRole.OWNER, WorkspaceRole.EDITOR}
    return role in {WorkspaceRole.OWNER, WorkspaceRole.EDITOR, WorkspaceRole.VIEWER}


async def require_workspace_access(
    session: AsyncSession,
    *,
    user_id: UUID,
    workspace_id: UUID,
    write: bool,
) -> WorkspaceMembership:
    try:
        membership = await session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace_id,
            )
        )
    except (SQLAlchemyError, OSError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        ) from error
    if membership is None or not role_allows(membership.role, write=write):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="workspace access denied",
        )
    return membership


def get_upload_service(request: Request) -> UploadService:
    existing: UploadService | None = getattr(request.app.state, "upload_service", None)
    if existing is not None:
        return existing
    try:
        settings = get_storage_settings()
        service = UploadService(
            request.app.state.database.session_factory,
            S3ObjectStorage(settings),
            max_upload_size_bytes=settings.max_upload_size_bytes,
        )
    except (BotoCoreError, ValidationError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="object storage is unavailable",
        ) from error
    request.app.state.upload_service = service
    return service


def get_retrieval_service(request: Request):
    service = getattr(request.app.state, "retrieval_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="search service is unavailable")
    return service
