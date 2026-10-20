"""Synthetic privacy, provenance and strict replay regressions; no remote actions."""

import base64
import copy
import hashlib
import json
import runpy
from pathlib import Path

import pytest

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.services.rag import EvidenceContext

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(params=("rag_baseline", "rag_model_compare"))
def runner(request):
    """Exercise both frozen runners with the same privacy/provenance regressions."""
    return runpy.run_path(str(ROOT / "tools/kaggle_gpu" / request.param / "benchmark.py"))


@pytest.fixture
def case_layout(runner):
    return {"rag_baseline": (20, 18, 1), "rag_model_compare": (15, 14, 0)}[
        Path(runner["__file__"]).parent.name
    ]


@pytest.fixture
def package(runner, case_layout):
    count, full_evidence_count, remaining_evidence = case_layout
    cases = []
    for i in range(count):
        evidence = [{"text": "synthetic"}] * (6 if i < full_evidence_count else remaining_evidence)
        messages = [
            {"role": "system", "content": runner["SYSTEM_PROMPT"]},
            {
                "role": "user",
                "content": json.dumps({"question": "Synthetic?", "evidence": evidence}),
            },
        ]
        cases.append(
            {
                "question_id": f"synthetic-{i}",
                "question": "Synthetic?",
                "messages": messages,
                "context_fingerprint": runner["fingerprint"](messages),
            }
        )
    return {"schema_version": 1, "experiment": {}, "cases": cases}


def freeze(runner, package, monkeypatch):
    raw = json.dumps(package).encode()
    namespace = runner["validate_input"].__globals__
    monkeypatch.setitem(namespace, "INPUT_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setitem(
        namespace,
        "CONTEXT_FINGERPRINT",
        runner["fingerprint"](
            [{"question_id": c["question_id"], "messages": c["messages"]} for c in package["cases"]]
        ),
    )
    return raw


def test_complete_frozen_input(runner, package, monkeypatch):
    raw = freeze(runner, package, monkeypatch)
    assert len(runner["validate_input"](raw)) == len(package["cases"])
    with pytest.raises(ValueError, match="hash"):
        runner["validate_input"](raw + b" ")


@pytest.mark.parametrize("change", ["missing", "duplicate", "gold", "prompt", "chunks"])
def test_export_completeness_and_leakage(runner, package, monkeypatch, change):
    if change == "missing":
        package["cases"].pop()
    if change == "duplicate":
        package["cases"][-1] = copy.deepcopy(package["cases"][0])
    if change == "gold":
        package["cases"][0]["reference_answer"] = "private gold"
    if change == "prompt":
        package["cases"][0]["messages"][0]["content"] = "changed"
    if change == "chunks":
        package["cases"][0]["messages"][1]["content"] = '{"evidence":[]}'
    raw = freeze(runner, package, monkeypatch)
    with pytest.raises(ValueError):
        runner["validate_input"](raw)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "content,expected",
    [
        (
            '{"answerable":false,"answer":null,"citations":[],"reason":"insufficient_evidence"}',
            "valid_refusal",
        ),
        ("not json", "invalid_json"),
        ('{"answerable":false,"answerable":true}', "invalid_json"),
        ('{"answerable":false}', "invalid_schema"),
        (
            json.dumps(
                {
                    "answerable": True,
                    "answer": "x",
                    "reason": None,
                    "citations": [
                        {
                            "chunk_id": "00000000-0000-0000-0000-000000000001",
                            "document_version_id": "00000000-0000-0000-0000-000000000002",
                            "quote": "x",
                            "quote_start": 0,
                            "quote_end": 1,
                            "answer_start": 0,
                            "answer_end": 1,
                        }
                    ],
                }
            ),
            "invalid_citation",
        ),
    ],
)
async def test_strict_replay(runner, content, expected):
    settings = RagSettings(
        _env_file=None,
        endpoint=runner["configuration"]()["endpoint"],
        model_id=runner["MODEL_ALIAS"],
        max_output_tokens=1024,
        timeout_seconds=120,
    )
    messages = [
        {"role": "system", "content": runner["SYSTEM_PROMPT"]},
        {"role": "user", "content": "synthetic"},
    ]
    request = {**runner["SETTINGS"], "messages": messages}
    raw = json.dumps(
        {
            "model": runner["MODEL_ALIAS"],
            "choices": [
                {"finish_reason": "stop", "message": {"role": "assistant", "content": content}}
            ],
        }
    ).encode()
    record = {
        "transport_status": "captured",
        "request": request,
        "http_status": 200,
        "headers": {"content-type": "application/json"},
        "raw_body_b64": base64.b64encode(raw).decode(),
        "response_bytes": len(raw),
    }
    result = await runner["replay"](record, EvidenceContext((), (), messages), settings)
    assert result[0] == expected


@pytest.mark.anyio
async def test_timeout_is_not_refusal(runner):
    result = await runner["replay"]({"transport_status": "timeout"}, None, None)
    assert result == ("timeout", None, [])


def test_provenance_rejects_substituted_source(runner):
    with pytest.raises(ValueError, match="source"):
        runner["verify_capture"]({"source_sha256": "wrong"}, [], "expected")


