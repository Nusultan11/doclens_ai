from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from doclens_ai.dense_baseline.embeddings import (
    MODEL_FILE_HASHES,
    MODEL_ID,
    MODEL_REVISION,
    DenseError,
    Embedder,
    EmbeddingConfig,
    validate_vectors,
)
from doclens_ai.models import (
    CanonicalChunk,
    Document,
    DocumentVersion,
    IndexRevision,
    IndexRevisionStatus,
    ProcessingJob,
    ProcessingStage,
    ProcessingStatus,
)
from doclens_ai.models.index_revision import chunk_set_fingerprint
from doclens_ai.services.processing import (
    InvalidProcessingTransition,
    LeaseOwnershipError,
    ProcessingJobNotFoundError,
    _locked_job_and_run,
    _processing_now,
    _require_active_lease,
    _require_current_ir_publication,
)
from doclens_ai.vector.qdrant import ProductionQdrant, VectorFailure, VectorPoint, point_id


class IndexingFailureCategory(StrEnum):
    OWNERSHIP_LOST = "index_ownership_lost"
    STATE_MISMATCH = "index_state_mismatch"
    CONFIGURATION_MISMATCH = "index_configuration_mismatch"
    DATA_INVALID = "index_data_invalid"
    SOURCE_LIMIT = "index_source_limit"
    EMBEDDING_UNAVAILABLE = "embedding_unavailable"
    EMBEDDING_INVALID = "embedding_invalid"
    VECTOR_UNAVAILABLE = "vector_unavailable"
    VECTOR_INVALID = "vector_invalid"
    DATABASE_UNAVAILABLE = "index_database_unavailable"


class IndexingFailure(RuntimeError):
    def __init__(self, category: IndexingFailureCategory, *, retryable: bool):
        super().__init__(category.value)
        self.category, self.retryable = category, retryable


def embedding_identity(provider: Embedder) -> tuple[dict[str, object], str]:
    try:
        metadata = json.loads(json.dumps(provider.metadata, allow_nan=False))
        config = metadata["configuration"]
        frozen = EmbeddingConfig(
            model_id=config["model_id"],
            revision=config["revision"],
            batch_size=config["batch_size"],
            max_tokens=config["max_tokens"],
            cpu_threads=config["cpu_threads"],
            device=config["device"],
        )
        if (
            config != frozen.to_dict()
            or provider.dimensions != 384
            or metadata["dimensions"] != 384
            or metadata["tokenizer_identity"] != MODEL_FILE_HASHES
            or metadata["tokenizer_class"] != "XLMRobertaTokenizerFast"
            or not isinstance(metadata["libraries"], dict)
            or not metadata["libraries"]
        ):
            raise ValueError("invalid embedding identity")
        if set(metadata) != {
            "configuration",
            "dimensions",
            "tokenizer_identity",
            "tokenizer_class",
            "libraries",
        }:
            raise ValueError("unexpected model metadata")
        if set(metadata["libraries"]) != {
            "torch",
            "transformers",
            "huggingface-hub",
            "tokenizers",
            "safetensors",
            "numpy",
        }:
            raise ValueError("incomplete library identity")
        if any(
            not isinstance(v, str) or not re.fullmatch(r"[a-zA-Z0-9.+_-]{1,64}", v)
            for v in metadata["libraries"].values()
        ):
            raise ValueError("invalid library identity")
        identity = {"schema_version": "production-e5-v1", "provider": metadata}
        fingerprint = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return identity, fingerprint
    except (KeyError, ValueError, TypeError, AttributeError):
        raise IndexingFailure(
            IndexingFailureCategory.CONFIGURATION_MISMATCH, retryable=False
        ) from None


def collection_name(fingerprint: str, prefix: str = "doclens_e5_v1") -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint) or not re.fullmatch(
        r"[a-z][a-z0-9_]{2,40}", prefix
    ):
        raise IndexingFailure(IndexingFailureCategory.CONFIGURATION_MISMATCH, retryable=False)
    return prefix + "_" + fingerprint


@dataclass(frozen=True, slots=True)
class Candidate:
    revision_id: UUID
    processing_run_id: UUID
    document_version_id: UUID
    document_id: UUID
    workspace_id: UUID
    chunk_set_fingerprint: str
    chunks: tuple[CanonicalChunk, ...]


@dataclass(frozen=True, slots=True)
class IndexingResult:
    revision_id: UUID
    indexed_chunks: int
    duration_ms: float
    embedding_ms: float


