"""Bounded dense retrieval with authoritative, freshly checked PostgreSQL scope."""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from doclens_ai.models import (
    CanonicalChunk,
    Document,
    DocumentVersion,
    IndexRevision,
    ProcessingRun,
    WorkspaceMembership,
)

if TYPE_CHECKING:
    from doclens_ai.vector.qdrant import ProductionQdrant, SearchHit


class SearchUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("search service is unavailable")


class SearchForbidden(RuntimeError):
    def __init__(self):
        super().__init__("workspace access denied")


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: UUID
    query: StrictStr = Field(min_length=1, max_length=2000)
    document_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=50)
    top_k: int = Field(default=20, ge=1, le=20, strict=True)
    limit: int = Field(default=10, ge=1, le=20, strict=True)

    @field_validator("query")
    @classmethod
    def valid_query(cls, value):
        if not value.strip() or any(ord(c) < 32 and c not in "\n\t\r" for c in value):
            raise ValueError("query must be a nonblank bounded text")
        return value.strip()

    @model_validator(mode="after")
    def valid_limits(self):
        if self.limit > self.top_k:
            raise ValueError("result limit must not exceed candidate limit")
        if self.document_ids is not None and len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("duplicate document filters are not allowed")
        return self


class SourceLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    page_number: int | None = Field(default=None, ge=1)
    block_index: int | None = Field(default=None, ge=0)
    sheet_index: int | None = Field(default=None, ge=0)
    sheet_name: str | None = Field(default=None, min_length=1, max_length=255)
    cell_coordinate: str | None = Field(
        default=None, pattern=r"^[A-Z]{1,3}[1-9][0-9]{0,6}(?::[A-Z]{1,3}[1-9][0-9]{0,6})?$"
    )
    table_index: int | None = Field(default=None, ge=0)
    row_index: int | None = Field(default=None, ge=0)
    column_index: int | None = Field(default=None, ge=0)


class SourceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: SourceLocation
    source_start: int = Field(ge=0)
    source_end: int = Field(gt=0)
    source_length: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_range(self):
        if not self.source_start < self.source_end <= self.source_length:
            raise ValueError("invalid source range")
        return self


