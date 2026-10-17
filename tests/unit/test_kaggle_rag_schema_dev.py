"""Deterministic ML-9 tests. Synthetic HTTP fixtures never claim GPU execution."""

import base64
import copy
import hashlib
import json
import runpy
from pathlib import Path

import pytest

from doclens_ai.llm.provider import strict_json
from doclens_ai.services.rag import SYSTEM_PROMPT, ModelAnswer

ROOT = Path(__file__).resolve().parents[2]
runner = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_schema_dev/benchmark.py"))


def cases():
    probes = runner["probe_cases"]()
    real_fixtures = [
        {"id": f"unit-dev-{i}", "request": copy.deepcopy(probes[0]["request"])} for i in range(15)
    ]
    return runner["paired_cases"](real_fixtures + probes)


def record(case, content=None):
    if content is None:
        content = {
            "answerable": False,
            "answer": None,
            "citations": [],
            "reason": "insufficient_evidence",
        }
    payload = {
        "model": runner["MODEL_ALIAS"],
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(content) if not isinstance(content, str) else content,
                },
            }
        ],
    }
    raw = json.dumps(payload).encode()
    return {
        **copy.deepcopy(case),
        "transport_status": "captured",
        "http_status": 200,
        "headers": {"content-type": "application/json"},
        "raw_body_b64": base64.b64encode(raw).decode(),
        "response_bytes": len(raw),
        "elapsed_seconds": 1,
        "usage": {"completion_tokens": 12},
    }


def capture():
    selected = cases()
    report = {
        "status": "complete",
        "gpu_offload_confirmed": True,
        "runtime_version": runner["RUNTIME_COMMIT"],
        "source_sha256": "unit-fixture",
        "configuration": runner["configuration"](),
        "configuration_fingerprint": runner["fingerprint"](runner["configuration"]()),
        "cases_fingerprint": runner["fingerprint"](selected),
        "responses": [record(c) for c in selected],
        "verified_artifacts": {
            "model_sha256": runner["MODEL_SHA256"],
            "runtime_archive_sha256": runner["RUNTIME_SHA256"],
            "llama_server_sha256": runner["SERVER_SHA256"],
        },
    }
    report["responses_fingerprint"] = runner["fingerprint"](report["responses"])
    return selected, report


def labels(selected):
    return {
        c["id"].rsplit("/", 1)[0]: {
            "split": "synthetic" if c["id"].startswith("probe-") else "dev",
            "answerable": False,
            "scope_verified": True,
        }
        for c in selected
    }


def unsafe_answer(case):
    evidence = strict_json(case["request"]["messages"][1]["content"])["evidence"][0]
    text = evidence["text"]
    value = "OMEGA" if "OMEGA" in text else "ALPHA"
    return {
        "answerable": True,
        "answer": value,
        "reason": None,
        "citations": [
            {
                "chunk_id": evidence["chunk_id"],
                "document_version_id": evidence["document_version_id"],
                "quote": text,
                "quote_start": 0,
                "quote_end": len(text),
                "answer_start": 0,
                "answer_end": len(value),
            }
        ],
    }


def test_schema_snapshot_matches_production_and_is_deterministic():
    assert runner["SCHEMA"] == ModelAnswer.model_json_schema()
    schema = runner["answer_schema"]()
    assert "$defs" not in schema and "$ref" not in json.dumps(schema)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"answerable", "answer", "citations", "reason"}
    assert schema["properties"]["citations"]["maxItems"] == 24
    answer = schema["properties"]["answer"]
    assert "maxLength" not in answer
    assert answer["anyOf"] == [{"type": "string", "maxLength": 8000}, {"type": "null"}]
    assert runner["fingerprint"](schema) == runner["fingerprint"](runner["answer_schema"]())
    assert runner["SYSTEM_PROMPT"] == SYSTEM_PROMPT


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "if": {}},
        {"anyOf": [{"type": "string"}], "maxLength": 8000},
        {"type": "string", "pattern": "unanchored"},
        {"type": "string", "pattern": "^a$", "maxLength": 1},
        {"type": "number", "minimum": 0},
        {"type": "object", "properties": {}, "anyOf": []},
        {"type": "array", "uniqueItems": True},
        {"$ref": "https://example.invalid/schema"},
    ],
)
def test_unsupported_schema_rejected_without_silent_downgrade(schema):
    with pytest.raises(ValueError):
        runner["check_schema_compatibility"](schema)


