"""Opt-in private ML-7 replay; never issues inference requests or reads TEST outputs."""

import asyncio
import base64
import json
import os
import runpy
from collections import Counter
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[2]
runner = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py"))
helpers = runpy.run_path(str(ROOT / "tests/integration/test_kaggle_rag_baseline.py"))


async def replay_dev(report, cases, gold, alias):
    """Reconstruct exactly the already packed context, without retrieval or repacking."""
    from doclens_ai.core.rag_config import RagSettings
    from doclens_ai.evaluation.rag_metrics import percentile, ratio
    from doclens_ai.services.rag import EvidenceContext
    from doclens_ai.services.retrieval import SourceLocator, VerifiedResult

    settings = RagSettings(
        _env_file=None,
        endpoint=runner["configuration"]()["endpoint"],
        model_id=alias,
        max_output_tokens=1024,
        timeout_seconds=120,
    )
    labels = {e.question_id: e for e in gold.examples if e.split == "dev"}
    assert len(labels) == 15 and {c["id"] for c in cases} == set(labels)
    records = {r["id"]: r for r in report["responses"] if r["id"] in labels}
    assert len(records) == 15
    statuses, reviews, latencies = [], [], []
    negative_answers = correct_refusals = positive_answers = citation_count = 0
    for case in cases:
        record, label = records[case["id"]], labels[case["id"]]
        messages = case["request"]["messages"]
        assert record["request"]["messages"] == messages
        packed = json.loads(messages[1]["content"])["evidence"]
        # Packed export omits workspace/source hashes. They are unused by citation validation.
        # Do not infer either identity from Gold or claim fresh authorization/source anchoring.
        hits = tuple(
            VerifiedResult(
                **{
                    k: UUID(h[k])
                    for k in ("chunk_id", "document_id", "document_version_id", "index_revision_id")
                },
                workspace_id=UUID(int=0),
                source_sha256="",
                score=0.0,
                text=h["text"],
                locator=SourceLocator.model_validate(h["source_locator"]),
            )
            for h in packed
        )
        context = EvidenceContext(hits, tuple(h.text for h in hits), messages)
        status, output, citations = await runner["replay"](record, context, settings)
        statuses.append(status)
        latencies.append(record["elapsed_seconds"] * 1000)
        positive_answers += status == "valid_answer" and label.answerable
        negative_answers += status == "valid_answer" and not label.answerable
        correct_refusals += status == "valid_refusal" and not label.answerable
        citation_count += len(citations)
        content = None
        try:
            content = json.loads(base64.b64decode(record["raw_body_b64"]))["choices"][0]["message"][
                "content"
            ]
        except (ValueError, KeyError, IndexError, TypeError):
            pass
        reviews.append(
            {
                "question_id": case["id"],
                "classification": status,
                "raw_capture": record,
                "raw_model_content_unrepaired": content,
                "packed_evidence": packed,
                "schema_valid_model_output": output.model_dump(mode="json") if output else None,
                "delivered_citations": [c.model_dump(mode="json") for c in citations],
                "gold_reference_local_only": label.model_dump(mode="json"),
                "gold_fingerprint": gold.fingerprint,
                "experiment_fingerprint": report["configuration_fingerprint"],
                "input_sha256": report["configuration"]["input_sha256"],
                "output_fingerprint": runner["fingerprint"](record),
                "human_review_status": "NOT_EVALUATED",
            }
        )
    counts = dict(Counter(statuses))
    accepted = sum(s in {"valid_answer", "valid_refusal"} for s in statuses)
    required = sum(len(e.required_citation_refs) for e in labels.values())
    metrics = {
        "case_count": 15,
        "positive_count": sum(e.answerable for e in labels.values()),
        "negative_count": sum(not e.answerable for e in labels.values()),
        "classifications": counts,
        "strict_acceptance": ratio(accepted, 15),
        "accepted_positive_answers": positive_answers,
        "correct_accepted_positives": "NOT_EVALUATED" if positive_answers else ratio(0, 12),
        "incorrect_accepted_positives": "NOT_EVALUATED" if positive_answers else ratio(0, 12),
        "unsupported_accepted_answers": "NOT_EVALUATED"
        if positive_answers or negative_answers
        else ratio(0, 15),
        "correct_negative_refusals": ratio(correct_refusals, 3),
        "unsafe_negative_acceptances": ratio(negative_answers, 3),
        "json_failure": ratio(counts.get("invalid_json", 0), 15),
        "schema_failure": ratio(counts.get("invalid_schema", 0), 15),
        "citation_failure": ratio(counts.get("invalid_citation", 0), 15),
        "runtime_protocol_failure": ratio(
            sum(
                s
                not in {
                    "valid_answer",
                    "valid_refusal",
                    "invalid_json",
                    "invalid_schema",
                    "invalid_citation",
                }
                for s in statuses
            ),
            15,
        ),
        "delivered_citation_count": citation_count,
        "required_evidence_coverage": "NOT_EVALUATED_SOURCE_IDENTITY_UNAVAILABLE"
        if citation_count
        else ratio(0, required),
        "latency_ms": {"p50": percentile(latencies, 0.5), "p95": percentile(latencies, 0.95)},
        "sampled_peaks": report["sampled_peaks"],
        "resource_scope": "whole server process, including startup; ML-6 includes its 20-case run",
        "human_semantic_quality": "NOT_EVALUATED",
    }
    return metrics, reviews


