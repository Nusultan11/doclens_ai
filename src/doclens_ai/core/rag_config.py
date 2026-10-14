"""Operator-only local generation settings; no model downloads or client overrides."""

import ipaddress

import httpx
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RagSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")
    enabled: bool = False
    endpoint: str | None = None
    model_id: str | None = Field(default=None, min_length=1, max_length=200)
    # Operator declarations, NOT proof that the remote process loaded these bytes.
    model_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    api_key: SecretStr | None = None
    temperature: float = Field(default=0, ge=0, le=2, allow_inf_nan=False)
    max_output_tokens: int = Field(default=1024, ge=64, le=4096)
    timeout_seconds: float = Field(default=60, gt=0, le=300, allow_inf_nan=False)
    queue_timeout_seconds: float = Field(default=1, gt=0, le=10, allow_inf_nan=False)
    concurrency: int = Field(default=1, ge=1, le=4)
    max_response_bytes: int = Field(default=65536, ge=1024, le=262144)
    max_context_chars: int = Field(default=16000, ge=4000, le=32000)
    max_chunk_chars: int = Field(default=4000, ge=128, le=8000)
    max_evidence_chunks: int = Field(default=6, ge=1, le=6)

    @field_validator("model_revision", "artifact_sha256", "api_key", mode="before")
    @classmethod
    def optional_declarations(cls, value):
        return None if value == "" else value

    @field_validator("endpoint")
    @classmethod
    def local_endpoint(cls, value):
        if value is None:
            return None
        try:
            url = httpx.URL(value)
            address = ipaddress.ip_address(url.host)
            # Explicit RFC1918/ULA or loopback literal only: no DNS/proxy/redirect escape.
            local = address.is_loopback or (
                address in ipaddress.ip_network("10.0.0.0/8")
                or address in ipaddress.ip_network("172.16.0.0/12")
                or address in ipaddress.ip_network("192.168.0.0/16")
                or address in ipaddress.ip_network("fc00::/7")
            )
            if not (
                local
                and url.scheme in {"http", "https"}
                and not url.username
                and not url.password
                and not url.query
                and not url.fragment
                and url.path == "/v1/chat/completions"
            ):
                raise ValueError
        except (ValueError, httpx.InvalidURL):
            raise ValueError(
                "generator must use an explicit private/loopback IP endpoint"
            ) from None
        return value

    @field_validator("model_id")
    @classmethod
    def valid_model(cls, value):
        if value is not None and (not value.strip() or any(ord(c) < 32 for c in value)):
            raise ValueError("invalid model identity")
        return value

    @model_validator(mode="after")
    def configured(self):
        if self.enabled and (self.endpoint is None or self.model_id is None):
            raise ValueError("local generator endpoint and model identity are required")
        return self
