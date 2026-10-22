"""Public in-memory evidence validates scoring and access boundaries."""

from __future__ import annotations

import copy

import pytest

from tools.extraction_quality import pdf_table_source_only_probe as tool


def fixture(monkeypatch):
    bars = [[-0.1, -0.1, 0, 1.1], [-0.1, -0.1, 1.1, 0], [1, -0.1, 1.1, 1.1], [-0.1, 1, 1.1, 1.1]]
    cell = dict(
        face_index=0,
        cell_id="face-0",
        bbox=[0, 0, 1, 1],
        boundary_objects=list(range(4)),
        glyph_indices=[0],
        literal_text="A",
    )
    page = dict(
        page=1,
        cells=[cell],
        source_rules=[dict(source_object_index=i, bbox=b) for i, b in enumerate(bars)],
        source_characters=[dict(text="A")],
        regions=[dict(region_id="region-0", face_indices=[0])],
        closed_faces=1,
        unassigned_nonspace_glyphs=[],
        issues=[],
    )
    doc = dict(
        document_id="public",
        source_sha256="a" * 64,
        cells=[
            dict(
                item_id="ref-a",
                table_id="ref-grid",
                literal_text="A",
                source_text_evidence=dict(source_glyph_indices=dict(pdfplumber=[0])),
            )
        ],
        logical_grids=[{}],
    )
    native = dict(status="success", warnings=[])
    digest = tool.fingerprint(native)
    monkeypatch.setitem(tool.NATIVE_FINGERPRINTS, "public", digest)
    capture = dict(
        probe=dict(source_sha256="a" * 64, status="needs_review", pages=[page]),
        baseline=native,
        baseline_after_fingerprint=digest,
    )
    return doc, capture


def test_source_glyph_identity_maps_without_reference_bbox_or_text_search(monkeypatch):
    doc, capture = fixture(monkeypatch)
    result = tool.score(doc, capture)
    assert result["glyph_correspondences"] == 1
    assert result["literal_observations"] == {"EXACT_LITERAL": 1}
    assert result["baseline_unchanged"] and not result["violations"]
    assert tool.decision([result], True, True) == "PROMOTE_FOR_FURTHER_OFFLINE_EVALUATION"


@pytest.mark.parametrize("mutation", ["coordinate", "literal", "duplicate", "native"])
def test_unsafe_evidence_or_native_loss_rejects(monkeypatch, mutation):
    doc, capture = fixture(monkeypatch)
    cell = capture["probe"]["pages"][0]["cells"][0]
    if mutation == "coordinate":
        cell["bbox"][0] = 99
    elif mutation == "literal":
        cell["literal_text"] = "B"
    elif mutation == "duplicate":
        other = copy.deepcopy(cell)
        other.update(cell_id="duplicate", face_index=1)
        capture["probe"]["pages"][0]["cells"].append(other)
    else:
        capture["baseline_after_fingerprint"] = "0" * 64
    assert tool.decision([tool.score(doc, capture)], True, True) == "REJECT"


def test_missing_or_nondeterministic_results_are_not_promotion():
    row = dict(violations=[], baseline_unchanged=None, glyph_correspondences=None)
    assert tool.decision([row], False, False) == "INCONCLUSIVE"
    row.update(baseline_unchanged=True, glyph_correspondences=0)
    assert tool.decision([row], True, True) == "REJECT"
    row["glyph_correspondences"] = 1
    assert tool.decision([row], True, False) == "INCONCLUSIVE"


def test_inference_audit_denies_reference_file_access(tmp_path, monkeypatch):
    path = tmp_path / "private-reference.json"
    path.write_text("not an inference input", encoding="utf-8")
    monkeypatch.setattr(tool.candidate, "infer", lambda data: path.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="Forbidden inference file access"):
        tool.guarded_infer(b"synthetic")
    assert path.read_text(encoding="utf-8") == "not an inference input"
