"""Add mutable upload session coordination state.

Revision ID: 0003_upload_sessions
Revises: 0002_version_immutability
Create Date: 2026-10-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_upload_sessions"
down_revision: str | Sequence[str] | None = "0002_version_immutability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "upload_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("object_storage_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("original_filename", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "committed_document_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND committed_document_version_id IS NOT NULL) OR "
            "(status <> 'completed' AND committed_document_version_id IS NULL)",
            name="ck_upload_sessions_completion_reference",
        ),
        sa.CheckConstraint(
            "length(btrim(content_type)) > 0",
            name="ck_upload_sessions_content_type_not_blank",
        ),
        sa.CheckConstraint("file_size > 0", name="ck_upload_sessions_file_size_positive"),
        sa.CheckConstraint(
            "length(btrim(original_filename)) > 0",
            name="ck_upload_sessions_filename_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_upload_sessions_idempotency_key_not_blank",
        ),
        sa.CheckConstraint(
            "sha256_checksum ~ '^[0-9a-f]{64}$'",
            name="ck_upload_sessions_sha256_lower_hex",
        ),
        sa.CheckConstraint(
            "length(btrim(object_storage_key)) > 0",
            name="ck_upload_sessions_storage_key_not_blank",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'uploaded', 'completed', 'failed')",
            name="ck_upload_sessions_status",
        ),
        sa.ForeignKeyConstraint(
            ["committed_document_version_id"],
            ["document_versions.id"],
            name="fk_upload_sessions_committed_document_version_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_upload_sessions_document_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_upload_sessions"),
        sa.UniqueConstraint(
            "committed_document_version_id",
            name="uq_upload_sessions_committed_version",
        ),
        sa.UniqueConstraint(
            "document_id",
            "idempotency_key",
            name="uq_upload_sessions_document_idempotency_key",
        ),
        sa.UniqueConstraint(
            "object_storage_key",
            name="uq_upload_sessions_object_storage_key",
        ),
    )
    op.create_index(
        "ix_upload_sessions_document_status",
        "upload_sessions",
        ["document_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_upload_sessions_document_status", table_name="upload_sessions")
    op.drop_table("upload_sessions")
