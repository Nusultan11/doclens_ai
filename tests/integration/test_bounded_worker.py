"""Actual process hangs/cancellation through the real leased PG/S3 worker."""

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import select, text

from doclens_ai.extraction.bounded import ExecutionBudget
from doclens_ai.extraction.engines import EnginePin
from doclens_ai.models import CanonicalChunk, ProcessingJob, ProcessingRun
from doclens_ai.services.processing import ProcessingCoordinator, ProcessingPolicy
from doclens_ai.services.worker import IngestionWorker, WorkerSettings
from tests.bounded_probe import ProbeEngine
from tests.integration.test_engine_ingestion import prepare_engine_run
from tests.integration.test_worker import _environment

pytestmark = [pytest.mark.integration, pytest.mark.storage]


def worker(factory, service, name="bounded-worker"):
    coordinator = ProcessingCoordinator(
        factory,
        policy=ProcessingPolicy(
            lease_duration=timedelta(seconds=8), retry_base_delay=timedelta(seconds=30)
        ),
    )
    return IngestionWorker(
        coordinator,
        service,
        worker_id=name,
        settings=WorkerSettings(
            _env_file=None,
            lease_seconds=8,
            heartbeat_interval_seconds=0.03,
            db_timeout_seconds=2,
            poll_interval_seconds=0.01,
        ),
    )


async def prepare(factory, storage, keys, path):
    pin = EnginePin(
        name="probe", revision="1", implementation_sha256="a" * 64, options_json='{"mode":"hang"}'
    )
    faulty, service, reviews, _, _, _ = await prepare_engine_run(
        factory,
        storage,
        keys,
        ProbeEngine(),
        path,
        route_overrides={
            "engines": (pin,),
            "review_id": "faulty-review",
            "execution_budget": replace(ExecutionBudget(), wall_seconds=2),
        },
    )
    healthy, _, healthy_reviews, _, _, _ = await prepare_engine_run(
        factory, storage, keys, ProbeEngine(), path
    )
    reviews.update(healthy_reviews)
    return faulty, healthy, service


def test_bounded_hang_retries_same_pin_and_does_not_stop_unrelated_job(
    migrated_database_url, test_storage_settings, tmp_path
):
    path = tmp_path / "fixture.pdf"
    path.write_bytes(b"%PDF-1.7\nbounded worker\n%%EOF")

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            faulty, healthy, service = await prepare(factory, storage, keys, path)
            current = worker(factory, service)
            assert await current.run_once()  # Real hang times out, job retries.
            assert await current.run_once()  # Independent healthy RAW source progresses.
            async with factory() as session:
                healthy_job = await session.get(ProcessingJob, healthy.processing_job_id)
                assert healthy_job.status == "queued"  # Handed to embedding.
                healthy_run = await session.get(ProcessingRun, healthy_job.processing_run_id)
                assert healthy_run.stage == "embedding"
                bad = await session.get(ProcessingJob, faulty.processing_job_id)
                assert bad.status == "retry_wait" and bad.attempt_count == 1
                assert len(tuple(await session.scalars(select(CanonicalChunk)))) == 1
            for _ in range(2):
                async with factory() as session, session.begin():
                    await session.execute(
                        text(
                            "UPDATE processing_jobs SET next_retry_at = "
                            "clock_timestamp() - INTERVAL '1 second' WHERE id = :id"
                        ),
                        {"id": faulty.processing_job_id},
                    )
                assert await current.run_once()
            async with factory() as session:
                bad = await session.get(ProcessingJob, faulty.processing_job_id)
                assert bad.status == "failed" and bad.attempt_count == bad.max_attempts == 3
                run = await session.get(ProcessingRun, bad.processing_run_id)
                assert run.extraction_route["engines"][0]["options_json"] == '{"mode":"hang"}'
                assert len(tuple(await session.scalars(select(CanonicalChunk)))) == 1
            assert service.executor.active == 0

    asyncio.run(exercise())


def test_worker_cancellation_kills_engine_and_keeps_lease_unpublished(
    migrated_database_url, test_storage_settings, tmp_path
):
    path = tmp_path / "fixture.pdf"
    path.write_bytes(b"%PDF-1.7\ncancel bounded worker\n%%EOF")

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            faulty, _, service = await prepare(factory, storage, keys, path)
            current = worker(factory, service)
            task = asyncio.create_task(current.run_once())
            try:
                for _ in range(500):
                    if service.executor.last_pid is not None:
                        break
                    await asyncio.sleep(0.01)
                else:
                    pytest.fail("bounded engine never started")
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 3)
                assert service.executor.active == 0
                async with factory() as session:
                    job = await session.get(ProcessingJob, faulty.processing_job_id)
                    assert job.status == "leased" and job.attempt_count == 1
                    assert not tuple(await session.scalars(select(CanonicalChunk)))
                assert await worker(factory, service, "surviving-worker").run_once()
                async with factory() as session:
                    assert len(tuple(await session.scalars(select(CanonicalChunk)))) == 1
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())
