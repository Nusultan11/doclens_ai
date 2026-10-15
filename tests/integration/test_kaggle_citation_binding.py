"""Opt-in original HTTP capture replay; no network, jobs, or model loading in pytest."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from doclens_ai.llm.provider import GeneratorUnavailable, LocalGenerator, strict_json
from doclens_ai.services.rag import SYSTEM_PROMPT, ModelAnswer, validate_citations
from tests.integration.test_kaggle_llm_contract_ab import (
    evaluate_record as evaluate_baseline,
)
from tests.integration.test_kaggle_llm_contract_ab import (
    evidence_context,
    settings_for,
)
from tests.integration.test_kaggle_llm_smoke import percentile
from tools.kaggle_gpu.citation_binding import benchmark
from tools.kaggle_gpu.citation_binding.binding import ExtractiveAnswer, bind, unique_offset

pytestmark = pytest.mark.integration
OUTPUT = Path(__file__).resolve().parents[2] / "tools/kaggle_gpu/outputs"
METRICS = (
    "protocol_valid",
    "json_valid",
    "schema_valid",
    "valid_selection",
    "binding_success",
    "correct_positive",
    "supported_correct_positive",
    "correct_refusal",
    "incorrect_accepted",
    "unsupported_accepted",
    "conflicting_accepted",
    "invalid_output_rejected",
    "http_failed",
    "invalid_binding",
    "unsupported_extractive",
    "unsupported_extractive_refusal",
)


def classify(answer, case):
    positive = (
        answer.answerable
        and case["expected_answerable"]
        and answer.answer in case["expected_answers"]
    )
    return {
        "correct_positive": bool(positive),
        "supported_correct_positive": bool(positive and case["extractive_supported"]),
        "correct_refusal": not answer.answerable and not case["expected_answerable"],
        "incorrect_accepted": answer.answerable and not positive,
        "unsupported_accepted": answer.answerable and not case["expected_answerable"],
        "conflicting_accepted": answer.answerable and case["category"] == "conflict",
        "unsupported_extractive_refusal": not answer.answerable
        and not case["extractive_supported"],
    }


async def evaluate(record, case, settings):
    if case["variant"] == "baseline":
        result = await evaluate_baseline(record, case, settings)
        result["valid_selection"] = result["valid_references"]
        result["binding_success"] = False  # Baseline does not use binder.
        result["invalid_binding"] = False
        result["supported_correct_positive"] = (
            result["correct_positive"] and case["extractive_supported"]
        )
        result["conflicting_accepted"] = (
            result["unsupported_accepted"] and case["category"] == "conflict"
        )
        result["unsupported_extractive"] = not case["extractive_supported"]
        result["unsupported_extractive_refusal"] = (
            result["rejection_stage"] == "accepted"
            and not case["extractive_supported"]
            and not result["citation_valid_answer"]
        )
        return result
    context = evidence_context(case, settings)
    outcome = dict.fromkeys(METRICS, False)
    outcome.update(
        id=case["id"],
        scenario_id=case["scenario_id"],
        split=case["split"],
        variant="candidate",
        categories=[],
        rejection_stage="http",
        unsupported_extractive=not case["extractive_supported"],
    )
    outcome["http_failed"] = (
        record["transport_status"] != "captured" or record.get("http_status") != 200
    )
    if record["transport_status"] != "captured":
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
            outcome["rejection_stage"] = "protocol"
            outcome["invalid_output_rejected"] = True
            return outcome
    finally:
        await generator.aclose()
    outcome["protocol_valid"] = True
    stage = "json"
    try:
        decoded = strict_json(generated)
        outcome["json_valid"] = True
        outcome["valid_selection"] = (
            isinstance(decoded, dict)
            and decoded.get("answerable") is True
            and isinstance(decoded.get("chunk_id"), str)
            and decoded["chunk_id"] in {str(item.chunk_id) for item in context.evidence}
        )
        stage = "schema"
        candidate = ExtractiveAnswer.model_validate(decoded)
        outcome["schema_valid"] = True
        stage = "binding"
        answer = bind(candidate, context)
        outcome["binding_success"] = answer.answerable
        # Independent audit of exact slices/trusted metadata after binding. A failed
        # audit is unsafe acceptance, not merely a rejected output.
        if answer.answerable:
            c = answer.citations[0]
            item, packed = next(
                (i, t)
                for i, t in zip(context.evidence, context.texts, strict=True)
                if str(i.chunk_id) == candidate.chunk_id
            )
            audit = (
                answer.answer == candidate.answer
                and c.quote == candidate.quote
                and c.chunk_id == str(item.chunk_id)
                and c.document_version_id == str(item.document_version_id)
                and packed[c.quote_start : c.quote_end] == candidate.quote
                and c.quote_start == unique_offset(packed, candidate.quote)
                and c.quote_end == c.quote_start + len(candidate.quote)
                and unique_offset(candidate.quote, candidate.answer) >= 0
                and c.answer_start == 0
                and c.answer_end == len(candidate.answer)
            )
            outcome["invalid_binding"] = not audit
        ModelAnswer.model_validate(answer.model_dump())
        validate_citations(answer, context)
        outcome.update(classify(answer, case))
        stage = "accepted"
    except (ValueError, TypeError) as error:
        if outcome["binding_success"]:
            outcome["invalid_binding"] = True
        outcome["categories"].append(stage + "_rejected_" + type(error).__name__)
    outcome["rejection_stage"] = stage
    outcome["invalid_output_rejected"] = stage != "accepted"
    if outcome["incorrect_accepted"]:
        outcome["categories"].append("incorrect_synthetic_answer_accepted")
    return outcome


def summarize(outcomes, records):
    return {
        "count": len(outcomes),
        "counts": {key: sum(bool(o[key]) for o in outcomes) for key in METRICS},
        "stages": dict(Counter(o["rejection_stage"] for o in outcomes)),
        "categories": dict(Counter(c for o in outcomes for c in o["categories"])),
        "p50_seconds": percentile([r["elapsed_seconds"] for r in records], 0.5),
        "p95_seconds": percentile([r["elapsed_seconds"] for r in records], 0.95),
        "input_tokens": sum((r.get("usage") or {}).get("prompt_tokens", 0) for r in records),
        "output_tokens": sum((r.get("usage") or {}).get("completion_tokens", 0) for r in records),
    }


def decision(groups, overall):
    b, c = (groups["fresh"][v]["counts"] for v in ("baseline", "candidate"))
    all_c = overall["candidate"]["counts"]
    checks = {
        "positives_improve": c["supported_correct_positive"] > b["supported_correct_positive"],
        "positive_threshold": c["supported_correct_positive"]
        >= benchmark.ACCEPTANCE["supported_positive_minimum"],
        "refusals_preserved": c["correct_refusal"] >= b["correct_refusal"],
        "refusal_threshold": c["correct_refusal"] == benchmark.ACCEPTANCE["refusals_required"],
        "no_incorrect_acceptance": all_c["incorrect_accepted"] == 0,
        "no_invalid_binding": all_c["invalid_binding"] == 0,
        "http_ok": all_c["http_failed"] == 0
        and all_c["protocol_valid"] == overall["candidate"]["count"],
    }
    return {
        "passes": all(checks.values()),
        "unsafe": not (checks["no_incorrect_acceptance"] and checks["no_invalid_binding"]),
        "checks": checks,
    }


def combined_decision(results):
    if any(r["unsafe"] for r in results):
        return "REJECT"
    if all(r["passes"] for r in results):
        return "PROMOTE_FOR_FURTHER_EVALUATION"
    return "INCONCLUSIVE" if any(r["passes"] for r in results) else "REJECT"


def test_frozen_protocol_definitions_and_contexts():
    base = benchmark.adapter()["load_frozen_runner"]()
    cases = benchmark.scenarios(base)
    fresh = cases[5:]
    assert len(fresh) == 26 and len({c["id"] for c in cases}) == 31
    assert sum(c["expected_answerable"] and c["extractive_supported"] for c in fresh) == 14
    assert sum(not c["expected_answerable"] for c in fresh) == 10
    assert sum(not c["extractive_supported"] for c in fresh) == 2
    previous = benchmark.adapter()["scenarios"](base)[5:]
    assert not (
        {c["request"]["messages"][1]["content"] for c in fresh}
        & {c["request"]["messages"][1]["content"] for c in previous}
    )
    paired = benchmark.paired_cases(base)
    for first, second in zip(paired[::2], paired[1::2], strict=True):
        assert first["request"]["messages"][1:] == second["request"]["messages"][1:]
        assert first["request"]["messages"][0] != second["request"]["messages"][0]
        for c in (first, second):
            evidence_context(c, settings_for(base))
            if c["variant"] == "baseline":
                assert c["request"]["messages"][0]["content"] == SYSTEM_PROMPT
    metadata = strict_json(Path(benchmark.__file__).with_name("kernel-metadata.json").read_bytes())
    assert metadata["id"] == "nurs2005/doclens-citation-binding"
    assert metadata["is_private"] and metadata["enable_gpu"] and not metadata["enable_internet"]
    assert metadata["dataset_sources"] == [benchmark.adapter()["INPUT_DATASET"]]


def test_unsafe_acceptance_overrides_other_repeat_and_quality():
    assert (
        combined_decision([{"unsafe": True, "passes": False}, {"unsafe": False, "passes": True}])
        == "REJECT"
    )
    assert combined_decision([{"unsafe": False, "passes": True}] * 2) == (
        "PROMOTE_FOR_FURTHER_EVALUATION"
    )
    assert (
        combined_decision([{"unsafe": False, "passes": True}, {"unsafe": False, "passes": False}])
        == "INCONCLUSIVE"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "kind",
    ["valid", "refusal", "extra", "invented", "foreign", "inconsistent", "wrong", "duplicate_json"],
)
async def test_candidate_replay_scoring_never_credits_invalid_as_refusal(kind):
    # Controlled local envelopes test the scorer, NOT evidence of a real GPU run.
    base = benchmark.adapter()["load_frozen_runner"]()
    case = next(
        c
        for c in benchmark.paired_cases(base)
        if c["variant"] == "candidate" and c["scenario_id"] == "positive-label"
    )
    evidence = strict_json(case["request"]["messages"][1]["content"])["evidence"][0]
    payload = {
        "answerable": True,
        "answer": "ALPHA",
        "chunk_id": evidence["chunk_id"],
        "quote": "ALPHA",
        "reason": None,
    }
    if kind == "refusal":
        case = dict(case, expected_answerable=False, expected_answers=[])
        payload = {
            "answerable": False,
            "answer": None,
            "chunk_id": None,
            "quote": None,
            "reason": "insufficient_evidence",
        }
    elif kind == "extra":
        payload["quote_start"] = 0
    elif kind == "invented":
        payload["quote"] = "BETA"
    elif kind == "foreign":
        payload["chunk_id"] = "11111111-1111-1111-1111-111111111111"
    elif kind == "inconsistent":
        payload["answerable"] = False
    elif kind == "wrong":
        case = dict(case, expected_answers=["BETA"])
    content = json.dumps(payload)
    if kind == "duplicate_json":
        content = content[:-1] + ',"answer":"ALPHA"}'
    raw = json.dumps(
        {
            "model": base.MODEL_ALIAS,
            "choices": [
                {"finish_reason": "stop", "message": {"role": "assistant", "content": content}}
            ],
        }
    ).encode()
    record = {
        "transport_status": "captured",
        "http_status": 200,
        "headers": {"content-type": "application/json"},
        "raw_body_b64": base64.b64encode(raw).decode(),
        "response_bytes": len(raw),
    }
    result = await evaluate(record, case, settings_for(base))
    assert result["correct_positive"] == (kind == "valid")
    assert result["correct_refusal"] == (kind == "refusal")
    assert result["incorrect_accepted"] == (kind == "wrong")
    assert result["invalid_output_rejected"] == (
        kind in {"extra", "invented", "foreign", "inconsistent", "duplicate_json"}
    )


@pytest.fixture
def real_captures():
    selected = os.getenv("DOCLENS_BINDING_REPORTS")
    if not selected:
        pytest.skip("Opt in with two real GPU captures: DOCLENS_BINDING_REPORTS and FREEZE")
    paths = [Path(p).resolve() for p in selected.split(os.pathsep)]
    assert len(paths) == 2 and paths[0] != paths[1]
    freeze_path = Path(os.environ["DOCLENS_BINDING_FREEZE"]).resolve()
    assert all(p.is_relative_to(OUTPUT.resolve()) for p in [*paths, freeze_path])
    freeze = strict_json(freeze_path.read_bytes())
    return paths, freeze_path, freeze


@pytest.mark.anyio
async def test_real_kaggle_citation_binding_replay(real_captures):
    paths, freeze_path, freeze = real_captures
    helper = benchmark.adapter()
    base = helper["load_frozen_runner"]()
    config, cases = benchmark.configuration(base), benchmark.paired_cases(base)
    assert freeze["configuration"] == config
    assert freeze["configuration_fingerprint"] == base.fingerprint(config)
    assert freeze["cases_fingerprint"] == base.fingerprint(cases)
    assert freeze["scenarios"] == benchmark.scenarios(base)
    for p, key in [
        (freeze_path.with_name("benchmark.py"), "entrypoint_sha256"),
        (Path(benchmark.__file__).with_name("binding.py"), "binder_sha256"),
    ]:
        assert helper["text_hash"](p.read_text(encoding="utf-8")) == freeze[key]
    results, reports, contents, remote_metadata = [], [], [], []
    for path in paths:
        report = strict_json(path.read_bytes())
        reports.append(report)
        assert report["status"] == "complete" and report["experiment"] == config["experiment"]
        assert report["configuration"] == config
        for key in ("configuration_fingerprint", "cases_fingerprint", "entrypoint_sha256"):
            assert report[key] == freeze[key]
        assert report["source_sha256"] == helper["FROZEN_RUNNER_SHA256"]
        assert datetime.fromisoformat(freeze["prepared_at_utc"]) < datetime.fromisoformat(
            report["started_at_utc"]
        )
        assert report["verified_artifacts"] == {
            "model_sha256": base.MODEL_SHA256,
            "runtime_archive_sha256": base.RUNTIME_SHA256,
            "llama_server_sha256": base.SERVER_SHA256,
        }
        assert report["gpu_offload_confirmed"] and "CUDA0: Tesla T4" in report["runtime_devices"]
        assert report["sampled_peaks"]["primary_gpu_used_mib"] > 0
        assert "layers to GPU" in (path.parent / "llama-server.log").read_bytes().decode(
            "ascii", errors="ignore"
        )
        metadata = strict_json((path.parent / "remote/kernel-metadata.json").read_bytes())
        remote_metadata.append(metadata)
        assert metadata["id"] == "nurs2005/doclens-citation-binding"
        assert metadata["is_private"] is True and metadata["enable_internet"] is False
        assert metadata["enable_gpu"] is True
        assert metadata["machine_shape"] == "NvidiaTeslaT4"
        assert all(
            not metadata[key] for key in ("kernel_sources", "competition_sources", "model_sources")
        )
        assert metadata["dataset_sources"] in (
            [helper["INPUT_DATASET"]],
            [helper["INPUT_DATASET"].removesuffix("/1")],
        )
        assert metadata["code_file"] == "doclens-citation-binding.py"
        assert (
            helper["text_hash"](
                (path.parent / "remote" / metadata["code_file"]).read_text(encoding="utf-8")
            )
            == freeze["entrypoint_sha256"]
        )
        assert len(report["responses"]) == len(cases)
        outcomes, hashes = [], []
        for record, case in zip(report["responses"], cases, strict=True):
            assert record["id"] == case["id"] and record["request"] == case["request"]
            outcomes.append(await evaluate(record, case, settings_for(base)))
            raw = base64.b64decode(record["raw_body_b64"], validate=True)
            content = strict_json(raw)["choices"][0]["message"]["content"]
            hashes.append(hashlib.sha256(content.encode()).hexdigest())
        groups = {
            split: {
                v: summarize(
                    [o for o in outcomes if o["split"] == split and o["variant"] == v],
                    [
                        r
                        for r, c in zip(report["responses"], cases, strict=True)
                        if c["split"] == split and c["variant"] == v
                    ],
                )
                for v in ("baseline", "candidate")
            }
            for split in ("development", "fresh")
        }
        overall = {
            v: summarize(
                [o for o in outcomes if o["variant"] == v],
                [r for r, c in zip(report["responses"], cases, strict=True) if c["variant"] == v],
            )
            for v in ("baseline", "candidate")
        }
        results.append(
            {
                "groups": groups,
                "overall": overall,
                "outcomes": outcomes,
                "decision": decision(groups, overall),
                "sampled_peaks": report["sampled_peaks"],
                "cold_start_seconds": report["cold_start_seconds"],
                "cold_generation_seconds": report["cold_generation"]["elapsed_seconds"],
            }
        )
        contents.append(hashes)
    assert reports[0]["started_at_utc"] != reports[1]["started_at_utc"]
    assert reports[0]["python"] == reports[1]["python"]
    assert reports[0]["libraries"] == reports[1]["libraries"]
    assert remote_metadata[0]["docker_image"] == remote_metadata[1]["docker_image"]
    assert remote_metadata[0]["docker_image"].startswith(
        "gcr.io/kaggle-private-byod/python@sha256:"
    )
    result = {
        "decision": combined_decision([r["decision"] for r in results]),
        "runs": results,
        "identical_generated_texts": sum(a == b for a, b in zip(*contents, strict=True)),
        "identical_verdicts": results[0]["outcomes"] == results[1]["outcomes"],
        "configuration_fingerprint": freeze["configuration_fingerprint"],
        "fresh_fingerprint": config["fresh_fingerprint"],
        "production_promotion": False,
        "human_reviewed_rag_quality": "NOT_EVALUATED",
    }
    (OUTPUT / "citation-binding-evaluation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
