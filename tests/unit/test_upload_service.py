from __future__ import annotations

import hashlib
import io
import zipfile

import pytest

from doclens_ai.services.upload import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    UploadValidationError,
    validate_upload,
)


def _office_package(member: str) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr(member, "<root />")
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("source.pdf", PDF_CONTENT_TYPE, b"%PDF-1.7\ncontent\n%%EOF\n"),
        ("source.docx", DOCX_CONTENT_TYPE, _office_package("word/document.xml")),
        ("source.xlsx", XLSX_CONTENT_TYPE, _office_package("xl/workbook.xml")),
    ],
)
def test_validate_upload_streams_and_hashes_supported_files(
    filename: str, content_type: str, content: bytes
) -> None:
    validated = validate_upload(
        io.BytesIO(content),
        original_filename=filename,
        content_type=content_type,
        max_upload_size_bytes=1024 * 1024,
        expected_file_size=len(content),
        expected_sha256_checksum=hashlib.sha256(content).hexdigest(),
    )
    try:
        assert validated.file_size == len(content)
        assert validated.sha256_checksum == hashlib.sha256(content).hexdigest()
        assert validated.stream.read() == content
    finally:
        validated.close()


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "message"),
    [
        ("empty.pdf", PDF_CONTENT_TYPE, b"", "empty"),
        ("notes.txt", "text/plain", b"notes", "only PDF"),
        ("fake.pdf", PDF_CONTENT_TYPE, b"not a pdf", "signature"),
        ("fake.docx", DOCX_CONTENT_TYPE, b"not a zip", "package"),
        ("sheet.xlsx", DOCX_CONTENT_TYPE, b"PK", "content type"),
    ],
)
def test_validate_upload_rejects_invalid_content(
    filename: str, content_type: str, content: bytes, message: str
) -> None:
    with pytest.raises(UploadValidationError, match=message):
        validate_upload(
            io.BytesIO(content),
            original_filename=filename,
            content_type=content_type,
            max_upload_size_bytes=1024,
        )


def test_validate_upload_enforces_actual_size_and_checksum() -> None:
    content = b"%PDF-1.7\ncontent\n%%EOF\n"
    with pytest.raises(UploadValidationError, match="expected size"):
        validate_upload(
            io.BytesIO(content),
            original_filename="source.pdf",
            content_type=PDF_CONTENT_TYPE,
            max_upload_size_bytes=1024,
            expected_file_size=len(content) + 1,
        )

    with pytest.raises(UploadValidationError, match="expected checksum"):
        validate_upload(
            io.BytesIO(content),
            original_filename="source.pdf",
            content_type=PDF_CONTENT_TYPE,
            max_upload_size_bytes=1024,
            expected_sha256_checksum="0" * 64,
        )


def test_validate_upload_enforces_size_limit_while_streaming() -> None:
    with pytest.raises(UploadValidationError, match="size limit"):
        validate_upload(
            io.BytesIO(b"%PDF-" + b"x" * 100 + b"%%EOF"),
            original_filename="large.pdf",
            content_type=PDF_CONTENT_TYPE,
            max_upload_size_bytes=20,
        )
