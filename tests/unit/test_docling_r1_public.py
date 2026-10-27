"""Contracts for the public-source Linux runner; no network or model inference."""

import io
import json
from pathlib import Path

import pytest

from tools.kaggle_gpu import docling_r1_public as runner


@pytest.mark.parametrize("name", ["../outside", "/absolute", "a/../../b", "a\\b"])
def test_upload_code_paths_cannot_escape_root(tmp_path, name):
    with pytest.raises(ValueError, match="unsafe_relative_path"):
        runner.safe_path(tmp_path, name)


def test_embedded_code_rejects_wrong_hash_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runner, "CONFIG", {"code": {"source.py": {"base64": "cGFzcw==", "sha256": "0" * 64}}}
    )
    with pytest.raises(ValueError, match="embedded_code_identity"):
        runner.install_code(tmp_path)
    assert not (tmp_path / "source.py").exists()


class Download(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.mark.parametrize("data", [b"wrong", b"too long"])
def test_unverified_public_original_is_never_published(tmp_path, monkeypatch, data):
    monkeypatch.setattr(runner.urllib.request, "urlopen", lambda *a, **k: Download(data))
    target = tmp_path / "source.pdf"
    with pytest.raises(ValueError, match="download_(identity_mismatch|size_exceeded)"):
        runner.download("https://example.invalid/source.pdf", target, "0" * 64, 5)
    assert not target.exists()
    assert target.with_suffix(".pdf.partial").exists()


def observation(text, page=1):
    return {"page": page, "text": text}


def test_missing_result_keeps_unknown_instead_of_zero():
    assert runner.comparison([observation("Count 003")], None)["status"] == "UNKNOWN"
    measured = runner.comparison([observation("Count 003")], [])
    assert measured["numeric_native"] == 1 and measured["numeric_retained"] == 0


def test_numeric_sign_zero_and_page_ownership_are_not_repaired():
    baseline = [observation("values 001.50 -2,5 +3 -4 12%")]
    candidate = [observation("values 1.50 2,5 +3 -4 12%", page=2)]
    result = runner.comparison(baseline, candidate)
    assert result["numeric_native"] == 5 and result["numeric_retained"] == 3
    assert result["numeric_lost"] == {"001.50": 1, "-2,5": 1}
    assert result["page_chunks_retained"] == 0
    same_text_wrong_page = runner.comparison(baseline, [observation(baseline[0]["text"], 2)])
    assert same_text_wrong_page["chunks_retained"] == 1
    assert same_text_wrong_page["page_chunks_retained"] == 0


def test_native_hashes_preserve_nan_but_exclude_only_explicit_timing(tmp_path):
    original = {"confidence": float("nan"), "status": "success", "timings": {"x": 2}}
    path = tmp_path / "conversion-metadata.json"
    path.write_text(json.dumps(original))
    first, errors = runner.captures(tmp_path, "docling")
    assert not errors
    original["timings"] = {"x": 9}
    path.write_text(json.dumps(original))
    assert runner.captures(tmp_path, "docling")[0] == first
    original["status"] = "partial_success"
    path.write_text(json.dumps(original))
    assert runner.captures(tmp_path, "docling")[0] != first
    with pytest.raises(ValueError):
        runner.fingerprint(float("nan"))


def test_partial_native_export_is_accounted_and_unchanged(tmp_path):
    path = tmp_path / "native.json"
    path.write_bytes(b'{"partial":')
    values, errors = runner.captures(tmp_path, "docling")
    assert not values and errors["native.json"]["type"] == "JSONDecodeError"
    assert errors["native.json"]["byte_sha256"] == runner.sha(path)
    assert path.read_bytes() == b'{"partial":'


def test_worker_environment_does_not_inherit_cloud_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("KAGGLE_API_TOKEN", "private-test-value")
    env = runner.environment(Path("/code"), tmp_path / "profile")
    assert "KAGGLE_API_TOKEN" not in env
    assert env["CUDA_VISIBLE_DEVICES"] == "" and env["HF_HUB_OFFLINE"] == "1"


def test_resource_percentiles_preserve_small_sample_scope():
    assert runner.percentiles([]) == {"n": 0, "p50": None, "p95": None}
    assert runner.percentiles([1, 3])["p50"] == 2
    assert runner.percentiles([1, 3])["p95"] == pytest.approx(2.9)


def test_venv_bootstrap_does_not_depend_on_platform_ensurepip():
    assert runner.venv_command("python", Path("/isolated")) == [
        "python",
        "-m",
        "venv",
        "--without-pip",
        str(Path("/isolated")),
    ]
