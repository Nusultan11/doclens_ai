"""Explicit local machine-assisted PDF drafts; never independent human Gold.

Geometry and document-specific partitions are hash-pinned private plan inputs.
Original text/rulings are re-read; existing review validators remain authoritative.
"""

from __future__ import annotations

import argparse
import copy
import csv
import html
import importlib.metadata
import io
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from pypdf import PdfReader

from doclens_ai.eda.corpus_v2 import read_json
from doclens_ai.extraction.evidence_v2 import Cell, Locator, Table, valid_bbox
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import pdf_cell_recovery as recovery
from tools.extraction_quality import pdf_grid_proposals as grids
from tools.extraction_quality import pdf_review_validation as review
from tools.extraction_quality import pdf_review_workbench as workbench
from tools.extraction_quality import pdf_table_review_packet as packet

METHOD = "pdf-assisted-review-v1"
ASSETS = Path(__file__).with_name("pdf_assisted_ui")


def load_plan(path: Path, expected_sha256: str, selected: set[str]) -> dict:
    """Plans contain private geometry, not source literals or human attestations."""
    if packet.sha(path) != expected_sha256:
        raise ValueError("Geometry plan SHA mismatch")
    plan = read_json(path, max_bytes=2 * 1024**2)
    if set(plan) != {"version", "documents"} or plan["version"] != "pdf-assisted-plan-v1":
        raise ValueError("Unsupported geometry plan")
    if set(plan["documents"]) != selected or not 0 < len(selected) <= 16:
        raise ValueError("Geometry plan admission population mismatch")
    for key, recipe in plan["documents"].items():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", key):
            raise ValueError("Unsafe document identity")
        if set(recipe) != {
            "source_sha256",
            "pages",
            "header_row",
            "language",
            "tables",
            "partitions",
        }:
            raise ValueError("Unsupported document plan fields")
        if type(recipe["header_row"]) is not int or not 0 <= recipe["header_row"] <= 255:
            raise ValueError("Invalid header row proposal")
        if recipe["language"] not in {"en", "ru", "kk", None}:
            raise ValueError("Unsupported language proposal")
        if not 0 < len(recipe["tables"]) <= 64:
            raise ValueError("Geometry table limit")
        table_ids = [t["table_id"] for t in recipe["tables"]]
        if len(table_ids) != len(set(table_ids)):
            raise ValueError("Duplicate geometry table identity")
        for table in recipe["tables"]:
            if set(table) != {
                "table_id",
                "bbox",
                "row_count",
                "column_count",
                "cells",
                "region_kind",
                "counting_convention",
            }:
                raise ValueError("Unsupported table plan fields")
            rows, columns = table["row_count"], table["column_count"]
            if (
                type(rows) is not int
                or type(columns) is not int
                or not 1 <= rows <= 256
                or not 1 <= columns <= 64
                or rows * columns > 2048
            ):
                raise ValueError("Logical geometry grid limit")
            if not 0 < len(table["cells"]) <= 2048 or any(
                set(c) != set(recovery.GEOMETRY_FIELDS) for c in table["cells"]
            ):
                raise ValueError("Geometry-only bounded cells required")
            for cell in table["cells"]:
                Cell(
                    cell_id=cell["review_cell_id"],
                    literal="",
                    row=cell["row"],
                    column=cell["column"],
                    row_span=cell["row_span"],
                    column_span=cell["column_span"],
                    role=None,
                    locator=Locator(
                        page=1,
                        bbox=tuple(cell["bbox_pdf_user_space_points"]),
                        coordinate_basis="pdf_user_space_unrotated",
                    ),
                )
                if (
                    cell["row"] + cell["row_span"] > rows
                    or cell["column"] + cell["column_span"] > columns
                ):
                    raise ValueError("Geometry span outside declared grid")
        parts = recipe["partitions"]
        if len({p["table_id"] for p in parts}) != len(parts):
            raise ValueError("At most one partition per single-row band")
        for part in parts:
            if set(part) != {
                "table_id",
                "cell_id",
                "expected_bbox",
                "split_x",
                "new_cell_id",
                "fill_object_index",
                "expected_fill_bbox",
                "counting_convention",
            }:
                raise ValueError("Unsupported partition plan fields")
            if part["table_id"] not in table_ids:
                raise ValueError("Partition table missing")
    return plan["documents"]


def partition_evidence(source: Path, rules: list[dict], part: dict) -> dict:
    """Never convert an unruled requested partition into a printed source divider."""
    index = part["fill_object_index"]
    if type(index) is not int or not 0 <= index < 10_000:
        raise ValueError("Source fill object limit")
    with pdfium.PdfDocument(source) as document:
        page = document[0]
        objects = list(page.get_objects())
        if index >= len(objects) or objects[index].type != pdfium.raw.FPDF_PAGEOBJ_PATH:
            raise ValueError("Source fill object missing")
        box = list(objects[index].get_bounds())
        if box != part["expected_fill_bbox"]:
            raise ValueError("Source fill geometry mismatch")
        split = part["split_x"]
        if not min(abs(box[0] - split), abs(box[2] - split)) <= recovery.MAX_RULE_WIDTH:
            raise ValueError("Requested partition does not align with fill extent")
        aligned = [
            r["source_object_index"]
            for r in rules
            if r["axis"] == "v" and abs(r["position"] - split) < 0.001
        ]
        if not aligned:
            raise ValueError("Requested partition lacks original column alignment")
        page.close()
    return dict(
        source_sha256=packet.sha(source),
        page=1,
        source_path_object_index=index,
        measured_fill_bbox=box,
        requested_partition_x=split,
        aligned_lower_ruling_objects=aligned,
        basis=(
            "User-requested segmentation aligned with the fill extent and lower grid; "
            "no printed vertical ruling in this band"
        ),
        printed_vertical_divider_present=False,
        semantic_interpretation=None,
    )


def geometry(source: Path, identity: dict, recipe: dict) -> tuple[list[dict], list[dict]]:
    if packet.sha(source) != recipe["source_sha256"] or recipe["pages"] != [identity]:
        raise ValueError("Geometry plan source/page mismatch")
    rules = recovery._rulings(source.read_bytes(), 1)
    tables = copy.deepcopy(recipe["tables"])
    for part in recipe["partitions"]:
        table = next(t for t in tables if t["table_id"] == part["table_id"])
        cell = next(c for c in table["cells"] if c["review_cell_id"] == part["cell_id"])
        box = cell["bbox_pdf_user_space_points"]
        split = part["split_x"]
        if (
            table["row_count"] != 1
            or cell["row"] != 0
            or cell["row_span"] != 1
            or cell["column_span"] != 1
            or box != part["expected_bbox"]
            or type(split) not in (int, float)
            or not math.isfinite(split)
            or not box[0] < split < box[2]
        ):
            raise ValueError("Requested single-row partition rejected")
        new = copy.deepcopy(cell)
        new.update(
            review_cell_id=part["new_cell_id"],
            column=cell["column"] + 1,
            bbox_pdf_user_space_points=[split, box[1], box[2], box[3]],
        )
        for other in table["cells"]:
            if other["column"] > cell["column"]:
                other["column"] += 1
        box[2] = split
        table["cells"].insert(table["cells"].index(cell) + 1, new)
        table["column_count"] += 1
        table["segmentation_evidence"] = partition_evidence(source, rules, part)
        table["counting_convention"] = copy.deepcopy(part["counting_convention"])
    return tables, rules


