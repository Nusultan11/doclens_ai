"""Synthetic saved observations only; never run a parser or manufacture human review."""

from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_eval import score_record
from doclens_ai.extraction.fidelity_gold import fingerprint
from doclens_ai.extraction.models import (
    ExtractionStatus,
    SourceLocation,
    SpreadsheetCell,
    SpreadsheetSheet,
    TextBlock,
)
from tests.unit.test_extraction_fidelity import _gold, _record, _result
from tests.unit.test_historical_gold_eligibility import fixture_data, qualify
from tools.extraction_quality import historical_dev_baseline as tool
from tools.extraction_quality import historical_gold_eligibility as eligibility
from tools.extraction_quality.readiness_io import atomic


def inputs(*, resolved=True, fmt="pdf", text="alpha beta"):
    args, population = fixture_data(fmt, resolved=resolved)
    ledger = qualify((args, population))
    ledger["fingerprint"] = fingerprint(ledger)
    source = SourceLocation(page_number=1) if fmt == "pdf" else SourceLocation(block_index=0)
    capture = _result(fmt, blocks=(TextBlock(0, text, source),))
    return ledger, args[0], {"c1-0001": capture}


def test_existing_scorer_agreement_and_separate_evidence_tiers():
    ledger, records, captures = inputs()
    result = tool.score(ledger, records, captures)
    summary = tool.summarize(result)
    native = score_record(records[0], captures["c1-0001"])["metrics"]
    for metric in ("required_text_recall", "provenance", "reading_order"):
        assert summary["metrics"][metric]["passed"] == native[metric]["passed"]
        assert summary["metrics"][metric]["evaluated"] == native[metric]["evaluated"]
    assert summary["by_evidence_tier"][tool.HISTORICAL]["eligible_assertions"] == 2
    assert summary["by_evidence_tier"][tool.TECHNICAL]["eligible_assertions"] == 1
    assert summary["quality_gate"] == "NOT_EVALUATED" and not summary["independent_gold"]


def test_unresolved_labels_retained_but_not_scored_and_direct_use_rejected():
    ledger, records, captures = inputs(resolved=False)
    summary = tool.summarize(tool.score(ledger, records, captures))
    assert summary["assertions"] == 3 and summary["eligible_assertions"] == 1
    assert summary["metrics"]["required_text_recall"]["evaluated"] == 1
    assert summary["metrics"]["required_text_recall"]["review_required"] == 1
    assert summary["metrics"]["reading_order"]["score"] is None
    with pytest.raises(ValueError, match="ineligible"):
        tool.dimension(
            records[0], captures["c1-0001"], ledger["assertions"][1], "required_text_recall"
        )


def test_failed_capture_and_failed_checks_stay_in_denominators():
    ledger, records, captures = inputs()
    captures["c1-0001"] = replace(captures["c1-0001"], status=ExtractionStatus.FAILED, blocks=())
    summary = tool.summarize(tool.score(ledger, records, captures))
    assert summary["metrics"]["required_text_recall"]["passed"] == 0
    assert summary["metrics"]["required_text_recall"]["evaluated"] == 2
    assert summary["metrics"]["reading_order"]["evaluated"] == 1
    assert summary["saved_capture_statuses"]["failed"] == 1


def test_original_locators_occurrences_and_order_dependencies_are_preserved():
    ledger, records, captures = inputs(text="beta alpha")
    summary = tool.summarize(tool.score(ledger, records, captures))
    assert summary["metrics"]["required_text_recall"]["passed"] == 2
    assert summary["metrics"]["reading_order"]["passed"] == 0
    captures["c1-0001"] = _result(
        blocks=(TextBlock(0, "alpha beta", SourceLocation(page_number=2)),)
    )
    summary = tool.summarize(tool.score(ledger, records, captures))
    assert summary["metrics"]["required_text_recall"]["passed"] == 2
    assert summary["metrics"]["provenance"]["passed"] == 0
    assert summary["metrics"]["reading_order"]["passed"] == 0


def test_unsupported_metric_cannot_be_inflated_even_by_a_forged_admission():
    ledger, records, captures = inputs(fmt="docx")
    summary = tool.summarize(tool.score(ledger, records, captures))
    assert summary["metrics"]["provenance"]["evaluated"] == 1
    assert summary["metrics"]["provenance"]["unsupported"] == 1
    row = ledger["assertions"][1]
    row["metrics"]["provenance"].update(eligibility=eligibility.ELIGIBLE, supported=True)
    with pytest.raises(ValueError, match="unsupported"):
        tool.score(ledger, records, captures)


