"""Actual OOXML note references must survive lexical decimal-ID differences."""

import pytest

from doclens_ai.chunking import ChunkingConfig, ChunkingStrategy, chunk_document
from doclens_ai.chunking.core import _build_source_units
from doclens_ai.extraction import extract_file
from tests.unit.test_docx_footnote_candidate import note, package


@pytest.mark.parametrize("note_id,reference_id", [("7", "07"), ("007", "+7"), ("0", "-0")])
def test_equivalent_note_ids_keep_reference_context_and_lexical_source_ids(
    tmp_path, note_id, reference_id
):
    result = extract_file(package(tmp_path, notes=note(note_id), references=(reference_id,)))
    assert result.note_references[0].note_id == reference_id
    assert result.blocks[-1].source.note_id == note_id
    units = _build_source_units(result)
    note_unit = next(u for u in units if u.source.note_id == note_id and u.text_block_map)
    assert note_unit.context_ids == ("docx-note-reference:0",)
    outcome = chunk_document(
        result,
        document_id="synthetic",
        config=ChunkingConfig(strategy=ChunkingStrategy.STRUCTURE_AWARE, allow_needs_review=True),
    )
    note_chunk = next(c for c in outcome.chunks if "Synthetic note 007.50" in c.text)
    assert f"footnote_reference={reference_id}" in note_chunk.text
    assert any(s.source.note_id == reference_id for s in note_chunk.provenance)


def test_distinct_note_ids_do_not_gain_reference_context(tmp_path):
    result = extract_file(package(tmp_path, notes=note("8"), references=("7",)))
    unit = next(u for u in _build_source_units(result) if u.source.note_id == "8")
    assert unit.context_ids == ()