def boundary_evidence(
    table: dict, cell: dict, rules: list[dict], recipe: dict
) -> tuple[list, dict | None]:
    refs, errors = recovery._boundaries(cell["bbox_pdf_user_space_points"], rules)
    parts = [
        p
        for p in recipe["partitions"]
        if p["table_id"] == table["table_id"]
        and cell["review_cell_id"] in (p["cell_id"], p["new_cell_id"])
    ]
    if not parts:
        if errors:
            raise ValueError("Unverified original physical cell geometry")
        return refs, None
    part = parts[0]
    missing = 3 if cell["review_cell_id"] == part["cell_id"] else 2
    if (
        errors != {"PHYSICAL_CELL_BOUNDARY_NOT_VERIFIED"}
        or refs[missing]
        or any(not side for i, side in enumerate(refs) if i != missing)
    ):
        raise ValueError("Requested unruled partition or original outer boundaries mismatch")
    return refs, dict(
        table["segmentation_evidence"], unruled_side="right" if missing == 3 else "left"
    )


MONTHS = {"June", "Aug", "April", "July", "Dec", "Jan", "March", "Nov", "Oct", "Sep", "Feb", "May"}
FIELDS = [
    "item_id",
    "kind",
    "source_id",
    "source_sha256",
    "page",
    "bbox",
    "table_id",
    "row",
    "column",
    "row_span",
    "column_span",
    "proposed_text",
    "proposed_value_json",
    "machine_support",
    "uncertainty",
    "decision",
    "reviewer_correction",
    "corrected_bbox",
    "reviewer_notes",
]
DECISION_FIELDS = ("decision", "reviewer_correction", "corrected_bbox", "reviewer_notes")


def read(path):
    return read_json(path)


def write(path, value):
    packet.write_json(path, value)


def bounds(boxes):
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def observations(source, identity):
    """Retain both engines' actual characters and bounds; never clip glyphs."""
    glyphs = []
    with pdfium.PdfDocument(source) as doc:
        page = doc[0]
        assert all(
            abs(a - b) < 0.001
            for a, b in zip(page.get_bbox(), identity["crop_box_pdf_user_space"], strict=True)
        )
        width, height = page.get_size()
        if max(width, height) > 1500 or width * height * 4 > 9_000_000:
            raise ValueError("Original raster limit")
        text = page.get_textpage()
        if text.count_chars() > 200_000:
            raise ValueError("Original glyph limit")
        for i in range(text.count_chars()):
            code = pdfium.raw.FPDFText_GetUnicode(text, i)
            glyphs.append(
                dict(
                    index=i,
                    text=chr(code),
                    bbox=list(text.get_charbox(i)),
                    generated=pdfium.raw.FPDFText_IsGenerated(text, i),
                    mapping_error=pdfium.raw.FPDFText_HasUnicodeMapError(text, i),
                    angle=pdfium.raw.FPDFText_GetCharAngle(text, i),
                )
            )
        text.close()
        bitmap = page.render(
            scale=2,
            may_draw_forms=False,
            force_bitmap_format=pdfium.raw.FPDFBitmap_BGR,
            rev_byteorder=True,
        )
        assert bitmap.mode == "RGB"
        converter = bitmap.get_posconv(page)
        crop = identity["crop_box_pdf_user_space"]
        for pixel, expected in (
            ((0, 0), (crop[0], crop[3])),
            ((bitmap.width, bitmap.height), (crop[2], crop[1])),
        ):
            assert all(
                abs(a - b) < 0.001 for a, b in zip(converter.to_page(*pixel), expected, strict=True)
            )
        image = Image.open(io.BytesIO(workbench.rgb_png(bitmap))).convert("RGB")
        assert abs(image.width / 2 - page.get_width()) < 0.51
        assert abs(image.height / 2 - page.get_height()) < 0.51
        bitmap.close()
        page.close()
    with pdfplumber.open(source) as pdf:
        page = pdf.pages[0]
        if len(page.chars) > 200_000:
            raise ValueError("Alternate original glyph limit")
        chars = [
            dict(
                index=i,
                text=c["text"],
                bbox=[c["x0"], page.height - c["bottom"], c["x1"], page.height - c["top"]],
            )
            for i, c in enumerate(page.chars)
        ]
        detected = [
            dict(
                bbox=list(t.bbox), rows=[[list(c) if c else None for c in r.cells] for r in t.rows]
            )
            for t in page.find_tables()
        ]
        images = len(page.images)
    return dict(
        pdfium=glyphs, pdfplumber=chars, plumber_detected_tables=detected, image_objects=images
    ), image


