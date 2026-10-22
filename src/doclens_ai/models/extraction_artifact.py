"""Durable extraction snapshots, separate from canonical/index publication."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from doclens_ai.db.base import Base


class ExtractionArtifact(Base):
    __tablename__ = "extraction_artifacts"
    __table_args__ = (
        UniqueConstraint("processing_run_id", "route_fingerprint", name="uq_artifact_run_route"),
        UniqueConstraint("object_storage_key", name="uq_artifact_object_key"),
        CheckConstraint("state IN ('staging', 'available', 'discarded')", name="ck_artifact_state"),
        CheckConstraint(
            "source_state IN ('complete', 'partial', 'failed', 'unsupported', 'unresolved')",
            name="ck_artifact_source_state",
        ),
        CheckConstraint(
            "checksum ~ '^[0-9a-f]{64}$' AND route_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_artifact_digests",
        ),
        CheckConstraint("size_bytes > 0", name="ck_artifact_size"),
        CheckConstraint("artifact_version = '1.0'", name="ck_artifact_version"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    processing_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("processing_runs.id"), nullable=False
    )
    document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_versions.id"), nullable=False
    )
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    route_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    object_storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    artifact_version: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    source_state: Mapped[str] = mapped_column(String(16), nullable=False)
    lease_token: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
