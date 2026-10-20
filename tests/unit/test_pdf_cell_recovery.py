"""Public source drawings reproduce native word ownership across a physical divider."""

from __future__ import annotations

import copy

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, FloatObject, NameObject

from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import pdf_cell_recovery as recovery
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_table_review_packet as packet


def reference(tmp_path, *, borderless=False, crossed=False, gap=False, merged=False):
    """Independent 2x2 drawing with an intentionally misassigned candidate token."""
    path = tmp_path / "public.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(300, 300)
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
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    commands = ["0 0 0 rg"]
    if not borderless:
        commands += [f"40 {y} 200.6 0.6 re f" for y in (100, 180, 260)]
        commands += [f"{x} 100 0.6 160.6 re f" for x in (40, 240)]
        if merged:
            commands += ["140 100 0.6 80.6 re f"]
        elif gap:
            commands += ["140 100 0.6 110 re f", "140 220 0.6 40.6 re f"]
        else:
            commands += ["140 100 0.6 160.6 re f"]
    literals = ("Rate", "Qty of parts", "+001.20", "Qty of parts")
    for i, literal in enumerate(literals):
        x, y = 50 + (i % 2) * 100, 220 - (i // 2) * 80
        if crossed and i == 0:
            x = 138
        commands.append(f"BT /F1 10 Tf 1 0 0 1 {x} {y} Tm ({literal}) Tj ET")
    stream = DecodedStreamObject()
    stream.set_data(("\n".join(commands) + "\n").encode())
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)
    boxes = (
        [40.3, 180.3, 140.3, 260.3],
        [140.3, 180.3, 240.3, 260.3],
        [40.3, 100.3, 140.3, 180.3],
        [140.3, 100.3, 240.3, 180.3],
    )
    cells = [
        {
            "review_cell_id": f"physical-{i}",
            "row": i // 2,
            "column": i % 2,
            "row_span": 1,
            "column_span": 1,
            "bbox_pdf_user_space_points": box,
            "literal_text": literal,
        }
        for i, (box, literal) in enumerate(
            zip(boxes, ("Rate Qty", "of parts", *literals[2:]), strict=True)
        )
    ]
    candidate = {"method": "public-wrong-word-assignment", "cells": cells}
    context = {
        "source_sha256": packet.sha(path),
        "document_id": "public-drawing",
        "page_identity": validation.original_pages(path)[0],
        "review_table_id": "physical-table",
        "bbox": [40.3, 100.3, 240.3, 260.3],
        "rows": 2,
        "columns": 2,
    }
    proposal = {"context": context, "candidate": candidate, "cells": copy.deepcopy(cells)}
    return path, bind(proposal), literals


def bind(proposal):
    proposal["proposal_id"] = fingerprint({key: proposal[key] for key in ("context", "candidate")})
    return proposal


def recover(path, proposal):
    return recovery.recover(path, packet.sha(path), proposal)


def test_split_phrase_reassigned_from_original_without_merging_physical_cells(tmp_path):
    path, proposal, literals = reference(tmp_path)
    original = copy.deepcopy(proposal)
    before = path.read_bytes()
    result = recover(path, proposal)
    cells = result["cells"]
    assert result["document_id"] == proposal["context"]["document_id"]
    assert [cell["literal_text"] for cell in cells] == list(literals)
    for before_cell, after in zip(original["cells"], cells, strict=True):
        for field in (
            "review_cell_id",
            "row",
            "column",
            "row_span",
            "column_span",
            "bbox_pdf_user_space_points",
        ):
            assert after[field] == before_cell[field]
        assert after["proposal_origin"]["method"] == recovery.METHOD
        assert after["header_role"] is None
    assert cells[1]["review_cell_id"] != cells[3]["review_cell_id"]
    evidence = result["lineage"]["cells"]
    assert evidence[1]["character_range"] != evidence[3]["character_range"]
    assert all(e["glyphs"] for e in evidence)
    indices = [g["index"] for e in evidence for g in e["glyphs"] if not g["generated"]]
    assert len(indices) == len(set(indices))
    assert result["qg_00"] == "NOT_EVALUATED" and not result["human_review_completed"]
    assert result["relationships"] == []
    assert proposal == original and path.read_bytes() == before
    assert result == recover(path, proposal)


@pytest.mark.parametrize("options", [{"borderless": True}, {"gap": True}])
def test_unverified_boundaries_never_repaired_from_reference_text(tmp_path, options):
    path, proposal, _ = reference(tmp_path, **options)
    result = recover(path, proposal)
    assert result["geometry_status"] == "UNRESOLVED"
    assert all(c["literal_text"] is None for c in result["cells"])
    assert not result["lineage"]["cells"]


def test_real_divider_prevents_joining_unrelated_cells(tmp_path):
    path, proposal, _ = reference(tmp_path)
    first = proposal["cells"][0]
    first["bbox_pdf_user_space_points"][2] = 240.3
    first["column_span"] = 2
    proposal["cells"].pop(1)
    result = recover(path, proposal)
    assert "INTERNAL_RULING_DIVIDES_CELL" in result["issues"]
    assert all(c["literal_text"] is None for c in result["cells"])


