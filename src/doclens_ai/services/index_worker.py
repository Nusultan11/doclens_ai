from __future__ import annotations

import asyncio
import logging
import time

from doclens_ai.models import IndexRevisionStatus, ProcessingStage
from doclens_ai.services.indexing import IndexingFailure, IndexingFailureCategory, IndexingService
from doclens_ai.services.processing import (
    ClaimedProcessingJob,
    InvalidProcessingTransition,
    LeaseOwnershipError,
    ProcessingCoordinator,
    ProcessingJobNotFoundError,
)
from doclens_ai.services.worker import IngestionWorker, WorkerSettings

logger = logging.getLogger(__name__)


class IndexWorker(IngestionWorker):
    """Reuse polling, heartbeat, shutdown and lease policy; execute only vector stages."""

    def __init__(
        self,
        coordinator: ProcessingCoordinator,
        indexing: IndexingService,
        *,
        settings: WorkerSettings | None = None,
        worker_id: str | None = None,
    ) -> None:
        # The parent owns lifecycle/heartbeat only; its extraction executor is overridden.
        super().__init__(coordinator, indexing, settings=settings, worker_id=worker_id)  # type: ignore[arg-type]
        self.indexing = indexing

    async def run_once(self) -> bool:
        if self._stop.is_set():
            return False
        try:
            async with asyncio.timeout(self.settings.db_timeout_seconds):
                claim = await self.coordinator.claim_next(
                    worker_id=self.worker_id,
                    stages=(ProcessingStage.EMBEDDING, ProcessingStage.INDEXING),
                )
        except Exception:
            logger.warning("index_claim_unavailable")
            return False
        if claim is None:
            return False
        await self._execute(claim)
        return True

    async def _execute(self, claim: ClaimedProcessingJob) -> None:
        started = time.perf_counter()
        heartbeat_stop = asyncio.Event()
        heartbeat = asyncio.create_task(self._heartbeat(claim, heartbeat_stop))
        operation = asyncio.create_task(
            self.indexing.index(
                claim.processing_run_id, worker_id=self.worker_id, lease_token=claim.lease_token
            )
        )
        failure, result, heartbeat_failed = None, None, False
        try:
            try:
                result = await asyncio.shield(operation)
            except asyncio.CancelledError:
                self.request_stop()
                try:
                    await asyncio.shield(operation)
                except Exception:
                    logger.warning("index_cancelled_operation_failed")
                raise
            except Exception as error:
                failure = error
        finally:
            heartbeat_stop.set()
            try:
                await heartbeat
            except Exception:
                heartbeat_failed = True
                logger.warning("index_heartbeat_lost")
        if heartbeat_failed:
            return
        try:
            async with asyncio.timeout(self.settings.db_timeout_seconds):
                if failure is None:
                    activation = await self.coordinator.complete(
                        job_id=claim.job_id,
                        worker_id=self.worker_id,
                        lease_token=claim.lease_token,
                        index_revision_id=result.revision_id,
                    )
                    logger.info(
                        "%s indexed_chunks=%d duration_ms=%.3f embedding_ms=%.3f "
                        "embedding_failures=0 incomplete_candidates=0",
                        "index_superseded"
                        if activation == IndexRevisionStatus.SUPERSEDED
                        else "index_completed",
                        result.indexed_chunks,
                        (time.perf_counter() - started) * 1000,
                        result.embedding_ms,
                    )
                    return
                if isinstance(failure, IndexingFailure):
                    if failure.category in {
                        IndexingFailureCategory.OWNERSHIP_LOST,
                        IndexingFailureCategory.STATE_MISMATCH,
                    }:
                        logger.warning("index_ownership_lost")
                        return
                    code, retryable = failure.category.value, failure.retryable
                else:
                    code, retryable = "index_unexpected_failure", True
                await self.coordinator.fail_attempt(
                    job_id=claim.job_id,
                    worker_id=self.worker_id,
                    lease_token=claim.lease_token,
                    failure_reason=code,
                    retryable=retryable,
                )
                embedding_failures = int(
                    isinstance(failure, IndexingFailure)
                    and failure.category
                    in {
                        IndexingFailureCategory.EMBEDDING_INVALID,
                        IndexingFailureCategory.EMBEDDING_UNAVAILABLE,
                    }
                )
                logger.warning(
                    "index_failed code=%s embedding_failures=%d duration_ms=%.3f",
                    code,
                    embedding_failures,
                    (time.perf_counter() - started) * 1000,
                )
        except (LeaseOwnershipError, ProcessingJobNotFoundError):
            logger.warning("index_ownership_lost")
        except InvalidProcessingTransition:
            try:
                async with asyncio.timeout(self.settings.db_timeout_seconds):
                    await self.coordinator.fail_attempt(
                        job_id=claim.job_id,
                        worker_id=self.worker_id,
                        lease_token=claim.lease_token,
                        failure_reason="invalid_index_completion",
                        retryable=False,
                    )
            except Exception:
                logger.warning("index_transition_unavailable")
        except Exception:
            # Ambiguous DB commit never routes another mutation through uncertain ownership.
            logger.warning("index_transition_unavailable")