@pytest.mark.anyio
async def test_model_compare_dev_capture():
    selected = os.environ.get("DOCLENS_RAG_MODEL_COMPARE_RUN")
    if not selected:
        pytest.skip("Opt in with DOCLENS_RAG_MODEL_COMPARE_RUN pointing to private capture")
    from doclens_ai.evaluation.rag_gold import load_rag_gold

    root = await asyncio.to_thread(Path(selected).resolve)
    assert root.is_relative_to((ROOT / "evaluation-output").resolve())
    assert root.name.startswith("rag-model-compare-")
    gold = load_rag_gold(
        ROOT / "local-evaluation/rag_gold_v1_approved.jsonl",
        manifest_path=ROOT / "docs/eda/corpus_v1_manifest.csv",
    )
    original = ROOT / (
        "evaluation-output/rag-real-export-ae3d74f4fcf14fcea7ae8361e071dfe8/"
        "kaggle-input-candidate.json"
    )
    dev_raw = runner["select_dev_input"](original.read_bytes(), gold)
    assert dev_raw == (root / "input-stage/dev-input.json").read_bytes()
    cases = runner["validate_input"](dev_raw)
    candidate = json.loads((root / "capture/rag_capture.json").read_text(encoding="utf-8"))
    baseline_path = ROOT / (
        "evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/"
        "capture/rag_capture.json"
    )
    assert runner["sha256_file"](baseline_path) == (
        "90a01c4166f2e079877d1afafe4ba0a3bff2f527506fcf67ec56b921e6d4b2df"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    source = (ROOT / "tools/kaggle_gpu/rag_model_compare/benchmark.py").read_bytes()
    import hashlib

    runner["verify_capture"](candidate, cases, hashlib.sha256(source).hexdigest())
    runner["assert_comparable"](candidate, baseline, cases)
    assert candidate["status"] == "complete"
    assert candidate["gpu_offload_confirmed"] is True
    assert candidate["gpu_before"][0]["name"] == "Tesla T4"
    assert runner["RUNTIME_COMMIT"][:8] in candidate["runtime_version"]
    offload = helpers["gpu_offload_counts"](
        (root / "capture/llama-server.log").read_text(encoding="utf-8")
    )
    assert all(r["transport_status"] == "captured" for r in candidate["responses"])
    new, packet = await replay_dev(candidate, cases, gold, runner["MODEL_ALIAS"])
    old, _ = await replay_dev(
        baseline, cases, gold, baseline["configuration"]["request_settings"]["model"]
    )
    status = runner["safety_decision"](new, old)
    comparison = {
        "status": status,
        "baseline_dev": old,
        "candidate_dev": new,
        "candidate_gpu_offload": {
            "offloaded": offload[0],
            "total": offload[1],
            "events": offload[2],
        },
        "human_semantic_quality": "NOT_EVALUATED",
        "production_promotion": False,
    }
    helpers["preserve_or_write_json"](root / "comparison.json", comparison)
    helpers["preserve_or_write_json"](root / "human-output-review.json", packet)
    print(json.dumps(comparison))
