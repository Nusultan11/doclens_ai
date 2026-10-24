"""Completeness at the ingestion boundary, independent of factual quality gates."""

import asyncio
import json
from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from doclens_ai.chunking.ir import IR_CHUNKER_VERSION, chunk_verified_ir
from doclens_ai.extraction.engines import EngineRoute, default_route
from doclens_ai.extraction.ir import DocumentIR
from doclens_ai.extraction.ir_validation import evidence_policy_fingerprint
from doclens_ai.extraction.models import SourceLocation
from doclens_ai.extraction.reconciliation import reconcile
from doclens_ai.services.ingestion import (
    IngestionFailure,
    IngestionService,
    _SourceIdentity,
)
from doclens_ai.services.processing import (
    PROCESSING_CONFIGURATION_VERSION,
    default_processing_configuration_fingerprint,
)
from doclens_ai.services.upload import PDF_CONTENT_TYPE
from tests.unit.test_ir_evidence import document, policy, review


def scoped_document():
    ir = document()
    return ir.model_copy(
        update={
            "source": ir.source.model_copy(
                update={"workspace_id": str(uuid4()), "document_version_id": str(uuid4())}
            )
        }
    )


def boundary(ir, **options):
    route = EngineRoute(
        engines=default_route().engines,
        runtime_manifest_json=default_route().runtime_manifest_json,
        mode="verified_ir",
        chunker_version=IR_CHUNKER_VERSION,
        review_id="fixture-review-1",
    )
    if options:
        limits = json.loads(route.ir_chunk_options_json) | options
        route = route.model_copy(
            update={
                "ir_chunk_options_json": json.dumps(limits, sort_keys=True, separators=(",", ":"))
            }
        )
    source = _SourceIdentity(
        processing_run_id=uuid4(),
        processing_job_id=uuid4(),
        document_version_id=UUID(ir.source.document_version_id),
        configuration_version="fixture",
        configuration_fingerprint="f" * 64,
        object_storage_key="fixture-only",
        content_type=PDF_CONTENT_TYPE,
        file_size=ir.source.size_bytes,
        sha256_checksum=ir.source.sha256,
        workspace_id=UUID(ir.source.workspace_id),
        extraction_route=route.model_dump(mode="json"),
    )
    return source


@pytest.mark.parametrize("state", ["complete", "partial", "failed", "unsupported", "unresolved"])
def test_reconcile_never_upgrades_an_incomplete_observation_without_issues(state):
    ir = document().model_copy(update={"state": state})
    restored = DocumentIR.model_validate_json(ir.model_dump_json())
    assert reconcile((restored,), expected=ir.source).state == state


@pytest.mark.parametrize("failure", ["partial", "rejected", "held", "unreviewed"])
def test_remaining_safe_chunks_cannot_publish_an_incomplete_document(failure):
    ir = scoped_document()
    first = ir.elements[0]
    second = first.model_copy(
        update={"id": "second", "source": SourceLocation(page_number=2), "text": "second"}
    )
    if failure == "rejected":
        second = second.model_copy(update={"state": "failed"})
    elif failure == "held":
        second = second.model_copy(update={"text": "x" * 1201})
    ir = ir.model_copy(
        update={
            "elements": (first, second),
            "state": "partial" if failure == "partial" else "complete",
        }
    )
    rev = review(ir, exclude=("second",) if failure == "unreviewed" else ())
    evidence_policy = policy(ir, allow_verified_pdf=True)
    result = chunk_verified_ir(ir, expected=ir.source, review=rev, policy=evidence_policy)
    assert result.chunks  # Diagnostic evidence still exists, but is not a complete document.
    service = IngestionService(
        object(), object(), evidence_policy=evidence_policy, review_loader=lambda _: rev
    )
    with pytest.raises(IngestionFailure, match="extraction_needs_review"):
        asyncio.run(service._chunk_ir(boundary(ir), ir))
    assert result.status == "partial_review_required"


def test_complete_and_blocked_outcomes_are_explicit():
    ir = scoped_document()
    evidence_policy = policy(ir, allow_verified_pdf=True)
    rev = review(ir)
    result = chunk_verified_ir(ir, expected=ir.source, review=rev, policy=evidence_policy)
    assert result.status == "complete"
    service = IngestionService(
        object(), object(), evidence_policy=evidence_policy, review_loader=lambda _: rev
    )
    assert asyncio.run(service._chunk_ir(boundary(ir), ir)) == result.chunks
    blocked = chunk_verified_ir(ir, expected=ir.source, review=None, policy=evidence_policy)
    assert blocked.status == "blocked" and blocked.chunks == ()


@pytest.mark.parametrize(
    "change", [{"validator_version": "2.0"}, {"chunker_version": "2.0"}, {"chunker_version": "2.1"}]
)
def test_artifact_reprocessing_cannot_silently_use_an_obsolete_validator_or_chunker(change):
    ir = scoped_document()
    evidence_policy = policy(ir, allow_verified_pdf=True)
    service = IngestionService(
        object(), object(), evidence_policy=evidence_policy, review_loader=lambda _: review(ir)
    )
    original = boundary(ir)
    route = EngineRoute.model_validate(original.extraction_route).model_copy(
        update={
            "policy_sha256": evidence_policy_fingerprint(evidence_policy),
        }
    )

    def pinned(value):
        return replace(
            original,
            extraction_route=value.model_dump(mode="json"),
            configuration_version=PROCESSING_CONFIGURATION_VERSION,
            configuration_fingerprint=default_processing_configuration_fingerprint(value),
        )

    service._validate_processing_configuration(pinned(route), require_engines=False)
    with pytest.raises(IngestionFailure, match="configuration_mismatch"):
        service._validate_processing_configuration(
            pinned(route.model_copy(update=change)), require_engines=False
        )
