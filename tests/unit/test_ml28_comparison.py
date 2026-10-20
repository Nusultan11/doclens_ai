"""Frozen comparison contracts and actual bounded subprocess probes."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from tests.unit.test_ml28_evidence import fixture
from tools.extraction_quality import table_comparison as benchmark
from tools.extraction_quality.pdf_table_review_packet import sha


def pin(arm):
    return benchmark.Pin(
        engine=arm,
        package_version="fixture-1",
        config_sha256="d" * 64,
        code_sha256="e" * 64,
        model_revisions=("fixture-model-v1",),
        model_artifacts=("f" * 64,),
        license_review_reference="public-fixture",
        dependencies_sha256="a" * 64,
    )


def captures():
    scope, gold, proposal, native = fixture()
    rows = {}
    for arm in benchmark.ARMS:
        rows[arm] = {
            scope.document_id: benchmark.Capture(
                scope=scope,
                pin=pin(arm),
                status="success",
                failure=None,
                page_text={1: native.blocks[0].text},
                proposal=None if arm == "pypdf" else proposal.model_copy(update={"engine": arm}),
                seconds=0.1,
                peak_rss_bytes=None,
                peak_gpu_bytes=None,
            )
        }
    return scope, gold, rows


def test_paired_metrics_and_unknown_native_structure():
    scope, gold, rows = captures()
    result = benchmark.compare((scope,), rows, {scope.document_id: gold}, allow_synthetic=True)
    paired = result["quality"]["documents"][0]
    assert paired["arms"]["pypdf"]["scores"]["cell_span"] is None
    for arm in benchmark.ARMS[1:]:
        metrics = paired["arms"][arm]["scores"]
        assert metrics["cell_span"]["matched"] == metrics["cell_span"]["expected"] == 5
        assert metrics["relationship"]["matched"] == 4
        assert metrics["locator"]["precision"] == 1
        assert paired["deltas"][arm]["new_losses"] == []
    assert result["quality"]["experiment"] == "INCONCLUSIVE"
    assert result["latency"]["pypdf"]["p95_seconds"] == 0.1


@pytest.mark.parametrize("failure", ["unavailable", "timeout", "memory_limit", "worker_failed"])
def test_failed_arms_stay_in_population_and_unknown_is_not_zero(failure):
    scope, gold, rows = captures()
    rows["mineru_basic"][scope.document_id] = benchmark.unavailable(
        scope, pin("mineru_basic"), failure
    )
    result = benchmark.compare((scope,), rows, {scope.document_id: gold}, allow_synthetic=True)
    assert result["quality"]["population"] == 1
    paired = result["quality"]["documents"][0]
    assert paired["arms"]["mineru_basic"]["scores"]["anchor_recall"] is None
    assert result["latency"]["mineru_basic"]["observed"] == 0
    assert result["latency"]["mineru_basic"]["denominator"] == 1
    assert result["quality"]["experiment"] == (
        "INCONCLUSIVE" if failure == "unavailable" else "REJECT"
    )


def test_new_native_anchor_loss_rejects_even_when_other_cells_improve():
    scope, gold, rows = captures()
    c = rows["mineru_basic"][scope.document_id]
    rows["mineru_basic"][scope.document_id] = c.model_copy(
        update={"page_text": {1: "Revenue Division 001.25 kg 2026-Q1"}}
    )
    result = benchmark.compare((scope,), rows, {scope.document_id: gold}, allow_synthetic=True)
    assert result["quality"]["experiment"] == "REJECT"
    assert len(result["quality"]["documents"][0]["deltas"]["mineru_basic"]["new_losses"]) == 1


def test_missing_gold_is_never_zero_errors():
    scope, _, rows = captures()
    result = benchmark.compare((scope,), rows)
    assert result["quality"]["quality"] == "NOT_EVALUATED"
    assert all(
        v is None
        for v in result["quality"]["documents"][0]["arms"]["mineru_basic"]["scores"].values()
    )


@pytest.mark.parametrize(
    "case",
    [
        "missing_arm",
        "missing_document",
        "extra_document",
        "duplicate",
        "wrong_tenant",
        "wrong_version",
        "synthetic_gold",
    ],
)
def test_population_identity_and_review_are_fail_closed(case):
    scope, gold, rows = captures()
    population = (scope,)
    if case == "missing_arm":
        rows.pop("mineru_basic")
    elif case == "missing_document":
        rows["mineru_basic"] = {}
    elif case == "extra_document":
        rows["mineru_basic"]["extra"] = rows["mineru_basic"][scope.document_id]
    elif case == "duplicate":
        population *= 2
    elif case in {"wrong_tenant", "wrong_version"}:
        c = rows["mineru_basic"][scope.document_id]
        key = "workspace_id" if case == "wrong_tenant" else "version_id"
        rows["mineru_basic"][scope.document_id] = c.model_copy(
            update={"scope": scope.model_copy(update={key: "wrong"})}
        )
    with pytest.raises(ValueError):
        benchmark.compare(
            population, rows, {scope.document_id: gold}, allow_synthetic=case != "synthetic_gold"
        )


def test_reproducibility_excludes_resources_but_includes_pins():
    scope, gold, rows = captures()
    first = benchmark.compare((scope,), rows, {scope.document_id: gold}, allow_synthetic=True)
    rows["mineru_basic"][scope.document_id] = rows["mineru_basic"][scope.document_id].model_copy(
        update={"seconds": 9.8, "peak_rss_bytes": 10000}
    )
    second = benchmark.compare((scope,), rows, {scope.document_id: gold}, allow_synthetic=True)
    assert first["fingerprint"] == second["fingerprint"]
    assert first["runtime"] != second["runtime"]
    c = rows["mineru_basic"][scope.document_id]
    rows["mineru_basic"][scope.document_id] = c.model_copy(
        update={"pin": c.pin.model_copy(update={"model_revisions": ("different",)})}
    )
    assert (
        first["fingerprint"]
        != benchmark.compare((scope,), rows, {scope.document_id: gold}, allow_synthetic=True)[
            "fingerprint"
        ]
    )


def test_duplicate_text_remains_unknown_and_false_cells_are_counted():
    scope, gold, rows = captures()
    c = rows["mineru_basic"][scope.document_id]
    repeated = c.model_copy(update={"page_text": {1: "-001.25 -001.25"}})
    metrics = benchmark.score(repeated, gold)
    assert metrics["anchor_recall"]["unknown"] == 1
    assert metrics["anchor_recall"]["recall"] is None
    assert benchmark._pr(["a"], ["a", "a", "b"])["false"] == 2
    assert benchmark._pr(["a"], ["a", "a", "b"])["duplicates"] == 1


def run_probe(tmp_path, content, *, budgets=None):
    pytest.importorskip("psutil", reason="offline process-tree monitor not installed")
    scope, _, rows = captures()
    source = tmp_path / "source.pdf"
    source.write_bytes(b"public synthetic RAW")
    scope = scope.model_copy(update={"raw_sha256": sha(source)})
    template = rows["mineru_basic"][scope.document_id].model_dump(mode="json")
    model = tmp_path / "public-model.bin"
    model.write_bytes(b"synthetic model artifact")
    template["pin"]["model_artifacts"] = [sha(model)]
    template["scope"] = scope.model_dump(mode="json")
    template["proposal"]["scope"] = scope.model_dump(mode="json")
    runner = tmp_path / "runner.py"
    runner.write_text(
        "import sys,json,hashlib,time\nfrom pathlib import Path\n"
        + "value=json.loads("
        + repr(json.dumps(template))
        + ")\n"
        + "value['pin']['code_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()\n"
        + content,
        encoding="utf-8",
    )
    frozen_pin = pin("mineru_basic").model_copy(
        update={"code_sha256": sha(runner), "model_artifacts": (sha(model),)}
    )
    result = benchmark.isolated_capture(
        source,
        scope,
        frozen_pin,
        executable=__import__("pathlib").Path(sys.executable),
        executable_sha256=sha(__import__("pathlib").Path(sys.executable)),
        runner=runner,
        output=tmp_path / "capture",
        budgets=budgets or benchmark.Budgets(),
        runtime_ready=True,
        model_files=(model,),
    )
    return result, template


def test_real_isolated_subprocess_capture(tmp_path):
    result, template = run_probe(tmp_path, "Path(sys.argv[2]).write_text(json.dumps(value))\n")
    assert result.status == "success" and result.failure is None
    assert result.seconds > 0 and result.peak_rss_bytes > 0
    assert result.page_text == {int(k): v for k, v in template["page_text"].items()}


@pytest.mark.parametrize("case", ["timeout", "oom", "invalid", "nonzero", "output", "wrong_page"])
def test_actual_worker_failures_are_isolated(tmp_path, case):
    budgets = benchmark.Budgets(
        seconds=0.2 if case == "timeout" else 10,
        rss_bytes=1 if case == "oom" else 1024**3,
        output_bytes=100 if case == "output" else 16 * 1024**2,
    )
    content = {
        "timeout": "time.sleep(30)\n",
        "oom": "time.sleep(30)\n",
        "invalid": "Path(sys.argv[2]).write_text('invalid')\n",
        "nonzero": "sys.exit(1)\n",
        "output": "Path(sys.argv[2]).write_text('X'*200)\n",
        "wrong_page": "value['scope']['version_id']='wrong'\n"
        "value['proposal']['scope']['version_id']='wrong'\n"
        "Path(sys.argv[2]).write_text(json.dumps(value))\n",
    }[case]
    result, _ = run_probe(tmp_path, content, budgets=budgets)
    expected = {
        "timeout": "timeout",
        "oom": "memory_limit",
        "invalid": "invalid_output",
        "nonzero": "worker_failed",
        "output": "output_limit",
        "wrong_page": "source_mismatch",
    }[case]
    assert result.failure == expected and result.page_text is None and result.proposal is None


def test_missing_runtime_does_not_launch(tmp_path, monkeypatch):
    scope, _, _ = captures()
    monkeypatch.setattr(benchmark.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    result = benchmark.isolated_capture(
        tmp_path / "source",
        scope,
        pin("mineru_basic"),
        executable=tmp_path / "python",
        executable_sha256="0" * 64,
        runner=tmp_path / "runner",
        output=tmp_path / "out",
        budgets=benchmark.Budgets(),
    )
    assert result.failure == "unavailable"


def test_declared_ready_but_missing_runtime_preserves_explicit_unknown(tmp_path, monkeypatch):
    scope, _, _ = captures()
    monkeypatch.setattr(benchmark.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned"))
    result = benchmark.isolated_capture(
        tmp_path / "source",
        scope,
        pin("mineru_basic"),
        executable=tmp_path / "missing-python",
        executable_sha256="0" * 64,
        runner=tmp_path / "missing-runner",
        output=tmp_path / "out",
        budgets=benchmark.Budgets(),
        runtime_ready=True,
    )
    assert result.status == "unknown" and result.proposal is None


def test_forged_trusted_state_is_not_a_capture_dimension():
    _, _, rows = captures()
    raw = copy.deepcopy(next(iter(rows["mineru_basic"].values())).model_dump(mode="json"))
    raw["trusted"] = True
    with pytest.raises(ValueError):
        benchmark.Capture.model_validate_json(json.dumps(raw))
