"""Fresh public PDF constructions. Expected topology comes from the generator."""

from __future__ import annotations

import json
import sys
from dataclasses import replace

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from tools.pdf_table_geometry import diagnose as d

GRID = (
    "50 100 m 350 100 l 50 150 m 350 150 l 50 200 m 350 200 l "
    "50 100 m 50 200 l 200 100 m 200 200 l 350 100 m 350 200 l S\n"
)
LITERALS = ("P1", "P2", "0012", "-12.5 kg")
VARIANTS = (
    "stroke",
    "filled_rules",
    "cell_rectangles",
    "continuous_split",
    "gap",
    "merged",
    "single_column",
    "borderless",
    "duplicate_edges",
    "text_crossing",
    "unpainted_rectangles",
    "separate_boxes",
)


def make_pdf(path, variant="stroke", pages=1):
    """Known 2x2 geometry except deliberately documented structural controls."""
    paint = GRID
    if variant == "filled_rules":
        paint = "".join(f"50 {y} 301 1 re f\n" for y in (100, 150, 200)) + "".join(
            f"{x} 100 1 101 re f\n" for x in (50, 200, 350)
        )
    elif variant == "cell_rectangles":
        paint = "".join(f"{x} {y} 150 50 re S\n" for y in (100, 150) for x in (50, 200))
    elif variant == "continuous_split":
        paint = GRID.replace("200 100 m 200 200 l", "200 100 m 200 150 l 200 150 m 200 200 l")
    elif variant == "gap":
        paint = GRID.replace("200 100 m 200 200 l", "200 100 m 200 149 l 200 151 m 200 200 l")
    elif variant == "merged":
        paint = GRID.replace("200 100 m 200 200 l", "200 100 m 200 150 l")
    elif variant == "single_column":
        paint = "50 50 150 150 re 50 100 m 200 100 l 50 150 m 200 150 l S\n"
    elif variant == "borderless":
        paint = ""
    elif variant == "duplicate_edges":
        paint = GRID * 2
    elif variant == "unpainted_rectangles":
        paint = "".join(f"{x} {y} 150 50 re n\n" for y in (100, 150) for x in (50, 200))
    elif variant == "separate_boxes":
        paint = "50 100 140 50 re S 210 100 140 50 re S\n"
    elif variant not in ("stroke", "text_crossing"):
        raise ValueError("Unknown public fixture")
    writer = PdfWriter()
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Courier"),
                NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
            }
        )
    )
    text = "".join(
        f"BT /F1 10 Tf 1 0 0 1 {x} {y} Tm ({value}) Tj ET\n"
        for (x, y), value in zip(
            ((60, 170), (210, 170), (60, 120), (210, 120)), LITERALS, strict=True
        )
    )
    if variant == "single_column":
        text = "BT /F1 10 Tf 1 0 0 1 70 175 Tm (Column) Tj ET"
    if variant == "text_crossing":
        text = "BT /F1 10 Tf 1 0 0 1 198 170 Tm (Crossing) Tj ET"
    for _ in range(pages):
        page = writer.add_blank_page(width=400, height=300)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        stream.set_data((paint + text).encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def inspect(tmp_path, variant):
    return d.analyze_pdf(make_pdf(tmp_path / (variant + ".pdf"), variant))["pages"][0]


def test_independent_stroked_control_and_structure(tmp_path):
    path = make_pdf(tmp_path / "control.pdf")
    page = d.analyze_pdf(path)["pages"][0]
    assert len(PdfReader(path).pages) == 1
    assert page["native_cells"] == 4 and len(page["tables"]) == 1
    table = page["tables"][0]
    assert table["cells"] == table["lattice_positions"] == 4
    assert table["missing_source_cell_boundaries"] == 0 and not table["minimum_grid_rejection"]
    assert table["char_boxes_in_no_cell"] == 0
    assert page["independent_pypdf_operators"]["re"] == 0
    assert page["independent_pypdf_operators"]["S"] == 1
    assert all(literal not in json.dumps(page) for literal in LITERALS)


def test_thin_filled_rule_outlines_create_micro_regions(tmp_path):
    page = inspect(tmp_path, "filled_rules")
    assert page["filled_thin_rectangles"] == 6
    assert page["independent_pypdf_operators"]["re"] == 6
    assert page["independent_pypdf_operators"]["f"] == 6
    assert page["native_cells"] > 4
    assert sum(t["micro_cells"] for t in page["tables"]) > 0
    assert sum(t["centers_in_filled_thin_rectangles"] for t in page["tables"]) > 0


def test_normal_rectangles_and_duplicate_edges_are_not_automatically_bad(tmp_path):
    for variant in ("cell_rectangles", "duplicate_edges"):
        page = inspect(tmp_path, variant)
        assert page["duplicate_edges"] > 0 and page["collinear_overlap_pairs"] > 0
        assert (
            page["native_cells"] == 4 and page["tables"][0]["missing_source_cell_boundaries"] == 0
        )


def test_nonpainting_paths_are_not_proof_of_visible_rules(tmp_path):
    page = inspect(tmp_path, "unpainted_rectangles")
    assert page["rectangles_total"] == 0 and page["raw_edges"] == 0
    assert page["independent_pypdf_operators"]["re"] == 4
    assert page["independent_pypdf_operators"]["n"] == 4
    assert page["independent_pypdf_operators"]["S"] == 0
    assert page["independent_pypdf_operators"]["f"] == 0
    assert page["native_cells"] == 0


def test_closed_but_disconnected_cells_are_filtered_as_singletons(tmp_path):
    page = inspect(tmp_path, "separate_boxes")
    assert page["native_cells"] == 2 and page["singleton_cells_filtered"] == 2
    assert page["tables"] == []


def test_exact_continuity_is_distinct_from_real_gap(tmp_path):
    continuous = inspect(tmp_path, "continuous_split")
    assert continuous["native_cells"] == 4
    gap = inspect(tmp_path, "gap")
    assert gap["near_collinear_gaps"] > 0 and gap["near_missing_crossing_pairs"] > 0
    assert gap["native_cells"] < 4


def test_true_merged_geometry_and_single_column_policy_are_distinct(tmp_path):
    merged = inspect(tmp_path, "merged")["tables"][0]
    assert merged["cells"] == 3 and merged["lattice_positions"] == 4
    assert merged["nonuniform_lattice_rejection"] and merged["missing_source_cell_boundaries"] == 0
    column = inspect(tmp_path, "single_column")["tables"][0]
    assert column["cells"] == column["lattice_positions"] == 3
    assert column["minimum_grid_rejection"] and not column["nonuniform_lattice_rejection"]
    assert column["missing_source_cell_boundaries"] == 0


def test_borderless_and_crossing_text_do_not_invent_cells(tmp_path):
    no_grid = inspect(tmp_path, "borderless")
    assert no_grid["characters"] > 0 and no_grid["native_cells"] == 0
    crossing = inspect(tmp_path, "text_crossing")["tables"][0]
    assert crossing["char_boxes_in_no_cell"] > 0


def test_public_pdfium_render_and_characters(tmp_path):
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(make_pdf(tmp_path / "public.pdf", "filled_rules")))
    try:
        page = doc[0]
        text = page.get_textpage()
        bitmap = page.render(scale=2)
        try:
            assert all(value in text.get_text_range() for value in LITERALS)
            image = bitmap.to_pil()
            assert image.size == (800, 600)
            for x, y in ((125, 125), (275, 125), (125, 175), (275, 175)):
                assert sum(image.getpixel((x * 2, (300 - y) * 2))[:3]) > 700
            for x, y in ((200.5, 125), (125, 150.5)):
                assert sum(image.getpixel((round(x * 2), round((300 - y) * 2)))[:3]) < 60
        finally:
            bitmap.close()
            text.close()
            page.close()
    finally:
        doc.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_file_bytes", 1),
        ("max_pages", 1),
        ("max_characters", 1),
        ("max_edges", 1),
        ("max_cells", 1),
        ("max_operations", 1),
        ("max_stream_bytes", 1),
    ],
)
def test_limits_do_not_publish_partial_diagnostics(tmp_path, field, value):
    path = make_pdf(tmp_path / "limit.pdf", pages=2)
    with pytest.raises(d.DiagnosticLimit):
        d.analyze_pdf(path, replace(d.Limits(), **{field: value}))


