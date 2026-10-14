"""Deterministic metadata-only metrics; reference validity != semantic groundedness."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from doclens_ai.evaluation.rag_gold import RagGoldDataset
from doclens_ai.services.rag import RagOutcome


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def output_fingerprint(outcome):
    # Only hash goes into metrics/review identity; the answer/citation text stays in memory.
    value = outcome.response.model_dump(mode="json")
    value.pop("request_id")
    return fingerprint(value)


class OutputReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,127}$")
    dataset_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    experiment_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_status: str = Field(pattern=r"^(reviewed|adjudicated)$")
    answer_correct: StrictBool
    supported_citations: int = Field(ge=0)
    unsupported_claims: int = Field(ge=0)
    total_claims: int = Field(ge=0)


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    question_id: str
    outcome: RagOutcome | None
    latency_ms: float
    failure: bool = False
    failure_kind: str | None = None


def ratio(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": round(numerator / denominator, 12) if denominator else None,
    }


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * p
    low = math.floor(position)
    return round(values[low] + (values[math.ceil(position)] - values[low]) * (position - low), 3)


def evaluate_rag(gold: RagGoldDataset, cases, *, experiment, reviews=()):
    by_id = {case.question_id: case for case in cases}
    if len(by_id) != len(cases) or set(by_id) != {e.question_id for e in gold.examples}:
        raise ValueError("RAG results must match Gold exactly")
    for case in cases:
        if (
            not math.isfinite(case.latency_ms)
            or case.latency_ms < 0
            or case.failure != (case.outcome is None)
            or case.failure_kind not in {None, "model", "retrieval"}
            or (case.failure_kind is not None and not case.failure)
        ):
            raise ValueError("invalid RAG observation")
    experiment_id = fingerprint(experiment)
    if reviews and gold.examples[0].synthetic_fixture:
        raise ValueError("synthetic fixtures must not claim human quality review")
    reviewed = {}
    for review in reviews:
        case = by_id.get(review.question_id)
        if (
            review.question_id in reviewed
            or case is None
            or case.outcome is None
            or review.dataset_fingerprint != gold.fingerprint
            or review.experiment_fingerprint != experiment_id
            or review.output_fingerprint != output_fingerprint(case.outcome)
            or review.supported_citations > len(case.outcome.response.citations)
            or review.unsupported_claims > review.total_claims
        ):
            raise ValueError("review not bound to this RAG output/experiment")
        reviewed[review.question_id] = review
    tp = fp = fn = tn = correct = citations = empty = invalid = matched = required = 0
    outputs, reasons = [], {}
    for example in gold.examples:
        case = by_id[example.question_id]
        required += len(example.required_citation_refs)
        if case.outcome is None:
            outputs.append((example.question_id, "failure"))
            continue  # Failure is NOT a successful abstention or a true negative.
        outcome, response = case.outcome, case.outcome.response
        outputs.append((example.question_id, output_fingerprint(outcome)))
        empty += outcome.retrieved_count == 0
        invalid += outcome.invalid_output
        if response.reason is not None:
            reasons[response.reason] = reasons.get(response.reason, 0) + 1
        if response.answerable:
            tp += example.answerable
            fp += not example.answerable
        else:
            fn += example.answerable
            tn += not example.answerable
        references = example.accepted_answers or (
            [example.reference_answer] if example.reference_answer else []
        )
        normalize = lambda value: " ".join(value.split()).casefold()  # noqa: E731
        correct += (
            response.answerable
            and example.answerable
            and normalize(response.answer) in {normalize(value) for value in references}
        ) or (not response.answerable and not example.answerable)
        citations += len(response.citations)
        # Locator/range/exact quote anchor coverage, NOT a judgment of claim meaning.
        for anchor in example.evidence:
            if anchor.evidence_id not in example.required_citation_refs:
                continue
            found = False
            for item in outcome.cited_evidence:
                if (
                    item.source_sha256 != anchor.document_sha256
                    or item.locator.document_format != anchor.document_format
                ):
                    continue
                if not any(
                    all(
                        span.source.model_dump(exclude_none=True).get(k) == v
                        for k, v in anchor.locator.model_dump(exclude_none=True).items()
                    )
                    and span.source_start
                    <= anchor.source_start
                    < anchor.source_end
                    <= span.source_end
                    for span in item.locator.spans
                ):
                    continue
                if any(
                    c.chunk_id == str(item.chunk_id) and anchor.verified_quote in c.quote
                    for c in response.citations
                ):
                    found = True
            matched += found
    successful = sum(case.outcome is not None for case in cases)
    review_citations = sum(len(by_id[q].outcome.response.citations) for q in reviewed)
    quality = {
        "status": "reviewed_subset" if reviewed else "NOT EVALUATED",
        "reviewed_output_count": len(reviewed),
        "answer_correctness": ratio(
            sum(r.answer_correct for r in reviewed.values()), len(reviewed)
        ),
        "citation_source_support": ratio(
            sum(r.supported_citations for r in reviewed.values()), review_citations
        ),
        "unsupported_claim_rate": ratio(
            sum(r.unsupported_claims for r in reviewed.values()),
            sum(r.total_claims for r in reviewed.values()),
        ),
    }
    return {
        "schema_version": "rag-metrics-1.0",
        "evaluation_basis": "synthetic_fixture_only"
        if gold.examples[0].synthetic_fixture
        else "reviewed_answer_gold",
        "dataset_revision": gold.examples[0].dataset_revision,
        "gold_fingerprint": gold.fingerprint,
        "experiment": experiment,
        "experiment_fingerprint": experiment_id,
        "results_fingerprint": fingerprint(sorted(outputs)),
        "query_count": len(cases),
        "successful_response_count": successful,
        "dependency_failure_rate": ratio(len(cases) - successful, len(cases)),
        "model_failure_rate": ratio(sum(c.failure_kind == "model" for c in cases), len(cases)),
        "retrieval_failure_rate": ratio(
            sum(c.failure_kind == "retrieval" for c in cases), len(cases)
        ),
        "normalized_exact_answer_match": ratio(correct, successful),
        "delivered_citation_reference_validity": ratio(citations, citations),
        "delivered_evidence_quote_validity": ratio(citations, citations),
        "required_anchor_coverage": ratio(matched, required),
        "answerability_precision": ratio(tp, tp + fp),
        "answerability_recall": ratio(tp, tp + fn),
        "refusal_precision": ratio(tn, tn + fn),
        "refusal_recall": ratio(tn, tn + fp),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "retrieval_empty_count": empty,
        "refusal_counts": reasons,
        "rejected_model_output_count": invalid,
        "human_quality": quality,
        "latency_ms": {
            "p50": percentile([c.latency_ms for c in cases], 0.5),
            "p95": percentile([c.latency_ms for c in cases], 0.95),
        },
        "latency_policy": "linear interpolation; failures included; startup excluded; no warmup",
        "language_counts": {
            language: sum(e.language == language for e in gold.examples)
            for language in sorted({e.language for e in gold.examples})
        },
    }
