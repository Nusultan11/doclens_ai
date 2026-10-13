from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doclens_ai.db.base import Base


class CanonicalChunk(Base):
    """Authoritative extracted chunk for one immutable processing run."""

    __tablename__ = "canonical_chunks"
    __table_args__ = (
        UniqueConstraint(
            "processing_run_id",
            "ordinal",
            name="uq_canonical_chunks_run_ordinal",
        ),
        UniqueConstraint(
            "processing_run_id",
            "chunk_identity",
            name="uq_canonical_chunks_run_identity",
        ),
        CheckConstraint("ordinal >= 0", name="ck_canonical_chunks_ordinal_nonnegative"),
        CheckConstraint(
            "chunk_identity ~ '^chunk-[0-9a-f]{64}$'",
            name="ck_canonical_chunks_identity",
        ),
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_canonical_chunks_content_sha256",
        ),
        CheckConstraint(
            "character_count > 0 AND character_count = char_length(chunk_text)",
            name="ck_canonical_chunks_character_count",
        ),
        CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_canonical_chunks_token_count_nonnegative",
        ),
        CheckConstraint(
            "chunker_configuration_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_canonical_chunks_configuration_fingerprint",
        ),
        CheckConstraint(
            "length(btrim(chunker_version)) > 0",
            name="ck_canonical_chunks_version_not_blank",
        ),
        CheckConstraint(
            "document_format IN ('pdf', 'docx', 'xlsx')",
            name="ck_canonical_chunks_document_format",
        ),
        CheckConstraint(
            "chunking_strategy IN ('fixed_size', 'structure_aware')",
            name="ck_canonical_chunks_strategy",
        ),
        CheckConstraint(
            "jsonb_typeof(source_provenance) = 'array' "
            "AND jsonb_array_length(source_provenance) > 0",
            name="ck_canonical_chunks_source_provenance",
        ),
        Index("ix_canonical_chunks_processing_run_id", "processing_run_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    processing_run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("processing_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_identity: Mapped[str] = mapped_column(String(70), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_format: Mapped[str] = mapped_column(String(16), nullable=False)
    chunking_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    chunker_version: Mapped[str] = mapped_column(String(64), nullable=False)
    chunker_configuration_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    source_provenance: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )
    split_oversized_element: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    processing_run = relationship("ProcessingRun")
