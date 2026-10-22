"""Independent trust boundary fixtures, never model/production qualification."""

from dataclasses import replace

import pytest

from doclens_ai.chunking.ir import chunk_verified_ir
from doclens_ai.extraction.ir import (
    CellElement,
    DocumentIR,
    FormulaElement,
    Issue,
    Relation,
    SourceIdentity,
    TableElement,
    TextElement,
    Verification,
)
from doclens_ai.extraction.ir_validation import (
    EvidencePolicy,
    EvidenceReview,
    ReviewDecision,
    canonical_digest,
    observation_digest,
    validate_ir,
)
from doclens_ai.extraction.models import DocumentFormat, SourceLocation
from doclens_ai.services.ingestion import canonicalize_chunk
from tests.unit.test_document_ir import (
    FakeRegionsEngine,
    FakeWordsEngine,
    adapt_regions,
    adapt_words,
    provenance,
)


def source(fmt=DocumentFormat.PDF):
    return SourceIdentity(
        sha256="b" * 64,
        size_bytes=123,
        document_format=fmt,
        workspace_id="workspace-1",
        document_version_id="version-1",
    )


def document(elements=None, relations=(), **kwargs):
    if elements is None:
        elements = (adapt_words(FakeWordsEngine().extract()),)
    return DocumentIR(
        source=source(), state="complete", elements=elements, relations=relations, **kwargs
    )


def policy(ir, **kwargs):
    return EvidencePolicy(
        trusted_reviewers=frozenset({("fixture-reviewer", "r1")}),
        allowed_engines=frozenset(
            (e.provenance.engine, e.provenance.revision, e.provenance.implementation_sha256)
            for e in ir.elements
        ),
        **kwargs,
    )


def review(ir, *, exclude=(), failed=()):
    return EvidenceReview(
        source=ir.source,
        reviewer="fixture-reviewer",
        revision="r1",
        document_sha256=canonical_digest(ir.model_dump(mode="json")),
        decisions=tuple(
            ReviewDecision(
                subject_id=subject.id,
                subject_kind=kind,
                observation_sha256=observation_digest(subject),
                state="verified" if subject.id not in failed else "failed",
            )
            for kind, subjects in (("element", ir.elements), ("relation", ir.relations))
            for subject in subjects
            if subject.id not in exclude
        ),
    )


def test_pdf_is_closed_by_default_and_self_claims_never_approve():
    ir = document()
    assert validate_ir(ir, expected=source(), review=review(ir), policy=policy(ir)).allowed == ()
    claimed = ir.elements[0].model_copy(update={"verification": Verification(state="verified")})
    ir = document((claimed,))
    verdict = validate_ir(
        ir, expected=source(), review=None, policy=policy(ir, allow_verified_pdf=True)
    )
    assert verdict.allowed == ()
    assert "missing_review" in verdict.global_reasons


@pytest.mark.parametrize(
    "engine,adapter", [(FakeWordsEngine(), adapt_words), (FakeRegionsEngine(), adapt_regions)]
)
def test_two_incompatible_fake_engines_have_same_validated_chunk_boundary(engine, adapter):
    ir = document((adapter(engine.extract()),))
    out = chunk_verified_ir(
        ir, expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True)
    )
    assert len(out.chunks) == 1
    assert out.chunks[0].text == "-10 kg"
    assert out.units[0].elements[0].geometry == ir.elements[0].geometry
    assert out.chunks[0].provenance[0].source == ir.elements[0].source
    assert (
        out.chunks
        == chunk_verified_ir(
            ir, expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True)
        ).chunks
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("workspace_id", "other"),
        ("document_version_id", "other"),
        ("sha256", "c" * 64),
        ("size_bytes", 124),
        ("document_format", DocumentFormat.DOCX),
    ],
)
def test_source_or_tenant_mismatch_is_global_failure(field, value):
    ir = document()
    expected = source().model_copy(update={field: value})
    assert (
        validate_ir(
            ir, expected=expected, review=review(ir), policy=policy(ir, allow_verified_pdf=True)
        ).allowed
        == ()
    )


@pytest.mark.parametrize(
    "change",
    [
        {"text": "-999 kg"},
        {"source": SourceLocation(page_number=2)},
        {"provenance": provenance("other-engine")},
        {"state": "partial"},
        {"source": SourceLocation(page_number=0)},
        {"source": SourceLocation(page_number=1, row_index=-1)},
        {"text": "bad\ufffd"},
    ],
)
def test_post_review_observation_tampering_and_bad_locators_fail(change):
    original = document()
    changed = document((original.elements[0].model_copy(update=change),))
    assert (
        validate_ir(
            changed,
            expected=source(),
            review=review(original),
            policy=policy(original, allow_verified_pdf=True),
        ).allowed
        == ()
    )


