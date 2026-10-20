"""Public synthetic evidence only; these attestations never stand for human Gold."""

from __future__ import annotations

import copy
from datetime import date

import pytest
from pydantic import ValidationError

from doclens_ai.chunking.core import chunk_document
from doclens_ai.chunking.models import ChunkingConfig, ChunkingStrategy
from doclens_ai.chunking.table_v2 import context_survival, table_chunks
from doclens_ai.extraction.evidence_v2 import (
    Cell,
    EvidenceEnvelope,
    HumanReview,
    Locator,
    Page,
    Proposal,
    Relation,
    ReviewedDocument,
    Scope,
    Table,
    envelope,
    native_text_evidence,
    verify_proposal,
)
from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.hybrid_pdf import CandidateOutcome, hybrid_pdf, merge_native
from doclens_ai.extraction.models import (
    DocumentFormat,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TextBlock,
)


def fixture():
    scope = Scope(
        workspace_id="synthetic-workspace",
        document_id="synthetic-document",
        version_id="v1",
        raw_sha256="a" * 64,
    )

    def cell(name, text, row, col, role, span=1):
        return Cell(
            cell_id=name,
            literal=text,
            row=row,
            column=col,
            row_span=1,
            column_span=span,
            locator=Locator(
                page=1,
                bbox=(float(col * 50), float(row * 30), float(col * 50 + 45), float(row * 30 + 20)),
                coordinate_basis="pdf_user_space_unrotated",
            ),
            role=role,
        )

    cells = (
        cell("header", "Revenue", 0, 0, "column_header", 2),
        cell("row", "Division", 1, 0, "row_header"),
        cell("value", "-001.25", 1, 1, "value"),
        cell("unit", "kg", 2, 0, "unit"),
        cell("period", "2026-Q1", 2, 1, "period"),
    )
    table = Table(
        table_id="table-1",
        section_id="section-1",
        cells=cells,
        relations=tuple(
            Relation(left="value", right=right, kind=kind, evidence_note="synthetic source oracle")
            for right, kind in (
                ("header", "column_header"),
                ("row", "row_header"),
                ("unit", "unit"),
                ("period", "period"),
            )
        ),
        complete=True,
    )
    review = HumanReview(
        reviewer_id="fixture-author",
        reviewed_on=date(2026, 1, 1),
        kind="synthetic_fixture",
        independent_of_annotator=True,
        original_pages_inspected=True,
        parser_outputs_seen=False,
        legacy_seen_before_draft=False,
        prior_exposure="public fixture",
        viewer="fixture",
        viewer_version="1",
        render_settings="native points",
        draft_sha256="b" * 64,
        annotation_authorized=True,
        annotation_permission_reference="synthetic-public-fixture",
    )
    gold = ReviewedDocument(
        revision="synthetic-v2",
        scope=scope,
        pages=(
            Page(
                number=1,
                media_box=(0.0, 0.0, 300.0, 400.0),
                crop_box=(0.0, 0.0, 300.0, 400.0),
                rotation=0,
            ),
        ),
        review=review,
        family_id="family-1",
        languages=("en",),
        split="dev",
        tables=(table,),
        decisions_sha256="c" * 64,
    )
    proposal = Proposal(
        scope=scope,
        engine="synthetic",
        candidate_revision="fixture-1",
        config_sha256="d" * 64,
        tables=(table,),
    )
    native = ExtractionResult(
        schema_version="1.0",
        document_format=DocumentFormat.PDF,
        status=ExtractionStatus.SUCCESS,
        source_sha256=scope.raw_sha256,
        source_size_bytes=10,
        blocks=(
            TextBlock(
                0,
                "Revenue Division -001.25 kg 2026-Q1",
                SourceLocation(page_number=1, block_index=0),
            ),
        ),
    )
    return scope, gold, proposal, native


def test_exact_independent_match_and_v1_roundtrip():
    scope, gold, proposal, native = fixture()
    e = envelope(
        native,
        scope,
        parser_revision="fixture",
        proposal=proposal,
        reviewed=gold,
        allow_synthetic=True,
    )
    assert e.decisions[0].state == "accepted"
    assert len(e.decisions[0].evidence_ids) == 5
    assert EvidenceEnvelope.model_validate_json(e.model_dump_json()) == e
    assert e.native_v1 == native.to_dict()
    assert not e.production_authorized
    ids = native_text_evidence(native, scope)
    assert ids[0]["literal"] == native.blocks[0].text and ids[0]["bbox"] is None
    assert ids == native_text_evidence(native, scope)
    before = chunk_document(
        native,
        document_id="synthetic-document",
        config=ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE),
    )
    assert before.chunks
    assert native.to_dict() == e.native_v1


