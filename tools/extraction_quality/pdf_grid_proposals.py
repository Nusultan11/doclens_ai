"""Deterministic ruled-grid candidates from original raster/text only, never Gold."""

from __future__ import annotations

import base64
import math
import struct
import zlib
from contextlib import closing

from doclens_ai.extraction.evidence_v2 import valid_bbox

METHOD = "ml30b-ruled-raster-v1"
MAX_CELLS = 2048


def png_rows(rendered: dict) -> list[bytes]:
    """Decode only the workbench's own unfiltered RGB PNG, never uploaded images."""
    png = base64.b64decode(rendered["png_base64"], validate=True)
    offset, compressed = 8, bytearray()
    while offset < len(png):
        size = struct.unpack(">I", png[offset : offset + 4])[0]
        if png[offset + 4 : offset + 8] == b"IDAT":
            compressed.extend(png[offset + 8 : offset + 8 + size])
        offset += size + 12
    raw = zlib.decompress(compressed)
    stride = 1 + 3 * rendered["width"]
    if len(raw) != stride * rendered["height"]:
        raise ValueError("Original raster dimensions rejected")
    if any(raw[y * stride] for y in range(rendered["height"])):
        raise ValueError("Original raster encoding rejected")
    return [raw[y * stride + 1 : (y + 1) * stride] for y in range(rendered["height"])]


def bands(values: list[tuple[int, float]], max_width: int) -> list[int]:
    groups: list[list[tuple[int, float]]] = []
    for value in values:
        if not groups or value[0] > groups[-1][-1][0] + 1:
            groups.append([])
        groups[-1].append(value)
    # Strongest pixel in each contiguous ruling band; deterministic central tie break.
    return [
        sorted(g, key=lambda v: (-v[1], abs(v[0] - (g[0][0] + g[-1][0]) / 2), v[0]))[0][0]
        for g in groups
        if g[-1][0] - g[0][0] + 1 <= max_width
    ]


