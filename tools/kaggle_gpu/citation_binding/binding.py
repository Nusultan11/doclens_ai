"""Experimental single-span binder; lexical validity is NOT semantic faithfulness."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, model_validator

from doclens_ai.services.rag import EvidenceContext, ModelAnswer, validate_citations


class ExtractiveAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    answerable: StrictBool
    answer: StrictStr | None = Field(max_length=8000)
    chunk_id: StrictStr | None = Field(pattern=r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
    quote: StrictStr | None = Field(max_length=8000)
    reason: Literal["insufficient_evidence"] | None

    @model_validator(mode="after")
    def branches(self):
        if self.answerable:
            if (
                not self.answer
                or not self.answer.strip()
                or not self.quote
                or not self.quote.strip()
                or self.chunk_id is None
                or self.reason is not None
            ):
                raise ValueError("inconsistent extractive answer")
        elif (
            self.answer is not None
            or self.chunk_id is not None
            or self.quote is not None
            or self.reason != "insufficient_evidence"
        ):
            raise ValueError("inconsistent refusal")
        return self


def unique_offset(text: str, fragment: str) -> int:
    start = text.find(fragment)
    # Include overlapping matches: 'aa' in 'aaa' is ambiguous.
    if start < 0:
        raise ValueError("missing exact match")
    if text.find(fragment, start + 1) >= 0:
        raise ValueError("ambiguous exact match")
    return start


def bind(output: ExtractiveAnswer, context: EvidenceContext) -> ModelAnswer:
    """No repairs, normalization, original-text fallback, or semantic inference.

    Context must come from the existing authorized pack_context boundary. Production
    authorization/revalidation is not replaced by this offline experiment.
    """
    # Recheck even a manually constructed Pydantic instance; no unchecked model_copy.
    output = ExtractiveAnswer.model_validate(output.model_dump())
    if not output.answerable:
        result = ModelAnswer(answerable=False, answer=None, citations=[], reason=output.reason)
    else:
        pairs = list(zip(context.evidence, context.texts, strict=True))
        ids = [str(item.chunk_id) for item, _ in pairs]
        if len(set(ids)) != len(ids):
            raise ValueError("ambiguous context identity")
        selected = [(item, text) for item, text in pairs if str(item.chunk_id) == output.chunk_id]
        if len(selected) != 1:
            raise ValueError("unauthorized evidence identity")
        item, text = selected[0]
        start = unique_offset(text, output.quote)
        unique_offset(output.quote, output.answer)
        result = ModelAnswer.model_validate(
            {
                "answerable": True,
                "answer": output.answer,
                "reason": None,
                "citations": [
                    {
                        "chunk_id": output.chunk_id,
                        "document_version_id": str(item.document_version_id),
                        "quote": output.quote,
                        "quote_start": start,
                        "quote_end": start + len(output.quote),
                        "answer_start": 0,
                        "answer_end": len(output.answer),
                    }
                ],
            }
        )
    validate_citations(result, context)
    return result
