"""Source verification must use the requested PDF block's own text bounds."""

import pytest

from doclens_ai.eda.data_quality_gate import resolve_unit
from doclens_ai.extraction.models import (
    DocumentFormat,
    ExtractionResult,
    ExtractionStatus,
    SourceLocation,
    TextBlock,
)


@pytest.mark.parametrize(
    "block,end,expected",
    [(0, 2, "invalid"), (0, 1, "verified"), (1, 8, "verified"), (9, 1, "not_evaluated")],
)
def test_pdf_source_bounds_do_not_borrow_text_from_other_blocks(block, end, expected):
    result = ExtractionResult(
        "1.1",
        DocumentFormat.PDF,
        ExtractionStatus.SUCCESS,
        "a" * 64,
        100,
        blocks=(
            TextBlock(0, "1", SourceLocation(page_number=1, block_index=0)),
            TextBlock(1, "12345678", SourceLocation(page_number=1, block_index=1)),
        ),
    )
    assert (
        resolve_unit(result, {"page_number": 1, "block_index": block}, start=0, end=end) == expected
    )