class SourceLocator(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_format: Literal["pdf", "docx", "xlsx"]
    spans: list[SourceSpan] = Field(min_length=1, max_length=10000)


def source_locator(chunk: CanonicalChunk) -> SourceLocator:
    spans = [
        SourceSpan.model_validate(
            {k: item[k] for k in ("source", "source_start", "source_end", "source_length")}
        )
        for item in chunk.source_provenance
    ]
    for span in spans:
        location = span.source
        if (
            (chunk.document_format == "pdf" and location.page_number is None)
            or (chunk.document_format == "docx" and location.block_index is None)
            or (
                chunk.document_format == "xlsx"
                and (
                    location.sheet_index is None
                    or (location.cell_coordinate is None and location.table_index is None)
                )
            )
        ):
            raise ValueError("missing source locator")
    return SourceLocator(document_format=chunk.document_format, spans=spans)


@dataclass(frozen=True, slots=True)
class VerifiedResult:
    chunk_id: UUID
    document_id: UUID
    document_version_id: UUID
    index_revision_id: UUID
    workspace_id: UUID
    score: float
    text: str
    locator: SourceLocator
    # Internal evaluation only; public response projects explicitly permitted fields.
    source_sha256: str


@dataclass(frozen=True, slots=True)
class SearchResult:
    results: tuple[VerifiedResult, ...]
    embedding_ms: float
    qdrant_ms: float
    end_to_end_ms: float
    rejected_candidates: int


class QueryEncoder:
    """One loaded provider, bounded inference; cancellation drains its CPU thread."""

    def __init__(self, provider, *, concurrency=1, queue_timeout_seconds=1):
        from doclens_ai.services.indexing import embedding_identity

        if type(concurrency) is not int or not 1 <= concurrency <= 2:
            raise ValueError("invalid inference concurrency")
        if not 0 < queue_timeout_seconds <= 10:
            raise ValueError("invalid inference queue timeout")
        self.configuration, self.fingerprint = embedding_identity(provider)
        self.provider = provider
        self._semaphore = asyncio.Semaphore(concurrency)
        self._queue_timeout = queue_timeout_seconds

    async def encode(self, query):
        from doclens_ai.dense_baseline.embeddings import validate_vectors

        try:
            async with asyncio.timeout(self._queue_timeout):
                await self._semaphore.acquire()
        except TimeoutError:
            raise SearchUnavailable() from None
        try:
            operation = asyncio.create_task(
                asyncio.to_thread(self.provider.encode, [query], kind="query")
            )
            try:
                batch = await asyncio.shield(operation)
            except asyncio.CancelledError:
                # Repeated cancellation must not release capacity while inference still runs.
                while not operation.done():
                    try:
                        await asyncio.shield(operation)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if not operation.cancelled():
                    operation.exception()
                raise
            return validate_vectors(batch.vectors, count=1, dimensions=384)[0]
        except Exception:
            raise SearchUnavailable() from None
        finally:
            self._semaphore.release()


class RetrievalService:
    def __init__(
        self,
        factory,
        encoder: QueryEncoder,
        vector: ProductionQdrant,
        *,
        max_active_revisions=128,
        db_timeout_seconds=5,
    ):
        if type(max_active_revisions) is not int or not 1 <= max_active_revisions <= 512:
            raise ValueError("invalid active revision budget")
        if not 0 < db_timeout_seconds <= 30:
            raise ValueError("invalid database timeout")
        if vector.dimensions != 384 or not vector.collection.endswith("_" + encoder.fingerprint):
            raise SearchUnavailable()
        self.factory, self.encoder, self.vector = factory, encoder, vector
        self.max_active_revisions, self.db_timeout = max_active_revisions, db_timeout_seconds

    async def _membership(self, session, user_id, workspace_id):
        role = await session.scalar(
            select(WorkspaceMembership.role).where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace_id,
            )
        )
        if role not in {"owner", "editor", "viewer"}:
            raise SearchForbidden()

    def _compatible(self, revision):
        return (
            revision.embedding_configuration == self.encoder.configuration
            and revision.embedding_configuration_fingerprint == self.encoder.fingerprint
            and revision.vector_dimension == 384
            and revision.collection_name == self.vector.collection
            and revision.embedding_model_revision
            == self.encoder.configuration["provider"]["configuration"]["revision"]
            and revision.embedding_model_id
            == self.encoder.configuration["provider"]["configuration"]["model_id"]
        )

    async def _scope(self, user_id, request):
        async with self.factory() as session:
            await self._membership(session, user_id, request.workspace_id)
            statement = (
                select(IndexRevision, ProcessingRun, DocumentVersion, Document)
                .join(ProcessingRun, ProcessingRun.id == IndexRevision.processing_run_id)
                .join(DocumentVersion, DocumentVersion.id == IndexRevision.document_version_id)
                .join(Document, Document.id == IndexRevision.document_id)
                .where(
                    IndexRevision.status == "active",
                    IndexRevision.workspace_id == request.workspace_id,
                    Document.workspace_id == request.workspace_id,
                )
            )
            if request.document_ids is not None:
                statement = statement.where(Document.id.in_(request.document_ids))
            rows = (
                await session.execute(
                    statement.order_by(IndexRevision.id).limit(self.max_active_revisions + 1)
                )
            ).all()
            if len(rows) > self.max_active_revisions:
                raise SearchUnavailable()
            for revision, run, version, document in rows:
                if not (
                    self._compatible(revision)
                    and run.status == "completed"
                    and run.stage == "indexing"
                    and run.document_version_id == version.id
                    and version.document_id == document.id
                    and version.version_number == revision.document_version_number
                ):
                    raise SearchUnavailable()
            return tuple((row[0].id, row[3].id) for row in rows)

    async def _resolve(self, user_id, request, revision_ids, hits: tuple[SearchHit, ...]):
        from doclens_ai.vector.qdrant import point_id

        async with self.factory() as session:
            await self._membership(session, user_id, request.workspace_id)
            if not hits:
                return ()
            chunk_ids = [UUID(hit.payload["chunk_id"]) for hit in hits]
            statement = (
                select(CanonicalChunk, IndexRevision, DocumentVersion, Document)
                .join(ProcessingRun, ProcessingRun.id == CanonicalChunk.processing_run_id)
                .join(IndexRevision, IndexRevision.processing_run_id == ProcessingRun.id)
                .join(DocumentVersion, DocumentVersion.id == ProcessingRun.document_version_id)
                .join(Document, Document.id == DocumentVersion.document_id)
                .join(
                    WorkspaceMembership, WorkspaceMembership.workspace_id == Document.workspace_id
                )
                .where(
                    CanonicalChunk.id.in_(chunk_ids),
                    IndexRevision.id.in_(revision_ids),
                    IndexRevision.status == "active",
                    ProcessingRun.status == "completed",
                    ProcessingRun.stage == "indexing",
                    IndexRevision.document_version_id == DocumentVersion.id,
                    IndexRevision.document_id == Document.id,
                    IndexRevision.workspace_id == Document.workspace_id,
                    Document.workspace_id == request.workspace_id,
                    WorkspaceMembership.user_id == user_id,
                    WorkspaceMembership.role.in_(["owner", "editor", "viewer"]),
                )
            )
            if request.document_ids is not None:
                statement = statement.where(Document.id.in_(request.document_ids))
            rows = {
                chunk.id: (chunk, revision, version, document)
                for chunk, revision, version, document in (await session.execute(statement)).all()
            }
            results, seen = [], set()
            for hit in hits:
                row = rows.get(UUID(hit.payload["chunk_id"]))
                if row is None:
                    continue
                chunk, revision, version, document = row
                expected = {
                    "workspace_id": str(document.workspace_id),
                    "document_id": str(document.id),
                    "document_version_id": str(version.id),
                    "processing_run_id": str(chunk.processing_run_id),
                    "index_revision_id": str(revision.id),
                    "chunk_id": str(chunk.id),
                    "embedding_revision": revision.embedding_model_revision,
                    "embedding_configuration_fingerprint": (
                        revision.embedding_configuration_fingerprint
                    ),
                }
                if (
                    hit.payload != expected
                    or not self._compatible(revision)
                    or hit.id != point_id(revision.id, chunk.id, chunk.chunk_identity)
                    or chunk.id in seen
                    or hashlib.sha256(chunk.chunk_text.encode()).hexdigest() != chunk.content_sha256
                ):
                    continue
                try:
                    locator = source_locator(chunk)
                except (ValueError, TypeError, KeyError):
                    continue
                seen.add(chunk.id)
                results.append(
                    VerifiedResult(
                        chunk.id,
                        document.id,
                        version.id,
                        revision.id,
                        document.workspace_id,
                        hit.score,
                        chunk.chunk_text,
                        locator,
                        version.sha256_checksum,
                    )
                )
            return tuple(results)

    async def search(self, *, user_id: UUID, request: SearchInput) -> SearchResult:
        from doclens_ai.vector.qdrant import VectorFailure

        started = time.perf_counter()
        try:
            async with asyncio.timeout(self.db_timeout):
                scope = await self._scope(user_id, request)
            revisions = tuple(revision_id for revision_id, _ in scope)
            # Client IDs are selectors only; send the authorized PostgreSQL intersection.
            documents = tuple(sorted({document_id for _, document_id in scope}))
            if not revisions:
                async with asyncio.timeout(self.db_timeout):
                    await self._resolve(user_id, request, revisions, ())
                return SearchResult((), 0, 0, (time.perf_counter() - started) * 1000, 0)
            before = time.perf_counter()
            vector = await self.encoder.encode(request.query)
            embedding_ms = (time.perf_counter() - before) * 1000
            before = time.perf_counter()
            hits = await self.vector.search(
                vector,
                workspace_id=request.workspace_id,
                revision_ids=revisions,
                document_ids=documents if request.document_ids is not None else (),
                limit=request.top_k,
            )
            qdrant_ms = (time.perf_counter() - before) * 1000
            async with asyncio.timeout(self.db_timeout):
                verified = await self._resolve(user_id, request, revisions, hits)
            accepted = {result.chunk_id for result in verified}
            fresh_hits = tuple(hit for hit in hits if UUID(hit.payload["chunk_id"]) in accepted)
            # A new transaction re-reads ACL and ACTIVE state after candidate validation.
            async with asyncio.timeout(self.db_timeout):
                fresh = await self._resolve(user_id, request, revisions, fresh_hits)
            return SearchResult(
                fresh[: request.limit],
                embedding_ms,
                qdrant_ms,
                (time.perf_counter() - started) * 1000,
                len(hits) - len(fresh),
            )
        except (SQLAlchemyError, VectorFailure, OSError, TimeoutError):
            raise SearchUnavailable() from None

    async def revalidate(
        self, *, user_id: UUID, workspace_id: UUID, evidence: tuple[VerifiedResult, ...]
    ) -> bool:
        """Fresh PG-only check of exact previously verified evidence; no network/row locks.

        False invalidates the WHOLE answer. Revoked membership still raises SearchForbidden.
        A revocation after this check but before delivery remains outside transaction atomicity.
        """
        try:
            async with asyncio.timeout(self.db_timeout):
                async with self.factory() as session:
                    await self._membership(session, user_id, workspace_id)
                    if not evidence:
                        return True
                    if (
                        len(evidence) > 20
                        or len({item.chunk_id for item in evidence}) != len(evidence)
                        or any(item.workspace_id != workspace_id for item in evidence)
                    ):
                        return False
                    statement = (
                        select(CanonicalChunk, IndexRevision, DocumentVersion, Document)
                        .join(ProcessingRun, ProcessingRun.id == CanonicalChunk.processing_run_id)
                        .join(IndexRevision, IndexRevision.processing_run_id == ProcessingRun.id)
                        .join(
                            DocumentVersion, DocumentVersion.id == ProcessingRun.document_version_id
                        )
                        .join(Document, Document.id == DocumentVersion.document_id)
                        .join(
                            WorkspaceMembership,
                            WorkspaceMembership.workspace_id == Document.workspace_id,
                        )
                        .where(
                            CanonicalChunk.id.in_([item.chunk_id for item in evidence]),
                            IndexRevision.id.in_([item.index_revision_id for item in evidence]),
                            IndexRevision.status == "active",
                            ProcessingRun.status == "completed",
                            ProcessingRun.stage == "indexing",
                            IndexRevision.document_version_id == DocumentVersion.id,
                            IndexRevision.document_id == Document.id,
                            IndexRevision.workspace_id == Document.workspace_id,
                            Document.workspace_id == workspace_id,
                            WorkspaceMembership.user_id == user_id,
                            WorkspaceMembership.role.in_(["owner", "editor", "viewer"]),
                        )
                    )
                    rows = {
                        (chunk.id, revision.id): (chunk, revision, version, document)
                        for chunk, revision, version, document in (
                            await session.execute(statement)
                        ).all()
                    }
                    for item in evidence:
                        row = rows.get((item.chunk_id, item.index_revision_id))
                        if row is None:
                            return False
                        chunk, revision, version, document = row
                        if not (
                            self._compatible(revision)
                            and revision.document_version_number == version.version_number
                            and document.id == item.document_id
                            and version.id == item.document_version_id
                            and version.sha256_checksum == item.source_sha256
                            and chunk.chunk_text == item.text
                            and chunk.content_sha256
                            == hashlib.sha256(item.text.encode()).hexdigest()
                        ):
                            return False
                        try:
                            if source_locator(chunk) != item.locator:
                                return False
                        except (ValueError, KeyError, TypeError):
                            return False
                    return True
        except (SQLAlchemyError, OSError, TimeoutError):
            raise SearchUnavailable() from None

    async def aclose(self):
        await self.vector.close()