@pytest.mark.parametrize("change", ["sha", "size", "format", "missing", "extra"])
def test_capture_identity_and_population_rejection(change):
    ledger, records, captures = inputs()
    if change == "missing":
        captures.clear()
    elif change == "extra":
        captures["foreign"] = captures["c1-0001"]
    else:
        kwargs = {
            "sha": {"source_sha256": "0" * 64},
            "size": {"source_size_bytes": 101},
            "format": {"document_format": "docx"},
        }[change]
        captures["c1-0001"] = replace(captures["c1-0001"], **kwargs)
    with pytest.raises(ValueError):
        tool.score(ledger, records, captures)


@pytest.mark.parametrize("change", ["missing", "duplicate", "payload", "plan", "dependency"])
def test_denominator_and_assertion_drift_rejection(change):
    ledger, records, captures = inputs()
    if change == "missing":
        ledger["assertions"].pop()
    elif change == "duplicate":
        ledger["assertions"].append(copy.deepcopy(ledger["assertions"][0]))
    elif change == "payload":
        ledger["assertions"][0]["assertion_sha256"] = "0" * 64
    elif change == "plan":
        ledger["assertions"][0]["metrics"].pop("provenance")
    else:
        ledger["assertions"][2]["anchor_dependencies"].clear()
    with pytest.raises(ValueError):
        tool.score(ledger, records, captures)


def cell_case(value="10.0", formula=None, cache=None, *, check_display=False):
    gold = _gold("xlsx")
    gold["cells"] = [
        {
            "source": gold["anchors"][0]["source"],
            "value": "10",
            "formula": None,
            "cached_value": None,
            "check_display": check_display,
            "displayed_value": "10" if check_display else None,
        }
    ]
    record = _record(gold)
    assertion = record.cells[0]
    row = {
        "group": "cells",
        "assertion_id": "c1-0001/cells/0",
        "eligibility": eligibility.ELIGIBLE,
        "metrics": {
            name: {"eligibility": eligibility.ELIGIBLE, "supported": True}
            for name in eligibility.metric_plan(record, "cells", assertion)
        },
    }
    source = SourceLocation(sheet_index=0, cell_coordinate="A1")
    cell = SpreadsheetCell("A1", 0, 0, value, formula, cache, None, source)
    capture = _result(
        "xlsx", sheets=(SpreadsheetSheet(0, "synthetic", "visible", (cell,), (), ()),)
    )
    return record, capture, row


def test_cell_provenance_does_not_include_unrelated_anchor_and_no_numeric_rounding():
    record, capture, row = cell_case()
    assert tool.dimension(record, capture, row, "provenance")["passed"] == 1
    assert tool.dimension(record, capture, row, "provenance")["evaluated"] == 1
    assert tool.dimension(record, capture, row, "stored_values")["passed"] == 0
    assert tool.dimension(record, capture, row, "formulas")["passed"] == 1
    assert tool.dimension(record, capture, row, "cached_values")["passed"] == 1
    _, wrong_fields, _ = cell_case("10", "10", "0")
    assert tool.dimension(record, wrong_fields, row, "formulas")["passed"] == 0
    assert tool.dimension(record, wrong_fields, row, "cached_values")["passed"] == 0


def test_display_remains_unsupported_and_no_null_denominator_inflation():
    record, capture, row = cell_case(check_display=True)
    with pytest.raises(ValueError, match="unsupported"):
        tool.dimension(record, capture, row, "displayed_values")


def test_capture_file_sha_missing_and_confined_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    path = tmp_path / "saved.json"
    atomic(path, _result().to_dict())
    row = {"parser_agreement": {"capture": "saved.json", "capture_sha256": corpus.sha256(path)}}
    assert tool.load_capture(row).source_sha256 == "a" * 64
    path.write_text("{}")
    with pytest.raises(ValueError, match="SHA"):
        tool.load_capture(row)
    path.unlink()
    with pytest.raises(OSError):
        tool.load_capture(row)
    row["parser_agreement"]["capture"] = "../escape.json"
    with pytest.raises(ValueError):
        tool.load_capture(row)


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    result = tool.score(*inputs())
    result["binding"] = {"eligibility_root": "evaluation-output/eligibility"}
    result["fingerprint"] = fingerprint(result)
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "reconstruct", lambda _: copy.deepcopy(result))
    output = tmp_path / "evaluation-output/first"
    tool.build(output, tmp_path / "evaluation-output/eligibility")
    return output


def test_reproduce_every_file_and_reject_overwrite(frozen):
    other = frozen.with_name("second")
    tool.build(other, other.parent / "eligibility")
    assert {p.name: p.read_bytes() for p in frozen.iterdir()} == {
        p.name: p.read_bytes() for p in other.iterdir()
    }
    assert tool.verify(frozen)["status"] == "PASS"
    with pytest.raises(ValueError, match="fresh"):
        tool.build(frozen, other.parent / "eligibility")


