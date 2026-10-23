from __future__ import annotations

import zipfile

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from tools.extraction_quality import office_readiness_oracle as oracle
from tools.extraction_quality import readiness_release as release
from tools.extraction_quality.readiness_io import atomic, cached, confined


def package(tmp_path, files):
    path = tmp_path / "original.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def workbook(tmp_path, cells):
    return package(
        tmp_path,
        {
            "xl/workbook.xml": f'<workbook xmlns="{oracle.S}" xmlns:r="{oracle.R}">'
            '<workbookPr date1904="1"/><sheets><sheet name="Data" sheetId="7" r:id="s1"/>'
            "</sheets></workbook>",
            "xl/_rels/workbook.xml.rels": '<Relationships><Relationship Id="s1" '
            'Type="urn:test/worksheet" Target="worksheets/s1.xml"/>'
            '<Relationship Id="ss" Type="urn:test/sharedStrings" Target="strings.xml"/>'
            '<Relationship Id="st" Type="urn:test/styles" Target="styles.xml"/></Relationships>',
            "xl/strings.xml": f'<sst xmlns="{oracle.S}"><si><t>literal</t></si></sst>',
            "xl/styles.xml": f'<styleSheet xmlns="{oracle.S}"><numFmts>'
            '<numFmt numFmtId="14" formatCode="yyyy-mm-dd"/></numFmts>'
            '<cellXfs><xf numFmtId="14"/></cellXfs></styleSheet>',
            "xl/worksheets/s1.xml": f'<worksheet xmlns="{oracle.S}"><sheetData><row r="1">'
            + cells
            + '</row></sheetData><mergeCells><mergeCell ref="A1:B1"/></mergeCells></worksheet>',
        },
    )


def test_stored_zero_blank_missing_formula_cache_and_format(tmp_path):
    path = workbook(
        tmp_path,
        '<c r="A1"><v>0</v></c><c r="B1"/>'
        '<c r="C1"><f>1-1</f><v>0</v></c><c r="D1"><f>1+1</f></c>'
        '<c r="E1"><f>1+1</f><v/></c><c r="F1" t="e"><v>#DIV/0!</v></c>'
        '<c r="G1" t="s"><v>0</v></c>',
    )
    value = oracle.observe(path, "e2-office-test", corpus.sha256(path), "xlsx")
    sheet = value["observations"]["sheets"][0]
    a, b, c, d, e, f, g = sheet["cells"]
    assert a["stored_v"] == "0" and a["stored_v_present"]
    assert b["stored_v"] is None and not b["stored_v_present"]
    assert [x["cache_state"] for x in (c, d, e)] == ["PRESENT", "MISSING", "EMPTY"]
    assert f["stored_type"] == "e" and g["resolved_string"] == "literal"
    assert a["num_format"] == "yyyy-mm-dd" and a["display_value"] is None
    assert sheet["merges"] == ["A1:B1"]
    assert value["human_reviewed"] is False and value["reviewer"] is None
    assert all(x["locator"]["sheet_id"] == "7" for x in sheet["cells"])


@pytest.mark.parametrize(
    "cells",
    [
        '<c r="A1"/><c r="A1"/>',
        '<c r="XFE1"/>',
        '<c r="A1048577"/>',
        '<c r="A1" t="s"><v>99</v></c>',
        '<c r="A1"><v>1</v><v>2</v></c>',
    ],
)
def test_bad_workbook_rejected(tmp_path, cells):
    path = workbook(tmp_path, cells)
    with pytest.raises(ValueError):
        oracle.observe(path, "e2-office-test", corpus.sha256(path), "xlsx")


def test_docx_physical_order_nested_merge_notes_and_true_locators(tmp_path):
    path = package(
        tmp_path,
        {
            "word/document.xml": f'<w:document xmlns:w="{oracle.W}"><w:body>'
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Title</w:t>'
            '<w:footnoteReference w:id="2"/></w:r></w:p><w:tbl><w:tr><w:tc>'
            '<w:tcPr><w:gridSpan w:val="2"/><w:vMerge w:val="restart"/></w:tcPr>'
            "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Nested</w:t></w:r></w:p></w:tc>"
            "</w:tr></w:tbl></w:tc></w:tr></w:tbl></w:body></w:document>",
            "word/_rels/document.xml.rels": '<Relationships><Relationship Id="n1" '
            'Type="urn:test/footnotes" Target="footnotes.xml"/></Relationships>',
            "word/footnotes.xml": f'<w:footnotes xmlns:w="{oracle.W}"><w:footnote w:id="2">'
            "<w:p><w:r><w:t>Note</w:t></w:r></w:p></w:footnote></w:footnotes>",
        },
    )
    value = oracle.observe(path, "e2-office-test", corpus.sha256(path), "docx")
    parts = value["observations"]["parts"]
    rows = parts["word/document.xml"]["elements"]
    assert rows[0]["native_t_text"] == "Title"
    assert sum(r["kind"] == "tbl" for r in rows) == 2
    assert any(r["kind"] == "gridSpan" for r in rows)
    assert "word/footnotes.xml" in parts
    assert value["observations"]["page_numbers"] is None
    assert len({r["locator"]["xml_path"] for r in rows}) == len(rows)