def text_for(cells, source, obs, image, identity):
    diagnostics = {}
    candidate = dict(cells=copy.deepcopy(cells), issues=[])
    for c in candidate["cells"]:
        c.update(literal_text=None, text_status="NO_RELIABLE_TEXT")
    grids.add_text(source, 1, candidate, diagnostics=diagnostics)
    crop = identity["crop_box_pdf_user_space"]
    sx = image.width / (crop[2] - crop[0])
    sy = image.height / (crop[3] - crop[1])
    for cell, builtin, diag in zip(cells, candidate["cells"], diagnostics["cells"], strict=True):
        box = cell["bbox_pdf_user_space_points"]
        selected = {}
        crossing = {}
        for engine in ("pdfium", "pdfplumber"):
            selected[engine] = [
                g
                for g in obs[engine]
                if valid_bbox(tuple(g["bbox"]), tuple(box))
                and (engine != "pdfium" or g["generated"] == 0)
            ]
            crossing[engine] = [
                g["index"]
                for g in obs[engine]
                if g["text"].isprintable()
                and not g["text"].isspace()
                and grids.intersects(g["bbox"], box)
                and not valid_bbox(tuple(g["bbox"]), tuple(box))
            ]
        second = "".join(g["text"] for g in selected["pdfplumber"])
        first = builtin["literal_text"]
        uncertain = []
        if first is not None:
            literal = first
            engine = "pdfium"
            status = "ORIGINAL_TEXT_LAYER_PROPOSAL"
        elif second and not crossing["pdfplumber"]:
            literal = second
            engine = "pdfplumber"
            status = "ALTERNATE_SOURCE_GLYPH_PROPOSAL"
            uncertain.append("PDFIUM_CONSERVATIVE_TEXT_UNRESOLVED")
        elif not second and not crossing["pdfplumber"] and not crossing["pdfium"]:
            literal = ""
            engine = "both"
            status = "EMPTY_TEXT_LAYER_CELL"
            left, b, r, t = box
            interior = image.crop(
                (
                    math.ceil((left - crop[0] + 2) * sx),
                    math.ceil((crop[3] - t + 2) * sy),
                    math.floor((r - crop[0] - 2) * sx),
                    math.floor((crop[3] - b - 2) * sy),
                )
            )
            if any(max(px) < 150 for px in interior.get_flattened_data()):
                literal = None
                status = "RASTER_MARK_WITHOUT_TEXT"
                uncertain.append(status)
        else:
            literal = None
            engine = None
            status = "UNRESOLVED_SOURCE_TEXT"
            uncertain.append(status)
        if first is not None and first != second:
            uncertain.append("ENGINE_LITERAL_OR_SPACING_DISAGREEMENT")
        if crossing["pdfplumber"]:
            uncertain.append("PDFPLUMBER_GLYPH_CROSSES_PHYSICAL_CELL")
        # Keep exact alternative strings; never normalize the chosen literal.
        cell.update(
            literal_text=literal,
            text_engine=engine,
            text_status=status,
            source_glyph_indices={e: [g["index"] for g in selected[e]] for e in selected},
            crossing_glyph_indices=crossing,
            alternate_text=second,
            pdfium_literal=first,
            pdfium_diagnostics=diag,
            uncertainty=sorted(set(uncertain)),
            numeric_observation=None,
        )
        if literal is not None and re.fullmatch(r"£[-+]?\d+(?:\.\d+)?", literal):
            number = literal[1:]
            cell["numeric_observation"] = dict(
                printed_literal=literal,
                lexical_number=number,
                decimal_value=str(Decimal(number)),
                printed_unit_symbol="£",
                currency_code=None,
                fraction_digits=len(number.split(".")[1]) if "." in number else 0,
                formula=None,
                stored_spreadsheet_value=None,
            )
    return diagnostics


def anchors(obs):
    stream = "".join(g["text"] for g in obs["pdfium"])
    result = []
    for m in re.finditer(r"[^\r\n]+", stream):
        glyphs = [
            g
            for g in obs["pdfium"][m.start() : m.end()]
            if g["text"].isprintable() and not g["text"].isspace() and valid_bbox(tuple(g["bbox"]))
        ]
        if not glyphs:
            continue
        result.append(
            dict(
                character_range=[m.start(), m.end()],
                literal_text=m.group(),
                bbox=bounds([g["bbox"] for g in glyphs]),
                source_glyph_indices=[g["index"] for g in glyphs],
                generated_separator_indices=[
                    g["index"] for g in obs["pdfium"][m.start() : m.end()] if g["generated"] != 0
                ],
                uncertainty=["NATIVE_CHARACTER_STREAM_ORDER_NOT_SEMANTIC_READING_ORDER"]
                + (
                    ["GENERATED_SEPARATORS_PRESENT"]
                    if any(g["generated"] != 0 for g in obs["pdfium"][m.start() : m.end()])
                    else []
                ),
            )
        )
    return result


def propose(key: str, source: Path, eligibility: dict, recipe: dict) -> tuple[dict, Image.Image]:
    sha = packet.sha(source)
    identity = review.original_pages(source)
    assert len(identity) == 1 and identity == eligibility["pages"]
    assert (
        sha == eligibility["source_sha256"]
        and source.stat().st_size == eligibility["source_size_bytes"]
    )
    page = PdfReader(source).pages[0]
    assert page.rotation == 0 and page.get("/UserUnit", 1) == 1
    obs, image = observations(source, identity[0])
    tables, rules = geometry(source, identity[0], recipe)
    for table in tables:
        table["text_diagnostics"] = text_for(table["cells"], source, obs, image, identity[0])
        for cell in table["cells"]:
            refs, segmentation = boundary_evidence(table, cell, rules, recipe)
            cell["physical_boundary_objects"] = refs
            if segmentation is not None:
                cell.update(
                    segmentation_evidence=segmentation,
                    semantic_interpretation=None,
                    boundary_status="REQUESTED_UNRULED_SEGMENTATION_NOT_PHYSICAL_DIVIDER",
                )
                cell["uncertainty"].append("UNRULED_SEGMENT_INTERPRETATION_UNKNOWN")
    return dict(
        document_id=key,
        sha256=sha,
        size_bytes=source.stat().st_size,
        pages=identity,
        coordinate_basis="pdf_user_space_unrotated",
        user_unit=1,
        pdf_encrypted=False,
        annotation_use_authorized=True,
        observations=obs,
        original_rulings=rules,
        tables=tables,
        text_anchors=anchors(obs),
        language_proposal=dict(
            value=recipe["language"], uncertainty=["LEXICAL_LANGUAGE_PROPOSAL_NOT_HUMAN_REVIEWED"]
        ),
        family_proposal=dict(
            value=eligibility["family_id"],
            basis="Verified acquisition source-page grouping",
            uncertainty=["FAMILY_COMPLETENESS_NOT_REVIEWED"],
        ),
        attribution=eligibility["attribution"],
        publisher=eligibility["publisher"],
        source_page_url=eligibility["source_page_url"],
        download_url=eligibility["download_url"],
    ), image


