"""Add durable processing runs and jobs.

Revision ID: 0005_processing_runs_jobs
Revises: 0004_auth_memberships
Create Date: 2026-10-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_processing_runs_jobs"
down_revision: str | Sequence[str] | None = "0004_auth_memberships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INITIAL_CONFIGURATION_FINGERPRINT = (
    "b4fbdf76ff96f38c4007380693a83fd82920645cd355f0f8abd80ee14d1ec9c3"
)


def upgrade() -> None:
    op.create_table(
        "processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_kind", sa.String(length=32), nullable=False),
        sa.Column("configuration_version", sa.String(length=64), nullable=False),
        sa.Column("configuration_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
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
            "operation_kind IN ('initial', 'reprocess')",
            name="ck_processing_runs_operation_kind",
        ),
        sa.CheckConstraint(
            "length(btrim(configuration_version)) > 0",
            name="ck_processing_runs_configuration_version_not_blank",
        ),
        sa.CheckConstraint(
            "configuration_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_processing_runs_configuration_fingerprint_lower_hex",
        ),
        sa.CheckConstraint(
            "stage IN ('extraction', 'cleaning', 'chunking', 'embedding', 'indexing')",
            name="ck_processing_runs_stage",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'processing', 'retry_wait', 'failed', 'completed')",
            name="ck_processing_runs_status",
        ),
        sa.CheckConstraint(
            "error_code IS NULL OR error_code ~ '^[a-z0-9][a-z0-9_]{0,63}$'",
            name="ck_processing_runs_error_code",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_processing_runs_document_version_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_processing_runs"),
        sa.UniqueConstraint("operation_id", name="uq_processing_runs_operation_id"),
    )
    op.create_index(
        "ix_processing_runs_document_version_id",
        "processing_runs",
        ["document_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_processing_runs_status_stage",
        "processing_runs",
        ["status", "stage"],
        unique=False,
    )
    op.create_index(
        "uq_processing_runs_initial_version",
        "processing_runs",
        ["document_version_id"],
        unique=True,
        postgresql_where=sa.text("operation_kind = 'initial'"),
    )

    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processing_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.Column("leased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('queued', 'leased', 'retry_wait', 'failed', 'completed')",
            name="ck_processing_jobs_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_processing_jobs_attempt_nonnegative",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="ck_processing_jobs_max_attempts_positive",
        ),
        sa.CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_processing_jobs_attempt_within_limit",
        ),
        sa.CheckConstraint(
            "worker_id IS NULL OR length(btrim(worker_id)) > 0",
            name="ck_processing_jobs_worker_not_blank",
        ),
        sa.CheckConstraint(
            "failure_reason IS NULL OR "
            "failure_reason ~ '^[a-z0-9][a-z0-9_]{0,63}$'",
            name="ck_processing_jobs_failure_reason",
        ),
        sa.CheckConstraint(
            "(status = 'leased' AND worker_id IS NOT NULL AND lease_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL AND leased_at IS NOT NULL "
            "AND next_retry_at IS NULL AND finished_at IS NULL) OR "
            "(status <> 'leased' AND worker_id IS NULL AND lease_token IS NULL "
            "AND lease_expires_at IS NULL)",
            name="ck_processing_jobs_lease_state",
        ),
        sa.CheckConstraint(
            "(status = 'retry_wait' AND next_retry_at IS NOT NULL "
            "AND failure_reason IS NOT NULL) OR "
            "(status <> 'retry_wait' AND next_retry_at IS NULL)",
            name="ck_processing_jobs_retry_state",
        ),
        sa.CheckConstraint(
            "(status IN ('failed', 'completed') AND finished_at IS NOT NULL) OR "
            "(status NOT IN ('failed', 'completed') AND finished_at IS NULL)",
            name="ck_processing_jobs_terminal_state",
        ),
        sa.CheckConstraint(
            "status <> 'failed' OR failure_reason IS NOT NULL",
            name="ck_processing_jobs_failed_reason",
        ),
        sa.ForeignKeyConstraint(
            ["processing_run_id"],
            ["processing_runs.id"],
            name="fk_processing_jobs_processing_run_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_processing_jobs"),
        sa.UniqueConstraint(
            "processing_run_id",
            name="uq_processing_jobs_processing_run_id",
        ),
    )
    op.create_index(
        "ix_processing_jobs_status_retry_created",
        "processing_jobs",
        ["status", "next_retry_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_processing_jobs_lease_expires_at",
        "processing_jobs",
        ["lease_expires_at"],
        unique=False,
    )

    op.execute(
        sa.text(
            "INSERT INTO processing_runs "
            "(id, document_version_id, operation_id, operation_kind, "
            "configuration_version, configuration_fingerprint, stage, status) "
            "SELECT gen_random_uuid(), id, id, 'initial', '1.0', "
            ":fingerprint, 'extraction', 'queued' FROM document_versions"
        ).bindparams(fingerprint=INITIAL_CONFIGURATION_FINGERPRINT)
    )
    op.execute(
        sa.text(
            "INSERT INTO processing_jobs "
            "(id, processing_run_id, status, attempt_count, max_attempts) "
            "SELECT gen_random_uuid(), id, 'queued', 0, 3 FROM processing_runs "
            "WHERE operation_kind = 'initial'"
        )
    )

    op.execute(
        """
        CREATE FUNCTION reject_processing_run_identity_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.document_version_id IS DISTINCT FROM OLD.document_version_id
               OR NEW.operation_id IS DISTINCT FROM OLD.operation_id
               OR NEW.operation_kind IS DISTINCT FROM OLD.operation_kind
               OR NEW.configuration_version IS DISTINCT FROM OLD.configuration_version
               OR NEW.configuration_fingerprint IS DISTINCT FROM OLD.configuration_fingerprint
            THEN
                RAISE EXCEPTION 'processing run identity and configuration are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_processing_run_identity_immutable
        BEFORE UPDATE ON processing_runs
        FOR EACH ROW
        EXECUTE FUNCTION reject_processing_run_identity_update();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_processing_run_identity_immutable ON processing_runs"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_processing_run_identity_update()")
    op.drop_index("ix_processing_jobs_lease_expires_at", table_name="processing_jobs")
    op.drop_index(
        "ix_processing_jobs_status_retry_created",
        table_name="processing_jobs",
    )
    op.drop_table("processing_jobs")
    op.drop_index(
        "uq_processing_runs_initial_version",
        table_name="processing_runs",
        postgresql_where=sa.text("operation_kind = 'initial'"),
    )
    op.drop_index("ix_processing_runs_status_stage", table_name="processing_runs")
    op.drop_index(
        "ix_processing_runs_document_version_id",
        table_name="processing_runs",
    )
    op.drop_table("processing_runs")
