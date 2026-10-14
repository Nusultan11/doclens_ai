from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from doclens_ai.core.config import Settings
from doclens_ai.db.session import Database
from doclens_ai.dense_baseline.embeddings import E5Embedder, EmbeddingConfig
from doclens_ai.services.index_worker import IndexWorker
from doclens_ai.services.indexing import IndexingService, collection_name, embedding_identity
from doclens_ai.services.processing import ProcessingCoordinator, ProcessingPolicy
from doclens_ai.services.worker import WorkerSettings
from doclens_ai.vector.qdrant import ProductionQdrant


class IndexSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INDEX_", env_file=".env", extra="ignore")
    model_dir: Path
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: SecretStr | None = None
    collection_prefix: str = "doclens_e5_v1"
    batch_size: int = Field(default=2, ge=1, le=8)
    cpu_threads: int = Field(default=4, ge=1, le=8)
    upsert_batch_size: int = Field(default=64, ge=1, le=256)
    qdrant_timeout_seconds: float = Field(default=15, gt=0, le=60, allow_inf_nan=False)


async def main(*, preflight: bool = False) -> None:
    settings = IndexSettings()
    lifecycle = WorkerSettings()
    logging.basicConfig(level="INFO")
    for handler in logging.getLogger().handlers:
        handler.addFilter(
            lambda record: (
                record.name
                in {__name__, "doclens_ai.services.index_worker", "doclens_ai.services.worker"}
            )
        )
    # E5 verifies all pinned files before loading; local_files_only and trust_remote_code=False.
    provider = await asyncio.to_thread(
        E5Embedder,
        settings.model_dir,
        config=EmbeddingConfig(batch_size=settings.batch_size, cpu_threads=settings.cpu_threads),
    )
    metadata, fingerprint = embedding_identity(provider)
    name = collection_name(fingerprint, settings.collection_prefix)
    if preflight:
        batch = await asyncio.to_thread(
            provider.encode, ["Controlled local model preflight."], kind="passage"
        )
        print(
            json.dumps(
                {
                    "model_preflight": "passed",
                    "configuration_fingerprint": fingerprint,
                    "dimensions": provider.dimensions,
                    "vectors": len(batch.vectors),
                    "model_load_ms": provider.load_ms,
                    "configuration": metadata,
                }
            )
        )
        return
    database = Database(Settings().database_url)
    index = ProductionQdrant(
        settings.qdrant_url,
        name,
        dimensions=provider.dimensions,
        batch_size=settings.upsert_batch_size,
        timeout_seconds=settings.qdrant_timeout_seconds,
        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
    )
    worker = IndexWorker(
        ProcessingCoordinator(
            database.session_factory,
            policy=ProcessingPolicy(lease_duration=timedelta(seconds=lifecycle.lease_seconds)),
        ),
        IndexingService(database.session_factory, provider, index),
        settings=lifecycle,
        worker_id="index-" + uuid4().hex,
    )
    previous = {
        sig: signal.signal(sig, lambda *_: worker.request_stop())
        for sig in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        await worker.run()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        await index.close()
        await database.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lease-fenced local CPU indexing worker")
    parser.add_argument("--preflight", action="store_true")
    arguments = parser.parse_args()
    try:
        asyncio.run(main(preflight=arguments.preflight))
    except Exception:
        logging.getLogger(__name__).error("index_worker_startup_failed")
        raise SystemExit(1) from None
