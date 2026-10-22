"""Real PG/S3 artifact faults; synthetic evidence, not model fidelity acceptance."""

import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from doclens_ai.extraction.engines import EngineRegistry, EngineRoute
from doclens_ai.extraction.ir import Issue, TextElement
from doclens_ai.extraction.models import SourceLocation
from doclens_ai.models import CanonicalChunk, ExtractionArtifact, ProcessingJob, ProcessingRun
from doclens_ai.services.extraction_artifacts import ArtifactError
from doclens_ai.services.ingestion import IngestionFailure
from doclens_ai.services.processing import (
    PROCESSING_CONFIGURATION_VERSION,
    ProcessingCoordinator,
    default_processing_configuration_fingerprint,
)
from doclens_ai.storage.s3 import ObjectStorageError
from tests.integration.test_engine_ingestion import prepare_engine_run
from tests.integration.test_worker import _environment
from tests.unit.test_extraction_engines import FakeWordsIR

pytestmark = [pytest.mark.integration, pytest.mark.storage]


def fixture_path(tmp_path):
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.7\nartifact fixture\n%%EOF")
    return path


class PartialFakeIR(FakeWordsIR):
    descriptor = replace(
        FakeWordsIR.descriptor,
        name="fake-partial",
        implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )

    def extract(self, source, *, options_json):
        ir = super().extract(source, options_json=options_json)
        failed = TextElement(
            id="failed-page",
            text="",
            state="failed",
            reason="page extraction failed",
            source=SourceLocation(page_number=2),
            provenance=ir.elements[0].provenance,
        )
        return ir.model_copy(
            update={
                "state": "partial",
                "elements": (*ir.elements, failed),
                "issues": (
                    Issue(
                        code="page_failed",
                        state="failed",
                        source=failed.source,
                        element_id=failed.id,
                        reason="fixture failure",
                    ),
                ),
            }
        )


def test_partial_page_failure_is_saved_but_only_independently_allowed_page_is_chunked(
    migrated_database_url, test_storage_settings, tmp_path
):
    path = fixture_path(tmp_path)

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            _, service, _, expected, _, _ = await prepare_engine_run(
                factory, storage, keys, PartialFakeIR(), path
            )
            claim = await ProcessingCoordinator(factory).claim_next(worker_id="partial-worker")
            await service.ingest(
                claim.processing_run_id, worker_id="partial-worker", lease_token=claim.lease_token
            )
            async with factory() as session:
                artifact = await session.scalar(select(ExtractionArtifact))
                assert artifact.source_state == "partial"
                chunks = tuple(await session.scalars(select(CanonicalChunk)))
                assert [chunk.chunk_text for chunk in chunks] == ["-10 kg"]
                assert chunks[0].source_provenance[0]["source"]["page_number"] == 1
            _, snapshot = await service.artifacts.load(artifact.id, expected=expected)
            assert snapshot.observations[0].elements[1].state == "failed"
            assert snapshot.observations[0].issues[0].source.page_number == 2

    asyncio.run(exercise())


async def expire(factory, job_id):
    async with factory() as session, session.begin():
        await session.execute(
            text(
                "UPDATE processing_jobs SET lease_expires_at = "
                "clock_timestamp() - INTERVAL '1 second' WHERE id = :id"
            ),
            {"id": job_id},
        )


