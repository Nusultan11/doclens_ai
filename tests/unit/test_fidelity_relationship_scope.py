"""A common row/column cannot join cells from distinct source tables or parts."""

import pytest
from pydantic import ValidationError

from tests.unit.test_extraction_fidelity import _gold, _record


@pytest.mark.parametrize("dimension", ["block_index", "part_index"])
def test_relationships_cannot_cross_block_or_ancillary_part_scope(dimension):
    data = _gold("docx")
    source = {
        "region": "header",
        "part_index": 0,
        "block_index": 0,
        "table_index": 0,
        "row_index": 0,
        "column_index": 0,
    }
    other = {**source, "column_index": 1}
    other[dimension] = 1
    data["anchors"] = [
        {"anchor_id": "a1", "text": "entity", "source": source},
        {"anchor_id": "a2", "text": "001.50", "source": other},
    ]
    data["table_relationships"] = [{"left": "a1", "right": "a2", "relationship": "same_row"}]
    with pytest.raises(ValidationError):
        _record(data)
    other[dimension] = 0
    assert _record(data).table_relationships