def test_kernel_has_only_private_frozen_sources():
    m = json.loads((ROOT / "tools/kaggle_gpu/rag_baseline/kernel-metadata.json").read_text())
    assert m["is_private"] and not m["enable_internet"] and m["enable_gpu"]
    assert len(m["dataset_sources"]) == 2 and all(
        s.rsplit("/", 1)[1].isdigit() for s in m["dataset_sources"]
    )
    assert not m["kernel_sources"] and not m["model_sources"]


@pytest.mark.parametrize(
    "change", ["binding", "duplicate", "artifact", "configuration", "response_hash"]
)
def test_capture_provenance_rejects_tampering(runner, package, monkeypatch, change):
    cases = runner["validate_input"](freeze(runner, package, monkeypatch))
    responses = [{"id": c["id"], "request": c["request"]} for c in cases]
    report = {
        "source_sha256": "source",
        "configuration": runner["configuration"](),
        "configuration_fingerprint": runner["fingerprint"](runner["configuration"]()),
        "cases_fingerprint": runner["fingerprint"](cases),
        "responses": responses,
        "verified_artifacts": {
            "model_sha256": runner["MODEL_SHA256"],
            "runtime_archive_sha256": runner["RUNTIME_SHA256"],
            "llama_server_sha256": runner["SERVER_SHA256"],
        },
    }
    if change == "binding":
        responses[0]["request"] = {"messages": []}
    if change == "duplicate":
        responses[-1] = copy.deepcopy(responses[0])
    if change == "artifact":
        report["verified_artifacts"]["model_sha256"] = "wrong"
    if change == "configuration":
        report["configuration"] = {}
    report["responses_fingerprint"] = runner["fingerprint"](responses)
    if change == "response_hash":
        report["responses_fingerprint"] = "wrong"
    with pytest.raises(ValueError):
        runner["verify_capture"](report, cases, "source")


@pytest.mark.anyio
async def test_http_failure_is_not_refusal(runner):
    settings = RagSettings(
        _env_file=None,
        endpoint=runner["configuration"]()["endpoint"],
        model_id=runner["MODEL_ALIAS"],
        max_output_tokens=1024,
        timeout_seconds=120,
    )
    messages = [{"role": "user", "content": "synthetic"}]
    raw = b"{}"
    record = {
        "transport_status": "captured",
        "request": {**runner["SETTINGS"], "messages": messages},
        "http_status": 500,
        "headers": {"content-type": "application/json"},
        "raw_body_b64": base64.b64encode(raw).decode(),
        "response_bytes": len(raw),
    }
    result = await runner["replay"](record, EvidenceContext((), (), messages), settings)
    assert result == ("http_protocol_failure", None, [])


def test_public_report_contains_no_raw_payload():
    path = ROOT / "docs/evaluation/rag_real_baseline_v1.md"
    text = path.read_text(encoding="utf-8")
    assert '"raw_body_b64"' not in text and '"messages"' not in text
    assert "postgresql+asyncpg://" not in text
    assert "NOT_EVALUATED" in text and "REJECT" in text


def test_offload_gate_keeps_verified_server_logging(runner):
    source = Path(runner["__file__"]).read_text()
    assert '"--verbosity",\n            "5",' in source
    assert '"offloaded" in text and "layers to GPU" in text' in source


@pytest.mark.parametrize(
    "log",
    [
        "",
        "CUDA0 selected; GPU memory 3731 MiB",
        "CUDA0 offloaded 0/29 layers to GPU",
        "CUDA0 offloaded 28/29 layers to GPU",
        "CUDA0 offloaded 29/29 layers to GPU; offloaded 28/28 layers to GPU",
    ],
)
def test_gpu_provenance_rejects_missing_partial_or_conflicting_offload(log):
    helper = runpy.run_path(str(ROOT / "tests/integration/test_kaggle_rag_baseline.py"))
    with pytest.raises(AssertionError):
        helper["gpu_offload_counts"](log)


def test_gpu_provenance_accepts_consistent_repeated_load_events():
    helper = runpy.run_path(str(ROOT / "tests/integration/test_kaggle_rag_baseline.py"))
    assert helper["gpu_offload_counts"](
        "CUDA0 load_tensors: offloaded 29/29 layers to GPU\n"
        "load_tensors: offloaded 29/29 layers to GPU\n"
    ) == (29, 29, 2)


@pytest.mark.parametrize("same", [True, False])
def test_replay_never_overwrites_frozen_packet(tmp_path, monkeypatch, same):
    helper = runpy.run_path(str(ROOT / "tests/integration/test_kaggle_rag_baseline.py"))
    path = tmp_path / "frozen.json"
    path.write_text('{"private": "synthetic"}\n', encoding="utf-8")
    before = path.read_bytes()

    def forbidden_write(*args, **kwargs):
        raise AssertionError("frozen packet must not be written")

    monkeypatch.setattr(Path, "write_text", forbidden_write)
    if same:
        helper["preserve_or_write_json"](path, {"private": "synthetic"})
    else:
        with pytest.raises(AssertionError):
            helper["preserve_or_write_json"](path, {"private": "changed"})
    assert path.read_bytes() == before


def test_replay_can_create_new_packet(tmp_path):
    helper = runpy.run_path(str(ROOT / "tests/integration/test_kaggle_rag_baseline.py"))
    path = tmp_path / "new.json"
    helper["preserve_or_write_json"](path, {"synthetic": True})
    assert json.loads(path.read_text(encoding="utf-8")) == {"synthetic": True}
