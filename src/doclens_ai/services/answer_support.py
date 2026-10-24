"""Bounded source-qualified support rules, never a general semantic entailment judge.

Only complete quotations, explicit scalar fields and a small declarative/question
grammar are verifiable here. Unknown language/constructions fail closed. This is
a positive grammar, not an instruction blacklist or an LLM correctness judgment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

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

_SCALAR_LABEL_WORDS = _VALUE_LABEL_WORDS | {"name", "имя", "атауы"}
# Closed equivalences for permission predicates only. Qualifiers must remain
# identical; synonyms never remove a condition, subject, period, number or unit.
_PERMISSIONS = {
    "allowed": "allow",
    "permitted": "allow",
    "not allowed": "deny",
    "not permitted": "deny",
    "forbidden": "deny",
    "prohibited": "deny",
    "разрешён": "allow",
    "разрешен": "allow",
    "разрешено": "allow",
    "не разрешён": "deny",
    "не разрешен": "deny",
    "не разрешено": "deny",
    "запрещён": "deny",
    "запрещен": "deny",
    "запрещено": "deny",
    "рұқсат бар": "allow",
    "рұқсат етілген": "allow",
    "рұқсат жоқ": "deny",
    "рұқсат етілмеген": "deny",
    "тыйым салынған": "deny",
}
_COPULA = re.compile(r"(.+?)\s+(is|are|was|were)\s+(.+)", re.IGNORECASE)
_OPEN_QUESTION = re.compile(
    r"(?:(?:what|which) (?P<copula>is|are|was|were) (?:the )?|"
    r"как(?:ова|ово|ов|овы) )(?P<topic>.+)",
    re.IGNORECASE,
)
_QUOTATION_QUESTION = re.compile(
    r"(?:what does (?:the )?(?:source|evidence|document) (?:say|state)|"
    r"quote (?:the )?(?:source|evidence|document))",
    re.IGNORECASE,
)
_SCOPE_PREFIX = re.compile(r"(?:for|in|during|as of|за|в|на)\s+.+", re.IGNORECASE)
_TEMPORAL_SCOPE = re.compile(
    r"(?:for|in|during|as of|за|в|на) (?:"
    r"[0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?(?: (?:год|года|году|жыл|жылы|жылға))?|"
    r"q[1-4] [0-9]{4}|"
    r"(?:january|february|march|april|may|june|july|august|september|october|november|"
    r"december) [0-9]{4})",
    re.IGNORECASE,
)
SupportMode = Literal["quotation", "value", "scoped"]


@dataclass(frozen=True, slots=True)
class _Fact:
    subject: str
    value: str
    field: bool = False
    tense: Literal["past", "present"] | None = None


def _identity(text: str) -> str:
    # Used only for grammatical subjects/questions, never numeric fact matching.
    # Keep digit-bearing and explicitly labelled identifiers case-sensitive.
    words = text.split()
    return " ".join(
        word
        if any(c.isnumeric() for c in word)
        or (i and words[i - 1].casefold() in {"id", "identifier", "идентификатор"})
        else word.casefold()
        for i, word in enumerate(words)
    ).removeprefix("the ")


def _tense(copula: str | None) -> Literal["past", "present"] | None:
    if copula is None:
        return None
    return "past" if copula.casefold() in {"was", "were"} else "present"


def _permission(value: str) -> tuple[str, str] | None:
    value = _identity(value)
    for phrase in sorted(_PERMISSIONS, key=len, reverse=True):
        if value == phrase or value.startswith(phrase + " "):
            return _PERMISSIONS[phrase], value[len(phrase) :].strip()
    return None


def _source_fact(text: str) -> _Fact | None:
    text = _fact(text)
    # No sentence/row selection: an omitted sibling clause may own the condition.
    if "\n" in text or re.search(r"[!?;]|\.\s+\w", text):
        return None
    subject, colon, value = text.partition(":")
    if colon and subject.strip() and value.strip():
        return _Fact(_identity(subject), value.strip(), True)
    if match := _COPULA.fullmatch(text):
        return _Fact(_identity(match[1]), match[3].strip(), tense=_tense(match[2]))
    # Russian/Kazakh zero-copula permission clauses. The complete subject must
    # bind to the question; a verb embedded in an instruction is not a subject hit.
    normalized = _identity(text)
    for phrase in sorted(_PERMISSIONS, key=len, reverse=True):
        if normalized.endswith(" " + phrase):
            return _Fact(normalized[: -len(phrase)].strip(), phrase)
    return None


def _bare_label(subject: str, words: frozenset[str]) -> bool:
    return bool(subject.split()) and all(word in words for word in subject.split())


def _question_mode(question: str, fact: _Fact | None) -> SupportMode | None:
    question = _identity(question.strip().removesuffix("?").removesuffix("."))
    if _QUOTATION_QUESTION.fullmatch(question):
        return "quotation"
    if fact is None:
        return None
    if question in {"value", "значение", "мән"} and fact.field:
        return "value"
    # Explicit label queries and open fact questions bind the complete subject.
    match = _OPEN_QUESTION.fullmatch(question)
    if match is not None:
        if fact.tense is not None and _tense(match["copula"]) != fact.tense:
            return None
        topic = match["topic"]
    else:
        topic = question
    topic = _identity(topic)
    if topic == fact.subject and (match is not None or fact.tense != "past"):
        if match is not None and _tense(match["copula"]) == "past" and fact.tense is None:
            return None  # An undated field/headline does not establish a past state.
        return "scoped"
    if topic.startswith(fact.subject + " "):
        scope = topic[len(fact.subject) :].strip()
        needs_period = (
            match is not None and _tense(match["copula"]) == "past" and fact.tense is None
        )
        if (
            _SCOPE_PREFIX.fullmatch(scope)
            and (not needs_period or _TEMPORAL_SCOPE.fullmatch(scope))
            and _identity(fact.value).endswith(" " + scope)
        ):
            return "scoped"
    permission = _permission(fact.value)
    if permission is None:
        return None
    # Closed boolean grammar; keep every additional qualifier in the question.
    for copula in ("is", "are", "was", "were"):
        prefix = f"{copula} {fact.subject} "
        if question.startswith(prefix) and (fact.tense is None or _tense(copula) == fact.tense):
            asked = _permission(question[len(prefix) :])
            if (
                asked is not None
                and (not asked[1] or asked[1] == permission[1])
                and (
                    fact.tense is not None
                    or _tense(copula) != "past"
                    or _TEMPORAL_SCOPE.fullmatch(asked[1])
                )
            ):
                return "scoped"
    for phrase in _PERMISSIONS:
        if question == f"{phrase} ли {fact.subject}":
            return "scoped"
        for particle in ("ба", "бе", "ма", "ме", "па", "пе"):
            if question == f"{fact.subject} {phrase} {particle}":
                return "scoped"
    return None


def _supported(answer: str, text: str, fact: _Fact | None, mode: SupportMode) -> bool:
    if _fact(answer) == _fact(text):
        return True
    if fact is None or mode == "quotation":
        return False
    # Subject elision needs either a question binding it or an explicitly bare
    # scalar field. A quotation request cannot reinterpret arbitrary instructions.
    if mode == "scoped" or (fact.field and _bare_label(fact.subject, _SCALAR_LABEL_WORDS)):
        if _fact(answer) == fact.value:
            return True
        if mode == "scoped" and (meaning := _permission(fact.value)):
            if _permission(_fact(answer)) == meaning:
                return True
            proposed = _source_fact(answer)
            if proposed is not None:
                if proposed.subject != fact.subject or (
                    proposed.tense is not None and proposed.tense != fact.tense
                ):
                    return False
                return _permission(proposed.value) == meaning
    return False


def _fact(text: str) -> str:
    # Whitespace at the edges and one terminal sentence stop are presentation only.
    # No numeric/Unicode/sign/decimal/unit/date normalization or value recomputation.
    return text.strip().removesuffix(".")


def validate_claim_support(
    output: ModelAnswer,
    context: EvidenceContext,
    *,
    question: str,
) -> None:
    """Require a complete source-qualified fact bound to the trusted request.

    Citation identities/offsets are validated by the existing provenance boundary
    first. Do not derive the question, subject or scope from model-supplied fields.
    Unknown support is refused, while the caller still revalidates every source's
    ACL/ACTIVE state. These bounded rules do not establish universal entailment.
    """
    answer = output.answer or ""
    if not output.answerable:
        return
    by_id = {
        str(item.chunk_id): text for item, text in zip(context.evidence, context.texts, strict=True)
    }
    for citation in output.citations:
        text = by_id[citation.chunk_id]
        if citation.answer_start != 0 or citation.answer_end != len(answer):
            raise ValueError("partial claim support")
        if citation.quote != text:
            raise ValueError("incomplete source quote")
        fact = _source_fact(text)
        mode = _question_mode(question, fact)
        if mode is None or not _supported(answer, text, fact, mode):
            raise ValueError("unsupported source-qualified claim")
        if mode != "quotation" and fact is not None:
            meaning = _permission(fact.value) or fact.value
            for other_text in context.texts:
                other = _source_fact(other_text)
                if (
                    mode == "scoped"
                    and _permission(fact.value) is not None
                    and other is not None
                    and other.subject == fact.subject
                    and _permission(other.value) is None
                ):
                    raise ValueError("unresolved source-qualified counterpart")
                if (
                    other is not None
                    and other.subject == fact.subject
                    and _question_mode(question, other) == mode
                    and (_permission(other.value) or other.value) != meaning
                ):
                    raise ValueError("conflicting source-qualified facts")
        if not any(c.isnumeric() for c in answer + text):
            continue
        # Preserve the earlier exact numeric guard, including signs, units and
        # precision. A grammatical paraphrase never bypasses numeric fidelity.
        if answer not in citation.quote:
            raise ValueError("non-extractive numeric claim")
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
