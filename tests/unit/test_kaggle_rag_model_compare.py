"""Synthetic privacy, provenance and strict replay regressions; no remote actions."""

import ast
import copy
import hashlib
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.unit.test_kaggle_rag_baseline import freeze
from tests.unit.test_kaggle_rag_baseline import package as package

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def case_layout():
    return 15, 14, 0


@pytest.fixture
def runner():
    return runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py"))


def test_kernel_has_only_private_frozen_sources():
    m = json.loads((ROOT / "tools/kaggle_gpu/rag_model_compare/kernel-metadata.json").read_text())
    assert m["is_private"] and not m["enable_internet"] and m["enable_gpu"]
    assert len(m["dataset_sources"]) == 3 and all(
        s.rsplit("/", 1)[1].isdigit() for s in m["dataset_sources"]
    )
    assert not m["kernel_sources"] and not m["model_sources"]


def test_public_report_contains_no_raw_payload():
    path = ROOT / "docs/evaluation/rag_model_compare_dev_v1.md"
    text = path.read_text(encoding="utf-8")
    assert '"raw_body_b64"' not in text and '"messages"' not in text
    assert "postgresql+asyncpg://" not in text
    assert "NOT_EVALUATED" in text and "production" in text


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
