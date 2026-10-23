"""Source-only checks of existing assertions and geometry; never human Gold.

The caller supplies frozen originals and existing proposal boxes. No geometry,
parser prediction, OCR transcript, formula result or semantic relationship is inferred.
"""

from __future__ import annotations

import math
import re
from contextlib import closing
from pathlib import Path

from PIL import Image, ImageStat

from doclens_ai.eda import corpus_v2 as corpus
from tools.extraction_quality import office_readiness_oracle as office
from tools.extraction_quality.pdf_cell_recovery import _boundaries, _rulings

VERSION = "readiness-source-checks-1.0"


def pdf_pages(path: Path, expected_sha256: str, pages: list[int]) -> dict:
    import pypdfium2 as pdfium

    corpus.no_links(path)
    if corpus.sha256(path) != expected_sha256 or path.stat().st_size > 50 * 1024**2:
        raise ValueError("PDF original identity or resource bound")
    if len(pages) != len(set(pages)) or len(pages) > 100:
        raise ValueError("PDF page selection rejected")
    result = {}
    with pdfium.PdfDocument(path.read_bytes()) as document:
        for number in pages:
            if type(number) is not int or not 1 <= number <= len(document):
                raise ValueError("PDF page outside original")
            with closing(document[number - 1]) as page, closing(page.get_textpage()) as text:
                if text.count_chars() > 200_000:
                    raise ValueError("source glyph budget")
                glyphs = []
                for index in range(text.count_chars()):
                    code = pdfium.raw.FPDFText_GetUnicode(text, index)
                    character = chr(code) if 0 < code <= 0x10FFFF else "\ufffd"
                    try:
                        box = list(text.get_charbox(index))
                    except Exception:
                        box = None
                    generated = pdfium.raw.FPDFText_IsGenerated(text, index)
                    mapping = pdfium.raw.FPDFText_HasUnicodeMapError(text, index)
                    angle = pdfium.raw.FPDFText_GetCharAngle(text, index)
                    glyphs.append(
                        {
                            "index": index,
                            "character": character,
                            "bbox": box,
                            "generated": generated,
                            "mapping_error": mapping,
                            "angle": angle,
                            "reliable": generated == 0
                            and mapping == 0
                            and abs(angle) < 0.001
                            and character != "\ufffd"
                            and box is not None
                            and all(math.isfinite(v) for v in box),
                        }
                    )
                result[number] = {
                    "page": number,
                    "width": page.get_width(),
                    "height": page.get_height(),
                    "rotation": page.get_rotation(),
                    "glyphs": glyphs,
                    "native_text": "".join(g["character"] for g in glyphs),
                }
    if corpus.sha256(path) != expected_sha256:
        raise ValueError("original changed during source check")
    return {
        "version": VERSION,
        "source_sha256": expected_sha256,
        "engine": "PDFium",
        "engine_version": str(pdfium.PYPDFIUM_INFO.version),
        "pages": result,
        "human_reviewed": False,
        "independent_gold": False,
    }


def contains(outer: list[float], inner: list[float]) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def intersects(left: list[float], right: list[float]) -> bool:
    return min(left[2], right[2]) > max(left[0], right[0]) and min(left[3], right[3]) > max(
        left[1], right[1]
    )


def union_box(glyphs: list[dict]) -> list[float] | None:
    boxes = [g["bbox"] for g in glyphs if not g["character"].isspace() and g["bbox"] is not None]
    if not boxes:
        return None
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def literal_matches(page: dict, literal: str) -> list[dict]:
    """Literal source glyph identity; empty string is never text evidence."""
    if not literal:
        return []
    text = page["native_text"]
    start, matches = 0, []
    while (index := text.find(literal, start)) >= 0:
        glyphs = page["glyphs"][index : index + len(literal)]
        matches.append(
            {
                "page": page["page"],
                "char_start": index,
                "char_end": index + len(literal),
                "bbox": union_box(glyphs),
                "literal": literal,
                "nonspace_glyphs_reliable": all(
                    g["reliable"] for g in glyphs if not g["character"].isspace()
                ),
                "generated_whitespace": any(
                    g["generated"] != 0 for g in glyphs if g["character"].isspace()
                ),
            }
        )
        start = index + len(literal)
    return matches


