from __future__ import annotations

import asyncio
import hashlib
import tempfile
from collections.abc import AsyncIterator
from dataclasses import dataclass, fields
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid5

from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from doclens_ai.chunking.core import chunk_document
from doclens_ai.chunking.models import (
    Chunk,
    ChunkingConfig,
    ChunkingReason,
    ChunkingStatus,
    ChunkingStrategy,
)
from doclens_ai.extraction.models import ExtractionStatus
from doclens_ai.extraction.parsers import SCHEMA_VERSION, ExtractionLimits, extract_file
from doclens_ai.extraction.runtime import runtime_versions_match
from doclens_ai.extraction.validation import evidence_is_indexable
from doclens_ai.models import (
    CanonicalChunk,
    DocumentVersion,
    ProcessingJob,
    ProcessingRun,
    ProcessingStage,
    ProcessingStatus,
)
from doclens_ai.services.processing import (
    PROCESSING_CONFIGURATION_VERSION,
    LeaseOwnershipError,
    ProcessingJobNotFoundError,
    _locked_job_and_run,
    _processing_now,
    _require_active_lease,
    default_processing_configuration_fingerprint,
)
from doclens_ai.storage.s3 import ObjectMetadata, ObjectStorageError

_SUFFIX_BY_CONTENT_TYPE = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}
_MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NoSuchObject", "NotFound"}


class IngestionFailureCategory(StrEnum):
    PROCESSING_RUN_NOT_FOUND = "processing_run_not_found"
    LEASE_OWNERSHIP_LOST = "lease_ownership_lost"
    PROCESSING_STATE_MISMATCH = "processing_state_mismatch"
    CONFIGURATION_MISMATCH = "configuration_mismatch"
    SOURCE_OBJECT_MISSING = "source_object_missing"
    SOURCE_IDENTITY_MISMATCH = "source_identity_mismatch"
    SOURCE_LIMIT_EXCEEDED = "source_limit_exceeded"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    TEMPORARY_STORAGE_UNAVAILABLE = "temporary_storage_unavailable"
    EXTRACTION_NEEDS_REVIEW = "extraction_needs_review"
    EXTRACTION_FAILED = "extraction_failed"
    EMPTY_CONTENT = "empty_content"
    CHUNKING_FAILED = "chunking_failed"
    PERSISTENCE_CONFLICT = "persistence_conflict"
    PERSISTENCE_UNAVAILABLE = "persistence_unavailable"


class IngestionFailure(RuntimeError):
    """Sanitized ingestion failure with an explicit retry classification."""

    def __init__(
        self,
        category: IngestionFailureCategory,
        *,
        retryable: bool,
        document_error_category: str | None = None,
    ) -> None:
        super().__init__(category.value)
        self.category = category
        self.retryable = retryable
        self.document_error_category = document_error_category


class IngestionResultStatus(StrEnum):
    PERSISTED = "persisted"
    ALREADY_PERSISTED = "already_persisted"


@dataclass(frozen=True, slots=True)
class IngestionResult:
    processing_run_id: UUID
    document_version_id: UUID
    status: IngestionResultStatus
    chunk_count: int


class ReadableObjectStorage(Protocol):
    async def inspect(self, key: str) -> ObjectMetadata: ...

    def stream_read(
        self,
        key: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]: ...


@dataclass(frozen=True, slots=True)
class _SourceIdentity:
    processing_run_id: UUID
    processing_job_id: UUID
    document_version_id: UUID
    configuration_version: str
    configuration_fingerprint: str
    object_storage_key: str
    content_type: str
    file_size: int
    sha256_checksum: str


@dataclass(frozen=True, slots=True)
class CanonicalChunkPayload:
    id: UUID
    processing_run_id: UUID
    ordinal: int
    chunk_identity: str
    chunk_text: str
    content_sha256: str
    character_count: int
    token_count: int | None
    document_format: str
    chunking_strategy: str
    chunker_version: str
    chunker_configuration_fingerprint: str
    source_provenance: list[dict[str, object]]
    split_oversized_element: bool


