from __future__ import annotations

import asyncio
import hashlib
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from doclens_ai.models import Document, DocumentVersion, UploadSession, UploadStatus
from doclens_ai.services.processing import (
    DEFAULT_MAX_ATTEMPTS,
    create_initial_processing_records,
    get_initial_processing_job,
)
from doclens_ai.storage.s3 import ObjectMetadata, ObjectStorageError

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SUPPORTED_UPLOADS = {
    ".pdf": PDF_CONTENT_TYPE,
    ".docx": DOCX_CONTENT_TYPE,
    ".xlsx": XLSX_CONTENT_TYPE,
}


class UploadValidationError(ValueError):
    pass


class UploadConflictError(RuntimeError):
    pass


class UploadNotFoundError(LookupError):
    pass


class UploadVerificationError(RuntimeError):
    pass


class ObjectStorage(Protocol):
    async def put_stream(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str,
        sha256_checksum: str,
    ) -> None: ...

    async def inspect(self, key: str) -> ObjectMetadata: ...

    async def sha256(self, key: str, *, chunk_size: int = 1024 * 1024) -> str: ...


@dataclass
class ValidatedUpload:
    stream: BinaryIO
    original_filename: str
    content_type: str
    file_size: int
    sha256_checksum: str
    suffix: str

    def close(self) -> None:
        self.stream.close()


@dataclass(frozen=True)
class UploadResult:
    upload_session_id: UUID
    document_version_id: UUID
    processing_job_id: UUID
    document_id: UUID
    version_number: int
    object_storage_key: str
    file_size: int
    sha256_checksum: str


@dataclass(frozen=True)
class _PreparedAttempt:
    id: UUID
    object_storage_key: str


def validate_upload(
    stream: BinaryIO,
    *,
    original_filename: str,
    content_type: str,
    max_upload_size_bytes: int,
    expected_file_size: int | None = None,
    expected_sha256_checksum: str | None = None,
) -> ValidatedUpload:
    """Stage and validate an upload without loading the whole file into memory."""

    if max_upload_size_bytes <= 0:
        raise UploadValidationError("maximum upload size must be positive")
    if not original_filename or Path(original_filename).name != original_filename:
        raise UploadValidationError("original filename must be a plain filename")

    suffix = Path(original_filename).suffix.lower()
    required_content_type = SUPPORTED_UPLOADS.get(suffix)
    if required_content_type is None:
        raise UploadValidationError("only PDF, DOCX, and XLSX uploads are supported")
    if content_type != required_content_type:
        raise UploadValidationError("declared content type does not match the file extension")

    staged = tempfile.SpooledTemporaryFile(max_size=min(max_upload_size_bytes, 8 * 1024 * 1024))
    digest = hashlib.sha256()
    file_size = 0
    try:
        while chunk := stream.read(1024 * 1024):
            if not isinstance(chunk, bytes):
                raise UploadValidationError("upload stream must yield bytes")
            file_size += len(chunk)
            if file_size > max_upload_size_bytes:
                raise UploadValidationError("upload exceeds the configured size limit")
            digest.update(chunk)
            staged.write(chunk)

        if file_size == 0:
            raise UploadValidationError("empty uploads are not allowed")

        checksum = digest.hexdigest()
        if expected_file_size is not None and expected_file_size != file_size:
            raise UploadValidationError("actual file size does not match the expected size")
        if (
            expected_sha256_checksum is not None
            and expected_sha256_checksum.lower() != checksum
        ):
            raise UploadValidationError("actual SHA-256 does not match the expected checksum")

        staged.seek(0)
        _validate_structure(staged, suffix)
        staged.seek(0)
        return ValidatedUpload(
            stream=staged,
            original_filename=original_filename,
            content_type=content_type,
            file_size=file_size,
            sha256_checksum=checksum,
            suffix=suffix,
        )
    except Exception:
        staged.close()
        raise


def _validate_structure(stream: BinaryIO, suffix: str) -> None:
    if suffix == ".pdf":
        if stream.read(5) != b"%PDF-":
            raise UploadValidationError("PDF signature is invalid")
        stream.seek(max(0, stream.seek(0, 2) - 2048))
        if b"%%EOF" not in stream.read():
            raise UploadValidationError("PDF end marker is missing")
        return

    required_member = "word/document.xml" if suffix == ".docx" else "xl/workbook.xml"
    try:
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            members = set(archive.namelist())
            if "[Content_Types].xml" not in members or required_member not in members:
                raise UploadValidationError(f"{suffix[1:].upper()} package structure is invalid")
            archive.getinfo(required_member)
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise UploadValidationError(f"{suffix[1:].upper()} package is invalid") from error


