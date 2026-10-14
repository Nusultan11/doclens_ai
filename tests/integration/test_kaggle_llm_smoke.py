"""Opt-in replay of REAL captured loopback HTTP; never submit jobs or load models."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import runpy
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
import pytest
from pydantic import ValidationError

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.llm.provider import GeneratorUnavailable, LocalGenerator, strict_json
from doclens_ai.services.rag import (
    PROMPT_HASH,
    SYSTEM_PROMPT,
    ModelAnswer,
    pack_context,
    validate_citations,
)
from doclens_ai.services.retrieval import SourceLocator, VerifiedResult

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / "tools/kaggle_gpu/outputs"
SCRIPT = ROOT / "tools/kaggle_gpu/llm_smoke/llm_smoke.py"


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def context_for(case, settings):
    user = strict_json(case["request"]["messages"][1]["content"])
    results = tuple(
        VerifiedResult(
            chunk_id=UUID(item["chunk_id"]),
            document_id=UUID(item["document_id"]),
            document_version_id=UUID(item["document_version_id"]),
            index_revision_id=UUID(item["index_revision_id"]),
            workspace_id=uuid5(NAMESPACE_URL, "doclens-llm-smoke-v1/workspace"),
            score=1.0,
            text=item["text"],
            locator=SourceLocator.model_validate(item["source_locator"]),
            source_sha256=hashlib.sha256(item["text"].encode()).hexdigest(),
        )
        for item in user["evidence"]
    )
    context = pack_context(user["question"], results, settings)
    assert context.messages == case["request"]["messages"]
    return context


async def validate_capture(record, case, settings):
    context = context_for(case, settings)
    outcome = {
        "id": case["id"],
        "valid_json": False,
        "schema_valid": False,
        "citation_valid_answer": False,
        "refusal": False,
        "expected_behavior": False,
    }
    if record["transport_status"] != "captured":
        outcome["status"] = record["transport_status"]
        return outcome
    raw = base64.b64decode(record["raw_body_b64"], validate=True)
    assert len(raw) == record["response_bytes"] <= settings.max_response_bytes

    def replay(request):
        assert str(request.url) == settings.endpoint
        assert strict_json(request.content) == case["request"]
        return httpx.Response(
            record["http_status"], headers=record["headers"], stream=httpx.ByteStream(raw)
        )

    generator = LocalGenerator(settings, transport=httpx.MockTransport(replay))
    try:
        try:
            generated = await generator.generate(context.messages)
        except GeneratorUnavailable:
            outcome["status"] = "protocol_rejected"
            return outcome
    finally:
        await generator.aclose()
    try:
        decoded = strict_json(generated)
        outcome["valid_json"] = True
    except (ValueError, TypeError):
        outcome["status"] = "json_rejected"
        return outcome
    try:
        answer = ModelAnswer.model_validate(decoded)
        outcome["schema_valid"] = True
    except ValidationError:
        outcome["status"] = "schema_rejected"
        return outcome
    try:
        citations = validate_citations(answer, context)
    except ValueError:
        outcome["status"] = "citations_rejected"
        return outcome
    outcome["citation_valid_answer"] = answer.answerable and bool(citations)
    outcome["refusal"] = not answer.answerable
    outcome["expected_behavior"] = (
        answer.answerable == case["expected_answerable"]
        and (not answer.answerable or answer.answer == context.texts[0])
    )
    outcome["status"] = "accepted_answer" if answer.answerable else "accepted_refusal"
    return outcome


@pytest.fixture
def captured_reports():
    selected = os.getenv("DOCLENS_KAGGLE_LLM_REPORTS")
    if not selected:
        pytest.skip("Opt in with DOCLENS_KAGGLE_LLM_REPORTS pointing to two real captured reports")
    paths = [Path(p).resolve() for p in selected.split(os.pathsep)]
    assert len(paths) == 2 and paths[0] != paths[1]
    assert all(p.is_relative_to(OUTPUT_ROOT.resolve()) for p in paths)
    # Kaggle CLI reads code as UTF-8 text with universal newlines before upload.
    # Match the submitted bytes even after a Windows CRLF checkout.
    submitted_hash = hashlib.sha256(SCRIPT.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    return [strict_json(path.read_bytes()) for path in paths], submitted_hash


@pytest.mark.anyio
async def test_real_kaggle_captures_through_unchanged_production_contracts(captured_reports):
    captures, submitted_hash = captured_reports
    experiment = runpy.run_path(str(SCRIPT))  # Definitions only: no LLM, downloads or Kaggle auth.
    assert experiment["SYSTEM_PROMPT"] == SYSTEM_PROMPT
    assert experiment["PROMPT_HASH"] == PROMPT_HASH
    cases = experiment["synthetic_cases"]()
    expected_config = experiment["configuration"]()
    settings = RagSettings(
        _env_file=None,
        enabled=True,
        endpoint=expected_config["endpoint"],
        model_id=experiment["MODEL_ALIAS"],
        model_revision=experiment["MODEL_REVISION"],
        artifact_sha256=experiment["MODEL_SHA256"],
        max_output_tokens=512,
        timeout_seconds=60,
        max_response_bytes=65536,
    )
    reports, summaries, generated_contents = [], [], []
    for report in captures:
        assert report["schema_version"] == 1 and report["status"] == "complete"
        assert report["source_sha256"] == submitted_hash
        assert report["configuration"] == expected_config
        assert report["configuration_fingerprint"] == experiment["fingerprint"](expected_config)
        assert report["cases_fingerprint"] == experiment["fingerprint"](cases)
        assert report["verified_artifacts"]["model_sha256"] == experiment["MODEL_SHA256"]
        assert (
            report["verified_artifacts"]["runtime_archive_sha256"] == experiment["RUNTIME_SHA256"]
        )
        assert report["verified_artifacts"]["llama_server_sha256"] == experiment["SERVER_SHA256"]
        assert report["gpu_offload_confirmed"] is True
        assert report["gpu_before"][0]["name"] == "Tesla T4"
        assert "CUDA0: Tesla T4" in report["runtime_devices"]
        assert "not found" not in report["cuda_backend_dependencies"]
        assert report["sampled_peaks"]["successful_samples"] > 0
        assert report["sampled_peaks"]["primary_gpu_used_mib"] > 0
        assert report["human_reviewed_rag_quality"] == "NOT_EVALUATED"
        assert len(report["responses"]) == len(cases) == 5
        outcomes, contents = [], []
        for case, record in zip(cases, report["responses"], strict=True):
            assert record["id"] == case["id"] and record["request"] == case["request"]
            outcome = await validate_capture(record, case, settings)
            outcomes.append(outcome)
            contents.append(record["raw_body_b64"])
        latencies = [r["elapsed_seconds"] for r in report["responses"]]
        usage = [r.get("usage") or {} for r in report["responses"]]
        timings = [r.get("timings") or {} for r in report["responses"]]
        counts = {
            key: sum(o[key] for o in outcomes)
            for key in (
                "valid_json",
                "schema_valid",
                "citation_valid_answer",
                "refusal",
                "expected_behavior",
            )
        }
        failures = {}
        for outcome in outcomes:
            if outcome["status"] not in {"accepted_answer", "accepted_refusal"}:
                failures[outcome["status"]] = failures.get(outcome["status"], 0) + 1
        # REJECT is an observed compatibility result, not a repaired output or weakened validator.
        decision = "PASS" if counts["expected_behavior"] == 5 and not failures else "REJECT"
        summaries.append(
            {
                "compatibility": decision,
                "counts": counts,
                "failures": failures,
                "cold_start_seconds": report["cold_start_seconds"],
                "cold_generation_seconds": report["cold_generation"]["elapsed_seconds"],
                "warm_samples": len(latencies),
                "warm_p50_seconds": percentile(latencies, 0.5),
                "warm_p95_seconds": percentile(latencies, 0.95),
                "input_tokens": [u.get("prompt_tokens") for u in usage],
                "output_tokens": [u.get("completion_tokens") for u in usage],
                "tokens_per_second": [t.get("predicted_per_second") for t in timings],
                "sampled_peaks": report["sampled_peaks"],
                "safety_probes": {
                    k: report["safety_probes"][k]["transport_status"]
                    for k in ("deadline", "response_size")
                },
                "case_outcomes": outcomes,
                "human_reviewed_rag_quality": "NOT_EVALUATED",
            }
        )
        reports.append(report)
        generated_contents.append(contents)
    assert reports[0]["started_at_utc"] != reports[1]["started_at_utc"]
    assert reports[0]["verified_artifacts"] == reports[1]["verified_artifacts"]
    assert reports[0]["python"] == reports[1]["python"]
    assert reports[0]["libraries"] == reports[1]["libraries"]
    # Envelope IDs/timestamps can vary even if generated text does not.
    # Record both without demanding equality.
    text_variation = []
    for first, second in zip(reports[0]["responses"], reports[1]["responses"], strict=True):
        try:
            a = strict_json(base64.b64decode(first["raw_body_b64"]))["choices"][0]["message"][
                "content"
            ]
            b = strict_json(base64.b64decode(second["raw_body_b64"]))["choices"][0]["message"][
                "content"
            ]
            text_variation.append(a != b)
        except (ValueError, KeyError, IndexError, TypeError):
            text_variation.append(None)
    print(
        json.dumps(
            {
                "paired_results": summaries,
                "generated_text_varied": text_variation,
                "raw_envelopes_equal": generated_contents[0] == generated_contents[1],
                "configuration_and_cases_identical": True,
            },
            sort_keys=True,
        )
    )