@pytest.mark.parametrize(
    "files",
    [
        {"../escape.xml": "x"},
        {"x.xml": '<!DOCTYPE a [<!ENTITY b "bad">]><a>&b;</a>'},
        {"x.xml": b"\xff\xfe" + "<!DOCTYPE a><a/>".encode("utf-16-le")},
        {"x.xml": "<a>"},
    ],
)
def test_unsafe_or_malformed_package(tmp_path, files):
    path = package(tmp_path, files)
    with pytest.raises((ValueError, oracle.ET.ParseError)):
        with oracle.Package(path) as pkg:
            pkg.xml("x.xml")


def test_duplicate_zip(tmp_path):
    path = package(tmp_path, {"x.xml": "<x/>"})
    with pytest.warns(UserWarning), zipfile.ZipFile(path, "a") as archive:
        archive.writestr("x.xml", "<y/>")
    with pytest.raises(ValueError):
        oracle.Package(path)


def test_wrong_sha_rejected_before_reading(tmp_path):
    path = package(tmp_path, {})
    with pytest.raises(ValueError, match="source identity"):
        oracle.observe(path, "e2-office-test", "0" * 64, "docx")


def test_checkpoint_interruption_binding_and_tamper(tmp_path):
    def interrupted():
        raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError):
        cached(tmp_path, "stage", {"sha": "a"}, interrupted)
    assert not (tmp_path / "stage.checkpoint.json").exists()
    atomic(tmp_path / "stage.json.tmp", {"partial": True})
    result, hit = cached(tmp_path, "stage", {"sha": "a"}, lambda: {"complete": True})
    assert not hit and result["complete"]
    assert cached(tmp_path, "stage", {"sha": "a"}, interrupted)[1]
    with pytest.raises(ValueError):
        cached(tmp_path, "stage", {"sha": "b"}, interrupted)
    atomic(tmp_path / "stage.json", {"tamper": True})
    with pytest.raises(ValueError):
        cached(tmp_path, "stage", {"sha": "a"}, interrupted)


@pytest.mark.parametrize("relative", ["../outside", "C:/outside", "/outside", "x:y"])
def test_unsafe_paths(tmp_path, relative):
    with pytest.raises(ValueError):
        confined(tmp_path, relative)


def test_symlink_rejected(tmp_path):
    target = tmp_path / "target"
    target.write_text("data")
    link = tmp_path / "link"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Windows host lacks symlink privilege")
    with pytest.raises(ValueError):
        confined(tmp_path, "link")


def test_unknown_rights_remain_quarantined():
    assert release.rights({"local_evaluation": True})["new_annotation"] is None
    assert release.rights({})["annotation_disposition"] == "QUARANTINE"
    with pytest.raises(ValueError):
        release.rights(
            {}, {"disposition": "admit", "annotation_use": True, "adaptation_granted": None}
        )


def test_blank_and_glyph_match_never_certify_gold():
    original = {
        "item_id": "cell1",
        "source_id": "c1-0033",
        "source_sha256": "a" * 64,
        "kind": "cell",
        "proposed_text": "",
        "uncertainty": "ambiguous_span",
    }
    inventory = [{"item_id": "cell1", "original_proposal": original, "field_admission": "LIMITED"}]
    probe = {
        "documents": [
            {"cell_findings": [{"reference_item_id": "cell1", "glyph_correspondence": True}]}
        ]
    }
    row = release.pdf_items(inventory, {"documents": []}, probe)[0]
    assert row["suspected_blank"] and not row["independent_gold"]
    assert row["state"] == "UNRESOLVED" and row["correction"] is None
    with pytest.raises(ValueError):
        release.pdf_items(inventory * 2, {"documents": []}, probe)


def test_duplicate_json_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"x": {"a":1,"a":2}}')
    with pytest.raises(ValueError):
        corpus.read_json(path)


def test_family_and_source_join_fail_closed():
    source = {
        "id": "c1-0001",
        "sha256": "a",
        "family": "f-a",
        "rights": {},
        "language": ["en"],
        "metadata": {},
        "gold": {"extraction": False},
        "warnings": [],
        "error": None,
    }
    guard = {
        "sample_id": "e2-c1-0001",
        "source_sha256": "a",
        "family_id": "f-a",
        "development_eligible_against_test_families": False,
    }
    row = release.join_population({"population": [source]}, {"rows": [guard]}, {"candidates": []})[
        0
    ]
    assert row["reserved_qa_family"] and row["split"] == "dev"
    guard["source_sha256"] = "b"
    with pytest.raises(ValueError):
        release.join_population({"population": [source]}, {"rows": [guard]}, {"candidates": []})
