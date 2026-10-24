"""Reserve -> immutable S3 write/readback -> fenced PG publication.

Reservations precede external writes, so interrupted writes retain a cleanup
identity. Staging snapshots can be recovered by a new lease without extraction.
Available snapshots are never rewritten or garbage-collected here.
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from typing import Annotated, Literal, Protocol
from uuid import UUID, uuid5

from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from doclens_ai.extraction.engines import EngineRoute, StoredEngineRouteV1, StoredEngineRouteV1_1
from doclens_ai.extraction.ir import Contract, DocumentIR, SourceIdentity
from doclens_ai.models import CanonicalChunk, ExtractionArtifact, ProcessingJob, ProcessingRun
from doclens_ai.services.processing import (
    LeaseOwnershipError,
    _locked_job_and_run,
    _processing_now,
    _require_active_lease,
)
from doclens_ai.storage.s3 import ObjectStorageError

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


class ArtifactError(RuntimeError):
    """Sanitized immutable snapshot conflict/corruption; never source text."""


class ArtifactStorage(Protocol):
    async def put_immutable(self, key: str, payload: bytes, *, sha256_checksum: str) -> None: ...
    def stream_read(self, key: str, *, chunk_size: int = 1024 * 1024) -> AsyncIterator[bytes]: ...
    async def delete(self, key: str) -> None: ...


class ExtractionSnapshot(Contract):
    artifact_version: Literal["1.0"] = "1.0"
    source: SourceIdentity
    route: Annotated[
        StoredEngineRouteV1 | StoredEngineRouteV1_1 | EngineRoute, Field(discriminator="version")
    ]
    observations: tuple[DocumentIR, ...]
    reconciled: DocumentIR


async def _owned(
    session: AsyncSession, run_id: UUID, job_id: UUID, worker_id: str, lease_token: UUID
) -> tuple[ProcessingJob, ProcessingRun]:
    job, run = await _locked_job_and_run(session, job_id)
    if run.id != run_id or run.stage != "extraction" or run.status != "processing":
        raise LeaseOwnershipError("artifact processing ownership lost")
    _require_active_lease(
        job, worker_id=worker_id, lease_token=lease_token, now=await _processing_now(session)
    )
    return job, run


class ExtractionArtifacts:
    def __init__(self, factory: async_sessionmaker[AsyncSession], storage: ArtifactStorage):
        self.factory, self.storage = factory, storage

    async def _read(
        self, record: ExtractionArtifact, expected: SourceIdentity
    ) -> ExtractionSnapshot:
        if (
            str(record.workspace_id) != expected.workspace_id
            or str(record.document_version_id) != expected.document_version_id
        ):
            raise ArtifactError("artifact_scope_mismatch")
        data = bytearray()
        async for piece in self.storage.stream_read(record.object_storage_key):
            if len(data) + len(piece) > min(record.size_bytes, MAX_ARTIFACT_BYTES):
                raise ArtifactError("artifact_size_mismatch")
            data.extend(piece)
        if len(data) != record.size_bytes or hashlib.sha256(data).hexdigest() != record.checksum:
            raise ArtifactError("artifact_checksum_mismatch")
        try:
            snapshot = ExtractionSnapshot.model_validate_json(bytes(data))
        except ValueError as exc:
            raise ArtifactError("artifact_invalid") from exc
        if (
            snapshot.source != expected
            or snapshot.reconciled.source != expected
            or snapshot.route.fingerprint() != record.route_fingerprint
        ):
            raise ArtifactError("artifact_identity_mismatch")
        return snapshot

    async def load(
        self, artifact_id: UUID, *, expected: SourceIdentity
    ) -> tuple[ExtractionArtifact, ExtractionSnapshot]:
        async with self.factory() as session:
            record = await session.get(ExtractionArtifact, artifact_id)
            if record is None or record.state != "available":
                raise ArtifactError("artifact_not_available")
        return record, await self._read(record, expected)

    async def for_run(
        self,
        *,
        run_id: UUID,
        job_id: UUID,
        expected: SourceIdentity,
        route: EngineRoute,
        worker_id: str,
        lease_token: UUID,
    ) -> tuple[UUID, str, ExtractionSnapshot] | None:
        async with self.factory() as session:
            record = await session.scalar(
                select(ExtractionArtifact).where(
                    ExtractionArtifact.processing_run_id == run_id,
                    ExtractionArtifact.route_fingerprint == route.fingerprint(),
                )
            )
        if record is None:
            return None
        if record.state == "discarded":
            raise ArtifactError("artifact_discarded")
        try:
            snapshot = await self._read(record, expected)
        except ObjectStorageError as exc:
            # A reservation whose object was never created is safe to retry; only
            # a definite missing key qualifies. Outages must not rerun extraction.
            cause = exc.__cause__
            response = getattr(cause, "response", {})
            if record.state == "staging" and str(response.get("Error", {}).get("Code")) in {
                "404",
                "NoSuchKey",
                "NotFound",
            }:
                return None
            raise
        if record.state == "staging":
            await self._publish(
                record.id,
                run_id=run_id,
                job_id=job_id,
                worker_id=worker_id,
                lease_token=lease_token,
            )
        return record.id, record.checksum, snapshot

    async def store(
        self,
        snapshot: ExtractionSnapshot,
        *,
        run_id: UUID,
        job_id: UUID,
        worker_id: str,
        lease_token: UUID,
    ) -> tuple[UUID, str]:
        data = snapshot.model_dump_json().encode()
        if len(data) > snapshot.route.artifact_max_bytes:
            raise ArtifactError("artifact_limit")
        checksum = hashlib.sha256(data).hexdigest()
        route_fp = snapshot.route.fingerprint()
        identity = uuid5(run_id, "extraction:" + route_fp)
        key = (
            f"workspaces/{snapshot.source.workspace_id}/versions/{snapshot.source.document_version_id}"
            f"/extraction/{identity}/{checksum}.json"
        )
        async with self.factory() as session, session.begin():
            _, run = await _owned(session, run_id, job_id, worker_id, lease_token)
            if run.extraction_route != snapshot.route.model_dump(mode="json"):
                raise ArtifactError("artifact_route_mismatch")
            record = await session.get(ExtractionArtifact, identity)
            if record is not None:
                if (
                    record.checksum != checksum
                    or record.object_storage_key != key
                    or record.state == "discarded"
                ):
                    raise ArtifactError("artifact_observation_conflict")
            else:
                record = ExtractionArtifact(
                    id=identity,
                    processing_run_id=run_id,
                    document_version_id=UUID(snapshot.source.document_version_id),
                    workspace_id=UUID(snapshot.source.workspace_id),
                    route_fingerprint=route_fp,
                    checksum=checksum,
                    size_bytes=len(data),
                    object_storage_key=key,
                    artifact_version="1.0",
                    state="staging",
                    source_state=snapshot.reconciled.state,
                    lease_token=lease_token,
                )
                session.add(record)
                await session.flush()
            await _owned(session, run_id, job_id, worker_id, lease_token)
        await self.storage.put_immutable(key, data, sha256_checksum=checksum)
        await self._read(record, snapshot.source)  # Exact readback, including on duplicate PUT.
        await self._publish(
            identity, run_id=run_id, job_id=job_id, worker_id=worker_id, lease_token=lease_token
        )
        return identity, checksum

    async def _publish(
        self, identity: UUID, *, run_id: UUID, job_id: UUID, worker_id: str, lease_token: UUID
    ) -> None:
        async with self.factory() as session, session.begin():
            await _owned(session, run_id, job_id, worker_id, lease_token)
            record = await session.scalar(
                select(ExtractionArtifact)
                .where(ExtractionArtifact.id == identity)
                .with_for_update()
            )
            if record is None or record.processing_run_id != run_id or record.state == "discarded":
                raise ArtifactError("artifact_publication_conflict")
            if record.state == "staging":
                record.state, record.lease_token = "available", lease_token
                await session.flush()
            await _owned(session, run_id, job_id, worker_id, lease_token)

    async def cleanup_failed(self, *, limit: int = 100) -> int:
        """Reference-owned terminal cleanup; retained reservations make retry safe.

        A stale writer may finish an already-started upload after deletion. Repeat
        cleanup of discarded rows removes it; available/rechunkable artifacts are
        never eligible. No list/delete of unrelated S3 prefixes is performed.
        """
        if not 1 <= limit <= 1000:
            raise ValueError("cleanup limit outside supported range")
        async with self.factory() as session:
            ids = tuple(
                await session.scalars(
                    select(ExtractionArtifact.id)
                    .join(
                        ProcessingJob,
                        ProcessingJob.processing_run_id == ExtractionArtifact.processing_run_id,
                    )
                    .where(
                        ExtractionArtifact.state.in_(("staging", "discarded")),
                        ProcessingJob.status == "failed",
                    )
                    .limit(limit)
                )
            )
        cleaned = 0
        for identity in ids:
            async with self.factory() as session, session.begin():
                candidate = await session.get(ExtractionArtifact, identity)
                job = await session.scalar(
                    select(ProcessingJob)
                    .where(ProcessingJob.processing_run_id == candidate.processing_run_id)
                    .with_for_update()
                )
                if job is None or job.status != "failed":
                    continue
                record = await session.scalar(
                    select(ExtractionArtifact)
                    .where(ExtractionArtifact.id == identity)
                    .with_for_update()
                )
                if record.state == "available":
                    continue
                referenced = await session.scalar(
                    select(CanonicalChunk.id)
                    .where(
                        CanonicalChunk.source_provenance.contains(
                            [{"extraction_artifact_id": str(record.id)}]
                        )
                    )
                    .limit(1)
                )
                if referenced is not None:
                    continue
                if record.state == "staging":
                    record.state = "discarded"
                key = record.object_storage_key
            await self.storage.delete(key)
            cleaned += 1
        return cleaned
