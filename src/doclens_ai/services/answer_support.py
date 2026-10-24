"""Conservative numeric fidelity checks; not a general semantic entailment judge."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from doclens_ai.services.rag import EvidenceContext, ModelAnswer

# Only these bare field labels may be elided. Unknown labels, units in labels,
# conditions, negation and entity descriptions require the complete source text.
_VALUE_LABEL_WORDS = frozenset(
    {
        "synthetic",
        "count",
        "value",
        "net",
        "mass",
        "amount",
        "total",
        "quantity",
        "масса",
        "значение",
        "количество",
        "салмақ",
        "мән",
        "саны",
    }
)


def _fact(text: str) -> str:
    # Whitespace at the edges and one terminal sentence stop are presentation only.
    # No numeric/Unicode/sign/decimal/unit/date normalization or value recomputation.
    return text.strip().removesuffix(".")


def validate_claim_support(output: ModelAnswer, context: EvidenceContext) -> None:
    """Allow number-bearing answers only as one complete, literal source fact.

    Match against the whole authorized chunk, not a model-selected cropped quote.
    Thus a quote cannot hide a sign, unit, period/header or conditional suffix.
    Ambiguous partial/multi-source numeric composition is refused. Supported full
    extractive facts and simple labelled scalar facts retain their original text.
    This establishes numeric fidelity only, never question relevance, global
    unanswerability or arbitrary semantic truth (which still need independent Gold).
    """
    answer = output.answer or ""
    if not output.answerable:
        return
    by_id = {
        str(item.chunk_id): text for item, text in zip(context.evidence, context.texts, strict=True)
    }
    for citation in output.citations:
        claim = answer[citation.answer_start : citation.answer_end]
        # Literal support is necessary even without digits: writing an invented
        # quantity in words must not evade the guard. This does not prove entailment.
        if claim not in citation.quote:
            raise ValueError("non-extractive claim support")
        if not any(c.isnumeric() for c in answer + by_id[citation.chunk_id]):
            continue
        if citation.answer_start != 0 or citation.answer_end != len(answer):
            raise ValueError("partial numeric claim support")
        text = by_id[citation.chunk_id]
        facts = {_fact(text)}
        label, colon, value = text.partition(":")
        if (
            colon
            and label.split()
            and all(word.casefold() in _VALUE_LABEL_WORDS for word in label.split())
        ):
            facts.add(_fact(value))
        if _fact(answer) not in facts or _fact(answer) not in citation.quote:
            raise ValueError("unsupported numeric claim")