def validate_document(doc: dict, source: Path, recipe: dict) -> dict:
    """Mechanical source consistency only; a proposal validator, never a Gold validator."""
    if packet.sha(source) != doc["sha256"]:
        raise ValueError("Source SHA mismatch")
    pages = review.original_pages(source)
    if doc["pages"] != pages or len(pages) != 1:
        raise ValueError("Wrong source page")
    if pages[0]["rotation"] != 0 or doc["user_unit"] != 1:
        raise ValueError("Unsupported coordinate transform")
    fresh, _ = observations(source, pages[0])
    if doc["observations"] != fresh:
        raise ValueError("Incomplete or changed source observations")
    fresh_rules = recovery._rulings(source.read_bytes(), 1)
    if fresh_rules != doc["original_rulings"]:
        raise ValueError("Changed original ruling observations")
    expected_tables, _ = geometry(source, pages[0], recipe)
    if len(expected_tables) != len(doc["tables"]):
        raise ValueError("Geometry plan population mismatch")
    for expected, actual in zip(expected_tables, doc["tables"], strict=True):
        for field in (
            "table_id",
            "bbox",
            "row_count",
            "column_count",
            "region_kind",
            "counting_convention",
        ):
            if expected[field] != actual[field]:
                raise ValueError("Geometry plan table mismatch")
        if expected.get("segmentation_evidence") != actual.get("segmentation_evidence"):
            raise ValueError("Partition source evidence mismatch")
        if len(expected["cells"]) != len(actual["cells"]):
            raise ValueError("Geometry plan cell mismatch")
        for target, cell in zip(expected["cells"], actual["cells"], strict=True):
            if any(target[k] != cell[k] for k in recovery.GEOMETRY_FIELDS):
                raise ValueError("Geometry plan cell mismatch")
    crop = tuple(pages[0]["crop_box_pdf_user_space"])
    ids = set()
    assignments = {e: set() for e in ("pdfium", "pdfplumber")}
    issues = []
    for table in doc["tables"]:
        if not valid_bbox(tuple(table["bbox"]), crop):
            raise ValueError("Invalid table coordinates")
        occupied = set()
        models = []
        for cell in table["cells"]:
            cid = cell["review_cell_id"]
            box = cell["bbox_pdf_user_space_points"]
            if cid in ids:
                raise ValueError("Duplicate cell identity")
            ids.add(cid)
            if not valid_bbox(tuple(box), tuple(table["bbox"])):
                raise ValueError("Invalid cell coordinates")
            refs, segmentation = boundary_evidence(table, cell, doc["original_rulings"], recipe)
            if refs != cell["physical_boundary_objects"]:
                raise ValueError("Cell boundary evidence changed")
            if segmentation is not None:
                if (
                    cell.get("segmentation_evidence") != segmentation
                    or cell.get("semantic_interpretation") is not None
                ):
                    raise ValueError("Unverified segment meaning or evidence")
                if segmentation["unruled_side"] == "left" and (
                    cell["literal_text"] != "" or any(cell["source_glyph_indices"].values())
                ):
                    raise ValueError("Rightmost year segment must remain source-empty")
            slots = {
                (r, c)
                for r in range(cell["row"], cell["row"] + cell["row_span"])
                for c in range(cell["column"], cell["column"] + cell["column_span"])
            }
            if (
                not slots
                or occupied & slots
                or any(r >= table["row_count"] or c >= table["column_count"] for r, c in slots)
            ):
                raise ValueError("Overlapping or invalid row-column assignments")
            occupied |= slots
            literal = cell["literal_text"]
            for engine, indices in cell["source_glyph_indices"].items():
                if assignments[engine] & set(indices):
                    raise ValueError("Duplicate source glyph assignment")
                assignments[engine].update(indices)
                if any(
                    not valid_bbox(tuple(fresh[engine][i]["bbox"]), tuple(box)) for i in indices
                ):
                    raise ValueError("Glyph outside source cell")
            second = "".join(
                g["text"] for g in fresh["pdfplumber"] if valid_bbox(tuple(g["bbox"]), tuple(box))
            )
            if cell["alternate_text"] != second:
                raise ValueError("Incomplete source cell text")
            if cell["text_engine"] == "pdfplumber" and literal != second:
                raise ValueError("Changed source literal")
            if cell["text_engine"] == "pdfium":
                nonspace = [
                    i
                    for i in cell["source_glyph_indices"]["pdfium"]
                    if not fresh["pdfium"][i]["text"].isspace()
                ]
                if not nonspace:
                    raise ValueError("Missing source literal glyphs")
                start, end = min(nonspace), max(nonspace) + 1
                native = "".join(g["text"] for g in fresh["pdfium"][start:end])
                if literal != native:
                    raise ValueError("Incomplete source cell text")
            number = cell["numeric_observation"]
            if number is not None and (
                literal != number["printed_unit_symbol"] + number["lexical_number"]
                or str(Decimal(number["lexical_number"])) != number["decimal_value"]
            ):
                raise ValueError("Numeric source mismatch")
            models.append(
                Cell(
                    cell_id=cid,
                    literal=literal or "",
                    row=cell["row"],
                    column=cell["column"],
                    row_span=cell["row_span"],
                    column_span=cell["column_span"],
                    role=None,
                    locator=Locator(
                        page=1, bbox=tuple(box), coordinate_basis="pdf_user_space_unrotated"
                    ),
                )
            )
        if occupied != {
            (r, c) for r in range(table["row_count"]) for c in range(table["column_count"])
        }:
            raise ValueError("Missing physical cells")
        Table(
            table_id=table["table_id"],
            cells=tuple(models),
            relations=(),
            section_id=None,
            complete=False,
            unresolved=("MACHINE_ASSISTED_NOT_REVIEWED",),
        )
        # Reuse proposal/adjudication binding without supplying review decisions.
        context = dict(
            document_id=doc["document_id"],
            source_sha256=doc["sha256"],
            page_identity=pages[0],
            review_table_id=table["table_id"],
            rows=table["row_count"],
            columns=table["column_count"],
            bbox=table["bbox"],
        )
        candidate = dict(
            method=METHOD, status="MACHINE_ASSISTED_NOT_REVIEWED", cells=table["cells"]
        )
        proposal = dict(context=context, candidate=candidate, cells=table["cells"])
        proposal["proposal_id"] = fingerprint({k: proposal[k] for k in ("context", "candidate")})
        unsigned = review.proposal_review(
            proposal, dict(document_id=doc["document_id"], sha256=doc["sha256"]), pages
        )
        assert all(
            d["decision"] is None and d["reviewer_id"] is None for d in unsigned["decisions"]
        )
    for i, table in enumerate(doc["tables"]):
        if any(grids.intersects(table["bbox"], other["bbox"]) for other in doc["tables"][i + 1 :]):
            raise ValueError("Overlapping physical table regions")
    for engine, used in assignments.items():
        required = {
            g["index"]
            for g in fresh[engine]
            if g["text"].isprintable()
            and not g["text"].isspace()
            and (engine != "pdfium" or g["generated"] == 0)
            and any(grids.intersects(g["bbox"], t["bbox"]) for t in doc["tables"])
        }
        missing = required - used
        if missing:
            issues.append(
                dict(code="UNASSIGNED_TABLE_GLYPHS", engine=engine, indices=sorted(missing))
            )
    result = dict(
        source_identity="PASS",
        pages="PASS",
        geometry="PASS",
        grid_coverage="PASS",
        exact_literal_correspondence="PASS",
        numeric_correspondence="PASS",
        duplicate_assignments="PASS",
        existing_proposal_validator="PASS",
        unassigned_glyph_diagnostics=issues,
        human_review_completed=False,
    )
    if recipe["partitions"]:
        result["requested_segmentation"] = (
            "REQUESTED_PARTITION_VALIDATED_WITH_UNRULED_BOUNDARY_DISCLOSED"
        )
    return result


