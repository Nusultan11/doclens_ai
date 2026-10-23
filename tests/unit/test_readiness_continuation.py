"""Regressions for defects discovered while closing the private release."""

from __future__ import annotations

import zipfile

import pytest

from doclens_ai.eda import corpus_v2 as corpus
from tools.extraction_quality import office_readiness_oracle as oracle
from tools.extraction_quality import readiness_evaluator as evaluator


def package(tmp_path, files):
    path = tmp_path / "source.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return path


def test_docx_namespaced_paths_do_not_alias(tmp_path):
    path = package(
        tmp_path,
        {
            "word/document.xml": f'<w:document xmlns:w="{oracle.W}" '
            'xmlns:a="urn:a" xmlns:b="urn:b">'
            "<w:body><a:wrap><w:p><w:r><w:t>first</w:t></w:r></w:p></a:wrap>"
            "<b:wrap><w:p><w:r><w:t>second</w:t></w:r></w:p></b:wrap></w:body></w:document>"
        },
    )
    value = oracle.observe(path, "source", corpus.sha256(path), "docx")
    records = value["observations"]["parts"]["word/document.xml"]["elements"]
    paths = [r["locator"]["xml_path"] for r in records]
    assert len(set(paths)) == len(paths)


def test_docx_relationship_part_root_must_match(tmp_path):
    path = package(
        tmp_path,
        {
            "word/document.xml": f'<w:document xmlns:w="{oracle.W}"><w:body/></w:document>',
            "word/_rels/document.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="h1" Type="{oracle.R}/header" Target="header1.xml"/>'
            "</Relationships>",
            "word/header1.xml": f'<w:document xmlns:w="{oracle.W}"/>',
        },
    )
    with pytest.raises(ValueError):
        oracle.observe(path, "source", corpus.sha256(path), "docx")


def test_xlsx_nonzero_style_without_styles_is_invalid(tmp_path):
    path = package(
        tmp_path,
        {
            "xl/workbook.xml": f'<workbook xmlns="{oracle.S}" xmlns:r="{oracle.R}">'
            '<sheets><sheet name="Data" sheetId="1" r:id="s1"/></sheets></workbook>',
            "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="s1" Type="{oracle.R}/worksheet" Target="worksheets/s1.xml"/>'
            "</Relationships>",
            "xl/worksheets/s1.xml": f'<worksheet xmlns="{oracle.S}"><sheetData><row r="1">'
            '<c r="A1" s="3"><v>0</v></c></row></sheetData></worksheet>',
        },
    )
    with pytest.raises(ValueError):
        oracle.observe(path, "source", corpus.sha256(path), "xlsx")


def prediction(kind="pdf_cell", status="success", failure=None):
    return evaluator.Predictions.model_validate(
        {
            "version": "readiness-predictions-1.0",
            "model_identity": "synthetic-regression",
            "predictions": [
                {
                    "source_id": "source",
                    "source_sha256": "a" * 64,
                    "status": status,
                    "failure": failure,
                    "observations": []
                    if status == "failed"
                    else [{"kind": kind, "locator": {"page": 1}, "fields": {"text": "0"}}],
                }
            ],
        }
    )


def source():
    return {
        "id": "source",
        "sha256": "a" * 64,
        "format": "xlsx",
        "split": "dev",
        "rights": {"local_evaluation": True, "new_annotation": True},
    }


def test_prediction_kind_must_match_original_format():
    with pytest.raises(ValueError):
        evaluator.compare([source()], prediction(), {})


def test_failure_reason_is_retained():
    result = evaluator.compare([source()], prediction(status="failed", failure="timeout"), {})
    assert result["rows"][0]["failure"] == "timeout"
