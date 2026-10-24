"""Incomplete reprocessing never displaces an existing verified ACTIVE revision."""

import asyncio
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import select

from doclens_ai.extraction.reconciliation import reconcile
from doclens_ai.models import CanonicalChunk, ExtractionArtifact, IndexRevision, ProcessingJob
from doclens_ai.services.worker import IngestionWorker
from tests.integration.test_engine_ingestion import prepare_engine_run
from tests.integration.test_engine_search import TwoPageWordsIR, rechunk_run
from tests.integration.test_production_indexing import _claim, _complete, _index, _index_environment
from tests.unit.test_ir_evidence import review

pytestmark = [pytest.mark.integration, pytest.mark.storage]


class PublicationWordsIR(TwoPageWordsIR):
    descriptor = replace(
        TwoPageWordsIR.descriptor,
        name="publication-fixture",
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    failure = None

    def extract(self, source, *, options_json):
        ir = super().extract(source, options_json=options_json)
        if self.failure == "partial":
            return ir.model_copy(update={"state": "partial"})
        first, second = ir.elements
        if self.failure == "rejected":
            second = second.model_copy(update={"state": "failed"})
        elif self.failure == "held":
            second = second.model_copy(update={"text": "x" * 1201})
        return ir.model_copy(update={"elements": (first, second)})


@pytest.mark.parametrize("failure", ["partial", "rejected", "held", "unreviewed"])
def test_failed_extraction_keeps_previous_active_and_no_partial_canonical_chunks(
    migrated_database_url, test_storage_settings, tmp_path, failure
):
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.7\nsynthetic publication fixture\n%%EOF")

    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
            indexer,
            _,
            _,
        ):
            engine = PublicationWordsIR()
            uploaded, ingestion, reviews, expected, _, _ = await prepare_engine_run(
                factory, storage, keys, engine, path
            )
            worker = IngestionWorker(
                indexer.coordinator,
                ingestion,
                settings=indexer.settings,
                worker_id="publication-ingester",
            )
            assert await worker.run_once()
            claim = await _claim(indexer)
            indexed = await _index(indexer, claim)
            assert await _complete(indexer, claim, indexed) == "active"
            async with factory() as session:
                original = {
                    c.id: c.chunk_text for c in await session.scalars(select(CanonicalChunk))
                }
            run_id, job_id, _ = await rechunk_run(factory, uploaded, claim.processing_run_id)
            engine.failure = failure
            ir = reconcile((engine.extract(path, options_json="{}"),), expected=expected)
            reviews["fixture-review-1"] = review(
                ir, exclude=(ir.elements[1].id,) if failure == "unreviewed" else ()
            )
            assert await worker.run_once()
            async with factory() as session:
                job = await session.get(ProcessingJob, job_id)
                assert job.status == "failed" and job.failure_reason == "extraction_needs_review"
                active = tuple(
                    await session.scalars(
                        select(IndexRevision).where(IndexRevision.status == "active")
                    )
                )
                assert len(active) == 1 and active[0].id == indexed.revision_id
                assert {
                    c.id: c.chunk_text for c in await session.scalars(select(CanonicalChunk))
                } == original
                assert not tuple(
                    await session.scalars(
                        select(CanonicalChunk).where(CanonicalChunk.processing_run_id == run_id)
                    )
                )
                artifacts = tuple(
                    await session.scalars(
                        select(ExtractionArtifact).where(
                            ExtractionArtifact.processing_run_id == run_id
                        )
                    )
                )
                assert len(artifacts) == 1  # Retained diagnostic evidence, never published.

    asyncio.run(exercise())
