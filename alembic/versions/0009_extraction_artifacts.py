"""Add scoped extraction artifact identities and fenced lifecycle.

Revision ID: 0009_extraction_artifacts
Revises: 0008_extraction_route
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009_extraction_artifacts"
down_revision = "0008_extraction_route"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "extraction_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "processing_run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("processing_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "document_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("document_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id", UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("route_fingerprint", sa.String(64), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("object_storage_key", sa.String(1024), nullable=False),
        sa.Column("artifact_version", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("source_state", sa.String(16), nullable=False),
        sa.Column("lease_token", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("processing_run_id", "route_fingerprint", name="uq_artifact_run_route"),
        sa.UniqueConstraint("object_storage_key", name="uq_artifact_object_key"),
        sa.CheckConstraint(
            "state IN ('staging', 'available', 'discarded')", name="ck_artifact_state"
        ),
        sa.CheckConstraint(
            "source_state IN ('complete', 'partial', 'failed', 'unsupported', 'unresolved')",
            name="ck_artifact_source_state",
        ),
        sa.CheckConstraint(
            "checksum ~ '^[0-9a-f]{64}$' AND route_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_artifact_digests",
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_artifact_size"),
        sa.CheckConstraint("artifact_version = '1.0'", name="ck_artifact_version"),
    )
    op.execute("""
        CREATE FUNCTION guard_extraction_artifact() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE j processing_jobs; r processing_runs; v document_versions; d documents;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'artifact identity is immutable' USING ERRCODE = 'check_violation';
            END IF;
            SELECT * INTO r FROM processing_runs WHERE id = NEW.processing_run_id;
            SELECT * INTO v FROM document_versions WHERE id = r.document_version_id;
            SELECT * INTO d FROM documents WHERE id = v.document_id;
            IF NEW.document_version_id IS DISTINCT FROM v.id
                OR NEW.workspace_id IS DISTINCT FROM d.workspace_id THEN
                RAISE EXCEPTION 'artifact scope mismatch' USING ERRCODE = 'check_violation';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF (to_jsonb(NEW) - 'state' - 'lease_token') IS DISTINCT FROM
                   (to_jsonb(OLD) - 'state' - 'lease_token')
                   OR OLD.state = 'available' OR OLD.state = 'discarded'
                   OR NEW.state NOT IN ('available', 'discarded') THEN
                    RAISE EXCEPTION 'artifact identity is immutable'
                        USING ERRCODE = 'check_violation';
                END IF;
            ELSIF NEW.state <> 'staging' THEN
                RAISE EXCEPTION 'artifact must be staged' USING ERRCODE = 'check_violation';
            END IF;
            SELECT * INTO j FROM processing_jobs WHERE processing_run_id = NEW.processing_run_id;
            IF NEW.state = 'discarded' THEN
                IF j.status IS DISTINCT FROM 'failed' THEN
                    RAISE EXCEPTION 'artifact cleanup requires terminal job'
                        USING ERRCODE = 'check_violation';
                END IF;
            ELSIF j.status IS DISTINCT FROM 'leased'
                OR j.lease_token IS DISTINCT FROM NEW.lease_token
                OR j.lease_expires_at <= clock_timestamp()
                OR r.stage <> 'extraction' OR r.status <> 'processing' THEN
                RAISE EXCEPTION 'artifact lease lost' USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END; $$;
    """)
    op.execute("""CREATE TRIGGER trg_extraction_artifact_guard BEFORE INSERT OR UPDATE OR DELETE
        ON extraction_artifacts FOR EACH ROW EXECUTE FUNCTION guard_extraction_artifact()""")


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_extraction_artifact_guard ON extraction_artifacts")
    op.execute("DROP FUNCTION guard_extraction_artifact()")
    op.drop_table("extraction_artifacts")
