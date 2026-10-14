from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from uuid import UUID

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from doclens_ai.db.base import Base


class IndexRevisionStatus(StrEnum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


def chunk_set_fingerprint(rows) -> str:
    """Fingerprint immutable canonical identities/content hashes, never store chunk text."""
    values = [(str(row.id), row.ordinal, row.chunk_identity, row.content_sha256) for row in rows]
    return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()


class IndexRevision(Base):
    """A lease-attempt-owned candidate; PostgreSQL alone selects the active document index."""

    __tablename__ = "index_revisions"
    __table_args__ = (
        UniqueConstraint("processing_run_id", "lease_token", name="uq_index_revisions_run_lease"),
        CheckConstraint("document_version_number >= 1", name="ck_index_revisions_version"),
        CheckConstraint(
            "embedding_model_revision ~ '^[0-9a-f]{40}$'", name="ck_index_revisions_model_revision"
        ),
        CheckConstraint(
            "embedding_configuration_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_index_revisions_configuration",
        ),
        CheckConstraint(
            "canonical_chunk_set_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_index_revisions_chunk_set",
        ),
        CheckConstraint(
            "jsonb_typeof(embedding_configuration) = 'object'",
            name="ck_index_revisions_config_object",
        ),
        CheckConstraint(
            "vector_dimension > 0 AND vector_dimension <= 8192", name="ck_index_revisions_dimension"
        ),
        CheckConstraint(
            "collection_name ~ '^[a-z][a-z0-9_]{2,127}$'", name="ck_index_revisions_collection"
        ),
        CheckConstraint(
            "length(btrim(embedding_model_id)) > 0", name="ck_index_revisions_model_id"
        ),
        CheckConstraint(
            "expected_point_count > 0 AND verified_point_count >= 0 "
            "AND verified_point_count <= expected_point_count",
            name="ck_index_revisions_counts",
        ),
        CheckConstraint(
            "(status = 'candidate' AND verified_point_count = 0 AND verified_at IS NULL "
            "AND activated_at IS NULL AND superseded_at IS NULL) OR "
            "(status = 'verified' AND verified_point_count = expected_point_count "
            "AND verified_at IS NOT NULL AND activated_at IS NULL AND superseded_at IS NULL) OR "
            "(status = 'active' AND verified_point_count = expected_point_count "
            "AND verified_at IS NOT NULL AND activated_at IS NOT NULL "
            "AND superseded_at IS NULL) OR "
            "(status = 'superseded' AND verified_point_count = expected_point_count "
            "AND verified_at IS NOT NULL AND superseded_at IS NOT NULL)",
            name="ck_index_revisions_state",
        ),
        Index("ix_index_revisions_processing_run_id", "processing_run_id"),
        Index(
            "uq_index_revisions_active_document",
            "document_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    processing_run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    document_version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_token: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    embedding_model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model_revision: Mapped[str] = mapped_column(String(40), nullable=False)
    embedding_configuration: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    embedding_configuration_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_chunk_set_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    vector_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    collection_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="candidate")
    expected_point_count: Mapped[int] = mapped_column(Integer, nullable=False)
    verified_point_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
