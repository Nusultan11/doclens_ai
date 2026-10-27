from __future__ import annotations

import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.models import (
    DocumentFormat,
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TextBlock,
)
from tools.extraction_campaign.run import run_one
from tools.extraction_quality import native_dev_baseline as baseline
from tools.extraction_quality.readiness_io import atomic


@pytest.fixture
def population(tmp_path, monkeypatch):
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    rows = []
    for index in range(5):
        path = tmp_path / f"source-{index}.pdf"
        path.write_bytes(b"%PDF-1.7\n" + str(index).encode())
        rows.append(
            {
                "id": f"source-{index}",
                "sha256": corpus.sha256(path),
                "source_reference": {
                    "path": path.name,
                    "sha256": corpus.sha256(path),
                    "size_bytes": path.stat().st_size,
                    "format": "pdf",
                },
                "format": "pdf",
                "split": "dev",
                "reserved_qa_family": False,
                "rights": {"local_evaluation": True},
                "family": f"family-{index}",
                "language": ["unknown"],
            }
        )
    rows[2]["split"] = "sealed_candidate"
    rows[3]["reserved_qa_family"] = True
    rows[4]["rights"]["local_evaluation"] = None
    return rows


COUNTS = {"registered": 5, "dev": 4, "sealed_candidate": 1, "eligible": 2}


def test_admission_uses_authoritative_records_and_excludes_sealed_qa_rights(population):
    registered, cohort = baseline.admission(population, COUNTS)
    assert len(cohort) == 2
    assert len(registered) == 5
    assert {r for row in registered for r in row["exclusion_reasons"]} == {
        "SEALED_CANDIDATE",
        "RESERVED_QA_FAMILY",
        "EVALUATION_RIGHTS_DENIED_OR_UNKNOWN",
    }
    assert all("source-" not in str(row) and "family-" not in str(row) for row in registered)
    population[4]["rights"]["local_evaluation"] = False
    assert baseline.admission(population, COUNTS)[0] == registered


@pytest.mark.parametrize(
    "mutation",
    ["test", "qa", "missing_qa", "rights", "sha", "size", "format", "duplicate", "count"],
)
def test_inconsistent_admission_fails_closed(population, mutation):
    row = population[0]
    if mutation in {"test", "qa"}:
        row["split"] = mutation
    elif mutation == "missing_qa":
        del row["reserved_qa_family"]
    elif mutation == "rights":
        row["rights"]["local_evaluation"] = 1
    elif mutation == "sha":
        row["sha256"] = "f" * 64
    elif mutation == "size":
        row["bytes"] = 999
    elif mutation == "format":
        row["format"] = "docx"
    elif mutation == "duplicate":
        population.append(deepcopy(row))
    else:
        population.pop()
    with pytest.raises((ValueError, KeyError)):
        baseline.admission(population, COUNTS)


def test_missing_modified_and_wrong_format_originals(population, tmp_path):
    asset = corpus.Asset.model_validate(population[0]["source_reference"])
    path = corpus.asset_path(tmp_path, asset)
    original = path.read_bytes()
    path.unlink()
    with pytest.raises(OSError):
        corpus.asset_path(tmp_path, asset)
    path.write_bytes(original.replace(b"0", b"1"))
    with pytest.raises(ValueError, match="bytes mismatch"):
        corpus.asset_path(tmp_path, asset)
    path.write_bytes(b"invalid format")
    bad = asset.model_copy(
        update={"sha256": corpus.sha256(path), "size_bytes": path.stat().st_size}
    )
    with pytest.raises(ValueError, match="signature"):
        corpus.asset_path(tmp_path, bad)


def receipt(status="completed", attempted=True):
    return {
        "status": status,
        "attempted_inference": attempted,
        "wall_seconds": 1.25,
        "peak_tree_rss_bytes": 123456,
        "exit_code": 0 if status == "completed" else 73,
    }


def native(metadata):
    return ExtractionResult(
        schema_version="1.1",
        document_format=DocumentFormat.PDF,
        status=ExtractionStatus.SUCCESS,
        source_sha256=metadata["sha256"],
        source_size_bytes=metadata["size_bytes"],
        blocks=(
            TextBlock(
                order=0,
                text="private sentinel 001 −2",
                source=SourceLocation(page_number=1, block_index=0),
            ),
        ),
    ).to_dict()