def item(kind, key, page, value, box=None, uncertainty=None, text="", table=None, cell=None):
    result = dict(
        item_id=key,
        kind=kind,
        page=page,
        bbox=box,
        proposed_value=value,
        proposed_text=text,
        uncertainty=uncertainty or [],
        machine_support="uncertain" if uncertainty else "source_observed",
        decision=None,
        reviewer_correction=None,
        reviewer_id=None,
    )
    if table:
        result["table_id"] = table["table_id"]
    if cell:
        result.update({k: cell[k] for k in ("row", "column", "row_span", "column_span")})
    return result


def items_for(doc: dict, header_row: int) -> list[dict]:
    key = doc["document_id"]
    items = []
    items.append(
        item(
            "table_presence",
            key + "-p1-presence",
            1,
            True,
            doc["pages"][0]["crop_box_pdf_user_space"],
        )
    )
    for kind in ("language", "family"):
        value = doc[kind + "_proposal"]
        items.append(item(kind, key + "-" + kind, 1, value, uncertainty=value["uncertainty"]))
    for ti, table in enumerate(doc["tables"]):
        prefix = f"{key}-p1-t{ti}"
        items.append(
            item(
                "table",
                prefix,
                1,
                {
                    k: table[k]
                    for k in ("row_count", "column_count", "region_kind", "counting_convention")
                },
                table["bbox"],
                ["PHYSICAL_REGION_COUNTING_CONVENTION_REQUIRES_REVIEW"],
                table=table,
            )
        )
        for cell in table["cells"]:
            cid = prefix + f"-r{cell['row']}-c{cell['column']}"
            cell["item_id"] = cid
            value = {
                k: cell[k]
                for k in (
                    "literal_text",
                    "row",
                    "column",
                    "row_span",
                    "column_span",
                    "bbox_pdf_user_space_points",
                    "numeric_observation",
                    "text_engine",
                    "text_status",
                )
            }
            if "segmentation_evidence" in cell:
                value.update(
                    segmentation_evidence=cell["segmentation_evidence"],
                    semantic_interpretation=None,
                    boundary_status=cell["boundary_status"],
                )
            items.append(
                item(
                    "cell",
                    cid,
                    1,
                    value,
                    cell["bbox_pdf_user_space_points"],
                    cell["uncertainty"],
                    cell["literal_text"] if cell["literal_text"] is not None else "[UNKNOWN]",
                    table,
                    cell,
                )
            )
            role = None
            if cell["literal_text"]:
                if table["region_kind"] == "header_only_ruled_band":
                    role = "period"
                elif cell["row"] == header_row:
                    role = "column_header"
                elif cell["numeric_observation"]:
                    role = "value"
                elif cell["column"] == 0:
                    role = "row_header_or_caption"
            if role:
                items.append(
                    item(
                        "role",
                        cid + "-role",
                        1,
                        dict(cell_id=cid, role=role),
                        cell["bbox_pdf_user_space_points"],
                        ["SEMANTIC_ROLE_HYPOTHESIS_FROM_LITERAL_AND_GRID"],
                        role,
                        table,
                        cell,
                    )
                )
        for cell in table["cells"]:
            if not cell["numeric_observation"]:
                continue
            unit = dict(
                cell_id=cell["item_id"],
                printed_symbol=cell["numeric_observation"]["printed_unit_symbol"],
                currency_code=None,
                basis="Exact printed literal prefix; no currency-code inference",
            )
            items.append(
                item(
                    "printed_unit",
                    cell["item_id"] + "-printed-unit",
                    1,
                    unit,
                    cell["bbox_pdf_user_space_points"],
                    cell["uncertainty"],
                    unit["printed_symbol"],
                    table,
                )
            )
            header = [
                h
                for h in table["cells"]
                if h["row"] == header_row
                and h["column"] <= cell["column"] < h["column"] + h["column_span"]
            ]
            if len(header) != 1:
                continue
            h = header[0]
            relation = dict(
                left=cell["item_id"],
                right=h["item_id"],
                relationship="column_header",
                basis="Shared original ruled column; semantic hypothesis, not approval",
                unit=None,
                period_scope=None,
            )
            items.append(
                item(
                    "relationship",
                    cell["item_id"] + "-header-link",
                    1,
                    relation,
                    cell["bbox_pdf_user_space_points"],
                    ["HEADER_VALUE_RELATIONSHIP_REQUIRES_REVIEW"],
                    table=table,
                )
            )
            if h["literal_text"] in MONTHS:
                relation = dict(
                    relation,
                    relationship="period",
                    basis="Printed month in shared ruled column; year scope unknown",
                )
                items.append(
                    item(
                        "relationship",
                        cell["item_id"] + "-period-link",
                        1,
                        relation,
                        cell["bbox_pdf_user_space_points"],
                        ["MONTH_SCOPE_AND_YEAR_ASSOCIATION_UNVERIFIED"],
                        table=table,
                    )
                )
        order = [
            c["item_id"] for c in sorted(table["cells"], key=lambda c: (c["row"], c["column"]))
        ]
        items.append(
            item(
                "reading_order",
                prefix + "-order",
                1,
                dict(cell_ids=order, basis="Physical row-major proposal"),
                table["bbox"],
                ["SEMANTIC_READING_ORDER_UNVERIFIED"],
                table=table,
            )
        )
    for i, anchor in enumerate(doc["text_anchors"]):
        items.append(
            item(
                "text_anchor",
                key + f"-p1-anchor-{i:03d}",
                1,
                anchor,
                anchor["bbox"],
                anchor["uncertainty"],
                anchor["literal_text"],
            )
        )
    for entry in items:
        entry.update(
            source_id=key, source_sha256=doc["sha256"], coordinate_basis="pdf_user_space_unrotated"
        )
        entry["fingerprint"] = fingerprint(entry)
    return items


