"""Reviewed IR evidence groups; only complete outcomes may enter ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from doclens_ai.chunking.models import Chunk, ChunkingStrategy, ChunkSourceSpan
from doclens_ai.extraction.ir import (
    ATOMIC_RELATION_KINDS,
    CellElement,
    DocumentElement,
    DocumentIR,
    FormulaElement,
    Relation,
    SourceIdentity,
)
from doclens_ai.extraction.ir_validation import (
    DEFAULT_EVIDENCE_POLICY,
    EvidencePolicy,
    EvidenceReview,
    EvidenceValidation,
    canonical_digest,
    observation_digest,
    validate_ir,
)

IR_CHUNKER_VERSION = "2.2"


@dataclass(frozen=True)
class SearchableUnit:
    unit_id: str
    text: str
    elements: tuple[DocumentElement, ...]
    relations: tuple[Relation, ...]


@dataclass(frozen=True)
class EvidenceChunks:
    validation: EvidenceValidation
    units: tuple[SearchableUnit, ...]
    chunks: tuple[Chunk, ...]
    held: tuple[tuple[str, str], ...]
    document_state: str = "complete"

    @property
    def status(self) -> Literal["complete", "partial_review_required", "blocked"]:
        """Diagnostic chunks are publishable only as a complete admitted document."""
        if self.validation.global_reasons or not self.chunks:
            return "blocked"
        if self.document_state != "complete" or self.validation.rejected or self.held:
            return "partial_review_required"
        return "complete"


def _render(element: DocumentElement) -> str:
    # Retain lexical values and formulas exactly, without executing or formatting
    # numbers. Field labels distinguish stored/cache/formula observations.
    if isinstance(element, CellElement):
        return "\n".join(
            f"{field}={value}"
            for field in ("text", "raw_value", "formula", "cached_value", "number_format")
            if (value := getattr(element, field)) is not None
        )
    if isinstance(element, FormulaElement):
        return "\n".join(
            f"{label}={value}"
            for label, value in (
                ("formula", element.expression),
                ("cached_value", element.cached_value),
            )
            if value is not None
        )
    return getattr(element, "text", None) or getattr(element, "caption", None) or ""


def chunk_verified_ir(
    ir: DocumentIR,
    *,
    expected: SourceIdentity,
    review: EvidenceReview | None,
    policy: EvidencePolicy = DEFAULT_EVIDENCE_POLICY,
    max_characters: int = 1200,
    max_source_characters: int = 5_000_000,
    max_chunks: int = 100_000,
) -> EvidenceChunks:
    if min(max_characters, max_source_characters, max_chunks) <= 0:
        raise ValueError("chunk limits must be positive")
    ir = DocumentIR.model_validate_json(ir.model_dump_json())
    validation = validate_ir(ir, expected=expected, review=review, policy=policy)
    if not validation.allowed:
        return EvidenceChunks(validation, (), (), (), ir.state)
    allowed = set(validation.allowed)
    groups = {identity: identity for identity in allowed}

    def root(identity: str) -> str:
        while groups[identity] != identity:
            groups[identity] = groups[groups[identity]]
            identity = groups[identity]
        return identity

    for relation in ir.relations:
        if (
            relation.kind in ATOMIC_RELATION_KINDS
            and relation.source_id in allowed
            and relation.target_id in allowed
        ):
            groups[root(relation.target_id)] = root(relation.source_id)
    members: dict[str, list[DocumentElement]] = {}
    for element in ir.elements:
        if element.id in allowed:
            members.setdefault(root(element.id), []).append(element)
    grouped_relations: dict[str, list[Relation]] = {}
    for relation in ir.relations:
        if relation.source_id in allowed and relation.target_id in allowed:
            # Keep outgoing reading-order links even when their endpoints belong
            # to different units. The original reviewed relation is not rewritten.
            grouped_relations.setdefault(root(relation.source_id), []).append(relation)
    config_fingerprint = canonical_digest(
        {
            "chunker": IR_CHUNKER_VERSION,
            "validation": validation.fingerprint,
            "max_characters": max_characters,
            "max_source_characters": max_source_characters,
            "max_chunks": max_chunks,
        }
    )
    units = []
    chunks = []
    held = []
    total = 0
    for group_id, elements in members.items():
        rendered = [(e, _render(e)) for e in elements]
        text = "\n".join(value for _, value in rendered if value)
        relations = tuple(grouped_relations.get(group_id, ()))
        unit_id = "ir-unit:" + canonical_digest(
            {
                "elements": [observation_digest(e) for e in elements],
                "relations": [observation_digest(r) for r in relations],
            }
        )
        reason = (
            "empty_evidence"
            if not text
            else "oversized_evidence"
            if len(text) > max_characters
            else None
        )
        if reason:
            held.append((unit_id, reason))
            continue
        total += len(text)
        if total > max_source_characters or len(chunks) >= max_chunks:
            # No partially published prefix when a document budget is exceeded.
            return EvidenceChunks(validation, (), (), ((unit_id, "document_limit"),), ir.state)
        units.append(SearchableUnit(unit_id, text, tuple(elements), relations))
        spans = tuple(
            ChunkSourceSpan(
                unit_id=f"ir-element:{e.id}:{observation_digest(e)}",
                source=e.source,
                source_start=0,
                source_end=len(value),
                source_length=len(value),
            )
            for e, value in rendered
            if value
        )
        identity = canonical_digest(
            {
                "source": expected.model_dump(mode="json"),
                "unit": unit_id,
                "config": config_fingerprint,
                "text": text,
            }
        )
        chunks.append(
            Chunk(
                chunk_id="chunk-" + identity,
                document_id=expected.document_version_id,
                source_sha256=expected.sha256,
                document_format=expected.document_format,
                strategy=ChunkingStrategy.STRUCTURE_AWARE,
                config_version=IR_CHUNKER_VERSION,
                config_fingerprint=config_fingerprint,
                ordinal=len(chunks),
                text=text,
                provenance=spans,
            )
        )
    return EvidenceChunks(validation, tuple(units), tuple(chunks), tuple(held), ir.state)
