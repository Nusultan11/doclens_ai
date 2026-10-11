from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doclens_ai.db.base import Base


class UploadStatus(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadSession(Base):
    """Mutable coordination state for one idempotent upload attempt."""

    __tablename__ = "upload_sessions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "idempotency_key",
            name="uq_upload_sessions_document_idempotency_key",
        ),
        UniqueConstraint("object_storage_key", name="uq_upload_sessions_object_storage_key"),
        UniqueConstraint(
            "committed_document_version_id",
            name="uq_upload_sessions_committed_version",
        ),
        CheckConstraint(
            "status IN ('pending', 'uploaded', 'completed', 'failed')",
            name="ck_upload_sessions_status",
        ),
        CheckConstraint("file_size > 0", name="ck_upload_sessions_file_size_positive"),
        CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_upload_sessions_idempotency_key_not_blank",
        ),
        CheckConstraint(
            "length(btrim(original_filename)) > 0",
            name="ck_upload_sessions_filename_not_blank",
        ),
        CheckConstraint(
            "length(btrim(content_type)) > 0",
            name="ck_upload_sessions_content_type_not_blank",
        ),
        CheckConstraint(
            "sha256_checksum ~ '^[0-9a-f]{64}$'",
            name="ck_upload_sessions_sha256_lower_hex",
        ),
        CheckConstraint(
            "length(btrim(object_storage_key)) > 0",
            name="ck_upload_sessions_storage_key_not_blank",
        ),
        CheckConstraint(
            "(status = 'completed' AND committed_document_version_id IS NOT NULL) OR "
            "(status <> 'completed' AND committed_document_version_id IS NULL)",
            name="ck_upload_sessions_completion_reference",
        ),
        Index("ix_upload_sessions_document_status", "document_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    object_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=UploadStatus.PENDING, server_default="pending"
    )
    original_filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    committed_document_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    document = relationship("Document")
    committed_document_version = relationship("DocumentVersion")
