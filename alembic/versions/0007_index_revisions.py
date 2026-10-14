"""Add immutable index revision identities and guarded lifecycle metadata.

Revision ID: 0007_index_revisions
Revises: 0006_canonical_chunks
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_index_revisions"
down_revision = "0006_canonical_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "index_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_number", sa.Integer(), nullable=False),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding_model_id", sa.String(128), nullable=False),
        sa.Column("embedding_model_revision", sa.String(40), nullable=False),
        sa.Column("embedding_configuration", postgresql.JSONB(), nullable=False),
        sa.Column("embedding_configuration_fingerprint", sa.String(64), nullable=False),
        sa.Column("canonical_chunk_set_fingerprint", sa.String(64), nullable=False),
        sa.Column("vector_dimension", sa.Integer(), nullable=False),
        sa.Column("collection_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="candidate"),
        sa.Column("expected_point_count", sa.Integer(), nullable=False),
        sa.Column("verified_point_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["processing_run_id"], ["processing_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["document_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "processing_run_id", "lease_token", name="uq_index_revisions_run_lease"
        ),
        sa.CheckConstraint("document_version_number >= 1", name="ck_index_revisions_version"),
        sa.CheckConstraint(
            "embedding_model_revision ~ '^[0-9a-f]{40}$'", name="ck_index_revisions_model_revision"
        ),
        sa.CheckConstraint(
            "embedding_configuration_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_index_revisions_configuration",
        ),
        sa.CheckConstraint(
            "canonical_chunk_set_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_index_revisions_chunk_set",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(embedding_configuration) = 'object'",
            name="ck_index_revisions_config_object",
        ),
        sa.CheckConstraint(
            "vector_dimension > 0 AND vector_dimension <= 8192", name="ck_index_revisions_dimension"
        ),
        sa.CheckConstraint(
            "collection_name ~ '^[a-z][a-z0-9_]{2,127}$'", name="ck_index_revisions_collection"
        ),
        sa.CheckConstraint(
            "length(btrim(embedding_model_id)) > 0", name="ck_index_revisions_model_id"
        ),
        sa.CheckConstraint(
            "expected_point_count > 0 AND verified_point_count >= 0 "
            "AND verified_point_count <= expected_point_count",
            name="ck_index_revisions_counts",
        ),
        sa.CheckConstraint(
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
    )
    op.create_index(
        "ix_index_revisions_processing_run_id", "index_revisions", ["processing_run_id"]
    )
    op.create_index(
        "uq_index_revisions_active_document",
        "index_revisions",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.execute("""
    CREATE FUNCTION guard_index_revision() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'UPDATE' THEN
        IF ROW(NEW.id, NEW.processing_run_id, NEW.document_version_id, NEW.document_id,
          NEW.workspace_id, NEW.document_version_number, NEW.lease_token, NEW.embedding_model_id,
          NEW.embedding_model_revision, NEW.embedding_configuration,
          NEW.embedding_configuration_fingerprint, NEW.canonical_chunk_set_fingerprint,
          NEW.vector_dimension, NEW.collection_name, NEW.expected_point_count, NEW.created_at)
          IS DISTINCT FROM
          ROW(OLD.id, OLD.processing_run_id, OLD.document_version_id, OLD.document_id,
          OLD.workspace_id, OLD.document_version_number, OLD.lease_token, OLD.embedding_model_id,
          OLD.embedding_model_revision, OLD.embedding_configuration,
          OLD.embedding_configuration_fingerprint, OLD.canonical_chunk_set_fingerprint,
          OLD.vector_dimension, OLD.collection_name, OLD.expected_point_count, OLD.created_at)
        THEN RAISE EXCEPTION 'index revision identity is immutable'
          USING ERRCODE = 'check_violation'; END IF;
        IF NEW.status <> OLD.status AND NOT
          ((OLD.status = 'candidate' AND NEW.status = 'verified') OR
           (OLD.status = 'verified' AND NEW.status IN ('active', 'superseded')) OR
           (OLD.status = 'active' AND NEW.status = 'superseded'))
        THEN RAISE EXCEPTION 'invalid index revision transition'
          USING ERRCODE = 'check_violation'; END IF;
        IF OLD.status <> 'candidate' AND
          ROW(NEW.verified_point_count, NEW.verified_at) IS DISTINCT FROM
          ROW(OLD.verified_point_count, OLD.verified_at)
        THEN RAISE EXCEPTION 'index verification is immutable'
          USING ERRCODE = 'check_violation'; END IF;
        IF OLD.status IN ('active', 'superseded')
          AND NEW.activated_at IS DISTINCT FROM OLD.activated_at
        THEN RAISE EXCEPTION 'activation timestamp is immutable'
          USING ERRCODE = 'check_violation'; END IF;
        IF OLD.status = 'superseded' AND NEW.superseded_at IS DISTINCT FROM OLD.superseded_at
        THEN RAISE EXCEPTION 'supersession timestamp is immutable'
          USING ERRCODE = 'check_violation'; END IF;
      ELSE
        IF NEW.status <> 'candidate' THEN
          RAISE EXCEPTION 'new index revision must be a candidate'
            USING ERRCODE = 'check_violation';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM processing_runs r
          JOIN document_versions v ON v.id = r.document_version_id
          JOIN documents d ON d.id = v.document_id
          WHERE r.id = NEW.processing_run_id AND v.id = NEW.document_version_id
          AND d.id = NEW.document_id AND d.workspace_id = NEW.workspace_id
          AND v.version_number = NEW.document_version_number)
        THEN RAISE EXCEPTION 'index revision scope mismatch'
          USING ERRCODE = 'check_violation'; END IF;
      END IF;
      RETURN NEW;
    END; $$;
    """)
    op.execute("""CREATE TRIGGER trg_index_revision_guard
    BEFORE INSERT OR UPDATE ON index_revisions
    FOR EACH ROW EXECUTE FUNCTION guard_index_revision();""")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_index_revision_guard ON index_revisions")
    op.execute("DROP FUNCTION IF EXISTS guard_index_revision()")
    op.drop_index("uq_index_revisions_active_document", table_name="index_revisions")
    op.drop_index("ix_index_revisions_processing_run_id", table_name="index_revisions")
    op.drop_table("index_revisions")
