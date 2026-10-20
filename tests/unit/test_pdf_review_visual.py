"""Known public vector rectangles; actual CPU rendering and browser mouse coverage."""

from __future__ import annotations

import base64
import copy
import csv
import json
import os
import subprocess
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, FloatObject, NameObject, RectangleObject

from tests.unit.test_ml28_review import completed
from tests.unit.test_pdf_review_workbench import fixture, frozen_hashes, request, seal
from tools.extraction_quality import pdf_review_workbench as tool
from tools.extraction_quality import pdf_table_review_packet as packet


@pytest.fixture(autouse=True)
def local_renderer():
    pytest.importorskip("pypdfium2", reason="Optional local visual renderer is not installed")


def visual_fixture(tmp_path, *, crop=(20, 30, 280, 370), rotation=0, unit=1, content_data=None):
    data = completed(tmp_path)[0]
    writer = PdfWriter()
    page = writer.add_blank_page(300, 400)
    page.cropbox = RectangleObject(crop)
    page.rotate(rotation)
    page[NameObject("/UserUnit")] = FloatObject(unit)
    content = DecodedStreamObject()
    # The only painted content: exact PDF-space rectangle [60,100,180,200].
    content.set_data(
        content_data if content_data is not None else b"0 0 0 rg 60 100 120 100 re f\n"
    )
    from pypdf.generic import DictionaryObject

    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    writer.write(data[5])
    digest = packet.sha(data[5])
    size = data[5].stat().st_size
    with data[1].open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[0].update(sha256=digest, size_bytes=str(size))
    with data[1].open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=fields)
        output.writeheader()
        output.writerows(rows)
    record = json.loads(data[3].read_text(encoding="utf-8"))
    record.update(source_sha256=digest, source_size_bytes=size)
    data[3].write_text(json.dumps(record) + "\n", encoding="utf-8")
    expected = replace(
        data[4], manifest_sha256=packet.sha(data[1]), gold_sha256=packet.sha(data[3])
    )
    bundle = data[0] / "evaluation-output/visual-packet"
    packet.generate(*data[1:4], bundle, expected=expected, allow_synthetic=True, root=data[0])
    return tool.Workbench(
        *data[1:4],
        bundle,
        data[0] / "evaluation-output/visual-review",
        root=data[0],
        expected=expected,
        allow_synthetic=True,
    )


def payload(app, *, page=1):
    key = next(iter(app.records))
    return {
        "revision": app.view()["revision"],
        "document_id": key,
        "page": page,
        "page_identity": app.pages[key][page - 1],
    }


def annotation(app):
    supplied = payload(app)
    rendered = app.render_page(supplied)
    draft = copy.deepcopy(app.state["documents"][supplied["document_id"]]["draft"])
    draft["pages"][0]["regions"] = [
        {"region_id": "human-region", "table_id": None, "bbox_pdf_user_space_points": None}
    ]
    table = copy.deepcopy(draft["table_template"])
    table.update(page_number=1, review_table_id="human-table")
    table["cells"].append(copy.deepcopy(draft["cell_template"]))
    draft["tables"] = [table]
    return {
        **supplied,
        "render_id": rendered["render_id"],
        "bbox": [60, 100, 180, 200],
        "draft": draft,
        "target": {"kind": "region", "region": 0},
    }


