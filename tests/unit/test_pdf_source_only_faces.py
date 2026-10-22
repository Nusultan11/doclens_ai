"""Independently drawn public PDFs, no private annotations or geometry plans."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pypdf.errors import PdfReadError

from tests.unit.test_pdf_cell_recovery import reference
from tools.extraction_quality import pdf_source_only_faces as tool


def test_source_only_faces_are_inner_edges_with_original_bar_and_glyph_evidence(tmp_path):
    path, _, literals = reference(tmp_path)
    before = path.read_bytes()
    result = tool.infer(before)
    page = result["pages"][0]
    assert len(page["regions"]) == 1 and len(page["cells"]) == 4
    assert [c["literal_text"] for c in page["cells"]] == list(literals)
    assert page["cells"][0]["bbox"] == pytest.approx([40.6, 180.6, 140, 260], abs=0.0001)
    rules = {r["source_object_index"]: r for r in page["source_rules"]}
    owned = []
    for cell in page["cells"]:
        left, bottom, right, top = [rules[i]["bbox"] for i in cell["boundary_objects"]]
        assert cell["bbox"] == [left[2], bottom[3], right[0], top[1]]
        assert cell["semantic_role"] is None
        assert cell["exact_border_fidelity"] == "NOT_EVALUATED"
        owned += cell["glyph_indices"]
    assert len(owned) == len(set(owned))
    assert result["relationships"] == [] and result["status"] == "needs_review"
    assert path.read_bytes() == before and tool.infer(before) == result


@pytest.mark.parametrize("options", [dict(borderless=True), dict(gap=True), dict(merged=True)])
def test_open_or_insufficient_region_never_gets_completed(tmp_path, options):
    path, _, _ = reference(tmp_path, **options)
    result = tool.infer(path.read_bytes())
    assert result["pages"][0]["regions"] == []
    assert result["pages"][0]["cells"] == []


def test_crossing_text_is_unknown_and_never_repaired(tmp_path):
    path, _, _ = reference(tmp_path, crossed=True)
    page = tool.infer(path.read_bytes())["pages"][0]
    assert page["regions"]
    assert any(c["literal_text"] is None for c in page["cells"])
    assert "CROSSING_GLYPHS_UNRESOLVED" in page["issues"]


def test_no_reference_or_filesystem_annotation_interface(tmp_path, monkeypatch):
    path, _, _ = reference(tmp_path)
    data = path.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Reference access during inference")

    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    assert len(tool.infer(data)["pages"][0]["cells"]) == 4
    with pytest.raises(TypeError):
        tool.infer(data, geometry_plan={"bbox": [40, 100, 240, 260]})
    with pytest.raises(TypeError):
        tool.infer(data, labels=["invented"])


@pytest.mark.parametrize(
    "config",
    [
        replace(tool.Config(), max_file_bytes=1),
        replace(tool.Config(), max_rules=1),
        replace(tool.Config(), max_characters=1),
        replace(tool.Config(), max_faces=1),
        replace(tool.Config(), max_operations=1),
    ],
)
def test_resource_limits_reject_instead_of_publishing_partial_cells(tmp_path, config):
    path, _, _ = reference(tmp_path)
    with pytest.raises(ValueError):
        tool.infer(path.read_bytes(), config)


def test_bad_inputs_and_invalid_configuration():
    for data in (b"", b"not a PDF", "not bytes"):
        with pytest.raises((ValueError, PdfReadError)):
            tool.infer(data)
    with pytest.raises(ValueError):
        tool.Config(min_face_side=float("nan"))


def test_duplicate_rules_do_not_create_duplicate_faces(tmp_path, monkeypatch):
    path, _, _ = reference(tmp_path)
    rules = tool._rulings(path.read_bytes(), 1)
    actual = tool.faces_from_rules(rules, tool.Config())
    repeated = tool.faces_from_rules(rules + rules, tool.Config())
    assert [f["bbox"] for f in actual] == [f["bbox"] for f in repeated]
