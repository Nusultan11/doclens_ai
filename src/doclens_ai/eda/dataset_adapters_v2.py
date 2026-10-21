"""Bounded local dataset adapters; coordinates are observations, never human attestations."""

from __future__ import annotations

import math
from pathlib import Path

from doclens_ai.eda.corpus_v2 import asset_path, read_json
from doclens_ai.extraction.evidence_v2 import Page, valid_bbox

DOCLAYNET_CLASSES = {
    "Caption",
    "Footnote",
    "Formula",
    "List-item",
    "Page-footer",
    "Page-header",
    "Picture",
    "Section-header",
    "Table",
    "Text",
    "Title",
}


def image_point(x: float, y: float, page: Page, width: int, height: int, *, frame: str):
    """Unrotated PDF user space -> rotated image top-left, including nonzero box origins."""
    if frame not in {"media", "crop"} or width <= 0 or height <= 0:
        raise ValueError("image frame rejected")
    left, bottom, right, top = page.media_box if frame == "media" else page.crop_box
    u, v = (x - left) / (right - left), (y - bottom) / (top - bottom)
    a, b = {0: (u, 1 - v), 90: (v, u), 180: (1 - u, v), 270: (1 - v, 1 - u)}[page.rotation]
    return a * width, b * height


def pdf_point(x: float, y: float, page: Page, width: int, height: int, *, frame: str):
    if frame not in {"media", "crop"} or width <= 0 or height <= 0:
        raise ValueError("image frame rejected")
    a, b = x / width, y / height
    u, v = {0: (a, 1 - b), 90: (b, a), 180: (1 - a, b), 270: (1 - b, 1 - a)}[page.rotation]
    left, bottom, right, top = page.media_box if frame == "media" else page.crop_box
    return left + u * (right - left), bottom + v * (top - bottom)


def image_box(box, page: Page, width: int, height: int, *, frame: str) -> list[float]:
    if len(box) != 4 or not valid_bbox(tuple(box)):
        raise ValueError("invalid PDF region")
    points = [
        image_point(x, y, page, width, height, frame=frame)
        for x in (box[0], box[2])
        for y in (box[1], box[3])
    ]
    return [
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
    ]


def xywh_box(box, width: int, height: int) -> list[float]:
    if len(box) != 4 or any(type(v) not in {int, float} or not math.isfinite(v) for v in box):
        raise ValueError("invalid annotation coordinates")
    x, y, w, h = box
    result = [x, y, x + w, y + h]
    if not valid_bbox(tuple(result), (0, 0, width, height)):
        # No silent clamping of publisher boxes slightly outside the image.
        raise ValueError("annotation outside image")
    return result


def page_identity(path: Path, number: int) -> Page:
    from pypdf import PdfReader

    reader = PdfReader(path)
    if (
        reader.is_encrypted
        or not 0 < len(reader.pages) <= 2000
        or not 1 <= number <= len(reader.pages)
    ):
        raise ValueError("PDF page inventory rejected")
    page = reader.pages[number - 1]
    if page.get("/UserUnit", 1) != 1:
        raise ValueError("unsupported PDF UserUnit")
    return Page(
        number=number,
        media_box=tuple(map(float, page.mediabox)),
        crop_box=tuple(map(float, page.cropbox)),
        rotation=page.rotation,
    )


