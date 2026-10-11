from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from typing import Any, BinaryIO

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from doclens_ai.storage.config import StorageSettings


class ObjectStorageError(RuntimeError):
    """A normalized object-storage operation failure."""


@dataclass(frozen=True)
class ObjectMetadata:
    size: int
    content_type: str | None
    metadata: Mapping[str, str]


class S3ObjectStorage:
    def __init__(self, settings: StorageSettings, client: BaseClient | None = None) -> None:
        self.settings = settings
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key.get_secret_value(),
            region_name=settings.region,
            use_ssl=settings.secure,
            config=Config(
                connect_timeout=settings.connect_timeout_seconds,
                read_timeout=settings.read_timeout_seconds,
                retries={"max_attempts": 2, "mode": "standard"},
                s3={"addressing_style": "path"},
            ),
        )
        self._transfer_config = TransferConfig(use_threads=False)

    async def probe(self) -> None:
        await self._call(self._client.head_bucket, Bucket=self.settings.bucket_name)

    async def ensure_private_bucket(self) -> None:
        """Create the configured bucket if needed and remove public bucket policy."""

        await self._call(self._ensure_private_bucket_sync)

    async def put_stream(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str,
        sha256_checksum: str,
    ) -> None:
        stream.seek(0)
        await self._call(
            self._client.upload_fileobj,
            stream,
            self.settings.bucket_name,
            key,
            ExtraArgs={
                "ContentType": content_type,
                "Metadata": {"sha256": sha256_checksum},
            },
            Config=self._transfer_config,
        )

    async def inspect(self, key: str) -> ObjectMetadata:
        response = await self._call(
            self._client.head_object,
            Bucket=self.settings.bucket_name,
            Key=key,
        )
        return ObjectMetadata(
            size=int(response["ContentLength"]),
            content_type=response.get("ContentType"),
            metadata=response.get("Metadata", {}),
        )

    async def sha256(self, key: str, *, chunk_size: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        async for chunk in self.stream_read(key, chunk_size=chunk_size):
            digest.update(chunk)
        return digest.hexdigest()

    async def stream_read(
        self, key: str, *, chunk_size: int = 1024 * 1024
    ) -> AsyncIterator[bytes]:
        response = await self._call(
            self._client.get_object,
            Bucket=self.settings.bucket_name,
            Key=key,
        )
        body = response["Body"]
        try:
            while chunk := await asyncio.to_thread(body.read, chunk_size):
                yield chunk
        except (BotoCoreError, ClientError, OSError) as error:
            raise ObjectStorageError(f"failed to read object {key!r}") from error
        finally:
            await asyncio.to_thread(body.close)

    async def delete(self, key: str) -> None:
        await self._call(
            self._client.delete_object,
            Bucket=self.settings.bucket_name,
            Key=key,
        )

    async def _call(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return await asyncio.to_thread(operation, *args, **kwargs)
        except (BotoCoreError, ClientError, OSError) as error:
            raise ObjectStorageError("S3-compatible object storage operation failed") from error

    def _ensure_private_bucket_sync(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.settings.bucket_name)
        except ClientError as error:
            error_code = str(error.response.get("Error", {}).get("Code", ""))
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            arguments: dict[str, Any] = {"Bucket": self.settings.bucket_name}
            if self.settings.region and self.settings.region != "us-east-1":
                arguments["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.settings.region
                }
            self._client.create_bucket(**arguments)

        self._client.put_bucket_acl(Bucket=self.settings.bucket_name, ACL="private")
        try:
            self._client.delete_bucket_policy(Bucket=self.settings.bucket_name)
        except ClientError as error:
            error_code = str(error.response.get("Error", {}).get("Code", ""))
            if error_code not in {"404", "NoSuchBucketPolicy", "NoSuchPolicy"}:
                raise


async def _initialize_bucket() -> None:
    from doclens_ai.storage.config import get_storage_settings

    storage = S3ObjectStorage(get_storage_settings())
    await storage.ensure_private_bucket()


if __name__ == "__main__":
    asyncio.run(_initialize_bucket())
