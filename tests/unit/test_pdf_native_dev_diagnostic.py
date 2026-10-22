"""Synthetic literal/topology observations only, with no private PDF labels."""

from __future__ import annotations

from dataclasses import replace

import pytest

from doclens_ai.extraction.models import (
    DocumentFormat,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TextBlock,
)
from tools.extraction_quality import pdf_native_dev_diagnostic as tool


def block(text, page=1, index=0):
    return TextBlock(index, text, SourceLocation(page_number=page, block_index=index))


@pytest.mark.parametrize(
    "literal,text,multiplicity,state,cause",
    [
        ("Public value", "Public value", 1, "PAGE_EXACT_UNIQUE", None),
        ("Public value", "Public value", 2, "PAGE_EXACT_AMBIGUOUS", "ambiguous_match"),
        (
            "Public value",
            "Public value; Public value",
            1,
            "PAGE_EXACT_AMBIGUOUS",
            "ambiguous_match",
        ),
        ("12", "3124", 1, "SUBSTRING_ONLY_AMBIGUOUS", "ambiguous_match"),
        ("12", "-12", 1, "SUBSTRING_ONLY_AMBIGUOUS", "ambiguous_match"),
        ("12", "12.0", 1, "SUBSTRING_ONLY_AMBIGUOUS", "ambiguous_match"),
        ("Rate 01.20", "Rate\n01.20", 1, "WHITESPACE_FRAGMENTATION", "fragmentation"),
        ("-01.20", "01.20", 1, "MISSING_TEXT", "omission"),
        ("ab", "b a", 1, "MISSING_TEXT", "unknown_cause"),
        ("", "anything", 9, "EMPTY_CELL_NOT_TEXT_SCORABLE", "empty_cell_case"),
    ],
)
def test_literals_never_become_cell_fidelity(literal, text, multiplicity, state, cause):
    actual = tool.literal_observation(literal, [block(text)], multiplicity)
    assert actual["literal_state"] == state
    assert actual["literal_cause"] == cause
    assert not actual["verified_cell_binding"]
    assert (actual["unique_page_match"] is not None) == (state == "PAGE_EXACT_UNIQUE")


def test_repeated_symbols_and_separate_blocks_do_not_create_bindings():
    symbols = tool.literal_observation("£", [block("£0"), block("£0", index=1)], 2, symbol=True)
    assert symbols["exact_occurrences"] == 2
    assert symbols["literal_state"] == "PAGE_EXACT_AMBIGUOUS"
    assert symbols["unique_page_match"] is None
    across = tool.literal_observation("AlphaBeta", [block("Alpha"), block("Beta", index=1)], 1)
    assert across["exact_occurrences"] == across["whitespace_equivalent_occurrences"] == 0


def fixture():
    doc = dict(
        document_id="public-1",
        source_sha256="1" * 64,
        source_size_bytes=100,
        pages=[dict(page_number=1)],
        cells=[dict(item_id="cell-a", literal_text="£1"), dict(item_id="cell-b", literal_text="")],
        text_anchors=[dict(item_id="anchor-a", literal_text="Public value")],
        printed_symbols=[dict(item_id="unit-a", printed_symbol="£")],
        logical_grids=[dict(table_id="public-grid")],
    )
    result = ExtractionResult(
        "1.1",
        DocumentFormat.PDF,
        ExtractionStatus.NEEDS_REVIEW,
        "1" * 64,
        100,
        (block("Public value £1"),),
    )
    return doc, result


def test_complete_population_and_only_genuine_native_page_locators():
    doc, result = fixture()
    actual = tool.assess_document(doc, result, None, {"public-grid": "grid-item-a"})
    assert actual["status"] == "needs_review"
    assert actual["native_cells"] == actual["native_tables"] == 0
    assert len(actual["findings"]) == 5
    assert {r["item_id"] for r in actual["findings"]} == {
        "cell-a",
        "cell-b",
        "anchor-a",
        "unit-a",
        "grid-item-a",
    }
    assert actual["native_locators"] == [tool.asdict(result.blocks[0].source)]
    assert not actual["native_bbox_support"]
    assert all(not r["verified_cell_binding"] for r in actual["findings"])
    assert actual["summary"]["cell"]["total"] == 2
    assert actual["summary"]["cell"]["literal_states"]["EMPTY_CELL_NOT_TEXT_SCORABLE"] == 1
    assert actual["verified_cell_fidelity"] == "NOT_EVALUATED"


@pytest.mark.parametrize("failure", [None, "timeout", "memory_limit", "worker_failed"])
def test_failed_capture_retains_all_denominators(failure):
    doc, _ = fixture()
    actual = tool.assess_document(doc, None, failure, {"public-grid": "grid-item-a"})
    assert len(actual["findings"]) == 5
    assert not any(r["page_locator_available"] for r in actual["findings"])
    assert actual["summary"]["cell"]["total"] == 2
    assert actual["summary"]["logical_grid"]["topology_support"] == {"CAPTURE_UNAVAILABLE": 1}


def test_wrong_page_and_source_cannot_supply_a_match():
    doc, result = fixture()
    actual = tool.assess_document(
        doc,
        replace(result, blocks=(block("Public value £1", page=2),)),
        None,
        {"public-grid": "grid-item-a"},
    )
    assert actual["summary"]["text_anchor"]["literal_states"] == {"NO_PAGE_OUTPUT": 1}
    with pytest.raises(ValueError, match="source binding"):
        tool.assess_document(
            doc, replace(result, source_sha256="2" * 64), None, {"public-grid": "grid-item-a"}
        )


def test_reference_grid_requires_original_item_identity():
    doc, result = fixture()
    with pytest.raises(KeyError):
        tool.assess_document(doc, result, None, {})


def test_config_rejects_unknown_keys_and_cli_sanitizes(monkeypatch, tmp_path, capsys):
    path = tmp_path / "config.json"
    path.write_text('{"execute": "private payload"}', encoding="utf-8")
    with pytest.raises(ValueError):
        tool.validation_args(path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "diagnostic",
            "--snapshot",
            "private.pdf",
            "--validation-config",
            str(path),
            "--output",
            "private",
        ],
    )
    assert tool.main() == 2
    output = capsys.readouterr().out
    assert "BLOCKED:" in output and "payload" not in output and "private.pdf" not in output
