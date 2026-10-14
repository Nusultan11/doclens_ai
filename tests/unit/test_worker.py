from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from doclens_ai.models import ProcessingStage
from doclens_ai.services.ingestion import IngestionFailure, IngestionFailureCategory
from doclens_ai.services.processing import ClaimedProcessingJob, LeaseOwnershipError
from doclens_ai.services.worker import IngestionWorker, WorkerSettings


def test_entrypoint_logging_excludes_sensitive_library_records():
    code = """
import logging
from doclens_ai.worker import _configure_logging
_configure_logging('DEBUG')
logging.getLogger('botocore').debug('private object key and credentials')
logging.getLogger('pypdf').warning('private document content')
logging.getLogger('doclens_ai.services.worker').info('worker_started')
"""
    result = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, timeout=10, text=True
    )
    assert "worker_started" in result.stderr
    assert "private" not in result.stderr and "credentials" not in result.stderr


def test_api_import_does_not_require_optional_parsers():
    code = """
import importlib.abc
import sys
class NoParsers(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'docx', 'pypdf', 'openpyxl'}:
            raise AssertionError('API attempted to import an optional parser')
sys.meta_path.insert(0, NoParsers())
import doclens_ai.main
from doclens_ai.services.processing import default_processing_configuration_fingerprint
assert len(default_processing_configuration_fingerprint()) == 64
"""
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, timeout=10)


def test_lazy_package_exports_preserve_public_contract():
    import doclens_ai.chunking as chunking
    import doclens_ai.extraction as extraction
    from doclens_ai.chunking.core import chunk_document
    from doclens_ai.extraction.parsers import ExtractionLimits, extract_file

    assert chunking.chunk_document is chunk_document
    assert extraction.extract_file is extract_file
    assert extraction.ExtractionLimits is ExtractionLimits
    for package in (chunking, extraction):
        with pytest.raises(AttributeError):
            _ = package.not_a_public_export


def _worker(*, error=None, heartbeat_error=None):
    settings = WorkerSettings(
        _env_file=None,
        poll_interval_seconds=0.01,
        heartbeat_interval_seconds=0.01,
        lease_seconds=1,
        db_timeout_seconds=0.1,
    )
    claim = ClaimedProcessingJob(
        uuid4(),
        uuid4(),
        uuid4(),
        ProcessingStage.EXTRACTION,
        uuid4(),
        datetime.now(UTC) + timedelta(seconds=1),
        1,
        3,
    )
    coordinator = SimpleNamespace(
        lease_duration=timedelta(seconds=1),
        claim_next=AsyncMock(return_value=claim),
        heartbeat=AsyncMock(side_effect=heartbeat_error),
        handoff_extraction=AsyncMock(),
        fail_attempt=AsyncMock(),
    )
    ingestion = SimpleNamespace(ingest=AsyncMock(side_effect=error))
    return IngestionWorker(
        coordinator, ingestion, settings=settings, worker_id="unit-worker"
    ), claim


@pytest.mark.parametrize(
    "field,value",
    [
        ("poll_interval_seconds", 0),
        ("heartbeat_interval_seconds", -1),
        ("lease_seconds", float("inf")),
        ("db_timeout_seconds", float("nan")),
        ("poll_interval_seconds", 61),
        ("lease_seconds", 3601),
    ],
)
def test_configuration_bounds(field, value):
    with pytest.raises(ValueError):
        WorkerSettings(_env_file=None, **{field: value})


def test_heartbeat_budget_and_coordinator_ttl_must_agree():
    with pytest.raises(ValueError):
        WorkerSettings(_env_file=None, lease_seconds=30, heartbeat_interval_seconds=10)
    worker, _ = _worker()
    worker.coordinator.lease_duration = timedelta(seconds=2)
    with pytest.raises(ValueError):
        IngestionWorker(worker.coordinator, worker.ingestion, settings=worker.settings)
    worker.coordinator.lease_duration = timedelta(seconds=1)
    for identity in (" ", "x" * 256):
        with pytest.raises(ValueError):
            IngestionWorker(
                worker.coordinator, worker.ingestion, settings=worker.settings, worker_id=identity
            )
    generated = IngestionWorker(worker.coordinator, worker.ingestion, settings=worker.settings)
    assert generated.worker_id.startswith("ingestion-")