def test_available_artifact_is_immutable_scoped_and_retry_does_not_extract(
    migrated_database_url, test_storage_settings, tmp_path, monkeypatch
):
    path = fixture_path(tmp_path)

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            _, service, _, expected, _, _ = await prepare_engine_run(
                factory, storage, keys, FakeWordsIR(), path
            )
            claim = await ProcessingCoordinator(factory).claim_next(worker_id="artifact-worker")
            await service.ingest(
                claim.processing_run_id, worker_id="artifact-worker", lease_token=claim.lease_token
            )
            async with factory() as session:
                record = await session.scalar(select(ExtractionArtifact))
                assert record.state == "available"
                identity, key, checksum = record.id, record.object_storage_key, record.checksum

            def forbidden(*args, **kwargs):
                raise AssertionError("extraction must not run on snapshot replay")

            monkeypatch.setattr(service._registry, "extract", forbidden)
            second = await service.ingest(
                claim.processing_run_id, worker_id="artifact-worker", lease_token=claim.lease_token
            )
            assert second.status == "already_persisted"
            await storage.put_immutable(key, b"corrupt replacement", sha256_checksum="f" * 64)
            _, snapshot = await service.artifacts.load(identity, expected=expected)
            assert snapshot.observations[0].elements[0].text == "-10 kg"
            assert await storage.sha256(key) == checksum
            with pytest.raises(ArtifactError, match="scope"):
                await service.artifacts.load(
                    identity, expected=expected.model_copy(update={"workspace_id": str(uuid4())})
                )
            for statement in (
                "UPDATE extraction_artifacts SET checksum = :v WHERE id = :id",
                "DELETE FROM extraction_artifacts WHERE id = :id",
            ):
                with pytest.raises(IntegrityError):
                    async with factory() as session, session.begin():
                        await session.execute(text(statement), {"id": identity, "v": "e" * 64})
            assert await service.artifacts.cleanup_failed() == 0

    asyncio.run(exercise())


@pytest.mark.parametrize("fault", ["crash_before_publish", "stale_after_put"])
def test_staged_artifact_recovers_under_new_lease_without_reextracting(
    migrated_database_url, test_storage_settings, tmp_path, monkeypatch, fault
):
    path = fixture_path(tmp_path)

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            _, service, _, _, _, _ = await prepare_engine_run(
                factory, storage, keys, FakeWordsIR(), path
            )
            coordinator = ProcessingCoordinator(factory)
            claim = await coordinator.claim_next(worker_id="artifact-a")
            original_publish = service.artifacts._publish
            original_put = storage.put_immutable

            async def crash(*args, **kwargs):
                raise OSError("injected crash")

            async def stale_put(*args, **kwargs):
                await original_put(*args, **kwargs)
                await expire(factory, claim.job_id)

            if fault == "crash_before_publish":
                monkeypatch.setattr(service.artifacts, "_publish", crash)
            else:
                monkeypatch.setattr(storage, "put_immutable", stale_put)
            with pytest.raises(IngestionFailure):
                await service.ingest(
                    claim.processing_run_id, worker_id="artifact-a", lease_token=claim.lease_token
                )
            async with factory() as session:
                assert (await session.scalar(select(ExtractionArtifact))).state == "staging"
                assert not tuple(await session.scalars(select(CanonicalChunk)))
            monkeypatch.setattr(service.artifacts, "_publish", original_publish)
            monkeypatch.setattr(storage, "put_immutable", original_put)

            def forbidden(*args, **kwargs):
                raise AssertionError("saved observation must be recovered")

            monkeypatch.setattr(service._registry, "extract", forbidden)
            await expire(factory, claim.job_id)
            recovered = await coordinator.claim_next(worker_id="artifact-b")
            with pytest.raises(IngestionFailure):
                await service.ingest(
                    claim.processing_run_id, worker_id="artifact-a", lease_token=claim.lease_token
                )
            await service.ingest(
                recovered.processing_run_id,
                worker_id="artifact-b",
                lease_token=recovered.lease_token,
            )
            async with factory() as session:
                record = await session.scalar(select(ExtractionArtifact))
                assert record.state == "available" and record.lease_token == recovered.lease_token
                assert len(tuple(await session.scalars(select(CanonicalChunk)))) == 1

    asyncio.run(exercise())


def test_corrupted_artifact_is_not_replaced_or_reused(
    migrated_database_url, test_storage_settings, tmp_path
):
    path = fixture_path(tmp_path)

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            _, service, _, expected, _, _ = await prepare_engine_run(
                factory, storage, keys, FakeWordsIR(), path
            )
            claim = await ProcessingCoordinator(factory).claim_next(worker_id="artifact-a")
            await service.ingest(
                claim.processing_run_id, worker_id="artifact-a", lease_token=claim.lease_token
            )
            async with factory() as session:
                record = await session.scalar(select(ExtractionArtifact))
            await asyncio.to_thread(
                storage._client.put_object,
                Bucket=storage.settings.bucket_name,
                Key=record.object_storage_key,
                Body=b"corrupt",
            )
            with pytest.raises(ArtifactError, match="checksum"):
                await service.artifacts.load(record.id, expected=expected)
            with pytest.raises(IngestionFailure):
                await service.ingest(
                    claim.processing_run_id, worker_id="artifact-a", lease_token=claim.lease_token
                )

    asyncio.run(exercise())