@pytest.mark.parametrize("value", [0, -1, True, 1.5, float("inf"), float("nan")])
def test_invalid_limits(value):
    with pytest.raises(ValueError):
        d.Limits(max_cells=value)


def test_timeout_invalid_geometry_and_corrupt_input(tmp_path, monkeypatch):
    path = make_pdf(tmp_path / "timeout.pdf")
    ticks = iter([0, 20])
    with monkeypatch.context() as m:
        m.setattr(d.time, "monotonic", lambda: next(ticks))
        with pytest.raises(d.DiagnosticLimit, match="timeout"):
            d.analyze_pdf(path)
    assert d.box((0, 0, float("nan"), 2)) is None
    path.write_bytes(b"PUBLIC corrupt PDF")
    from pdfplumber.utils.exceptions import PdfminerException

    with pytest.raises(PdfminerException):
        d.analyze_pdf(path)


@pytest.mark.parametrize("mode", ["timeout", "memory_limit", "worker_failed"])
def test_parent_resource_failure_cleanup(tmp_path, mode):
    from tools.pdf_table_candidate import benchmark as base

    guards = {
        **base.GUARDS,
        "timeout_seconds": 0.05 if mode == "timeout" else 5,
        "max_process_bytes": 1 if mode == "memory_limit" else base.GUARDS["max_process_bytes"],
    }
    result = base.monitor(
        [
            sys.executable,
            "-B",
            "-c",
            "raise SystemExit(4)" if mode == "worker_failed" else "import time; time.sleep(10)",
        ],
        tmp_path,
        guards=guards,
    )
    assert (
        result["failure"] == mode and result["cleanup"] and not (tmp_path / "result.json").exists()
    )


def test_capture_publication_and_bounded_output(tmp_path):
    path = tmp_path / "result.capture"
    d.write_capture(path, {"count": 4}, max_bytes=100)
    assert not (tmp_path / "result.json").exists()
    assert d.collect_capture(tmp_path, {"failure": None, "cleanup": True}) == {"count": 4}
    assert not path.exists()
    (tmp_path / "result.json").unlink()
    with pytest.raises(d.DiagnosticLimit, match="output_limit"):
        d.write_capture(path, {"large": "x" * 100}, max_bytes=10)
    assert d.collect_capture(tmp_path, {"failure": "worker_failed", "cleanup": True}) is None
    assert not path.exists() and not (tmp_path / "result.json").exists()


@pytest.mark.parametrize(
    "resource",
    [
        {"failure": None, "cleanup": True},
        {"failure": "timeout", "cleanup": True},
        {"failure": None, "cleanup": False},
    ],
)
def test_invalid_or_terminated_capture_is_never_published(tmp_path, resource):
    (tmp_path / "result.capture").write_text('{"incomplete":', encoding="utf-8")
    assert d.collect_capture(tmp_path, resource) is None
    assert not (tmp_path / "result.capture").exists() and not (tmp_path / "result.json").exists()
