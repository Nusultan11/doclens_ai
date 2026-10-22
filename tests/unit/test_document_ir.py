"""Synthetic contract tests; these are not independent extraction fidelity evidence."""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from doclens_ai.extraction.adapters import adapt_native
from doclens_ai.extraction.ir import (
    CellElement,
    DocumentIR,
    FormulaElement,
    Geometry,
    LayoutElement,
    Provenance,
    Relation,
    SourceIdentity,
    TextElement,
    VisualElement,
)
from doclens_ai.extraction.models import (
    DocumentFormat,
    ErrorCategory,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    SpreadsheetCell,
    SpreadsheetSheet,
    TableBlock,
    TableCell,
    TableRow,
    TextBlock,
)


def provenance(engine="native"):
    return Provenance(
        engine=engine,
        revision="fixture-r1",
        implementation_sha256="a" * 64,
        observation_id="observation-1",
    )


def result(fmt=DocumentFormat.PDF):
    return ExtractionResult(
        schema_version="1.1",
        document_format=fmt,
        status=ExtractionStatus.SUCCESS,
        source_sha256="b" * 64,
        source_size_bytes=123,
        blocks=(TextBlock(order=0, text="-001.50 kg", source=SourceLocation(page_number=1)),),
    )


@pytest.mark.parametrize("fmt", list(DocumentFormat))
def test_native_roundtrip_is_additive_and_does_not_invent_trust_or_geometry(fmt):
    original = result(fmt)
    before = original.to_dict()
    ir = adapt_native(original, provenance=provenance())
    restored = DocumentIR.model_validate_json(ir.model_dump_json())
    assert restored == ir
    assert restored.native.to_dict() == before == original.to_dict()
    assert ir.elements[0].text == "-001.50 kg"
    assert ir.elements[0].geometry is None
    assert ir.elements[0].verification.state == "unknown"
    assert ir.source.workspace_id is None


def test_native_cells_formulas_and_full_sparse_metadata_survive():
    cell = SpreadsheetCell(
        coordinate="B7",
        row_index=6,
        column_index=1,
        value="-001.50",
        formula="A7*-1",
        cached_value="-001.50",
        data_type="n",
        source=SourceLocation(
            sheet_index=0, sheet_name="S", cell_coordinate="B7", row_index=6, column_index=1
        ),
        raw_value="-001.50",
        number_format="0.00",
        has_formula=True,
        formula_attributes=(("t", "shared"),),
    )
    original = replace(
        result(DocumentFormat.XLSX),
        blocks=(),
        sheets=(
            SpreadsheetSheet(
                index=0,
                name="S",
                state="hidden",
                cells=(cell,),
                merged_ranges=("B7:C7",),
                tables=(),
            ),
        ),
    )
    ir = adapt_native(original, provenance=provenance())
    restored = DocumentIR.model_validate_json(ir.model_dump_json())
    assert restored.native == original
    assert ir.elements[0].formula == "A7*-1"
    assert ir.elements[0].cached_value == ir.elements[0].raw_value == "-001.50"
    assert ir.relations == ()  # No invented headers/units/row semantics.


def test_native_table_spans_and_containment_preserved():
    loc = SourceLocation(
        block_index=0, table_index=0, part_uri="/word/document.xml", xml_path=(0, 0)
    )
    cell = TableCell(
        row_index=0,
        column_index=0,
        text="001",
        source=replace(loc, row_index=0, column_index=0),
        column_span=2,
    )
    native = replace(
        result(DocumentFormat.DOCX),
        blocks=(
            TableBlock(
                order=0,
                table_index=0,
                rows=(TableRow(row_index=0, cells=(cell,)),),
                source=loc,
                header_row_indices=(0,),
            ),
        ),
    )
    ir = adapt_native(native, provenance=provenance())
    assert DocumentIR.model_validate_json(ir.model_dump_json()).native == native
    assert ir.elements[1].column_span == 2
    assert [(r.kind, r.source_id, r.target_id) for r in ir.relations] == [
        ("contains", "block:0", "block:0:row:0:cell:0")
    ]


def test_missing_source_and_failure_remain_unknown():
    native = replace(
        result(),
        source_sha256=None,
        source_size_bytes=None,
        status=ExtractionStatus.FAILED,
        error_category=ErrorCategory.CORRUPT_DOCUMENT,
    )
    ir = adapt_native(native, provenance=provenance())
    assert ir.source.sha256 is None
    assert ir.state == "failed"
    assert ir.issues[0].code == "corrupt_document"