def test_full_capture_and_incomplete_outputs_are_accounted(population, tmp_path):
    _, cohort = baseline.admission(population, COUNTS)
    metadata = cohort[0]["metadata"]
    directory = tmp_path / "capture"
    value = native(metadata)
    atomic(directory / "native.json", value)
    atomic(directory / "result.json", {"native_status": "success"})
    row = baseline.capture_record(directory, metadata, receipt())
    assert row["status"] == "success"
    assert row["capture"]["structure"]["page_locators"] == 1
    assert row["capture"]["content_sha256"] == baseline.fingerprint(value)
    assert "private sentinel" not in str(baseline.summarize({"rows": [row]}))
    del value["note_references"]
    atomic(directory / "native.json", value)
    row = baseline.capture_record(directory, metadata, receipt())
    assert row["capture"] is None and row["status"] == "failed"
    (directory / "native.json").unlink()
    assert baseline.capture_record(directory, metadata, receipt())["status"] == "failed"
    atomic(directory / "native.json", native(metadata))
    (directory / "result.json").unlink()
    row = baseline.capture_record(directory, metadata, receipt())
    assert row["capture"] and row["failure"] == "incomplete_worker_output"


def test_capture_source_drift_is_fatal(population, tmp_path):
    _, cohort = baseline.admission(population, COUNTS)
    metadata = cohort[0]["metadata"]
    value = native(metadata)
    value["source_sha256"] = "e" * 64
    atomic(tmp_path / "native.json", value)
    with pytest.raises(ValueError, match="source identity drift"):
        baseline.capture_record(tmp_path, metadata, receipt())


@pytest.mark.parametrize("status", list(ExtractionStatus))
def test_native_status_and_error_are_preserved(population, tmp_path, status):
    _, cohort = baseline.admission(population, COUNTS)
    metadata = cohort[0]["metadata"]
    value = native(metadata)
    value["status"] = status.value
    value["error_category"] = "corrupt_document" if status == ExtractionStatus.FAILED else None
    atomic(tmp_path / "native.json", value)
    atomic(tmp_path / "result.json", {"native_status": status.value})
    row = baseline.capture_record(tmp_path, metadata, receipt())
    assert row["status"] == status.value
    assert row["failure"] == value["error_category"]
    assert row["capture"]["error_category"] == value["error_category"]
    if status == ExtractionStatus.FAILED:
        assert row["failure"] == ErrorCategory.CORRUPT_DOCUMENT.value


def test_complete_artifacts_verify_and_tampering_fails(population, tmp_path, monkeypatch):
    registered, cohort = baseline.admission(population, COUNTS)
    monkeypatch.setattr(baseline, "fresh_private", lambda path: None)
    monkeypatch.setattr(baseline, "EXPECTED", COUNTS)
    output = tmp_path / "evaluation-output" / "complete"
    config = {"policy": {}, "packages": {}}

    def executor(python, job, directory):
        metadata = next(r["metadata"] for r in cohort if r["metadata"]["id"] == job["document_id"])
        atomic(directory / "native.json", native(metadata))
        atomic(directory / "result.json", {"native_status": "success"})
        atomic(directory / "receipt.json", receipt())
        return receipt()

    runs = [
        baseline.run_pass(cohort, config, output / name, executor=executor)
        for name in ("pass-1", "pass-2")
    ]
    atomic(output / "protocol.json", {"registered": registered, "configuration": config})
    comparison = baseline.compare(*runs, {r["metadata"]["id"] for r in cohort})
    atomic(output / "reproducibility.json", comparison)
    complete = {
        "configuration": baseline.fingerprint(config),
        "registered": baseline.fingerprint(registered),
        "artifacts": baseline.artifact_hashes(output),
        "reproducibility": comparison,
        "all_attempted": True,
    }
    complete["fingerprint"] = baseline.fingerprint(complete)
    atomic(output / "COMPLETE.json", complete)
    result = baseline.verify(output)
    assert result["execution"] == "PASS"
    assert result["attempted_per_pass"] == [2, 2]
    capture = output / "pass-2" / cohort[0]["metadata"]["id"] / "native.json"
    value = corpus.read_json(capture)
    value["blocks"][0]["text"] = "tampered"
    atomic(capture, value)
    with pytest.raises(ValueError, match="modified baseline artifacts"):
        baseline.verify(output)


