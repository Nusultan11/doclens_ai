"""Independent public synthetic grids, never private sources or Gold."""

from __future__ import annotations

import json
import sys
from dataclasses import replace

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from doclens_ai.extraction import pdf_table_candidate as c
from doclens_ai.extraction.fidelity_eval import score_record
from doclens_ai.extraction.fidelity_gold import FidelityRecord
from doclens_ai.extraction.parsers import extract_file
from tools.pdf_table_candidate import benchmark as b

LINES = (
    "50 100 m 350 100 l 50 150 m 350 150 l 50 200 m 350 200 l "
    "50 100 m 50 200 l 200 100 m 200 200 l 350 100 m 350 200 l S\n"
)
VALUES = ("Header A", "Header B", "-001.50", "+27.00")


def fixture(tmp_path, *, lines=LINES, extra="", text=None, font_change=None, rotate=0, pages=1):
    writer = PdfWriter()
    descriptor = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/FontDescriptor"),
            NameObject("/FontName"): NameObject("/Courier"),
            NameObject("/Flags"): NumberObject(33),
            NameObject("/FontBBox"): ArrayObject([NumberObject(v) for v in (-23, -250, 715, 805)]),
            NameObject("/Ascent"): NumberObject(805),
            NameObject("/Descent"): NumberObject(-250),
            NameObject("/ItalicAngle"): NumberObject(0),
            NameObject("/CapHeight"): NumberObject(600),
            NameObject("/StemV"): NumberObject(80),
        }
    )
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Courier"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            NameObject("/FirstChar"): NumberObject(32),
            NameObject("/LastChar"): NumberObject(126),
            NameObject("/Widths"): ArrayObject([NumberObject(600) for _ in range(95)]),
            NameObject("/FontDescriptor"): writer._add_object(descriptor),
        }
    )
    for key, value in (font_change or {}).items():
        if value is None:
            font.pop(NameObject(key), None)
        else:
            font[NameObject(key)] = value
    font_ref = writer._add_object(font)
    if text is None:
        text = "".join(
            f"BT /F1 10 Tf 1 0 0 1 {x} {y} Tm ({value}) Tj ET\n"
            for (x, y), value in zip(
                ((60, 170), (210, 170), (60, 120), (210, 120)), VALUES, strict=True
            )
        )
    for _ in range(pages):
        page = writer.add_blank_page(width=400, height=300)
        page[NameObject("/Resources")] = writer._add_object(
            DictionaryObject(
                {
                    NameObject("/Font"): writer._add_object(
                        DictionaryObject({NameObject("/F1"): font_ref})
                    )
                }
            )
        )
        stream = DecodedStreamObject()
        stream.set_data((lines + text + extra).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
        if rotate:
            page.rotate(rotate)
    path = tmp_path / "synthetic-grid.pdf"
    with path.open("wb") as f:
        writer.write(f)
    return path


def gold(path):
    base = extract_file(path)
    return FidelityRecord.model_validate_json(
        json.dumps(
            {
                "schema_version": "1.0",
                "dataset_revision": "corpus-v1-fidelity-v1",
                "dataset_kind": "synthetic",
                "review_basis": "synthetic_fixture",
                "document_id": "c1-0001",
                "source_sha256": base.source_sha256,
                "source_size_bytes": base.source_size_bytes,
                "document_format": "pdf",
                "review_status": "reviewed",
                "reviewer_count": 1,
                "reviewed_on": "2026-01-01",
                "anchors": [
                    {
                        "anchor_id": f"a{i + 1}",
                        "text": v,
                        "source": {
                            "region": "body",
                            "page_number": 1,
                            "block_index": 1,
                            "table_index": 0,
                            "row_index": i // 2,
                            "column_index": i % 2,
                        },
                    }
                    for i, v in enumerate(VALUES)
                ],
                "table_cells": [{"anchor_id": f"a{i + 1}"} for i in range(4)],
                "table_relationships": [
                    {"left": "a1", "right": "a2", "relationship": "same_row"},
                    {"left": "a1", "right": "a3", "relationship": "same_column"},
                ],
                "order_pairs": [{"before": "a1", "after": "a2"}, {"before": "a2", "after": "a3"}],
                "cells": [],
            }
        )
    )


def test_complete_grid_numeric_literals_and_existing_scorer(tmp_path):
    path = fixture(tmp_path)
    original = path.read_bytes()
    before = extract_file(path)
    evidence = c.extract_tables(path)
    assert evidence.status.value == "success" and len(evidence.grids) == 1
    grid = evidence.grids[0]
    assert grid.x_lines == (50, 200, 350) and grid.y_lines == (200, 150, 100)
    assert tuple(cell.text for cell in grid.cells) == VALUES
    assert grid.cells[0].bounds == (50, 150, 200, 200)
    after = c.supplement(before, evidence)
    assert after.blocks[: len(before.blocks)] == before.blocks and before == extract_file(path)
    assert path.read_bytes() == original and after.warnings == before.warnings
    record = gold(path)
    assert score_record(record, before)["metrics"]["table_cells"]["passed"] == 0
    scores = score_record(record, after)["metrics"]
    assert scores["table_cells"]["passed"] == 4 and scores["table_relationships"]["passed"] == 2
    assert scores["provenance"]["passed"] == 4 and scores["reading_order"]["passed"] == 2
    assert b.restore(after.to_dict()) == after


def test_independent_pdfium_text_and_rendered_fixture(tmp_path):
    pdfium = pytest.importorskip("pypdfium2")
    doc = pdfium.PdfDocument(str(fixture(tmp_path)))
    try:
        page = doc[0]
        try:
            text = page.get_textpage()
            try:
                assert all(value in text.get_text_range() for value in VALUES)
            finally:
                text.close()
            bitmap = page.render(scale=1)
            try:
                assert bitmap.width == 400 and bitmap.height == 300
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        doc.close()


def test_rectangle_translated_grid_and_drawing_after_text(tmp_path):
    rectangles = "50 100 300 100 re 200 100 m 200 200 l 50 150 m 350 150 l S\n"
    path = fixture(tmp_path, lines="q 1 0 0 1 10 20 cm\n" + rectangles, extra=LINES + "Q")
    evidence = c.extract_tables(path)
    assert evidence.status.value == "success"
    assert evidence.grids[0].x_lines == (60, 210, 360)
    assert evidence.grids[0].y_lines == (220, 170, 120)
    assert tuple(cell.text for cell in evidence.grids[0].cells) == VALUES


@pytest.mark.parametrize(
    "extra",
    ["0 0 400 300 re f", "0 0 400 300 re W n", "100 w " + LINES],
)
def test_fill_clipping_or_thick_stroke_cannot_claim_unambiguous_cells(tmp_path, extra):
    evidence = c.extract_tables(fixture(tmp_path, extra=extra))
    assert evidence.status.value == "needs_review" and not evidence.grids


def test_composed_geometry_overflow_is_not_emitted(tmp_path):
    evidence = c.extract_tables(
        fixture(tmp_path, lines="10000000 0 0 10000000 0 0 cm\n" * 3 + LINES)
    )
    assert evidence.status.value == "needs_review" and not evidence.grids
    assert evidence.pages[0].issues == ("invalid_geometry",)


@pytest.mark.parametrize("variant", ["missing", "partial", "merged", "diagonal"])
def test_incomplete_or_nonrectangular_lines_never_completed(tmp_path, variant):
    lines = LINES
    if variant == "missing":
        lines = lines.replace("200 100 m 200 200 l ", "")
    elif variant == "partial":
        lines = lines.replace("200 200 l", "200 199 l")
    elif variant == "merged":
        lines = lines.replace("200 100 m 200 200 l", "200 100 m 200 150 l")
    else:
        lines += "50 100 m 350 200 l S\n"
    e = c.extract_tables(fixture(tmp_path, lines=lines))
    assert e.status.value == "needs_review" and not e.grids


@pytest.mark.parametrize(
    "text",
    [
        "BT /F1 10 Tf (Unlocated) Tj ET",
        "BT /F1 10 Tf 1 0 0 1 199 170 Tm (Crossing) Tj ET",
        "BT /F1 10 Tf 0 1 -1 0 60 170 Tm (Rotated) Tj ET",
        "BT /F1 10 Tf 1 0 0 1 60 170 Tm (A) Tj (B) Tj ET",
        "BT /F1 10 Tf 1 0 0 1 60 170 Tm (A) Tj ET BT /F1 10 Tf 1 0 0 1 60 170 Tm (A) Tj ET",
        "BT /F1 10 Tf 3 Tr 1 0 0 1 60 170 Tm (Hidden) Tj ET",
    ],
)
def test_ambiguous_rotated_duplicate_or_missing_text_locators(tmp_path, text):
    e = c.extract_tables(fixture(tmp_path, text=text))
    assert e.status.value == "needs_review" and not e.grids


@pytest.mark.parametrize(
    "change",
    [
        {"/Widths": None},
        {"/FontDescriptor": None},
        {"/Encoding": None},
        {"/Encoding": NameObject("/Custom")},
        {"/Subtype": NameObject("/Type0")},
        {"/ToUnicode": DictionaryObject()},
    ],
)
def test_unverifiable_font_mapping_or_metrics_are_unknown(tmp_path, change):
    e = c.extract_tables(fixture(tmp_path, font_change=change))
    assert e.status.value == "needs_review" and not e.grids


def test_page_provenance_rotation_and_all_native_blocks_are_preserved(tmp_path):
    path = fixture(tmp_path, pages=2)
    e = c.extract_tables(path)
    assert [g.page for g in e.grids] == [1, 2]
    native = extract_file(path)
    after = c.supplement(native, e)
    assert after.blocks[:2] == native.blocks
    assert [block.source.block_index for block in after.blocks[2:]] == [2, 3]
    assert all(
        cell.source.block_index == block.order
        for block in after.blocks[2:]
        for row in block.rows
        for cell in row.cells
    )
    assert after.blocks[-1].rows[1].cells[1].source.page_number == 2
    assert all(
        cell.row_span == cell.column_span == 1
        for block in after.blocks[2:]
        for row in block.rows
        for cell in row.cells
    )
    assert not c.extract_tables(fixture(tmp_path, rotate=90)).grids


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_file_bytes", 1),
        ("max_pages", 1),
        ("max_stream_bytes", 1),
        ("max_operations", 1),
        ("max_segments", 1),
        ("max_runs", 1),
        ("max_characters", 1),
        ("max_cells", 1),
        ("max_stack", 1),
    ],
)
def test_resource_limits_discard_partial_geometry(tmp_path, field, value):
    path = fixture(tmp_path, pages=2, extra="q q Q Q")
    result = c.extract_tables(path, limits=replace(c.TableLimits(), **{field: value}))
    assert result.status.value == "failed" and not result.grids and not result.pages


