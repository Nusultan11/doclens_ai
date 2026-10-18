"""Opt-in replay of two genuine ML-14 GPU captures. Never launches inference."""

import base64
import hashlib
import json
import os
import re
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tools/kaggle_gpu/outputs/ml14-paired-sufficiency-v1"
R = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_sufficiency_dev/benchmark.py"))


@pytest.mark.anyio
async def test_genuine_paired_gpu_repetitions():
    if os.environ.get("DOCLENS_RAG_SUFFICIENCY_REPLAY") != "1":
        pytest.skip("Opt in only after genuine ML-14 GPU captures")
    source = (ROOT / "tools/kaggle_gpu/rag_sufficiency_dev/benchmark.py").read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    registered = json.loads((OUT / "preregistration.json").read_text(encoding="utf-8"))
    assert (
        registered["protocol"] == R["preregistration"]()
        and registered["source_sha256"] == source_hash
    )
    for path, expected_hash in registered["post_validation_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected_hash
    versions = []
    metrics = []
    all_rows = []
    environments = []
    contents = []
    for repetition in (1, 2):
        folder = OUT / f"run-{repetition}"
        proof = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
        assert proof["status"] == "COMPLETE" and proof["private"] and not proof["internet"]
        assert proof["docker_image"] == R["KAGGLE_DOCKER_IMAGE"]
        # Kaggle's read API returns mount slugs without dataset version suffixes.
        expected_datasets = [R["RUNTIME_DATASET"], R["MODEL_DATASET"]]
        assert set(proof["datasets"]) == {d.rsplit("/", 1)[0] for d in expected_datasets}
        submitted = folder / "submitted-metadata.json"
        assert hashlib.sha256(submitted.read_bytes()).hexdigest() == proof["metadata_sha256"]
        metadata = json.loads(submitted.read_text(encoding="utf-8"))
        assert metadata["dataset_sources"] == expected_datasets
        assert metadata["is_private"] and not metadata["enable_internet"]
        assert metadata["docker_image"] == R["KAGGLE_DOCKER_IMAGE"]
        assert proof["source_sha256"] == source_hash
        assert (folder / "remote-source.py").read_bytes() == source
        capture = folder / "capture/rag_capture.json"
        log = folder / "capture/llama-server.log"
        assert hashlib.sha256(capture.read_bytes()).hexdigest() == proof["capture_sha256"]
        assert hashlib.sha256(log.read_bytes()).hexdigest() == proof["log_sha256"]
        text = log.read_text(encoding="utf-8")
        events = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", text)
        assert events and all(a == b == "37" for a, b in events)
        buffers = re.findall(r"CUDA0.*model buffer size\s*=\s*([\d.]+) MiB", text)
        assert buffers and max(map(float, buffers)) >= 4000
        report = json.loads(capture.read_text(encoding="utf-8"))
        environments.append(
            (
                report["python"],
                report["libraries"],
                report["runtime_version"],
                report["server_settings"],
            )
        )
        assert report["gpu_before"][0]["name"] == "Tesla T4"
        assert report["sampled_peaks"]["primary_gpu_used_mib"] >= 4096
        assert report["sampled_peaks"]["successful_samples"] > 0
        assert report["inference_started_at_utc"] > registered["registered_at_utc"]
        result, rows = await R["evaluate"](report, source_hash)
        assert result["planned"] == result["attempted"] == 24
        assert result["sufficient_denominator"] == result["insufficient_denominator"] == 12
        metrics.append(result)
        content = []
        for response in report["responses"]:
            try:
                envelope = json.loads(base64.b64decode(response["raw_body_b64"], validate=True))
                content.append(envelope["choices"][0]["message"]["content"])
            except (ValueError, KeyError, IndexError, TypeError):
                content.append(None)
        contents.append(content)
        all_rows.append(rows)
        versions.append(proof["version"])
    assert versions == [1, 2]
    assert environments[0] == environments[1]
    assert len(all_rows[0]) == len(all_rows[1]) == 24
    comparison = {
        "versions": versions,
        "metrics": metrics,
        "status_changes": sum(a["status"] != b["status"] for a, b in zip(*all_rows, strict=True)),
        "response_changes": sum(
            a["response_sha256"] != b["response_sha256"] for a, b in zip(*all_rows, strict=True)
        ),
        "content_changes": sum(a != b for a, b in zip(*contents, strict=True)),
        "production_authorized": False,
    }
    raw = json.dumps(comparison, sort_keys=True, indent=2) + "\n"
    destination = OUT / "comparison.json"
    if destination.exists():
        assert destination.read_text(encoding="utf-8") == raw
    else:
        destination.write_text(raw, encoding="utf-8")
    print(json.dumps(comparison, sort_keys=True))