@pytest.mark.parametrize(
    "failure",
    ["timeout", "memory_limit", "output_limit", "failed", "control_failed", "cleanup_unverified"],
)
def test_failures_never_disappear_from_denominators(population, tmp_path, monkeypatch, failure):
    _, cohort = baseline.admission(population, COUNTS)
    monkeypatch.setattr(baseline, "fresh_private", lambda path: None)

    def executor(python, job, output):
        output.mkdir()
        return receipt(failure)

    run = baseline.run_pass(
        cohort, {"policy": {}, "packages": {}}, tmp_path / "run", executor=executor
    )
    summary = baseline.summarize(run)
    assert summary["accounted"] == summary["attempted"] == 2
    assert summary["statuses"] == {"failed": 2}
    assert summary["failures"] == {failure: 2}
    assert summary["full_captures"] == 0


def test_reproducibility_ignores_only_runtime_and_rejects_missing_duplicates(population, tmp_path):
    _, cohort = baseline.admission(population, COUNTS)
    metadata = cohort[0]["metadata"]
    atomic(tmp_path / "native.json", native(metadata))
    atomic(tmp_path / "result.json", {"native_status": "success"})
    row = baseline.capture_record(tmp_path, metadata, receipt())
    left = {"configuration": "same", "rows": [row]}
    right = deepcopy(left)
    right["rows"][0]["runtime"] = receipt("different_timing")
    expected = {row["id"]}
    assert baseline.compare(left, right, expected)["reproducible"]
    for key in ("sha256", "status", "capture", "deterministic_sha256"):
        changed = deepcopy(right)
        changed["rows"][0][key] = None
        assert not baseline.compare(left, changed, expected)["reproducible"]
    right["rows"].append(deepcopy(row))
    with pytest.raises(ValueError, match="duplicate"):
        baseline.compare(left, right, expected)
    with pytest.raises(ValueError, match="incomplete"):
        baseline.compare(left, {"configuration": "same", "rows": []}, expected)
    assert not baseline.compare(left, {**left, "configuration": "drift"}, expected)["reproducible"]


def test_private_destination_rejects_public_existing_and_not_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(baseline, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="private"):
        baseline.fresh_private(tmp_path / "docs" / "leak")
    private = tmp_path / "evaluation-output" / "new"
    private.mkdir(parents=True)
    with pytest.raises(ValueError, match="fresh"):
        baseline.fresh_private(private)
    destination = private / "another"
    monkeypatch.setattr(
        baseline.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 1})
    )
    monkeypatch.setattr(baseline, "git", lambda *args: "")
    with pytest.raises(ValueError, match="ignored and untracked"):
        baseline.fresh_private(destination)
    monkeypatch.setattr(
        baseline.subprocess, "run", lambda *a, **k: type("R", (), {"returncode": 0})
    )
    monkeypatch.setattr(baseline, "git", lambda *args: "already-tracked")
    with pytest.raises(ValueError, match="ignored and untracked"):
        baseline.fresh_private(destination)
    atomic(private / "RELEASE.json", {})
    with pytest.raises(ValueError, match="frozen"):
        baseline.fresh_private(destination)


def test_real_repository_ignore_and_incomplete_completion():
    baseline.fresh_private(baseline.ROOT / "evaluation-output" / "ex01-unused-test-destination")
    with pytest.raises(OSError):
        baseline.verify(baseline.ROOT / "evaluation-output" / "ex01-unused-test-destination")


@pytest.mark.skipif(os.name != "nt", reason="existing Windows job controls")
@pytest.mark.parametrize(
    "mode,expected",
    [("crash", "failed"), ("hang", "timeout"), ("output", "output_limit"), ("oom", "failed")],
)
def test_existing_resource_executor_failure_modes(mode, expected):
    # Genuine child processes, not fake timeouts or synthetic 199-document coverage.
    private = Path(tempfile.mkdtemp(prefix="ex01-probe-", dir=baseline.ROOT / "evaluation-output"))
    output = private / mode
    policy = {
        **baseline.POLICY,
        "wall_seconds_per_document": 3,
        "cpu_seconds": 3,
        "os_commit_bytes": 256 * 1024**2,
        "native_output_bytes": 128 * 1024,
        "minimum_available_ram_bytes": 0,
    }
    result = run_one(
        Path(sys.executable),
        {"candidate": "probe", "configuration": {"mode": mode}, "policy": policy},
        output,
    )
    assert result["status"] == expected
    assert result["attempted_inference"] is True
    assert result["remaining_owned_processes"] == []
    assert result["peak_tree_rss_bytes"] > 0
