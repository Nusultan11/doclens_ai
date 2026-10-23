from __future__ import annotations

from xml.etree import ElementTree as ET

import pytest
from PIL import Image
from pypdf import PdfWriter

from doclens_ai.eda import corpus_v2 as corpus
from tests.unit.test_readiness_release import workbook
from tools.extraction_quality import office_readiness_oracle as oracle
from tools.extraction_quality import readiness_evaluator as evaluator
from tools.extraction_quality import readiness_pdf_metrics as metrics
from tools.extraction_quality import readiness_source_checks as checks
from tools.extraction_quality.readiness_evaluator import Prediction, Predictions, compare


def page(text=""):
    return {
        "page": 1,
        "width": 100,
        "height": 100,
        "rotation": 0,
        "native_text": text,
        "glyphs": [
            {
                "index": i,
                "character": c,
                "bbox": [10 + i, 10, 11 + i, 12],
                "reliable": True,
                "generated": 0,
            }
            for i, c in enumerate(text)
        ],
    }


def cell(text=""):
    return {
        "item_id": "c",
        "bbox": [5, 5, 50, 50],
        "proposed_text": text,
        "row_span": 1,
        "column_span": 1,
    }


def rules():
    return [
        {"axis": axis, "position": pos, "low": 5, "high": 50, "source_object_index": i}
        for i, (axis, pos) in enumerate((("h", 5), ("h", 50), ("v", 5), ("v", 50)))
    ]


def test_false_blank_and_uniform_dark_interior_are_not_certified():
    white = Image.new("RGB", (100, 100), "white")
    assert (
        checks.cell_check(page("0"), cell(), rules(), white)["state"]
        == "CONFLICT_VISIBLE_SOURCE_GLYPHS"
    )
    assert (
        checks.cell_check(page(), cell(), rules(), white)["state"]
        == "SOURCE_EMPTY_INTERIOR_SUPPORTED"
    )
    dark = Image.new("RGB", (100, 100), "black")
    assert checks.cell_check(page(), cell(), rules(), dark)["state"] == "BLANK_UNRESOLVED"
    assert checks.cell_check(page(), cell(), [], white)["state"] == "BLANK_UNRESOLVED"


def test_sign_and_internal_rule_preserved():
    image = Image.new("RGB", (100, 100), "white")
    assert (
        checks.cell_check(page("-10"), cell("10"), rules(), image)["state"]
        == "SOURCE_LITERAL_CONFLICT"
    )
    divided = rules() + [
        {"axis": "v", "position": 25, "low": 5, "high": 50, "source_object_index": 5}
    ]
    result = checks.cell_check(page("-10"), cell("-10"), divided, image)
    assert "INTERNAL_RULING_DIVIDES_CELL" in result["boundary_issues"]
    assert result["span_state"] == "PROPOSED_LOGICAL_SPAN_NOT_CERTIFIED"
    assert not result["independent_gold"]


@pytest.mark.parametrize(
    "field,value", [("row_span", 0), ("column_span", True), ("bbox", [-1, 0, 2, 3])]
)
def test_invalid_existing_geometry_rejected(field, value):
    proposal = cell()
    proposal[field] = value
    with pytest.raises(ValueError):
        checks.cell_check(page(), proposal, rules(), Image.new("RGB", (100, 100)))


def test_literal_repetition_empty_and_namespace_resolution():
    matches = checks.literal_matches(page("-1 -1"), "-1")
    assert [m["char_start"] for m in matches] == [0, 3]
    assert checks.literal_matches(page("0"), "") == []
    root = ET.fromstring('<a:root xmlns:a="urn:a" xmlns:b="urn:b"><b:p/><a:p>0</a:p></a:root>')
    locator = {"xml_path": "/a:root[1]/a:p[1]", "namespaces": {"a": "urn:a"}}
    assert checks.resolve_xml(root, locator).text == "0"
    with pytest.raises(ValueError):
        checks.resolve_xml(root, {**locator, "xml_path": "/a:root[1]/a:p[2]"})


def test_targeted_xlsx_retains_cache_and_rejects_missing_selection(tmp_path):
    path = workbook(
        tmp_path, '<c r="A1"><v>0</v></c><c r="B1"><f>1+1</f></c><c r="C1"><f>1+1</f><v/></c>'
    )
    selected = {"xl/worksheets/s1.xml": ["B1", "C1"]}
    value = oracle.observe(path, "source", corpus.sha256(path), "xlsx", selected_cells=selected)
    cells = value["observations"]["sheets"][0]["cells"]
    assert [c["cache_state"] for c in cells] == ["MISSING", "EMPTY"]
    assert not value["observations"]["selection"]["whole_workbook_coverage"]
    for bad in ({"xl/worksheets/s1.xml": ["Z9"]}, {"xl/worksheets/s1.xml": ["A1", "A1"]}, {}):
        with pytest.raises(ValueError):
            oracle.observe(path, "source", corpus.sha256(path), "xlsx", selected_cells=bad)