class UploadService:
    """Trusted internal service for idempotent upload and version confirmation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: ObjectStorage,
        *,
        max_upload_size_bytes: int,
        processing_max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    ) -> None:
        if processing_max_attempts <= 0:
            raise ValueError("processing max attempts must be positive")
        self._session_factory = session_factory
        self._storage = storage
        self._max_upload_size_bytes = max_upload_size_bytes
        self._processing_max_attempts = processing_max_attempts

    async def upload_and_confirm(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        idempotency_key: str,
        original_filename: str,
        content_type: str,
        stream: BinaryIO,
        expected_file_size: int | None = None,
        expected_sha256_checksum: str | None = None,
    ) -> UploadResult:
        self._validate_idempotency_key(idempotency_key)
        validated = await asyncio.to_thread(
            validate_upload,
            stream,
            original_filename=original_filename,
            content_type=content_type,
            max_upload_size_bytes=self._max_upload_size_bytes,
            expected_file_size=expected_file_size,
            expected_sha256_checksum=expected_sha256_checksum,
        )
        try:
            prepared = await self._prepare_attempt(
                workspace_id=workspace_id,
                document_id=document_id,
                idempotency_key=idempotency_key,
                upload=validated,
            )
            if isinstance(prepared, UploadResult):
                return prepared

            try:
                await self._storage.put_stream(
                    prepared.object_storage_key,
                    validated.stream,
                    content_type=validated.content_type,
                    sha256_checksum=validated.sha256_checksum,
                )
                await self._verify_object(prepared.object_storage_key, validated)
            except (ObjectStorageError, UploadVerificationError):
                await self._record_failure(prepared.id, "storage_or_verification_failed")
                raise

            await self._mark_uploaded(prepared.id)
            return await self._finalize(
                upload_session_id=prepared.id,
                workspace_id=workspace_id,
            )
        finally:
            validated.close()

    @staticmethod
    def _validate_idempotency_key(idempotency_key: str) -> None:
        if not idempotency_key.strip() or len(idempotency_key) > 255:
            raise UploadValidationError("idempotency key must contain 1 to 255 characters")

    async def _prepare_attempt(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        idempotency_key: str,
        upload: ValidatedUpload,
    ) -> _PreparedAttempt | UploadResult:
        upload_session_id = uuid4()
        object_storage_key = (
            f"workspaces/{workspace_id}/documents/{document_id}/uploads/"
            f"{upload_session_id}/source{upload.suffix}"
        )
        async with self._session_factory() as session, session.begin():
            document_exists = await session.scalar(
                select(Document.id).where(
                    Document.id == document_id,
                    Document.workspace_id == workspace_id,
                )
            )
            if document_exists is None:
                raise UploadNotFoundError("document does not exist in the trusted workspace scope")

            statement = (
                insert(UploadSession)
                .values(
                    id=upload_session_id,
                    document_id=document_id,
                    idempotency_key=idempotency_key,
                    object_storage_key=object_storage_key,
                    status=UploadStatus.PENDING,
                    original_filename=upload.original_filename,
                    content_type=upload.content_type,
                    file_size=upload.file_size,
                    sha256_checksum=upload.sha256_checksum,
                )
                .on_conflict_do_nothing(
                    index_elements=[UploadSession.document_id, UploadSession.idempotency_key]
                )
            )
            await session.execute(statement)
            attempt = await session.scalar(
                select(UploadSession)
                .where(
                    UploadSession.document_id == document_id,
                    UploadSession.idempotency_key == idempotency_key,
                )
                .with_for_update()
            )
            if attempt is None:
                raise RuntimeError("upload attempt was not persisted")
            self._ensure_same_upload(attempt, upload)
            if attempt.status == UploadStatus.COMPLETED:
                return await self._result_for_completed(session, attempt)
            return _PreparedAttempt(attempt.id, attempt.object_storage_key)

    @staticmethod
    def _ensure_same_upload(attempt: UploadSession, upload: ValidatedUpload) -> None:
        persisted = (
            attempt.original_filename,
            attempt.content_type,
            attempt.file_size,
            attempt.sha256_checksum,
        )
        incoming = (
            upload.original_filename,
            upload.content_type,
            upload.file_size,
            upload.sha256_checksum,
        )
        if persisted != incoming:
            raise UploadConflictError("idempotency key is already bound to different content")

    async def _verify_object(self, key: str, upload: ValidatedUpload) -> None:
        metadata = await self._storage.inspect(key)
        if (
            metadata.size != upload.file_size
            or metadata.content_type != upload.content_type
            or metadata.metadata.get("sha256") != upload.sha256_checksum
        ):
            raise UploadVerificationError("stored object metadata does not match the upload")
        if await self._storage.sha256(key) != upload.sha256_checksum:
            raise UploadVerificationError("stored object bytes do not match the upload")

    async def _record_failure(self, upload_session_id: UUID, failure_code: str) -> None:
        try:
            async with self._session_factory() as session, session.begin():
                attempt = await session.scalar(
                    select(UploadSession)
                    .where(UploadSession.id == upload_session_id)
                    .with_for_update()
                )
                if attempt is not None and attempt.status != UploadStatus.COMPLETED:
                    attempt.status = UploadStatus.FAILED
                    attempt.failure_code = failure_code
        except Exception:
            # The original storage error remains authoritative. A pending row and its
            # deterministic object key still identify any object requiring recovery.
            return

    async def _mark_uploaded(self, upload_session_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            attempt = await session.scalar(
                select(UploadSession)
                .where(UploadSession.id == upload_session_id)
                .with_for_update()
            )
            if attempt is None:
                raise UploadNotFoundError("upload session disappeared before confirmation")
            if attempt.status != UploadStatus.COMPLETED:
                attempt.status = UploadStatus.UPLOADED
                attempt.failure_code = None

    async def _finalize(
        self, *, upload_session_id: UUID, workspace_id: UUID
    ) -> UploadResult:
        async with self._session_factory() as session, session.begin():
            attempt = await session.scalar(
                select(UploadSession)
                .join(Document, Document.id == UploadSession.document_id)
                .where(
                    UploadSession.id == upload_session_id,
                    Document.workspace_id == workspace_id,
                )
                .with_for_update()
            )
            if attempt is None:
                raise UploadNotFoundError("upload session is outside the trusted workspace scope")
            if attempt.status == UploadStatus.COMPLETED:
                return await self._result_for_completed(session, attempt)
            if attempt.status != UploadStatus.UPLOADED:
                raise UploadConflictError("upload session is not ready to be committed")

            document = await session.scalar(
                select(Document)
                .where(Document.id == attempt.document_id)
                .with_for_update()
            )
            if document is None:
                raise UploadNotFoundError("document disappeared before confirmation")

            latest_version = await session.scalar(
                select(func.max(DocumentVersion.version_number)).where(
                    DocumentVersion.document_id == document.id
                )
            )
            version = DocumentVersion(
                document_id=document.id,
                version_number=(latest_version or 0) + 1,
                original_filename=attempt.original_filename,
                content_type=attempt.content_type,
                file_size=attempt.file_size,
                sha256_checksum=attempt.sha256_checksum,
                object_storage_key=attempt.object_storage_key,
            )
            session.add(version)
            await session.flush()
            _, job = await create_initial_processing_records(
                session,
                document_version_id=version.id,
                max_attempts=self._processing_max_attempts,
            )
            attempt.status = UploadStatus.COMPLETED
            attempt.committed_document_version_id = version.id
            attempt.failure_code = None
            return self._result(attempt, version, processing_job_id=job.id)

    async def _result_for_completed(
        self, session: AsyncSession, attempt: UploadSession
    ) -> UploadResult:
        if attempt.committed_document_version_id is None:
            raise UploadConflictError("completed upload is missing its document version")
        version = await session.get(DocumentVersion, attempt.committed_document_version_id)
        if version is None or version.document_id != attempt.document_id:
            raise UploadConflictError("completed upload references an invalid document version")
        job = await get_initial_processing_job(
            session,
            document_version_id=version.id,
        )
        if job is None:
            raise UploadConflictError("completed upload is missing its processing job")
        return self._result(attempt, version, processing_job_id=job.id)

    @staticmethod
    def _result(
        attempt: UploadSession,
        version: DocumentVersion,
        *,
        processing_job_id: UUID,
    ) -> UploadResult:
        return UploadResult(
            upload_session_id=attempt.id,
            document_version_id=version.id,
            processing_job_id=processing_job_id,
            document_id=version.document_id,
            version_number=version.version_number,
            object_storage_key=version.object_storage_key,
            file_size=version.file_size,
            sha256_checksum=version.sha256_checksum,
        )