def detect(rendered: dict, bbox: list[float], rows: int, columns: int) -> dict:
    """Require every divider segment; never assume equal spacing or infer merged cells."""
    crop = rendered["page_identity"]["crop_box_pdf_user_space"]
    if (
        type(rows) is not int
        or type(columns) is not int
        or not 1 <= rows <= 256
        or not 1 <= columns <= 64
        or rows * columns > MAX_CELLS
        or not isinstance(bbox, list)
        or len(bbox) != 4
        or any(type(v) not in (int, float) or not math.isfinite(v) for v in bbox)
        or not valid_bbox(tuple(bbox), tuple(crop))
    ):
        raise ValueError("Declared grid or original table rectangle rejected")
    pixels = png_rows(rendered)
    sx = rendered["width"] / (crop[2] - crop[0])
    sy = rendered["height"] / (crop[3] - crop[1])
    x0, x1 = round((bbox[0] - crop[0]) * sx), round((bbox[2] - crop[0]) * sx)
    y0, y1 = round((crop[3] - bbox[3]) * sy), round((crop[3] - bbox[1]) * sy)
    result = {
        "method": METHOD,
        "status": "UNRESOLVED",
        "cells": [],
        "issues": [],
        "x_boundaries": [],
        "y_boundaries": [],
    }
    if x1 - x0 < columns * 4 or y1 - y0 < rows * 4:
        result["issues"] = ["Insufficient raster resolution for declared grid"]
        return result

    # Black/gray ruling strokes. Text alone rarely covers 80% of an entire axis.
    def dark(x, y):
        p = pixels[y][x * 3 : x * 3 + 3]
        return max(p) < 200

    xs = bands(
        [
            (x, sum(dark(x, y) for y in range(y0, y1)) / (y1 - y0))
            for x in range(
                max(0, x0 - math.ceil(2 * sx)), min(rendered["width"], x1 + math.ceil(2 * sx) + 1)
            )
            if sum(dark(x, y) for y in range(y0, y1)) / (y1 - y0) >= 0.8
        ],
        max(2, math.ceil(3 * sx)),
    )
    ys = bands(
        [
            (y, sum(dark(x, y) for x in range(x0, x1)) / (x1 - x0))
            for y in range(
                max(0, y0 - math.ceil(2 * sy)), min(rendered["height"], y1 + math.ceil(2 * sy) + 1)
            )
            if sum(dark(x, y) for x in range(x0, x1)) / (x1 - x0) >= 0.8
        ],
        max(2, math.ceil(3 * sy)),
    )
    outer_x = [min(xs, key=lambda v: abs(v - edge), default=-9999) for edge in (x0, x1)]
    outer_y = [min(ys, key=lambda v: abs(v - edge), default=-9999) for edge in (y0, y1)]
    if any(
        abs(value - edge) > max(1, 2 * scale)
        for values, edges, scale in ((outer_x, (x0, x1), sx), (outer_y, (y0, y1), sy))
        for value, edge in zip(values, edges, strict=True)
    ):
        result["issues"] = ["Thin outer ruling not confirmed near selected bounds"]
        return result
    # Reviewer-selected outer bounds remain authoritative. Ignore nearby border bands.
    xs = [x for x in xs if x0 + 2 * sx < x < x1 - 2 * sx]
    ys = [y for y in ys if y0 + 2 * sy < y < y1 - 2 * sy]
    result["detected_internal_dividers"] = {"rows": len(ys), "columns": len(xs)}
    if len(xs) != columns - 1 or len(ys) != rows - 1:
        result["issues"] = ["Ruling count differs from declared grid; no equal-spacing fallback"]
        return result
    px, py = [outer_x[0], *xs, outer_x[1]], [outer_y[0], *ys, outer_y[1]]
    # A mostly full-height line can still hide a merged cell: inspect each local segment.
    for x in px:
        for top, bottom in zip(py, py[1:], strict=False):
            if sum(dark(x, y) for y in range(top + 1, bottom)) / max(1, bottom - top - 1) < 0.9:
                result["issues"] = [
                    "Partial divider or merged cell; manual structure review required"
                ]
                return result
    for y in py:
        for left, right in zip(px, px[1:], strict=False):
            if sum(dark(x, y) for x in range(left + 1, right)) / max(1, right - left - 1) < 0.9:
                result["issues"] = [
                    "Partial divider or merged cell; manual structure review required"
                ]
                return result
    xpdf = [bbox[0], *(crop[0] + x / sx for x in xs), bbox[2]]
    ypdf = [bbox[3], *(crop[3] - y / sy for y in ys), bbox[1]]
    result.update(status="PROPOSED", x_boundaries=xpdf, y_boundaries=ypdf)
    result["cells"] = [
        {
            "row": row,
            "column": column,
            "row_span": 1,
            "column_span": 1,
            "bbox_pdf_user_space_points": [
                xpdf[column],
                ypdf[row + 1],
                xpdf[column + 1],
                ypdf[row],
            ],
            "literal_text": None,
            "text_status": "NO_RELIABLE_TEXT",
        }
        for row in range(rows)
        for column in range(columns)
    ]
    return result


