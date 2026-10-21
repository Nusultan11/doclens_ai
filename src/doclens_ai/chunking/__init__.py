"""Deterministic offline document chunking baseline."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

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
    NormalizationRange,
    TextBlockOffsetMap,
)

if TYPE_CHECKING:
    from doclens_ai.chunking.core import (
        EvaluationConfigurationError,
        chunk_document,
        chunk_documents,
        evaluate_corpus,
    )


def __getattr__(name: str) -> Any:
    # API processing configuration uses models, not the optional extraction engine.
    if name in {
        "EvaluationConfigurationError",
        "chunk_document",
        "chunk_documents",
        "evaluate_corpus",
    }:
        return getattr(import_module("doclens_ai.chunking.core"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "NormalizationRange",
    "TextBlockOffsetMap",
    "chunk_document",
    "chunk_documents",
    "evaluate_corpus",
]
