"""Private, reproducible production retrieval evaluation; no labels enter search filters."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from collections import Counter
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.engine import make_url

from doclens_ai.chunking.core import chunk_document
from doclens_ai.core.config import Settings
from doclens_ai.core.search_config import SearchSettings
from doclens_ai.db.session import Database
from doclens_ai.dense_baseline.embeddings import E5Embedder, EmbeddingConfig
from doclens_ai.evaluation.gold import EvidenceLocator, load_gold_jsonl
from doclens_ai.evaluation.metrics import (
    EvaluationConfig,
    EvaluationError,
    QueryResults,
    RankedResult,
    RetrievedAnchor,
    _anchor_matches,
    evaluate_retrieval,
)
from doclens_ai.extraction.models import DocumentFormat
from doclens_ai.extraction.parsers import extract_file
from doclens_ai.models import (
    CanonicalChunk,
    Document,
    DocumentVersion,
    IndexRevision,
    ProcessingJob,
    ProcessingRun,
    User,
    Workspace,
    WorkspaceMembership,
)
from doclens_ai.retrieval_baseline.runner import (
    FROZEN_CHUNKING,
    FROZEN_GOLD_FINGERPRINT,
    file_sha256,
    verify_corpus,
)
from doclens_ai.services.index_worker import IndexWorker
from doclens_ai.services.indexing import IndexingService, collection_name
from doclens_ai.services.ingestion import IngestionService, canonicalize_chunk
from doclens_ai.services.processing import ProcessingCoordinator, ProcessingPolicy
from doclens_ai.services.retrieval import QueryEncoder, RetrievalService, SearchInput
from doclens_ai.services.upload import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    XLSX_CONTENT_TYPE,
    UploadService,
)
from doclens_ai.services.worker import IngestionWorker, WorkerSettings
from doclens_ai.storage.config import StorageSettings
from doclens_ai.storage.s3 import S3ObjectStorage
from doclens_ai.vector.qdrant import ProductionQdrant


def percentiles(values):
    ordered = sorted(values)
    if not ordered:
        return {"sample_count": 0, "p50_ms": None, "p95_ms": None}

    def percentile(p):
        position = (len(ordered) - 1) * p
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        return ordered[low] + (ordered[high] - ordered[low]) * (position - low)

    return {"sample_count": len(ordered), "p50_ms": percentile(0.5), "p95_ms": percentile(0.95)}


async def prepare_corpus(database, provider, vector, documents):
    # Explicit opt-in only, on an empty disposable database; never seed a production workspace.
    name = make_url(Settings().database_url).database or ""
    if not re.fullmatch(r"doclens_eval_[0-9a-f]{32}", name):
        raise EvaluationError("preparation requires an explicitly disposable evaluation database")
    factory = database.session_factory
    async with factory() as session, session.begin():
        if await session.scalar(select(func.count()).select_from(Document)):
            raise EvaluationError("preparation requires an empty document domain")
        workspace = Workspace(name="Private production retrieval evaluation")
        user = User(issuer="https://evaluation.invalid/", subject=uuid4().hex)
        session.add_all([workspace, user])
        await session.flush()
        session.add(WorkspaceMembership(user_id=user.id, workspace_id=workspace.id, role="owner"))
    storage = S3ObjectStorage(StorageSettings())
    await storage.probe()
    settings = WorkerSettings(_env_file=None)
    policy = ProcessingPolicy(lease_duration=timedelta(seconds=settings.lease_seconds))
    extraction = IngestionWorker(
        ProcessingCoordinator(factory, policy=policy),
        IngestionService(factory, storage),
        settings=settings,
        worker_id="eval-extraction",
    )
    indexing = IndexWorker(
        ProcessingCoordinator(factory, policy=policy),
        IndexingService(factory, provider, vector),
        settings=settings,
        worker_id="eval-index",
    )
    types = {"pdf": PDF_CONTENT_TYPE, "docx": DOCX_CONTENT_TYPE, "xlsx": XLSX_CONTENT_TYPE}
    try:
        for document in documents:
            async with factory() as session, session.begin():
                record = Document(workspace_id=workspace.id)
                session.add(record)
                await session.flush()
            with document.path.open("rb") as stream:
                await UploadService(
                    factory, storage, max_upload_size_bytes=50 * 1024 * 1024
                ).upload_and_confirm(
                    workspace_id=workspace.id,
                    document_id=record.id,
                    idempotency_key=document.sha256,
                    original_filename=document.path.name,
                    content_type=types[document.document_format.value],
                    stream=stream,
                )
            if file_sha256(document.path) != document.sha256:
                raise EvaluationError("approved source changed during preparation")
            if not await extraction.run_once():
                raise EvaluationError("extraction claim failed during preparation")
            await indexing.run_once()
        return user.id, workspace.id
    finally:
        await asyncio.to_thread(storage._client.close)


def result_anchors(hit):
    return tuple(
        RetrievedAnchor(
            hit.source_sha256,
            DocumentFormat(hit.locator.document_format),
            EvidenceLocator(**span.source.model_dump(exclude_none=True)),
            span.source_start,
            span.source_end,
        )
        for span in hit.locator.spans
    )


async def verify_alignment(factory, workspace_id, documents):
    """Reproduce source spans using actual version UUIDs; never derive mapping from labels."""
    async with factory() as session:
        versions = list(
            await session.scalars(
                select(DocumentVersion).join(Document).where(Document.workspace_id == workspace_id)
            )
        )
        runs = list(
            await session.scalars(
                select(ProcessingRun)
                .join(DocumentVersion)
                .join(Document)
                .where(Document.workspace_id == workspace_id)
            )
        )
        revisions = list(
            await session.scalars(
                select(IndexRevision).where(
                    IndexRevision.workspace_id == workspace_id, IndexRevision.status == "active"
                )
            )
        )
        chunks = list(
            await session.scalars(
                select(CanonicalChunk)
                .join(ProcessingRun)
                .join(DocumentVersion)
                .join(Document)
                .where(Document.workspace_id == workspace_id)
            )
        )
    by_sha = {v.sha256_checksum: v for v in versions}
    by_version = {r.document_version_id: r for r in runs}
    if (
        len(by_sha) != len(versions)
        or set(by_sha) != {d.sha256 for d in documents}
        or len(by_version) != len(runs)
        or len(runs) != len(documents)
    ):
        raise EvaluationError("approved source/version/run coverage is not one-to-one")
    active_runs = {r.processing_run_id for r in revisions}
    by_run = {run.id: [] for run in runs}
    for chunk in chunks:
        by_run[chunk.processing_run_id].append(chunk)
    anchors = []
    eligible = 0
    for document in documents:
        version = by_sha[document.sha256]
        run = by_version[version.id]
        if version.file_size != document.size_bytes:
            raise EvaluationError("source metadata differs from approved manifest")
        extraction = await asyncio.to_thread(extract_file, document.path)
        expected = chunk_document(extraction, document_id=str(version.id), config=FROZEN_CHUNKING)
        actual = sorted(by_run[run.id], key=lambda c: c.ordinal)
        if len(expected.chunks) != len(actual):
            raise EvaluationError("canonical chunk coverage differs from frozen extraction")
        if actual:
            eligible += 1
            if run.id not in active_runs or run.status != "completed":
                raise EvaluationError("eligible source lacks a completed active index")
        elif run.id in active_runs:
            raise EvaluationError("excluded source has an unexpected active index")
        for chunk, reference in zip(actual, expected.chunks, strict=True):
            canonical = canonicalize_chunk(run.id, reference)
            if (
                chunk.id != canonical.id
                or chunk.chunk_identity != canonical.chunk_identity
                or chunk.ordinal != canonical.ordinal
                or chunk.content_sha256 != canonical.content_sha256
                or chunk.source_provenance != canonical.source_provenance
                or chunk.chunker_configuration_fingerprint
                != canonical.chunker_configuration_fingerprint
                or hashlib.sha256(chunk.chunk_text.encode()).hexdigest() != canonical.content_sha256
            ):
                raise EvaluationError("source-anchor/content alignment could not be verified")
            for span in reference.provenance:
                from dataclasses import asdict

                anchors.append(
                    RetrievedAnchor(
                        document.sha256,
                        document.document_format,
                        EvidenceLocator(**asdict(span.source)),
                        span.source_start,
                        span.source_end,
                    )
                )
        if file_sha256(document.path) != document.sha256:
            raise EvaluationError("source changed during alignment verification")
    return tuple(anchors), {
        "verified_source_count": len(documents),
        "active_document_count": eligible,
        "canonical_chunk_count": len(chunks),
        "source_anchor_alignment": "verified",
        "excluded_source_count": len(documents) - eligible,
    }


async def run(arguments):
    documents = verify_corpus(arguments.corpus_dir, arguments.corpus_manifest)
    gold = load_gold_jsonl(arguments.gold, corpus_manifest_path=arguments.corpus_manifest)
    if gold.fingerprint != FROZEN_GOLD_FINGERPRINT:
        raise EvaluationError("reviewed Gold differs from the frozen snapshot")
    if arguments.output_dir.exists():
        raise EvaluationError("output directory must be new and private")
    settings = SearchSettings(model_dir=arguments.model_dir)
    if settings.model_dir is None:
        raise EvaluationError("local pinned model artifacts are required")
    provider = await asyncio.to_thread(
        E5Embedder,
        settings.model_dir,
        config=EmbeddingConfig(batch_size=settings.batch_size, cpu_threads=settings.cpu_threads),
    )
    encoder = QueryEncoder(
        provider,
        concurrency=settings.inference_concurrency,
        queue_timeout_seconds=settings.queue_timeout_seconds,
    )
    vector = ProductionQdrant(
        settings.qdrant_url,
        collection_name(encoder.fingerprint, settings.collection_prefix),
        timeout_seconds=settings.qdrant_timeout_seconds,
        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
    )
    database = Database(Settings().database_url)
    service = RetrievalService(
        database.session_factory,
        encoder,
        vector,
        max_active_revisions=settings.max_active_revisions,
        db_timeout_seconds=settings.db_timeout_seconds,
    )
    try:
        if arguments.prepare_corpus:
            user_id, workspace_id = await prepare_corpus(database, provider, vector, documents)
        else:
            user_id, workspace_id = arguments.user_id, arguments.workspace_id
            if user_id is None or workspace_id is None:
                raise EvaluationError("trusted evaluation identity/workspace are required")
        anchors, composition = await verify_alignment(
            database.session_factory, workspace_id, documents
        )
        if any(
            not any(_anchor_matches(evidence, anchor) for anchor in anchors)
            for example in gold.examples
            for evidence in example.evidence
        ):
            raise EvaluationError("reviewed evidence cannot be aligned to canonical source spans")
        # Only query IDs/text reach retrieval; no answer labels, source-document filters or splits.
        outcomes = []
        for question_id, query in sorted((e.question_id, e.question) for e in gold.examples):
            outcome = await service.search(
                user_id=user_id,
                request=SearchInput(workspace_id=workspace_id, query=query, top_k=20, limit=20),
            )
            outcomes.append((question_id, outcome))
        records = tuple(
            QueryResults(
                "1.0",
                gold.dataset_revision,
                question_id,
                tuple(
                    RankedResult(
                        rank, result_anchors(hit), str(hit.chunk_id), str(hit.workspace_id)
                    )
                    for rank, hit in enumerate(outcome.results, start=1)
                ),
                str(workspace_id),
            )
            for question_id, outcome in outcomes
        )
        report = evaluate_retrieval(
            gold, records, config=EvaluationConfig(require_workspace_scope=True)
        ).to_dict()
        unauthorized = sum(
            hit.workspace_id != workspace_id for _, outcome in outcomes for hit in outcome.results
        )
        if unauthorized or report["security"]["violation_count"]:
            raise EvaluationError("hard security gate failed")
        async with database.session_factory() as session:
            revisions = list(
                await session.scalars(
                    select(IndexRevision).where(IndexRevision.workspace_id == workspace_id)
                )
            )
            reasons = list(
                await session.scalars(
                    select(ProcessingJob.failure_reason)
                    .join(ProcessingRun)
                    .join(DocumentVersion)
                    .join(Document)
                    .where(Document.workspace_id == workspace_id)
                )
            )
        # Only sanitized metrics are persisted; never queries, hits, paths, worksheet names or text.
        payload = {
            "evaluation": report,
            "corpus": composition,
            "embedding_configuration": encoder.configuration,
            "embedding_fingerprint": encoder.fingerprint,
            "candidate_limit": 20,
            "result_limit": 20,
            "unauthorized_result_count": unauthorized,
            "verified_returned_result_count": sum(len(o.results) for _, o in outcomes),
            "latency_percentile_method": "linear interpolation (n-1)*p, includes queue wait",
            "latency": {
                "query_embedding": percentiles([o.embedding_ms for _, o in outcomes]),
                "qdrant": percentiles([o.qdrant_ms for _, o in outcomes]),
                "end_to_end": percentiles([o.end_to_end_ms for _, o in outcomes]),
            },
            "preparation": {
                "failure_reason_counts": dict(Counter(r for r in reasons if r)),
                "incomplete_candidate_count": sum(r.status == "candidate" for r in revisions),
            },
        }
        arguments.output_dir.mkdir(parents=True)
        (arguments.output_dir / "metrics.json").write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "evaluation": "passed",
                    "queries": len(records),
                    "corpus": composition,
                    "overall": report["overall"],
                    "unauthorized_result_count": unauthorized,
                    "latency": payload["latency"],
                }
            )
        )
    finally:
        await service.aclose()
        await database.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Private real-corpus production dense retrieval evaluation"
    )
    parser.add_argument("--corpus-dir", type=Path, default=Path("local-corpus"))
    parser.add_argument(
        "--corpus-manifest", type=Path, default=Path("docs/eda/corpus_v1_manifest.csv")
    )
    parser.add_argument(
        "--gold", type=Path, default=Path("local-evaluation/retrieval_gold_v1.jsonl")
    )
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--workspace-id", type=UUID)
    parser.add_argument("--user-id", type=UUID)
    parser.add_argument("--prepare-corpus", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except Exception:
        print("production_retrieval_evaluation_failed")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