class IngestionService:
    """Extract and atomically publish canonical chunks for a trusted processing run."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: ReadableObjectStorage,
        *,
        download_chunk_size: int = 1024 * 1024,
    ) -> None:
        if download_chunk_size <= 0:
            raise ValueError("download chunk size must be positive")
        self._session_factory = session_factory
        self._storage = storage
        self._extraction_limits = ExtractionLimits()
        self._download_chunk_size = download_chunk_size
        self._chunking_config = ChunkingConfig(
            strategy=ChunkingStrategy.STRUCTURE_AWARE
        )

    async def ingest(
        self, processing_run_id: UUID, *, worker_id: str, lease_token: UUID
    ) -> IngestionResult:
        source = await self._resolve_source(
            processing_run_id, worker_id=worker_id, lease_token=lease_token
        )
        self._validate_processing_configuration(source)
        suffix = _SUFFIX_BY_CONTENT_TYPE.get(source.content_type)
        if suffix is None:
            raise IngestionFailure(
                IngestionFailureCategory.SOURCE_IDENTITY_MISMATCH,
                retryable=False,
            )
        chunks = await self._extract_and_chunk(source, suffix=suffix)
        canonical = tuple(canonicalize_chunk(source.processing_run_id, chunk) for chunk in chunks)
        return await self._persist(source, canonical, worker_id=worker_id, lease_token=lease_token)

    async def _resolve_source(
        self, processing_run_id: UUID, *, worker_id: str, lease_token: UUID
    ) -> _SourceIdentity:
        try:
            async with self._session_factory() as session:
                row = (
                    await session.execute(
                        select(ProcessingRun, DocumentVersion, ProcessingJob)
                        .join(
                            DocumentVersion,
                            DocumentVersion.id == ProcessingRun.document_version_id,
                        )
                        .outerjoin(
                            ProcessingJob, ProcessingJob.processing_run_id == ProcessingRun.id
                        )
                        .where(ProcessingRun.id == processing_run_id)
                    )
                ).first()
                if row is None:
                    raise IngestionFailure(
                        IngestionFailureCategory.PROCESSING_RUN_NOT_FOUND, retryable=False
                    )
                run, version, job = row
                await _require_ingestion_ownership(
                    session, job, run, worker_id=worker_id, lease_token=lease_token
                )
        except SQLAlchemyError as exc:
            raise IngestionFailure(
                IngestionFailureCategory.PERSISTENCE_UNAVAILABLE,
                retryable=True,
            ) from exc
        return _SourceIdentity(
            processing_run_id=run.id,
            processing_job_id=job.id,
            document_version_id=version.id,
            configuration_version=run.configuration_version,
            configuration_fingerprint=run.configuration_fingerprint,
            object_storage_key=version.object_storage_key,
            content_type=version.content_type,
            file_size=version.file_size,
            sha256_checksum=version.sha256_checksum,
        )

    def _validate_processing_configuration(self, source: _SourceIdentity) -> None:
        if (
            not runtime_versions_match()
            or source.configuration_version != PROCESSING_CONFIGURATION_VERSION
            or source.configuration_fingerprint != default_processing_configuration_fingerprint()
        ):
            raise IngestionFailure(
                IngestionFailureCategory.CONFIGURATION_MISMATCH,
                retryable=False,
            )

    async def _extract_and_chunk(
        self,
        source: _SourceIdentity,
        *,
        suffix: str,
    ) -> tuple[Chunk, ...]:
        if source.file_size <= 0:
            raise IngestionFailure(
                IngestionFailureCategory.SOURCE_IDENTITY_MISMATCH,
                retryable=False,
            )
        if source.file_size > self._extraction_limits.max_file_bytes:
            raise IngestionFailure(
                IngestionFailureCategory.SOURCE_LIMIT_EXCEEDED,
                retryable=False,
            )
        try:
            metadata = await self._storage.inspect(source.object_storage_key)
        except ObjectStorageError as exc:
            raise _classified_storage_failure(exc) from exc
        self._validate_metadata(source, metadata)

        try:
            temporary = await asyncio.to_thread(
                tempfile.TemporaryDirectory,
                prefix="doclens-ingestion-",
            )
        except OSError as exc:
            raise IngestionFailure(
                IngestionFailureCategory.TEMPORARY_STORAGE_UNAVAILABLE,
                retryable=True,
            ) from exc
        source_path = Path(temporary.name) / f"source{suffix}"
        try:
            await self._download_verified(source, source_path)
            extraction = await asyncio.to_thread(
                extract_file,
                source_path,
                limits=self._extraction_limits,
            )
            if extraction.schema_version != SCHEMA_VERSION:
                raise IngestionFailure(
                    IngestionFailureCategory.CONFIGURATION_MISMATCH,
                    retryable=False,
                )
            if (
                extraction.source_sha256 != source.sha256_checksum
                or extraction.source_size_bytes != source.file_size
                or extraction.document_format is None
                or f".{extraction.document_format.value}" != suffix
            ):
                raise IngestionFailure(
                    IngestionFailureCategory.SOURCE_IDENTITY_MISMATCH,
                    retryable=False,
                )
            if extraction.status is ExtractionStatus.NEEDS_REVIEW:
                raise IngestionFailure(
                    IngestionFailureCategory.EXTRACTION_NEEDS_REVIEW,
                    retryable=False,
                )
            if extraction.status is ExtractionStatus.FAILED:
                raise IngestionFailure(
                    IngestionFailureCategory.EXTRACTION_FAILED,
                    retryable=False,
                    document_error_category=(
                        extraction.error_category.value
                        if extraction.error_category is not None
                        else None
                    ),
                )

            if not evidence_is_indexable(extraction):
                raise IngestionFailure(
                    IngestionFailureCategory.EXTRACTION_NEEDS_REVIEW,
                    retryable=False,
                )

            outcome = await asyncio.to_thread(
                chunk_document,
                extraction,
                document_id=str(source.document_version_id),
                config=self._chunking_config,
            )
            if outcome.status is not ChunkingStatus.CHUNKED:
                category = (
                    IngestionFailureCategory.EMPTY_CONTENT
                    if outcome.reason is ChunkingReason.EMPTY_CONTENT
                    else IngestionFailureCategory.CHUNKING_FAILED
                )
                raise IngestionFailure(category, retryable=False)
            self._validate_chunks(source, outcome.chunks)
            return outcome.chunks
        except IngestionFailure:
            raise
        except OSError as exc:
            raise IngestionFailure(
                IngestionFailureCategory.TEMPORARY_STORAGE_UNAVAILABLE,
                retryable=True,
            ) from exc
        finally:
            try:
                await asyncio.to_thread(temporary.cleanup)
            except OSError as exc:
                raise IngestionFailure(
                    IngestionFailureCategory.TEMPORARY_STORAGE_UNAVAILABLE,
                    retryable=True,
                ) from exc

    def _validate_metadata(
        self,
        source: _SourceIdentity,
        metadata: ObjectMetadata,
    ) -> None:
        stored_checksum = metadata.metadata.get("sha256")
        if (
            metadata.size != source.file_size
            or (metadata.content_type is not None and metadata.content_type != source.content_type)
            or (stored_checksum is not None and stored_checksum != source.sha256_checksum)
        ):
            raise IngestionFailure(
                IngestionFailureCategory.SOURCE_IDENTITY_MISMATCH,
                retryable=False,
            )

    async def _download_verified(
        self,
        source: _SourceIdentity,
        destination: Path,
    ) -> None:
        digest = hashlib.sha256()
        total = 0
        output = await asyncio.to_thread(destination.open, "wb")
        try:
            try:
                async for payload in self._storage.stream_read(
                    source.object_storage_key,
                    chunk_size=self._download_chunk_size,
                ):
                    if not payload:
                        continue
                    total += len(payload)
                    if (
                        total > source.file_size
                        or total > self._extraction_limits.max_file_bytes
                    ):
                        raise IngestionFailure(
                            IngestionFailureCategory.SOURCE_IDENTITY_MISMATCH,
                            retryable=False,
                        )
                    digest.update(payload)
                    await asyncio.to_thread(output.write, payload)
            except ObjectStorageError as exc:
                raise _classified_storage_failure(exc) from exc
        finally:
            await asyncio.to_thread(output.close)
        if total != source.file_size or digest.hexdigest() != source.sha256_checksum:
            raise IngestionFailure(
                IngestionFailureCategory.SOURCE_IDENTITY_MISMATCH,
                retryable=False,
            )

    def _validate_chunks(
        self,
        source: _SourceIdentity,
        chunks: tuple[Chunk, ...],
    ) -> None:
        expected_document_id = str(source.document_version_id)
        expected_fingerprint = self._chunking_config.fingerprint()
        if not chunks:
            raise IngestionFailure(
                IngestionFailureCategory.EMPTY_CONTENT,
                retryable=False,
            )
        for ordinal, chunk in enumerate(chunks):
            if (
                chunk.ordinal != ordinal
                or chunk.document_id != expected_document_id
                or chunk.source_sha256 != source.sha256_checksum
                or f".{chunk.document_format.value}"
                != _SUFFIX_BY_CONTENT_TYPE.get(source.content_type)
                or chunk.strategy is not ChunkingStrategy.STRUCTURE_AWARE
                or chunk.config_fingerprint != expected_fingerprint
                or chunk.config_version != self._chunking_config.version
                or not chunk.text
                or not chunk.provenance
                or any(
                    not 0 <= span.source_start < span.source_end <= span.source_length
                    for span in chunk.provenance
                )
                or (
                    chunk.split_oversized_element
                    and any(
                        span.source.table_index is not None or span.source.sheet_index is not None
                        for span in chunk.provenance
                    )
                )
            ):
                raise IngestionFailure(
                    IngestionFailureCategory.CHUNKING_FAILED,
                    retryable=False,
                )

    async def _persist(
        self,
        source: _SourceIdentity,
        chunks: tuple[CanonicalChunkPayload, ...],
        *,
        worker_id: str,
        lease_token: UUID,
    ) -> IngestionResult:
        try:
            async with self._session_factory() as session, session.begin():
                try:
                    job, run = await _locked_job_and_run(session, source.processing_job_id)
                except ProcessingJobNotFoundError:
                    raise IngestionFailure(
                        IngestionFailureCategory.LEASE_OWNERSHIP_LOST,
                        retryable=False,
                    ) from None
                if run.id != source.processing_run_id:
                    raise IngestionFailure(
                        IngestionFailureCategory.LEASE_OWNERSHIP_LOST, retryable=False
                    )
                await _require_ingestion_ownership(
                    session, job, run, worker_id=worker_id, lease_token=lease_token
                )
                if (
                    run.document_version_id != source.document_version_id
                    or run.configuration_version != source.configuration_version
                    or run.configuration_fingerprint != source.configuration_fingerprint
                ):
                    raise IngestionFailure(
                        IngestionFailureCategory.CONFIGURATION_MISMATCH,
                        retryable=False,
                    )
                existing = tuple(
                    (
                        await session.scalars(
                            select(CanonicalChunk)
                            .where(CanonicalChunk.processing_run_id == source.processing_run_id)
                            .order_by(CanonicalChunk.ordinal)
                        )
                    ).all()
                )
                if existing:
                    if tuple(_model_data(item) for item in existing) != chunks:
                        raise IngestionFailure(
                            IngestionFailureCategory.PERSISTENCE_CONFLICT,
                            retryable=False,
                        )
                    status = IngestionResultStatus.ALREADY_PERSISTED
                else:
                    session.add_all(CanonicalChunk(**_data_mapping(item)) for item in chunks)
                    await session.flush()
                    status = IngestionResultStatus.PERSISTED
                # Also fence expiry during flush/comparison, including idempotent returns.
                await _require_ingestion_ownership(
                    session, job, run, worker_id=worker_id, lease_token=lease_token
                )
        except IngestionFailure:
            raise
        except IntegrityError as exc:
            raise IngestionFailure(
                IngestionFailureCategory.PERSISTENCE_CONFLICT,
                retryable=False,
            ) from exc
        except SQLAlchemyError as exc:
            raise IngestionFailure(
                IngestionFailureCategory.PERSISTENCE_UNAVAILABLE,
                retryable=True,
            ) from exc
        return IngestionResult(
            processing_run_id=source.processing_run_id,
            document_version_id=source.document_version_id,
            status=status,
            chunk_count=len(chunks),
        )


async def _require_ingestion_ownership(
    session: AsyncSession,
    job: ProcessingJob | None,
    run: ProcessingRun,
    *,
    worker_id: str,
    lease_token: UUID,
) -> None:
    if job is None:
        raise IngestionFailure(IngestionFailureCategory.LEASE_OWNERSHIP_LOST, retryable=False)
    try:
        _require_active_lease(
            job,
            worker_id=worker_id,
            lease_token=lease_token,
            now=await _processing_now(session),
        )
    except (LeaseOwnershipError, ValueError):
        # A stale caller must not fail/complete a job now owned by someone else.
        raise IngestionFailure(
            IngestionFailureCategory.LEASE_OWNERSHIP_LOST, retryable=False
        ) from None
    if run.status != ProcessingStatus.PROCESSING or run.stage != ProcessingStage.EXTRACTION:
        raise IngestionFailure(IngestionFailureCategory.PROCESSING_STATE_MISMATCH, retryable=False)


def canonical_chunk_uuid(processing_run_id: UUID, chunk_identity: str) -> UUID:
    """Derive a stable per-run UUID suitable for future vector indexing."""

    return uuid5(processing_run_id, chunk_identity)


def canonicalize_chunk(processing_run_id: UUID, chunk: Chunk) -> CanonicalChunkPayload:
    provenance = [
        {
            "unit_id": span.unit_id,
            "source": {
                field.name: (
                    list(getattr(span.source, field.name))
                    if isinstance(getattr(span.source, field.name), tuple)
                    else getattr(span.source, field.name)
                )
                for field in fields(span.source)
                if getattr(span.source, field.name) is not None
            },
            "source_start": span.source_start,
            "source_end": span.source_end,
            "source_length": span.source_length,
            "offset_basis": "rendered_source_unit",
        }
        for span in chunk.provenance
    ]
    return CanonicalChunkPayload(
        id=canonical_chunk_uuid(processing_run_id, chunk.chunk_id),
        processing_run_id=processing_run_id,
        ordinal=chunk.ordinal,
        chunk_identity=chunk.chunk_id,
        chunk_text=chunk.text,
        content_sha256=hashlib.sha256(chunk.text.encode()).hexdigest(),
        character_count=len(chunk.text),
        token_count=None,
        document_format=chunk.document_format.value,
        chunking_strategy=chunk.strategy.value,
        chunker_version=chunk.config_version,
        chunker_configuration_fingerprint=chunk.config_fingerprint,
        source_provenance=provenance,
        split_oversized_element=chunk.split_oversized_element,
    )


def _model_data(model: CanonicalChunk) -> CanonicalChunkPayload:
    return CanonicalChunkPayload(
        id=model.id,
        processing_run_id=model.processing_run_id,
        ordinal=model.ordinal,
        chunk_identity=model.chunk_identity,
        chunk_text=model.chunk_text,
        content_sha256=model.content_sha256,
        character_count=model.character_count,
        token_count=model.token_count,
        document_format=model.document_format,
        chunking_strategy=model.chunking_strategy,
        chunker_version=model.chunker_version,
        chunker_configuration_fingerprint=model.chunker_configuration_fingerprint,
        source_provenance=model.source_provenance,
        split_oversized_element=model.split_oversized_element,
    )


def _data_mapping(data: CanonicalChunkPayload) -> dict[str, object]:
    return {field.name: getattr(data, field.name) for field in fields(data)}


def _classified_storage_failure(error: ObjectStorageError) -> IngestionFailure:
    cause: BaseException | None = error
    while cause is not None:
        if isinstance(cause, ClientError):
            code = str(cause.response.get("Error", {}).get("Code", ""))
            if code in _MISSING_OBJECT_CODES:
                return IngestionFailure(
                    IngestionFailureCategory.SOURCE_OBJECT_MISSING,
                    retryable=False,
                )
        cause = cause.__cause__
    return IngestionFailure(
        IngestionFailureCategory.STORAGE_UNAVAILABLE,
        retryable=True,
    )
