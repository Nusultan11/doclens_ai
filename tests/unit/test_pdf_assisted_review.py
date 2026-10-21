"""Public synthetic plans and PDF drawings only; no private annotations or rights."""

from __future__ import annotations

import copy
import csv
import json
import os
import subprocess
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("pdfplumber")
pytest.importorskip("pypdfium2")
pytest.importorskip("PIL")

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from tests.unit.test_pdf_cell_recovery import reference
from tests.unit.test_pdf_review_eligibility import fixture as rights_fixture
from tools.extraction_quality import pdf_assisted_review as tool
from tools.extraction_quality import pdf_cell_recovery as recovery
from tools.extraction_quality import pdf_review_validation as validation
from tools.extraction_quality import pdf_table_review_packet as packet


def band_source(path: Path) -> tuple[Path, dict]:
    writer = PdfWriter()
    page = writer.add_blank_page(300, 200)
    font = writer._add_object(
        DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Courier"),
            }
        )
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"\n".join(
            [
                b"1 .8 0 rg 100.3 100.3 90.05 40 re f",  # First path is the colored band.
                b"0 0 0 rg 40 100 200.6 .6 re f 40 140 200.6 .6 re f",
                b"40 100 .6 40.6 re f 100 100 .6 40.6 re f 240 100 .6 40.6 re f",
                b"190 40 .6 50 re f",  # Lower column alignment, no upper printed divider.
                b"BT /F1 10 Tf 1 0 0 1 50 120 Tm (W1) Tj ET",
                b"BT /F1 10 Tf 1 0 0 1 120 120 Tm (W2) Tj ET",
                b"BT /F1 10 Tf 1 0 0 1 205 70 Tm (SUM) Tj ET",
            ]
        )
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(path)
    cells = [
        dict(
            review_cell_id=f"band-{i}",
            row=0,
            column=i,
            row_span=1,
            column_span=1,
            bbox_pdf_user_space_points=box,
        )
        for i, box in enumerate([[40.3, 100.3, 100.3, 140.3], [100.3, 100.3, 240.3, 140.3]])
    ]
    import pypdfium2

    with pypdfium2.PdfDocument(path) as doc:
        with closing(doc[0]) as original:
            fill_bbox = list(list(original.get_objects())[0].get_bounds())
    return path, dict(
        table_id="public-band",
        bbox=[40.3, 100.3, 240.3, 140.3],
        row_count=1,
        column_count=2,
        cells=cells,
        region_kind="header_only_ruled_band",
        counting_convention="Public synthetic band",
        partition=dict(
            table_id="public-band",
            cell_id="band-1",
            expected_bbox=cells[1]["bbox_pdf_user_space_points"],
            split_x=190.3,
            new_cell_id="band-2",
            fill_object_index=0,
            expected_fill_bbox=fill_bbox,
            counting_convention="Three synthetic segments",
        ),
    )


def fixture(tmp_path, *, partition=False):
    app, expected, eligibility, rights = rights_fixture(tmp_path)
    drawing = tmp_path / "drawing"
    drawing.mkdir()
    if partition:
        source, table = band_source(drawing / "public.pdf")
        part = table.pop("partition")
        parts = [part]
    else:
        source, candidate, _ = reference(drawing)
        table = dict(
            table_id="public-grid",
            bbox=candidate["context"]["bbox"],
            row_count=2,
            column_count=2,
            cells=[{k: c[k] for k in recovery.GEOMETRY_FIELDS} for c in candidate["cells"]],
            region_kind="regular_ruled_table",
            counting_convention="Public synthetic rows",
        )
        parts = []
    first = rights["candidates"][0]
    target = app.paths[first["document_id"]]
    target.write_bytes(source.read_bytes())
    first.update(
        source_sha256=packet.sha(target),
        source_size_bytes=target.stat().st_size,
        pages=validation.original_pages(target),
    )
    with app.manifest.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[0].update(sha256=first["source_sha256"], size_bytes=str(first["source_size_bytes"]))
    with app.manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    records = [json.loads(line) for line in app.gold.read_text(encoding="utf-8").splitlines()]
    records[0].update(
        source_sha256=first["source_sha256"], source_size_bytes=first["source_size_bytes"]
    )
    app.gold.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    rights.update(manifest_sha256=packet.sha(app.manifest), gold_sha256=packet.sha(app.gold))
    eligibility.write_text(json.dumps(rights), encoding="utf-8")
    expected = replace(
        expected, manifest_sha256=packet.sha(app.manifest), gold_sha256=packet.sha(app.gold)
    )
    recipe = dict(
        source_sha256=first["source_sha256"],
        pages=first["pages"],
        header_row=0,
        language="en",
        tables=[table],
        partitions=parts,
    )
    plan = eligibility.parent / "public-plan.json"
    packet.write_json(
        plan, dict(version="pdf-assisted-plan-v1", documents={first["document_id"]: recipe})
    )
    return app, expected, eligibility, plan, recipe, first


