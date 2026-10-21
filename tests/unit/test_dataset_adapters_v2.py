"""Coordinate transforms and publisher-shaped synthetic pairs, never dataset quality evidence."""

from __future__ import annotations

import json

import pytest
from PIL import Image
from pypdf import PdfWriter

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.eda import dataset_adapters_v2 as adapters
from doclens_ai.extraction.evidence_v2 import Page
from tests.unit.test_corpus_v2 import sample


@pytest.mark.parametrize(
    "rotation,expected",
    [
        (0, (0.0, 100.0)),
        (90, (0.0, 0.0)),
        (180, (200.0, 0.0)),
        (270, (200.0, 100.0)),
    ],
)
def test_transform_known_corners_and_roundtrip(rotation, expected):
    page = Page(
        number=1,
        media_box=(-10.0, -20.0, 290.0, 180.0),
        crop_box=(10.0, 0.0, 210.0, 100.0),
        rotation=rotation,
    )
    assert adapters.image_point(10.0, 0.0, page, 200, 100, frame="crop") == expected
    for point in [(10.0, 0.0), (27.0, 32.0), (210.0, 100.0)]:
        image = adapters.image_point(*point, page, 200, 100, frame="crop")
        assert adapters.pdf_point(*image, page, 200, 100, frame="crop") == pytest.approx(point)


def pair(tmp_path):
    pdf = tmp_path / "publichash.pdf"
    writer = PdfWriter()
    writer.add_blank_page(300, 200)
    writer.write(pdf)
    image = tmp_path / "publichash.png"
    Image.new("RGB", (1025, 1025), "white").save(image)
    annotation = tmp_path / "coco.json"
    annotation.write_text(
        json.dumps(
            {
                "images": [
                    {
                        "id": 7,
                        "file_name": image.name,
                        "width": 1025,
                        "height": 1025,
                        "doc_name": "public-parent.pdf",
                        "page_no": 4,
                        "precedence": 0,
                    }
                ],
                "categories": [{"id": 1, "name": "Text"}],
                "annotations": [
                    {"id": 1, "image_id": 7, "category_id": 1, "bbox": [0, 0, 1025, 1025]}
                ],
            }
        )
    )
    auxiliary = tmp_path / "aux.json"
    auxiliary.write_text(
        json.dumps(
            {
                "metadata": {
                    "page_hash": "publichash",
                    "original_filename": "public-parent.pdf",
                    "page_no": 4,
                    "coco_width": 1025,
                    "coco_height": 1025,
                    "original_width": 300,
                    "original_height": 200,
                },
                "cells": [],
            }
        )
    )

    def asset(path, fmt):
        return corpus.Asset(
            path=path.name, sha256=corpus.sha256(path), size_bytes=path.stat().st_size, format=fmt
        )

    value = sample(
        tmp_path,
        original=asset(pdf, "pdf"),
        image=asset(image, "png"),
        page=adapters.page_identity(pdf, 1),
        original_page_number=4,
        annotation=corpus.Annotation(
            asset=asset(annotation, "json"),
            auxiliary=asset(auxiliary, "json"),
            kind="doclaynet_coco",
            revision="fixture-1",
            provenance="synthetic-fixture",
            coordinate_system="image_top_left_xywh",
            source_sha256=corpus.sha256(pdf),
            source_page=1,
            review=corpus.Review(status="synthetic"),
        ),
    )
    return value


def test_doclaynet_quartet_geometry(tmp_path):
    value = pair(tmp_path)
    report = adapters.doclaynet(tmp_path, value)
    assert report["dimension_discrepancy_points"] == 0
    assert report["regions"][0]["bbox_pdf"] == [0.0, 0.0, 300.0, 200.0]
    assert report["human_verification"] == "NOT_PERFORMED"


@pytest.mark.parametrize("field", ["page_no", "page_hash", "original_filename", "coco_width"])
def test_doclaynet_wrong_pair_rejected(tmp_path, field):
    value = pair(tmp_path)
    path = tmp_path / "aux.json"
    data = json.loads(path.read_text())
    data["metadata"][field] = 99 if field in {"page_no", "coco_width"} else "wrong-pair"
    path.write_text(json.dumps(data))
    asset = corpus.Asset(
        path=path.name, sha256=corpus.sha256(path), size_bytes=path.stat().st_size, format="json"
    )
    value = value.model_copy(
        update={"annotation": value.annotation.model_copy(update={"auxiliary": asset})}
    )
    with pytest.raises(ValueError, match="pair identity"):
        adapters.doclaynet(tmp_path, value)


