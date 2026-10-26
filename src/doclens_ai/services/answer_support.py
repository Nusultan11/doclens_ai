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
# Known grammar/field words may be uppercased as natural language. Other acronyms,
# mixed-case symbols and explicitly labelled identifiers remain opaque.
_LINGUISTIC_WORDS = (
    _SCALAR_LABEL_WORDS
    | {
        "the",
        "of",
        "in",
        "unit",
        "units",
        "id",
        "identifier",
        "идентификатор",
        "export",
        "import",
        "state",
        "status",
        "power",
        "torque",
        "password",
        "access",
        "code",
        "экспорт",
        "импорт",
        "экспортқа",
        "импортқа",
    }
    | {word for phrase in _PERMISSIONS for word in phrase.split()}
)
_PERMISSION_PATTERN = "|".join(
    r"\s+".join(re.escape(word) for word in p.split())
    for p in sorted(_PERMISSIONS, key=len, reverse=True)
)
_PERMISSION_VALUE = re.compile(
    rf"(?P<predicate>{_PERMISSION_PATTERN})(?:\s+(?P<qualifier>.+))?", re.IGNORECASE
)
_BOOLEAN_QUESTION = re.compile(
    rf"(?P<copula>is|are|was|were)\s+(?P<subject>.+?)\s+"
    rf"(?P<value>(?:{_PERMISSION_PATTERN})(?:\s+.+)?)",
    re.IGNORECASE,
)
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
# A bounded positive scalar grammar, not a converter or arbitrary formula
# interpreter. Spelling/signs/precision/symbols are always compared literally.
_UNIT = (
    r"(?:(?:da|[QRYZEPTGMkhdcmµμunpfazyrq])?"
    r"(?:mol|kat|Wb|Hz|Pa|lm|lx|Bq|Gy|Sv|cd|rad|sr|m|g|s|A|K|N|J|W|C|V|F|Ω|S|T|H)"
    r"|%|°C|°F|L|l|min|h|d|кг|мг|г|т|м|см|мм|с|Вт|мВт|МВт)"
)
_QUANTITY = (
    r"[+−-]?[0-9]+(?:[.,][0-9]+)?(?:[eE][+-]?[0-9]+)?"
    rf"(?:\s*{_UNIT})?"
)
_QUANTITY_VALUE = re.compile(_QUANTITY)
_QUALIFIED_QUANTITY = re.compile(rf"(?P<value>{_QUANTITY})\s+(?P<scope>.+)")
_TEMPORAL_SUBJECT = re.compile(rf"(?P<subject>.+?)\s+(?P<scope>(?i:{_TEMPORAL_SCOPE.pattern}))")
SupportMode = Literal["quotation", "value", "scoped"]


@dataclass(frozen=True, slots=True)
class _Fact:
    subject: str
    value: str
    field: bool = False
    tense: Literal["past", "present"] | None = None


def _identity(text: str) -> str:
    # Only subjects/field labels use this key. Never apply it to fact values,
    # qualifiers or quantities. Entity tails and explicitly labelled IDs are raw.
    text = text.strip()
    entity = False

    def linguistic(match: re.Match[str]) -> str:
        nonlocal entity
        word = match[0]
        # Capitalization shape cannot distinguish a word from a symbol (Nm,
        # Nmm, Mmol). Unknown case aliases must not establish symbol equality.
        ordinary = word.casefold() in _LINGUISTIC_WORDS
        result = word.casefold() if not entity and ordinary else word
        entity = entity or word.casefold() in {
            "of",
            "in",
            "unit",
            "units",
            "id",
            "identifier",
            "идентификатор",
        }
        return result

    return re.sub(r"\S+", linguistic, text).removeprefix("the ")


def _tense(copula: str | None) -> Literal["past", "present"] | None:
    if copula is None:
        return None
    return "past" if copula.casefold() in {"was", "were"} else "present"


def _permission(value: str) -> tuple[str, str] | None:
    if match := _PERMISSION_VALUE.fullmatch(value):
        predicate = " ".join(match["predicate"].casefold().split())
        # Unicode IGNORECASE has aliases whose casefold is not a known word.
        # They cannot acquire a meaning or escape the refusal path via KeyError.
        if meaning := _PERMISSIONS.get(predicate):
            return meaning, match["qualifier"] or ""
    return None


def _boolean_question(question: str) -> tuple[str, str, str | None] | None:
    if match := _BOOLEAN_QUESTION.fullmatch(question):
        return _identity(match["subject"]), match["value"], match["copula"]
    for phrase in _PERMISSIONS:
        match = re.fullmatch(rf"{re.escape(phrase)} ли (.+)", question, re.IGNORECASE)
        if match:
            return _identity(match[1]), phrase, None
        for particle in ("ба", "бе", "ма", "ме", "па", "пе"):
            match = re.fullmatch(rf"(.+) {re.escape(phrase)} {particle}", question, re.IGNORECASE)
            if match:
                return _identity(match[1]), phrase, None
    return None


def _subject_scope(subject: str) -> tuple[str, str] | None:
    if match := _TEMPORAL_SUBJECT.fullmatch(subject):
        # At most one explicit temporal relation. A neighboring period cannot
        # become part of an opaque property and then inherit the last period.
        if _TEMPORAL_SCOPE.search(match["subject"]) is None:
            return _identity(match["subject"]), match["scope"]
    return None


