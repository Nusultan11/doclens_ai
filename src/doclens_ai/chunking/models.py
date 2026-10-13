"""Typed contracts for deterministic offline document chunking."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum

from doclens_ai.extraction.models import DocumentFormat, SourceLocation

CHUNKING_SCHEMA_VERSION = "1.0"


class ChunkingStrategy(StrEnum):
    """Available deterministic baseline strategies."""

    FIXED_SIZE = "fixed_size"
    STRUCTURE_AWARE = "structure_aware"


class FormulaPolicy(StrEnum):
    """How spreadsheet formula cells are represented without execution."""

    FORMULA_AND_CACHED_VALUE = "formula_and_cached_value"


class ChunkingStatus(StrEnum):
    """Outcome for one document and one strategy."""

    CHUNKED = "chunked"
    SKIPPED = "skipped"
    FAILED = "failed"


class ChunkingReason(StrEnum):
    """Sanitized skip and failure reasons."""

    EXTRACTION_NEEDS_REVIEW = "extraction_needs_review"
    EXTRACTION_FAILED = "extraction_failed"
    MISSING_DOCUMENT_IDENTITY = "missing_document_identity"
    EMPTY_CONTENT = "empty_content"
    LIMIT_EXCEEDED = "limit_exceeded"
    CHUNKING_FAILED = "chunking_failed"


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    """Versioned settings that fully determine chunk boundaries."""

    strategy: ChunkingStrategy
    max_characters: int = 1_200
    overlap_characters: int = 120
    allow_needs_review: bool = False
    formula_policy: FormulaPolicy = FormulaPolicy.FORMULA_AND_CACHED_VALUE
    max_source_characters: int = 5_000_000
    max_chunks_per_document: int = 100_000
    version: str = CHUNKING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.max_characters <= 0:
            raise ValueError("max_characters must be positive")
        if self.overlap_characters < 0:
            raise ValueError("overlap_characters must be non-negative")
        if self.overlap_characters >= self.max_characters:
            raise ValueError("overlap_characters must be smaller than max_characters")
        if self.max_source_characters <= 0:
            raise ValueError("max_source_characters must be positive")
        if self.max_chunks_per_document <= 0:
            raise ValueError("max_chunks_per_document must be positive")
        if not self.version.strip():
            raise ValueError("version must not be empty")

    def fingerprint(self) -> str:
        """Return a stable fingerprint for the complete configuration."""

        payload = {
            "allow_needs_review": self.allow_needs_review,
            "formula_policy": self.formula_policy.value,
            "max_characters": self.max_characters,
            "max_chunks_per_document": self.max_chunks_per_document,
            "max_source_characters": self.max_source_characters,
            "overlap_characters": self.overlap_characters,
            "strategy": self.strategy.value,
            "version": self.version,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ChunkSourceSpan:
    """A range from one normalized source unit represented in a chunk."""

    unit_id: str
    source: SourceLocation
    source_start: int
    source_end: int
    source_length: int


@dataclass(frozen=True, slots=True)
class Chunk:
    """One deterministic in-memory chunk with complete provenance."""

    chunk_id: str
    document_id: str
    source_sha256: str
    document_format: DocumentFormat
    strategy: ChunkingStrategy
    config_version: str
    config_fingerprint: str
    ordinal: int
    text: str
    provenance: tuple[ChunkSourceSpan, ...]
    split_oversized_element: bool = False


@dataclass(frozen=True, slots=True)
class ChunkingOutcome:
    """Isolated result for one document and one chunking configuration."""

    document_id: str
    source_sha256: str | None
    document_format: DocumentFormat | None
    strategy: ChunkingStrategy
    config_version: str
    config_fingerprint: str
    status: ChunkingStatus
    chunks: tuple[Chunk, ...] = ()
    reason: ChunkingReason | None = None
    normalized_source_characters: int = 0
    covered_source_characters: int = 0
    emitted_source_characters: int = 0

    def deterministic_fingerprint(self) -> str:
        """Fingerprint content and metadata without exposing chunk text."""

        payload = {
            "chunks": [chunk.chunk_id for chunk in self.chunks],
            "config_fingerprint": self.config_fingerprint,
            "document_id": self.document_id,
            "format": self.document_format.value if self.document_format else None,
            "reason": self.reason.value if self.reason else None,
            "source_sha256": self.source_sha256,
            "status": self.status.value,
            "strategy": self.strategy.value,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def config_as_dict(config: ChunkingConfig) -> dict[str, object]:
    """Return a JSON-safe configuration mapping."""

    payload = asdict(config)
    payload["strategy"] = config.strategy.value
    payload["formula_policy"] = config.formula_policy.value
    payload["fingerprint"] = config.fingerprint()
    return payload