def test_failed_staging_cleanup_preserves_raw_and_is_retryable(
    migrated_database_url, test_storage_settings, tmp_path, monkeypatch
):
    path = fixture_path(tmp_path)

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            _, service, _, _, _, _ = await prepare_engine_run(
                factory, storage, keys, FakeWordsIR(), path
            )
            coordinator = ProcessingCoordinator(factory)
            claim = await coordinator.claim_next(worker_id="artifact-a")

            async def crash(*args, **kwargs):
                raise OSError("injected crash")

            monkeypatch.setattr(service.artifacts, "_publish", crash)
            with pytest.raises(IngestionFailure):
                await service.ingest(
                    claim.processing_run_id, worker_id="artifact-a", lease_token=claim.lease_token
                )
            assert await service.artifacts.cleanup_failed() == 0
            await coordinator.fail_attempt(
                job_id=claim.job_id,
                worker_id="artifact-a",
                lease_token=claim.lease_token,
                failure_reason="fixture_failed",
                retryable=False,
            )
            assert await service.artifacts.cleanup_failed() == 1
            assert await service.artifacts.cleanup_failed() == 1
            async with factory() as session:
                record = await session.scalar(select(ExtractionArtifact))
                assert record.state == "discarded"
            with pytest.raises(ObjectStorageError):
                await storage.inspect(record.object_storage_key)
            assert (await storage.inspect(keys[0])).size > 0

    asyncio.run(exercise())


def test_rechunk_existing_artifact_with_new_pinned_budget_and_no_engine(
    migrated_database_url, test_storage_settings, tmp_path
):
    path = fixture_path(tmp_path)

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            uploaded, service, _, _, _, _ = await prepare_engine_run(
                factory, storage, keys, FakeWordsIR(), path
            )
            coordinator = ProcessingCoordinator(factory)
            first = await coordinator.claim_next(worker_id="artifact-a")
            await service.ingest(
                first.processing_run_id, worker_id="artifact-a", lease_token=first.lease_token
            )
            async with factory() as session, session.begin():
                record = await session.scalar(select(ExtractionArtifact))
                original = await session.get(ProcessingRun, first.processing_run_id)
                route = EngineRoute.model_validate(original.extraction_route).model_copy(
                    update={
                        "ir_chunk_options_json": json.dumps(
                            {
                                "max_characters": 900,
                                "max_chunks": 100000,
                                "max_source_characters": 5000000,
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                    }
                )
                run = ProcessingRun(
                    id=uuid4(),
                    operation_id=uuid4(),
                    operation_kind="reprocess",
                    document_version_id=uploaded.document_version_id,
                    extraction_route=route.model_dump(mode="json"),
                    configuration_version=PROCESSING_CONFIGURATION_VERSION,
                    configuration_fingerprint=default_processing_configuration_fingerprint(route),
                    stage="extraction",
                    status="queued",
                )
                session.add(run)
                session.add(
                    ProcessingJob(
                        id=uuid4(),
                        processing_run_id=run.id,
                        status="queued",
                        attempt_count=0,
                        max_attempts=3,
                    )
                )
            service._registry = EngineRegistry()
            claim = await coordinator.claim_next(worker_id="rechunk-worker")
            await service.ingest_from_artifact(
                claim.processing_run_id,
                record.id,
                worker_id="rechunk-worker",
                lease_token=claim.lease_token,
            )
            async with factory() as session:
                chunks = tuple(await session.scalars(select(CanonicalChunk)))
                assert len(chunks) == 2 and chunks[0].chunk_identity != chunks[1].chunk_identity
                assert {chunk.chunk_text for chunk in chunks} == {"-10 kg"}
                assert {
                    span["extraction_artifact_id"] for c in chunks for span in c.source_provenance
                } == {str(record.id)}

    asyncio.run(exercise())


def test_artifact_schema_upgrade_check_downgrade(disposable_database_url, alembic_runner):
    for _ in range(2):
        alembic_runner(disposable_database_url, "upgrade", "head")
        alembic_runner(disposable_database_url, "check")
        alembic_runner(disposable_database_url, "downgrade", "0008_extraction_route")