def build(data, name="assisted", **kwargs):
    app, expected, eligibility, plan, _, _ = data
    output = app.root / "evaluation-output" / name
    counts = tool.generate(
        app.manifest,
        app.corpus,
        app.gold,
        eligibility,
        plan,
        packet.sha(plan),
        output,
        expected=expected,
        allow_synthetic=True,
        root=app.root,
        **kwargs,
    )
    return output, counts


def tree(path):
    return {p.relative_to(path).as_posix(): packet.sha(p) for p in path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("partition", [False, True])
def test_original_observations_determinism_and_unsigned_review(tmp_path, partition):
    data = fixture(tmp_path, partition=partition)
    app, _, eligibility, plan, recipe, first = data
    protected = {
        p: p.read_bytes()
        for p in (app.manifest, app.gold, eligibility, plan, app.paths[first["document_id"]])
    }
    one, counts = build(data)
    two, repeated = build(data, "repeat")
    assert counts == repeated and tree(one) == tree(two)
    assert counts["cells"] == (3 if partition else 4)
    payload = tool.read(one / "proposals.json")
    assert not payload["human_review_completed"] and payload["approved"] is None
    assert payload["reviewer_id"] is None and payload["inspection_attestation"] is None
    assert payload["independent_gold"] == "NOT_EVALUATED"
    assert all(i["decision"] is None and i["reviewer_id"] is None for i in payload["items"])
    assert first["document_id"] in {d["document_id"] for d in payload["documents"]}
    assert len(payload["documents"]) == 1  # Blocked second source never copied or analyzed.
    doc = payload["documents"][0]
    assert (
        tool.validate_document(doc, app.paths[first["document_id"]], recipe)["grid_coverage"]
        == "PASS"
    )
    tool.validate_items(payload["documents"], payload["items"])
    if partition:
        band = doc["tables"][0]
        assert band["column_count"] == len(band["cells"]) == 3
        assert band["cells"][1]["bbox_pdf_user_space_points"][2] == 190.3
        empty = band["cells"][2]
        assert empty["literal_text"] == "" and empty["semantic_interpretation"] is None
        assert not any(empty["source_glyph_indices"].values())
        assert band["segmentation_evidence"]["printed_vertical_divider_present"] is False
        assert counts["uncertain_cells"] >= 2
    assert all(p.read_bytes() == original for p, original in protected.items())
    with pytest.raises(ValueError):
        build(data)


@pytest.mark.parametrize(
    "kind",
    [
        "source",
        "page",
        "sha",
        "duplicate",
        "missing",
        "coordinates",
        "body_data",
        "review_status",
        "partition",
        "paint",
        "population",
    ],
)
def test_invalid_or_private_embedded_plan_inputs_fail_closed(tmp_path, kind):
    data = fixture(tmp_path, partition=True)
    app, expected, eligibility, path, recipe, first = data
    plan = tool.read(path)
    if kind == "source":
        recipe["source_sha256"] = "0" * 64
    elif kind == "page":
        recipe["pages"][0]["page_number"] = 2
    elif kind == "duplicate":
        recipe["tables"][0]["cells"].append(copy.deepcopy(recipe["tables"][0]["cells"][0]))
    elif kind == "missing":
        recipe["tables"][0]["cells"].pop(0)
    elif kind == "coordinates":
        recipe["tables"][0]["cells"][0]["bbox_pdf_user_space_points"][0] = -1
    elif kind == "body_data":
        recipe["tables"][0]["cells"][0]["literal_text"] = "FABRICATED"
    elif kind == "review_status":
        recipe["human_review_completed"] = True
    elif kind == "partition":
        recipe["partitions"][0]["split_x"] = 280
    elif kind == "paint":
        recipe["partitions"][0]["expected_fill_bbox"][2] -= 10
    elif kind == "population":
        plan["documents"]["unexpected"] = copy.deepcopy(recipe)
    if kind != "population":
        plan["documents"][first["document_id"]] = recipe
    path.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises((ValueError, StopIteration)):
        if kind == "sha":
            tool.generate(
                app.manifest,
                app.corpus,
                app.gold,
                eligibility,
                path,
                "0" * 64,
                app.root / "evaluation-output/assisted",
                expected=expected,
                allow_synthetic=True,
                root=app.root,
            )
        else:
            build(data)
    assert not (app.root / "evaluation-output/assisted/COMPLETE.json").exists()


def test_corrections_preserved_in_csv_and_escaped_html(tmp_path):
    data = fixture(tmp_path)
    one, _ = build(data)
    payload = tool.read(one / "proposals.json")
    record = tool.csv_row(payload["items"][0])
    attack = '<img src="https://example.invalid/leak" onerror="alert(1)">'
    record.update(
        decision="correct",
        reviewer_correction=attack,
        reviewer_notes="public correction",
        corrected_bbox="[40,100,140,180]",
    )
    prior = one.parent / "public-decisions.csv"
    with prior.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=tool.FIELDS)
        writer.writeheader()
        writer.writerow(record)
    output, _ = build(data, "carried", decisions_from=prior)
    with (output / "review_decisions.csv").open(encoding="utf-8-sig", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert all(row[k] == record[k] for k in tool.DECISION_FIELDS)
    rendered = (output / "REVIEW.html").read_text(encoding="utf-8")
    assert attack not in rendered and "&lt;img" in rendered
    assert 'value="correct" selected' in rendered
    assert tool.read(output / "proposals.json")["items"][0]["decision"] is None


def test_plan_drift_during_build_never_publishes_complete(tmp_path, monkeypatch):
    data = fixture(tmp_path)
    original = tool.propose

    def drift(*args, **kwargs):
        result = original(*args, **kwargs)
        data[3].write_text("{}", encoding="utf-8")
        return result

    monkeypatch.setattr(tool, "propose", drift)
    with pytest.raises(ValueError, match="changed during build"):
        build(data)
    assert not (data[0].root / "evaluation-output/assisted/COMPLETE.json").exists()


def test_cli_rejection_never_echoes_private_paths(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "assisted",
            *sum(
                (
                    [f"--{n}", "PRIVATE"]
                    for n in (
                        "manifest",
                        "corpus",
                        "gold",
                        "eligibility",
                        "plan",
                        "output",
                        "plan-sha256",
                    )
                ),
                [],
            ),
        ],
    )
    assert tool.main() == 2
    assert "PRIVATE" not in capsys.readouterr().out


def test_offline_browser_review_and_csv_export(tmp_path):
    node = os.environ.get("ML30_NODE")
    if not node or not os.environ.get("ML30_NODE_MODULES"):
        pytest.skip("Local Node/Playwright/Edge browser inputs required")
    output, counts = build(fixture(tmp_path, partition=True))
    run = subprocess.run(
        [node, str(Path(__file__).with_name("pdf_assisted_review.browser.cjs")), str(output)],
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    with (output / "public-edited.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == counts["review_items"]
    assert rows[0]["reviewer_correction"] == "PUBLIC_SYNTHETIC_BROWSER_CORRECTION"
    assert rows[0]["decision"] == "correct" and all(not row["decision"] for row in rows[1:])