def doclaynet(root: Path, sample, *, frame: str = "media") -> dict:
    """Validate a bounded COCO subset + auxiliary JSON + original page/PNG quartet.

    Auxiliary JSON and COCO annotation bytes are separately hashed by the
    manifest. No PDF is rendered or text re-labelled here.
    """
    from PIL import Image
    from pypdf import PdfReader

    if frame not in {"media", "crop"}:
        raise ValueError("image frame rejected")
    if (
        not sample.original
        or not sample.image
        or not sample.annotation
        or not sample.page
        or not sample.annotation.auxiliary
    ):
        raise ValueError("DocLayNet original/image/annotation/page required")
    if sample.annotation.kind != "doclaynet_coco":
        raise ValueError("wrong annotation adapter")
    source = asset_path(root, sample.original)
    image_path = asset_path(root, sample.image)
    annotation = read_json(asset_path(root, sample.annotation.asset))
    # Auxiliary text metadata is not treated as an independently reviewed annotation.
    auxiliary = read_json(asset_path(root, sample.annotation.auxiliary))
    if page_identity(source, sample.page.number) != sample.page:
        raise ValueError("PDF page identity mismatch")
    metadata = auxiliary["metadata"]
    matches = [i for i in annotation["images"] if i["file_name"] == image_path.name]
    if len(annotation["images"]) > 2000 or len(annotation["annotations"]) > 100_000:
        raise ValueError("COCO subset limit")
    if len(matches) != 1:
        raise ValueError("COCO image identity mismatch")
    image = matches[0]
    with Image.open(image_path) as png:
        width, height = png.size
    if (
        (width, height) != (image["width"], image["height"])
        or (width, height) != (metadata["coco_width"], metadata["coco_height"])
        or metadata["page_hash"] != image_path.stem
        or source.stem != image_path.stem
        or metadata["original_filename"] != image["doc_name"]
        or metadata["page_no"] != image["page_no"]
        or metadata["page_no"] != sample.original_page_number
        or image.get("precedence", 0) != 0
    ):
        raise ValueError("DocLayNet pair identity mismatch")
    box = sample.page.media_box if frame == "media" else sample.page.crop_box
    physical = [box[2] - box[0], box[3] - box[1]]
    if sample.page.rotation in {90, 270}:
        physical.reverse()
    discrepancy = max(
        abs(a - b)
        for a, b in zip(
            physical, [metadata["original_width"], metadata["original_height"]], strict=True
        )
    )
    categories = {c["id"]: c["name"] for c in annotation["categories"]}
    regions, unsupported = [], []
    ids = set()
    for item in annotation["annotations"]:
        if item["image_id"] != image["id"]:
            continue
        if item["id"] in ids:
            raise ValueError("duplicate COCO annotation")
        ids.add(item["id"])
        label = categories[item["category_id"]]
        try:
            region = xywh_box(item["bbox"], width, height)
        except ValueError:
            unsupported.append({"annotation_id": item["id"], "reason": "out_of_image_box"})
            continue
        if label not in DOCLAYNET_CLASSES or item.get("precedence", 0) != 0:
            unsupported.append({"annotation_id": item["id"], "reason": "class_or_precedence"})
            continue
        points = [
            pdf_point(x, y, sample.page, width, height, frame=frame)
            for x in (region[0], region[2])
            for y in (region[1], region[3])
        ]
        pdf_box = [
            min(p[0] for p in points),
            min(p[1] for p in points),
            max(p[0] for p in points),
            max(p[1] for p in points),
        ]
        regions.append(
            {"annotation_id": item["id"], "class": label, "bbox_image": region, "bbox_pdf": pdf_box}
        )
    text = PdfReader(source).pages[sample.page.number - 1].extract_text() or ""
    text_cells = auxiliary.get("cells", [])
    if len(text_cells) > 100_000:
        raise ValueError("auxiliary text limit")
    return {
        "sample_id": sample.sample_id,
        "frame": frame,
        "page": sample.page.model_dump(mode="json"),
        "width": width,
        "height": height,
        "dimension_discrepancy_points": discrepancy,
        "regions": regions,
        "unsupported": unsupported,
        "automatic_text_cells": len(text_cells),
        "auto_reference_text_present": sum(
            bool(c.get("text")) and c["text"] in text for c in text_cells
        ),
        "human_verification": "NOT_PERFORMED",
        "status": "needs_review" if discrepancy or unsupported else "automatic_consistency_only",
    }


