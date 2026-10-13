from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doclens_ai.db.base import Base


class ProcessingOperationKind(StrEnum):
    INITIAL = "initial"
    REPROCESS = "reprocess"


class ProcessingStage(StrEnum):
    EXTRACTION = "extraction"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"


class ProcessingStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRY_WAIT = "retry_wait"
    FAILED = "failed"
    COMPLETED = "completed"


class ProcessingJobStatus(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RETRY_WAIT = "retry_wait"
    FAILED = "failed"
    COMPLETED = "completed"


class ProcessingRun(Base):
    """Durable processing identity and current pipeline state."""

    __tablename__ = "processing_runs"
    __table_args__ = (
        UniqueConstraint("operation_id", name="uq_processing_runs_operation_id"),
        CheckConstraint(
            "operation_kind IN ('initial', 'reprocess')",
            name="ck_processing_runs_operation_kind",
        ),
        CheckConstraint(
            "length(btrim(configuration_version)) > 0",
            name="ck_processing_runs_configuration_version_not_blank",
        ),
        CheckConstraint(
            "configuration_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_processing_runs_configuration_fingerprint_lower_hex",
        ),
        CheckConstraint(
            "stage IN ('extraction', 'cleaning', 'chunking', 'embedding', 'indexing')",
            name="ck_processing_runs_stage",
        ),
        CheckConstraint(
            "status IN ('queued', 'processing', 'retry_wait', 'failed', 'completed')",
            name="ck_processing_runs_status",
        ),
        CheckConstraint(
            "error_code IS NULL OR error_code ~ '^[a-z0-9][a-z0-9_]{0,63}$'",
            name="ck_processing_runs_error_code",
        ),
        Index("ix_processing_runs_document_version_id", "document_version_id"),
        Index("ix_processing_runs_status_stage", "status", "stage"),
        Index(
            "uq_processing_runs_initial_version",
            "document_version_id",
            unique=True,
            postgresql_where=text("operation_kind = 'initial'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    operation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    document_version = relationship("DocumentVersion")
    job: Mapped[ProcessingJob] = relationship(
        back_populates="processing_run",
        uselist=False,
        passive_deletes=True,
    )


class ProcessingJob(Base):
    """PostgreSQL-backed queue, lease, and retry state for one processing run."""

    __tablename__ = "processing_jobs"
    __table_args__ = (
        UniqueConstraint("processing_run_id", name="uq_processing_jobs_processing_run_id"),
        CheckConstraint(
            "status IN ('queued', 'leased', 'retry_wait', 'failed', 'completed')",
            name="ck_processing_jobs_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_processing_jobs_attempt_nonnegative"),
        CheckConstraint("max_attempts > 0", name="ck_processing_jobs_max_attempts_positive"),
        CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_processing_jobs_attempt_within_limit",
        ),
        CheckConstraint(
            "worker_id IS NULL OR length(btrim(worker_id)) > 0",
            name="ck_processing_jobs_worker_not_blank",
        ),
        CheckConstraint(
            "failure_reason IS NULL OR "
            "failure_reason ~ '^[a-z0-9][a-z0-9_]{0,63}$'",
            name="ck_processing_jobs_failure_reason",
        ),
        CheckConstraint(
            "(status = 'leased' AND worker_id IS NOT NULL AND lease_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL AND leased_at IS NOT NULL "
            "AND next_retry_at IS NULL AND finished_at IS NULL) OR "
            "(status <> 'leased' AND worker_id IS NULL AND lease_token IS NULL "
            "AND lease_expires_at IS NULL)",
            name="ck_processing_jobs_lease_state",
        ),
        CheckConstraint(
            "(status = 'retry_wait' AND next_retry_at IS NOT NULL "
            "AND failure_reason IS NOT NULL) OR "
            "(status <> 'retry_wait' AND next_retry_at IS NULL)",
            name="ck_processing_jobs_retry_state",
        ),
        CheckConstraint(
            "(status IN ('failed', 'completed') AND finished_at IS NOT NULL) OR "
            "(status NOT IN ('failed', 'completed') AND finished_at IS NULL)",
            name="ck_processing_jobs_terminal_state",
        ),
        CheckConstraint(
            "status <> 'failed' OR failure_reason IS NOT NULL",
            name="ck_processing_jobs_failed_reason",
        ),
        Index(
            "ix_processing_jobs_status_retry_created",
            "status",
            "next_retry_at",
            "created_at",
        ),
        Index("ix_processing_jobs_lease_expires_at", "lease_expires_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    processing_run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProcessingJobStatus.QUEUED,
        server_default="queued",
    )
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    leased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    processing_run: Mapped[ProcessingRun] = relationship(back_populates="job")
