from __future__ import annotations

import asyncio
import hashlib
import io
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

import pytest
from botocore.exceptions import ClientError
from docx import Document as DocxDocument
from openpyxl import Workbook
from openpyxl.worksheet.table import Table as XlsxTable
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import doclens_ai.services.ingestion as ingestion_module
from doclens_ai.models import (
    CanonicalChunk,
    Document,
    DocumentVersion,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingOperationKind,
    ProcessingRun,
    ProcessingStage,
    ProcessingStatus,
    Workspace,
)
from doclens_ai.services.ingestion import (
    IngestionFailure,
    IngestionFailureCategory,
    IngestionResultStatus,
    IngestionService,
    canonical_chunk_uuid,
)
from doclens_ai.services.processing import (
    PROCESSING_CONFIGURATION_VERSION,
    default_processing_configuration_fingerprint,
)
from doclens_ai.services.upload import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    UploadService,
)
from doclens_ai.storage.config import StorageSettings
from doclens_ai.storage.s3 import ObjectMetadata, ObjectStorageError, S3ObjectStorage


@dataclass
class _StoredObject:
    content: bytes
    content_type: str
    checksum: str


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, _StoredObject] = {}
        self.available = True

    def _require(self, key: str) -> _StoredObject:
        if not self.available:
            raise ObjectStorageError("storage unavailable")
        try:
            return self.objects[key]
        except KeyError:
            try:
                raise ClientError(
                    {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
                    "GetObject",
                )
            except ClientError as exc:
                raise ObjectStorageError("object unavailable") from exc

    async def put_stream(
        self,
        key: str,
        stream: io.BytesIO,
        *,
        content_type: str,
        sha256_checksum: str,
    ) -> None:
        if not self.available:
            raise ObjectStorageError("storage unavailable")
        stream.seek(0)
        self.objects[key] = _StoredObject(
            content=stream.read(),
            content_type=content_type,
            checksum=sha256_checksum,
        )

    async def inspect(self, key: str) -> ObjectMetadata:
        stored = self._require(key)
        return ObjectMetadata(
            size=len(stored.content),
            content_type=stored.content_type,
            metadata={"sha256": stored.checksum},
        )

    async def sha256(self, key: str, *, chunk_size: int = 1024 * 1024) -> str:
        return hashlib.sha256(self._require(key).content).hexdigest()

    async def stream_read(
        self,
        key: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> AsyncIterator[bytes]:
        content = self._require(key).content
        for offset in range(0, len(content), chunk_size):
            yield content[offset : offset + chunk_size]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)


def _pdf_bytes(page_texts: list[str]) -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)  # noqa: SLF001
    for page_text in page_texts:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
        )
        escaped = page_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)  # noqa: SLF001
    writer.write(output)
    return output.getvalue()


def _docx_bytes(*, empty: bool = False) -> bytes:
    output = io.BytesIO()
    document = DocxDocument()
    if not empty:
        document.add_paragraph("A production document paragraph with useful content.")
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "left value"
        table.cell(0, 1).text = "right value"
    document.save(output)
    return output.getvalue()


def _xlsx_bytes() -> bytes:
    output = io.BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Metrics"
    sheet.append(["name", "value"])
    sheet.append(["alpha", 7])
    sheet.add_table(XlsxTable(displayName="MetricsTable", ref="A1:B2"))
    workbook.save(output)
    return output.getvalue()


async def _create_document(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID]:
    async with session_factory() as session, session.begin():
        workspace = Workspace(name=f"Canonical chunks {uuid4()}")
        document = Document(workspace=workspace)
        session.add(document)
        await session.flush()
        return workspace.id, document.id


