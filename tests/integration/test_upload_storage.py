from __future__ import annotations

import asyncio
import hashlib
import io
from uuid import uuid4

import pytest

from doclens_ai.storage.config import StorageSettings
from doclens_ai.storage.s3 import ObjectStorageError, S3ObjectStorage


@pytest.mark.integration
@pytest.mark.storage
def test_real_object_storage_upload_inspect_stream_and_delete(
    test_storage_settings: StorageSettings,
) -> None:
    async def exercise_storage() -> None:
        storage = S3ObjectStorage(test_storage_settings)
        content = b"%PDF-1.7\nreal object storage\n%%EOF\n"
        checksum = hashlib.sha256(content).hexdigest()
        key = f"integration-tests/{uuid4()}/source.pdf"

        await storage.probe()
        await storage.put_stream(
            key,
            io.BytesIO(content),
            content_type="application/pdf",
            sha256_checksum=checksum,
        )
        try:
            metadata = await storage.inspect(key)
            downloaded = b"".join([chunk async for chunk in storage.stream_read(key)])

            assert metadata.size == len(content)
            assert metadata.content_type == "application/pdf"
            assert metadata.metadata["sha256"] == checksum
            assert downloaded == content
            assert await storage.sha256(key) == checksum
        finally:
            await storage.delete(key)

        with pytest.raises(ObjectStorageError):
            await storage.inspect(key)

    asyncio.run(exercise_storage())
