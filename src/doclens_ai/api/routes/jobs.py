from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from doclens_ai.api.dependencies import get_current_user, get_database_session
from doclens_ai.models import (
    Document,
    DocumentVersion,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingRun,
    ProcessingStage,
    User,
    WorkspaceMembership,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class ProcessingJobResponse(BaseModel):
    id: UUID
    status: ProcessingJobStatus
    stage: ProcessingStage
    attempt_count: int
    created_at: datetime
    updated_at: datetime
    leased_at: datetime | None
    last_heartbeat_at: datetime | None
    lease_expires_at: datetime | None
    next_retry_at: datetime | None
    finished_at: datetime | None
    failure_reason: str | None


SessionDependency = Annotated[AsyncSession, Depends(get_database_session)]
UserDependency = Annotated[User, Depends(get_current_user)]


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_processing_job(
    job_id: UUID,
    session: SessionDependency,
    user: UserDependency,
) -> ProcessingJobResponse:
    try:
        row = (
            await session.execute(
                select(ProcessingJob, ProcessingRun)
                .join(ProcessingRun, ProcessingRun.id == ProcessingJob.processing_run_id)
                .join(
                    DocumentVersion,
                    DocumentVersion.id == ProcessingRun.document_version_id,
                )
                .join(Document, Document.id == DocumentVersion.document_id)
                .join(
                    WorkspaceMembership,
                    WorkspaceMembership.workspace_id == Document.workspace_id,
                )
                .where(
                    ProcessingJob.id == job_id,
                    WorkspaceMembership.user_id == user.id,
                )
            )
        ).first()
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database is unavailable",
        ) from error
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="processing job not found",
        )
    job, run = row
    return ProcessingJobResponse(
        id=job.id,
        status=ProcessingJobStatus(job.status),
        stage=ProcessingStage(run.stage),
        attempt_count=job.attempt_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        leased_at=job.leased_at,
        last_heartbeat_at=job.last_heartbeat_at,
        lease_expires_at=job.lease_expires_at,
        next_retry_at=job.next_retry_at,
        finished_at=job.finished_at,
        failure_reason=job.failure_reason,
    )
