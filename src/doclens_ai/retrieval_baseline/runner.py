"""Verified corpus -> frozen chunks -> text-only BM25 -> existing evaluator."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path

from doclens_ai.chunking.core import chunk_document
from doclens_ai.chunking.models import (
    Chunk,
    ChunkingConfig,
    ChunkingStatus,
    ChunkingStrategy,
    config_as_dict,
)
from doclens_ai.evaluation.gold import (
    GOLD_SCHEMA_VERSION,
    EvidenceLocator,
    GoldDataset,
    load_gold_jsonl,
)
from doclens_ai.evaluation.metrics import (
    QueryResults,
    RankedResult,
    RetrievedAnchor,
    evaluate_retrieval,
    load_ranked_results_jsonl,
)
from doclens_ai.extraction.models import DocumentFormat, ExtractionStatus
from doclens_ai.extraction.parsers import extract_file
from doclens_ai.retrieval_baseline.bm25 import BM25Config, BM25Document, BM25Index

FROZEN_GOLD_FINGERPRINT = "d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94"
FROZEN_CHUNKING = ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE)
FROZEN_BM25 = BM25Config()


class BaselineError(ValueError):
    """A sanitized prerequisite or experiment failure; not a quality threshold."""


@dataclass(frozen=True, slots=True)
class VerifiedDocument:
    document_id: str
    sha256: str
    size_bytes: int
    document_format: DocumentFormat
    path: Path

    def identity(self) -> dict[str, object]:
        return {
            "document_id": self.document_id,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "format": self.document_format.value,
        }


@dataclass(frozen=True, slots=True)
class RetrievalCorpus:
    chunks: tuple[Chunk, ...]
    metadata: dict[str, object]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fingerprint(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def verify_corpus(
    corpus_dir: Path, manifest_path: Path, *, expected_source_count: int = 90
) -> tuple[VerifiedDocument, ...]:
    """Resolve identities by verified bytes, independent of filenames or traversal order."""
    if not corpus_dir.is_dir() or corpus_dir.is_symlink():
        raise BaselineError("corpus directory missing or symlinked")
    identities: dict[str, tuple[str, int, DocumentFormat]] = {}
    document_ids: set[str] = set()
    with manifest_path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            document_id = row.get("document_id", "")
            sha = row.get("sha256", "")
            if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", document_id):
                raise BaselineError("manifest document ID is invalid")
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                raise BaselineError("manifest SHA-256 is invalid")
            if sha in identities or document_id in document_ids:
                raise BaselineError("duplicate manifest identity")
            try:
                size = int(row["size_bytes"])
                document_format = DocumentFormat(row["format"])
            except (KeyError, ValueError) as exc:
                raise BaselineError("invalid manifest size or format") from exc
            if size <= 0:
                raise BaselineError("manifest size must be positive")
            document_ids.add(document_id)
            identities[sha] = (document_id, size, document_format)
    if len(identities) != expected_source_count:
        raise BaselineError("manifest source count differs from frozen expectation")
    verified: dict[str, VerifiedDocument] = {}
    for path in sorted(corpus_dir.rglob("*")):
        if path.is_symlink():
            raise BaselineError("corpus symlinks are not allowed")
        if not path.is_file():
            continue
        sha = file_sha256(path)
        if sha not in identities:
            raise BaselineError("corpus contains unapproved or modified bytes")
        if sha in verified:
            raise BaselineError("corpus contains duplicate source bytes")
        document_id, size, document_format = identities[sha]
        if path.stat().st_size != size or path.suffix.casefold() != "." + document_format:
            raise BaselineError(f"source size or format mismatch: {document_id}")
        verified[sha] = VerifiedDocument(document_id, sha, size, document_format, path)
    if verified.keys() != identities.keys():
        raise BaselineError("corpus is missing approved sources")
    return tuple(sorted(verified.values(), key=lambda item: item.document_id))


def build_corpus(documents: tuple[VerifiedDocument, ...]) -> RetrievalCorpus:
    """No Gold input here: every verified source goes through the same extraction gate."""
    chunks: list[Chunk] = []
    exclusions: list[dict[str, object]] = []
    statuses: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    eligible = 0
    indexed_documents = 0
    by_format = {
        fmt.value: {"source_count": 0, "eligible_count": 0, "indexed_chunks": 0}
        for fmt in DocumentFormat
    }
    for document in documents:
        extraction = extract_file(document.path)
        # Abort corrupted experiment inputs; ordinary parser failures remain isolated below.
        if file_sha256(document.path) != document.sha256:
            raise BaselineError(f"source changed during extraction: {document.document_id}")
        if extraction.source_sha256 not in (None, document.sha256):
            raise BaselineError(f"extraction identity mismatch: {document.document_id}")
        fmt_counts = by_format[document.document_format.value]
        fmt_counts["source_count"] += 1
        statuses[extraction.status.value] += 1
        warning_codes = sorted({warning.code.value for warning in extraction.warnings})
        warnings.update(warning_codes)
        if extraction.status is ExtractionStatus.SUCCESS:
            eligible += 1
            fmt_counts["eligible_count"] += 1
        outcome = chunk_document(
            extraction, document_id=document.document_id, config=FROZEN_CHUNKING
        )
        if outcome.status is ChunkingStatus.CHUNKED:
            chunks.extend(outcome.chunks)
            indexed_documents += 1
            fmt_counts["indexed_chunks"] += len(outcome.chunks)
        else:
            exclusions.append(
                {
                    "document_id": document.document_id,
                    "format": document.document_format.value,
                    "extraction_status": extraction.status.value,
                    "reason": outcome.reason.value if outcome.reason else outcome.status.value,
                    "warning_codes": warning_codes,
                    "error_category": (
                        extraction.error_category.value if extraction.error_category else None
                    ),
                }
            )
    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise BaselineError("duplicate chunk identities")
    metadata: dict[str, object] = {
        "source_count": len(documents),
        "eligible_count": eligible,
        "indexed_document_count": indexed_documents,
        "indexed_chunk_count": len(chunks),
        "by_format": by_format,
        "extraction_status_counts": dict(statuses),
        "warning_document_counts": dict(warnings),
        "exclusion_reason_counts": dict(Counter(str(item["reason"]) for item in exclusions)),
        "exclusions": exclusions,
        "corpus_fingerprint": _fingerprint([item.identity() for item in documents]),
        "chunking_configuration": config_as_dict(FROZEN_CHUNKING),
        "chunk_metadata_fingerprint": _fingerprint(
            [
                {key: value for key, value in asdict(chunk).items() if key != "text"}
                for chunk in chunks
            ]
        ),
    }
    return RetrievalCorpus(tuple(chunks), metadata)


def chunk_evidence(chunk: Chunk) -> tuple[RetrievedAnchor, ...]:
    """Copy normalized source-unit spans, not chunk offsets or Gold-provided spans."""
    anchors = []
    seen: set[str] = set()
    for span in chunk.provenance:
        if not 0 <= span.source_start < span.source_end <= span.source_length:
            raise BaselineError("invalid chunk provenance span")
        anchor = RetrievedAnchor(
            document_sha256=chunk.source_sha256,
            document_format=chunk.document_format,
            locator=EvidenceLocator(**asdict(span.source)),
            source_start=span.source_start,
            source_end=span.source_end,
        )
        key = _json(anchor.to_dict())
        if key not in seen:
            anchors.append(anchor)
            seen.add(key)
    if not anchors:
        raise BaselineError("retrieved chunk lacks provenance")
    return tuple(anchors)


def retrieve_queries(
    index: BM25Index,
    chunks: Mapping[str, Chunk],
    questions: Iterable[tuple[str, str]],
    *,
    dataset_revision: str,
) -> tuple[tuple[QueryResults, ...], tuple[float, ...]]:
    """The ranking boundary accepts IDs/text only, never relevance or split metadata."""
    records = []
    latencies = []
    for question_id, text in sorted(questions):
        start = time.perf_counter()
        hits = index.search(text)
        latencies.append((time.perf_counter() - start) * 1000)
        results = tuple(
            RankedResult(rank, chunk_evidence(chunks[hit.stable_id]), hit.stable_id)
            for rank, hit in enumerate(hits, start=1)
        )
        records.append(QueryResults(GOLD_SCHEMA_VERSION, dataset_revision, question_id, results))
    return tuple(records), tuple(latencies)


def results_jsonl(records: tuple[QueryResults, ...]) -> str:
    return "".join(
        _json(
            {
                "schema_version": record.schema_version,
                "dataset_revision": record.dataset_revision,
                "question_id": record.question_id,
                "results": [
                    {
                        "rank": result.rank,
                        "runtime_chunk_id": result.runtime_chunk_id,
                        "evidence": [anchor.to_dict() for anchor in result.evidence],
                    }
                    for result in record.results
                ],
            }
        )
        + "\n"
        for record in records
    )


def _percentile(samples: tuple[float, ...], fraction: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _checked_output_dir(output_dir: Path) -> Path:
    root = Path.cwd() / "evaluation-output"
    output = output_dir.resolve()
    if root.is_symlink() or not output.is_relative_to(root.resolve()) or output == root.resolve():
        raise BaselineError("output must be a subdirectory of evaluation-output")
    if output.exists():
        raise BaselineError("output directory already exists; preserve the first frozen run")
    return output


def run_baseline(
    *,
    corpus_dir: Path,
    manifest_path: Path,
    gold_path: Path,
    output_dir: Path,
    expected_gold_fingerprint: str = FROZEN_GOLD_FINGERPRINT,
    expected_source_count: int = 90,
) -> dict[str, object]:
    output = _checked_output_dir(output_dir)
    documents = verify_corpus(
        corpus_dir, manifest_path, expected_source_count=expected_source_count
    )
    gold: GoldDataset = load_gold_jsonl(gold_path, corpus_manifest_path=manifest_path)
    if gold.fingerprint != expected_gold_fingerprint:
        raise BaselineError("Gold fingerprint differs from frozen expectation")
    start = time.perf_counter()
    corpus = build_corpus(documents)
    preparation_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    index = BM25Index(BM25Document(chunk.chunk_id, chunk.text) for chunk in corpus.chunks)
    indexing_ms = (time.perf_counter() - start) * 1000
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    records, latencies = retrieve_queries(
        index,
        chunks,
        ((example.question_id, example.question) for example in gold.examples),
        dataset_revision=gold.dataset_revision,
    )
    output.mkdir(parents=True)
    ranked_path = output / "ranked_results.jsonl"
    ranked_path.write_text(results_jsonl(records), encoding="utf-8", newline="\n")
    parsed = load_ranked_results_jsonl(ranked_path)
    report = evaluate_retrieval(gold, parsed).to_dict()
    experiment: dict[str, object] = {
        "baseline_version": "bm25-v1",
        "corpus": corpus.metadata,
        "manifest_sha256": file_sha256(manifest_path),
        "dataset_revision": gold.dataset_revision,
        "gold_fingerprint": gold.fingerprint,
        "bm25_configuration": FROZEN_BM25.to_dict(),
        "index_fingerprint": index.fingerprint,
        "vocabulary_size": len(index.document_frequency),
        "average_chunk_token_count": index.average_length,
        "query_count": len(records),
        "ranked_jsonl_sha256": file_sha256(ranked_path),
        "results_fingerprint": report["results_fingerprint"],
        "report_fingerprint": report["report_fingerprint"],
    }
    timings = {
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "dependencies": {name: version(name) for name in ("pypdf", "python-docx", "openpyxl")},
        },
        "corpus_preparation_ms": preparation_ms,
        "bm25_indexing_ms": indexing_ms,
        "query_latency_scope": "tokenization and BM25 search; excludes evidence serialization",
        "query_sample_count": len(latencies),
        "query_ms": list(latencies),
        "query_p50_ms": _percentile(latencies, 0.5),
        "query_p95_ms": _percentile(latencies, 0.95),
        "percentile_method": "linear interpolation at (n-1)*p",
    }
    for name, payload in (
        ("quality_report.json", report),
        ("experiment.json", experiment),
        ("latency.json", timings),
    ):
        (output / name).write_text(_json(payload) + "\n", encoding="utf-8", newline="\n")
    return experiment
