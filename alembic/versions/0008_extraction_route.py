"""Pin immutable extraction routes; legacy rows remain explicitly unpinned.

Revision ID: 0008_extraction_route
Revises: 0007_index_revisions
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_extraction_route"
down_revision = "0007_index_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No guessed backfill: historical fingerprints cannot recover effective pins.
    op.add_column("processing_runs", sa.Column("extraction_route", JSONB(), nullable=True))
    op.create_check_constraint(
        "ck_processing_runs_extraction_route_object",
        "processing_runs",
        "extraction_route IS NULL OR jsonb_typeof(extraction_route) = 'object'",
    )
    op.execute("""
        CREATE FUNCTION reject_extraction_route_update() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.extraction_route IS DISTINCT FROM OLD.extraction_route THEN
                RAISE EXCEPTION 'extraction route is immutable' USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END; $$;
    """)
    op.execute("""
        CREATE TRIGGER trg_extraction_route_immutable BEFORE UPDATE ON processing_runs
        FOR EACH ROW EXECUTE FUNCTION reject_extraction_route_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_extraction_route_immutable ON processing_runs")
    op.execute("DROP FUNCTION reject_extraction_route_update()")
    op.drop_constraint(
        "ck_processing_runs_extraction_route_object", "processing_runs", type_="check"
    )
    op.drop_column("processing_runs", "extraction_route")
