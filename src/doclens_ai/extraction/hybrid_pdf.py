"""Offline native-first merge boundary; deliberately absent from production routing."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pypdf import PdfReader

from doclens_ai.extraction.evidence_v2 import (
    Contract,
    EvidenceEnvelope,
    Page,
    Proposal,
    ReviewedDocument,
    Scope,
    envelope,
)
from doclens_ai.extraction.models import ExtractionResult
from doclens_ai.extraction.parsers import extract_file


class CandidateOutcome(Contract):
    status: Literal["success", "needs_review", "failed", "unknown"]
    failure: (
        Literal[
            "unavailable",
            "timeout",
            "memory_limit",
            "output_limit",
            "worker_failed",
            "invalid_output",
            "source_mismatch",
            "cleanup_failed",
        ]
        | None
    )
    proposal: Proposal | None


def merge_native(
    native: ExtractionResult,
    scope: Scope,
    *,
    outcome: CandidateOutcome | None = None,
    reviewed: ReviewedDocument | None = None,
    enabled: bool = False,
    parser_revision: str = "pypdf-v1",
    allow_synthetic: bool = False,
) -> EvidenceEnvelope:
    """Consume a bounded capture. Never execute an engine in the worker process.

    Accepted evidence is supplemental. The exact v1 snapshot is always retained,
    including failures and warnings. No v2-to-v1 table conversion is provided.
    """
    if not enabled:
        return envelope(native, scope, parser_revision=parser_revision)
    warnings = ()
    proposal = None
    if outcome is None:
        warnings = ("candidate_unavailable",)
    else:
        try:
            outcome = CandidateOutcome.model_validate(outcome)
            if outcome.failure or outcome.status in {"failed", "unknown"}:
                warnings = ("candidate_" + (outcome.failure or "unavailable"),)
            else:
                proposal = outcome.proposal
                if proposal is None:
                    warnings = ("candidate_invalid_output",)
        except ValueError:
            warnings = ("candidate_invalid_output",)
    return envelope(
        native,
        scope,
        parser_revision=parser_revision,
        proposal=proposal,
        reviewed=reviewed,
        warnings=warnings,
        allow_synthetic=allow_synthetic,
    )


def hybrid_pdf(
    path: Path,
    scope: Scope,
    *,
    outcome: CandidateOutcome | None = None,
    reviewed: ReviewedDocument | None = None,
    enabled: bool = False,
    allow_synthetic: bool = False,
) -> EvidenceEnvelope:
    """Local entrypoint checks actual original page identities before accepting review."""
    native = extract_file(path)
    if enabled and reviewed is not None:
        try:
            reader = PdfReader(path)
            actual = tuple(
                Page(
                    number=i + 1,
                    media_box=tuple(map(float, p.mediabox)),
                    crop_box=tuple(map(float, p.cropbox)),
                    rotation=p.rotation,
                )
                for i, p in enumerate(reader.pages)
            )
            if actual != reviewed.pages:
                reviewed = None
        except Exception:  # noqa: BLE001 - malformed candidate metadata preserves native
            reviewed = None
    return merge_native(
        native,
        scope,
        outcome=outcome,
        reviewed=reviewed,
        enabled=enabled,
        allow_synthetic=allow_synthetic,
    )
