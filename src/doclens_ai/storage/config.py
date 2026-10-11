from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """S3 settings loaded only by code that needs object storage."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="S3_",
        extra="ignore",
    )

    endpoint_url: str
    access_key: str
    secret_key: SecretStr
    bucket_name: str
    region: str | None = None
    secure: bool = True
    max_upload_size_bytes: int = 50 * 1024 * 1024
    connect_timeout_seconds: int = 3
    read_timeout_seconds: int = 30

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("S3_ENDPOINT_URL must be an absolute HTTP(S) URL")
        return value.rstrip("/")

    @field_validator("access_key", "bucket_name")
    @classmethod
    def validate_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("storage values must not be blank")
        return value

    @field_validator(
        "max_upload_size_bytes", "connect_timeout_seconds", "read_timeout_seconds"
    )
    @classmethod
    def validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("storage size and timeout values must be positive")
        return value

    @model_validator(mode="after")
    def validate_transport(self) -> StorageSettings:
        expected_scheme = "https" if self.secure else "http"
        if urlparse(self.endpoint_url).scheme != expected_scheme:
            raise ValueError(
                f"S3_SECURE={self.secure} requires an {expected_scheme.upper()} endpoint"
            )
        return self


@lru_cache
def get_storage_settings() -> StorageSettings:
    return StorageSettings()
