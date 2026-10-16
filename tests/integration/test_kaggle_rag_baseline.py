"""Opt-in strict replay of the private ML-6 capture, without remote actions."""

import asyncio
import base64
import json
import os
import re
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
runner = runpy.run_path(str(ROOT / "tools/kaggle_gpu/rag_baseline/benchmark.py"))
validate_input = runner["validate_input"]
verify_capture = runner["verify_capture"]
configuration = runner["configuration"]
fingerprint = runner["fingerprint"]
replay = runner["replay"]
MODEL_ALIAS = runner["MODEL_ALIAS"]


def preserve_or_write_json(path, value):
    """Replay must never overwrite a previously frozen metric or review packet."""
    if path.exists():
        assert json.loads(path.read_text(encoding="utf-8")) == value
    else:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gpu_offload_counts(runtime_log):
    layers = re.findall(r"\boffloaded\s+(\d+)/(\d+)\s+layers to GPU", runtime_log)
    assert layers and "CUDA0" in runtime_log
    counts = [tuple(map(int, pair)) for pair in layers]
    assert all(offloaded == total and total > 0 for offloaded, total in counts)
    assert len(set(counts)) == 1
    return *counts[0], len(counts)


async def evaluate_capture(report, package, manifest, gold, *, source_sha256):
    """Offline strict replay only; never assert live PostgreSQL authorization."""
    from collections import Counter
    from uuid import UUID, uuid4

    from doclens_ai.core.rag_config import RagSettings
    from doclens_ai.evaluation.rag_metrics import (
        EvaluationCase,
        evaluate_rag,
        output_fingerprint,
        ratio,
    )
    from doclens_ai.llm.provider import strict_json
    from doclens_ai.services.rag import AnswerResponse, RagOutcome, pack_context
    from doclens_ai.services.retrieval import SourceLocator, VerifiedResult

    cases = validate_input(json.dumps(package, ensure_ascii=False, indent=2).encode() + b"\n")
    verify_capture(report, cases, source_sha256)
    if {e.question_id for e in gold.examples} != {c["id"] for c in cases}:
        raise ValueError("Gold case mismatch")
    settings = RagSettings(
        _env_file=None,
        enabled=True,
        endpoint=configuration()["endpoint"],
        model_id=MODEL_ALIAS,
        max_output_tokens=1024,
        timeout_seconds=120,
    )
    observations, reviews, statuses = [], [], []
    citation_attempts = accepted_citations = 0
    by_id = {c["question_id"]: c for c in manifest["cases"]}
    labels = {e.question_id: e for e in gold.examples}
    for case, record in zip(cases, report["responses"], strict=True):
        saved = by_id[case["id"]]
        hits = tuple(
            VerifiedResult(
                **{
                    **h,
                    **{
                        key: UUID(h[key])
                        for key in (
                            "chunk_id",
                            "document_id",
                            "document_version_id",
                            "index_revision_id",
                            "workspace_id",
                        )
                    },
                    "locator": SourceLocator.model_validate(h["locator"]),
                }
            )
            for h in saved["retrieved"]
        )
        context = pack_context(saved["question"], hits, settings)
        if context.messages != case["request"]["messages"]:
            raise ValueError("frozen context mismatch")
        status, output, citations = await replay(record, context, settings)
        statuses.append(status)
        citation_attempts += len(output.citations) if output else 0
        accepted_citations += len(citations)
        outcome = None
        if status in {"valid_answer", "valid_refusal"}:
            cited_ids = {c.chunk_id for c in citations}
            outcome = RagOutcome(
                AnswerResponse(
                    answerable=output.answerable,
                    answer=output.answer,
                    citations=citations,
                    reason=output.reason,
                    request_id=uuid4(),
                ),
                record["elapsed_seconds"] * 1000,
                len(context.evidence),
                False,
                tuple(h for h in context.evidence if str(h.chunk_id) in cited_ids),
                len(hits),
            )
        failure_kind = "model" if outcome is None and not status.startswith("invalid_") else None
        observations.append(
            EvaluationCase(
                case["id"], outcome, record["elapsed_seconds"] * 1000, outcome is None, failure_kind
            )
        )
        label = labels[case["id"]]
        raw_model_content = None
        try:
            envelope = strict_json(base64.b64decode(record["raw_body_b64"]))
            raw_model_content = envelope["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            pass
        reviews.append(
            {
                "question_id": case["id"],
                "question": saved["question"],
                "classification": status,
                "raw_model_content_unrepaired": raw_model_content,
                "schema_valid_model_output": output.model_dump(mode="json") if output else None,
                "raw_capture": record,
                "delivered_response": outcome.response.model_dump(mode="json") if outcome else None,
                "actual_cited_evidence": [
                    h
                    for h in saved["retrieved"]
                    if any(c.chunk_id == h["chunk_id"] for c in citations)
                ],
                "gold_reference_local_only": label.model_dump(mode="json"),
                "gold_fingerprint": gold.fingerprint,
                "experiment_fingerprint": fingerprint(configuration()),
                "output_fingerprint": output_fingerprint(outcome)
                if outcome
                else fingerprint(record),
                "human_review_status": "NOT_EVALUATED",
            }
        )
    metrics = evaluate_rag(gold, observations, experiment=configuration())
    counts = dict(Counter(statuses))
    metrics["classifications"] = counts
    normalize = lambda value: " ".join(value.split()).casefold()  # noqa: E731
    positive_matches = 0
    for o in observations:
        label = labels[o.question_id]
        refs = label.accepted_answers or (
            [label.reference_answer] if label.reference_answer else []
        )
        positive_matches += bool(
            label.answerable
            and o.outcome
            and o.outcome.response.answerable
            and normalize(o.outcome.response.answer) in {normalize(r) for r in refs}
        )
    metrics["positive_lexical_exact_match"] = ratio(
        positive_matches, sum(e.answerable for e in gold.examples)
    )
    metrics["invalid_output_rate"] = ratio(sum(s.startswith("invalid_") for s in statuses), 20)
    metrics["generation_failure_rate"] = ratio(
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
        20,
    )
    metrics["citation_structural_validity"] = ratio(accepted_citations, citation_attempts)
    metrics["missing_retrieval_context_count"] = sum(
        c["missing_context"] for c in manifest["cases"]
    )
    metrics["retrieval_failure_count"] = 0
    metrics["scope"] = "staged offline capture replay; no live PostgreSQL revalidation"
    metrics["prior_production_safety"] = "REJECT"
    metrics["human_semantic_quality"] = "NOT_EVALUATED"
    groups = {}
    for field in ("split", "category"):
        groups[field] = {}
        for value in sorted({getattr(e, field) for e in gold.examples}):
            subset = tuple(e for e in gold.examples if getattr(e, field) == value)
            ids = {e.question_id for e in subset}
            selected = gold.model_copy(update={"examples": subset})
            groups[field][value] = evaluate_rag(
                selected,
                [o for o in observations if o.question_id in ids],
                experiment=configuration(),
            )
    for field, values in groups.items():
        for value, group in values.items():
            selected_statuses = [
                status
                for case, status in zip(cases, statuses, strict=True)
                if getattr(labels[case["id"]], field) == value
            ]
            group["classifications"] = dict(Counter(selected_statuses))
            group["invalid_output_rate"] = ratio(
                sum(status.startswith("invalid_") for status in selected_statuses),
                len(selected_statuses),
            )
    metrics["groups"] = groups
    return metrics, reviews


@pytest.mark.anyio
async def test_real_rag_capture_replay():
    selected = os.environ.get("DOCLENS_RAG_REAL_RUN")
    if not selected:
        pytest.skip("Opt in with DOCLENS_RAG_REAL_RUN pointing to private captured run")
    from doclens_ai.evaluation.rag_gold import load_rag_gold

    root = await asyncio.to_thread(Path(selected).resolve)
    assert root.is_relative_to((ROOT / "evaluation-output").resolve())
    frozen = ROOT / "evaluation-output/rag-real-export-ae3d74f4fcf14fcea7ae8361e071dfe8"
    package = json.loads((frozen / "kaggle-input-candidate.json").read_text(encoding="utf-8"))
    manifest = json.loads((frozen / "retrieval-snapshot.json").read_text(encoding="utf-8"))
    report = json.loads((root / "capture/rag_capture.json").read_text(encoding="utf-8"))
    freeze = json.loads((root / "freeze.json").read_text())
    gold = load_rag_gold(
        ROOT / "local-evaluation/rag_gold_v1_approved.jsonl",
        manifest_path=ROOT / "docs/eda/corpus_v1_manifest.csv",
    )
    metrics, reviews = await evaluate_capture(
        report, package, manifest, gold, source_sha256=freeze["source_sha256"]
    )
    expected_status = os.environ.get("DOCLENS_RAG_REAL_EXPECT_STATUS", "complete")
    assert expected_status in {"complete", "runtime_failure"}
    assert report["status"] == expected_status
    if expected_status == "complete":
        assert report["gpu_offload_confirmed"] is True
        runtime_log = await asyncio.to_thread(
            (root / "capture/llama-server.log").read_text, encoding="utf-8"
        )
        offloaded, total, events = gpu_offload_counts(runtime_log)
        metrics["explicit_gpu_offload_events"] = events
        assert runner["RUNTIME_COMMIT"][:8] in report["runtime_version"]
        metrics["explicit_gpu_layers_offloaded"] = offloaded
        metrics["explicit_gpu_layers_total"] = total
    else:
        assert report["gpu_offload_confirmed"] is False
        assert report["failure_type"] == "RuntimeError"
    metrics["kernel_execution_status"] = report["status"]
    metrics["gpu_offload_gate"] = report["gpu_offload_confirmed"]
    metrics["kernel_execution_accepted"] = expected_status == "complete"
    assert report["gpu_before"][0]["name"] == "Tesla T4"
    assert len(reviews) == 20
    preserve_or_write_json(root / "metrics.json", metrics)
    preserve_or_write_json(root / "human-output-review.json", reviews)
    print(
        json.dumps(
            {
                "classifications": metrics["classifications"],
                "invalid_output_rate": metrics["invalid_output_rate"],
                "generation_failure_rate": metrics["generation_failure_rate"],
                "latency_ms": metrics["latency_ms"],
            }
        )
    )
