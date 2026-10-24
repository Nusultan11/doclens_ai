"""Old canonical IR subsets cannot bypass the new ingestion completeness gate."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4, uuid5

import pytest
from sqlalchemy import select

from doclens_ai.extraction.engines import EngineRoute
from doclens_ai.models import (
    CanonicalChunk,
    IndexRevision,
    ProcessingJob,
    ProcessingRun,
)
from doclens_ai.models.index_revision import chunk_set_fingerprint
from doclens_ai.services.indexing import IndexingFailure
from doclens_ai.services.processing import (
    PROCESSING_CONFIGURATION_VERSION,
    InvalidProcessingTransition,
    default_processing_configuration_fingerprint,
)
from doclens_ai.services.worker import IngestionWorker
from tests.integration.test_engine_ingestion import prepare_engine_run
from tests.integration.test_engine_search import TwoPageWordsIR
from tests.integration.test_production_indexing import (
    _claim,
    _complete,
    _index,
    _index_environment,
)

pytestmark = [pytest.mark.integration, pytest.mark.storage]


@pytest.mark.parametrize("boundary", ["prepare", "cutover"])
def test_previously_persisted_ir_subset_cannot_become_active(
    migrated_database_url, test_storage_settings, tmp_path, boundary
):
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.7\nlegacy publication fixture\n%%EOF")

    async def exercise():
        async with _index_environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
            indexer,
            _,
            _,
        ):
            uploaded, ingestion, _, _, _, _ = await prepare_engine_run(
                factory, storage, keys, TwoPageWordsIR(), path
            )
            worker = IngestionWorker(
                indexer.coordinator,
                ingestion,
                settings=indexer.settings,
                worker_id="legacy-ingester",
            )
            assert await worker.run_once()
            first_claim = await _claim(indexer)
            first_index = await _index(indexer, first_claim)
            assert await _complete(indexer, first_claim, first_index) == "active"
            async with factory() as session, session.begin():
                original = await session.get(ProcessingRun, first_claim.processing_run_id)
                old_route = EngineRoute.model_validate(original.extraction_route).model_copy(
                    update={"chunker_version": "2.0", "validator_version": "2.0"}
                )
                run = ProcessingRun(
                    id=uuid4(),
                    operation_id=uuid4(),
                    operation_kind="reprocess",
                    document_version_id=uploaded.document_version_id,
                    configuration_version=PROCESSING_CONFIGURATION_VERSION,
                    configuration_fingerprint=default_processing_configuration_fingerprint(
                        old_route
                    ),
                    extraction_route=old_route.model_dump(mode="json"),
                    stage="embedding",
                    status="queued",
                )
                job = ProcessingJob(
                    id=uuid4(),
                    processing_run_id=run.id,
                    status="queued",
                    attempt_count=0,
                    max_attempts=3,
                )
                source = await session.scalar(
                    select(CanonicalChunk)
                    .where(CanonicalChunk.processing_run_id == original.id)
                    .order_by(CanonicalChunk.ordinal)
                )
                # Faithfully model a previously committed subset, not a DB rewrite.
                values = {
                    c.name: getattr(source, c.name)
                    for c in CanonicalChunk.__table__.columns
                    if c.name not in {"id", "processing_run_id", "created_at"}
                }
                subset = CanonicalChunk(id=uuid4(), processing_run_id=run.id, **values)
                subset.chunker_version = "2.0"
                session.add(run)
                await session.flush()
                session.add_all([job, subset])
                run_id = run.id
            claim = await _claim(indexer)
            assert claim.processing_run_id == run_id
            if boundary == "prepare":
                with pytest.raises(IndexingFailure, match="index_configuration_mismatch"):
                    await _index(indexer, claim)
            else:
                # Represents a candidate verified by an older worker before rollout.
                async with factory() as session, session.begin():
                    old = await session.get(IndexRevision, first_index.revision_id)
                    values = {
                        c.name: getattr(old, c.name)
                        for c in IndexRevision.__table__.columns
                        if c.name
                        not in {
                            "id",
                            "processing_run_id",
                            "lease_token",
                            "status",
                            "created_at",
                            "verified_at",
                            "activated_at",
                            "superseded_at",
                            "expected_point_count",
                            "verified_point_count",
                            "canonical_chunk_set_fingerprint",
                        }
                    }
                    candidate = IndexRevision(
                        id=uuid5(run_id, "index:" + str(claim.lease_token)),
                        processing_run_id=run_id,
                        lease_token=claim.lease_token,
                        status="candidate",
                        expected_point_count=1,
                        verified_point_count=0,
                        canonical_chunk_set_fingerprint=chunk_set_fingerprint((subset,)),
                        verified_at=None,
                        **values,
                    )
                    session.add(candidate)
                    await session.flush()
                    candidate.status = "verified"
                    candidate.verified_point_count = 1
                    candidate.verified_at = datetime.now(UTC)
                    run = await session.get(ProcessingRun, run_id)
                    run.stage = "indexing"
                    candidate_id = candidate.id
                with pytest.raises(
                    InvalidProcessingTransition, match="complete current IR evidence"
                ):
                    await _complete(indexer, claim, SimpleNamespace(revision_id=candidate_id))
            async with factory() as session:
                active = tuple(
                    await session.scalars(
                        select(IndexRevision).where(IndexRevision.status == "active")
                    )
                )
                assert len(active) == 1 and active[0].id == first_index.revision_id
                assert (
                    len(
                        tuple(
                            await session.scalars(
                                select(CanonicalChunk).where(
                                    CanonicalChunk.processing_run_id == run_id
                                )
                            )
                        )
                    )
                    == 1
                )  # Historical data is retained, never silently rewritten/deleted.

    asyncio.run(exercise())
