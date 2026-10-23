"""Synthetic adapter/evaluator contracts; never real-document Gold."""

import sys
from pathlib import Path
from types import SimpleNamespace as S

import pytest

from tools.extraction_campaign import adapters
from tools.extraction_campaign.evidence import Observation, compare, exact_present, score


@pytest.mark.parametrize("value", [False, "1", 11, float("nan")])
def test_geometry_does_not_coerce_or_hide_invalid_coordinates(value):
    with pytest.raises(ValueError):
        Observation("a", "text", "-2,5", 1, 0, bbox=(value, 0, 10, 10))


def test_docling_native_tree_picture_descendants_and_unknowns():
    payload = {
        "body": {"self_ref": "#/body", "children": [{"$ref": "#/pictures/0"}]},
        "pictures": [
            {"self_ref": "#/pictures/0", "label": "picture", "children": [{"$ref": "#/texts/0"}]}
        ],
        "texts": [
            {
                "self_ref": "#/texts/0",
                "label": "text",
                "text": "00125 -2,5 kg",
                "prov": [{"page_no": 2}],
            }
        ],
    }
    rows = adapters.docling(payload)
    assert rows[0].page is None and rows[0].text is None
    assert rows[1].text == "00125 -2,5 kg" and rows[1].page == 2
    assert rows[1].bbox is None and rows[1].parent == "#/pictures/0"
    payload["texts"][0]["children"] = [{"$ref": "#/pictures/0"}]
    with pytest.raises(ValueError, match="cycle"):
        adapters.docling(payload)


def test_docling_multipage_text_is_sliced_from_native_charspans():
    item = {
        "self_ref": "#/texts/0",
        "label": "text",
        "text": "AABB",
        "prov": [{"page_no": 1, "charspan": [0, 2]}, {"page_no": 2, "charspan": [2, 4]}],
    }
    data = {"body": {"self_ref": "#/body", "children": [{"$ref": "#/texts/0"}]}, "texts": [item]}
    assert [(o.text, o.page) for o in adapters.docling(data)] == [("AA", 1), ("BB", 2)]
    item["prov"][1].pop("charspan")
    with pytest.raises(ValueError, match="charspan"):
        adapters.docling(data)


def test_docling_cell_geometry_and_native_axes_are_preserved_without_flipping_errors():
    table = {
        "self_ref": "#/tables/0",
        "label": "table",
        "prov": [{"page_no": 1}],
        "data": {
            "table_cells": [
                {
                    "text": "-2,5",
                    "start_row_offset_idx": 0,
                    "end_row_offset_idx": 1,
                    "start_col_offset_idx": 0,
                    "end_col_offset_idx": 2,
                    "bbox": {"l": 1, "t": 10, "r": 8, "b": 2, "coord_origin": "BOTTOMLEFT"},
                }
            ]
        },
    }
    payload = {
        "body": {"self_ref": "#/body", "children": [{"$ref": "#/tables/0"}]},
        "tables": [table],
    }
    cell = adapters.docling(payload)[1]
    assert cell.bbox == (1, 2, 8, 10) and cell.coordinate_system == "bottom_left_points"
    assert (cell.row_span, cell.column_span, cell.table) == (1, 2, "#/tables/0")
    table["data"]["table_cells"][0]["bbox"]["coord_origin"] = "TOPLEFT"
    with pytest.raises(ValueError, match="rectangle"):
        adapters.docling(payload)


def test_paddle_keeps_raw_table_separate_and_page_unknown_if_missing():
    block = {"block_label": "table", "block_content": "<table><td>00125</td></table>"}
    data = {
        "res": {
            "parsing_res_list": [block],
            "table_res_list": [
                {"cell_box_list": [[1, 2, 3, 4]], "pred_html": block["block_content"]}
            ],
        }
    }
    row = adapters.paddle(data)[0]
    assert row.page is None and row.bbox is None and row.row is None
    assert row.text.strip() == "00125" and "table_res_list" in data["res"]
    data["res"]["page_index"] = True
    with pytest.raises(ValueError):
        adapters.paddle(data)


def test_paddle_html_attributes_are_not_extracted_evidence():
    row = adapters.paddle(
        {
            "page_index": 0,
            "parsing_res_list": [
                {
                    "block_label": "table",
                    "block_content": '<table data-key="999"><tr><td>00125</td></tr></table>',
                }
            ],
        }
    )[0]
    assert not exact_present("999", row.text)
    assert exact_present("00125", row.text)


def test_marker_html_entities_and_source_page_do_not_invent_geometry():
    out = adapters.marker(
        {
            "children": [
                {"id": "/page/0/Text/1", "block_type": "Text", "html": "<p>-2,5 &amp; 00125</p>"}
            ]
        }
    )
    assert out[0].text.strip() == "-2,5 & 00125" and out[0].page == 1
    assert out[0].bbox is None and out[0].coordinate_system is None
    with pytest.raises(ValueError):
        adapters.marker({"children": [{"html": "<p>missing identity</p>"}]})


