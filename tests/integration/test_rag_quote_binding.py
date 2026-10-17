"""Offline opt-in replay of one frozen DEV packet; never runs inference/retrieval."""

import base64
import hashlib
import json
import os
import runpy
from collections import Counter
from pathlib import Path
from uuid import UUID

import pytest

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.llm.provider import strict_json
from doclens_ai.services.rag import EvidenceContext, validate_citations
from doclens_ai.services.rag_quote_binding import bind_quote_offsets
from doclens_ai.services.retrieval import SourceLocator, VerifiedResult

ROOT = Path(__file__).resolve().parents[2]
PACKET_SHA256 = "2392acbf710bb336670aff2f83131424451536009c61e394ae7ef8078f13da93"


def packet_context(record):
    messages = record["raw_capture"]["request"]["messages"]
    packed = strict_json(messages[1]["content"])["evidence"]
    assert packed == record["packed_evidence"]
    # Export preserves packed metadata/text, not workspace/source-SHA mappings.
    # These unused internal placeholders do not assert live authorization or Gold source identity.
    hits = tuple(
        VerifiedResult(
            **{
                k: UUID(h[k])
                for k in ("chunk_id", "document_id", "document_version_id", "index_revision_id")
            },
            workspace_id=UUID(int=0),
            source_sha256="",
            score=0.0,
            text=h["text"],
            locator=SourceLocator.model_validate(h["source_locator"]),
        )
        for h in packed
    )
    return EvidenceContext(hits, tuple(h.text for h in hits), messages)


