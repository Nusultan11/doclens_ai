"""Opt-in offline recovery from original glyphs and verified physical cell boundaries.

Reference literals, predicted word ownership, headers and relationships are never
used to reconstruct text. This produces machine evidence, never reviewed Gold.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from contextlib import closing
from ctypes import c_float, c_int, c_uint
from io import BytesIO
from itertools import pairwise
from pathlib import Path

from pypdf import PdfReader

from doclens_ai.extraction.evidence_v2 import Cell, Locator, valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import pdf_grid_proposals as grids
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_table_review_packet as packet

METHOD = "original-physical-cell-text-recovery-v1"
EPSILON = 0.001  # Numerical comparison of PDFium floats, not a glyph ownership tolerance.
MAX_RULE_WIDTH = 2.0  # Restricted supported filled-ruling representation in PDF points.
GEOMETRY_FIELDS = (
    "review_cell_id",
    "row",
    "column",
    "row_span",
    "column_span",
    "bbox_pdf_user_space_points",
)


def _rulings(data: bytes, page_number: int) -> list[dict]:
    """Only direct opaque black, thin filled rectangles; unsupported paint is not evidence."""
    import pypdfium2 as pdfium

    rules = []
    with pdfium.PdfDocument(data) as document, closing(document[page_number - 1]) as page:
        for index, obj in enumerate(page.get_objects()):
            if index >= 10_000:
                raise ValueError("Original object limit")
            if obj.type == pdfium.raw.FPDF_PAGEOBJ_IMAGE:
                rules = [r for r in rules if not grids.intersects(r["bbox"], obj.get_bounds())]
            if obj.type != pdfium.raw.FPDF_PAGEOBJ_PATH or obj.level != 0:
                continue
            fill, stroke = c_int(), c_int()
            rgba = [c_uint() for _ in range(4)]
            if (
                not pdfium.raw.FPDFPath_GetDrawMode(obj, fill, stroke)
                or not pdfium.raw.FPDFPageObj_GetFillColor(obj, *rgba)
                or not fill.value
                or stroke.value
                or pdfium.raw.FPDFPath_CountSegments(obj) not in (4, 5)
            ):
                continue
            if [v.value for v in rgba] != [0, 0, 0, 255]:
                # Later paint can hide earlier rulers; do not claim an invisible cell boundary.
                rules = [r for r in rules if not grids.intersects(r["bbox"], obj.get_bounds())]
                continue
            if pdfium.raw.FPDFClipPath_CountPaths(pdfium.raw.FPDFPageObj_GetClipPath(obj)) > 0:
                continue  # Clipped rulers need separate visible-boundary evidence.
            # Axis-aligned bounding boxes alone do not establish a rectangle.
            points = []
            matrix = obj.get_matrix()
            for i in range(pdfium.raw.FPDFPath_CountSegments(obj)):
                segment = pdfium.raw.FPDFPath_GetPathSegment(obj, i)
                x, y = c_float(), c_float()
                if not pdfium.raw.FPDFPathSegment_GetPoint(segment, x, y):
                    break
                kind = pdfium.raw.FPDFPathSegment_GetType(segment)
                if kind != (
                    pdfium.raw.FPDF_SEGMENT_MOVETO if i == 0 else pdfium.raw.FPDF_SEGMENT_LINETO
                ):
                    break
                points.append(matrix.on_point(x.value, y.value))
            if len(points) != pdfium.raw.FPDFPath_CountSegments(obj):
                continue
            if len(points) == 5 and points[-1] == points[0]:
                points.pop()
            if len(points) != 4 or not pdfium.raw.FPDFPathSegment_GetClose(segment):
                continue
            left, bottom = min(x for x, y in points), min(y for x, y in points)
            right, top = max(x for x, y in points), max(y for x, y in points)
            corners = {(left, bottom), (left, top), (right, bottom), (right, top)}
            if set(points) != corners or any(
                a[0] != b[0] and a[1] != b[1]
                for a, b in zip(points, points[1:] + points[:1], strict=True)
            ):
                continue
            width, height = right - left, top - bottom
            if not 0 < min(width, height) <= MAX_RULE_WIDTH or max(width, height) < 3:
                continue
            horizontal = width > height
            rules.append(
                {
                    "source_object_index": index,
                    "bbox": [left, bottom, right, top],
                    "axis": "h" if horizontal else "v",
                    "position": (bottom + top) / 2 if horizontal else (left + right) / 2,
                    "low": left if horizontal else bottom,
                    "high": right if horizontal else top,
                }
            )
    return rules


def _boundaries(box: list[float], rules: list[dict]) -> tuple[list[list[int]], set[str]]:
    left, bottom, right, top = box
    sides, issues = [], set()
    for axis, position, low, high in (
        ("h", bottom, left, right),
        ("h", top, left, right),
        ("v", left, bottom, top),
        ("v", right, bottom, top),
    ):
        matching = [
            r for r in rules if r["axis"] == axis and abs(r["position"] - position) <= EPSILON
        ]
        # A filled border terminates at the adjoining border's inside ink edge.
        # Check the whole side interior, without extending missing interior segments.
        endpoint_inset = MAX_RULE_WIDTH / 2
        end = low + endpoint_inset
        used = []
        for rule in sorted(matching, key=lambda r: r["low"]):
            if rule["high"] < end:
                continue
            if rule["low"] > end + EPSILON:
                break
            end = max(end, rule["high"])
            used.append(rule["source_object_index"])
        if end < high - endpoint_inset:
            issues.add("PHYSICAL_CELL_BOUNDARY_NOT_VERIFIED")
        sides.append(used)
    for rule in rules:
        if rule["axis"] == "v":
            inside = left + EPSILON < rule["position"] < right - EPSILON
            overlap = min(top, rule["high"]) - max(bottom, rule["low"])
        else:
            inside = bottom + EPSILON < rule["position"] < top - EPSILON
            overlap = min(right, rule["high"]) - max(left, rule["low"])
        if inside and overlap > MAX_RULE_WIDTH:
            issues.add("INTERNAL_RULING_DIVIDES_CELL")
    return sides, issues


def recover(
    source: Path, expected_sha256: str, proposal: dict, *, max_file_bytes: int = 50 * 1024**2
) -> dict:
    """Re-read physical cells, ignoring proposed literals; return separate machine evidence."""
    packet.no_links(source)
    if type(max_file_bytes) is not int or max_file_bytes <= 0:
        raise ValueError("Invalid input limit")
    if not 0 < source.stat().st_size <= max_file_bytes:
        raise ValueError("Original input limit")
    data = source.read_bytes()
    if len(data) > max_file_bytes or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("Original SHA mismatch")
    context = proposal["context"]
    if context["source_sha256"] != expected_sha256 or proposal["proposal_id"] != fingerprint(
        {key: proposal[key] for key in ("context", "candidate")}
    ):
        raise ValueError("Reference source or fingerprint mismatch")
    reader = PdfReader(BytesIO(data))
    number = context["page_identity"]["page_number"]
    if (
        reader.is_encrypted
        or not 0 < len(reader.pages) <= 100
        or type(number) is not int
        or not 1 <= number <= len(reader.pages)
    ):
        raise ValueError("Original page rejected")
    page = reader.pages[number - 1]
    identity = {
        "page_number": number,
        "media_box_pdf_user_space": list(map(float, page.mediabox)),
        "crop_box_pdf_user_space": list(map(float, page.cropbox)),
        "rotation": page.rotation,
    }
    if identity != context["page_identity"]:
        raise ValueError("Reference page identity mismatch")
    if page.rotation != 0 or page.get("/UserUnit", 1) != 1:
        raise ValueError("Unsupported original page transform")
    rows, columns = context["rows"], context["columns"]
    if (
        type(rows) is not int
        or not 1 <= rows <= 256
        or type(columns) is not int
        or not 1 <= columns <= 64
    ):
        raise ValueError("Reference grid limit")
    if not valid_bbox(tuple(context["bbox"]), tuple(identity["crop_box_pdf_user_space"])):
        raise ValueError("Reference region outside page")
    if not isinstance(proposal["cells"], list) or not 0 < len(proposal["cells"]) <= 2048:
        raise ValueError("Reference cell limit")
    cells, ids, occupied = [], set(), set()
    x_edges, y_edges = {}, {}
    for raw in proposal["cells"]:
        if (
            raw.get("page_number", number) != number
            or raw.get("coordinate_basis", "pdf_user_space_unrotated") != "pdf_user_space_unrotated"
        ):
            raise ValueError("Reference cell page or coordinate basis mismatch")
        cell = {key: copy.deepcopy(raw[key]) for key in GEOMETRY_FIELDS}
        Cell(
            cell_id=cell["review_cell_id"],
            literal="",
            row=cell["row"],
            column=cell["column"],
            row_span=cell["row_span"],
            column_span=cell["column_span"],
            role=None,
            locator=Locator(
                page=number,
                bbox=tuple(cell["bbox_pdf_user_space_points"]),
                coordinate_basis="pdf_user_space_unrotated",
            ),
        )
        if cell["review_cell_id"] in ids or any(
            cell[k] is None for k in ("row", "column", "row_span", "column_span")
        ):
            raise ValueError("Reference cell identity or grid missing")
        if cell["row"] + cell["row_span"] > rows or cell["column"] + cell["column_span"] > columns:
            raise ValueError("Reference cell outside grid")
        slots = {
            (r, c)
            for r in range(cell["row"], cell["row"] + cell["row_span"])
            for c in range(cell["column"], cell["column"] + cell["column_span"])
        }
        if occupied & slots or any(r >= rows or c >= columns for r, c in slots):
            raise ValueError("Reference cell grid conflict")
        if not valid_bbox(tuple(cell["bbox_pdf_user_space_points"]), tuple(context["bbox"])) or any(
            grids.intersects(
                cell["bbox_pdf_user_space_points"], other["bbox_pdf_user_space_points"]
            )
            for other in cells
        ):
            raise ValueError("Reference cell geometry conflict")
        left, bottom, right, top = cell["bbox_pdf_user_space_points"]
        for edges, index, value in (
            (x_edges, cell["column"], left),
            (x_edges, cell["column"] + cell["column_span"], right),
            (y_edges, cell["row"], top),
            (y_edges, cell["row"] + cell["row_span"], bottom),
        ):
            if index in edges and abs(edges[index] - value) > EPSILON:
                raise ValueError("Physical geometry disagrees with logical grid")
            edges[index] = value
        occupied.update(slots)
        ids.add(cell["review_cell_id"])
        cell.update(
            literal_text=None,
            text_status="NO_RELIABLE_TEXT",
            header_role=None,
            page_number=number,
            coordinate_basis="pdf_user_space_unrotated",
            proposal_origin={"method": METHOD, "proposal_id": proposal["proposal_id"]},
        )
        cells.append(cell)
    if len(occupied) != rows * columns:
        raise ValueError("Incomplete physical grid reference")
    if any(a >= b for a, b in pairwise(x_edges[k] for k in sorted(x_edges))) or any(
        a <= b for a, b in pairwise(y_edges[k] for k in sorted(y_edges))
    ):
        raise ValueError("Physical grid order mismatch")
    outer = (x_edges[0], y_edges[rows], x_edges[columns], y_edges[0])
    if any(abs(a - b) > EPSILON for a, b in zip(outer, context["bbox"], strict=True)):
        raise ValueError("Physical grid extent mismatch")
    rules = _rulings(data, number)
    issues, boundaries = set(), []
    for cell in cells:
        refs, errors = _boundaries(cell["bbox_pdf_user_space_points"], rules)
        boundaries.append({"cell_id": cell["review_cell_id"], "side_object_indices": refs})
        issues.update(errors)
    candidate = {"method": METHOD, "cells": cells, "issues": sorted(issues)}
    diagnostics, lineage = {}, {"page_number": number, "cells": []}
    if not issues:
        grids.add_text(data, number, candidate, diagnostics=diagnostics, lineage=lineage)
    for evidence in lineage["cells"]:
        evidence["cell_id"] = cells[evidence["cell_index"]]["review_cell_id"]
    by_index = {e["cell_index"]: e for e in lineage["cells"]}
    for index, cell in enumerate(cells):
        cell["unresolved"] = []
        if cell["literal_text"] is None:
            cell["unresolved"].append("NO_RELIABLE_ORIGINAL_TEXT")
        elif any(g["generated"] != 0 for g in by_index[index]["glyphs"]):
            cell["unresolved"].append("POSITION_INFERRED_SEPARATORS_NOT_LITERAL_SPACE_PROOF")
        cell["uncertain"] = bool(cell["unresolved"])
    return {
        "method": METHOD,
        "source_sha256": expected_sha256,
        "source_size_bytes": len(data),
        "document_id": context["document_id"],
        "input_proposal_sha256": fingerprint(proposal),
        "page_identity": identity,
        "review_table_id": context["review_table_id"],
        "geometry_status": "UNRESOLVED" if issues else "VERIFIED_ORIGINAL_RULINGS",
        "cells": cells,
        "lineage": lineage,
        "ruling_objects": rules,
        "boundaries": boundaries,
        "diagnostics": diagnostics,
        "issues": sorted(issues),
        "relationships": [],
        "human_review_completed": False,
        "qg_00": "NOT_EVALUATED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet.no_links(args.output)
        output = args.output.resolve()
        if output.parent != packet.ROOT / "evaluation-output" or not output.name.startswith(
            "pdf-cell-recovery-"
        ):
            raise ValueError("Fresh ignored recovery output required")
        packet.fresh_output(output, args.source.parent)
        result = recover(args.source, args.source_sha256, validation.read_json(args.proposal))
        output.mkdir()
        packet.write_json(output / "cell-evidence.json", result)
        print(
            json.dumps(
                {
                    "geometry_status": result["geometry_status"],
                    "cells": len(result["cells"]),
                    "recovered_literals": sum(
                        c["literal_text"] is not None for c in result["cells"]
                    ),
                    "issues": result["issues"],
                    "qg_00": result["qg_00"],
                }
            )
        )
        return 0
    except Exception:  # noqa: BLE001 - private literals and paths never enter CLI diagnostics
        print("BLOCKED: original binding, physical reference or fresh private output rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