def test_doclaynet_changed_auxiliary_rejected(tmp_path):
    value = pair(tmp_path)
    (tmp_path / "aux.json").write_text("{}")
    with pytest.raises(ValueError, match="bytes mismatch"):
        adapters.doclaynet(tmp_path, value)


def test_outside_coordinates_not_clamped():
    with pytest.raises(ValueError):
        adapters.xywh_box([0, -0.5, 100, 100], 100, 100)
    with pytest.raises(ValueError):
        adapters.xywh_box([float("nan"), 0, 1, 1], 100, 100)


@pytest.mark.parametrize("dataset", ["pubtables-1m", "fintabnet-c"])
def test_tables_keep_empty_spanning_cells_and_automatic_provenance(dataset):
    record = {
        "pdf_page_index": 0,
        "cells": [
            {
                "row_nums": [0],
                "column_nums": [0, 1],
                "pdf_bbox": [1, 2, 9, 4],
                "pdf_text_content": "-001,25 %",
            },
            {"row_nums": [1], "column_nums": [0], "pdf_text_content": ""},
            {"row_nums": [1], "column_nums": [1], "pdf_text_content": "001"},
        ],
    }
    result = adapters.table_pdf([record], dataset=dataset)
    assert result["independent_gold"] is False
    assert result["tables"][0]["cells"][0]["column_span"] == 2
    assert result["tables"][0]["cells"][0]["literal"] == "-001,25 %"
    assert result["tables"][0]["cells"][1]["literal"] == ""
    assert result["tables"][0]["semantic_relationships"] is None
    record["cells"].append(record["cells"][0])
    with pytest.raises(ValueError, match="topology"):
        adapters.table_pdf([record], dataset=dataset)


def test_omnidocbench_order_and_ignored_regions_are_preserved():
    record = {
        "page_info": {"width": 100, "height": 100},
        "layout_dets": [
            {
                "category_type": "text_block",
                "anno_id": 1,
                "poly": [0, 0, 10, 0, 10, 10, 0, 10],
                "ignore": True,
                "order": 3,
                "text": "public-fixture",
            }
        ],
    }
    result = adapters.omnidocbench(record)
    assert result["regions"][0]["ignore"] is True
    assert result["regions"][0]["order"] == 3
    record["layout_dets"][0]["poly"][0] = -1
    with pytest.raises(ValueError):
        adapters.omnidocbench(record)


def test_darmm_is_synthetic_not_real_document_gold():
    result = adapters.darmm({"label": "Ә Ғ Қ Ң Ө Ұ Ү Һ І", "tier": "page", "level": "page"})
    assert result["domain"] == "synthetic"
    assert result["source_pdf"] is None
    assert "\u04d8" in result["literal"]


def test_visual_packet_is_private_and_has_no_automatic_human_signoff(tmp_path, monkeypatch):
    from tools.extraction_quality import geometry_v2

    value = pair(tmp_path)
    monkeypatch.setattr(geometry_v2, "private_destination", lambda _: None)
    output = tmp_path / "packet"
    result = geometry_v2.packet(tmp_path, value, output, frame="media")
    assert result["human_review"] == "NOT_PERFORMED"
    assert corpus.sha256(output / "original.pdf") == value.original.sha256
    checklist = json.loads((output / "manual-checklist.json").read_text())
    assert checklist["reviewer"] is None and checklist["text_alignment"] is None
    markup = (output / "inspection.html").read_text(encoding="utf-8")
    assert "data:image/png;base64," in markup
    assert '<rect x="0"' in markup


@pytest.mark.parametrize(
    "field,value",
    [
        ("pdf_page_index", -1),
        ("pdf_page_index", True),
        ("pdf_table_bbox", [0, 0, -1, 20]),
        ("pdf_table_bbox", [0, 0, 1, 20, 25]),
    ],
)
def test_table_metadata_must_not_fabricate_valid_locators(field, value):
    record = {"pdf_page_index": 0, "cells": [], field: value}
    with pytest.raises(ValueError):
        adapters.table_pdf([record], dataset="pubtables-1m")


@pytest.mark.parametrize("width,height", [(0, 100), (-1, 100), (float("nan"), 100)])
def test_empty_omnidocbench_page_still_requires_valid_geometry(width, height):
    with pytest.raises(ValueError):
        adapters.omnidocbench({"page_info": {"width": width, "height": height}, "layout_dets": []})


def test_doclaynet_rejects_unknown_frame_before_transform(tmp_path):
    with pytest.raises(ValueError, match="frame"):
        adapters.doclaynet(tmp_path, pair(tmp_path), frame="invented")