class FakeWordsEngine:
    """One fake reports top-left point coordinates and page words."""

    def extract(self):
        return {"pages": [{"number": 1, "words": [(5, 10, 50, 20, "-10 kg")]}]}


class FakeRegionsEngine:
    """An incompatible fake reports bottom-left pixel-independent regions."""

    def extract(self):
        return [
            {
                "page_id": 1,
                "region": {"left": 5, "bottom": 80, "right": 50, "top": 90},
                "transcript": "-10 kg",
            }
        ]


def adapt_words(payload):
    page = payload["pages"][0]
    x0, y0, x1, y1, text = page["words"][0]
    return TextElement(
        id="words:0",
        source=SourceLocation(page_number=page["number"]),
        text=text,
        provenance=provenance("fake-words"),
        geometry=Geometry(
            coordinate_system="top_left_points",
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            page_width=100,
            page_height=100,
        ),
    )


def adapt_regions(payload):
    region = payload[0]
    box = region["region"]
    return TextElement(
        id="region:0",
        source=SourceLocation(page_number=region["page_id"]),
        text=region["transcript"],
        provenance=provenance("fake-regions"),
        geometry=Geometry(
            coordinate_system="bottom_left_points",
            x0=box["left"],
            y0=box["bottom"],
            x1=box["right"],
            y1=box["top"],
            page_width=100,
            page_height=100,
        ),
    )


@pytest.mark.parametrize(
    "engine,adapter", [(FakeWordsEngine(), adapt_words), (FakeRegionsEngine(), adapt_regions)]
)
def test_incompatible_fake_observations_share_one_contract(engine, adapter):
    element = adapter(engine.extract())
    ir = DocumentIR(
        source=SourceIdentity(sha256="b" * 64, document_format=DocumentFormat.PDF, size_bytes=123),
        state="complete",
        elements=(element,),
    )
    assert DocumentIR.model_validate_json(ir.model_dump_json()) == ir
    assert ir.elements[0].verification.state == "unknown"
    assert ir.elements[0].text == "-10 kg"


@pytest.mark.parametrize(
    "change",
    [
        {"x0": -1},
        {"x1": 101},
        {"x0": 50, "x1": 40},
        {"y1": float("nan")},
        {"page_height": float("inf")},
        {"coordinate_system": "guessed"},
        {"x0": False},
        {"x1": "10"},
        {"page_width": "100"},
    ],
)
def test_geometry_rejects_unbounded_or_ambiguous_coordinates(change):
    kwargs = dict(
        coordinate_system="top_left_points",
        x0=0,
        y0=0,
        x1=10,
        y1=10,
        page_width=100,
        page_height=100,
    )
    with pytest.raises(ValidationError):
        Geometry(**(kwargs | change))


def test_optional_element_types_and_explicit_partial_state():
    common = dict(source=SourceLocation(page_number=1), provenance=provenance())
    elements = (
        LayoutElement(id="section", kind="section", role=None, **common),
        LayoutElement(id="layout", kind="layout", **common),
        VisualElement(id="image", kind="image", **common),
        VisualElement(id="figure", kind="figure", **common),
        FormulaElement(
            id="formula",
            expression="x=-1",
            state="unresolved",
            reason="unverified transcription",
            **common,
        ),
        CellElement(id="cell", row_index=0, column_index=0, **common),
    )
    ir = DocumentIR(source=SourceIdentity(), state="partial", elements=elements)
    assert DocumentIR.model_validate_json(ir.model_dump_json()) == ir


def test_contract_rejects_duplicate_ids_dangling_links_unknown_versions_and_geometry_without_page():
    element = adapt_words(FakeWordsEngine().extract())
    common = dict(source=SourceIdentity(), state="complete")
    bad_cases = [
        {"elements": (element, element)},
        {"schema_version": "3.0"},
        {
            "elements": (element,),
            "relations": (
                Relation(
                    id="r",
                    kind="header_value",
                    source_id=element.id,
                    target_id="missing",
                    provenance=provenance(),
                ),
            ),
        },
        {"elements": (element.model_copy(update={"source": SourceLocation()}),)},
    ]
    for case in bad_cases:
        with pytest.raises(ValidationError):
            DocumentIR(**(common | case))