def test_genuine_merged_cell_preserves_span_and_separate_numeric_values(tmp_path):
    path, proposal, _ = reference(tmp_path, merged=True)
    first = proposal["cells"][0]
    first["bbox_pdf_user_space_points"][2] = 240.3
    first["column_span"] = 2
    proposal["cells"].pop(1)
    result = recover(path, proposal)
    assert result["geometry_status"] == "VERIFIED_ORIGINAL_RULINGS"
    assert result["cells"][0]["column_span"] == 2
    assert result["cells"][1]["literal_text"] == "+001.20"


def test_crossing_glyph_is_unresolved_not_clipped_or_reassigned_by_center(tmp_path):
    path, proposal, _ = reference(tmp_path, crossed=True)
    result = recover(path, proposal)
    assert result["cells"][0]["literal_text"] is None
    assert result["cells"][1]["literal_text"] is None
    assert result["cells"][2]["literal_text"] == "+001.20"


@pytest.mark.parametrize(
    "fault", ["hash", "page", "id", "slot", "outside", "fingerprint", "cell_page", "basis"]
)
def test_malformed_or_mismatched_reference_rejected(tmp_path, fault):
    path, proposal, _ = reference(tmp_path)
    if fault == "hash":
        proposal["context"]["source_sha256"] = "a" * 64
    elif fault == "page":
        proposal["context"]["page_identity"]["crop_box_pdf_user_space"][0] += 1
    elif fault == "id":
        proposal["cells"][1]["review_cell_id"] = proposal["cells"][0]["review_cell_id"]
    elif fault == "slot":
        proposal["cells"][1]["column"] = 0
    elif fault == "outside":
        proposal["cells"][0]["bbox_pdf_user_space_points"][0] = -1
    elif fault == "cell_page":
        proposal["cells"][0]["page_number"] = 2
    elif fault == "basis":
        proposal["cells"][0]["coordinate_basis"] = "viewer_pixels"
    if fault != "fingerprint":
        bind(proposal)
    else:
        proposal["proposal_id"] = "0" * 64
    with pytest.raises(ValueError):
        recover(path, proposal)


def test_logical_slot_cannot_be_relabelled_using_another_physical_cell(tmp_path):
    path, proposal, _ = reference(tmp_path)
    left, right = proposal["cells"][:2]
    left["bbox_pdf_user_space_points"], right["bbox_pdf_user_space_points"] = (
        right["bbox_pdf_user_space_points"],
        left["bbox_pdf_user_space_points"],
    )
    with pytest.raises(ValueError, match="geometry disagrees|grid order"):
        recover(path, proposal)


def test_unsupported_page_transform_and_bounded_input(tmp_path):
    path, proposal, _ = reference(tmp_path)
    with pytest.raises(ValueError):
        recovery.recover(path, packet.sha(path), proposal, max_file_bytes=1)
    writer = PdfWriter(clone_from=path)
    writer.pages[0][NameObject("/UserUnit")] = FloatObject(2)
    writer.write(path)
    proposal["context"]["source_sha256"] = packet.sha(path)
    bind(proposal)
    with pytest.raises(ValueError, match="transform"):
        recover(path, proposal)


@pytest.mark.parametrize("operation", ["clip", "cover"])
def test_invisible_rulings_do_not_verify_physical_cells(tmp_path, operation):
    from pypdf import PdfReader

    path, proposal, _ = reference(tmp_path)
    reader = PdfReader(path)
    writer = PdfWriter(clone_from=reader)
    data = reader.pages[0].get_contents().get_data()
    if operation == "clip":
        data = b"q 0 0 10 10 re W n\n" + data + b"\nQ"
    else:
        data += b"\n1 1 1 rg 0 0 300 300 re f"
    stream = DecodedStreamObject()
    stream.set_data(data)
    writer.pages[0][NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)
    proposal["context"]["source_sha256"] = packet.sha(path)
    bind(proposal)
    result = recover(path, proposal)
    assert result["geometry_status"] == "UNRESOLVED"
    assert all(c["literal_text"] is None for c in result["cells"])


def test_lineage_capture_does_not_change_existing_text_reconstruction(tmp_path):
    from tools.extraction_quality import pdf_grid_proposals as grids

    path, proposal, _ = reference(tmp_path)
    plain = {"cells": copy.deepcopy(proposal["cells"]), "issues": []}
    captured = copy.deepcopy(plain)
    lineage = {}
    grids.add_text(path, 1, plain)
    grids.add_text(path.read_bytes(), 1, captured, lineage=lineage)
    assert captured == plain
    assert len(lineage["cells"]) == 4
    for evidence in lineage["cells"]:
        assert (
            "".join(chr(g["unicode"]) for g in evidence["glyphs"])
            == captured["cells"][evidence["cell_index"]]["literal_text"]
        )