def test_synthetic_review_never_qualifies_default():
    scope, gold, proposal, _ = fixture()
    with pytest.raises(ValueError, match="synthetic"):
        verify_proposal(proposal, scope, gold)


@pytest.mark.parametrize(
    "field,value",
    [
        ("workspace_id", "other"),
        ("document_id", "other"),
        ("version_id", "v2"),
        ("raw_sha256", "f" * 64),
    ],
)
def test_cross_scope_rejected(field, value):
    scope, gold, proposal, _ = fixture()
    changed = proposal.model_copy(update={"scope": scope.model_copy(update={field: value})})
    decisions = verify_proposal(changed, scope, gold, allow_synthetic=True)
    assert decisions[0].state == "rejected" and decisions[0].evidence_ids == ()


@pytest.mark.parametrize("literal", ["001.25", "-001,25", "1.25", "-001.26", "kg ", "2027-Q1"])
def test_changed_number_sign_decimal_unit_period_needs_review(literal):
    scope, gold, proposal, _ = fixture()
    table = proposal.tables[0]
    changed = table.cells[2].model_copy(update={"literal": literal})
    candidate = proposal.model_copy(
        update={
            "tables": (
                table.model_copy(update={"cells": (*table.cells[:2], changed, *table.cells[3:])}),
            )
        }
    )
    assert verify_proposal(candidate, scope, gold, allow_synthetic=True)[0].state == "needs_review"


@pytest.mark.parametrize("change", ["bbox", "page", "span", "row", "role", "relationship"])
def test_source_or_structural_conflict_never_accepted(change):
    scope, gold, proposal, _ = fixture()
    raw = proposal.model_dump(mode="json")
    cell = raw["tables"][0]["cells"][2]
    if change == "bbox":
        cell["locator"]["bbox"] = [1.0, 1.0, 2.0, 2.0]
    elif change == "page":
        cell["locator"]["page"] = 2
    elif change == "relationship":
        raw["tables"][0]["relations"][0]["right"] = "period"
    else:
        cell[{"span": "column_span", "row": "row", "role": "role"}[change]] = (
            "unit" if change == "role" else 4
        )
    candidate = Proposal.model_validate_json(__import__("json").dumps(raw))
    assert verify_proposal(candidate, scope, gold, allow_synthetic=True)[0].state != "accepted"


def test_unreviewed_borderless_repeated_rotated_multipage_proposals_are_untrusted():
    scope, _, proposal, native = fixture()
    e = envelope(native, scope, parser_revision="fixture", proposal=proposal)
    assert e.decisions[0].state == "needs_review"
    assert e.native_v1 == native.to_dict()


def test_duplicate_table_identity_invalidates_all_occurrences():
    scope, gold, proposal, _ = fixture()
    proposal = proposal.model_copy(update={"tables": proposal.tables * 2})
    assert all(
        d.state == "rejected" for d in verify_proposal(proposal, scope, gold, allow_synthetic=True)
    )


@pytest.mark.parametrize(
    "failure",
    [
        "timeout",
        "memory_limit",
        "output_limit",
        "unavailable",
        "worker_failed",
        "invalid_output",
        "cleanup_failed",
    ],
)
def test_failed_candidate_and_disabled_merge_preserve_native(failure):
    scope, gold, proposal, native = fixture()
    outcome = CandidateOutcome(status="failed", failure=failure, proposal=proposal)
    enriched = merge_native(native, scope, outcome=outcome, reviewed=gold, enabled=True)
    assert enriched.native_v1 == native.to_dict() and enriched.proposal is None
    assert enriched.warnings == ("candidate_" + failure,)
    disabled = merge_native(native, scope, outcome=outcome, reviewed=gold)
    assert disabled.proposal is None and disabled.native_v1 == native.to_dict()


def test_native_tampering_detected_even_after_nested_dict_mutation():
    scope, _, _, native = fixture()
    e = envelope(native, scope, parser_revision="fixture")
    e.native_v1["blocks"][0]["text"] = "overwritten"
    with pytest.raises(ValidationError):
        EvidenceEnvelope.model_validate(e)