@pytest.mark.parametrize(
    "change", ["denominator", "ineligible", "unsupported", "extra", "interrupted"]
)
def test_resealed_result_forgery_and_incomplete_outputs_rejected(frozen, change):
    if change == "extra":
        atomic(frozen / "predictions.json", {})
    elif change == "interrupted":
        (frozen / "COMPLETE.json").unlink()
    else:
        path = frozen / "scores.json"
        result = corpus.read_json(path)
        row = result["assertions"][0]
        if change == "denominator":
            row["metrics"]["required_text_recall"]["measurement"]["evaluated"] = 0
        elif change == "ineligible":
            row["eligibility"] = eligibility.REVIEW
        else:
            row["metrics"]["provenance"]["supported"] = False
        atomic(path, result)
        atomic(
            frozen / "COMPLETE.json",
            {n: corpus.sha256(frozen / n) for n in ("scores.json", "summary.json")},
        )
    with pytest.raises(ValueError):
        tool.verify(frozen)


def test_summary_has_no_text_paths_names_values_or_labels():
    summary = json.dumps(tool.summarize(tool.score(*inputs())))
    for secret in (
        "alpha",
        "beta",
        "synthetic",
        "capture_sha256",
        "source_reference",
        "reviewed_on",
    ):
        assert secret not in summary


def test_literal_sign_punctuation_and_case_not_normalized():
    gold = _gold()
    gold["anchors"][0]["text"] = "−10.00 %"
    record = _record(gold)
    row = {
        "group": "anchors",
        "assertion_id": "c1-0001/anchors/0",
        "eligibility": eligibility.ELIGIBLE,
        "metrics": {
            "required_text_recall": {"eligibility": eligibility.ELIGIBLE, "supported": True}
        },
    }
    for text, passed in (("−10.00   %", 1), ("10.00 %", 0), ("−10.0 %", 0), ("−10.00", 0)):
        capture = _result(blocks=(TextBlock(0, text, SourceLocation(page_number=1)),))
        assert tool.dimension(record, capture, row, "required_text_recall")["passed"] == passed


def test_reserved_labels_cannot_be_scored():
    ledger, records, captures = inputs()
    for row in ledger["assertions"]:
        row["eligibility"] = eligibility.EXCLUDED
        for metric in row["metrics"].values():
            metric["eligibility"] = eligibility.EXCLUDED
    result = tool.score(ledger, records, {})
    assert tool.summarize(result)["eligible_assertions"] == 0
    assert tool.summarize(result)["metrics"]["required_text_recall"]["score"] is None
    with pytest.raises(ValueError, match="ineligible"):
        tool.dimension(
            records[0], captures["c1-0001"], ledger["assertions"][0], "required_text_recall"
        )


def test_scorer_denominator_change_rejected(monkeypatch):
    original = tool.score_record

    def drift(record, capture):
        scored = original(record, capture)
        scored["metrics"]["required_text_recall"]["evaluated"] += 1
        return scored

    monkeypatch.setattr(tool, "score_record", drift)
    with pytest.raises(ValueError, match="denominator"):
        tool.score(*inputs())


def test_structural_checks_keep_missing_and_repeated_anchor_failures():
    ledger, records, captures = inputs(text="alpha")
    result = tool.summarize(tool.score(ledger, records, captures))
    assert result["metrics"]["reading_order"]["evaluated"] == 1
    assert result["metrics"]["reading_order"]["passed"] == 0
    gold = _gold()
    gold["anchors"][0]["occurrence"] = 2
    record = _record(gold)
    row = {
        "group": "anchors",
        "assertion_id": "c1-0001/anchors/0",
        "eligibility": eligibility.ELIGIBLE,
        "metrics": {"provenance": {"eligibility": eligibility.ELIGIBLE, "supported": True}},
    }
    assert tool.dimension(record, captures["c1-0001"], row, "provenance")["passed"] == 0


def test_summary_breakdowns_reconcile_every_metric():
    summary = tool.summarize(tool.score(*inputs()))
    for group in ("by_format", "by_group", "by_evidence_tier", "by_document"):
        for name, total in summary["metrics"].items():
            for count in (
                "passed",
                "evaluated",
                "requested",
                "review_required",
                "excluded",
                "unsupported",
            ):
                assert (
                    sum(s["metrics"][name][count] for s in summary[group].values()) == total[count]
                )


@pytest.mark.parametrize("reseal", [False, True])
def test_eligibility_change_between_verification_and_read_rejected(tmp_path, monkeypatch, reseal):
    ledger, _, _ = inputs()
    proof = {"ledger_fingerprint": ledger["fingerprint"]}
    monkeypatch.setattr(eligibility, "verify", lambda _: proof)
    ledger["assertions"][0]["eligibility"] = eligibility.EXCLUDED
    if reseal:
        ledger["fingerprint"] = fingerprint({k: v for k, v in ledger.items() if k != "fingerprint"})
    atomic(tmp_path / "eligibility.json", ledger)
    with pytest.raises(ValueError, match="eligibility changed"):
        tool.reconstruct(tmp_path)
