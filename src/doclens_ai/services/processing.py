from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from doclens_ai.chunking.models import (
    ChunkingConfig,
    ChunkingStrategy,
    config_as_dict,
)
from doclens_ai.models import (
    CanonicalChunk,
    Document,
    IndexRevision,
    IndexRevisionStatus,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingOperationKind,
    ProcessingRun,
    ProcessingStage,
    ProcessingStatus,
)
from doclens_ai.models.index_revision import chunk_set_fingerprint

PROCESSING_CONFIGURATION_VERSION = "1.0"
DEFAULT_MAX_ATTEMPTS = 3
_SAFE_CODE = re.compile(r"^[a-z0-9][a-z0-9_]{0,63}$")
_STAGE_ORDER = tuple(ProcessingStage)


class ProcessingJobNotFoundError(LookupError):
    pass


class LeaseOwnershipError(RuntimeError):
    pass


class InvalidProcessingTransition(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProcessingPolicy:
    lease_duration: timedelta = timedelta(minutes=5)
    retry_base_delay: timedelta = timedelta(seconds=30)
    retry_max_delay: timedelta = timedelta(minutes=30)

    def __post_init__(self) -> None:
        if self.lease_duration <= timedelta(0):
            raise ValueError("lease duration must be positive")
        if self.retry_base_delay <= timedelta(0):
            raise ValueError("retry base delay must be positive")
        if self.retry_max_delay < self.retry_base_delay:
            raise ValueError("retry max delay must not be smaller than the base delay")

    def retry_delay(self, attempt_count: int) -> timedelta:
        if attempt_count <= 0:
            raise ValueError("attempt count must be positive")
        multiplier = 2 ** min(attempt_count - 1, 30)
        return min(self.retry_base_delay * multiplier, self.retry_max_delay)


@dataclass(frozen=True, slots=True)
class ClaimedProcessingJob:
    job_id: UUID
    processing_run_id: UUID
    document_version_id: UUID
    stage: ProcessingStage
    lease_token: UUID
    lease_expires_at: datetime
    attempt_count: int
    max_attempts: int


def default_processing_configuration_fingerprint() -> str:
    """Fingerprint the frozen offline contracts selected for the initial pipeline."""

    payload = {
        "chunking": config_as_dict(ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE)),
        "extraction_contract_version": "1.0",
        "pipeline_version": PROCESSING_CONFIGURATION_VERSION,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


async def create_initial_processing_records(
    session: AsyncSession,
    *,
    document_version_id: UUID,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> tuple[ProcessingRun, ProcessingJob]:
    """Add the one initial run and queued job to the caller's transaction."""

    if max_attempts <= 0:
        raise ValueError("max attempts must be positive")
    run = ProcessingRun(
        id=uuid4(),
        document_version_id=document_version_id,
        operation_id=document_version_id,
        operation_kind=ProcessingOperationKind.INITIAL,
        configuration_version=PROCESSING_CONFIGURATION_VERSION,
        configuration_fingerprint=default_processing_configuration_fingerprint(),
        stage=ProcessingStage.EXTRACTION,
        status=ProcessingStatus.QUEUED,
    )
    job = ProcessingJob(
        id=uuid4(),
        processing_run_id=run.id,
        status=ProcessingJobStatus.QUEUED,
        attempt_count=0,
        max_attempts=max_attempts,
    )
    session.add_all([run, job])
    await session.flush()
    return run, job


async def get_initial_processing_job(
    session: AsyncSession,
    *,
    document_version_id: UUID,
) -> ProcessingJob | None:
    return await session.scalar(
        select(ProcessingJob)
        .join(ProcessingRun, ProcessingRun.id == ProcessingJob.processing_run_id)
        .where(
            ProcessingRun.document_version_id == document_version_id,
            ProcessingRun.operation_kind == ProcessingOperationKind.INITIAL,
        )
    )


class ProcessingCoordinator:
    """Lease-based PostgreSQL coordinator without any document-processing handler."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        policy: ProcessingPolicy | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy or ProcessingPolicy()

    @property
    def lease_duration(self) -> timedelta:
        return self._policy.lease_duration

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime | None = None,
        stage: ProcessingStage | None = None,
        stages: tuple[ProcessingStage, ...] | None = None,
    ) -> ClaimedProcessingJob | None:
        _validate_worker_id(worker_id)
        if stages is not None and (stage is not None or not stages):
            raise ValueError("choose one nonempty stage filter")
        selected_stages = (
            stages if stages is not None else ((stage,) if stage is not None else None)
        )
        async with self._session_factory() as session, session.begin():
            while True:
                claimed_at = await _processing_now(session, now)
                row = (
                    await session.execute(
                        select(ProcessingJob, ProcessingRun)
                        .join(
                            ProcessingRun,
                            ProcessingRun.id == ProcessingJob.processing_run_id,
                        )
                        .where(
                            ProcessingRun.stage.in_(selected_stages)
                            if selected_stages is not None
                            else True,
                            or_(
                                ProcessingJob.status == ProcessingJobStatus.QUEUED,
                                (
                                    (ProcessingJob.status == ProcessingJobStatus.RETRY_WAIT)
                                    & (ProcessingJob.next_retry_at <= claimed_at)
                                ),
                                (
                                    (ProcessingJob.status == ProcessingJobStatus.LEASED)
                                    & (ProcessingJob.lease_expires_at <= claimed_at)
                                ),
                            ),
                        )
                        .order_by(ProcessingJob.created_at, ProcessingJob.id)
                        .limit(1)
                        .with_for_update(of=ProcessingJob, skip_locked=True)
                    )
                ).first()
                if row is None:
                    return None
                job, run = row
                job, run = await _locked_job_and_run(session, job.id)
                claimed_at = await _processing_now(session, now)
                if selected_stages is not None and run.stage not in selected_stages:
                    return None
                if job.attempt_count >= job.max_attempts:
                    _mark_terminal_failure(
                        job,
                        run,
                        reason="attempts_exhausted",
                        now=claimed_at,
                    )
                    await session.flush()
                    continue

                lease_token = uuid4()
                lease_expires_at = claimed_at + self._policy.lease_duration
                job.status = ProcessingJobStatus.LEASED
                job.worker_id = worker_id
                job.lease_token = lease_token
                job.lease_expires_at = lease_expires_at
                job.attempt_count += 1
                job.next_retry_at = None
                job.failure_reason = None
                job.leased_at = claimed_at
                job.last_heartbeat_at = claimed_at
                job.finished_at = None
                run.status = ProcessingStatus.PROCESSING
                run.error_code = None
                await session.flush()
                return ClaimedProcessingJob(
                    job_id=job.id,
                    processing_run_id=run.id,
                    document_version_id=run.document_version_id,
                    stage=ProcessingStage(run.stage),
                    lease_token=lease_token,
                    lease_expires_at=lease_expires_at,
                    attempt_count=job.attempt_count,
                    max_attempts=job.max_attempts,
                )

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        lease_token: UUID,
        now: datetime | None = None,
    ) -> datetime:
        async with self._session_factory() as session, session.begin():
            job = await _locked_job(session, job_id)
            heartbeat_at = await _processing_now(session, now)
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=heartbeat_at,
            )
            job.last_heartbeat_at = heartbeat_at
            job.lease_expires_at = heartbeat_at + self._policy.lease_duration
            await session.flush()
            return job.lease_expires_at

    async def advance_stage(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        lease_token: UUID,
        stage: ProcessingStage,
        now: datetime | None = None,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            job, run = await _locked_job_and_run(session, job_id)
            transition_at = await _processing_now(session, now)
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=transition_at,
            )
            current_index = _STAGE_ORDER.index(ProcessingStage(run.stage))
            if current_index + 1 >= len(_STAGE_ORDER) or _STAGE_ORDER[current_index + 1] != stage:
                raise InvalidProcessingTransition("processing stages must advance one step")
            run.stage = stage

    async def fail_attempt(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        lease_token: UUID,
        failure_reason: str,
        now: datetime | None = None,
        retryable: bool = True,
    ) -> ProcessingJobStatus:
        _validate_safe_code(failure_reason)
        async with self._session_factory() as session, session.begin():
            job, run = await _locked_job_and_run(session, job_id)
            failed_at = await _processing_now(session, now)
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=failed_at,
            )
            if not retryable or job.attempt_count >= job.max_attempts:
                _mark_terminal_failure(job, run, reason=failure_reason, now=failed_at)
                return ProcessingJobStatus.FAILED

            job.status = ProcessingJobStatus.RETRY_WAIT
            job.next_retry_at = failed_at + self._policy.retry_delay(job.attempt_count)
            job.failure_reason = failure_reason
            _clear_lease(job)
            run.status = ProcessingStatus.RETRY_WAIT
            run.error_code = failure_reason
            return ProcessingJobStatus.RETRY_WAIT

    async def handoff_extraction(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        lease_token: UUID,
    ) -> None:
        """Publish one atomic EXTRACTION -> EMBEDDING stage boundary, not completion."""
        async with self._session_factory() as session, session.begin():
            job, run = await _locked_job_and_run(session, job_id)
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=await _processing_now(session),
            )
            if run.status != ProcessingStatus.PROCESSING or run.stage != ProcessingStage.EXTRACTION:
                raise InvalidProcessingTransition("extraction handoff requires an extraction run")
            if not await session.scalar(
                select(CanonicalChunk.id).where(CanonicalChunk.processing_run_id == run.id).limit(1)
            ):
                raise InvalidProcessingTransition("extraction handoff requires canonical chunks")
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=await _processing_now(session),
            )
            # Cleaning and chunking already succeeded within the fenced ingestion contract.
            lease_expires_at = job.lease_expires_at
            # Reset the per-stage attempt budget only on a successful durable boundary.
            run.stage = ProcessingStage.EMBEDDING
            run.status = ProcessingStatus.QUEUED
            run.error_code = None
            job.status = ProcessingJobStatus.QUEUED
            job.attempt_count = 0
            job.next_retry_at = None
            job.failure_reason = None
            job.finished_at = None
            job.leased_at = None
            job.last_heartbeat_at = None
            _clear_lease(job)
            await session.flush()
            if await _processing_now(session) >= lease_expires_at:
                raise LeaseOwnershipError("processing lease expired during handoff")

    async def complete(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        lease_token: UUID,
        now: datetime | None = None,
        index_revision_id: UUID | None = None,
    ) -> IndexRevisionStatus:
        async with self._session_factory() as session, session.begin():
            job, run = await _locked_job_and_run(session, job_id)
            completed_at = await _processing_now(session, now)
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=completed_at,
            )
            if run.stage != ProcessingStage.INDEXING:
                raise InvalidProcessingTransition(
                    "processing cannot complete before the indexing stage"
                )
            if index_revision_id is None:
                raise InvalidProcessingTransition("completion requires a verified index revision")
            revision = await session.get(IndexRevision, index_revision_id)
            if revision is None or revision.processing_run_id != run.id:
                raise InvalidProcessingTransition("completion requires a verified index revision")
            # Serialize cutover across different runs/versions of the same logical document.
            document = await session.scalar(
                select(Document).where(Document.id == revision.document_id).with_for_update()
            )
            if document is None or document.workspace_id != revision.workspace_id:
                raise InvalidProcessingTransition("verified index scope changed")
            revision = await session.scalar(
                select(IndexRevision)
                .where(IndexRevision.id == index_revision_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if (
                run.status != ProcessingStatus.PROCESSING
                or revision.lease_token != lease_token
                or revision.document_version_id != run.document_version_id
                or revision.status != IndexRevisionStatus.VERIFIED
                or revision.verified_at is None
                or revision.verified_point_count != revision.expected_point_count
            ):
                raise InvalidProcessingTransition("completion requires this lease's verified index")
            canonical = tuple(
                await session.execute(
                    select(
                        CanonicalChunk.id,
                        CanonicalChunk.ordinal,
                        CanonicalChunk.chunk_identity,
                        CanonicalChunk.content_sha256,
                    )
                    .where(CanonicalChunk.processing_run_id == run.id)
                    .order_by(CanonicalChunk.ordinal)
                )
            )
            if (
                len(canonical) != revision.expected_point_count
                or chunk_set_fingerprint(canonical) != revision.canonical_chunk_set_fingerprint
            ):
                raise InvalidProcessingTransition("verified canonical chunk set changed")
            active = await session.scalar(
                select(IndexRevision)
                .where(
                    IndexRevision.document_id == revision.document_id,
                    IndexRevision.status == IndexRevisionStatus.ACTIVE,
                )
                .with_for_update()
            )
            active_run = (
                await session.get(ProcessingRun, active.processing_run_id) if active else None
            )
            completed_at = await _processing_now(session)
            _require_active_lease(
                job, worker_id=worker_id, lease_token=lease_token, now=completed_at
            )
            lease_expires_at = job.lease_expires_at
            older = active is not None and (
                (revision.document_version_number, run.created_at, str(run.id))
                < (active.document_version_number, active_run.created_at, str(active_run.id))
            )
            if older:
                revision.status = IndexRevisionStatus.SUPERSEDED
                revision.superseded_at = completed_at
                _mark_terminal_failure(job, run, reason="obsolete_index_revision", now=completed_at)
            else:
                if active is not None:
                    active.status = IndexRevisionStatus.SUPERSEDED
                    active.superseded_at = completed_at
                    # Release the unique active slot before activating the replacement.
                    await session.flush()
                revision.status = IndexRevisionStatus.ACTIVE
                revision.activated_at = completed_at
                job.status = ProcessingJobStatus.COMPLETED
                job.failure_reason = None
                job.finished_at = completed_at
                _clear_lease(job)
                run.status = ProcessingStatus.COMPLETED
                run.error_code = None
            await session.flush()
            if await _processing_now(session) >= lease_expires_at:
                raise LeaseOwnershipError("processing lease expired during activation")
            return IndexRevisionStatus(revision.status)


async def _locked_job(session: AsyncSession, job_id: UUID) -> ProcessingJob:
    job = await session.scalar(
        select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
    )
    if job is None:
        raise ProcessingJobNotFoundError("processing job does not exist")
    return job


async def _locked_job_and_run(
    session: AsyncSession,
    job_id: UUID,
) -> tuple[ProcessingJob, ProcessingRun]:
    # All coordinator and canonical-ingestion writers acquire Job before Run.
    job = await _locked_job(session, job_id)
    run = await session.scalar(
        select(ProcessingRun)
        .where(ProcessingRun.id == job.processing_run_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if run is None:
        raise ProcessingJobNotFoundError("processing job does not exist")
    return job, run


async def _processing_now(session: AsyncSession, value: datetime | None = None) -> datetime:
    """Sample wall-clock time after locks; explicit coordinator times support existing tests."""
    if value is not None:
        return _coerce_now(value)
    current = await session.scalar(select(func.clock_timestamp()))
    assert current is not None
    return current


def _require_active_lease(
    job: ProcessingJob,
    *,
    worker_id: str,
    lease_token: UUID,
    now: datetime,
) -> None:
    _validate_worker_id(worker_id)
    if (
        job.status != ProcessingJobStatus.LEASED
        or job.worker_id != worker_id
        or job.lease_token != lease_token
        or job.lease_expires_at is None
        or job.lease_expires_at <= now
    ):
        raise LeaseOwnershipError("processing lease is not active for this worker")


def _mark_terminal_failure(
    job: ProcessingJob,
    run: ProcessingRun,
    *,
    reason: str,
    now: datetime,
) -> None:
    _validate_safe_code(reason)
    job.status = ProcessingJobStatus.FAILED
    job.next_retry_at = None
    job.failure_reason = reason
    job.finished_at = now
    _clear_lease(job)
    run.status = ProcessingStatus.FAILED
    run.error_code = reason


def _clear_lease(job: ProcessingJob) -> None:
    job.worker_id = None
    job.lease_token = None
    job.lease_expires_at = None


def _validate_worker_id(worker_id: str) -> None:
    if not isinstance(worker_id, str) or not worker_id.strip() or len(worker_id) > 255:
        raise ValueError("worker identity must contain 1 to 255 characters")


def _validate_safe_code(value: str) -> None:
    if _SAFE_CODE.fullmatch(value) is None:
        raise ValueError("failure reason must be a sanitized code")


def _coerce_now(value: datetime | None) -> datetime:
    now = value or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return now