def cell_check(page: dict, proposal: dict, rules: list[dict], raster: Image.Image) -> dict:
    box = proposal["bbox"]
    if (
        len(box) != 4
        or not all(type(v) in (int, float) and math.isfinite(v) for v in box)
        or not 0 <= box[0] < box[2] <= page["width"]
        or not 0 <= box[1] < box[3] <= page["height"]
        or page["rotation"] != 0
        or any(
            type(proposal.get(k)) is not int or proposal[k] < 1 for k in ("row_span", "column_span")
        )
    ):
        raise ValueError("existing cell geometry rejected")
    sides, issues = _boundaries(box, rules)
    present = [
        g
        for g in page["glyphs"]
        if not g["character"].isspace() and g["bbox"] is not None and intersects(box, g["bbox"])
    ]
    owned = [g for g in present if contains(box, g["bbox"])]
    unknown_geometry = any(
        g["bbox"] is None for g in page["glyphs"] if not g["character"].isspace()
    )
    reliable = (
        not unknown_geometry and len(owned) == len(present) and all(g["reliable"] for g in present)
    )
    compact = "".join(g["character"] for g in owned)
    proposed = proposal["proposed_text"]
    # A strictly uniform interior is a raster observation, not a proof of a logical blank cell.
    xscale, yscale = raster.width / page["width"], raster.height / page["height"]
    inset = 2.0
    bounds = [
        math.ceil((box[0] + inset) * xscale),
        math.ceil((page["height"] - box[3] + inset) * yscale),
        math.floor((box[2] - inset) * xscale),
        math.floor((page["height"] - box[1] - inset) * yscale),
    ]
    uniform = None
    if bounds[0] < bounds[2] and bounds[1] < bounds[3]:
        interior = raster.crop(tuple(bounds)).convert("RGB")
        statistics = ImageStat.Stat(interior)
        uniform = all(v == 0 for v in statistics.var) and statistics.mean == [255, 255, 255]
    if proposed == "":
        state = (
            "CONFLICT_VISIBLE_SOURCE_GLYPHS"
            if present
            else "SOURCE_EMPTY_INTERIOR_SUPPORTED"
            if uniform is True and not issues and reliable
            else "BLANK_UNRESOLVED"
        )
    else:
        same = compact == "".join(c for c in proposed if not c.isspace())
        state = (
            "SOURCE_VISIBLE_LITERAL_SUPPORTED"
            if same and reliable
            else "SOURCE_LITERAL_CONFLICT"
            if reliable and present
            else "SOURCE_LITERAL_UNRESOLVED"
        )
    return {
        "item_id": proposal["item_id"],
        "page": page["page"],
        "bbox": box,
        "proposed_text": proposed,
        "observed_nonspace_literal": compact,
        "glyph_indices": [g["index"] for g in owned],
        "reliable_unique_ownership": reliable,
        "boundary_source_objects": sides,
        "boundary_issues": sorted(issues),
        "raster_interior_uniform": uniform,
        "raster_inset_pdf_points": inset,
        "state": state,
        "span_state": "PROPOSED_LOGICAL_SPAN_NOT_CERTIFIED",
        "semantic_links": "NOT_EVALUATED",
        "correction": None,
        "limitations": [
            "not_human_review",
            "not_exact_spacing_or_font_semantics",
            "logical_grid_and_blank_meaning_require_review",
        ],
        "human_reviewed": False,
        "independent_gold": False,
    }


def pdf_cells(path: Path, sha256: str, proposals: list[dict], raster_path: Path) -> dict:
    page_numbers = sorted({p["page"] for p in proposals})
    if page_numbers != [1]:
        raise ValueError("existing single-page raster binding required")
    source = pdf_pages(path, sha256, page_numbers)
    corpus.no_links(raster_path)
    with Image.open(raster_path) as image:
        image.load()
        rules = _rulings(path.read_bytes(), 1)
        results = [cell_check(source["pages"][1], proposal, rules, image) for proposal in proposals]
    return {
        "version": VERSION,
        "source_sha256": sha256,
        "raster_sha256": corpus.sha256(raster_path),
        "geometry_regenerated": False,
        "cells": results,
        "source": source,
        "human_reviewed": False,
        "independent_gold": False,
    }


def resolve_xml(root, locator: dict):
    """Resolve our namespace-qualified physical path against the unchanged original."""
    nodes = locator["xml_path"].strip("/").split("/")
    namespaces = locator.get("namespaces", {})
    current = root
    for depth, component in enumerate(nodes):
        match = re.fullmatch(r"([\w:.-]+)\[([1-9][0-9]*)\]", component)
        if not match:
            raise ValueError("physical XML path rejected")
        name, index = match[1], int(match[2])
        if ":" in name:
            prefix, name = name.split(":", 1)
            name = "{" + namespaces[prefix] + "}" + name
        if depth == 0:
            if current.tag != name or index != 1:
                raise ValueError("physical XML root mismatch")
        else:
            children = [n for n in current if n.tag == name]
            if index > len(children):
                raise ValueError("physical XML path missing in original")
            current = children[index - 1]
    return current


def docx_literal(path: Path, sha256: str, literal: str) -> dict:
    value = office.observe(path, "source-check", sha256, "docx")
    matches = []
    with office.Package(path) as package:
        for part in value["observations"]["parts"].values():
            for node in part["elements"]:
                if node["kind"] != "p" or literal not in node["native_t_text"]:
                    continue
                locator = node["locator"]
                original = resolve_xml(package.xml(locator["part"]), locator)
                observed = "".join(n.text or "" for n in original.iter("{" + office.W + "}t"))
                if observed != node["native_t_text"]:
                    raise ValueError("source path/text binding mismatch")
                matches.append(
                    {
                        "locator": locator,
                        "observed": observed,
                        "char_start": observed.index(literal),
                        "literal": literal,
                    }
                )
    return {
        "source_sha256": sha256,
        "matches": matches,
        "human_reviewed": False,
        "independent_gold": False,
        "method": "original_OOXML_namespace_qualified_element",
    }
