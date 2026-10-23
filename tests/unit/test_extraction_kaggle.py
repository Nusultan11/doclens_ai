import json
from io import BytesIO
from types import SimpleNamespace

import pytest

from tools.kaggle_gpu.extraction_remote import CASES, synthetic_pdf
from tools.kaggle_gpu.extraction_stage import sha, stage, verify


def test_synthetic_sources_are_readable_deterministic():
    from pypdf import PdfReader

    for lines in CASES.values():
        data = synthetic_pdf(lines)
        assert data == synthetic_pdf(lines)
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


def test_missing_pinned_weight_rejected_before_inference(monkeypatch, tmp_path):
    from tools.kaggle_gpu import extraction_remote as remote

    monkeypatch.setattr(
        remote,
        "CONFIG",
        {
            "assets": [
                {
                    "name": "fixture",
                    "repo": "public/fixture",
                    "revision": "fixed",
                    "patterns": ["*.safetensors"],
                    "sha256": {"model.safetensors": "expected"},
                }
            ]
        },
    )
    monkeypatch.setattr(
        remote, "public_snapshot", lambda *args: {"files": {"config.json": "other"}}
    )
    with pytest.raises(RuntimeError, match="missing_pinned"):
        remote.pinned_prepare(tmp_path)


def test_cuda_stats_initialize_context_and_reject_cpu():
    from tools.kaggle_gpu.extraction_remote import initialize_cuda

    class LazyCuda:
        initialized = False

        def is_available(self):
            return True

        def init(self):
            self.initialized = True

        def set_device(self, index):
            assert self.initialized and index == 0

        def reset_peak_memory_stats(self, index):
            if not self.initialized:
                raise RuntimeError("Invalid device argument")
            assert index == 0

    cuda = LazyCuda()
    with pytest.raises(RuntimeError, match="Invalid device"):
        cuda.reset_peak_memory_stats(0)
    initialize_cuda(SimpleNamespace(cuda=cuda))
    with pytest.raises(RuntimeError, match="required_cuda"):
        initialize_cuda(SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