def table_pdf(records: list[dict], *, dataset: str) -> dict:
    """Normalize publisher PDF JSON cell topology; automatic reference only.

    PubTables/FinTabNet.c PDF archives contain lists of table dictionaries. The
    adapter requires their documented full row_nums/column_nums + pdf_bbox cells;
    image-only VOC boxes cannot be promoted to cell topology or source text.
    """
    if dataset not in {"pubtables-1m", "fintabnet-c"} or len(records) > 1000:
        raise ValueError("table adapter budget or source rejected")
    tables = []
    for record in records:
        page_index = record.get("pdf_page_index")
        table_box = record.get("pdf_table_bbox")
        if page_index is not None and (type(page_index) is not int or page_index < 0):
            raise ValueError("invalid publisher page index")
        if table_box is not None and (len(table_box) != 4 or not valid_bbox(tuple(table_box))):
            raise ValueError("invalid publisher table bbox")
        if len(record["cells"]) > 2048:
            raise ValueError("table cell budget")
        cells, occupied = [], set()
        for cell in record["cells"]:
            rows, columns = cell["row_nums"], cell["column_nums"]
            if (
                not rows
                or not columns
                or len(rows) > 256
                or len(columns) > 64
                or any(type(n) is not int or n < 0 for n in rows + columns)
                or rows != list(range(min(rows), max(rows) + 1))
                or columns != list(range(min(columns), max(columns) + 1))
            ):
                raise ValueError("noncontiguous cell topology")
            slots = {(r, c) for r in rows for c in columns}
            if occupied & slots or len(occupied | slots) > 16_384:
                raise ValueError("overlapping or oversized topology")
            occupied |= slots
            box = cell.get("pdf_bbox")
            if box is not None and (len(box) != 4 or not valid_bbox(tuple(box))):
                raise ValueError("invalid publisher cell bbox")
            cells.append(
                {
                    "row": min(rows),
                    "column": min(columns),
                    "row_span": len(rows),
                    "column_span": len(columns),
                    "bbox_pdf": box,
                    "literal": cell.get("pdf_text_content"),
                    "label_origin": "automatic_reference",
                }
            )
        if len(cells) > 2048:
            raise ValueError("table cell budget")
        tables.append(
            {
                "cells": cells,
                "page_index": record.get("pdf_page_index"),
                "bbox_pdf": record.get("pdf_table_bbox"),
                "coordinate_system": "publisher_pymupdf_top_left_not_native_user_space",
                "semantic_relationships": None,
            }
        )
    return {"dataset": dataset, "tables": tables, "independent_gold": False}


def omnidocbench(record: dict) -> dict:
    """Keep publisher order/ignore flags and polygons; do not convert image PDFs to native PDFs."""
    page = record["page_info"]
    width, height = page["width"], page["height"]
    if any(type(v) not in {int, float} or not math.isfinite(v) or v <= 0 for v in (width, height)):
        raise ValueError("invalid publisher image dimensions")
    regions = []
    if len(record["layout_dets"]) > 10_000:
        raise ValueError("region limit")
    for item in record["layout_dets"]:
        polygon = item["poly"]
        if len(polygon) != 8 or not all(math.isfinite(v) for v in polygon):
            raise ValueError("polygon rejected")
        if any(
            not 0 <= x <= width or not 0 <= y <= height
            for x, y in zip(polygon[::2], polygon[1::2], strict=True)
        ):
            raise ValueError("polygon outside image")
        regions.append(
            {
                "id": item["anno_id"],
                "polygon": polygon,
                "class": item["category_type"],
                "order": item.get("order"),
                "ignore": item.get("ignore", False),
                "literal": item.get("text"),
                "table_html": item.get("html"),
            }
        )
    if len({r["id"] for r in regions}) != len(regions):
        raise ValueError("duplicate OmniDocBench identity")
    return {
        "regions": regions,
        "width": width,
        "height": height,
        "review": "publisher_mixed_process_not_local_independent_review",
    }


def darmm(record: dict) -> dict:
    if (
        record["tier"] not in {"clean", "hard", "page"}
        or record["level"] not in {"word", "line", "page"}
        or not isinstance(record["label"], str)
        or len(record["label"]) > 100_000
    ):
        raise ValueError("Darmm record rejected")
    return {
        "literal": record["label"],
        "tier": record["tier"],
        "level": record["level"],
        "domain": "synthetic",
        "review": "generated_not_human_gold",
        "source_pdf": None,
    }
