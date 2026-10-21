"""Shared-string values belong to the workbook's actual relationship target."""

import zipfile
from xml.etree import ElementTree as ET

import pytest
from openpyxl import Workbook

from doclens_ai.extraction import ErrorCategory, ExtractionStatus, extract_file
from tests.unit.test_evidence_regressions import rewrite

S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings"
P = "http://schemas.openxmlformats.org/package/2006/relationships"


@pytest.mark.parametrize(
    "relationship", ["internal", "missing", "external", "duplicate", "wrong-root"]
)
def test_shared_strings_use_only_the_relationship_bound_part(tmp_path, relationship):
    path = tmp_path / "strings.xlsx"
    wb = Workbook()
    wb.active["A1"] = "placeholder"
    wb.save(path)
    with zipfile.ZipFile(path) as archive:
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        types = ET.fromstring(archive.read("[Content_Types].xml"))
    if relationship != "missing":
        relation = ET.SubElement(
            rels,
            f"{{{P}}}Relationship",
            {"Id": "strings", "Type": R, "Target": "strings/actual.xml"},
        )
        if relationship == "external":
            relation.set("TargetMode", "External")
        elif relationship == "duplicate":
            ET.SubElement(
                rels,
                f"{{{P}}}Relationship",
                {"Id": "other-strings", "Type": R, "Target": "sharedStrings.xml"},
            )
    for part in ("/xl/sharedStrings.xml", "/xl/strings/actual.xml"):
        ET.SubElement(
            types,
            "{http://schemas.openxmlformats.org/package/2006/content-types}Override",
            {
                "PartName": part,
                "ContentType": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"
                ),
            },
        )
    rewrite(
        path,
        {
            "xl/_rels/workbook.xml.rels": ET.tostring(rels),
            "[Content_Types].xml": ET.tostring(types),
            "xl/sharedStrings.xml": f'<sst xmlns="{S}"><si><t>WRONG 999</t></si></sst>',
            "xl/strings/actual.xml": (
                f'<wrong xmlns="{S}"/>'
                if relationship == "wrong-root"
                else f'<sst xmlns="{S}"><si><t>actual 001.50 kg</t></si></sst>'
            ),
            "xl/worksheets/sheet1.xml": (
                f'<worksheet xmlns="{S}"><sheetData><row r="1">'
                '<c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>'
            ),
        },
    )
    result = extract_file(path)
    if relationship == "internal":
        assert result.status is ExtractionStatus.SUCCESS
        cell = result.sheets[0].cells[0]
        assert cell.value == "actual 001.50 kg" and cell.raw_value == "0"
        assert cell.coordinate == cell.source.cell_coordinate == "A1"
    else:
        assert result.status is ExtractionStatus.FAILED
        assert result.error_category is ErrorCategory.CORRUPT_DOCUMENT
        assert not result.sheets
