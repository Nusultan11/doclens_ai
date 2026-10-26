"""Public synthetic qualification cases; no human attestations or model execution."""

from __future__ import annotations

import copy
import json

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_gold import GoldError, fingerprint, load_gold
from tests.unit.test_extraction_fidelity import _gold, _record
from tools.extraction_quality import historical_gold_eligibility as tool
from tools.extraction_quality.readiness_io import atomic


def fixture_data(fmt="pdf", *, resolved=True):
    value = _gold(fmt)
    second = copy.deepcopy(value["anchors"][0])
    second.update(anchor_id="a2", text="beta")
    if fmt == "docx":
        second["source"] = {"region": "footnote", "part_index": 0}
    value["anchors"].append(second)
    value["order_pairs"] = [{"before": "a1", "after": "a2"}]
    record = _record(value)
    source = {
        "id": "c1-0001",
        "sha256": "a" * 64,
        "format": fmt,
        "family": "f-safe",
        "split": "dev",
        "reserved_qa_family": False,
        "independent_gold": False,
        "rights": {"local_evaluation": True, "new_annotation": None},
        "source_reference": {
            "path": f"originals/c1-0001.{fmt}",
            "sha256": "a" * 64,
            "size_bytes": 100,
            "format": fmt,
        },
    }
    reserved = copy.deepcopy(source)
    reserved.update(id="reserved", sha256="b" * 64, family="f-test", reserved_qa_family=True)
    reserved["source_reference"] = {
        "path": f"originals/reserved.{fmt}",
        "sha256": "b" * 64,
        "size_bytes": 100,
        "format": fmt,
    }
    historical = {"records": 1, "assertions": []}
    for key, (r, group, assertion) in tool.assertions((record,)).items():
        historical["assertions"].append(
            {
                "assertion_id": key,
                "source_id": r.document_id,
                "source_sha256": r.source_sha256,
                "group": group,
                "assertion": assertion.model_dump(mode="json"),
                "classification": "LOSS_OR_SOURCE_AMBIGUITY"
                if key.endswith("anchors/1")
                else "OBSERVATION_MATCH",
                "needs_review": key.endswith("anchors/1"),
                "reviewer": None,
                "metrics": {"provenance": {"passed": 0, "evaluated": 1, "unsupported": 0}},
                "capture": "synthetic/capture.json",
                "capture_sha256": "c" * 64,
            }
        )
    old = historical["assertions"][1]
    technical = {
        "input_assertions": 1,
        "items": [
            {
                "assertion_id": old["assertion_id"],
                "source_id": source["id"],
                "source_sha256": source["sha256"],
                "source_reference": source["source_reference"],
                "group": old["group"],
                "assertion": old["assertion"],
                "original_verified": True,
                "human_reviewed": False,
                "independent_gold": False,
                "reviewer": None,
                "tier": "SOURCE_NATIVE_DIAGNOSTIC",
                "method": "readiness-source-checks-1.0",
                "technical_source_resolved": resolved,
                "source_state": "SOURCE_LITERAL_AND_REGION_SUPPORTED"
                if resolved
                else "SOURCE_AMBIGUOUS",
                "source_evidence": {"synthetic_source_locator": True},
                "annotation_rights": None,
                "confidence_limitations": ["not_independent_review"],
                "correction": None,
            }
        ],
    }
    return ((record,), [source, reserved], historical, technical, {"b" * 64}), tool.Population(
        1, 3, 1, int(resolved)
    )


def qualify(data):
    args, expected = data
    return tool.qualify(*args, expected=expected, allow_synthetic=True)


def test_complete_separate_evidence_fields_and_no_promotion():
    result = qualify(fixture_data())
    summary = tool.summarize(result)
    assert summary[tool.ELIGIBLE] == 3 and summary["assertions"] == 3
    assert summary["technical_resolved"] == 1 and summary["not_source_reinspected"] == 2
    technically_supported = result["assertions"][1]
    assert technically_supported["parser_agreement"]["previous_issue"]
    assert technically_supported["historical_review"]["tier"] == "HISTORICAL_ATTESTATION"
    assert technically_supported["technical_support"]["technically_resolved"] is True
    assert technically_supported["independent_review"]["independent_gold"] is False
    assert summary["QG-00"] == summary["QG-01"] == "NOT_EVALUATED"
    assert summary["quality_scores"] is None and summary["new_human_reviews"] == 0


def test_agreement_is_informational_not_eligibility():
    data = fixture_data()
    first = qualify(data)
    for row in data[0][2]["assertions"]:
        row["classification"] = "DIFFERENT_SAVED_PARSER_OUTCOME"
        row["metrics"]["provenance"]["passed"] = 1
    second = qualify(data)
    assert [(r["eligibility"], r["reason_codes"]) for r in first["assertions"]] == [
        (r["eligibility"], r["reason_codes"]) for r in second["assertions"]
    ]


