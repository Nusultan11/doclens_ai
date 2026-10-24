"""Synthetic engines through real RAW storage, PostgreSQL and the ingestion service."""

import asyncio
import io
from dataclasses import replace

import pytest
from sqlalchemy import select

from doclens_ai.extraction.engines import (
    EngineCapability,
    EngineRegistry,
    EngineRoute,
    default_route,
)
from doclens_ai.extraction.ir import SourceIdentity
from doclens_ai.extraction.ir_validation import EvidencePolicy, evidence_policy_fingerprint
from doclens_ai.extraction.reconciliation import reconcile
from doclens_ai.models import CanonicalChunk, Document, DocumentVersion, Workspace
from doclens_ai.services.ingestion import IngestionFailure, IngestionService
from doclens_ai.services.processing import ProcessingCoordinator
from doclens_ai.services.upload import PDF_CONTENT_TYPE, UploadService
from tests.integration.test_worker import _environment
from tests.unit.test_extraction_engines import FakeRegionsIR, FakeWordsIR, pin
from tests.unit.test_ir_evidence import review

pytestmark = [pytest.mark.integration, pytest.mark.storage]


async def prepare_engine_run(factory, storage, keys, engine, path, *, route_overrides=None):
    policy = EvidencePolicy(
        allow_verified_pdf=True,
        trusted_reviewers=frozenset({("fixture-reviewer", "r1")}),
        allowed_engines=frozenset(
            {
                (
                    engine.descriptor.name,
                    engine.descriptor.revision,
                    engine.descriptor.implementation_sha256,
                )
            }
        ),
    )
    route = EngineRoute(
        engines=(pin(engine),),
        mode="verified_ir",
        chunker_version="2.0",
        runtime_manifest_json=default_route().runtime_manifest_json,
        policy_sha256=evidence_policy_fingerprint(policy),
        review_id="fixture-review-1",
    )
    if route_overrides:
        route = route.model_copy(update=route_overrides)
    async with factory() as session, session.begin():
        doc = Document(workspace=Workspace(name="Synthetic engine fixture"))
        session.add(doc)
        await session.flush()
        document_id, workspace_id = doc.id, doc.workspace_id
    uploaded = await UploadService(
        factory, storage, max_upload_size_bytes=1024 * 1024, extraction_route=route
    ).upload_and_confirm(
        workspace_id=workspace_id,
        document_id=document_id,
        idempotency_key="fake-engine-upload",
        original_filename="fixture.pdf",
        content_type=PDF_CONTENT_TYPE,
        stream=io.BytesIO(path.read_bytes()),
    )
    async with factory() as session:
        version = await session.get(DocumentVersion, uploaded.document_version_id)
        keys.append(version.object_storage_key)
    expected = SourceIdentity(
        sha256=version.sha256_checksum,
        size_bytes=version.file_size,
        document_format="pdf",
        workspace_id=str(workspace_id),
        document_version_id=str(version.id),
    )
    ir = reconcile((engine.extract(path, options_json="{}"),), expected=expected)
    reviews = {route.review_id: review(ir)}  # Explicit synthetic review, not real adjudication.
    service = IngestionService(
        factory,
        storage,
        registry=EngineRegistry((engine,)),
        evidence_policy=policy,
        review_loader=reviews.get,
    )
    return uploaded, service, reviews, expected, document_id, workspace_id


@pytest.mark.parametrize("engine_class", [FakeWordsIR, FakeRegionsIR])
@pytest.mark.parametrize("require_ocr", [False, True])
def test_fake_engine_routes_raw_pdf_to_canonical_chunks(
    migrated_database_url, test_storage_settings, tmp_path, engine_class, require_ocr
):
    path = tmp_path / "fixture.pdf"
    path.write_bytes(b"%PDF-1.7\nsynthetic engine source\n%%EOF")

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            engine = engine_class()
            engine.descriptor = replace(
                engine.descriptor, capabilities=frozenset({EngineCapability.OCR})
            )
            uploaded, service, _, expected, _, _ = await prepare_engine_run(
                factory,
                storage,
                keys,
                engine,
                path,
                route_overrides={
                    "required_capabilities": (EngineCapability.OCR,) if require_ocr else ()
                },
            )
            claim = await ProcessingCoordinator(factory).claim_next(worker_id="fake-worker")
            first = await service.ingest(
                claim.processing_run_id, worker_id="fake-worker", lease_token=claim.lease_token
            )
            second = await service.ingest(
                claim.processing_run_id, worker_id="fake-worker", lease_token=claim.lease_token
            )
            assert first.status == "persisted" and second.status == "already_persisted"
            async with factory() as session:
                chunks = tuple(await session.scalars(select(CanonicalChunk)))
                assert len(chunks) == 1
                assert chunks[0].chunk_text == "-10 kg"
                assert chunks[0].source_provenance[0]["source"]["page_number"] == 1
                assert str(uploaded.document_version_id) == expected.document_version_id

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "failure", ["missing_review", "wrong_tenant", "missing_engine", "missing_capability"]
)
def test_fake_engine_failures_never_publish_chunks(
    migrated_database_url, test_storage_settings, tmp_path, failure
):
    path = tmp_path / "fixture.pdf"
    path.write_bytes(b"%PDF-1.7\nsynthetic fixture\n%%EOF")

    async def exercise():
        async with _environment(migrated_database_url, test_storage_settings) as (
            factory,
            storage,
            keys,
        ):
            _, service, reviews, _, _, _ = await prepare_engine_run(
                factory,
                storage,
                keys,
                FakeWordsIR(),
                path,
                route_overrides={"required_capabilities": (EngineCapability.OCR,)}
                if failure == "missing_capability"
                else None,
            )
            if failure == "missing_review":
                reviews.clear()
            elif failure == "wrong_tenant":
                r = reviews["fixture-review-1"]
                reviews["fixture-review-1"] = replace(
                    r, source=r.source.model_copy(update={"workspace_id": "other-tenant"})
                )
            elif failure == "missing_engine":
                service._registry = EngineRegistry()
            claim = await ProcessingCoordinator(factory).claim_next(worker_id="fake-worker")
            with pytest.raises(IngestionFailure):
                await service.ingest(
                    claim.processing_run_id, worker_id="fake-worker", lease_token=claim.lease_token
                )
            if failure == "missing_capability":
                assert service.executor.last_pid is None
            async with factory() as session:
                assert not tuple(await session.scalars(select(CanonicalChunk)))

    asyncio.run(exercise())