@pytest.mark.parametrize("value", [0, -1, True, 1.5, float("inf"), float("nan")])
def test_invalid_limits_rejected(value):
    with pytest.raises(ValueError):
        c.TableLimits(max_cells=value)


def test_timeout_corrupt_and_identity_failure_are_sanitized(tmp_path, monkeypatch):
    path = fixture(tmp_path)
    ticks = iter([0, 20])
    with monkeypatch.context() as m:
        m.setattr(c.time, "monotonic", lambda: next(ticks))
        e = c.extract_tables(path)
    assert e.issues == ("timeout",) and not e.grids
    path.write_bytes(b"PRIVATE invalid PDF")
    e = c.extract_tables(path)
    assert e.status.value == "failed" and "PRIVATE" not in json.dumps(e.to_dict())
    path = fixture(tmp_path)
    native = extract_file(path)
    with pytest.raises(ValueError):
        c.supplement(native, replace(c.extract_tables(path), source_sha256="0" * 64))


def test_native_review_cannot_be_promoted_and_failures_keep_denominators(tmp_path):
    path = fixture(tmp_path)
    native = extract_file(path)
    evidence = c.extract_tables(path)
    native = replace(native, status=c.ExtractionStatus.NEEDS_REVIEW)
    assert c.supplement(native, evidence).status.value == "needs_review"
    record = gold(path)
    missing = b.summarize(record, None)
    assert missing["labels"] == {
        "anchors": 4,
        "provenance": 4,
        "order": 2,
        "cells": 4,
        "relations": 2,
        "numeric": 2,
    }
    assert b.totals([missing], "candidate")["table_cells"] == {
        "passed": 0,
        "evaluated": 0,
        "label_total": 4,
        "unknown_documents": 1,
    }
    assert b.decision([missing]) == "REJECT"
    bad = replace(evidence, status=c.ExtractionStatus.FAILED, grids=(), issues=("timeout",))
    raw = {
        "baseline": native.to_dict(),
        "candidate": c.supplement(native, bad).to_dict(),
        "geometry": bad.to_dict(),
        "baseline_after": b.fingerprint(native.to_dict()),
    }
    summary = b.summarize(record, raw)
    assert summary["candidate_scores"] is None and summary["status"] == "failed"


@pytest.mark.parametrize("mode", ["timeout", "memory_limit", "worker_failed"])
def test_isolated_resource_failure_and_cleanup(tmp_path, mode):
    guards = {
        **b.GUARDS,
        "timeout_seconds": 0.05 if mode == "timeout" else 5,
        "max_process_bytes": 1 if mode == "memory_limit" else b.GUARDS["max_process_bytes"],
    }
    command = [
        sys.executable,
        "-B",
        "-c",
        "raise SystemExit(3)" if mode == "worker_failed" else "import time; time.sleep(10)",
    ]
    r = b.monitor(command, tmp_path, guards=guards)
    assert r["failure"] == mode and r["cleanup"] and not (tmp_path / "result.json").exists()


def test_worker_success_and_no_private_console_output(tmp_path, capsys):
    path = fixture(tmp_path)
    assert b.worker(path, tmp_path) == 0
    assert capsys.readouterr().out == "" and capsys.readouterr().err == ""
    raw = json.loads((tmp_path / "result.json").read_text())
    summary = b.summarize(gold(path), raw)
    assert summary["native_preserved"] and b.decision([summary]) == "PROMOTE"
    assert "Header A" not in json.dumps(summary)