def test_metadata_input_order_does_not_change_qualification():
    data = fixture_data()
    before = qualify(data)
    data[0][1].reverse()
    data[0][2]["assertions"].reverse()
    data[0][3]["items"].reverse()
    assert qualify(data) == before


def test_known_unresolved_evidence_and_dependencies_stay_in_denominators():
    result = qualify(fixture_data(resolved=False))
    summary = tool.summarize(result)
    assert summary[tool.ELIGIBLE] == 1 and summary[tool.REVIEW] == 2
    assert summary["technical_unresolved"] == 1 and summary["assertions"] == 3
    assert "ANCHOR_DEPENDENCY_SOURCE_UNRESOLVED" in result["assertions"][2]["reason_codes"]


@pytest.mark.parametrize(
    "permission,code", [(False, "LOCAL_EVALUATION_DENIED"), (None, "LOCAL_EVALUATION_UNRESOLVED")]
)
def test_rights_fail_closed_without_hidden_exclusions(permission, code):
    data = fixture_data()
    data[0][1][0]["rights"]["local_evaluation"] = permission
    result = qualify(data)
    assert tool.summarize(result)[tool.EXCLUDED] == 3
    assert all(code in row["reason_codes"] for row in result["assertions"])


@pytest.mark.parametrize(
    "link",
    [
        "family",
        "related_families",
        "near_duplicate_group",
        "normalized_text_sha256",
        "sha256",
        "split",
    ],
)
def test_reserved_and_test_connected_family_leakage(link):
    data = fixture_data()
    safe, reserved = data[0][1]
    if link == "family":
        safe["family"] = reserved["family"]
    elif link == "related_families":
        safe[link] = [reserved["family"]]
    elif link == "sha256":
        reserved["sha256"] = reserved["source_reference"]["sha256"] = safe["sha256"]
        data[0][4].clear()
        data[0][4].add(safe["sha256"])
    elif link == "split":
        safe["split"] = "sealed_candidate"
    else:
        safe[link] = reserved[link] = "d" * 64
    result = qualify(data)
    assert tool.summarize(result)[tool.EXCLUDED] == 3


@pytest.mark.parametrize("target", ["historical", "technical", "population", "gold"])
def test_duplicates_rejected(target):
    args, counts = fixture_data()
    records, population, historical, technical, reserved = args
    if target == "historical":
        historical["assertions"].append(copy.deepcopy(historical["assertions"][0]))
    elif target == "technical":
        technical["items"].append(copy.deepcopy(technical["items"][0]))
    elif target == "population":
        population.append(copy.deepcopy(population[0]))
    else:
        records *= 2
    with pytest.raises(ValueError):
        tool.qualify(
            records,
            population,
            historical,
            technical,
            reserved,
            expected=counts,
            allow_synthetic=True,
        )


@pytest.mark.parametrize(
    "target", ["historical", "technical", "payload", "sha", "denominator", "reserved"]
)
def test_missing_or_changed_bindings_rejected(target):
    args, expected = fixture_data()
    if target == "historical":
        args[2]["assertions"].pop()
    elif target == "technical":
        args[3]["items"].clear()
    elif target == "payload":
        args[2]["assertions"][0]["assertion"]["text"] = "forged"
    elif target == "sha":
        args[1][0]["sha256"] = "0" * 64
    elif target == "reserved":
        args[4].clear()
    else:
        expected = tool.Population(1, 4, 1, 1)
    with pytest.raises(ValueError):
        tool.qualify(*args, expected=expected, allow_synthetic=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("human_reviewed", True),
        ("independent_gold", True),
        ("reviewer", "fabricated"),
        ("source_evidence", {}),
        ("original_verified", False),
    ],
)
def test_fabricated_review_and_absent_evidence_rejected(field, value):
    data = fixture_data()
    data[0][3]["items"][0][field] = value
    with pytest.raises(ValueError):
        qualify(data)


def test_fabricated_population_review_rejected():
    data = fixture_data()
    data[0][1][0]["independent_gold"] = True
    with pytest.raises(ValueError):
        qualify(data)


def test_partial_metric_support_ancillary_and_display():
    result = qualify(fixture_data("docx"))
    anchor = result["assertions"][1]
    assert anchor["eligibility"] == tool.ELIGIBLE
    assert anchor["metrics"]["required_text_recall"]["eligibility"] == tool.ELIGIBLE
    assert anchor["metrics"]["provenance"]["supported"] is False
    assert anchor["metrics"]["provenance"]["eligibility"] == tool.EXCLUDED
    assert result["assertions"][2]["eligibility"] == tool.EXCLUDED
    value = _gold("xlsx")
    value["cells"] = [
        {
            "source": value["anchors"][0]["source"],
            "value": None,
            "formula": None,
            "cached_value": None,
            "check_display": True,
            "displayed_value": "synthetic display",
        }
    ]
    record = _record(value)
    plan = tool.metric_plan(record, "cells", record.cells[0])
    assert plan["displayed_values"] == ["DISPLAY_VALUES_UNSUPPORTED_BY_FROZEN_SCORER"]
    assert plan["stored_values"] == []


