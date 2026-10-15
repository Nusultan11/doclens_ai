"""Opt-in REAL A/B capture replay. Default checks are offline definitions only."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import runpy
from collections import Counter
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.llm.provider import GeneratorUnavailable, LocalGenerator, strict_json
from doclens_ai.services.rag import PROMPT_HASH, SYSTEM_PROMPT, ModelAnswer, validate_citations
from tests.integration.test_kaggle_llm_smoke import context_for, percentile

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "tools/kaggle_gpu/outputs"
SCRIPT = ROOT / "tools/kaggle_gpu/llm_contract_ab/benchmark.py"
OLD_HASHES = (
    "71a037da6b6978903cf86d2a24093eb1c0a7b2351b3e671e5ae18daf19273c1a",
    "4306cf10de72b97e306a9d0c39bea5f7d4c1083c02449ff55a75054808952dbe",
)
METRICS = (
    "protocol_valid",
    "json_valid",
    "schema_valid",
    "valid_references",
    "citation_valid_answer",
    "correct_positive",
    "correct_refusal",
    "expected_behavior",
    "incorrect_accepted",
    "unsupported_accepted",
    "invalid_output_rejected",
    "http_failed",
)


def settings_for(base):
    return RagSettings(
        _env_file=None,
        enabled=True,
        api_key=None,
        endpoint=base.configuration()["endpoint"],
        model_id=base.MODEL_ALIAS,
        model_revision=base.MODEL_REVISION,
        artifact_sha256=base.MODEL_SHA256,
        temperature=0,
        max_output_tokens=512,
        timeout_seconds=60,
        max_response_bytes=65536,
        concurrency=1,
        max_context_chars=16000,
        max_chunk_chars=4000,
        max_evidence_chunks=6,
    )


def evidence_context(case, settings):
    # The existing helper invokes unchanged pack_context and checks exact user JSON.
    baseline_case = json.loads(json.dumps(case))
    baseline_case["request"]["messages"][0]["content"] = SYSTEM_PROMPT
    context = context_for(baseline_case, settings)
    return replace(context, messages=case["request"]["messages"])


def raw_diagnostics(decoded, case, context):
    """Literal diagnostics only: never repair or construct a bypassed ModelAnswer."""
    categories = set()
    if not isinstance(decoded, dict):
        return {"other"}, False
    answer, citations = decoded.get("answer"), decoded.get("citations")
    by_id = {
        str(item.chunk_id): (item, text)
        for item, text in zip(context.evidence, context.texts, strict=True)
    }
    refs = isinstance(citations, list) and bool(citations)
    covered, spans_checkable = set(), isinstance(answer, str)
    for citation in citations if isinstance(citations, list) else []:
        if not isinstance(citation, dict):
            refs, spans_checkable = False, False
            continue
        chunk_id = citation.get("chunk_id")
        pair = by_id.get(chunk_id) if isinstance(chunk_id, str) else None
        if pair is None or citation.get("document_version_id") != str(pair[0].document_version_id):
            refs = False
            categories.add("other")
        start, end = citation.get("quote_start"), citation.get("quote_end")
        if (
            pair
            and type(start) is int
            and type(end) is int
            and isinstance(citation.get("quote"), str)
        ):
            if not (0 <= start < end <= len(pair[1])) or pair[1][start:end] != citation["quote"]:
                categories.add("quote_offset_mismatch")
        start, end = citation.get("answer_start"), citation.get("answer_end")
        if isinstance(answer, str) and type(start) is int and type(end) is int:
            if 0 <= start < end <= len(answer):
                covered.update(range(start, end))
            else:
                spans_checkable = False
                categories.add("other")  # Observed out-of-bounds answer range.
        else:
            spans_checkable = False
    if spans_checkable and any(
        not char.isspace() and i not in covered for i, char in enumerate(answer)
    ):
        categories.add("uncovered_answer_span")
    if decoded.get("answerable") is True and (
        not case["expected_answerable"] or answer not in case["expected_answers"]
    ):
        categories.add("incorrect_synthetic_answer")
    return categories, bool(refs)


async def evaluate_record(record, case, settings):
    context = evidence_context(case, settings)
    outcome = {key: False for key in METRICS}
    outcome.update(
        id=case["id"],
        scenario_id=case.get("scenario_id", case["id"]),
        split=case.get("split", "development"),
        variant=case.get("variant", "baseline"),
    )
    outcome["http_failed"] = (
        record["transport_status"] != "captured" or record.get("http_status") != 200
    )
    categories, stage, decoded, answer = set(), "http", None, None
    if record["transport_status"] == "captured":
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
                await generator.generate(context.messages)
                outcome["protocol_valid"] = True
            except GeneratorUnavailable:
                pass
        finally:
            await generator.aclose()
        # Independently inspect raw JSON/schema even if the envelope was rejected.
        # Diagnostic success never overrides a production protocol rejection.
        try:
            envelope = strict_json(raw)
            content = envelope["choices"][0]["message"]["content"]
            decoded = strict_json(content)
            outcome["json_valid"] = True
        except (ValueError, TypeError, KeyError, IndexError):
            categories.add("other")
        if outcome["json_valid"]:
            raw_categories, outcome["valid_references"] = raw_diagnostics(decoded, case, context)
            categories.update(raw_categories)
            try:
                answer = ModelAnswer.model_validate(decoded)
                outcome["schema_valid"] = True
            except ValidationError as error:
                for detail in error.errors():
                    location, kind = detail["loc"], detail["type"]
                    if kind == "extra_forbidden":
                        categories.add("additional_prohibited_fields")
                    elif kind == "missing" and location and location[0] == "citations":
                        categories.add("missing_citation_fields")
                    elif (
                        not location
                        and isinstance(decoded, dict)
                        and (decoded.get("answerable") is False or decoded.get("answer") is None)
                    ):
                        categories.add("invalid_refusal")
                    else:
                        categories.add("invalid_ModelAnswer_field")
    if not outcome["http_failed"]:
        stage = "protocol"
        if outcome["protocol_valid"]:
            stage = "json"
            if outcome["json_valid"]:
                stage = "schema"
                if answer is not None:
                    stage = "citations"
                    try:
                        citations = validate_citations(answer, context)
                    except ValueError:
                        pass
                    else:
                        stage = "accepted"
                        outcome["citation_valid_answer"] = answer.answerable and bool(citations)
                        outcome["correct_positive"] = (
                            case["expected_answerable"]
                            and answer.answerable
                            and answer.answer in case["expected_answers"]
                        )
                        outcome["correct_refusal"] = (
                            not case["expected_answerable"] and not answer.answerable
                        )
                        outcome["incorrect_accepted"] = (
                            answer.answerable and not outcome["correct_positive"]
                        )
                        outcome["unsupported_accepted"] = (
                            answer.answerable and not case["expected_answerable"]
                        )
        outcome["invalid_output_rejected"] = stage != "accepted"
    outcome["expected_behavior"] = outcome["correct_positive"] or outcome["correct_refusal"]
    outcome["rejection_stage"] = stage
    outcome["categories"] = sorted(categories)
    return outcome


def test_ab_frozen_definitions_are_prompt_only():
    experiment = runpy.run_path(str(SCRIPT))
    base = experiment["load_frozen_runner"]()
    # Regression for the real post-inference UnicodeDecodeError, not a fake response.
    log = b"split token: \xd0\nload_tensors: offloaded 29/29 layers to GPU\n"
    with pytest.raises(UnicodeDecodeError):
        log.decode("utf-8")
    assert "offloaded 29/29 layers to GPU" in experiment["ascii_log_markers"](log)
    assert base.SYSTEM_PROMPT == SYSTEM_PROMPT and base.PROMPT_HASH == PROMPT_HASH
    cases = experiment["scenarios"](base)
    assert len(cases) == 19 and sum(c["split"] == "heldout" for c in cases) == 14
    assert sum(not c["expected_answerable"] for c in cases if c["split"] == "heldout") == 5
    assert len({c["id"] for c in cases}) == len(cases)
    assert cases[:5] == [
        dict(
            c,
            split="development",
            expected_answers={"positive-label": ["ALPHA"], "positive-value": ["42"]}.get(
                c["id"], []
            ),
        )
        for c in base.synthetic_cases()
    ]
    paired = experiment["paired_cases"](base)
    assert len(paired) == 38
    settings = settings_for(base)
    for case in paired:
        evidence_context(case, settings)
    for case in cases:
        requests = [c["request"] for c in paired if c["scenario_id"] == case["id"]]
        assert requests[0]["messages"][0] != requests[1]["messages"][0]
        assert requests[0]["messages"][1:] == requests[1]["messages"][1:]
        assert {k: v for k, v in requests[0].items() if k != "messages"} == {
            k: v for k, v in requests[1].items() if k != "messages"
        }


@pytest.fixture
def real_reports():
    selected = os.getenv("DOCLENS_KAGGLE_AB_REPORTS")
    if not selected:
        pytest.skip("Opt in with DOCLENS_KAGGLE_AB_REPORTS: two real GPU reports")
    paths = [Path(value).resolve() for value in selected.split(os.pathsep)]
    assert len(paths) == 2 and paths[0] != paths[1]
    assert all(path.is_relative_to(OUTPUT.resolve()) for path in paths)
    freezes = os.getenv("DOCLENS_KAGGLE_AB_FREEZE")
    assert freezes, "Provide the pre-inference freeze.json via DOCLENS_KAGGLE_AB_FREEZE"
    freeze_path = Path(freezes).resolve()
    assert freeze_path.is_relative_to(OUTPUT.resolve())
    freeze = strict_json(freeze_path.read_bytes())
    entrypoint = freeze_path.with_name("benchmark.py").read_text(encoding="utf-8")
    assert hashlib.sha256(entrypoint.encode()).hexdigest() == freeze["entrypoint_sha256"]
    reports = [strict_json(path.read_bytes()) for path in paths]
    return reports, freeze


def group_summary(outcomes, captures):
    latencies = [r["elapsed_seconds"] for r in captures]
    tokens = [(r.get("usage") or {}).get("completion_tokens") for r in captures]
    input_tokens = [(r.get("usage") or {}).get("prompt_tokens") for r in captures]
    speeds = [(r.get("timings") or {}).get("predicted_per_second") for r in captures]
    return {
        "count": len(outcomes),
        "counts": {key: sum(outcome[key] for outcome in outcomes) for key in METRICS},
        "rejections": dict(Counter(o["rejection_stage"] for o in outcomes)),
        "categories": dict(Counter(category for o in outcomes for category in o["categories"])),
        "p50_seconds": percentile(latencies, 0.5),
        "p95_seconds": percentile(latencies, 0.95),
        "generated_tokens": tokens,
        "input_tokens": input_tokens,
        "input_tokens_total": sum(t for t in input_tokens if t is not None),
        "generated_tokens_total": sum(t for t in tokens if t is not None),
        "token_samples_available": sum(t is not None for t in tokens),
        "tokens_per_second": speeds,
    }


def decide(groups, outcomes, acceptance):
    baseline, candidate = (groups["heldout"][v]["counts"] for v in ("baseline", "candidate"))
    regressions = [
        o["scenario_id"]
        for o in outcomes
        if o["variant"] == "candidate"
        and not o["expected_behavior"]
        and any(
            b["scenario_id"] == o["scenario_id"]
            and b["variant"] == "baseline"
            and b["expected_behavior"]
            for b in outcomes
        )
    ]
    counts = {
        v: {k: sum(o[k] for o in outcomes if o["variant"] == v) for k in METRICS}
        for v in ("baseline", "candidate")
    }
    checks = {
        "schema_improved": candidate["schema_valid"] > baseline["schema_valid"],
        "expected_improved": candidate["expected_behavior"] > baseline["expected_behavior"],
        "reliable_schema": candidate["schema_valid"] >= acceptance["heldout_schema_minimum"],
        "reliable_expected": candidate["expected_behavior"]
        >= acceptance["heldout_expected_minimum"],
        "no_incorrect_heldout": candidate["incorrect_accepted"]
        <= acceptance["heldout_incorrect_accepted_maximum"],
        "all_refusals": candidate["correct_refusal"] == acceptance["heldout_refusals_required"],
        "no_case_regressions": len(regressions)
        <= acceptance["per_case_expected_behavior_regressions_maximum"],
        "no_incorrect_increase": counts["candidate"]["incorrect_accepted"]
        <= counts["baseline"]["incorrect_accepted"],
        "http_ok": counts["candidate"]["http_failed"] <= acceptance["http_failures_maximum"],
    }
    return {"passes": all(checks.values()), "checks": checks, "regressions": regressions}


@pytest.mark.anyio
async def test_real_kaggle_prompt_ab_through_production_contracts(real_reports):
    reports, freeze = real_reports
    experiment = runpy.run_path(str(SCRIPT))
    base = experiment["load_frozen_runner"]()
    config, cases = experiment["configuration"](base), experiment["paired_cases"](base)
    assert freeze["configuration"] == config
    assert freeze["configuration_fingerprint"] == base.fingerprint(config)
    assert freeze["cases_fingerprint"] == base.fingerprint(cases)
    assert freeze["scenarios"] == experiment["scenarios"](base)
    settings, all_results, contents = settings_for(base), [], []
    for report in reports:
        assert (
            report["status"] == "complete" and report["experiment"] == "doclens-llm-contract-ab-v1"
        )
        assert report["configuration"] == config
        assert report["configuration_fingerprint"] == freeze["configuration_fingerprint"]
        assert report["cases_fingerprint"] == freeze["cases_fingerprint"]
        assert report["entrypoint_sha256"] == freeze["entrypoint_sha256"]
        assert report["benchmark_sha256"] == config["benchmark_sha256"]
        assert report["source_sha256"] == experiment["FROZEN_RUNNER_SHA256"]
        assert datetime.fromisoformat(freeze["prepared_at_utc"]) < datetime.fromisoformat(
            report["started_at_utc"]
        )
        assert report["verified_artifacts"] == {
            "model_sha256": base.MODEL_SHA256,
            "runtime_archive_sha256": base.RUNTIME_SHA256,
            "llama_server_sha256": base.SERVER_SHA256,
        }
        assert report["gpu_offload_confirmed"] and "CUDA0: Tesla T4" in report["runtime_devices"]
        assert report["sampled_peaks"]["successful_samples"] > 0
        assert report["sampled_peaks"]["primary_gpu_used_mib"] > 0
        assert len(report["responses"]) == len(cases)
        outcomes, text_hashes = [], {}
        for record, case in zip(report["responses"], cases, strict=True):
            assert record["id"] == case["id"] and record["request"] == case["request"]
            outcomes.append(await evaluate_record(record, case, settings))
            try:
                content = strict_json(base64.b64decode(record["raw_body_b64"]))["choices"][0][
                    "message"
                ]["content"]
                text_hashes[case["id"]] = hashlib.sha256(content.encode()).hexdigest()
            except (ValueError, TypeError, KeyError, IndexError):
                text_hashes[case["id"]] = None
        groups = {
            split: {
                variant: group_summary(
                    [o for o in outcomes if o["split"] == split and o["variant"] == variant],
                    [
                        r
                        for r, c in zip(report["responses"], cases, strict=True)
                        if c["split"] == split and c["variant"] == variant
                    ],
                )
                for variant in ("baseline", "candidate")
            }
            for split in ("development", "heldout")
        }
        overall = {
            v: group_summary(
                [o for o in outcomes if o["variant"] == v],
                [r for r, c in zip(report["responses"], cases, strict=True) if c["variant"] == v],
            )
            for v in ("baseline", "candidate")
        }
        all_results.append(
            {
                "groups": groups,
                "overall": overall,
                "outcomes": outcomes,
                "decision": decide(groups, outcomes, experiment["ACCEPTANCE"]),
                "cold_start_seconds": report["cold_start_seconds"],
                "cold_generation_seconds": report["cold_generation"]["elapsed_seconds"],
                "sampled_peaks": report["sampled_peaks"],
            }
        )
        contents.append(text_hashes)
    assert reports[0]["started_at_utc"] != reports[1]["started_at_utc"]
    assert reports[0]["python"] == reports[1]["python"]
    assert reports[0]["libraries"] == reports[1]["libraries"]
    passes = [r["decision"]["passes"] for r in all_results]
    decision = (
        "PROMOTE_FOR_FURTHER_EVALUATION"
        if all(passes)
        else "INCONCLUSIVE"
        if any(passes)
        else "REJECT"
    )
    legacy = []
    for n, checksum in enumerate(OLD_HASHES, 1):
        path = OUTPUT / f"llm-run-{n}/llm_smoke.json"
        if not path.exists():
            legacy.append({"capture": n, "status": "NOT_AVAILABLE"})
            continue
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == checksum
        old = strict_json(raw)
        original_cases = experiment["scenarios"](base)[:5]
        diagnoses = [
            await evaluate_record(r, c, settings)
            for r, c in zip(old["responses"], original_cases, strict=True)
        ]
        legacy.append({"capture": n, "sha256": checksum, "outcomes": diagnoses})
        assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum
    summary = {
        "decision": decision,
        "runs": all_results,
        "changed_texts": [key for key in contents[0] if contents[0][key] != contents[1][key]],
        "prior_diagnostics": legacy,
        "configuration_fingerprint": base.fingerprint(config),
        "heldout_fingerprint": config["heldout_fingerprint"],
        "human_reviewed_rag_quality": "NOT_EVALUATED",
        "production_promotion": False,
    }
    # Metadata-only generated metrics, never response bodies or source excerpts.
    (OUTPUT / "contract-ab-evaluation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "prior_diagnostics"}))
