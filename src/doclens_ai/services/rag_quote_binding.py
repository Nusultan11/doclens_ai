"""Offline structural experiment. Exact text membership does NOT authorize release.

Callers supply an original authorized EvidenceContext; this module cannot establish
authorization freshness or semantic support. It is deliberately unused by RagService.
"""

from dataclasses import dataclass
from typing import Literal

from doclens_ai.llm.provider import strict_json
from doclens_ai.services.rag import (
    Citation,
    EvidenceContext,
    ModelAnswer,
    ModelCitation,
    validate_citations,
)


@dataclass(frozen=True, slots=True)
class StructuralBindingResult:
    """Diagnostic payload only, never a RagOutcome or production release decision."""

    output: ModelAnswer
    citations: tuple[Citation, ...]

    @property
    def production_authorized(self) -> Literal[False]:
        return False

    @property
    def semantic_support(self) -> Literal["NOT_EVALUATED"]:
        return "NOT_EVALUATED"


def _unique_start(text: str, fragment: str, *, kind: Literal["quote", "answer"]) -> int:
    start = text.find(fragment)
    if start < 0:
        raise ValueError(f"missing exact {kind}")
    # Count overlapping occurrences too: 'aa' appears twice in 'aaa'.
    if text.find(fragment, start + 1) >= 0:
        raise ValueError(f"ambiguous exact {kind}")
    return start


def _packed_pairs(context: EvidenceContext):
    if not isinstance(context, EvidenceContext):
        raise TypeError("original EvidenceContext required")
    pairs = list(zip(context.evidence, context.texts, strict=True))
    if len({item.chunk_id for item, _ in pairs}) != len(pairs):
        raise ValueError("ambiguous context identity")
    records = []
    for item, text in pairs:
        if not isinstance(text, str) or not text.strip() or not item.text.startswith(text):
            raise ValueError("inconsistent packed evidence")
        records.append(
            {
                "chunk_id": str(item.chunk_id),
                "document_id": str(item.document_id),
                "document_version_id": str(item.document_version_id),
                "index_revision_id": str(item.index_revision_id),
                "source_locator": item.locator.model_dump(mode="json", exclude_none=True),
                "text": text,
            }
        )
    try:
        if len(context.messages) != 2 or context.messages[1]["role"] != "user":
            raise ValueError
        packed = strict_json(context.messages[1]["content"])
        if (
            set(packed) != {"question", "evidence"}
            or not isinstance(packed["question"], str)
            or packed["evidence"] != records
        ):
            raise ValueError
    except (ValueError, TypeError, KeyError, IndexError):
        raise ValueError("inconsistent packed context") from None
    return {str(item.chunk_id): (item, text) for item, text in pairs}


def bind_quote_offsets(output: ModelAnswer, context: EvidenceContext) -> StructuralBindingResult:
    """Bind only four offsets per citation; preserve all other model fields exactly.

    Schema-invalid objects, even unchecked model_construct/model_copy instances,
    are rejected before binding. No paraphrase, normalization, quote replacement,
    citation dropping, original-source suffix fallback or semantic inference occurs.
    Multiple citations must EACH contain the complete answer, not complementary
    fragments. All matches use Python Unicode code-point indices, exclusive ends.
    A valid refusal is preserved; invalid refusals are never repaired.
    """
    if not isinstance(output, ModelAnswer):
        raise TypeError("already schema-valid ModelAnswer required")
    # model_dump can hide unchecked extra attributes and emit private-input warnings.
    # Revalidate raw fields instead, including nested objects, without serialization.
    if output.model_extra:
        raise ValueError("schema-invalid ModelAnswer")
    data = vars(output).copy()
    if isinstance(data.get("citations"), list):
        references = []
        for reference in data["citations"]:
            if isinstance(reference, ModelCitation):
                if reference.model_extra:
                    raise ValueError("schema-invalid citation")
                reference = vars(reference).copy()
            references.append(reference)
        data["citations"] = references
    original = ModelAnswer.model_validate(data)
    by_id = _packed_pairs(context)
    payload = original.model_dump()
    if original.answerable:
        for reference, data in zip(original.citations, payload["citations"], strict=True):
            pair = by_id.get(reference.chunk_id)
            if pair is None or reference.document_version_id != str(pair[0].document_version_id):
                raise ValueError("chunk or document-version identity mismatch")
            start = _unique_start(pair[1], reference.quote, kind="quote")
            _unique_start(reference.quote, original.answer, kind="answer")
            data.update(
                quote_start=start,
                quote_end=start + len(reference.quote),
                answer_start=0,
                answer_end=len(original.answer),
            )
    bound = ModelAnswer.model_validate(payload)
    citations = validate_citations(bound, context)
    return StructuralBindingResult(bound, tuple(citations))