def validate_items(docs, items):
    by_doc = {d["document_id"]: d for d in docs}
    by_id = {e["item_id"]: e for e in items}
    if len(by_id) != len(items):
        raise ValueError("Duplicate proposal identity")
    for entry in items:
        doc = by_doc[entry["source_id"]]
        if entry["source_sha256"] != doc["sha256"] or entry["page"] != 1:
            raise ValueError("Wrong proposal source or page")
        if entry["bbox"] is not None and not valid_bbox(
            tuple(entry["bbox"]), tuple(doc["pages"][0]["crop_box_pdf_user_space"])
        ):
            raise ValueError("Proposal coordinate invalid")
        if entry["decision"] is not None or entry["reviewer_id"] is not None:
            raise ValueError("Fabricated machine review status")
        if entry["kind"] == "relationship":
            relation = entry["proposed_value"]
            left = by_id[relation["left"]]
            right = by_id[relation["right"]]
            if left["source_id"] != right["source_id"] or left["table_id"] != right["table_id"]:
                raise ValueError("Header relationship source/grid mismatch")
            if not right["column"] <= left["column"] < right["column"] + right["column_span"]:
                raise ValueError("Header relationship column mismatch")
            if not entry["uncertainty"]:
                raise ValueError("Unattested semantic relationship")
            if relation["relationship"] == "period" and right["proposed_text"] not in MONTHS:
                raise ValueError("Unsupported period relationship")
        if entry["kind"] == "printed_unit":
            target = by_id[entry["proposed_value"]["cell_id"]]
            if not target["proposed_text"].startswith(entry["proposed_value"]["printed_symbol"]):
                raise ValueError("Printed unit source mismatch")
        if entry["kind"] == "reading_order":
            refs = entry["proposed_value"]["cell_ids"]
            if len(refs) != len(set(refs)) or any(
                by_id[c]["table_id"] != entry["table_id"] for c in refs
            ):
                raise ValueError("Reading order identity mismatch")
        if (
            fingerprint({k: v for k, v in entry.items() if k != "fingerprint"})
            != entry["fingerprint"]
        ):
            raise ValueError("Proposal fingerprint mismatch")


def csv_row(entry):
    row = {k: entry.get(k, "") for k in FIELDS}
    row.update(
        proposed_value_json=json.dumps(entry["proposed_value"], ensure_ascii=False, sort_keys=True),
        bbox=json.dumps(entry["bbox"]),
        uncertainty="; ".join(entry["uncertainty"]),
        decision="",
        reviewer_correction="",
        corrected_bbox="",
        reviewer_notes="",
    )
    return row


def load_decisions(path):
    if path is None:
        return {}
    packet.no_links(path)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len({row["item_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate review decision ID")
    if any(row.get("decision", "") not in ("", "accept", "correct", "reject") for row in rows):
        raise ValueError("Unsupported review decision")
    return {row["item_id"]: {key: row.get(key, "") for key in DECISION_FIELDS} for row in rows}


def review_row(entry, decisions):
    row = csv_row(entry)
    row.update(decisions.get(entry["item_id"], {}))
    return row


def escaped(value):
    return html.escape(str(value), quote=True)


def svg_markup(doc, image_ref):
    crop = doc["pages"][0]["crop_box_pdf_user_space"]
    width = crop[2] - crop[0]
    height = crop[3] - crop[1]
    rects = []
    for table in doc["tables"]:
        for cell in table["cells"]:
            left, b, r, t = cell["bbox_pdf_user_space_points"]
            color = "#bc6215" if cell["uncertainty"] else "#087c73"
            title = f"{cell['item_id']}: {cell['literal_text'] if cell['literal_text'] is not None else '[UNKNOWN]'}"  # noqa: E501 - escaped HTML/SVG template
            rects.append(
                f'<a href="#{escaped(cell["item_id"])}"><rect data-cell="{escaped(cell["item_id"])}" x="{left - crop[0]}" y="{crop[3] - t}" width="{r - left}" height="{t - b}" fill="{color}" fill-opacity=".08" stroke="{color}" stroke-width=".55"><title>{escaped(title)}</title></rect></a>'  # noqa: E501 - escaped HTML/SVG template
            )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Annotated original page" width="{width * 2}" height="{height * 2}" viewBox="0 0 {width} {height}"><image href="{escaped(image_ref)}" width="{width}" height="{height}"/>'  # noqa: E501 - escaped HTML/SVG template
        + "".join(rects)
        + "</svg>"
    )


def overlay(doc, image, destination):
    crop = doc["pages"][0]["crop_box_pdf_user_space"]
    width = crop[2] - crop[0]
    height = crop[3] - crop[1]
    rects = []
    png = image.convert("RGBA")
    draw = ImageDraw.Draw(png)
    for table in doc["tables"]:
        for cell in table["cells"]:
            left, b, r, t = cell["bbox_pdf_user_space_points"]
            color = "#bc6215" if cell["uncertainty"] else "#087c73"
            title = f"{cell['item_id']}: {cell['literal_text'] if cell['literal_text'] is not None else '[UNKNOWN]'}"  # noqa: E501 - escaped HTML/SVG template
            rects.append(
                f'<a href="../REVIEW.html#{escaped(cell["item_id"])}" target="_top"><rect id="{escaped(cell["item_id"])}" x="{left - crop[0]}" y="{crop[3] - t}" width="{r - left}" height="{t - b}" fill="{color}" fill-opacity=".08" stroke="{color}" stroke-width=".55"><title>{escaped(title)}</title></rect></a>'  # noqa: E501 - escaped HTML/SVG template
            )
            draw.rectangle(
                (
                    (left - crop[0]) * image.width / width,
                    (crop[3] - t) * image.height / height,
                    (r - crop[0]) * image.width / width,
                    (crop[3] - b) * image.height / height,
                ),
                outline=color,
                width=2,
            )
    key = doc["document_id"]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 2}" height="{height * 2}" viewBox="0 0 {width} {height}"><image href="{key}-original.png" width="{width}" height="{height}"/>'  # noqa: E501 - escaped HTML/SVG template
        + "".join(rects)
        + "</svg>"
    )
    (destination / f"{key}-overlay.svg").write_text(svg, encoding="utf-8")
    png.convert("RGB").save(destination / f"{key}-annotated.png", optimize=False)