def test_pdf_grid_metric_is_supported_even_when_native_parser_does_not_emit_it():
    value = _gold()
    value["anchors"][0]["source"].update(block_index=0, table_index=0, row_index=0, column_index=0)
    value["table_cells"] = [{"anchor_id": "a1", "row_span": 1, "column_span": 2}]
    record = _record(value)
    assert tool.metric_plan(record, "table_cells", record.table_cells[0]) == {"table_cells": []}


def test_technical_literal_does_not_confirm_logical_grid_mapping():
    args, expected = fixture_data()
    value = args[0][0].model_dump(mode="json")
    for index, anchor in enumerate(value["anchors"]):
        anchor["source"].update(block_index=0, table_index=0, row_index=0, column_index=index)
    record = _record(value)
    mapping = tool.assertions((record,))
    for old in args[2]["assertions"]:
        old["assertion"] = mapping[old["assertion_id"]][2].model_dump(mode="json")
    args[3]["items"][0]["assertion"] = mapping[args[3]["items"][0]["assertion_id"]][2].model_dump(
        mode="json"
    )
    result = tool.qualify((record,), *args[1:], expected=expected, allow_synthetic=True)
    literal = result["assertions"][1]
    assert literal["eligibility"] == tool.ELIGIBLE
    assert literal["metrics"]["required_text_recall"]["eligibility"] == tool.ELIGIBLE
    assert literal["metrics"]["provenance"]["eligibility"] == tool.REVIEW
    assert literal["metrics"]["provenance"]["supported"] is True


def test_strict_gold_rejects_fabricated_review_without_leaking(tmp_path):
    value = _gold()
    value["independent_human_reviewer"] = "PRIVATE_SENTINEL"
    path = tmp_path / "gold.jsonl"
    path.write_text(json.dumps(value))
    with pytest.raises(GoldError) as error:
        load_gold(path, {"c1-0001": ("a" * 64, 100, "pdf")}, allow_synthetic=True)
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_source_drift_rejected_by_existing_raw_validator(tmp_path):
    from pypdf import PdfWriter

    path = tmp_path / "raw/source.pdf"
    path.parent.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    writer.write(path)
    sources = {"c1-0001": (corpus.sha256(path), path.stat().st_size, "pdf")}
    assert tool.verify_corpus(path.parent, sources, tool.ExtractionLimits())
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError):
        tool.verify_corpus(path.parent, sources, tool.ExtractionLimits())


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    ledger = qualify(fixture_data())
    ledger["binding"] = {"release_root": "evaluation-output/release"}
    ledger["fingerprint"] = fingerprint(ledger)
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "reconstruct", lambda _: copy.deepcopy(ledger))
    release_root = tmp_path / "evaluation-output/release"
    output = tmp_path / "evaluation-output/first"
    tool.build(output, release_root)
    return output, release_root


def test_deterministic_build_and_verification(frozen):
    output, release_root = frozen
    other = output.with_name("second")
    tool.build(other, release_root)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == {
        p.name: p.read_bytes() for p in other.iterdir()
    }
    assert tool.verify(output)["status"] == "PASS"
    with pytest.raises(ValueError):
        tool.build(output, release_root)


def test_resealed_forged_ledger_is_rejected(frozen):
    output, _ = frozen
    path = output / "eligibility.json"
    ledger = corpus.read_json(path)
    ledger["assertions"][0]["independent_review"]["independent_gold"] = True
    atomic(path, ledger)
    atomic(
        output / "COMPLETE.json",
        {name: corpus.sha256(output / name) for name in ("eligibility.json", "summary.json")},
    )
    with pytest.raises(ValueError, match="reconstruction"):
        tool.verify(output)


def test_extra_payload_is_rejected(frozen):
    output, _ = frozen
    atomic(output / "predictions.json", {"unexpected": True})
    with pytest.raises(ValueError, match="inventory"):
        tool.verify(output)


def test_summary_contains_no_private_payloads():
    summary = tool.summarize(qualify(fixture_data()))
    text = json.dumps(summary)
    for private in ("alpha", "beta", "originals/", "synthetic/capture", "reviewed_on"):
        assert private not in text
    assert (
        sum(summary[state] for state in (tool.ELIGIBLE, tool.REVIEW, tool.EXCLUDED))
        == summary["assertions"]
    )
