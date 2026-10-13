"""Deterministic offline document chunking baseline."""

from doclens_ai.chunking.core import (
    EvaluationConfigurationError,
    chunk_document,
    chunk_documents,
    evaluate_corpus,
)
from doclens_ai.chunking.models import (
    CHUNKING_SCHEMA_VERSION,
    Chunk,
    ChunkingConfig,
    ChunkingOutcome,
    ChunkingReason,
    ChunkingStatus,
    ChunkingStrategy,
    ChunkSourceSpan,
    FormulaPolicy,
)

__all__ = [
    "CHUNKING_SCHEMA_VERSION",
    "Chunk",
    "ChunkSourceSpan",
    "ChunkingConfig",
    "ChunkingOutcome",
    "ChunkingReason",
    "ChunkingStatus",
    "ChunkingStrategy",
    "EvaluationConfigurationError",
    "FormulaPolicy",
    "chunk_document",
    "chunk_documents",
    "evaluate_corpus",
]