def test_success_uses_exact_ownership_and_extraction_filter():
    async def exercise():
        worker, claim = _worker()
        assert await worker.run_once()
        worker.coordinator.claim_next.assert_awaited_once_with(
            worker_id="unit-worker", stage=ProcessingStage.EXTRACTION
        )
        worker.ingestion.ingest.assert_awaited_once_with(
            claim.processing_run_id, worker_id="unit-worker", lease_token=claim.lease_token
        )
        worker.coordinator.handoff_extraction.assert_awaited_once_with(
            job_id=claim.job_id, worker_id="unit-worker", lease_token=claim.lease_token
        )
        worker.coordinator.fail_attempt.assert_not_awaited()
        assert len(asyncio.all_tasks()) == 1

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "failure,retryable,code",
    [
        (
            IngestionFailure(IngestionFailureCategory.STORAGE_UNAVAILABLE, retryable=True),
            True,
            "storage_unavailable",
        ),
        (
            IngestionFailure(IngestionFailureCategory.EXTRACTION_FAILED, retryable=False),
            False,
            "extraction_failed",
        ),
        (
            RuntimeError("private object/path password document content"),
            True,
            "worker_unexpected_failure",
        ),
    ],
)
def test_failure_routing_is_sanitized(failure, retryable, code, caplog):
    async def exercise():
        worker, claim = _worker(error=failure)
        assert await worker.run_once()
        worker.coordinator.fail_attempt.assert_awaited_once_with(
            job_id=claim.job_id,
            worker_id="unit-worker",
            lease_token=claim.lease_token,
            failure_reason=code,
            retryable=retryable,
        )
        worker.coordinator.handoff_extraction.assert_not_awaited()

    asyncio.run(exercise())
    assert "password" not in caplog.text and "private object" not in caplog.text


@pytest.mark.parametrize(
    "category",
    [
        IngestionFailureCategory.LEASE_OWNERSHIP_LOST,
        IngestionFailureCategory.PROCESSING_STATE_MISMATCH,
    ],
)
def test_stale_ingestion_never_routes_failure_or_handoff(category):
    async def exercise():
        worker, _ = _worker(error=IngestionFailure(category, retryable=False))
        await worker.run_once()
        worker.coordinator.fail_attempt.assert_not_awaited()
        worker.coordinator.handoff_extraction.assert_not_awaited()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "heartbeat_error", [None, LeaseOwnershipError("private"), RuntimeError("secret DB details")]
)
def test_heartbeat_lifecycle_and_shutdown_drain(heartbeat_error, caplog):
    async def exercise():
        worker, _ = _worker(heartbeat_error=heartbeat_error)
        entered, heartbeat_seen, release = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def ingest(*args, **kwargs):
            entered.set()
            await release.wait()

        async def heartbeat(**kwargs):
            heartbeat_seen.set()
            if heartbeat_error:
                raise heartbeat_error

        worker.ingestion.ingest.side_effect = ingest
        worker.coordinator.heartbeat.side_effect = heartbeat
        task = asyncio.create_task(worker.run())
        try:
            await asyncio.wait_for(entered.wait(), 1)
            await asyncio.wait_for(heartbeat_seen.wait(), 1)
            worker.request_stop()
            assert not task.done()
            release.set()
            await asyncio.wait_for(task, 1)
            worker.coordinator.claim_next.assert_awaited_once()
            worker.coordinator.fail_attempt.assert_not_awaited()
            assert worker.coordinator.handoff_extraction.await_count == (
                0 if heartbeat_error else 1
            )
            assert len(asyncio.all_tasks()) == 1
        finally:
            release.set()
            worker.request_stop()
            await task

    asyncio.run(exercise())
    assert "secret" not in caplog.text and "private" not in caplog.text


def test_idle_polling_and_claim_failure_continue_and_stop():
    async def exercise():
        worker, _ = _worker()
        polled = asyncio.Event()
        calls = 0

        async def claim(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("secret")
            if calls == 3:
                polled.set()
            return None

        worker.coordinator.claim_next.side_effect = claim
        task = asyncio.create_task(worker.run())
        try:
            await asyncio.wait_for(polled.wait(), 1)
            worker.request_stop()
            await asyncio.wait_for(task, 1)
            assert calls == 3
            assert not await worker.run_once()
            assert calls == 3
            worker.ingestion.ingest.assert_not_awaited()
        finally:
            worker.request_stop()
            await task

    asyncio.run(exercise())


def test_cancellation_drains_ingestion_and_stops_heartbeat_without_handoff():
    async def exercise():
        worker, _ = _worker()
        entered, release = asyncio.Event(), asyncio.Event()

        async def ingest(*args, **kwargs):
            entered.set()
            await release.wait()

        worker.ingestion.ingest.side_effect = ingest
        task = asyncio.create_task(worker.run_once())
        try:
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            worker.coordinator.handoff_extraction.assert_not_awaited()
            worker.coordinator.fail_attempt.assert_not_awaited()
            assert len(asyncio.all_tasks()) == 1
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())


def test_transition_failure_does_not_try_to_fail_uncertain_lease():
    async def exercise():
        worker, _ = _worker()
        worker.coordinator.handoff_extraction.side_effect = RuntimeError("secret commit failure")
        await worker.run_once()
        worker.coordinator.fail_attempt.assert_not_awaited()

    asyncio.run(exercise())
