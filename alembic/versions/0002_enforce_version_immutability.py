"""Enforce document version immutability.

Revision ID: 0002_version_immutability
Revises: 0001_document_domain
Create Date: 2026-10-10

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_version_immutability"
down_revision: str | Sequence[str] | None = "0001_document_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION doclens_prevent_document_version_update()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION 'document_versions rows are immutable after insert'
                USING ERRCODE = '23514';
            RETURN OLD;
        END;
        $function$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_document_versions_immutable
        BEFORE UPDATE ON document_versions
        FOR EACH ROW
        EXECUTE FUNCTION doclens_prevent_document_version_update()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_document_versions_immutable ON document_versions")
    op.execute("DROP FUNCTION doclens_prevent_document_version_update()")
