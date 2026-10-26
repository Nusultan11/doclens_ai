from __future__ import annotations

import copy
import json
import zipfile

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import blind_review_batch as batch
from tools.extraction_quality import office_readiness_oracle as office
from tools.extraction_quality.readiness_io import atomic


def source(key, fmt, family=None):
    digest = fingerprint(key)
    return {
        "id": key,
        "format": fmt,
        "family": family or "f-" + key,
        "sha256": digest,
        "split": "dev",
        "reserved_qa_family": False,
        "rights": {"local_evaluation": True, "new_annotation": True},
        "metadata": {
            "nested_tables": 1,
            "body_tables": 2,
            "ancillary_xml_text_characters": 3,
            "stored_xml_cells": 10,
        },
        "source_reference": {
            "path": f"originals/{key}.{fmt}",
            "sha256": digest,
            "size_bytes": 100,
            "format": fmt,
        },
    }


def population():
    return [
        source(k, fmt)
        for k, fmt in (
            ("c1-0033", "pdf"),
            ("c1-0040", "pdf"),
            ("e2-doc", "docx"),
            ("e2-sheet", "xlsx"),
        )
    ]


def test_selection_determinism_family_alternatives_and_complete_denominator():
    rows = population()
    alternative = source("e2-duplicate-family", "xlsx", rows[2]["family"])
    alternative["metadata"]["stored_xml_cells"] = 1000
    rows += [alternative, source("e2-extra", "xlsx")]
    result = batch.select(rows)
    assert result == batch.select(list(reversed(rows)))
    assert result["selected"] == [*batch.PDF_IDS, "e2-doc", "e2-extra"]
    assert len(result["decisions"]) == len(rows)
    assert result["family_completeness"] == "NOT_EVALUATED"
    assert sum(d["selected"] for d in result["decisions"]) == 4


@pytest.mark.parametrize(
    "field,value",
    [
        ("rights", {"local_evaluation": True, "new_annotation": None}),
        ("rights", {"local_evaluation": None, "new_annotation": True}),
        ("split", "sealed_candidate"),
        ("split", "test"),
        ("reserved_qa_family", True),
        ("reserved_qa_family", None),
        ("metadata", {}),
    ],
)
def test_ineligible_office_is_never_selected(field, value):
    rows = population()
    rows[2][field] = value
    with pytest.raises(ValueError):
        batch.select(rows)


@pytest.mark.parametrize(
    "link",
    ["family", "related_families", "near_duplicate_group", "normalized_text_sha256", "sha256"],
)
def test_connected_reserved_families_are_excluded(link):
    rows = population()
    reserved = source("e2-reserved", "docx")
    reserved["reserved_qa_family"] = True
    if link == "family":
        reserved[link] = rows[2][link]
    elif link == "related_families":
        reserved[link] = [rows[2]["family"]]
    elif link == "sha256":
        reserved["sha256"] = rows[2]["sha256"]
        reserved["source_reference"]["sha256"] = rows[2]["sha256"]
    else:
        rows[2][link] = reserved[link] = "a" * 64
    with pytest.raises(ValueError):
        batch.select([*rows, reserved])