def test_trusted_chunks_keep_complete_semantic_closure_and_exact_literals():
    scope, gold, proposal, native = fixture()
    e = envelope(
        native,
        scope,
        parser_revision="fixture",
        proposal=proposal,
        reviewed=gold,
        allow_synthetic=True,
    )
    chunks, warnings = table_chunks(e, gold, allow_synthetic=True)
    assert not warnings and len(chunks) == 1
    chunk = chunks[0]
    assert {c.literal for c in chunk.cells} == {"Revenue", "Division", "-001.25", "kg", "2026-Q1"}
    assert chunk.cells[0].column_span == 2
    assert chunk.table_id == "table-1" and chunk.section_id == "section-1"
    assert chunk.scope == scope and len(chunk.relations) == 4
    assert table_chunks(e, gold, allow_synthetic=True)[0] == chunks
    survival = context_survival(chunks, (frozenset(chunk.evidence_ids),), max_characters=1200)
    assert survival["complete_in_context"] == 1 and survival["answer_quality"] == "NOT_EVALUATED"
    assert (
        context_survival(chunks, (frozenset(chunk.evidence_ids),), max_characters=1)[
            "complete_in_context"
        ]
        == 0
    )
    limited, warnings = table_chunks(e, gold, max_characters=2, allow_synthetic=True)
    assert limited == () and warnings == ("complete_evidence_exceeds_budget",)


def test_unverified_or_forged_decisions_do_not_enter_trusted_chunks():
    scope, gold, proposal, native = fixture()
    e = envelope(native, scope, parser_revision="fixture", proposal=proposal)
    with pytest.raises(ValueError, match="decision mismatch"):
        table_chunks(e, gold, allow_synthetic=True)
    gold_other = gold.model_copy(update={"scope": scope.model_copy(update={"version_id": "v2"})})
    with pytest.raises(ValueError, match="scope"):
        table_chunks(e, gold_other, allow_synthetic=True)
    e = e.model_copy(
        update={"decisions": verify_proposal(proposal, scope, gold, allow_synthetic=True)}
    )
    changed = copy.deepcopy(e.native_v1)
    changed["blocks"][0]["text"] = "bad"
    with pytest.raises(ValueError):
        table_chunks(e.model_copy(update={"native_v1": changed}), gold, allow_synthetic=True)


@pytest.mark.parametrize("identity", ["Codex", "LLM reviewer", "extractor", "ChatGPT", "assistant"])
def test_machine_identity_is_not_human(identity):
    _, gold, _, _ = fixture()
    with pytest.raises(ValidationError):
        HumanReview.model_validate(gold.review.model_copy(update={"reviewer_id": identity}))


@pytest.mark.parametrize(
    "bbox", [(0.0, 0.0, float("nan"), 10.0), (0.0, 0.0, 0.0, 10.0), (10.0, 10.0, 1.0, 1.0)]
)
def test_invalid_geometry_rejected(bbox):
    with pytest.raises(ValidationError):
        Locator(page=1, bbox=bbox, coordinate_basis="pdf_user_space_unrotated")


def test_actual_pdf_page_inventory_is_checked(tmp_path):
    from pypdf import PdfWriter

    from tools.extraction_quality.pdf_table_review_packet import sha

    scope, gold, proposal, _ = fixture()
    path = tmp_path / "fixture.pdf"
    writer = PdfWriter()
    writer.add_blank_page(300, 400)
    writer.write(path)
    scope = scope.model_copy(update={"raw_sha256": sha(path)})
    gold = gold.model_copy(update={"scope": scope})
    proposal = proposal.model_copy(update={"scope": scope})
    outcome = CandidateOutcome(status="success", failure=None, proposal=proposal)
    actual = hybrid_pdf(
        path, scope, outcome=outcome, reviewed=gold, enabled=True, allow_synthetic=True
    )
    assert actual.decisions[0].state == "accepted"
    wrong = gold.model_copy(update={"pages": (gold.pages[0].model_copy(update={"rotation": 90}),)})
    actual = hybrid_pdf(
        path, scope, outcome=outcome, reviewed=wrong, enabled=True, allow_synthetic=True
    )
    assert actual.decisions[0].state == "needs_review"
    assert fingerprint(actual.native_v1) == actual.native_sha256