async def evaluate_packet(packet, prior_review):
    runner = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py"))
    assert len(packet) == len({p["question_id"] for p in packet}) == 15
    assert all(p["gold_reference_local_only"]["split"] == "dev" for p in packet)
    assert sum(p["gold_reference_local_only"]["answerable"] for p in packet) == 12
    assert prior_review["source_packet_sha256"] == PACKET_SHA256
    verdicts = prior_review["verdicts"]
    assert set(verdicts) == {p["question_id"] for p in packet}
    assert Counter(verdicts.values()) == {
        "CORRECT": 12,
        "UNSUPPORTED_ASSERTION": 1,
        "SEMANTIC_ABSTENTION_INVALID_CONTRACT": 1,
        "INCORRECT_QUESTION_ANSWER": 1,
    }
    assert prior_review["human_review_status"] == "NOT_EVALUATED"
    assert prior_review["operator_confirmation_status"] == "NOT_CONFIRMED"
    settings = RagSettings(
        _env_file=None,
        endpoint=runner["configuration"]()["endpoint"],
        model_id=runner["MODEL_ALIAS"],
        max_output_tokens=1024,
        timeout_seconds=120,
    )
    original, classifications, reasons = Counter(), Counter(), Counter()
    rows, elapsed = [], []
    citation_count = bound_positive = bound_unsafe = refusals = 0
    import time

    for p in packet:
        record = p["raw_capture"]
        assert p["gold_fingerprint"] == runner["GOLD_FINGERPRINT"]
        assert (verdicts[p["question_id"]] == "CORRECT") == p["gold_reference_local_only"][
            "answerable"
        ]
        assert p["experiment_fingerprint"] == runner["fingerprint"](runner["configuration"]())
        assert p["input_sha256"] == runner["INPUT_SHA256"]
        assert p["output_fingerprint"] == runner["fingerprint"](record)
        assert record["id"] == p["question_id"] and record["http_status"] == 200
        assert record["request"] == {
            **runner["SETTINGS"],
            "messages": record["request"]["messages"],
        }
        raw = base64.b64decode(record["raw_body_b64"], validate=True)
        content = strict_json(raw)["choices"][0]["message"]["content"]
        assert content == p["raw_model_content_unrepaired"]
        context = packet_context(p)
        status, output, _ = await runner["replay"](record, context, settings)
        assert status == p["classification"]
        original[status] += 1
        result, failure = None, None
        start = time.perf_counter()
        if output is None:
            classification = "rejected_before_binding"
            failure = status
        else:
            try:
                result = bind_quote_offsets(output, context)
                classification = (
                    "structurally_bound_answer" if output.answerable else "valid_refusal"
                )
                assert result.output.answer == output.answer
                assert [c.quote for c in result.output.citations] == [
                    c.quote for c in output.citations
                ]
                assert result.production_authorized is False
                assert result.semantic_support == "NOT_EVALUATED"
                assert validate_citations(result.output, context) == list(result.citations)
                citation_count += len(result.citations)
                refusals += not output.answerable
                # Supplied previous AI diagnostics, NOT correctness inferred from binding or Gold.
                bound_positive += output.answerable and verdicts[p["question_id"]] == "CORRECT"
                bound_unsafe += output.answerable and verdicts[p["question_id"]] in {
                    "UNSUPPORTED_ASSERTION",
                    "INCORRECT_QUESTION_ANSWER",
                }
            except ValueError as error:
                classification, failure = "binding_rejected", str(error)
        if output is not None:
            elapsed.append((time.perf_counter() - start) * 1000)
        classifications[classification] += 1
        if failure:
            reasons[failure] += 1
        rows.append(
            {
                "question_id": p["question_id"],
                "original_stage": status,
                "classification": classification,
                "failure": failure,
                "gold_example_fingerprint": runner["fingerprint"](p["gold_reference_local_only"]),
                "output_fingerprint": p["output_fingerprint"],
                "raw_content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "bound_model_answer": result.output.model_dump(mode="json") if result else None,
                "structurally_valid_citations": [
                    c.model_dump(mode="json") for c in result.citations
                ]
                if result
                else [],
                "prior_ai_diagnostic_verdict": verdicts[p["question_id"]],
                "semantic_support": "NOT_EVALUATED",
                "production_authorized": False,
            }
        )
    assert dict(original) == {"invalid_schema": 9, "invalid_citation": 6}
    required = sum(len(p["gold_reference_local_only"]["required_citation_refs"]) for p in packet)
    assert required == 19
    bound = classifications["structurally_bound_answer"]
    metrics = {
        "scope": "offline frozen DEV diagnostics only",
        "packet_sha256": PACKET_SHA256,
        "case_count": 15,
        "positive_count": 12,
        "negative_count": 3,
        "original_classifications": dict(original),
        "original_strict_acceptance": {"numerator": 0, "denominator": 15},
        "classifications": dict(classifications),
        "failure_categories": dict(reasons),
        "structurally_bound_answers": {"numerator": bound, "denominator": 15},
        "eligible_schema_valid": {"numerator": 6, "denominator": 15},
        "still_rejected": {"numerator": 15 - bound - refusals, "denominator": 15},
        "prior_ai_positive_raw_correct": {"numerator": 12, "denominator": 12},
        "prior_ai_correct_structurally_bound_answers": {
            "numerator": bound_positive,
            "denominator": bound,
        },
        "prior_ai_incorrect_or_unsafe_structurally_bound_answers": {
            "numerator": bound_unsafe,
            "denominator": bound,
        },
        "valid_refusals": {"numerator": refusals, "denominator": 3},
        "structural_citation_validity": {
            "numerator": citation_count,
            "denominator": citation_count,
        },
        "delivered_production_required_coverage": {"numerator": 0, "denominator": required},
        "structural_required_anchor_coverage": "NOT_EVALUATED_SOURCE_IDENTITY_UNAVAILABLE"
        if citation_count
        else {"numerator": 0, "denominator": required},
        "production_authorized_count": 0,
        "semantic_support": "NOT_EVALUATED",
        "human_review_status": "NOT_EVALUATED",
        "operator_confirmation_status": "NOT_CONFIRMED",
        "synthetic_safety": (
            "structurally bindable unsafe counterexamples; never release-authorized"
        ),
    }
    timing = {
        "binding_attempt_ms": elapsed,
        "note": "Six local binding attempts; schema skips excluded. Not model generation latency.",
    }
    return metrics, rows, timing


def preserve_or_write(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)


@pytest.mark.anyio
async def test_frozen_ml7_dev_binding_replay():
    if os.environ.get("DOCLENS_RAG_QUOTE_BINDING_REPLAY") != "1":
        pytest.skip("Opt in to offline packet replay with DOCLENS_RAG_QUOTE_BINDING_REPLAY=1")
    packet_path = ROOT / "evaluation-output/rag-model-compare-dev-v1/human-output-review.json"
    raw = packet_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PACKET_SHA256
    packet = strict_json(raw)
    output = ROOT / "evaluation-output/rag-quote-binding-dev-v1"
    output.mkdir(exist_ok=True)
    prior = strict_json((output / "prior-diagnostic-assessment.json").read_bytes())
    metrics, rows, timing = await evaluate_packet(packet, prior)
    preserve_or_write(output / "metrics.json", metrics)
    preserve_or_write(output / "binding-review.json", rows)
    # Timings are observational, not compared across replays; never overwrite a first observation.
    if not (output / "timing.json").exists():
        preserve_or_write(output / "timing.json", timing)
    assert packet_path.read_bytes() == raw
    print(json.dumps(metrics))