def add_text(path, page_number: int, proposal: dict) -> None:
    """Bounded original text only when each intersecting glyph belongs to one cell."""
    import pypdfium2 as pdfium

    if not proposal["cells"]:
        return
    cells = proposal["cells"]
    bad, present = set(), set()
    owners, characters = {}, []
    with (
        pdfium.PdfDocument(path.read_bytes()) as document,
        closing(document[page_number - 1]) as page,
    ):
        with closing(page.get_textpage()) as text:
            if text.count_chars() > 200_000:
                proposal["issues"].append("Text layer exceeds inspection limit")
                return
            for index in range(text.count_chars()):
                codepoint = pdfium.raw.FPDFText_GetUnicode(text, index)
                character = chr(codepoint) if codepoint <= 0x10FFFF else "\ufffd"
                characters.append(character)
                generated = pdfium.raw.FPDFText_IsGenerated(text, index)
                if character.isspace():
                    # Retain literal source whitespace only if its geometry assigns it uniquely.
                    if generated == 0:
                        box = text.get_charbox(index)
                        hits = [
                            i
                            for i, cell in enumerate(cells)
                            if valid_bbox(tuple(box), tuple(cell["bbox_pdf_user_space_points"]))
                        ]
                        if len(hits) == 1:
                            owners[index] = hits[0]
                    continue
                box = text.get_charbox(index)
                hits = [
                    i
                    for i, cell in enumerate(cells)
                    if intersects(box, cell["bbox_pdf_user_space_points"])
                ]
                if not hits:
                    continue
                reliable = (
                    len(hits) == 1
                    and generated == 0
                    and codepoint >= 32
                    and character.isprintable()
                    and character != "\ufffd"
                    and pdfium.raw.FPDFText_HasUnicodeMapError(text, index) == 0
                    and abs(pdfium.raw.FPDFText_GetCharAngle(text, index)) < 0.001
                    and valid_bbox(tuple(box), tuple(cells[hits[0]]["bbox_pdf_user_space_points"]))
                )
                (present if reliable else bad).update(hits)
                if reliable:
                    owners[index] = hits[0]
            for index, cell in enumerate(cells):
                if index in present and index not in bad:
                    selected = [i for i, owner in owners.items() if owner == index]
                    start, end = min(selected), max(selected) + 1
                    # Interior generated separators are inspectable; interleaved cells are not.
                    if any(
                        not characters[i].isspace() and owners.get(i) != index
                        for i in range(start, end)
                    ):
                        cell["text_status"] = "AMBIGUOUS_TEXT_ORDER"
                        continue
                    ambiguous_spacing = False
                    for i in range(start, end - 1):
                        if not characters[i].isspace() or characters[i + 1].isspace():
                            continue
                        space = text.get_charbox(i, loose=True)
                        following = text.get_charbox(i + 1, loose=True)
                        # PDFium may collapse repeated spaces. Never reconstruct their count.
                        if following[0] - space[2] > max(0.5, (space[2] - space[0]) * 0.2):
                            ambiguous_spacing = True
                    if ambiguous_spacing:
                        cell["text_status"] = "AMBIGUOUS_TEXT_SPACING"
                        continue
                    literal = "".join(characters[start:end])
                    if literal and "\ufffd" not in literal:
                        cell.update(
                            literal_text=literal, text_status="ORIGINAL_TEXT_LAYER_PROPOSAL"
                        )
                elif index in bad:
                    cell["text_status"] = "AMBIGUOUS_TEXT_CONTAINMENT_OR_MAPPING"


def intersects(a, b) -> bool:
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def check_cells(cells: list, bbox: list, rows: int, columns: int) -> None:
    """Validate reviewer corrections without deciding semantic completeness or truth."""
    if not isinstance(cells, list) or len(cells) != rows * columns:
        raise ValueError("Corrected proposal must cover the declared grid")
    seen = set()
    for cell in cells:
        row, column = cell["row"], cell["column"]
        box = cell["bbox_pdf_user_space_points"]
        if (
            type(row) is not int
            or type(column) is not int
            or not 0 <= row < rows
            or not 0 <= column < columns
            or (row, column) in seen
            or type(cell["row_span"]) is not int
            or type(cell["column_span"]) is not int
            or cell["row_span"] != 1
            or cell["column_span"] != 1
            or not isinstance(box, list)
            or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
            or not valid_bbox(tuple(box), tuple(bbox))
            or (cell["literal_text"] is not None and not isinstance(cell["literal_text"], str))
        ):
            raise ValueError("Corrected proposal cell rejected")
        seen.add((row, column))
    for index, cell in enumerate(cells):
        if any(
            intersects(cell["bbox_pdf_user_space_points"], other["bbox_pdf_user_space_points"])
            for other in cells[index + 1 :]
        ):
            raise ValueError("Corrected proposal cells overlap")
