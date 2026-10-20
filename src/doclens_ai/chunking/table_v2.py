"""Offline evidence bundles, with lossless literals and no canonical Markdown.

Chunks are independently reverified against reviewed evidence on every call.
They have no persistence/index publication adapter. Existing v1 chunking is intact.
"""

from __future__ import annotations

from doclens_ai.extraction.evidence_v2 import (
    Cell,
    Contract,
    Digest,
    EvidenceEnvelope,
    Name,
    Relation,
    ReviewedDocument,
    Scope,
    cell_evidence_id,
    verify_proposal,
)
from doclens_ai.extraction.fidelity_gold import fingerprint


class TableChunk(Contract):
    schema_version: str = "table-chunk-2.0"
    chunk_id: Digest
    scope: Scope
    table_id: Name
    section_id: Name | None
    value_cell_id: Name
    cells: tuple[Cell, ...]
    relations: tuple[Relation, ...]
    evidence_ids: tuple[Digest, ...]
    review_revision: Name
    candidate_revision: Name
    config_sha256: Digest


def table_chunks(
    enriched: EvidenceEnvelope,
    reviewed: ReviewedDocument,
    *,
    max_characters: int = 1200,
    max_cells: int = 256,
    allow_synthetic: bool = False,
) -> tuple[tuple[TableChunk, ...], tuple[str, ...]]:
    """Keep the complete semantic dependency closure for each literal value.

    Oversized evidence is reported, never truncated. Relations point from a value
    to its row/column header, unit or period; merged headers can chain. Geometric
    same-row/column/order links are preserved if both endpoints are in the bundle,
    but never used to infer semantic links. No cross-page continuation is inferred.
    """
    if max_characters <= 0 or max_cells <= 0:
        raise ValueError("positive chunk budgets required")
    enriched = EvidenceEnvelope.model_validate(enriched)
    if enriched.scope != reviewed.scope:
        raise ValueError("review scope mismatch")
    if enriched.proposal is None:
        return (), ()
    checked = verify_proposal(
        enriched.proposal, enriched.scope, reviewed, allow_synthetic=allow_synthetic
    )
    if checked != enriched.decisions:
        raise ValueError("merge decision mismatch")
    chunks, warnings = [], []
    semantic = {"row_header", "column_header", "unit", "period", "merged_header"}
    for table, decision in zip(enriched.proposal.tables, checked, strict=True):
        if decision.state != "accepted":
            warnings.append("unverified_table_omitted")
            continue
        for value in table.cells:
            if value.role != "value":
                continue
            selected = {value.cell_id}
            while True:
                additions = {
                    r.right for r in table.relations if r.left in selected and r.kind in semantic
                }
                if additions <= selected:
                    break
                selected |= additions
            included = tuple(c for c in table.cells if c.cell_id in selected)
            if len(included) > max_cells or sum(len(c.literal) for c in included) > max_characters:
                warnings.append("complete_evidence_exceeds_budget")
                continue
            relations = tuple(
                r for r in table.relations if r.left in selected and r.right in selected
            )
            evidence_ids = tuple(
                cell_evidence_id(enriched.scope, table.table_id, c) for c in included
            )
            payload = {
                "scope": enriched.scope.model_dump(mode="json"),
                "table_id": table.table_id,
                "section_id": table.section_id,
                "value_cell_id": value.cell_id,
                "evidence_ids": evidence_ids,
                "relations": [r.model_dump(mode="json") for r in relations],
                "review_revision": reviewed.revision,
                "candidate_revision": enriched.proposal.candidate_revision,
                "config_sha256": enriched.proposal.config_sha256,
                "chunker": "table-chunk-2.0",
                "max_characters": max_characters,
                "max_cells": max_cells,
            }
            chunks.append(
                TableChunk(
                    chunk_id=fingerprint(payload),
                    scope=enriched.scope,
                    table_id=table.table_id,
                    section_id=table.section_id,
                    value_cell_id=value.cell_id,
                    cells=included,
                    relations=relations,
                    evidence_ids=evidence_ids,
                    review_revision=reviewed.revision,
                    candidate_revision=enriched.proposal.candidate_revision,
                    config_sha256=enriched.proposal.config_sha256,
                )
            )
    return tuple(chunks), tuple(warnings)


def context_survival(
    chunks: tuple[TableChunk, ...], required: tuple[frozenset[str], ...], *, max_characters: int
) -> dict:
    """Fixed-output diagnostic: only whole bundles enter the context budget."""
    if max_characters <= 0:
        raise ValueError("positive context budget required")
    packed, used = [], 0
    for chunk in chunks:
        size = sum(len(c.literal) for c in chunk.cells)
        if used + size <= max_characters:
            packed.append(frozenset(chunk.evidence_ids))
            used += size
    return {
        "required": len(required),
        "complete_in_chunk": sum(any(r <= set(c.evidence_ids) for c in chunks) for r in required),
        "complete_in_context": sum(any(r <= c for c in packed) for r in required),
        "packed_characters": used,
        "answer_quality": "NOT_EVALUATED",
    }
