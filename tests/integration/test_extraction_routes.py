"""Real PostgreSQL migration and immutable route pin tests."""

import asyncio

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from doclens_ai.models import ProcessingRun
from tests.integration.test_domain_migrations import _insert_document_version
from tests.integration.test_processing_jobs import _uploaded_job

pytestmark = pytest.mark.integration


def test_route_upgrade_downgrade_preserves_legacy_unpinned_rows(
    disposable_database_url, alembic_runner
):
    url = disposable_database_url
    alembic_runner(url, "upgrade", "0007_index_revisions")
    version = asyncio.run(_insert_document_version(url))

    async def insert():
        engine = create_async_engine(url)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO processing_runs "
                        "(id, document_version_id, operation_id, operation_kind, "
                        "configuration_version, "
                        "configuration_fingerprint, stage, status) VALUES "
                        "(gen_random_uuid(), :v, gen_random_uuid(), 'reprocess', "
                        "'1.1', :f, 'extraction', 'queued')"
                    ),
                    {"v": version, "f": "a" * 64},
                )
        finally:
            await engine.dispose()

    asyncio.run(insert())
    for _ in range(2):
        alembic_runner(url, "upgrade", "head")
        alembic_runner(url, "check")

        async def inspect():
            engine = create_async_engine(url)
            try:
                async with engine.connect() as connection:
                    return (
                        await connection.execute(
                            text(
                                "SELECT extraction_route, configuration_version "
                                "FROM processing_runs"
                            )
                        )
                    ).one()
            finally:
                await engine.dispose()

        assert asyncio.run(inspect()) == (None, "1.1")
        alembic_runner(url, "downgrade", "0007_index_revisions")


def test_new_run_pins_route_and_database_rejects_route_mutation(migrated_database_url):
    async def exercise():
        engine, factory, job_id = await _uploaded_job(migrated_database_url)
        try:
            async with factory() as session:
                run = await session.scalar(select(ProcessingRun))
                assert run.extraction_route["engines"][0]["name"] == "native"
                assert run.extraction_route["engines"][0]["implementation_sha256"]
                assert run.extraction_route["ir_version"] == "2.0"
                identity = run.id
            with pytest.raises(IntegrityError):
                async with factory() as session, session.begin():
                    await session.execute(
                        text(
                            "UPDATE processing_runs SET extraction_route = '{}'::jsonb "
                            "WHERE id = :id"
                        ),
                        {"id": identity},
                    )
            async with factory() as session:
                assert (await session.get(ProcessingRun, identity)).extraction_route["engines"]
        finally:
            await engine.dispose()

    asyncio.run(exercise())