def reference():
    return {
        "independent_gold": False,
        "human_reviewed": False,
        "cells": [
            {
                "reference_id": "ref",
                "tier": "SOURCE",
                "page": 1,
                "bbox": [0, 0, 10, 10],
                "fields": {"native_nonspace_text": "-10", "row_span": 2},
            },
            {
                "reference_id": "unknown",
                "tier": "SOURCE",
                "page": 1,
                "bbox": [20, 0, 30, 10],
                "fields": {},
            },
        ],
    }


def prediction(text="-10", span=2):
    return Prediction.model_validate(
        {
            "source_id": "source",
            "source_sha256": "a" * 64,
            "status": "needs_review",
            "failure": None,
            "observations": [
                {
                    "kind": "pdf_cell",
                    "locator": {"page": 1, "bbox": [0, 0, 10, 10]},
                    "fields": {"text": text, "row_span": span},
                },
                {
                    "kind": "pdf_cell",
                    "locator": {"page": 1, "bbox": [40, 0, 50, 10]},
                    "fields": {"text": "extra"},
                },
            ],
        }
    )


def test_pdf_dimensions_keep_sign_span_missing_extra_and_unknown_separate():
    result = metrics.compare(prediction("10", 1), reference())
    fields = result["field_denominators"]
    assert fields["SOURCE.native_nonspace_text.exact"] == 0
    assert fields["SOURCE.row_span.exact"] == 0
    assert fields["SOURCE.native_nonspace_text.expected"] == 1
    geometry = result["geometry_diagnostic_by_page"]["1"]
    assert (geometry["matched"], geometry["expected"], geometry["predicted"]) == (1, 2, 2)
    assert metrics.compare(None, reference())["field_denominators"]["SOURCE.row_span.observed"] == 0
    assert (
        metrics.compare(prediction(" - 10 "), reference())["field_denominators"][
            "SOURCE.native_nonspace_text.exact"
        ]
        == 1
    )
    assert result["quality"] == "NOT_EVALUATED"


def test_reference_cannot_spoof_human_gold():
    with pytest.raises(ValueError):
        metrics.compare(None, {**reference(), "human_reviewed": True})


def test_reference_rejects_wrong_source_page_and_geometry():
    source = {
        "id": "source",
        "sha256": "a" * 64,
        "format": "pdf",
        "split": "dev",
        "rights": {"new_annotation": True},
        "pdf_page_count": 1,
        "pdf_page_geometry": {"1": {"width": 100, "height": 100, "rotation": 0}},
    }
    ref = {**reference(), "source_id": "source", "source_sha256": "a" * 64}
    metrics.validate_reference(ref, source)
    for modified in (
        {**ref, "source_sha256": "b" * 64},
        {**ref, "cells": [ref["cells"][0], ref["cells"][0]]},
        {**ref, "cells": [{**ref["cells"][0], "page": 2}]},
        {**ref, "cells": [{**ref["cells"][0], "bbox": [0, 0, 101, 10]}]},
    ):
        with pytest.raises(ValueError):
            metrics.validate_reference(modified, source)


@pytest.mark.parametrize("span", [0, True, 1.0])
def test_prediction_rejects_invalid_spans(span):
    with pytest.raises(ValueError):
        prediction(span=span)


def test_five_future_candidate_identities_use_identical_semantics(tmp_path, monkeypatch):
    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    original = tmp_path / "original.pdf"
    writer.write(original)
    digest = corpus.sha256(original)
    monkeypatch.setattr(evaluator, "ROOT", tmp_path)
    outputs = []
    source = {
        "id": "source",
        "sha256": digest,
        "format": "pdf",
        "split": "dev",
        "rights": {"local_evaluation": True},
        "source_reference": {
            "path": "original.pdf",
            "sha256": digest,
            "size_bytes": original.stat().st_size,
            "format": "pdf",
        },
        "pdf_page_count": 1,
        "pdf_page_geometry": {"1": {"width": 100, "height": 100, "rotation": 0}},
    }
    for index in range(5):
        item = prediction()
        item.source_sha256 = digest
        supplied = Predictions(
            version="readiness-predictions-1.0",
            model_identity=f"synthetic-candidate-{index}",
            predictions=[item],
        )
        result = compare([source], supplied, {})
        result.pop("model_identity")
        outputs.append(result)
    assert all(r == outputs[0] for r in outputs)
    invalid = prediction().model_dump()
    invalid["source_sha256"] = digest
    invalid["observations"][0]["locator"]["page"] = 2
    with pytest.raises(ValueError, match="outside original"):
        compare(
            [source],
            Predictions(
                version="readiness-predictions-1.0",
                model_identity="test",
                predictions=[Prediction.model_validate(invalid)],
            ),
            {},
        )
    invalid["observations"][0]["locator"].update(page=1, bbox=[0, 0, 101, 10])
    with pytest.raises(ValueError, match="outside original"):
        compare(
            [source],
            Predictions(
                version="readiness-predictions-1.0",
                model_identity="test",
                predictions=[Prediction.model_validate(invalid)],
            ),
            {},
        )
