"""Optional local search runtime, imported only when explicitly enabled."""

from __future__ import annotations

import asyncio

from doclens_ai.core.search_config import SearchSettings


async def build_search_runtime(factory, settings: SearchSettings):
    from doclens_ai.dense_baseline.embeddings import E5Embedder, EmbeddingConfig
    from doclens_ai.services.indexing import collection_name
    from doclens_ai.services.retrieval import QueryEncoder, RetrievalService, SearchUnavailable
    from doclens_ai.vector.qdrant import ProductionQdrant

    if settings.model_dir is None:
        raise SearchUnavailable()
    provider = await asyncio.to_thread(
        E5Embedder,
        settings.model_dir,
        config=EmbeddingConfig(batch_size=settings.batch_size, cpu_threads=settings.cpu_threads),
    )
    encoder = QueryEncoder(
        provider,
        concurrency=settings.inference_concurrency,
        queue_timeout_seconds=settings.queue_timeout_seconds,
    )
    vector = ProductionQdrant(
        settings.qdrant_url,
        collection_name(encoder.fingerprint, settings.collection_prefix),
        timeout_seconds=settings.qdrant_timeout_seconds,
        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
    )
    try:
        return RetrievalService(
            factory,
            encoder,
            vector,
            max_active_revisions=settings.max_active_revisions,
            db_timeout_seconds=settings.db_timeout_seconds,
        )
    except BaseException:
        await vector.close()
        raise