def candidate_points(candidate: Candidate, vectors, fingerprint: str) -> tuple[VectorPoint, ...]:
    try:
        validated = validate_vectors(vectors, count=len(candidate.chunks), dimensions=384)
    except (DenseError, TypeError, ValueError, AttributeError, OverflowError):
        raise IndexingFailure(IndexingFailureCategory.EMBEDDING_INVALID, retryable=False) from None
    return tuple(
        VectorPoint(
            point_id(candidate.revision_id, chunk.id, chunk.chunk_identity),
            vector,
            {
                "workspace_id": str(candidate.workspace_id),
                "document_id": str(candidate.document_id),
                "document_version_id": str(candidate.document_version_id),
                "processing_run_id": str(candidate.processing_run_id),
                "index_revision_id": str(candidate.revision_id),
                "chunk_id": str(chunk.id),
                "embedding_revision": MODEL_REVISION,
                "embedding_configuration_fingerprint": fingerprint,
            },
        )
        for chunk, vector in zip(candidate.chunks, validated, strict=True)
    )


class IndexingService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        provider: Embedder,
        vector_index: ProductionQdrant,
        *,
        max_chunks: int = 10000,
        max_characters: int = 20000000,
    ) -> None:
        if type(max_chunks) is not int or not 1 <= max_chunks <= 10000:
            raise ValueError("invalid bounded chunk limit")
        if type(max_characters) is not int or not 1 <= max_characters <= 20000000:
            raise ValueError("invalid bounded character limit")
        self.configuration, self.fingerprint = embedding_identity(provider)
        self._factory, self._provider, self._vector = session_factory, provider, vector_index
        if vector_index.dimensions != 384 or not vector_index.collection.endswith(
            "_" + self.fingerprint
        ):
            raise IndexingFailure(IndexingFailureCategory.CONFIGURATION_MISMATCH, retryable=False)
        self.max_chunks, self.max_characters = max_chunks, max_characters

    async def _owned(self, session, run_id, worker_id, lease_token):
        job_id = await session.scalar(
            select(ProcessingJob.id).where(ProcessingJob.processing_run_id == run_id)
        )
        if job_id is None:
            raise IndexingFailure(IndexingFailureCategory.OWNERSHIP_LOST, retryable=False)
        try:
            job, run = await _locked_job_and_run(session, job_id)
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=await _processing_now(session),
            )
        except (LeaseOwnershipError, ProcessingJobNotFoundError, ValueError):
            raise IndexingFailure(IndexingFailureCategory.OWNERSHIP_LOST, retryable=False) from None
        if run.status != ProcessingStatus.PROCESSING or run.stage not in {
            ProcessingStage.EMBEDDING,
            ProcessingStage.INDEXING,
        }:
            raise IndexingFailure(IndexingFailureCategory.STATE_MISMATCH, retryable=False)
        return job, run

    async def _prepare(self, run_id, worker_id, lease_token) -> Candidate:
        async with self._factory() as session, session.begin():
            job, run = await self._owned(session, run_id, worker_id, lease_token)
            count, characters = (
                await session.execute(
                    select(
                        func.count(CanonicalChunk.id),
                        func.coalesce(func.sum(CanonicalChunk.character_count), 0),
                    ).where(CanonicalChunk.processing_run_id == run_id)
                )
            ).one()
            if count == 0:
                raise IndexingFailure(IndexingFailureCategory.DATA_INVALID, retryable=False)
            if count > self.max_chunks or characters > self.max_characters:
                raise IndexingFailure(IndexingFailureCategory.SOURCE_LIMIT, retryable=False)
            chunks = tuple(
                await session.scalars(
                    select(CanonicalChunk)
                    .where(CanonicalChunk.processing_run_id == run_id)
                    .order_by(CanonicalChunk.ordinal)
                )
            )
            if [chunk.ordinal for chunk in chunks] != list(range(count)):
                raise IndexingFailure(IndexingFailureCategory.DATA_INVALID, retryable=False)
            if any(
                hashlib.sha256(chunk.chunk_text.encode()).hexdigest() != chunk.content_sha256
                for chunk in chunks
            ):
                raise IndexingFailure(IndexingFailureCategory.DATA_INVALID, retryable=False)
            try:
                _require_current_ir_publication(run, (chunk.chunker_version for chunk in chunks))
            except InvalidProcessingTransition:
                raise IndexingFailure(
                    IndexingFailureCategory.CONFIGURATION_MISMATCH, retryable=False
                ) from None
            version, document = (
                await session.execute(
                    select(DocumentVersion, Document)
                    .join(Document, Document.id == DocumentVersion.document_id)
                    .where(DocumentVersion.id == run.document_version_id)
                )
            ).one()
            revision_id = uuid5(run_id, "index:" + str(lease_token))
            digest = chunk_set_fingerprint(chunks)
            revision = await session.get(IndexRevision, revision_id)
            if revision is None:
                session.add(
                    IndexRevision(
                        id=revision_id,
                        processing_run_id=run_id,
                        document_version_id=version.id,
                        document_id=document.id,
                        workspace_id=document.workspace_id,
                        document_version_number=version.version_number,
                        lease_token=lease_token,
                        embedding_model_id=MODEL_ID,
                        embedding_model_revision=MODEL_REVISION,
                        embedding_configuration=self.configuration,
                        embedding_configuration_fingerprint=self.fingerprint,
                        canonical_chunk_set_fingerprint=digest,
                        vector_dimension=384,
                        collection_name=self._vector.collection,
                        status=IndexRevisionStatus.CANDIDATE,
                        expected_point_count=count,
                        verified_point_count=0,
                    )
                )
            elif (
                revision.embedding_configuration != self.configuration
                or revision.embedding_configuration_fingerprint != self.fingerprint
                or revision.collection_name != self._vector.collection
                or revision.canonical_chunk_set_fingerprint != digest
                or revision.status
                not in {IndexRevisionStatus.CANDIDATE, IndexRevisionStatus.VERIFIED}
            ):
                raise IndexingFailure(
                    IndexingFailureCategory.CONFIGURATION_MISMATCH, retryable=False
                )
            await session.flush()
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=await _processing_now(session),
            )
            return Candidate(
                revision_id, run_id, version.id, document.id, document.workspace_id, digest, chunks
            )

    async def _checkpoint(self, candidate, worker_id, lease_token, *, verified_count=None):
        async with self._factory() as session, session.begin():
            job, run = await self._owned(
                session, candidate.processing_run_id, worker_id, lease_token
            )
            revision = await session.scalar(
                select(IndexRevision)
                .where(IndexRevision.id == candidate.revision_id)
                .with_for_update()
            )
            if (
                revision is None
                or revision.lease_token != lease_token
                or revision.embedding_configuration_fingerprint != self.fingerprint
                or revision.collection_name != self._vector.collection
                or revision.canonical_chunk_set_fingerprint != candidate.chunk_set_fingerprint
                or revision.status
                not in {IndexRevisionStatus.CANDIDATE, IndexRevisionStatus.VERIFIED}
            ):
                raise IndexingFailure(
                    IndexingFailureCategory.CONFIGURATION_MISMATCH, retryable=False
                )
            run.stage = ProcessingStage.INDEXING
            if verified_count is not None:
                if verified_count != revision.expected_point_count:
                    raise IndexingFailure(IndexingFailureCategory.VECTOR_INVALID, retryable=False)
                if revision.status == IndexRevisionStatus.CANDIDATE:
                    verified_at = await _processing_now(session)
                    revision.status = IndexRevisionStatus.VERIFIED
                    revision.verified_point_count = verified_count
                    revision.verified_at = verified_at
            await session.flush()
            _require_active_lease(
                job,
                worker_id=worker_id,
                lease_token=lease_token,
                now=await _processing_now(session),
            )

    async def index(self, run_id: UUID, *, worker_id: str, lease_token: UUID) -> IndexingResult:
        started = time.perf_counter()
        try:
            candidate = await self._prepare(run_id, worker_id, lease_token)
            # Immutable snapshots leave all database locks before inference and network operations.
            embedding_started = time.perf_counter()
            try:
                batch = await asyncio.to_thread(
                    self._provider.encode,
                    [chunk.chunk_text for chunk in candidate.chunks],
                    kind="passage",
                )
            except Exception:
                raise IndexingFailure(
                    IndexingFailureCategory.EMBEDDING_UNAVAILABLE, retryable=True
                ) from None
            try:
                points = candidate_points(candidate, batch.vectors, self.fingerprint)
            except (AttributeError, TypeError):
                raise IndexingFailure(
                    IndexingFailureCategory.EMBEDDING_INVALID, retryable=False
                ) from None
            embedding_ms = (time.perf_counter() - embedding_started) * 1000
            await self._checkpoint(candidate, worker_id, lease_token)
            await self._vector.ensure_collection()
            await self._vector.upsert(candidate.revision_id, points)
            count = await self._vector.verify(candidate.revision_id, points)
            await self._checkpoint(candidate, worker_id, lease_token, verified_count=count)
            return IndexingResult(
                candidate.revision_id, count, (time.perf_counter() - started) * 1000, embedding_ms
            )
        except VectorFailure as error:
            category = (
                IndexingFailureCategory.VECTOR_UNAVAILABLE
                if error.retryable
                else IndexingFailureCategory.VECTOR_INVALID
            )
            raise IndexingFailure(category, retryable=error.retryable) from None
        except SQLAlchemyError:
            raise IndexingFailure(
                IndexingFailureCategory.DATABASE_UNAVAILABLE, retryable=True
            ) from None
        except (LeaseOwnershipError, ProcessingJobNotFoundError):
            raise IndexingFailure(IndexingFailureCategory.OWNERSHIP_LOST, retryable=False) from None