def linked_table():
    common = dict(provenance=provenance("fake-table"))
    header = TextElement(
        id="header",
        text="Net amount",
        source=SourceLocation(page_number=1, block_index=0),
        **common,
    )
    row = TextElement(
        id="row", text="2026", source=SourceLocation(page_number=1, block_index=1), **common
    )
    unit = TextElement(
        id="unit", text="kg", source=SourceLocation(page_number=1, block_index=2), **common
    )
    value = CellElement(
        id="value",
        text="-001.50",
        raw_value="-001.50",
        source=SourceLocation(page_number=1, block_index=3, row_index=0, column_index=0),
        row_index=0,
        column_index=0,
        **common,
    )
    formula = FormulaElement(
        id="formula",
        expression="A1*-1",
        cached_value="-001.50",
        source=SourceLocation(page_number=1, block_index=4),
        **common,
    )
    elements = (header, row, unit, value, formula)
    relations = tuple(
        Relation(
            id=f"link:{e.id}",
            kind=kind,
            source_id=e.id,
            target_id="value",
            provenance=provenance("fake-table"),
        )
        for e, kind in (
            (header, "header_value"),
            (row, "row_value"),
            (unit, "unit_value"),
            (formula, "formula_value"),
        )
    )
    return document(elements, relations)


def test_atomic_semantic_group_keeps_signs_precision_units_formula_and_all_locations():
    ir = linked_table()
    out = chunk_verified_ir(
        ir, expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True)
    )
    assert len(out.units) == len(out.chunks) == 1
    text = out.chunks[0].text
    for exact in ("Net amount", "2026", "kg", "-001.50", "A1*-1"):
        assert exact in text
    assert len(out.units[0].relations) == 4
    assert len(out.chunks[0].provenance) == 5
    from uuid import uuid4

    assert len(canonicalize_chunk(uuid4(), out.chunks[0]).source_provenance) == 5


@pytest.mark.parametrize("subject", ["header", "unit", "value", "link:formula"])
def test_missing_review_for_any_linked_element_or_relation_holds_the_whole_group(subject):
    ir = linked_table()
    out = chunk_verified_ir(
        ir,
        expected=source(),
        review=review(ir, exclude=(subject,)),
        policy=policy(ir, allow_verified_pdf=True),
    )
    assert out.chunks == ()


def test_oversized_linked_group_is_not_split_and_partial_elements_do_not_leak():
    ir = linked_table()
    assert (
        chunk_verified_ir(
            ir,
            expected=source(),
            review=review(ir),
            policy=policy(ir, allow_verified_pdf=True),
            max_characters=5,
        ).chunks
        == ()
    )
    element = adapt_words(FakeWordsEngine().extract()).model_copy(update={"id": "unrelated"})
    failed = TextElement(
        id="bad",
        text="unreviewed",
        source=SourceLocation(page_number=2),
        provenance=provenance(),
        state="failed",
        reason="page extraction failed",
    )
    ir = document(
        (element, failed), issues=(Issue(code="page_failed", state="failed", element_id="bad"),)
    )
    out = chunk_verified_ir(
        ir, expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True)
    )
    assert [chunk.text for chunk in out.chunks] == ["-10 kg"]
    assert out.validation.rejected


def test_conflicting_numbers_are_preserved_and_both_denied_even_if_review_claims_verified():
    a = adapt_words(FakeWordsEngine().extract())
    b = a.model_copy(update={"id": "other", "text": "-999 kg"})
    link = Relation(
        id="conflict", kind="conflict", source_id=a.id, target_id=b.id, provenance=provenance()
    )
    ir = document((a, b), (link,))
    assert (
        chunk_verified_ir(
            ir, expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True)
        ).chunks
        == ()
    )
    assert ir.elements[1].text == "-999 kg"


def test_untrusted_reviewer_and_stale_review_and_duplicate_decisions_rejected():
    ir = document()
    rev = review(ir)
    for changed in (
        replace(rev, reviewer="engine-self-review"),
        replace(rev, source=source().model_copy(update={"workspace_id": "other"})),
        replace(rev, decisions=rev.decisions + rev.decisions),
    ):
        assert (
            validate_ir(
                ir, expected=source(), review=changed, policy=policy(ir, allow_verified_pdf=True)
            ).allowed
            == ()
        )


def test_chunk_identity_changes_with_review_policy_and_preserves_exact_text():
    ir = document()
    kw = dict(expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True))
    first = chunk_verified_ir(ir, **kw).chunks[0]
    second = chunk_verified_ir(ir, max_characters=999, **kw).chunks[0]
    assert first.chunk_id != second.chunk_id
    assert first.text == second.text == ir.elements[0].text


@pytest.mark.parametrize(
    "change",
    [
        {"source": SourceLocation(page_number=0)},
        {"source": SourceLocation(page_number=1, xml_path=(0,))},
        {"source": SourceLocation(page_number=1, sheet_name="fabricated")},
        {"source": SourceLocation(page_number=1, row_index=-1)},
        {"text": "bad\x00value"},
        {"text": "bad\ufffdvalue"},
        {"state": "unsupported"},
    ],
)
def test_structural_defects_rejected_even_with_matching_external_review(change):
    element = adapt_words(FakeWordsEngine().extract()).model_copy(update=change)
    ir = document((element,))
    assert not validate_ir(
        ir, expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True)
    ).allowed


