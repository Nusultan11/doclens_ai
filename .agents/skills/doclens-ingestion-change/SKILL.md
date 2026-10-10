---
name: doclens-ingestion-change
description: Change DocLens document ingestion behavior, including parsing, extraction, cleaning, chunking, embeddings, indexing, retries, processing state, deletion, or reindexing. Do not use for document features that leave ingestion unchanged.
---

# DocLens ingestion changes

Map the affected flow into explicit pipeline stages and preserve clear handoffs among upload, extraction/parsing, cleaning/validation, chunking, embeddings, and indexing.

Before implementation, inspect the relevant persistence model, processing states, retry path, vector metadata, and targeted tests. Then ensure:

- PostgreSQL remains authoritative and consistent across success, retry, partial failure, and cancellation.
- Repeating a request is safe: stable identities or uniqueness constraints prevent duplicate documents, chunks, and vectors.
- One document's failure is isolated from unrelated work; external-service failures cannot leave business state falsely complete.
- Chunk boundaries are deterministic for the same inputs and configuration. Persist or expose the chunking configuration and embedding model/revision needed to reproduce indexed data.
- Qdrant remains rebuildable from authoritative state. Backend-owned scope metadata and filters preserve workspace/document isolation.
- Deletion and reindex operations define cleanup, replacement, partial-failure, and retry behavior without orphaning authoritative or indexed records.

Add focused unit tests for deterministic logic and retry/state transitions. Add integration coverage where persistence, Qdrant, or another service boundary is material. Exercise relevant failures and repeated ingestion, then report the exact checks and results.