def _qualified_value(value: str) -> tuple[str, str] | None:
    if permission := _permission(value):
        if permission[1]:
            return permission
    elif match := _QUALIFIED_QUANTITY.fullmatch(value):
        return match["value"], match["scope"]
    return None


def _period_key(scope: str) -> str | None:
    # Case/spacing equivalence is grammatical here, after full period validation;
    # no quantities, entity names or unknown trailing clauses enter this key.
    if _TEMPORAL_SCOPE.fullmatch(scope):
        return " ".join(scope.split()).casefold()
    return None


def _temporal_fact(fact: _Fact) -> tuple[str, str, str] | None:
    if subject := _subject_scope(fact.subject):
        permission = _permission(fact.value)
        period = _period_key(subject[1])
        if period and (_QUANTITY_VALUE.fullmatch(fact.value) or (permission and not permission[1])):
            return subject[0], permission[0] if permission else fact.value, period
    elif qualified := _qualified_value(fact.value):
        if period := _period_key(qualified[1]):
            return fact.subject, qualified[0], period
    return None


def _requested_period(question: str) -> tuple[str, str] | None:
    question = question.strip().removesuffix("?").removesuffix(".")
    if boolean := _boolean_question(question):
        subject, value, _ = boolean
        permission = _permission(value)
        if permission and (period := _period_key(permission[1])):
            return subject, period
        if scoped := _subject_scope(subject):
            if period := _period_key(scoped[1]):
                return scoped[0], period
        return None
    match = _OPEN_QUESTION.fullmatch(question)
    if subject := _subject_scope(match["topic"] if match else question):
        if period := _period_key(subject[1]):
            return subject[0], period
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


def _counterpart_subject(text: str) -> str | None:
    # An explicit relation with an unparseable value is still a possible
    # contradiction. This key can only cause refusal, never establish support.
    subject, colon, _ = _fact(text).partition(":")
    if not colon:
        match = _COPULA.fullmatch(_fact(text))
        if match is None:
            return None
        subject = match[1]
    if "\n" in subject or re.search(r"[!?;]|\.\s+\w", subject):
        return None
    return _identity(subject)


def _bare_label(subject: str, words: frozenset[str]) -> bool:
    return bool(subject.split()) and all(word in words for word in subject.split())


def _question_mode(question: str, fact: _Fact | None) -> SupportMode | None:
    question = question.strip().removesuffix("?").removesuffix(".")
    if _QUOTATION_QUESTION.fullmatch(question):
        return "quotation"
    if fact is None:
        return None
    if question.casefold() in {"value", "значение", "мән"} and fact.field:
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
        if requested := _requested_period(question):
            bound = _temporal_fact(fact)
            return "scoped" if bound and (bound[0], bound[2]) == requested else None
        if _TEMPORAL_SCOPE.search(topic):
            return None  # Recognizable but ambiguous temporal subject.
        if match is not None and _tense(match["copula"]) == "past" and fact.tense is None:
            return None  # An undated field/headline does not establish a past state.
        return "scoped"
    if topic.startswith(fact.subject + " "):
        scope = topic[len(fact.subject) :].strip()
        needs_period = (
            match is not None and _tense(match["copula"]) == "past" and fact.tense is None
        )
        if _SCOPE_PREFIX.fullmatch(scope):
            if period := _period_key(scope):
                bound = _temporal_fact(fact)
                return (
                    "scoped" if bound and bound[0] == fact.subject and bound[2] == period else None
                )
            if _TEMPORAL_SCOPE.search(scope):
                return None  # Failed temporal parsing cannot become a generic condition.
            qualified = _qualified_value(fact.value)
            if not needs_period and qualified and qualified[1] == scope:
                return "scoped"
    permission = _permission(fact.value)
    if permission is None:
        return None
    # Closed boolean grammar; keep every additional qualifier in the question.
    if boolean := _boolean_question(question):
        subject, value, copula = boolean
        if subject == fact.subject and (
            fact.tense is None
            or _tense(copula) == fact.tense
            or (
                copula is None
                and (fact.tense == "present" or _requested_period(question) is not None)
            )
        ):
            asked = _permission(value)
            if (
                asked is not None
                and (not asked[1] or asked[1] == permission[1])
                and (
                    fact.tense is not None
                    or _tense(copula) != "past"
                    or _TEMPORAL_SCOPE.fullmatch(asked[1])
                )
            ):
                if requested := _requested_period(question):
                    bound = _temporal_fact(fact)
                    return "scoped" if bound and (bound[0], bound[2]) == requested else None
                if _TEMPORAL_SCOPE.search(subject) or _TEMPORAL_SCOPE.search(asked[1]):
                    return None
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
            requested = _requested_period(question)
            bound = _temporal_fact(fact) if requested else None
            for other_text in context.texts:
                other = _source_fact(other_text)
                if requested:
                    subject = other.subject if other else _counterpart_subject(other_text)
                    subject_scope = _subject_scope(subject) if subject else None
                    key = subject_scope[0] if subject_scope else subject
                    if key == requested[0]:
                        other_bound = _temporal_fact(other) if other else None
                        if other_bound is None or bound is None:
                            raise ValueError("unresolved temporal counterpart")
                        if other_bound[2] == requested[1] and other_bound[1] != bound[1]:
                            raise ValueError("conflicting temporal facts")
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