@pytest.mark.parametrize("crop", [(20, 30, 280, 370), (20.25, 30.25, 280.55, 370.45)])
def test_real_render_crop_and_pixel_mapping(tmp_path, crop):
    app = visual_fixture(tmp_path, crop=crop)
    before = frozen_hashes(app)
    result = app.render_page(payload(app))
    # Decode the actual PNG via stdlib: encoder uses unfiltered RGB scanlines.
    import struct
    import zlib

    png = base64.b64decode(result["png_base64"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    offset, compressed = 8, b""
    while offset < len(png):
        length = struct.unpack(">I", png[offset : offset + 4])[0]
        if png[offset + 4 : offset + 8] == b"IDAT":
            compressed += png[offset + 8 : offset + 8 + length]
        offset += length + 12
    pixels = zlib.decompress(compressed)
    width, height = result["width"], result["height"]
    marked = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if pixels[y * (1 + 3 * width) + 1 + 3 * x] < 64
    ]
    x0, x1 = min(x for x, _ in marked), max(x for x, _ in marked) + 1
    y0, y1 = min(y for _, y in marked), max(y for _, y in marked) + 1
    measured = [
        crop[0] + x0 / width * (crop[2] - crop[0]),
        crop[3] - y1 / height * (crop[3] - crop[1]),
        crop[0] + x1 / width * (crop[2] - crop[0]),
        crop[3] - y0 / height * (crop[3] - crop[1]),
    ]
    assert measured == pytest.approx([60, 100, 180, 200], abs=0.6)
    assert before == frozen_hashes(app)
    assert not list(app.output.rglob("*.png"))


@pytest.mark.parametrize(
    "settings",
    [
        {"rotation": 90},
        {"rotation": 180},
        {"rotation": 270},
        {"unit": 2},
        {"crop": (-10, 0, 280, 370)},
    ],
)
def test_unsupported_transforms_fail_closed(tmp_path, settings):
    app = visual_fixture(tmp_path, **settings)
    with pytest.raises(ValueError, match="Capture disabled"):
        app.render_page(payload(app))
    assert not app.renders


def test_renderer_and_requested_page_mismatch_fail_closed(tmp_path, monkeypatch):
    import pypdfium2

    app = visual_fixture(tmp_path)
    supplied = copy.deepcopy(payload(app))
    supplied["page_identity"]["crop_box_pdf_user_space"][0] += 1
    with pytest.raises(ValueError, match="identity"):
        app.render_page(supplied)
    supplied = payload(app)
    supplied["page"] = 2
    with pytest.raises(ValueError, match="page"):
        app.render_page(supplied)
    monkeypatch.setattr(pypdfium2.PdfPage, "get_bbox", lambda _: (0, 0, 1, 1))
    with pytest.raises(ValueError, match="geometry mismatch"):
        app.render_page(payload(app))


def test_missing_renderer_has_clear_diagnostic(tmp_path, monkeypatch):
    import sys

    app = visual_fixture(tmp_path)
    monkeypatch.setitem(sys.modules, "pypdfium2", None)
    with pytest.raises(ValueError, match="optional local pypdfium2"):
        app.render_page(payload(app))


@pytest.mark.parametrize("kind", ["region", "table", "cell"])
def test_assign_save_reload_resume_preserves_other_fields(tmp_path, kind):
    app = visual_fixture(tmp_path)
    supplied = annotation(app)
    supplied["target"] = {"kind": kind, "region": 0, "table": 0, "cell": 0}
    before = copy.deepcopy(supplied["draft"])
    result = app.annotate(supplied)
    saved = result["documents"][supplied["document_id"]]["draft"]
    destination = (
        before["pages"][0]["regions"][0]
        if kind == "region"
        else before["tables"][0]
        if kind == "table"
        else before["tables"][0]["cells"][0]
    )
    destination["bbox_pdf_user_space_points"] = supplied["bbox"]
    if kind == "table":
        destination["coordinate_basis"] = "pdf_user_space_unrotated"
    assert saved == before
    resumed = tool.Workbench(
        app.manifest,
        app.corpus,
        app.gold,
        app.bundle,
        app.output,
        resume=True,
        root=app.root,
        expected=app.expected,
        allow_synthetic=True,
    )
    assert resumed.view() == result
    assert all(v is None for v in saved["reviewer"].values())
    with pytest.raises(ValueError, match="locked"):
        resumed.legacy(supplied["document_id"])


@pytest.mark.parametrize(
    "case", ["zero", "outside", "nan", "bool", "page", "target_page", "render", "source"]
)
def test_invalid_or_mismatched_assignment_blocked(tmp_path, case):
    app = visual_fixture(tmp_path)
    supplied = annotation(app)
    before = app.state_path.read_bytes()
    if case == "zero":
        supplied["bbox"][2] = supplied["bbox"][0]
    elif case == "outside":
        supplied["bbox"][0] = -1
    elif case == "nan":
        supplied["bbox"][0] = float("nan")
    elif case == "bool":
        supplied["bbox"][0] = True
    elif case == "page":
        supplied["page_identity"] = {"page_number": 2}
    elif case == "target_page":
        supplied["draft"]["tables"][0]["page_number"] = 2
        supplied["target"] = {"kind": "table", "table": 0}
    elif case == "source":
        app.pdf(supplied["document_id"]).write_bytes(b"changed public synthetic source")
    else:
        supplied["render_id"] = "forged"
    with pytest.raises(ValueError):
        app.annotate(supplied)
    assert before == app.state_path.read_bytes()


def test_frozen_annotation_rejected(tmp_path):
    app, parts = fixture(tmp_path)
    seal(app, parts)
    supplied = payload(app)
    supplied.update(render_id=app.render_page(supplied)["render_id"])
    with pytest.raises(ValueError, match="frozen"):
        app.annotate(supplied)


def test_visual_routes_use_existing_security_boundary(tmp_path):
    app = visual_fixture(tmp_path)
    with tool.ReviewServer(app) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for route in ("render", "annotate"):
                assert request(server, route)[0] == 403
                assert (
                    request(
                        server,
                        route,
                        method="POST",
                        payload=payload(app),
                        headers={"X-Review-Token": "wrong"},
                    )[0]
                    == 409
                )
                assert (
                    request(
                        server,
                        route,
                        method="POST",
                        payload=payload(app),
                        headers={"Origin": "https://attacker.invalid"},
                    )[0]
                    == 409
                )
            status, headers, body = request(server, "render", method="POST", payload=payload(app))
            assert status == 200 and headers["Cache-Control"] == "no-store"
            assert request(server, "annotation.js")[0] == 200
            assert set(json.loads(body)) == {
                "document_id",
                "page",
                "page_identity",
                "source_sha256",
                "width",
                "height",
                "scale",
                "renderer",
                "render_id",
                "png_base64",
            }
            assert request(server, "legacy?document_id=c1-0001")[0] == 403
            assert request(server, "predictions")[0] == 403
        finally:
            server.shutdown()
            thread.join(timeout=5)


def test_browser_rendered_mouse_selection(tmp_path):
    node = os.environ.get("ML30_NODE")
    if not node or not os.environ.get("ML30_NODE_MODULES"):
        pytest.skip("Set ML30_NODE and ML30_NODE_MODULES for the actual browser path")
    app = visual_fixture(tmp_path)
    with tool.ReviewServer(app) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            subprocess.run(
                [
                    node,
                    str(Path(__file__).with_name("pdf_review_visual.browser.cjs")),
                    f"http://127.0.0.1:{server.server_port}/{server.token}/",
                ],
                check=True,
                timeout=120,
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
    saved = app.view()["documents"]["c1-0001"]["draft"]
    assert saved["pages"][0]["regions"][0]["bbox_pdf_user_space_points"] == pytest.approx(
        [60, 100, 180, 200], abs=0.6
    )
    assert not app.state["exposed"]