async def _upload(
    session_factory: async_sessionmaker[AsyncSession],
    storage: MemoryStorage | S3ObjectStorage,
    *,
    workspace_id: UUID,
    document_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[UUID, UUID, str]:
    result = await UploadService(
        session_factory,
        storage,
        max_upload_size_bytes=50 * 1024 * 1024,
    ).upload_and_confirm(
        workspace_id=workspace_id,
        document_id=document_id,
        idempotency_key=str(uuid4()),
        original_filename=filename,
        content_type=content_type,
        stream=io.BytesIO(content),
    )
    async with session_factory() as session:
        job = await session.get(ProcessingJob, result.processing_job_id)
        assert job is not None
        version = await session.get(DocumentVersion, result.document_version_id)
        assert version is not None
        return version.id, job.processing_run_id, version.object_storage_key


@pytest.mark.integration
def test_pdf_docx_xlsx_persistence_idempotency_and_reprocessing_isolation(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(migrated_database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        storage = MemoryStorage()
        workspace_id, document_id = await _create_document(session_factory)
        sources = (
            (
                "source.pdf",
                PDF_CONTENT_TYPE,
                _pdf_bytes(["PDF page content long enough for production extraction."]),
            ),
            ("source.docx", DOCX_CONTENT_TYPE, _docx_bytes()),
            ("source.xlsx", XLSX_CONTENT_TYPE, _xlsx_bytes()),
        )
        uploaded = [
            await _upload(
                session_factory,
                storage,
                workspace_id=workspace_id,
                document_id=document_id,
                filename=filename,
                content_type=content_type,
                content=content,
            )
            for filename, content_type, content in sources
        ]
        service = IngestionService(session_factory, storage)
        try:
            competing = await asyncio.gather(
                service.ingest(uploaded[0][1]),
                service.ingest(uploaded[0][1]),
            )
            assert {item.status for item in competing} == {
                IngestionResultStatus.PERSISTED,
                IngestionResultStatus.ALREADY_PERSISTED,
            }
            for _, run_id, _ in uploaded[1:]:
                assert (await service.ingest(run_id)).status is IngestionResultStatus.PERSISTED

            async with session_factory() as session:
                chunks_by_run: dict[UUID, tuple[CanonicalChunk, ...]] = {}
                for version_id, run_id, _ in uploaded:
                    chunks = tuple(
                        (
                            await session.scalars(
                                select(CanonicalChunk)
                                .where(CanonicalChunk.processing_run_id == run_id)
                                .order_by(CanonicalChunk.ordinal)
                            )
                        ).all()
                    )
                    assert chunks
                    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
                    assert all(
                        chunk.id == canonical_chunk_uuid(run_id, chunk.chunk_identity)
                        and chunk.content_sha256
                        == hashlib.sha256(chunk.chunk_text.encode()).hexdigest()
                        and chunk.character_count == len(chunk.chunk_text)
                        and chunk.token_count is None
                        for chunk in chunks
                    )
                    chunks_by_run[run_id] = chunks
                    resolved_workspace = await session.scalar(
                        select(Document.workspace_id)
                        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
                        .join(
                            ProcessingRun,
                            ProcessingRun.document_version_id == DocumentVersion.id,
                        )
                        .where(ProcessingRun.id == run_id)
                    )
                    assert resolved_workspace == workspace_id
                    assert version_id == (
                        await session.get(ProcessingRun, run_id)
                    ).document_version_id

                pdf_chunks = chunks_by_run[uploaded[0][1]]
                assert {
                    span["source"]["page_number"]
                    for chunk in pdf_chunks
                    for span in chunk.source_provenance
                } == {1}
                docx_chunks = chunks_by_run[uploaded[1][1]]
                assert any(
                    span["source"].get("table_index") == 0
                    for chunk in docx_chunks
                    for span in chunk.source_provenance
                )
                xlsx_chunks = chunks_by_run[uploaded[2][1]]
                assert all(
                    span["source"]["sheet_index"] == 0
                    for chunk in xlsx_chunks
                    for span in chunk.source_provenance
                )
                assert any(
                    span["source"].get("cell_coordinate") == "B2"
                    for chunk in xlsx_chunks
                    for span in chunk.source_provenance
                )

                original_run = await session.get(ProcessingRun, uploaded[0][1])
                original_job = await session.scalar(
                    select(ProcessingJob).where(
                        ProcessingJob.processing_run_id == uploaded[0][1]
                    )
                )
                assert original_run is not None
                assert original_job is not None
                assert original_run.status == ProcessingStatus.QUEUED
                assert original_run.stage == ProcessingStage.EXTRACTION
                assert original_job.status == ProcessingJobStatus.QUEUED

            reprocess_run_id = uuid4()
            async with session_factory() as session, session.begin():
                session.add(
                    ProcessingRun(
                        id=reprocess_run_id,
                        document_version_id=uploaded[0][0],
                        operation_id=uuid4(),
                        operation_kind=ProcessingOperationKind.REPROCESS,
                        configuration_version=PROCESSING_CONFIGURATION_VERSION,
                        configuration_fingerprint=default_processing_configuration_fingerprint(),
                        stage=ProcessingStage.EXTRACTION,
                        status=ProcessingStatus.QUEUED,
                    )
                )
            assert (
                await service.ingest(reprocess_run_id)
            ).status is IngestionResultStatus.PERSISTED
            async with session_factory() as session:
                original = tuple(
                    (
                        await session.scalars(
                            select(CanonicalChunk)
                            .where(CanonicalChunk.processing_run_id == uploaded[0][1])
                            .order_by(CanonicalChunk.ordinal)
                        )
                    ).all()
                )
                reprocessed = tuple(
                    (
                        await session.scalars(
                            select(CanonicalChunk)
                            .where(CanonicalChunk.processing_run_id == reprocess_run_id)
                            .order_by(CanonicalChunk.ordinal)
                        )
                    ).all()
                )
                assert [item.chunk_identity for item in original] == [
                    item.chunk_identity for item in reprocessed
                ]
                assert {item.id for item in original}.isdisjoint(
                    {item.id for item in reprocessed}
                )
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_ingestion_failure_gates_publish_no_chunks(migrated_database_url: str) -> None:
    async def exercise() -> None:
        engine = create_async_engine(migrated_database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        storage = MemoryStorage()
        workspace_id, document_id = await _create_document(session_factory)
        try:
            _, missing_run, missing_key = await _upload(
                session_factory,
                storage,
                workspace_id=workspace_id,
                document_id=document_id,
                filename="missing.pdf",
                content_type=PDF_CONTENT_TYPE,
                content=_pdf_bytes(["A complete source document for the missing-object test."]),
            )
            await storage.delete(missing_key)
            with pytest.raises(IngestionFailure) as missing:
                await IngestionService(session_factory, storage).ingest(missing_run)
            assert (missing.value.category, missing.value.retryable) == (
                IngestionFailureCategory.SOURCE_OBJECT_MISSING,
                False,
            )

            _, mismatch_run, mismatch_key = await _upload(
                session_factory,
                storage,
                workspace_id=workspace_id,
                document_id=document_id,
                filename="mismatch.pdf",
                content_type=PDF_CONTENT_TYPE,
                content=_pdf_bytes(["Original source identity with sufficient extracted text."]),
            )
            stored = storage.objects[mismatch_key]
            storage.objects[mismatch_key] = replace(
                stored,
                content=stored.content[:-1] + bytes([stored.content[-1] ^ 1]),
            )
            with pytest.raises(IngestionFailure) as mismatch:
                await IngestionService(session_factory, storage).ingest(mismatch_run)
            assert mismatch.value.category is IngestionFailureCategory.SOURCE_IDENTITY_MISMATCH

            _, unavailable_run, _ = await _upload(
                session_factory,
                storage,
                workspace_id=workspace_id,
                document_id=document_id,
                filename="unavailable.pdf",
                content_type=PDF_CONTENT_TYPE,
                content=_pdf_bytes(["Infrastructure failure source with sufficient text."]),
            )
            storage.available = False
            with pytest.raises(IngestionFailure) as unavailable:
                await IngestionService(session_factory, storage).ingest(unavailable_run)
            assert (unavailable.value.category, unavailable.value.retryable) == (
                IngestionFailureCategory.STORAGE_UNAVAILABLE,
                True,
            )
            storage.available = True

            _, corrupt_run, _ = await _upload(
                session_factory,
                storage,
                workspace_id=workspace_id,
                document_id=document_id,
                filename="corrupt.pdf",
                content_type=PDF_CONTENT_TYPE,
                content=b"%PDF-1.7\nnot a valid pdf\n%%EOF\n",
            )
            with pytest.raises(IngestionFailure) as corrupt:
                await IngestionService(session_factory, storage).ingest(corrupt_run)
            assert corrupt.value.category is IngestionFailureCategory.EXTRACTION_FAILED
            assert corrupt.value.document_error_category == "corrupt_document"

            _, empty_run, _ = await _upload(
                session_factory,
                storage,
                workspace_id=workspace_id,
                document_id=document_id,
                filename="empty.docx",
                content_type=DOCX_CONTENT_TYPE,
                content=_docx_bytes(empty=True),
            )
            with pytest.raises(IngestionFailure) as empty:
                await IngestionService(session_factory, storage).ingest(empty_run)
            assert empty.value.category is IngestionFailureCategory.EMPTY_CONTENT

            _, review_run, _ = await _upload(
                session_factory,
                storage,
                workspace_id=workspace_id,
                document_id=document_id,
                filename="review.pdf",
                content_type=PDF_CONTENT_TYPE,
                content=_pdf_bytes(["short"]),
            )
            with pytest.raises(IngestionFailure) as review:
                await IngestionService(session_factory, storage).ingest(review_run)
            assert review.value.category is IngestionFailureCategory.EXTRACTION_NEEDS_REVIEW

            async with session_factory() as session:
                assert await session.scalar(select(func.count(CanonicalChunk.id))) == 0
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_canonical_chunk_set_rolls_back_on_persistence_failure(
    migrated_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(migrated_database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        storage = MemoryStorage()
        workspace_id, document_id = await _create_document(session_factory)
        _, run_id, _ = await _upload(
            session_factory,
            storage,
            workspace_id=workspace_id,
            document_id=document_id,
            filename="rollback.pdf",
            content_type=PDF_CONTENT_TYPE,
            content=_pdf_bytes(
                [
                    "First page has enough text for an independent canonical chunk.",
                    "Second page has enough text for an independent canonical chunk.",
                ]
            ),
        )
        original = ingestion_module.canonicalize_chunk

        def invalid_second(processing_run_id: UUID, chunk: object):
            payload = original(processing_run_id, chunk)  # type: ignore[arg-type]
            return replace(payload, character_count=0) if payload.ordinal == 1 else payload

        monkeypatch.setattr(ingestion_module, "canonicalize_chunk", invalid_second)
        try:
            with pytest.raises(IngestionFailure) as failure:
                await IngestionService(session_factory, storage).ingest(run_id)
            assert failure.value.category is IngestionFailureCategory.PERSISTENCE_CONFLICT
            async with session_factory() as session:
                assert await session.scalar(select(func.count(CanonicalChunk.id))) == 0
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_configuration_mismatch_and_existing_chunk_conflict_fail_safely(
    migrated_database_url: str,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(migrated_database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        storage = MemoryStorage()
        workspace_id, document_id = await _create_document(session_factory)
        version_id, run_id, _ = await _upload(
            session_factory,
            storage,
            workspace_id=workspace_id,
            document_id=document_id,
            filename="conflict.pdf",
            content_type=PDF_CONTENT_TYPE,
            content=_pdf_bytes(["Conflict source with sufficient extractable text."]),
        )
        conflicting_text = "pre-existing conflicting canonical text"
        conflicting_id = f"chunk-{'d' * 64}"
        async with session_factory() as session, session.begin():
            session.add(
                CanonicalChunk(
                    id=canonical_chunk_uuid(run_id, conflicting_id),
                    processing_run_id=run_id,
                    ordinal=0,
                    chunk_identity=conflicting_id,
                    chunk_text=conflicting_text,
                    content_sha256=hashlib.sha256(conflicting_text.encode()).hexdigest(),
                    character_count=len(conflicting_text),
                    token_count=None,
                    document_format="pdf",
                    chunking_strategy="structure_aware",
                    chunker_version="1.0",
                    chunker_configuration_fingerprint="e" * 64,
                    source_provenance=[
                        {
                            "unit_id": "page:1:block:0",
                            "source": {"page_number": 1, "block_index": 0},
                            "source_start": 0,
                            "source_end": len(conflicting_text),
                            "source_length": len(conflicting_text),
                        }
                    ],
                    split_oversized_element=False,
                )
            )

        service = IngestionService(session_factory, storage)
        try:
            with pytest.raises(IngestionFailure) as conflict:
                await service.ingest(run_id)
            assert conflict.value.category is IngestionFailureCategory.PERSISTENCE_CONFLICT
            async with session_factory() as session:
                persisted = tuple(
                    (
                        await session.scalars(
                            select(CanonicalChunk).where(
                                CanonicalChunk.processing_run_id == run_id
                            )
                        )
                    ).all()
                )
                assert len(persisted) == 1
                assert persisted[0].chunk_text == conflicting_text

            mismatched_run_id = uuid4()
            async with session_factory() as session, session.begin():
                session.add(
                    ProcessingRun(
                        id=mismatched_run_id,
                        document_version_id=version_id,
                        operation_id=uuid4(),
                        operation_kind=ProcessingOperationKind.REPROCESS,
                        configuration_version=PROCESSING_CONFIGURATION_VERSION,
                        configuration_fingerprint="f" * 64,
                        stage=ProcessingStage.EXTRACTION,
                        status=ProcessingStatus.QUEUED,
                    )
                )
            with pytest.raises(IngestionFailure) as mismatch:
                await service.ingest(mismatched_run_id)
            assert mismatch.value.category is IngestionFailureCategory.CONFIGURATION_MISMATCH
            async with session_factory() as session:
                assert (
                    await session.scalar(
                        select(func.count(CanonicalChunk.id)).where(
                            CanonicalChunk.processing_run_id == mismatched_run_id
                        )
                    )
                    == 0
                )
        finally:
            await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.integration
def test_canonical_chunk_migration_upgrade_check_and_downgrade(
    disposable_database_url: str,
    alembic_runner: Callable[..., None],
) -> None:
    alembic_runner(disposable_database_url, "upgrade", "0005_processing_runs_jobs")
    alembic_runner(disposable_database_url, "upgrade", "head")
    alembic_runner(disposable_database_url, "check")

    async def table_exists() -> bool:
        engine = create_async_engine(disposable_database_url)
        try:
            async with engine.connect() as connection:
                return bool(
                    await connection.scalar(
                        text(
                            "SELECT to_regclass('public.canonical_chunks') IS NOT NULL"
                        )
                    )
                )
        finally:
            await engine.dispose()

    assert asyncio.run(table_exists()) is True
    alembic_runner(disposable_database_url, "downgrade", "0005_processing_runs_jobs")
    assert asyncio.run(table_exists()) is False


@pytest.mark.integration
@pytest.mark.storage
def test_real_minio_ingestion_persists_canonical_chunks(
    migrated_database_url: str,
    test_storage_settings: StorageSettings,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(migrated_database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        storage = S3ObjectStorage(test_storage_settings)
        await storage.probe()
        workspace_id, document_id = await _create_document(session_factory)
        _, run_id, object_key = await _upload(
            session_factory,
            storage,
            workspace_id=workspace_id,
            document_id=document_id,
            filename="real-minio.docx",
            content_type=DOCX_CONTENT_TYPE,
            content=_docx_bytes(),
        )
        try:
            result = await IngestionService(session_factory, storage).ingest(run_id)
            assert result.status is IngestionResultStatus.PERSISTED
            assert result.chunk_count > 0
            async with session_factory() as session:
                assert (
                    await session.scalar(
                        select(func.count(CanonicalChunk.id)).where(
                            CanonicalChunk.processing_run_id == run_id
                        )
                    )
                    == result.chunk_count
                )
        finally:
            await storage.delete(object_key)
            await engine.dispose()

    asyncio.run(exercise())
