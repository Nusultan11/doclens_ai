import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.kaggle_gpu import extraction_preflight
from tools.kaggle_gpu.extraction_stage import sha, stage, verify


def test_current_local_synthetic_sources_are_readable_deterministic(tmp_path):
    from pypdf import PdfReader

    from tests.unit.test_extraction import _write_pdf

    # Retain the source-fidelity control using the maintained native parser fixture.
    for number, lines in enumerate(
        (("Count: 7",), ("Net mass: -001.50 kg",), ("Period: 2026", "Value: 003.00"))
    ):
        path = tmp_path / f"control-{number}.pdf"
        _write_pdf(path, ["\n".join(lines)])
        data = path.read_bytes()
        _write_pdf(path, ["\n".join(lines)])
        assert data == path.read_bytes()
        reader = PdfReader(BytesIO(data), strict=True)
        assert len(reader.pages) == 1
        text = reader.pages[0].extract_text()
        assert all(line in text for line in lines)


def test_stage_only_explicit_source(tmp_path):
    source = tmp_path / "source.py"
    source.write_bytes(b"print(1)\r\n")
    (tmp_path / ".env").write_text("PRIVATE_DO_NOT_UPLOAD")
    destination = tmp_path / "stage"
    manifest = stage(source, destination, slug="safe-test", title="Safe Test", internet=False)
    assert set(manifest) == {"runner.py", "kernel-metadata.json"}
    assert (destination / "runner.py").read_bytes() == b"print(1)\n"
    metadata = json.loads((destination / "kernel-metadata.json").read_text())
    assert metadata["is_private"] is True
    assert metadata["dataset_sources"] == []
    with pytest.raises(ValueError):
        stage(source, destination, slug="safe-test", title="Safe Test", internet=False)


def test_artifact_validation(tmp_path):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"run_id": "new", "source_sha256": "source"}))
    checksums = tmp_path / "checksums.json"
    checksums.write_text(json.dumps({"report.json": sha(report)}))
    assert verify(tmp_path, "source", "new", "report.json")["run_id"] == "new"
    with pytest.raises(ValueError, match="stale"):
        verify(tmp_path, "old", "new", "report.json")
    report.write_text("{}")
    with pytest.raises(ValueError, match="checksum"):
        verify(tmp_path, "source", "new", "report.json")
    checksums.write_text(json.dumps({"report.json": sha(report), "../secret": "bad"}))
    with pytest.raises(ValueError, match="unsafe"):
        verify(tmp_path, "source", "new", "report.json")


@pytest.mark.parametrize("payload", [b"bad", b"wrong", b"truncated", b"model"])
def test_current_staging_requires_pinned_weight_bytes(monkeypatch, tmp_path, payload):
    import hashlib

    from tools.extraction_campaign.staging import get_file

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: BytesIO(payload))
    output = tmp_path / "model.safetensors"
    args = {"expected_size": 5, "expected_sha256": hashlib.sha256(b"model").hexdigest()}
    if payload == b"model":
        assert (
            get_file("https://unused.invalid", output, **args)["sha256"] == args["expected_sha256"]
        )
        assert output.read_bytes() == payload
    else:
        with pytest.raises(ValueError, match="download_(identity_mismatch|budget)"):
            get_file("https://unused.invalid", output, **args)
        assert not output.exists()  # Unverified bytes never become a published weight.


@pytest.mark.parametrize("available", [True, False])
def test_current_preflight_initializes_cuda_before_stats_and_rejects_cpu(
    monkeypatch, tmp_path, available
):
    import sys

    initialized = False

    def ones(shape, *, device):
        nonlocal initialized
        if device == "cuda:0":
            if not available:
                raise RuntimeError("CUDA required")
            initialized = True
        return Matrix(device)

    class Matrix:
        def __init__(self, device):
            self.device = device

        def __matmul__(self, other):
            return self

        def __eq__(self, value):
            assert value == 512
            return SimpleNamespace(all=lambda: SimpleNamespace(item=lambda: True))

    def stats(index):
        assert initialized and index == 0
        return 128

    cuda = SimpleNamespace(
        device_count=lambda: 1,
        max_memory_allocated=stats,
        get_device_properties=lambda _: SimpleNamespace(name="synthetic", total_memory=1024),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            set_num_threads=lambda _: None,
            ones=ones,
            cuda=cuda,
            version=SimpleNamespace(cuda="fixture"),
        ),
    )
    metrics = SimpleNamespace(_asdict=lambda: {"total": 1024})
    monkeypatch.setitem(
        sys.modules,
        "psutil",
        SimpleNamespace(
            virtual_memory=lambda: metrics,
            disk_usage=lambda _: metrics,
        ),
    )
    monkeypatch.setattr(
        extraction_preflight, "Path", lambda p: tmp_path if str(p) == "/kaggle/working" else Path(p)
    )
    assert extraction_preflight.main() == (0 if available else 1)
    report = json.loads((tmp_path / "preflight.json").read_text())
    assert report["status"] == ("completed" if available else "failed")
    assert ("peak_cuda_allocated_bytes" in report) is available
    if available:
        assert report["cuda:0"]["valid"] and report["cuda:0"]["device"] == "cuda:0"


def test_cli_requires_explicit_reviewed_source(monkeypatch, tmp_path):
    from tools.kaggle_gpu import extraction_stage

    base = ["extraction-stage", "docling", str(tmp_path / "stage"), "--run-id", "fixture"]
    monkeypatch.setattr("sys.argv", base)
    with pytest.raises(SystemExit) as error:
        extraction_stage.main()
    assert error.value.code == 2
    calls = []
    monkeypatch.setattr(extraction_stage, "configured_stage", lambda *a, **k: calls.append((a, k)))
    source = tmp_path / "explicit.py"
    monkeypatch.setattr("sys.argv", [*base, "--source", str(source)])
    extraction_stage.main()
    assert len(calls) == 1 and calls[0][0][0] == source
    assert calls[0][0][2]["run_id"] == "fixture"
