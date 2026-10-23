from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tools.extraction_quality import readiness_evaluator as evaluator


def source(key="e2-office-demo", **changes):
    return {
        "id": key,
        "sha256": "a" * 64,
        "format": "xlsx",
        "split": "dev",
        "reserved_qa_family": False,
        "rights": {"local_evaluation": True},
        **changes,
    }


def reference():
    return {
        "version": "office-source-oracle-1.0",
        "tier": "SOURCE_NATIVE_ORACLE",
        "source_id": "e2-office-demo",
        "source_sha256": "a" * 64,
        "format": "xlsx",
        "human_reviewed": False,
        "independent_gold": False,
        "reviewer": None,
        "observations": {
            "sheets": [
                {
                    "sheet": {"sheetId": "1", "name": "Data"},
                    "relationship": {"part": "xl/worksheets/s1.xml"},
                    "merges": [],
                    "cells": [
                        {
                            "locator": {
                                "part": "xl/worksheets/s1.xml",
                                "sheet_id": "1",
                                "sheet_name": "Data",
                                "cell": "A1",
                            },
                            "stored_v": "0",
                            "stored_v_present": True,
                            "stored_type": "n",
                            "formula": None,
                            "display_value": None,
                            "date_interpretation": "NOT_INTERPRETED",
                        }
                    ],
                }
            ]
        },
    }


def predictions(observations=None, **changes):
    return evaluator.Predictions.model_validate(
        {
            "version": "readiness-predictions-1.0",
            "model_identity": "synthetic-test-only",
            "predictions": [
                {
                    "source_id": "e2-office-demo",
                    "source_sha256": "a" * 64,
                    "status": "success",
                    "failure": None,
                    "observations": observations or [],
                    **changes,
                }
            ],
        }
    )


def test_missing_references_and_predictions_stay_in_population():
    refs = {"e2-office-demo": reference()}
    result = evaluator.compare([source(), source("unlabeled")], predictions(), refs)
    assert result["attempted_population"] == 2
    assert result["prediction_statuses"] == {"success": 1, "NOT_ATTEMPTED": 1}
    assert result["metrics"]["xlsx_cell.stored_v"] == {"expected": 1}
    assert result["quality"] == "NOT_EVALUATED"
    assert result["rows"][1]["reference"] == "NOT_EVALUATED"


def test_exact_oracle_comparison_has_separate_display_and_quality():
    value = reference()
    observations = evaluator.oracle_observations(value)
    result = evaluator.compare([source()], predictions(observations), {"e2-office-demo": value})
    assert result["metrics"]["xlsx_cell.stored_v"] == {"expected": 1, "observed": 1, "exact": 1}
    assert not any("display" in key for key in result["metrics"])
    assert result["quality"] == "NOT_EVALUATED"
    wrong = copy.deepcopy(observations)
    wrong[1]["fields"]["stored_v"] = None
    mismatch = evaluator.compare([source()], predictions(wrong), {"e2-office-demo": value})
    assert mismatch["metrics"]["xlsx_cell.stored_v"]["exact"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("reviewer", "bogus reviewer"),
        ("human_reviewed", True),
        ("independent_gold", True),
        ("source_sha256", "b" * 64),
    ],
)
def test_forged_review_or_source_rejected(field, value):
    ref = reference()
    ref[field] = value
    with pytest.raises(ValueError):
        evaluator.compare([source()], predictions(), {"e2-office-demo": ref})


@pytest.mark.parametrize(
    "change",
    [
        {"reserved_qa_family": True},
        {"split": "test"},
        {"rights": {"local_evaluation": None}},
        {"sha256": "b" * 64},
    ],
)
def test_rights_source_and_test_leakage_fail_closed(change):
    with pytest.raises(ValueError):
        evaluator.compare([source(**change)], predictions(), {})


@pytest.mark.parametrize(
    "kind,locator",
    [
        ("pdf_cell", {"page": 0}),
        ("pdf_text", {"page": True}),
        ("docx_element", {"part": "word/document.xml", "xml_path": "/document", "page": 2}),
        ("docx_element", {"part": "../escape.xml", "xml_path": "/document"}),
        ("xlsx_cell", {"part": "xl/worksheets/s1.xml", "sheet_id": "1"}),
    ],
)
def test_invalid_or_invented_locators(kind, locator):
    with pytest.raises(ValidationError):
        evaluator.Observation(kind=kind, locator=locator, fields={})


@pytest.mark.parametrize(
    "kind",
    [
        "pdf_text",
        "pdf_reading_order",
        "pdf_ocr_transcript",
        "pdf_table",
        "pdf_cell",
        "pdf_relation",
        "pdf_provenance",
    ],
)
def test_pdf_dimensions_supported_without_fake_gold(kind):
    observation = {
        "kind": kind,
        "locator": {"page": 1},
        "fields": {
            "text": "literal",
            "row_span": 2,
            "column_span": 1,
            "bbox": [0, 0, 1, 1],
            "links": ["header", "value", "unit", "period"],
        },
    }
    assert predictions([observation]).predictions[0].observations[0].kind == kind


def test_duplicate_predictions_and_partial_failure_rejected():
    observation = {"kind": "pdf_text", "locator": {"page": 1}, "fields": {"text": "x"}}
    with pytest.raises(ValidationError):
        predictions([observation, observation])
    with pytest.raises(ValidationError):
        predictions([observation], status="failed", failure="timeout")
    assert predictions(status="failed", failure="timeout").predictions[0].status == "failed"


def test_orphan_reference_rejected():
    with pytest.raises(ValueError):
        evaluator.compare([source()], predictions(), {"orphan": reference()})


def test_prediction_schema_is_synchronized():
    root = Path(__file__).resolve().parents[2]
    schema = json.loads((root / "docs/eda/readiness_predictions_v1_schema.json").read_text())
    assert schema == evaluator.Predictions.model_json_schema()
