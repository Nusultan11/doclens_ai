from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SearchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SEARCH_", env_file=".env", extra="ignore")
    enabled: bool = False
    model_dir: Path | None = None
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: SecretStr | None = None
    collection_prefix: str = "doclens_e5_v1"
    batch_size: int = Field(default=2, ge=1, le=8)
    cpu_threads: int = Field(default=4, ge=1, le=8)
    inference_concurrency: int = Field(default=1, ge=1, le=2)
    queue_timeout_seconds: float = Field(default=1, gt=0, le=10, allow_inf_nan=False)
    qdrant_timeout_seconds: float = Field(default=5, gt=0, le=30, allow_inf_nan=False)
    db_timeout_seconds: float = Field(default=5, gt=0, le=30, allow_inf_nan=False)
    max_active_revisions: int = Field(default=128, ge=1, le=512)