@pytest.mark.parametrize(
    "fmt,locator,valid",
    [
        (DocumentFormat.DOCX, SourceLocation(part_uri="/word/document.xml", xml_path=(0, 2)), True),
        (DocumentFormat.DOCX, SourceLocation(part_uri="/word/../x.xml", xml_path=(0,)), False),
        (DocumentFormat.DOCX, SourceLocation(part_uri="/word/document.xml", xml_path=(-1,)), False),
        (
            DocumentFormat.DOCX,
            SourceLocation(part_uri="/word/document.xml", xml_path=(0,), page_number=1),
            False,
        ),
        (
            DocumentFormat.XLSX,
            SourceLocation(
                sheet_index=0, sheet_name="S", cell_coordinate="B7", row_index=6, column_index=1
            ),
            True,
        ),
        (
            DocumentFormat.XLSX,
            SourceLocation(
                sheet_index=0, sheet_name="S", cell_coordinate="B7", row_index=7, column_index=1
            ),
            False,
        ),
        (
            DocumentFormat.XLSX,
            SourceLocation(
                sheet_index=0,
                sheet_name="S",
                cell_coordinate="XFE1",
                row_index=0,
                column_index=16384,
            ),
            False,
        ),
    ],
)
def test_office_locators_are_native_and_bounded(fmt, locator, valid):
    element = TextElement(id="text", text="-001.5 kg", source=locator, provenance=provenance())
    ir = DocumentIR(source=source(fmt), state="complete", elements=(element,))
    verdict = validate_ir(ir, expected=source(fmt), review=review(ir), policy=policy(ir))
    assert bool(verdict.allowed) is valid


@pytest.mark.parametrize(
    "required",
    [{"required_kinds": frozenset({"table"})}, {"required_relations": frozenset({"header_value"})}],
)
def test_capability_is_measured_from_eligible_observations(required):
    ir = document()
    out = validate_ir(
        ir,
        expected=source(),
        review=review(ir),
        policy=policy(ir, allow_verified_pdf=True, **required),
    )
    assert "required_capability_not_validated" in out.global_reasons
    assert out.allowed == ()


def test_table_overlap_and_huge_spans_are_bounded_and_block_the_complete_group():
    for span in (1, 10**12):
        table = TableElement(
            id="table", source=SourceLocation(page_number=1, table_index=0), provenance=provenance()
        )
        cells = tuple(
            CellElement(
                id=f"cell:{index}",
                source=SourceLocation(
                    page_number=1, block_index=index, table_index=0, row_index=0, column_index=0
                ),
                provenance=provenance(),
                text=str(index),
                row_index=0,
                column_index=0,
                column_span=span,
            )
            for index in range(2)
        )
        links = tuple(
            Relation(
                id=f"contains:{c.id}",
                kind="contains",
                source_id="table",
                target_id=c.id,
                provenance=provenance(),
            )
            for c in cells
        )
        ir = document((table, *cells), links)
        verdict = validate_ir(
            ir, expected=source(), review=review(ir), policy=policy(ir, allow_verified_pdf=True)
        )
        assert verdict.allowed == ()
        reasons = dict(verdict.rejected)["table"]
        assert ("overlapping_table_cells" if span == 1 else "table_grid_limit") in reasons


def test_valid_spanning_table_has_one_atomic_chunk():
    table = TableElement(
        id="table", source=SourceLocation(page_number=1, table_index=0), provenance=provenance()
    )
    cell = CellElement(
        id="cell",
        source=SourceLocation(page_number=1, table_index=0, row_index=0, column_index=0),
        provenance=provenance(),
        text="001",
        row_index=0,
        column_index=0,
        column_span=2,
    )
    link = Relation(
        id="contains", kind="contains", source_id="table", target_id="cell", provenance=provenance()
    )
    ir = document((table, cell), (link,))
    out = chunk_verified_ir(
        ir,
        expected=source(),
        review=review(ir),
        policy=policy(ir, allow_verified_pdf=True, required_kinds=frozenset({"table", "cell"})),
    )
    assert out.chunks[0].text == "text=001"
    assert out.units[0].elements[1].column_span == 2


def test_document_budget_does_not_return_a_partial_prefix():
    a = adapt_words(FakeWordsEngine().extract())
    b = a.model_copy(update={"id": "second", "source": SourceLocation(page_number=2)})
    ir = document((a, b))
    for budget in ({"max_chunks": 1}, {"max_source_characters": 6}):
        out = chunk_verified_ir(
            ir,
            expected=source(),
            review=review(ir),
            policy=policy(ir, allow_verified_pdf=True),
            **budget,
        )
        assert out.chunks == out.units == ()
        assert out.held[0][1] == "document_limit"


@pytest.mark.parametrize("blocks", ["bad", ["bad"], [{"kind": "wrong", "text": "bad"}]])
def test_malformed_native_wire_fails_with_validation_error(blocks):
    from pydantic import ValidationError

    from doclens_ai.extraction.adapters import adapt_native
    from tests.unit.test_document_ir import result

    wire = adapt_native(result(), provenance=provenance()).model_dump(mode="json")
    wire["native"]["blocks"] = blocks
    with pytest.raises(ValidationError):
        DocumentIR.model_validate(wire)