def test_missing_pdf_duplicate_identity_wrong_binding_and_budget():
    for rows in (population()[1:], population() * 2):
        with pytest.raises(ValueError):
            batch.select(rows)
    rows = population()
    rows[2]["source_reference"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA"):
        batch.select(rows)
    rows = population()
    rows[3]["metadata"]["stored_xml_cells"] = 20_001
    with pytest.raises(ValueError):
        batch.select(rows)


def test_reused_pdf_families_must_be_disjoint():
    rows = population()
    rows[1]["related_families"] = [rows[0]["family"]]
    with pytest.raises(ValueError, match="PDF families overlap"):
        batch.select(rows)


def package(path, files):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in files.items():
            archive.writestr(name, value)


def docx(path):
    package(
        path,
        {
            "word/document.xml": f'<w:document xmlns:w="{office.W}"><w:body><w:p><w:r>'
            "<w:t>PRIVATE_SENTINEL</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:tbl><w:tr><w:tc>"
            "<w:p/></w:tc></w:tr></w:tbl></w:tc></w:tr></w:tbl></w:body></w:document>",
            "word/_rels/document.xml.rels": '<Relationships><Relationship Id="n" '
            'Type="urn:test/footnotes" Target="footnotes.xml"/></Relationships>',
            "word/footnotes.xml": f'<w:footnotes xmlns:w="{office.W}"><w:footnote w:id="2">'
            "<w:p><w:r><w:t>SECRET_NOTE</w:t></w:r></w:p></w:footnote></w:footnotes>",
        },
    )


def xlsx(path, address="A1", cells=None):
    package(
        path,
        {
            "xl/workbook.xml": f'<workbook xmlns="{office.S}" xmlns:r="{office.R}">'
            '<sheets><sheet name="PRIVATE_SHEET" sheetId="7" r:id="s"/></sheets></workbook>',
            "xl/_rels/workbook.xml.rels": '<Relationships><Relationship Id="s" '
            'Type="urn:test/worksheet" Target="worksheets/s.xml"/></Relationships>',
            "xl/worksheets/s.xml": f'<worksheet xmlns="{office.S}"><sheetData><row r="1">'
            + (
                cells
                if cells is not None
                else f'<c r="{address}"><f>PRIVATE_FORMULA</f><v>123</v></c>'
            )
            + "</row></sheetData></worksheet>",
        },
    )


def test_physical_locators_no_literal_or_semantic_leakage(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("machine oracle must never be called")

    monkeypatch.setattr(office, "observe", forbidden)
    monkeypatch.setattr(office, "docx", forbidden)
    monkeypatch.setattr(office, "xlsx", forbidden)
    dp, xp = tmp_path / "d.docx", tmp_path / "s.xlsx"
    docx(dp)
    xlsx(xp)
    locators = batch.office_locators(dp, "docx")
    assert any(loc["part"] == "word/footnotes.xml" for loc in locators)
    assert any(loc["xml_path"].count("w:tbl") == 2 for loc in locators)
    sheet = batch.office_sheet(source("e2-sheet", "xlsx"), xp)
    assert sheet["physical_locators"] == [
        {"part": "xl/worksheets/s.xml", "sheet_id": "7", "cell": "A1"}
    ]
    assert all(v is None for v in sheet["review_template"].values())
    assert "PRIVATE" not in json.dumps(sheet) and "123" not in json.dumps(sheet)
    assert "SECRET" not in json.dumps(locators)
    assert not sheet["human_reviewed"] and sheet["reviewer"] is None


@pytest.mark.parametrize("address", ["A0", "A01", "a1", "XFE1", "A1048577", "../A1"])
def test_invalid_cell_locator_rejected(tmp_path, address):
    path = tmp_path / "s.xlsx"
    xlsx(path, address)
    with pytest.raises((ValueError, KeyError)):
        batch.office_locators(path, "xlsx")


def test_duplicate_cell_locator_rejected(tmp_path):
    path = tmp_path / "s.xlsx"
    xlsx(path, cells='<c r="A1"/><c r="A1"/>')
    with pytest.raises(ValueError, match="duplicate"):
        batch.office_locators(path, "xlsx")


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "ROOT", tmp_path)
    code = tmp_path / "tools/batch.py"
    code.parent.mkdir()
    code.write_text("fixture code")
    monkeypatch.setattr(batch, "__file__", str(code))
    release_root = tmp_path / "evaluation-output/release"
    release_root.mkdir(parents=True)
    rows = population()
    for row in rows:
        path = tmp_path / row["source_reference"]["path"]
        if row["format"] == "docx":
            docx(path)
        elif row["format"] == "xlsx":
            xlsx(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"%PDF-1.7 synthetic original")
        row["sha256"] = row["source_reference"]["sha256"] = corpus.sha256(path)
        # Distinct PDF bytes are required for family separation.
        if row["id"] == "c1-0040":
            path.write_bytes(b"%PDF-1.7 other synthetic original")
            row["sha256"] = row["source_reference"]["sha256"] = corpus.sha256(path)
        row["source_reference"]["size_bytes"] = path.stat().st_size
    atomic(release_root / "effective-matrix.json", {"population": rows})
    atomic(release_root / "RELEASE.json", {"fixture": True})
    monkeypatch.setattr(batch.release, "verify", lambda _: {"integrity": "PASS"})
    monkeypatch.setattr(batch, "pdf_inputs", lambda: ({"review/pdf.json": b"{}\n"}, {}))
    monkeypatch.setattr(batch, "attribution", lambda *_: b"synthetic attribution\n")
    output = tmp_path / "evaluation-output/batch"
    batch.prepare(output, release_root)
    return output, release_root, rows


def reseal(output):
    manifest = corpus.read_json(output / "BATCH.json")
    for relative in manifest["artifact_sha256"]:
        manifest["artifact_sha256"][relative] = corpus.sha256(output / relative)
    manifest.pop("fingerprint")
    manifest["fingerprint"] = fingerprint(manifest)
    atomic(output / "BATCH.json", manifest)


def test_deterministic_reproduction_and_existing_output_rejection(frozen):
    output, release_root, _ = frozen
    other = output.with_name("reproduction")
    a = batch.verify(output)
    b = batch.prepare(other, release_root)
    assert a == b
    assert {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()} == {
        p.relative_to(other): p.read_bytes() for p in other.rglob("*") if p.is_file()
    }
    with pytest.raises(ValueError, match="fresh"):
        batch.prepare(output, release_root)


@pytest.mark.parametrize("mutation", ["review", "prediction", "literal", "locator", "source_sha"])
def test_forgery_and_leakage_rejected_even_with_refreshed_hashes(frozen, mutation):
    output, _, _ = frozen
    path = output / "reviewer/review/e2-sheet/independent.json"
    sheet = corpus.read_json(path)
    if mutation == "review":
        sheet.update(state="REVIEWED", reviewer="forged person", human_reviewed=True)
    elif mutation == "prediction":
        sheet["machine_predictions"] = {"value": "123"}
    elif mutation == "literal":
        sheet["review_template"]["literal"] = "machine value"
    elif mutation == "source_sha":
        sheet["source_sha256"] = "0" * 64
    else:
        sheet["physical_locators"][0]["cell"] = "XFE1"
    atomic(path, sheet)
    reseal(output)
    with pytest.raises(ValueError, match="forged review|invalid locator"):
        batch.verify(output)


@pytest.mark.parametrize(
    "name", ["predictions.json", "nested/BATCH.json", "legacy-assertions.json"]
)
def test_extra_artifact_leakage_rejected(frozen, name):
    output, _, _ = frozen
    atomic(output / "reviewer" / name, {"secret": "prediction"})
    with pytest.raises(ValueError, match="unexpected artifact"):
        batch.verify(output)


def test_wrong_original_sha_rejected(frozen):
    output, release_root, rows = frozen
    (batch.ROOT / rows[2]["source_reference"]["path"]).write_bytes(b"changed original")
    with pytest.raises(ValueError):
        batch.verify(output)
    with pytest.raises(ValueError):
        batch.prepare(output.with_name("wrong-sha"), release_root)


def test_forged_batch_claims_rejected(frozen):
    output, _, _ = frozen
    manifest = corpus.read_json(output / "BATCH.json")
    manifest["human_reviews"] = 1
    atomic(output / "BATCH.json", manifest)
    reseal(output)
    with pytest.raises(ValueError, match="forged review"):
        batch.verify(output)


def test_selection_manifest_cannot_hide_exclusions(frozen):
    output, _, _ = frozen
    path = output / "selection.json"
    value = copy.deepcopy(corpus.read_json(path))
    value["decisions"].pop()
    atomic(path, value)
    reseal(output)
    with pytest.raises(ValueError):
        batch.verify(output)


@pytest.mark.parametrize("relative", ["../escape", "/outside", "C:/outside", "x:y"])
def test_existing_path_confinement_reused(tmp_path, relative):
    with pytest.raises(ValueError):
        batch.confined(tmp_path, relative)


def test_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / "forged.json"
    path.write_text('{"reviewer":null,"reviewer":"forged"}')
    with pytest.raises(ValueError, match="duplicate"):
        corpus.read_json(path)
