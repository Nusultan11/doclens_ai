from __future__ import annotations

import ctypes
import hashlib
import json
import os
import platform
import sys
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from doclens_ai.chunking.models import Chunk
from doclens_ai.dense_baseline.embeddings import DenseError, E5Embedder, Embedder, validate_vectors
from doclens_ai.dense_baseline.qdrant import QDRANT_IMAGE, QdrantIndex, point_id
from doclens_ai.evaluation.gold import GOLD_SCHEMA_VERSION, GoldDataset, load_gold_jsonl
from doclens_ai.evaluation.metrics import (
    QueryResults,
    RankedResult,
    _matched_evidence_by_rank,
    evaluate_retrieval,
    load_ranked_results_jsonl,
)
from doclens_ai.retrieval_baseline.bm25 import BM25Document, BM25Index
from doclens_ai.retrieval_baseline.runner import (
    FROZEN_GOLD_FINGERPRINT,
    RetrievalCorpus,
    _json,
    _percentile,
    build_corpus,
    chunk_evidence,
    results_jsonl,
    verify_corpus,
)

BM25_RESULTS_FINGERPRINT = "064bbdd32793c73bc352a34ad2dab69dc16f79faf623cbd3552d89df98917429"
BM25_REPORT_FINGERPRINT = "fea872420356de8ac4c0137f339b676e72737350499728c7a4aeca46d81587f0"


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def verify_reference(corpus: RetrievalCorpus, reference: dict[str, Any]) -> None:
    if corpus.metadata != reference.get("corpus"):
        raise DenseError("dense corpus/chunk identities differ from frozen BM25")
    index = BM25Index(BM25Document(chunk.chunk_id, chunk.text) for chunk in corpus.chunks)
    if index.fingerprint != reference.get("index_fingerprint"):
        raise DenseError("chunk texts differ from BM25 reference")


def rank_queries(
    index: QdrantIndex,
    embedder: Embedder,
    chunks: Mapping[str, Chunk],
    questions: Iterable[tuple[str, str]],
    *,
    dataset_revision: str,
) -> tuple[tuple[QueryResults, ...], dict[str, object]]:
    """Text/ID boundary: no Gold evidence, source filters, answerability, or split labels."""
    records = []
    inference_ms = []
    search_ms = []
    total_ms = []
    truncated = 0
    token_counts = []
    for question_id, text in sorted(questions):
        start = time.perf_counter()
        if text.strip():
            encoded = embedder.encode([text], kind="query")
            vector = validate_vectors(encoded.vectors, count=1, dimensions=embedder.dimensions)[0]
            truncated += encoded.truncated_count
            token_counts.extend(encoded.token_counts)
            after_inference = time.perf_counter()
            hits = index.search(vector)
            after_search = time.perf_counter()
        else:
            hits = ()
            after_inference = after_search = start
            token_counts.append(0)
        ranked = []
        for rank, hit in enumerate(hits, start=1):
            if hit.chunk_id not in chunks:
                raise DenseError("retrieved chunk identity missing from canonical local mapping")
            ranked.append(RankedResult(rank, chunk_evidence(chunks[hit.chunk_id]), hit.chunk_id))
        records.append(
            QueryResults(GOLD_SCHEMA_VERSION, dataset_revision, question_id, tuple(ranked))
        )
        inference_ms.append((after_inference - start) * 1000)
        search_ms.append((after_search - after_inference) * 1000)
        total_ms.append((time.perf_counter() - start) * 1000)
    return tuple(records), {
        "query_embedding_ms": inference_ms,
        "qdrant_search_ms": search_ms,
        "offline_query_total_ms": total_ms,
        "truncated_query_count": truncated,
        "query_token_counts": token_counts,
    }


def rank_diagnostics(
    gold: GoldDataset, dense: tuple[QueryResults, ...], bm25: tuple[QueryResults, ...]
) -> dict[str, object]:
    """After retrieval only: opaque per-query first-relevant-rank differences and Hit@1."""
    dense_by_id = {record.question_id: record for record in dense}
    bm25_by_id = {record.question_id: record for record in bm25}
    rows = []
    for example in gold.examples:
        ranks = {}
        for method, records in (("dense", dense_by_id), ("bm25", bm25_by_id)):
            matches = _matched_evidence_by_rank(
                example.evidence, records[example.question_id].results
            )
            ranks[method] = min((rank for rank, ids in matches.items() if ids), default=None)
        rows.append(
            {
                "question_id": example.question_id,
                "split": example.split.value,
                "answerable": example.answerable,
                **ranks,
            }
        )
    hit_at_1 = {}
    for split in ("dev", "test", "overall"):
        positives = [
            row
            for row in rows
            if row["answerable"] and (split == "overall" or row["split"] == split)
        ]
        hit_at_1[split] = {}
        for method in ("dense", "bm25"):
            n = sum(row[method] == 1 for row in positives)
            d = len(positives)
            hit_at_1[split][method] = {
                "numerator": n,
                "denominator": d,
                "value": n / d if d else None,
            }
    return {"first_relevant_rank": rows, "hit_at_1": hit_at_1}


