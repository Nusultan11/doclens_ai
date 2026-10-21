"""Synthetic regressions for explicitly stored OOXML number format IDs."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from openpyxl import Workbook

from doclens_ai.extraction import ErrorCategory, ExtractionStatus, extract_file
from tests.unit.test_evidence_regressions import rewrite

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _workbook(tmp_path: Path, definitions: str, *, format_id: int = 43) -> Path:
    path = tmp_path / "explicit-format.xlsx"
    Workbook().save(path)
    rewrite(
        path,
        {
            "xl/styles.xml": (
                f'<styleSheet xmlns="{NS}"><numFmts>{definitions}</numFmts>'
                f'<cellXfs count="1"><xf numFmtId="{format_id}"/></cellXfs></styleSheet>'
            ),
            "xl/worksheets/sheet1.xml": (
                f'<worksheet xmlns="{NS}"><sheetData><row r="1">'
                '<c r="A1" s="0" t="n"><v>001.2300</v></c>'
                '<c r="B1" s="0" t="n"><f>A1*2</f><v>2.4600</v></c>'
                "</row></sheetData></worksheet>"
            ),
        },
    )
    return path


@pytest.mark.parametrize("format_id", [0, 5, 6, 14, 23, 42, 43, 44, 163, 164])
def test_explicit_number_format_preserves_code_and_cell_evidence(tmp_path, format_id):
    path = _workbook(
        tmp_path,
        f'<numFmt numFmtId="{format_id}" formatCode="&quot;kg&quot; 0.0000"/>',
        format_id=format_id,
    )
    original = path.read_bytes()

    result = extract_file(path)

    assert result.status is ExtractionStatus.SUCCESS
    assert result.source_sha256 == hashlib.sha256(original).hexdigest()
    assert result.source_size_bytes == len(original)
    assert path.read_bytes() == original
    first, formula = result.sheets[0].cells
    assert (first.value, first.raw_value, first.formula, first.cached_value) == (
        "001.2300",
        "001.2300",
        None,
        None,
    )
    assert (formula.value, formula.raw_value, formula.formula, formula.cached_value) == (
        "2.4600",
        "2.4600",
        "A1*2",
        "2.4600",
    )
    for cell, coordinate, column in ((first, "A1", 0), (formula, "B1", 1)):
        assert cell.number_format_id == format_id
        assert cell.number_format == '"kg" 0.0000'
        assert cell.style_index == 0
        assert cell.coordinate == cell.source.cell_coordinate == coordinate
        assert cell.row_index == cell.source.row_index == 0
        assert cell.column_index == cell.source.column_index == column
        assert cell.source.sheet_index == 0


@pytest.mark.parametrize(
    "definitions",
    [
        '<numFmt numFmtId="-1" formatCode="0"/>',
        '<numFmt formatCode="0"/>',
        '<numFmt numFmtId="bad" formatCode="0"/>',
        '<numFmt numFmtId="43"/>',
        '<numFmt numFmtId="43" formatCode="0"/><numFmt numFmtId="43" formatCode="0.00"/>',
        '<numFmt numFmtId="164" formatCode="0"/><numFmt numFmtId="164" formatCode="0.00"/>',
    ],
)
def test_invalid_explicit_number_formats_still_fail_closed(tmp_path, definitions):
    result = extract_file(_workbook(tmp_path, definitions))

    assert result.status is ExtractionStatus.FAILED
    assert result.error_category is ErrorCategory.CORRUPT_DOCUMENT
    assert not result.sheets