def html_report(proposals, decisions=None):
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\' file:; object-src \'self\' file:; style-src \'self\'; script-src \'self\'; connect-src \'none\'; base-uri \'none\'; form-action \'none\'"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QG-00 assisted PDF table review</title><link rel="stylesheet" href="assets/review.css"><script defer src="assets/review.js"></script></head><body><header><h1>PDF table annotation review</h1><span class="badge">MACHINE ASSISTED · NOT HUMAN REVIEWED</span><p>Authorized local-dev originals · excluded sources omitted</p></header><main><div class="notice">Inspect the original and overlay, then accept, correct or reject proposed items below. Source text is preserved; amber cells have unresolved text evidence. All semantic roles and header links are hypotheses. These pages reveal machine proposals and cannot serve as independent blind review. No identity, inspection attestation or approval has been supplied.</div><p><a href="proposals.json">Structured proposals</a> · <a href="review_decisions.csv">Editable CSV</a> · <a href="summary.md">Checks and limitations</a></p><nav>'  # noqa: E501 - escaped HTML/SVG template
    ]
    for doc in proposals["documents"]:
        parts.append(f'<a href="#{doc["document_id"]}">{doc["document_id"]}</a>')
    parts.append("</nav>")
    for doc in proposals["documents"]:
        key = doc["document_id"]
        parts.append(
            f'<section id="{key}"><h2>{key}</h2><p>{escaped(doc["publisher"])} · page 1 · {len(doc["tables"])} physical table regions · {sum(len(t["cells"]) for t in doc["tables"])} cells</p><details><summary>Verified source identity and attribution</summary><p>SHA-256 <code>{doc["sha256"]}</code><br>{escaped(doc["attribution"])}<br>Source: <code>{escaped(doc["source_page_url"])}</code><br>Licence: Open Government Licence v3.0. Captured terms and eligibility v2 are retained in the parent evidence package.</p></details><div class="page-pair"><div class="page"><h3>Original page</h3><a href="assets/{key}-original.png"><img alt="Original {key}, page 1" src="assets/{key}-original.png"></a><p><a href="sources/{key}.pdf">Open original PDF</a></p></div><div class="page"><h3>Annotated overlay</h3>{svg_markup(doc, "assets/" + key + "-original.png")}<p>Teal: mechanically supported text/geometry. Amber: unresolved text or engine disagreement. Hover a cell for its ID/value. <a href="assets/{key}-overlay.svg">Open full-size interactive overlay</a> · <a href="assets/{key}-annotated.png">Annotated PNG</a></p></div></div>'  # noqa: E501 - escaped HTML/SVG template
        )
        for table in doc["tables"]:
            parts.append(
                f'<h3>{escaped(table["table_id"])} — {table["row_count"]} rows × {table["column_count"]} columns</h3><p class="muted">{escaped(table["counting_convention"])}</p><div class="grid-wrap"><table class="extracted">'  # noqa: E501 - escaped HTML/SVG template
            )
            for ri in range(table["row_count"]):
                parts.append("<tr>")
                for cell in sorted(
                    [c for c in table["cells"] if c["row"] == ri], key=lambda c: c["column"]
                ):
                    literal = cell["literal_text"]
                    value = "[UNKNOWN]" if literal is None else "∅" if literal == "" else literal
                    klass = "uncertain" if cell["uncertainty"] else "empty" if literal == "" else ""
                    parts.append(
                        f'<td class="{klass}" rowspan="{cell["row_span"]}" colspan="{cell["column_span"]}" title="{escaped(cell["item_id"])}"><a href="#{escaped(cell["item_id"])}">{escaped(value)}</a></td>'  # noqa: E501 - escaped HTML/SVG template
                    )
                parts.append("</tr>")
            parts.append(
                "</table></div><small>∅ displays an observed empty text-layer cell; this symbol is not source text.</small>"  # noqa: E501 - escaped HTML/SVG template
            )
        parts.append("</section>")
    parts.append(
        '<h2>Editable review queue</h2><p>Decisions remain blank until you edit them. Browser edits are held in memory; download the edited CSV before closing or reloading. The original CSV and machine proposals are never overwritten. For geometry corrections use the CSV corrected_bbox field in unrotated PDF points [left,bottom,right,top].</p><div class="toolbar"><input id="search" placeholder="Find ID or text" aria-label="Search proposals"><label><input type="checkbox" id="uncertain-only"> Uncertain only</label><select id="kind" aria-label="Proposal kind"><option value="">All kinds</option>'  # noqa: E501 - escaped HTML/SVG template
    )
    for kind in sorted({e["kind"] for e in proposals["items"]}):
        parts.append(f"<option>{kind}</option>")
    parts.append(
        '</select> <button id="download">Download edited decisions CSV</button></div><table id="items"><thead><tr><th>Item / locator</th><th>Proposed value</th><th>Evidence / uncertainty</th><th>Decision</th><th>Correction</th><th>Notes</th></tr></thead><tbody>'  # noqa: E501 - escaped HTML/SVG template
    )
    for entry in proposals["items"]:
        row = review_row(entry, decisions or {})
        value = (
            entry["proposed_text"]
            if entry["kind"] in ("cell", "text_anchor")
            else json.dumps(entry["proposed_value"], ensure_ascii=False)
        )
        options = "".join(
            f'<option value="{choice}"'
            + (" selected" if choice == row["decision"] else "")
            + f">{choice}</option>"
            for choice in ("", "accept", "correct", "reject")
        )
        parts.append(
            f'<tr id="{escaped(entry["item_id"])}" data-item="true" data-kind="{entry["kind"]}" data-uncertain="{str(bool(entry["uncertainty"])).lower()}" data-csv="{escaped(json.dumps(row, ensure_ascii=False))}" class="{"uncertain" if entry["uncertainty"] else "supported"}"><td><code>{escaped(entry["item_id"])}</code><br>{entry["kind"]} · {entry["source_id"]} p{entry["page"]}<br><small>{escaped(entry["bbox"])}</small></td><td class="literal">{escaped(value)}<details><summary>Full proposed fields</summary><code>{escaped(json.dumps(entry["proposed_value"], ensure_ascii=False))}</code></details></td><td>{escaped("; ".join(entry["uncertainty"]) or "Source-observed; no human review")}<br><small>No calibrated confidence score is available.</small></td><td><select aria-label="Decision for {escaped(entry["item_id"])}">{options}</select></td><td><textarea aria-label="Correction for {escaped(entry["item_id"])}">{escaped(row["reviewer_correction"])}</textarea></td><td><input aria-label="Notes for {escaped(entry["item_id"])}" value="{escaped(row["reviewer_notes"])}"></td></tr>'  # noqa: E501 - escaped HTML/SVG template
        )
    parts.append(
        '</tbody></table><script type="application/json" id="fields">'
        + json.dumps(FIELDS)
        + "</script></main></body></html>"
    )
    return "".join(parts)