def peak_process_rss_bytes() -> int:
    if os.name != "nt":
        import resource

        return int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            * (1 if sys.platform == "darwin" else 1024)
        )

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    if not psapi.GetProcessMemoryInfo(
        kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        raise DenseError("unable to measure process peak working set")
    return int(counters.PeakWorkingSetSize)


def run_dense(
    *,
    corpus_dir: Path,
    manifest_path: Path,
    gold_path: Path,
    bm25_dir: Path,
    model_dir: Path,
    qdrant_url: str,
    output_dir: Path,
) -> dict[str, object]:
    root = Path.cwd() / "evaluation-output"
    output = output_dir.resolve()
    if (
        root.is_symlink()
        or not output.is_relative_to(root.resolve())
        or not output.name.startswith("dense-v1-")
        or output.exists()
    ):
        raise DenseError("use a new evaluation-output/dense-v1-* directory")
    documents = verify_corpus(corpus_dir, manifest_path)
    gold = load_gold_jsonl(gold_path, corpus_manifest_path=manifest_path)
    if gold.fingerprint != FROZEN_GOLD_FINGERPRINT:
        raise DenseError("Gold differs from frozen reviewed v1")
    reference = json.loads((bm25_dir / "experiment.json").read_text(encoding="utf-8"))
    bm25_ranked = load_ranked_results_jsonl(bm25_dir / "ranked_results.jsonl")
    bm25_report = evaluate_retrieval(gold, bm25_ranked).to_dict()
    if (
        bm25_report["results_fingerprint"] != BM25_RESULTS_FINGERPRINT
        or bm25_report["report_fingerprint"] != BM25_REPORT_FINGERPRINT
        or bm25_report != json.loads((bm25_dir / "quality_report.json").read_text())
    ):
        raise DenseError("BM25 reference reports differ from frozen v1")
    preparation_start = time.perf_counter()
    corpus = build_corpus(documents)
    verify_reference(corpus, reference)
    if corpus.metadata["eligible_count"] != 56 or len(corpus.chunks) != 1092:
        raise DenseError("dense eligible/chunk counts differ from frozen full corpus")
    preparation_ms = (time.perf_counter() - preparation_start) * 1000
    embedder = E5Embedder(model_dir)
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    start = time.perf_counter()
    encoded = embedder.encode([chunk.text for chunk in corpus.chunks], kind="passage")
    embedding_ms = (time.perf_counter() - start) * 1000
    vectors = validate_vectors(encoded.vectors, count=len(chunks), dimensions=embedder.dimensions)
    index = QdrantIndex(
        qdrant_url, "dense_v1_" + output.name[9:].replace("-", "_"), dimensions=embedder.dimensions
    )
    try:
        start = time.perf_counter()
        index.create()
        collection_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        index.upsert(corpus.chunks, vectors)
        upsert_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        point_count = index.verify()
        verification_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        warm = embedder.encode(["warmup"], kind="query")
        index.search(warm.vectors[0])
        warmup_ms = (time.perf_counter() - start) * 1000
        records, latency = rank_queries(
            index,
            embedder,
            chunks,
            ((item.question_id, item.question) for item in gold.examples),
            dataset_revision=gold.dataset_revision,
        )
        index.verify()  # Detect index changes while the experiment was querying.
        diagnostics = rank_diagnostics(gold, records, bm25_ranked)
        experiment = {
            "baseline_version": "dense-v1",
            "corpus": corpus.metadata,
            "gold_fingerprint": gold.fingerprint,
            "model": embedder.metadata,
            "bm25_reference": {
                "version": "bm25-v1",
                "results_fingerprint": BM25_RESULTS_FINGERPRINT,
                "report_fingerprint": BM25_REPORT_FINGERPRINT,
            },
            "vector_fingerprint": _fingerprint(vectors),
            "point_identity_fingerprint": _fingerprint(sorted(point_id(c) for c in corpus.chunks)),
            "qdrant": {
                "image": QDRANT_IMAGE,
                "server_version": index.server_version,
                "configuration": index.configuration,
                "exact": True,
                "top_k": 10,
                "score_pool_limit": point_count,
                "point_count": point_count,
                "tie_break": "stable chunk ID; no score rounding",
            },
            "truncated_chunk_count": encoded.truncated_count,
            "truncated_query_count": latency["truncated_query_count"],
            "failed_chunk_count": 0,
            "failed_query_count": 0,
        }
    finally:
        index.close()
    output.mkdir(parents=True)
    ranked_path = output / "ranked_results.jsonl"
    ranked_path.write_text(results_jsonl(records), encoding="utf-8", newline="\n")
    parsed = load_ranked_results_jsonl(ranked_path)
    report = evaluate_retrieval(gold, parsed).to_dict()
    experiment.update(
        {
            "results_fingerprint": report["results_fingerprint"],
            "report_fingerprint": report["report_fingerprint"],
        }
    )
    timing = {
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "peak_process_rss_bytes": peak_process_rss_bytes(),
        "model_load_ms": embedder.load_ms,
        "corpus_preparation_ms": preparation_ms,
        "passage_embedding_ms": embedding_ms,
        "collection_creation_ms": collection_ms,
        "upsert_ms": upsert_ms,
        "index_verification_ms": verification_ms,
        "warmup_ms": warmup_ms,
        "query_sample_count": len(records),
        "percentile_method": "linear interpolation at (n-1)*p",
        "warm_query_samples": {key: value for key, value in latency.items() if key.endswith("ms")},
        "warm_query_summary": {
            key: {
                "p50_ms": _percentile(tuple(value), 0.5),
                "p95_ms": _percentile(tuple(value), 0.95),
            }
            for key, value in latency.items()
            if key.endswith("ms")
        },
    }
    for name, payload in (
        ("quality_report.json", report),
        ("experiment.json", experiment),
        ("rank_diagnostics.json", diagnostics),
        ("latency.json", timing),
    ):
        (output / name).write_text(_json(payload) + "\n", encoding="utf-8", newline="\n")
    return experiment