def test_ab_only_changes_decoding_and_order_is_deterministic():
    selected = cases()
    assert len(selected) == 38 and selected == cases()
    for index in range(19):
        pair = selected[index * 2 : index * 2 + 2]
        assert [c["id"].rsplit("/", 1)[1] for c in pair] == (
            ["A", "B"] if index % 2 == 0 else ["B", "A"]
        )
        left, right = [c["request"] for c in pair]
        assert {k: v for k, v in left.items() if k != "response_format"} == {
            k: v for k, v in right.items() if k != "response_format"
        }
        assert left["response_format"] != right["response_format"]


@pytest.mark.parametrize("raw", [b"{}", b'{"cases": []}', b'{"split":"test"}'])
def test_frozen_input_excludes_mutation_and_test(raw):
    with pytest.raises(ValueError, match="hash"):
        runner["validate_input"](raw)


@pytest.mark.parametrize(
    "content,status",
    [
        ('{"answerable":false,"answerable":true}', "invalid_json"),
        ("not JSON", "invalid_json"),
        (
            {"answerable": False, "answer": "", "citations": [], "reason": "insufficient_evidence"},
            "invalid_schema",
        ),
        (
            {"answerable": True, "answer": "ALPHA", "citations": [], "reason": None},
            "invalid_schema",
        ),
        ({}, "invalid_schema"),
    ],
)
@pytest.mark.anyio
async def test_malformed_or_inconsistent_outputs_never_repaired(content, status):
    observed, output, citations = await runner["replay"](record(cases()[0], content))
    assert observed == status and output is None and citations == []


@pytest.mark.parametrize("field", ["chunk_id", "document_version_id", "quote_end"])
@pytest.mark.anyio
async def test_foreign_or_invalid_citations(field):
    case = cases()[0]
    value = unsafe_answer(case)
    value["citations"][0][field] = (
        999 if field == "quote_end" else ("00000000-0000-0000-0000-000000009999")
    )
    status, output, citations = await runner["replay"](record(case, value))
    assert status == "invalid_citation" and output is not None and not citations


@pytest.mark.parametrize("arm", ["A", "B"])
@pytest.mark.anyio
async def test_valid_refusal_both_arms_through_unchanged_adapter(arm):
    case = next(c for c in cases() if c["id"].endswith("/" + arm))
    status, output, citations = await runner["replay"](record(case))
    assert status == "valid_refusal" and output.answer is None and not citations


@pytest.mark.parametrize("index", range(4))
@pytest.mark.anyio
async def test_known_unsafe_probes_can_pass_structural_validation(index):
    probe = runner["probe_cases"]()[index]
    case = {"id": probe["id"] + "/A", "request": probe["request"]}
    status, output, citations = await runner["replay"](record(case, unsafe_answer(case)))
    assert status == "valid_answer" and output and citations
    assert runner["candidate_decision"](1, True, False) == "REJECT"


@pytest.mark.parametrize(
    "mutation",
    [
        "source_sha256",
        "configuration_fingerprint",
        "cases_fingerprint",
        "responses_fingerprint",
        "runtime_version",
        "status",
    ],
)
def test_capture_provenance_rejects_tampering(mutation):
    selected, report = capture()
    report[mutation] = "tampered"
    with pytest.raises(ValueError):
        runner["verify_capture"](report, selected, "unit-fixture")


@pytest.mark.anyio
async def test_metrics_deterministic_invalid_refusal_not_counted_and_test_forbidden():
    selected, report = capture()
    result, _ = await runner["evaluate"](report, selected, labels(selected), "unit-fixture")
    again, _ = await runner["evaluate"](report, selected, labels(selected), "unit-fixture")
    assert result == again
    assert result["candidate_quality"] == "INCONCLUSIVE"
    assert result["production_authorization"] is False
    assert result["arms"]["A"]["counts"]["accepted"] == 19
    invalid = {
        "answerable": False,
        "answer": "",
        "citations": [],
        "reason": "insufficient_evidence",
    }
    report["responses"][0] = record(selected[0], invalid)
    report["responses_fingerprint"] = runner["fingerprint"](report["responses"])
    result, _ = await runner["evaluate"](report, selected, labels(selected), "unit-fixture")
    assert result["arms"]["A"]["counts"]["accepted"] == 18
    assert result["arms"]["A"]["counts"]["invalid_refusal_attempts"] == 1
    bad = labels(selected)
    bad[next(iter(bad))]["split"] = "test"
    with pytest.raises(ValueError, match="TEST"):
        await runner["evaluate"](report, selected, bad, "unit-fixture")


