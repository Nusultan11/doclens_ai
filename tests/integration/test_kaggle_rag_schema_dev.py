"""Opt-in genuine ML-9 capture replay. Never launches a model or remote job."""

import hashlib
import json
import os
import re
import runpy
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "tools/kaggle_gpu/outputs/rag-schema-dev-v1"
runner = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_schema_dev/benchmark.py"))


def preserve(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)


@pytest.mark.anyio
async def test_genuine_schema_ab_repetitions():
    if os.environ.get("DOCLENS_RAG_SCHEMA_REPLAY") != "1":
        pytest.skip("Opt in with DOCLENS_RAG_SCHEMA_REPLAY=1; genuine private captures required")
    source = (ROOT / "tools/kaggle_gpu/rag_schema_dev/benchmark.py").read_bytes()
    source_hash = hashlib.sha256(source).hexdigest()
    original = ROOT / "evaluation-output/rag-model-compare-dev-v1/input-stage/dev-input.json"
    raw = original.read_bytes()
    cases = runner["paired_cases"](runner["validate_input"](raw) + runner["probe_cases"]())
    prereg = json.loads((PRIVATE / "preregistration.json").read_text(encoding="utf-8"))
    assert prereg == runner["preregistration"](cases, source_hash)
    registration = json.loads((PRIVATE / "preregistration-timestamp.json").read_text())
    assert (
        registration["preregistration_sha256"]
        == hashlib.sha256((PRIVATE / "preregistration.json").read_bytes()).hexdigest()
    )
    labels = json.loads((PRIVATE / "labels.json").read_text(encoding="utf-8"))
    review = json.loads((PRIVATE / "label-review.json").read_text(encoding="utf-8"))
    assert review["operator_confirmed_synthetic_labels"] is True
    assert review["probe_fingerprint"] == runner["fingerprint"](runner["synthetic_probes"]())
    assert review["labels_fingerprint"] == runner["fingerprint"](labels)
    assert len(labels) == 19
    assert sum(label["split"] == "dev" for label in labels.values()) == 15
    assert sum(label["answerable"] for label in labels.values()) == 12
    all_metrics, all_rows = [], []
    libraries = []
    versions = []
    for repetition in (1, 2):
        folder = PRIVATE / f"run-{repetition}"
        provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
        assert provenance["status"] == "COMPLETE"
        assert provenance["source_sha256"] == source_hash
        assert provenance["private"] is True and provenance["internet"] is False
        assert provenance["datasets"] == [
            runner["RUNTIME_DATASET"],
            runner["MODEL_DATASET"],
            runner["INPUT_DATASET"],
        ]
        assert hashlib.sha256((folder / "remote-source.py").read_bytes()).hexdigest() == source_hash
        versions.append(provenance["version"])
        capture_path = folder / "capture/rag_capture.json"
        assert hashlib.sha256(capture_path.read_bytes()).hexdigest() == provenance["capture_sha256"]
        log_path = folder / "capture/llama-server.log"
        assert hashlib.sha256(log_path.read_bytes()).hexdigest() == provenance["log_sha256"]
        report = json.loads(capture_path.read_text(encoding="utf-8"))
        log = (folder / "capture/llama-server.log").read_text(encoding="utf-8")
        offloads = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", log)
        assert offloads and all(pair == ("37", "37") for pair in offloads)
        assert report["gpu_before"][0]["name"] == "Tesla T4"
        libraries.append(report["libraries"])
        assert datetime.fromisoformat(report["inference_started_at_utc"]) > datetime.fromisoformat(
            registration["at_utc"]
        )
        assert prereg["source_sha256"] == report["source_sha256"]
        assert prereg["cases_fingerprint"] == report["cases_fingerprint"]
        assert prereg["configuration_fingerprint"] == report["configuration_fingerprint"]
        result, rows = await runner["evaluate"](report, cases, labels, source_hash)
        all_metrics.append(result)
        all_rows.append(rows)
    assert versions[0] != versions[1]
    assert libraries[0] == libraries[1]
    comparison = {
        "runs": all_metrics,
        "versions": versions,
        "paired_classification_regressions": {},
        "production_authorization": False,
    }
    for repetition, rows in enumerate(all_rows, 1):
        paired = {}
        for row in rows:
            identity, arm = row["id"].rsplit("/", 1)
            paired.setdefault(identity, {})[arm] = row["classification"]
        accepted = {"valid_answer", "valid_refusal"}
        comparison["paired_classification_regressions"][str(repetition)] = {
            "A_accepted_B_rejected": sum(
                p["A"] in accepted and p["B"] not in accepted for p in paired.values()
            ),
            "A_rejected_B_accepted": sum(
                p["A"] not in accepted and p["B"] in accepted for p in paired.values()
            ),
            "classification_changes": sum(p["A"] != p["B"] for p in paired.values()),
        }
    first = {row["id"]: row["classification"] for row in all_rows[0]}
    second = {row["id"]: row["classification"] for row in all_rows[1]}
    accepted = {"valid_answer", "valid_refusal"}
    comparison["between_repetition_changes"] = {
        arm: {
            "classification_changes": sum(
                first[identity] != second[identity]
                for identity in first
                if identity.endswith("/" + arm)
            ),
            "accepted_then_rejected": sum(
                first[identity] in accepted and second[identity] not in accepted
                for identity in first
                if identity.endswith("/" + arm)
            ),
            "rejected_then_accepted": sum(
                first[identity] not in accepted and second[identity] in accepted
                for identity in first
                if identity.endswith("/" + arm)
            ),
        }
        for arm in ("A", "B")
    }
    preserve(PRIVATE / "comparison.json", comparison)
    preserve(PRIVATE / "output-review-private.json", all_rows)
    assert original.read_bytes() == raw
    print(json.dumps(comparison))
