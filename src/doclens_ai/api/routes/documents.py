from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from doclens_ai.api.dependencies import (
    get_current_user,
    get_database_session,
    get_upload_service,
    require_workspace_access,
)
from doclens_ai.models import Document, User
from doclens_ai.services.upload import (
    UploadConflictError,
    UploadNotFoundError,
    UploadService,
    UploadValidationError,
    UploadVerificationError,
)
from doclens_ai.storage.s3 import ObjectStorageError

router = APIRouter(prefix="/workspaces", tags=["documents"])


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_number: int
    original_filename: str
    content_type: str
    file_size: int
    sha256_checksum: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionResponse]


class UploadResponse(BaseModel):
    upload_session_id: UUID
    document_version_id: UUID
    processing_job_id: UUID
    document_id: UUID
    version_number: int
    file_size: int
    sha256_checksum: str


SessionDependency = Annotated[AsyncSession, Depends(get_database_session)]
UserDependency = Annotated[User, Depends(get_current_user)]
UploadServiceDependency = Annotated[UploadService, Depends(get_upload_service)]


@router.post(
    "/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    workspace_id: UUID,
    session: SessionDependency,
    user: UserDependency,
) -> DocumentResponse:
    await require_workspace_access(
        session,
        user_id=user.id,
        workspace_id=workspace_id,
        write=True,
    )
    document = Document(workspace_id=workspace_id)
    session.add(document)
    try:
        await session.commit()
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        ) from error
    return DocumentResponse(
        id=document.id,
        workspace_id=document.workspace_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[],
    )


@router.post(
    "/{workspace_id}/documents/{document_id}/versions",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_version(
    workspace_id: UUID,
    document_id: UUID,
    session: SessionDependency,
    user: UserDependency,
    upload_service: UploadServiceDependency,
    file: Annotated[UploadFile, File()],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> UploadResponse:
    await require_workspace_access(
        session,
        user_id=user.id,
        workspace_id=workspace_id,
        write=True,
    )
    try:
        result = await upload_service.upload_and_confirm(
            workspace_id=workspace_id,
            document_id=document_id,
            idempotency_key=idempotency_key,
            original_filename=file.filename or "",
            content_type=file.content_type or "",
            stream=file.file,
        )
    except UploadConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="upload conflict",
        ) from error
    except UploadNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document not found",
        ) from error
    except UploadValidationError as error:
        raise _upload_validation_http_error(error) from error
    except (ObjectStorageError, UploadVerificationError, SQLAlchemyError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="upload dependency is unavailable",
        ) from error
    finally:
        await file.close()

    return UploadResponse(
        upload_session_id=result.upload_session_id,
        document_version_id=result.document_version_id,
        processing_job_id=result.processing_job_id,
        document_id=result.document_id,
        version_number=result.version_number,
        file_size=result.file_size,
        sha256_checksum=result.sha256_checksum,
    )


@router.get(
    "/{workspace_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    workspace_id: UUID,
    document_id: UUID,
    session: SessionDependency,
    user: UserDependency,
) -> Document:
    await require_workspace_access(
        session,
        user_id=user.id,
        workspace_id=workspace_id,
        write=False,
    )
    try:
        document = await session.scalar(
            select(Document)
            .options(selectinload(Document.versions))
            .where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
            )
        )
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        ) from error
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
    return document


def _upload_validation_http_error(error: UploadValidationError) -> HTTPException:
    message = str(error)
    if "size limit" in message:
        return HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="upload too large",
        )
    unsupported_markers = (
        "supported",
        "content type",
        "signature",
        "end marker",
        "package",
    )
    if any(marker in message for marker in unsupported_markers):
        return HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported document format",
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="invalid upload request",
    )