@pytest.mark.anyio
async def test_unsafe_acceptance_forces_reject_with_private_diagnostics():
    selected, report = capture()
    i = next(i for i, c in enumerate(selected) if c["id"].startswith("probe-"))
    report["responses"][i] = record(selected[i], unsafe_answer(selected[i]))
    report["responses_fingerprint"] = runner["fingerprint"](report["responses"])
    result, rows = await runner["evaluate"](report, selected, labels(selected), "unit-fixture")
    assert result["candidate_quality"] == "REJECT"
    assert all(r["production_authorized"] is False for r in rows)
    assert all(r["semantic_support"] == "NOT_EVALUATED" for r in rows)


def test_preregistration_has_no_expected_answers_and_freezes_source():
    selected = cases()
    source_hash = hashlib.sha256(Path(runner["__file__"]).read_bytes()).hexdigest()
    prereg = runner["preregistration"](selected, source_hash)
    assert prereg["source_sha256"] == source_hash and prereg["repetitions"] == 2
    assert prereg["only_experimental_variable"] == "response_format"
    assert prereg["production_authorized"] is False
    assert "expected_answer" not in json.dumps(prereg)
    assert runner["candidate_decision"](0, True, False) == "INCONCLUSIVE"


def test_report_contains_sanitized_aggregates_only():
    report = (ROOT / "docs/evaluation/rag_schema_dev_v1.md").read_text(encoding="utf-8")
    assert "PRODUCTION_AUTHORIZATION: false" in report
    assert "rgv1-q-" not in report and "raw_body_b64" not in report
    assert "-----BEGIN" not in report


def test_frozen_model_runtime_prompt_and_capture_functions_preserved():
    import ast

    baseline_path = ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py"
    baseline = runpy.run_path(str(baseline_path))
    for key in (
        "MODEL_REPO",
        "MODEL_REVISION",
        "MODEL_FILE",
        "MODEL_BYTES",
        "MODEL_SHA256",
        "RUNTIME_TAG",
        "RUNTIME_COMMIT",
        "RUNTIME_FILE",
        "RUNTIME_BYTES",
        "RUNTIME_SHA256",
        "SERVER_SHA256",
        "MODEL_ALIAS",
        "SETTINGS",
        "CONTEXT_TOKENS",
        "DEADLINE_SECONDS",
        "MAX_RESPONSE_BYTES",
        "SYSTEM_PROMPT",
        "PROMPT_HASH",
        "INPUT_SHA256",
        "CONTEXT_FINGERPRINT",
        "INPUT_DATASET",
        "MODEL_DATASET",
        "RUNTIME_DATASET",
        "GOLD_FINGERPRINT",
    ):
        assert runner[key] == baseline[key]
    trees = [
        ast.parse(path.read_text(encoding="utf-8"))
        for path in (baseline_path, Path(runner["__file__"]))
    ]
    functions = [
        {
            node.name: ast.dump(node, include_attributes=False)
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for tree in trees
    ]
    for name in ("capture", "gpu_snapshot", "sha256_file", "validate_input"):
        assert functions[0][name] == functions[1][name]


@pytest.mark.parametrize("mutation", ["http_status", "headers", "raw_body_b64"])
@pytest.mark.anyio
async def test_genuine_envelope_failures_not_schema_success(mutation):
    fixture = record(cases()[0])
    if mutation == "http_status":
        fixture[mutation] = 500
    elif mutation == "headers":
        fixture[mutation] = {"content-type": "text/html"}
    else:
        raw = b"{}"
        fixture[mutation] = base64.b64encode(raw).decode()
        fixture["response_bytes"] = len(raw)
    status, output, citations = await runner["replay"](fixture)
    assert status == "http_protocol_failure" and output is None and not citations


def test_kernel_metadata_only_existing_pinned_private_assets():
    metadata = json.loads(
        (ROOT / "tools/kaggle_gpu/rag_schema_dev/kernel-metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["is_private"] is True and metadata["enable_internet"] is False
    assert metadata["enable_gpu"] is True
    assert metadata["dataset_sources"] == [
        runner["RUNTIME_DATASET"],
        runner["MODEL_DATASET"],
        runner["INPUT_DATASET"],
    ]
    assert metadata["kernel_sources"] == metadata["model_sources"] == []


def test_nullable_sibling_bound_is_distributed_without_schema_loss(monkeypatch):
    function = runner["answer_schema"]
    expected = function()
    altered = copy.deepcopy(runner["SCHEMA"])
    nullable = altered["properties"]["answer"]
    bound = nullable["anyOf"][0].pop("maxLength")
    nullable["maxLength"] = bound
    monkeypatch.setitem(function.__globals__, "SCHEMA", altered)
    assert function() == expected
