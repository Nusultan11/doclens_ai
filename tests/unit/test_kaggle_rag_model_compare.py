"""Synthetic privacy, provenance and strict replay regressions; no remote actions."""

import ast
import base64
import copy
import hashlib
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.services.rag import EvidenceContext

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def runner():
    return runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py"))


@pytest.fixture
def package(runner):
    cases = []
    for i in range(15):
        evidence = [{"text": "synthetic"}] * (6 if i < 14 else 0)
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
    assert len(runner["validate_input"](raw)) == 15
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
    m = json.loads((ROOT / "tools/kaggle_gpu/rag_model_compare/kernel-metadata.json").read_text())
    assert m["is_private"] and not m["enable_internet"] and m["enable_gpu"]
    assert len(m["dataset_sources"]) == 3 and all(
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
    path = ROOT / "docs/evaluation/rag_model_compare_dev_v1.md"
    if not path.exists():
        pytest.skip("Report is written after actual capture replay")
    text = path.read_text(encoding="utf-8")
    assert '"raw_body_b64"' not in text and '"messages"' not in text
    assert "postgresql+asyncpg://" not in text
    assert "NOT_EVALUATED" in text and "production" in text


def test_offload_gate_keeps_verified_server_logging():
    source = (ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py").read_text()
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


def test_selection_excludes_test_and_exports_no_labels(runner, package, monkeypatch):
    frozen = freeze(runner, package, monkeypatch)
    test = copy.deepcopy(package["cases"][0])
    test["question_id"] = "held-out-test"
    original = {**package, "cases": [*package["cases"], test]}
    raw = json.dumps(original).encode()
    namespace = runner["select_dev_input"].__globals__
    monkeypatch.setitem(namespace, "ORIGINAL_INPUT_SHA256", hashlib.sha256(raw).hexdigest())
    gold = SimpleNamespace(
        fingerprint=runner["GOLD_FINGERPRINT"],
        examples=[
            SimpleNamespace(question_id=c["question_id"], split="dev", reference_answer="SECRET")
            for c in package["cases"]
        ]
        + [SimpleNamespace(question_id="held-out-test", split="test")],
    )
    # select_dev_input uses the production canonical serialization.
    canonical = (
        (json.dumps(package, ensure_ascii=False, indent=2) + "\n").replace("\n", "\r\n").encode()
    )
    monkeypatch.setitem(namespace, "INPUT_SHA256", hashlib.sha256(canonical).hexdigest())
    selected = runner["select_dev_input"](raw, gold)
    assert selected == canonical and b"SECRET" not in selected and b"held-out-test" not in selected
    assert len(json.loads(selected)["cases"]) == 15
    assert frozen != selected  # Different serialization, identical packed messages.
    gold.examples.pop(0)
    with pytest.raises(ValueError, match="15 DEV"):
        runner["select_dev_input"](raw, gold)


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"is_private": False, "owner": "nurs2005", "collaborators": []},
        {"is_private": True, "owner": "other", "collaborators": []},
        {"is_private": True, "owner": "nurs2005", "collaborators": ["other"]},
    ],
)
def test_privacy_fails_closed(runner, metadata):
    with pytest.raises(ValueError, match="visibility"):
        runner["validate_private_metadata"](metadata)


def test_comparability_rejects_prompt_and_generation_changes(runner, package, monkeypatch):
    cases = runner["validate_input"](freeze(runner, package, monkeypatch))
    candidate = {"configuration": runner["configuration"]()}
    baseline = {"configuration": copy.deepcopy(candidate["configuration"]), "responses": cases}
    runner["assert_comparable"](candidate, baseline, cases)
    baseline["configuration"]["seed"] = 43
    with pytest.raises(ValueError, match="configuration"):
        runner["assert_comparable"](candidate, baseline, cases)
    baseline["configuration"]["seed"] = 42
    changed = copy.deepcopy(cases)
    changed[0]["request"]["messages"][0]["content"] = "changed"
    with pytest.raises(ValueError, match="messages"):
        runner["assert_comparable"](candidate, baseline, changed)


def test_frozen_generation_and_replay_code_is_unchanged(runner):
    baseline_path = ROOT / "tools/kaggle_gpu/rag_baseline/benchmark.py"
    baseline = runpy.run_path(str(baseline_path))
    candidate_path = ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py"

    def functions(path):
        return {
            n.name: ast.dump(n)
            for n in ast.parse(path.read_text(encoding="utf-8")).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    old, new = functions(baseline_path), functions(candidate_path)
    # main differs only in the public experiment identifier.
    for name in ("capture", "replay", "gpu_snapshot", "sha256_file"):
        assert old[name] == new[name]
    assert runner["SYSTEM_PROMPT"] == baseline["SYSTEM_PROMPT"]
    for name in ("RUNTIME_SHA256", "SERVER_SHA256", "RUNTIME_COMMIT", "RUNTIME_BYTES"):
        assert runner[name] == baseline[name]
    assert runner["MODEL_SHA256"] == (
        "8c2f07f26af9747e41988551106f149b03eb9b5cb6df636027b6bf6278473300"
    )
    assert runner["MODEL_BYTES"] == 4280404704


@pytest.mark.parametrize(
    "accepted,negative,unsafe,expected",
    [
        (0, 0, 0, "FIX"),
        (1, 0, 0, "CANDIDATE_FOR_FURTHER_EVALUATION"),
        (2, 1, 0, "REJECT"),
        (2, 0, 1, "REJECT"),
    ],
)
def test_safety_gate_never_promotes_or_ignores_unsafe_acceptance(
    runner, accepted, negative, unsafe, expected
):
    new = {
        "strict_acceptance": {"numerator": accepted},
        "unsafe_negative_acceptances": {"numerator": negative},
    }
    old = {"strict_acceptance": {"numerator": 0}}
    assert runner["safety_decision"](new, old, observed_unsafe_acceptances=unsafe) == expected
