from __future__ import annotations

import json
from dataclasses import replace

import pytest

from doclens_ai.evaluation.rag_gold import RagGoldExample, load_rag_gold, validate_rag_gold
from doclens_ai.evaluation.rag_metrics import EvaluationCase, OutputReview, evaluate_rag, percentile
from doclens_ai.rag_eval import (
    SyntheticGenerator,
    SyntheticRetrieval,
    run_cases,
    synthetic_gold,
)
from doclens_ai.services.rag import RagService
from tests.unit.test_rag import settings


def test_synthetic_contract_and_private_loader(tmp_path):
    gold = synthetic_gold()
    assert len(gold.examples) == 4
    path = tmp_path / "private.jsonl"
    path.write_text("\n".join(e.model_dump_json() for e in gold.examples), encoding="utf-8")
    loaded = load_rag_gold(path)
    assert loaded.fingerprint == gold.fingerprint
    assert validate_rag_gold(tuple(reversed(loaded.examples))).fingerprint == loaded.fingerprint


@pytest.mark.parametrize(
    "mutation",
    [
        "draft",
        "false_review",
        "no_answers",
        "no_evidence",
        "unknown_ref",
        "duplicate_ref",
        "unknown_field",
        "type",
        "wrong_format",
        "bad_sha",
        "negative_answer",
        "mixed_revision",
        "family_split",
        "source_family",
        "duplicate_question",
        "unapproved_real",
    ],
)
def test_strict_gold_rejects_unsupported_labels(mutation):
    gold = synthetic_gold()
    data = gold.examples[0].model_dump(mode="json")
    others = list(gold.examples[1:])
    if mutation == "draft":
        data.update(
            synthetic_fixture=False,
            dataset_revision="corpus-v1-rag-gold-v1",
            reviewer_status="draft",
            reviewer_count=1,
        )
    elif mutation == "false_review":
        data.update(reviewer_status="reviewed", reviewer_count=1)
    elif mutation == "no_answers":
        data["accepted_answers"] = []
    elif mutation == "no_evidence":
        data["evidence"] = []
    elif mutation == "unknown_ref":
        data["required_citation_refs"] = ["nonexistent-ref"]
    elif mutation == "duplicate_ref":
        data["required_citation_refs"] *= 2
    elif mutation == "unknown_field":
        data["confidence"] = 0.99
    elif mutation == "type":
        data["answerable"] = "true"
    elif mutation == "wrong_format":
        data["evidence"][0]["document_format"] = "xlsx"
    elif mutation == "bad_sha":
        data["source_document_sha256"] = ["not-sha"]
    elif mutation == "negative_answer":
        data["answerable"] = False
    elif mutation == "mixed_revision":
        data.update(
            synthetic_fixture=False,
            dataset_revision="corpus-v1-rag-gold-v1",
            reviewer_status="reviewed",
            reviewer_count=1,
        )
    elif mutation == "family_split":
        data["split"] = "test"
    elif mutation == "source_family":
        data["document_family_id"] = "other-family"
    elif mutation == "duplicate_question":
        others.append(gold.examples[0])
    elif mutation == "unapproved_real":
        data.update(
            synthetic_fixture=False,
            dataset_revision="corpus-v1-rag-gold-v1",
            reviewer_status="reviewed",
            reviewer_count=1,
        )
        others = []
    with pytest.raises(ValueError):
        first = RagGoldExample.model_validate(data)
        validate_rag_gold([first, *others])


@pytest.mark.anyio
async def test_deterministic_metrics_are_sanitized_and_not_human_groundedness():
    from uuid import UUID

    gold = synthetic_gold()
    service = RagService(SyntheticRetrieval(), SyntheticGenerator(), settings())
    cases = await run_cases(gold, service, UUID(int=5), UUID(int=6))
    fixed = [replace(c, latency_ms=index * 10) for index, c in enumerate(cases)]
    report = evaluate_rag(gold, fixed, experiment={"provider": "synthetic-only"})
    again = await run_cases(gold, service, UUID(int=5), UUID(int=6))
    repeat = evaluate_rag(
        gold,
        [replace(c, latency_ms=i * 10) for i, c in enumerate(again)],
        experiment={"provider": "synthetic-only"},
    )
    assert report == repeat
    assert report["normalized_exact_answer_match"] == {
        "numerator": 4,
        "denominator": 4,
        "value": 1.0,
    }
    assert report["required_anchor_coverage"]["value"] == 1
    assert report["rejected_model_output_count"] == 1
    assert report["retrieval_empty_count"] == 1
    assert report["refusal_counts"] == {"insufficient_evidence": 2, "no_relevant_context": 1}
    assert report["latency_ms"] == {"p50": 15.0, "p95": 28.5}
    assert report["human_quality"]["status"] == "NOT EVALUATED"
    assert report["human_quality"]["unsupported_claim_rate"]["value"] is None
    rendered = json.dumps(report)
    for private in (
        "Synthetic count?",
        "Synthetic count: 7",
        '"answer"',
        '"quote"',
        '"question"',
        "source_locator",
        "sheet_name",
        "filename",
        "endpoint",
    ):
        assert private not in rendered
    failed = [EvaluationCase(cases[0].question_id, None, 5, True), *cases[1:]]
    metrics = evaluate_rag(gold, failed, experiment={})
    assert metrics["dependency_failure_rate"]["value"] == 0.25
    assert metrics["confusion"] == {"tp": 0, "fp": 0, "fn": 0, "tn": 3}
    assert metrics["answerability_recall"]["value"] is None
    with pytest.raises(ValueError):
        evaluate_rag(gold, cases[:-1], experiment={})
    with pytest.raises(ValueError):
        evaluate_rag(gold, [replace(cases[0], latency_ms=float("nan")), *cases[1:]], experiment={})
    review = OutputReview(
        question_id=cases[0].question_id,
        dataset_fingerprint="b" * 64,
        experiment_fingerprint="c" * 64,
        output_fingerprint="d" * 64,
        reviewer_status="reviewed",
        answer_correct=True,
        supported_citations=1,
        unsupported_claims=0,
        total_claims=1,
    )
    with pytest.raises(ValueError):
        evaluate_rag(gold, cases, experiment={}, reviews=[review])
    assert percentile([], 0.5) is None and percentile([1], 0.95) == 1