def generate(
    manifest: Path,
    corpus: Path,
    gold: Path,
    eligibility: Path,
    plan_path: Path,
    plan_sha256: str,
    destination: Path,
    *,
    decisions_from: Path | None = None,
    expected: packet.Expected | None = None,
    allow_synthetic: bool = False,
    root: Path = packet.ROOT,
) -> dict:
    """Fresh private outputs only; never import into an independent-review workspace."""
    packet.require_unoptimized()
    packet.fresh_output(destination, corpus, root=root)
    expected = expected or packet.Expected()
    identity, paths, records, _ = packet.preflight(
        manifest, corpus, gold, expected, eligibility=eligibility, allow_synthetic=allow_synthetic
    )
    recipes = load_plan(plan_path, plan_sha256, {r.document_id for r in records})
    inputs = (
        manifest,
        gold,
        eligibility,
        plan_path,
        *((decisions_from,) if decisions_from else ()),
    )
    before = {str(p.resolve()): packet.sha(p) for p in inputs}
    saved = load_decisions(decisions_from)
    decisions = {c["document_id"]: c for c in read(eligibility)["candidates"]}
    code = {Path(__file__).relative_to(packet.ROOT).as_posix(): packet.sha(Path(__file__))}
    for module in (grids, recovery, review, packet):
        code[Path(module.__file__).relative_to(packet.ROOT).as_posix()] = packet.sha(
            Path(module.__file__)
        )
    for name in ("review.css", "review.js"):
        code[(ASSETS / name).relative_to(packet.ROOT).as_posix()] = packet.sha(ASSETS / name)
    destination.mkdir(parents=True)
    (destination / "assets").mkdir()
    (destination / "sources").mkdir()
    docs, items, checks = [], [], {}
    for record in records:
        key = record.document_id
        doc, image = propose(key, paths[key], decisions[key], recipes[key])
        checks[key] = validate_document(doc, paths[key], recipes[key])
        items += items_for(doc, recipes[key]["header_row"])
        docs.append(doc)
        image.save(destination / f"assets/{key}-original.png", optimize=False)
        overlay(doc, image, destination / "assets")
        shutil.copyfile(paths[key], destination / f"sources/{key}.pdf")
        if packet.sha(destination / f"sources/{key}.pdf") != record.source_sha256:
            raise ValueError("Original review copy mismatch")
    validate_items(docs, items)
    ids = {i["item_id"] for i in items}
    if any(any(row.values()) for key, row in saved.items() if key not in ids):
        raise ValueError("Existing review decision would lose its item identity")
    after = packet.preflight(
        manifest, corpus, gold, expected, eligibility=eligibility, allow_synthetic=allow_synthetic
    )[0]
    if (
        identity != after
        or before != {str(p.resolve()): packet.sha(p) for p in inputs}
        or code != {p: packet.sha(packet.ROOT / p) for p in code}
    ):
        raise ValueError("Source, decision, plan or code changed during build")
    result = dict(
        version=METHOD,
        evidence_class="MACHINE_ASSISTED_NOT_REVIEWED",
        documents=docs,
        items=items,
        provenance=dict(
            head=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=packet.ROOT, text=True
            ).strip(),
            eligibility=identity["eligibility"],
            geometry_plan_sha256=plan_sha256,
            code=code,
            review_decisions_input_sha256=packet.sha(decisions_from) if decisions_from else None,
            packages={
                n: importlib.metadata.version(n)
                for n in ("pypdf", "pypdfium2", "pdfplumber", "Pillow", "pydantic")
            },
        ),
        human_review_completed=False,
        independent_gold="NOT_EVALUATED",
        qg_00="NOT_EVALUATED",
        qg_01="NOT_EVALUATED",
        reviewer_id=None,
        inspection_attestation=None,
        approved=None,
        unsupported=[
            "No stored spreadsheet formulas or values exist in the PDF evidence.",
            "Currency code and implicit unit scope unknown; printed symbols retained.",
            "Header, period, value and reading-order interpretations require human review.",
            "Declared families are not a completed near-duplicate/family audit.",
            "No calibrated numeric confidence is available.",
        ],
    )
    result["fingerprint"] = fingerprint(result)
    write(destination / "proposals.json", result)
    write(destination / "validation.json", checks)
    with (destination / "review_decisions.csv").open(
        "x", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(review_row(e, saved) for e in items)
    for name in ("review.css", "review.js"):
        shutil.copyfile(ASSETS / name, destination / "assets" / name)
    (destination / "REVIEW.html").write_text(html_report(result, saved), encoding="utf-8")
    cells = [c for d in docs for t in d["tables"] for c in t["cells"]]
    counts = dict(
        documents=len(docs),
        pages=sum(len(d["pages"]) for d in docs),
        tables=sum(len(d["tables"]) for d in docs),
        cells=len(cells),
        supported_cells=sum(not c["uncertainty"] for c in cells),
        uncertain_cells=sum(bool(c["uncertainty"]) for c in cells),
        unknown_cell_literals=sum(c["literal_text"] is None for c in cells),
        empty_cells=sum(c["literal_text"] == "" for c in cells),
        spanning_cells=sum(c["row_span"] > 1 or c["column_span"] > 1 for c in cells),
        review_items=len(items),
        supported_items=sum(not i["uncertainty"] for i in items),
        uncertain_items=sum(bool(i["uncertainty"]) for i in items),
        item_kinds=dict(Counter(i["kind"] for i in items)),
    )
    write(destination / "counts.json", counts)
    summary = (
        "# Machine-assisted PDF review\n\n"
        "Preparation PASS; independent Gold/QG-00/QG-01 NOT_EVALUATED.\n\n"
        "Open REVIEW.html locally. Edits are held in memory until CSV download; existing supplied "
        "decision fields are carried unchanged. "
        "No reviewer attestations or approvals are generated.\n\n"
        f"```json\n{json.dumps(counts, indent=2)}\n```\n\n"
        "The pinned private plan supplies source-bound geometry and requested partitions. "
        "Both glyph engines, physical rulings and raster evidence are re-read from the originals. "
        "Unruled partitions are disclosed; their meanings remain unknown. No absent divider is "
        "reported as a printed stroke. Semantic roles and header/period/order links remain "
        "hypotheses; currency codes, formulas and stored spreadsheet values are unknown. "
        "Coordinates are unrotated PDF points [left,bottom,right,top], rotation 0, UserUnit 1.\n\n"
        "validation.json records executed source, page, grid, text, numeric and proposal checks. "
        "proposals.json pins the plan, decision input, code and package versions. "
        "Only admitted dev sources are included. No blind workspace is opened or changed.\n"
    )
    (destination / "summary.md").write_text(summary, encoding="utf-8")
    artifacts = {
        p.relative_to(destination).as_posix(): packet.sha(p)
        for p in sorted(destination.rglob("*"))
        if p.is_file()
    }
    write(destination / "artifact-manifest.json", artifacts)
    write(
        destination / "COMPLETE.json",
        dict(
            artifact_fingerprint=fingerprint(artifacts),
            manifest_sha256=packet.sha(destination / "artifact-manifest.json"),
        ),
    )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "corpus", "gold", "eligibility", "plan", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--decisions-from", type=Path)
    args = parser.parse_args()
    try:
        counts = generate(
            args.manifest,
            args.corpus,
            args.gold,
            args.eligibility,
            args.plan,
            args.plan_sha256,
            args.output,
            decisions_from=args.decisions_from,
        )
        print(json.dumps(counts, sort_keys=True))
        return 0
    except Exception:
        print("BLOCKED: source, rights, geometry plan or fresh private output rejected")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
