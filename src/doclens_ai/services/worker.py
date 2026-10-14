from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from uuid import uuid4

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from doclens_ai.models import ProcessingStage
from doclens_ai.services.ingestion import (
    IngestionFailure,
    IngestionFailureCategory,
    IngestionService,
)
from doclens_ai.services.processing import (
    ClaimedProcessingJob,
    LeaseOwnershipError,
    ProcessingCoordinator,
    ProcessingJobNotFoundError,
)

logger = logging.getLogger(__name__)
_OWNERSHIP_FAILURES = {
    IngestionFailureCategory.LEASE_OWNERSHIP_LOST,
    IngestionFailureCategory.PROCESSING_STATE_MISMATCH,
}


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_", env_file=".env", extra="ignore")

    poll_interval_seconds: float = Field(default=1, gt=0, le=60, allow_inf_nan=False)
    heartbeat_interval_seconds: float = Field(default=10, gt=0, le=60, allow_inf_nan=False)
    lease_seconds: float = Field(default=120, gt=0, le=3600, allow_inf_nan=False)
    db_timeout_seconds: float = Field(default=5, gt=0, le=60, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_heartbeat_budget(self) -> WorkerSettings:
        if self.heartbeat_interval_seconds + self.db_timeout_seconds >= self.lease_seconds / 2:
            raise ValueError("heartbeat interval plus DB timeout must be below half the lease TTL")
        return self


async def _wait(event: asyncio.Event, seconds: float) -> bool:
    try:
        async with asyncio.timeout(seconds):
            await event.wait()
        return True
    except TimeoutError:
        return False


class IngestionWorker:
    """One in-flight document per process; PostgreSQL coordinates competing processes."""

    def __init__(
        self,
        coordinator: ProcessingCoordinator,
        ingestion: IngestionService,
        *,
        settings: WorkerSettings | None = None,
        worker_id: str | None = None,
    ) -> None:
        self.settings = settings or WorkerSettings()
        if coordinator.lease_duration != timedelta(seconds=self.settings.lease_seconds):
            raise ValueError("worker and coordinator lease TTL must agree")
        self.worker_id = worker_id if worker_id is not None else f"ingestion-{uuid4().hex}"
        if not self.worker_id.strip() or len(self.worker_id) > 255:
            raise ValueError("worker identity must contain 1 to 255 characters")
        self.coordinator = coordinator
        self.ingestion = ingestion
        self._stop = asyncio.Event()

    def request_stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        logger.info("worker_started")
        try:
            while not self._stop.is_set():
                if not await self.run_once():
                    await _wait(self._stop, self.settings.poll_interval_seconds)
        finally:
            logger.info("worker_stopped")

    async def run_once(self) -> bool:
        if self._stop.is_set():
            return False
        try:
            async with asyncio.timeout(self.settings.db_timeout_seconds):
                claim = await self.coordinator.claim_next(
                    worker_id=self.worker_id,
                    stage=ProcessingStage.EXTRACTION,
                )
        except Exception:
            logger.warning("worker_claim_unavailable")
            return False
        if claim is None:
            return False
        await self._execute(claim)
        return True

    async def _heartbeat(self, claim: ClaimedProcessingJob, stop: asyncio.Event) -> None:
        while not await _wait(stop, self.settings.heartbeat_interval_seconds):
            async with asyncio.timeout(self.settings.db_timeout_seconds):
                await self.coordinator.heartbeat(
                    job_id=claim.job_id,
                    worker_id=self.worker_id,
                    lease_token=claim.lease_token,
                )

    async def _execute(self, claim: ClaimedProcessingJob) -> None:
        heartbeat_stop = asyncio.Event()
        heartbeat = asyncio.create_task(self._heartbeat(claim, heartbeat_stop))
        ingestion = asyncio.create_task(
            self.ingestion.ingest(
                claim.processing_run_id,
                worker_id=self.worker_id,
                lease_token=claim.lease_token,
            )
        )
        failure: Exception | None = None
        heartbeat_failed = False
        try:
            try:
                await asyncio.shield(ingestion)
            except asyncio.CancelledError:
                self.request_stop()
                # A parser may still be running in a thread. Drain instead of deleting its
                # temporary source or leaving an orphaned task; no handoff on cancellation.
                try:
                    await asyncio.shield(ingestion)
                except Exception:
                    logger.warning("worker_cancelled_ingestion_failed")
                raise
            except Exception as error:
                failure = error
        finally:
            heartbeat_stop.set()
            try:
                await heartbeat
            except Exception:
                heartbeat_failed = True
                logger.warning("worker_heartbeat_lost")
        if heartbeat_failed:
            # Do not route even a document error through a lease with uncertain ownership.
            return
        try:
            async with asyncio.timeout(self.settings.db_timeout_seconds):
                if failure is None:
                    await self.coordinator.handoff_extraction(
                        job_id=claim.job_id,
                        worker_id=self.worker_id,
                        lease_token=claim.lease_token,
                    )
                    logger.info("worker_handoff_embedding")
                elif isinstance(failure, IngestionFailure):
                    if failure.category in _OWNERSHIP_FAILURES:
                        logger.warning("worker_ownership_lost")
                        return
                    await self.coordinator.fail_attempt(
                        job_id=claim.job_id,
                        worker_id=self.worker_id,
                        lease_token=claim.lease_token,
                        failure_reason=failure.category.value,
                        retryable=failure.retryable,
                    )
                    logger.warning("worker_ingestion_failed")
                else:
                    await self.coordinator.fail_attempt(
                        job_id=claim.job_id,
                        worker_id=self.worker_id,
                        lease_token=claim.lease_token,
                        failure_reason="worker_unexpected_failure",
                        retryable=True,
                    )
                    logger.warning("worker_unexpected_failure")
        except (LeaseOwnershipError, ProcessingJobNotFoundError):
            logger.warning("worker_ownership_lost")
        except Exception:
            # A failed/ambiguous transaction is recovered by lease expiry and idempotent replay.
            logger.warning("worker_transition_unavailable")