def test_mineru_missing_page_is_unknown_and_spans_stay_ordered():
    data = {
        "pdf_info": [
            {
                "para_blocks": [
                    {"type": "text", "lines": [{"spans": [{"content": "-2,5"}, {"content": "kg"}]}]}
                ]
            }
        ]
    }
    out = adapters.mineru(data)
    assert out[0].page is None and out[0].text == "-2,5\nkg"


@pytest.mark.parametrize(
    "a,b,present",
    [
        ("00125", "125", False),
        ("125", "00125", False),
        ("-2,5", "2,5", False),
        ("2,5", "-2,5", False),
        ("-2,5 kg", "value -2,5 kg", True),
        ("-2,5 kg", "value -2.5 kg", False),
    ],
)
def test_numeric_tokens_never_normalize_signs_zeros_or_separators(a, b, present):
    assert exact_present(a, b) is present


def test_failed_observation_denominators_and_page_error_are_separate():
    anchor = S(anchor_id="a1", text="-2,5 kg", occurrence=1, source=S(page_number=1))
    record = S(anchors=(anchor,), order_pairs=())
    missing = score(record, None)
    assert missing["anchor_presence"] is None and missing["denominators"]["anchors"] == 1
    before = score(record, (Observation("a", "text", "-2,5 kg", 1, 0),))
    after = score(record, (Observation("a", "text", "-2,5 kg", 2, 0),))
    assert after["anchor_presence"] == {"a1": True}
    assert compare(before, after)["page_presence"]["lost"] == ["a1"]
    assert compare(before, missing)["anchor_presence"]["status"] == "UNKNOWN"


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("hang", "timeout"),
        ("crash", "failed"),
        ("oom", "failed"),
        ("output", "output_limit"),
        ("asyncio", "completed"),
    ],
)
def test_actual_research_worker_bounds_and_cleanup(mode, expected):
    from uuid import uuid4

    from tools.extraction_campaign.protocol import ROOT
    from tools.extraction_campaign.run import run_one

    output = ROOT / "evaluation-output/extraction-campaign-contract-tests" / uuid4().hex
    result = run_one(
        Path(sys.executable),
        {
            "candidate": "probe",
            "configuration": {"mode": mode},
            "policy": {
                "wall_seconds_per_document": 2,
                "cpu_seconds": 10,
                "process_tree_rss_bytes": 128 * 1024**2,
                "os_commit_bytes": 256 * 1024**2,
                "native_output_bytes": 32768,
                "scratch_bytes": 2 * 1024**2,
            },
        },
        output,
    )
    assert result["status"] == expected
    assert result["remaining_owned_processes"] == []
    if mode == "crash":
        assert result["exit_code"] == 73
    if mode == "oom":
        assert result["error_type"] == "MemoryError"


def test_owned_auxiliary_processes_are_killed_when_worker_finishes():
    import json
    from uuid import uuid4

    import psutil

    from tools.extraction_campaign.protocol import ROOT
    from tools.extraction_campaign.run import run_one

    output = ROOT / "evaluation-output/extraction-campaign-contract-tests" / uuid4().hex
    result = run_one(
        Path(sys.executable),
        {
            "candidate": "probe",
            "configuration": {"mode": "child"},
            "policy": {
                "wall_seconds_per_document": 5,
                "cpu_seconds": 10,
                "process_tree_rss_bytes": 256 * 1024**2,
                "os_commit_bytes": 512 * 1024**2,
                "native_output_bytes": 32768,
                "scratch_bytes": 2 * 1024**2,
            },
        },
        output,
    )
    assert result["status"] == "completed" and result["remaining_owned_processes"] == []
    child = json.loads((output / "child.json").read_text())["pid"]
    assert not psutil.pid_exists(child)


@pytest.mark.parametrize("name", ["../model", "/model", "C:/model", "a\\b", ""])
def test_public_staging_cannot_escape_its_model_directory(name):
    from tools.extraction_campaign.staging import safe_relative

    with pytest.raises(ValueError):
        safe_relative(name)


def test_reused_model_config_must_match_pinned_git_blob(tmp_path):
    import hashlib

    from tools.extraction_campaign.staging import get_file

    path = tmp_path / "config.json"
    path.write_bytes(b"bad")
    expected = hashlib.sha1(b"blob 3\0" + b"yes", usedforsecurity=False).hexdigest()
    with pytest.raises(ValueError):
        get_file(
            "https://huggingface.co/unused",
            path,
            expected_size=3,
            expected_sha256=None,
            blob_id=expected,
        )
