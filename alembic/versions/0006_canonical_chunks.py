"""Add canonical document chunks.

Revision ID: 0006_canonical_chunks
Revises: 0005_processing_runs_jobs
Create Date: 2026-10-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_canonical_chunks"
down_revision: str | Sequence[str] | None = "0005_processing_runs_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("chunk_identity", sa.String(length=70), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("document_format", sa.String(length=16), nullable=False),
        sa.Column("chunking_strategy", sa.String(length=32), nullable=False),
        sa.Column("chunker_version", sa.String(length=64), nullable=False),
        sa.Column(
            "chunker_configuration_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("source_provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "split_oversized_element",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ordinal >= 0",
            name="ck_canonical_chunks_ordinal_nonnegative",
        ),
        sa.CheckConstraint(
            "chunk_identity ~ '^chunk-[0-9a-f]{64}$'",
            name="ck_canonical_chunks_identity",
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_canonical_chunks_content_sha256",
        ),
        sa.CheckConstraint(
            "character_count > 0 AND character_count = char_length(chunk_text)",
            name="ck_canonical_chunks_character_count",
        ),
        sa.CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_canonical_chunks_token_count_nonnegative",
        ),
        sa.CheckConstraint(
            "chunker_configuration_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_canonical_chunks_configuration_fingerprint",
        ),
        sa.CheckConstraint(
            "length(btrim(chunker_version)) > 0",
            name="ck_canonical_chunks_version_not_blank",
        ),
        sa.CheckConstraint(
            "document_format IN ('pdf', 'docx', 'xlsx')",
            name="ck_canonical_chunks_document_format",
        ),
        sa.CheckConstraint(
            "chunking_strategy IN ('fixed_size', 'structure_aware')",
            name="ck_canonical_chunks_strategy",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_provenance) = 'array' "
            "AND jsonb_array_length(source_provenance) > 0",
            name="ck_canonical_chunks_source_provenance",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            ["processing_runs.id"],
            name="fk_canonical_chunks_processing_run_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_canonical_chunks"),
        sa.UniqueConstraint(
            "processing_run_id",
            "chunk_identity",
            name="uq_canonical_chunks_run_identity",
        ),
        sa.UniqueConstraint(
            "processing_run_id",
            "ordinal",
            name="uq_canonical_chunks_run_ordinal",
        ),
    )
    op.create_index(
        "ix_canonical_chunks_processing_run_id",
        "canonical_chunks",
        ["processing_run_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION reject_canonical_chunk_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'canonical chunks are immutable'
                USING ERRCODE = 'check_violation';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_canonical_chunk_immutable
        BEFORE UPDATE ON canonical_chunks
        FOR EACH ROW
        EXECUTE FUNCTION reject_canonical_chunk_update();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_canonical_chunk_immutable ON canonical_chunks"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_canonical_chunk_update()")
    op.drop_index(
        "ix_canonical_chunks_processing_run_id",
        table_name="canonical_chunks",
    )
    op.drop_table("canonical_chunks")
