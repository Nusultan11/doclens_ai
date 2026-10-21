"""Ambiguous JSON annotations must fail at the public Fidelity Gold loader."""

import json

import pytest

from doclens_ai.extraction.fidelity_gold import GoldError, load_gold
from tests.unit.test_extraction_fidelity import _gold


@pytest.mark.parametrize("field", ["review_status", "page_number", "escaped_page_number"])
def test_duplicate_gold_keys_are_rejected_before_model_parsing(tmp_path, field):
    text = json.dumps(_gold())
    if field == "review_status":
        text = text.replace(
            '"review_status": "reviewed"',
            '"review_status": "PRIVATE_DRAFT", "review_status": "reviewed"',
        )
    else:
        key = "page_number" if field == "page_number" else "page_\\u006eumber"
        text = text.replace('"page_number": 1', f'"page_number": 999, "{key}": 1')
    path = tmp_path / "synthetic.jsonl"
    path.write_text(text + "\n", encoding="utf8")
    with pytest.raises(GoldError) as caught:
        load_gold(path, {"c1-0001": ("a" * 64, 100, "pdf")}, allow_synthetic=True)
    assert "PRIVATE_DRAFT" not in str(caught.value)
