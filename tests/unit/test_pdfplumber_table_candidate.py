"""Public synthetic geometry/character regressions, independent of private Gold."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest

from doclens_ai.extraction import pdfplumber_table_candidate as c
from doclens_ai.extraction.parsers import extract_file
from tests.unit.test_pdf_table_candidate import LINES, VALUES, fixture, gold
from tools.pdf_table_candidate import benchmark as base
from tools.pdfplumber_table_candidate import benchmark as b


def test_simple_grid_geometry_numbers_scoring_and_native_preservation(tmp_path):
    path = fixture(tmp_path)
    raw = path.read_bytes()
    native = extract_file(path)
    evidence = c.extract_tables(path)
    assert evidence.status.value == "success" and len(evidence.grids) == 1
    grid = evidence.grids[0]
    assert grid.bounds == (50, 100, 350, 200)
    assert [cell.text for cell in grid.cells] == list(VALUES)
    assert all(
        len(cell.boundary_edge_indices) == 4 and all(cell.boundary_edge_indices)
        for cell in grid.cells
    )
    ids = [i for cell in grid.cells for i in cell.character_indices]
    assert len(ids) == len(set(ids))
    result = c.supplement(native, evidence)
    assert (
        result.blocks[: len(native.blocks)] == native.blocks and result.warnings == native.warnings
    )
    assert path.read_bytes() == raw and extract_file(path) == native
    score = base.score_record(gold(path), result)["metrics"]
    assert score["table_cells"]["passed"] == 4 and score["table_relationships"]["passed"] == 2
    assert score["provenance"]["passed"] == 4


@pytest.mark.parametrize("change", ["missing", "partial", "merged"])
def test_missing_boundaries_and_merges_are_not_filled(tmp_path, change):
    lines = (
        LINES.replace("200 100 m 200 200 l ", "")
        if change == "missing"
        else LINES.replace("200 200 l", "200 199 l" if change == "partial" else "200 150 l")
    )
    evidence = c.extract_tables(fixture(tmp_path, lines=lines))
    assert evidence.status.value == "needs_review" and not evidence.grids


@pytest.mark.parametrize(
    "text",
    [
        "BT /F1 10 Tf 1 0 0 1 199 170 Tm (Crossing) Tj ET",
        "BT /F1 10 Tf 0 1 -1 0 60 170 Tm (Rotated) Tj ET",
        "BT /F1 10 Tf 1 0 0 1 60 170 Tm (Repeat) Tj ET " * 2,
    ],
)
def test_ambiguous_rotated_overprinted_text_is_review(tmp_path, text):
    evidence = c.extract_tables(fixture(tmp_path, text=text))
    assert evidence.status.value == "needs_review" and not evidence.grids


def test_duplicate_text_in_distinct_cells_and_multipage_provenance(tmp_path):
    text = (
        "BT /F1 10 Tf 1 0 0 1 60 170 Tm (Same) Tj ET BT /F1 10 Tf 1 0 0 1 210 170 Tm (Same) Tj ET"
    )
    path = fixture(tmp_path, text=text, pages=2)
    e = c.extract_tables(path)
    assert len(e.grids) == 2 and [g.page for g in e.grids] == [1, 2]
    assert all([cell.text for cell in g.cells] == ["Same", "Same", "", ""] for g in e.grids)
    after = c.supplement(extract_file(path), e)
    assert [block.source.block_index for block in after.blocks[2:]] == [2, 3]
    assert after.blocks[-1].rows[0].cells[1].source.page_number == 2
    assert not c.extract_tables(fixture(tmp_path, rotate=90)).grids


def test_numeric_units_signs_and_leading_zeros_are_literal(tmp_path):
    text = (
        "BT /F1 10 Tf 1 0 0 1 60 170 Tm (-0001.50 kg) Tj ET "
        "BT /F1 10 Tf 1 0 0 1 210 170 Tm (+0027 mm) Tj ET"
    )
    evidence = c.extract_tables(fixture(tmp_path, text=text))
    assert [cell.text for cell in evidence.grids[0].cells] == ["-0001.50 kg", "+0027 mm", "", ""]


def test_text_reordering_is_rejected_even_when_character_counts_match(tmp_path, monkeypatch):
    path = fixture(tmp_path)
    import pdfplumber.utils

    original = pdfplumber.utils.extract_text
    monkeypatch.setattr(
        pdfplumber.utils, "extract_text", lambda chars, **kwargs: original(chars, **kwargs)[::-1]
    )
    evidence = c.extract_tables(path)
    assert not evidence.grids and evidence.pages[0].issues == ("character_preservation_failed",)


def test_geometric_spaces_cannot_silently_split_one_numeric_literal(tmp_path):
    text = "BT /F1 10 Tf 10 Tc 1 0 0 1 60 170 Tm (0012) Tj ET"
    evidence = c.extract_tables(fixture(tmp_path, text=text))
    assert not evidence.grids
    assert evidence.pages[0].issues == ("numeric_token_ambiguity",)


@pytest.mark.parametrize("box", [(0, 0, float("nan"), 1), (0, 0, 0, 1), (0, 0, 1, float("inf"))])
def test_nonfinite_or_missing_geometry_cannot_be_normalized(box):
    with pytest.raises(c._Review):
        c._box(box)


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_file_bytes", 1),
        ("max_pages", 1),
        ("max_characters", 1),
        ("max_edges", 1),
        ("max_cells", 1),
        ("max_tables", 1),
    ],
)
def test_limits_discard_partial_candidate(tmp_path, field, value):
    e = c.extract_tables(fixture(tmp_path, pages=2), limits=replace(c.Limits(), **{field: value}))
    assert e.status.value == "failed" and not e.grids and not e.pages


@pytest.mark.parametrize("value", [0, -1, True, 1.5, float("inf"), float("nan")])
def test_invalid_resource_configuration(value):
    with pytest.raises(ValueError):
        c.Limits(max_cells=value)


def test_corrupt_timeout_and_identity_fail_closed(tmp_path, monkeypatch):
    path = fixture(tmp_path)
    ticks = iter([0, 20])
    with monkeypatch.context() as m:
        m.setattr(c.time, "monotonic", lambda: next(ticks))
        assert c.extract_tables(path).issues == ("timeout",)
    native = extract_file(path)
    e = c.extract_tables(path)
    with pytest.raises(ValueError):
        c.supplement(native, replace(e, source_sha256="0" * 64))
    assert (
        c.supplement(replace(native, status=c.ExtractionStatus.NEEDS_REVIEW), e).status.value
        == "needs_review"
    )
    path.write_bytes(b"PRIVATE broken PDF")
    result = c.extract_tables(path)
    assert result.status.value == "failed" and "PRIVATE" not in json.dumps(result.to_dict())


def test_geometry_without_source_boundaries_is_rejected():
    page = SimpleNamespace(bbox=(0, 0, 400, 300), page_number=1)
    table = SimpleNamespace(
        bbox=(50, 100, 350, 200),
        cells=[
            (50, 100, 200, 150),
            (200, 100, 350, 150),
            (50, 150, 200, 200),
            (200, 150, 350, 200),
        ],
    )
    with pytest.raises(c._Review, match="unverified_boundary"):
        c._grid(page, table, 0, [], [], c.Limits(), lambda: None)


@pytest.mark.parametrize("mode", ["timeout", "memory_limit", "worker_failed"])
def test_isolated_worker_resource_failure_and_cleanup(tmp_path, mode):
    guards = {
        **base.GUARDS,
        "timeout_seconds": 0.05 if mode == "timeout" else 5,
        "max_process_bytes": 1 if mode == "memory_limit" else base.GUARDS["max_process_bytes"],
    }
    command = [
        sys.executable,
        "-B",
        "-c",
        "raise SystemExit(3)" if mode == "worker_failed" else "import time; time.sleep(10)",
    ]
    r = base.monitor(command, tmp_path, guards=guards)
    assert r["failure"] == mode and r["cleanup"] and not (tmp_path / "result.json").exists()


def test_real_worker_and_full_missing_denominators(tmp_path, capsys):
    path = fixture(tmp_path)
    assert b.worker(path, tmp_path) == 0
    assert capsys.readouterr().out == ""
    raw = json.loads((tmp_path / "result.json").read_text())
    summary = base.summarize(gold(path), raw)
    assert summary["native_preserved"] and base.decision([summary]) == "PROMOTE"
    missing = base.summarize(gold(path), None)
    assert base.totals([missing], "candidate")["table_cells"] == {
        "passed": 0,
        "evaluated": 0,
        "label_total": 4,
        "unknown_documents": 1,
    }
    assert "Header A" not in json.dumps(summary)
