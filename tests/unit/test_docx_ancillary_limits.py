"""The bounded note reader must not turn resource rejections into corruption."""

from dataclasses import replace

import pytest

from doclens_ai.extraction import ErrorCategory, ExtractionStatus, extract_file
from doclens_ai.extraction import docx_footnote_candidate as notes
from tests.unit.test_docx_footnote_candidate import note, package, paragraph


@pytest.mark.parametrize(
    "limits",
    [
        {"max_characters": 8},
        {"max_notes": 1},
        {"max_references": 1},
        {"max_paragraphs": 1},
        {"max_nodes": 2},
        {"max_depth": 2},
        {"max_entry_bytes": 8},
        {"max_expanded_bytes": 8},
    ],
)
def test_ancillary_resource_rejections_retain_their_failure_category(tmp_path, monkeypatch, limits):
    path = package(
        tmp_path,
        notes=note("7", extra=paragraph("Second paragraph")) + note("8"),
        references=("7", "8"),
    )
    reader = notes.extract_footnotes
    monkeypatch.setattr(
        notes,
        "extract_footnotes",
        lambda source: reader(source, limits=replace(notes.FootnoteLimits(), **limits)),
    )

    result = extract_file(path)

    assert result.status is ExtractionStatus.FAILED
    assert result.error_category is ErrorCategory.LIMIT_EXCEEDED
    assert not result.blocks and not result.note_references
