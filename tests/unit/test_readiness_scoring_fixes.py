"""Regression fixtures for the three acceptance-audit scoring defects."""

from __future__ import annotations

import hashlib
import json

import pytest
from pypdf import PdfWriter

from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import readiness_evaluator as ev
from tools.extraction_quality import readiness_pdf_metrics as pdf
from tools.extraction_quality import readiness_release as release


def source():
    return {
        "id": "office-a",
        "sha256": "a" * 64,
        "format": "xlsx",
        "split": "dev",
        "reserved_qa_family": False,
        "rights": {"local_evaluation": True, "new_annotation": True},
    }


def oracle():
    row = source()
    return {
        "version": "office-source-oracle-1.0",
        "tier": "SOURCE_NATIVE_ORACLE",
        "source_id": row["id"],
        "source_sha256": row["sha256"],
        "format": "xlsx",
        "human_reviewed": False,
        "independent_gold": False,
        "reviewer": None,
        "observations": {"sheets": []},
    }


def frozen(tmp_path, monkeypatch, oracle_files=None):
    monkeypatch.setattr(ev, "private_root", lambda path: None)
    monkeypatch.setattr(release, "private_root", lambda path: None)
    folder = tmp_path / "frozen"
    folder.mkdir()
    files = {"effective-matrix.json": {"population": [source()]}, **(oracle_files or {})}
    hashes = {}
    for relative, value in files.items():
        path = folder / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"artifact_sha256": hashes, "protected_sha256": {}, "gates": {}}
    manifest["fingerprint"] = fingerprint(manifest)
    (folder / "RELEASE.json").write_text(json.dumps(manifest), encoding="utf-8")
    prediction_path = tmp_path / "empty.json"
    prediction_path.write_text(
        json.dumps(
            {
                "version": "readiness-predictions-1.0",
                "model_identity": "synthetic",
                "predictions": [],
            }
        ),
        encoding="utf-8",
    )
    return folder, prediction_path


def test_valid_manifest_bound_oracle_scores(tmp_path, monkeypatch):
    folder, supplied = frozen(
        tmp_path,
        monkeypatch,
        {
            "office-oracles/office-a.json": oracle(),
            "office-oracles/office-a.checkpoint.json": {},
        },
    )
    assert ev.score(folder, supplied)["reference_documents"] == 1


def test_injection_rejected_even_when_surrounding_verification_passes(tmp_path, monkeypatch):
    folder, supplied = frozen(tmp_path, monkeypatch)
    assert ev.score(folder, supplied)["reference_documents"] == 0
    target = folder / "office-oracles/RELEASE.json"
    target.parent.mkdir()
    target.write_text(json.dumps(oracle()), encoding="utf-8")
    monkeypatch.setattr(release, "verify_runtime", lambda path: {"integrity": "PASS"})
    with pytest.raises(ValueError):
        ev.score(folder, supplied)


def test_unlisted_nested_manifest_rejected(tmp_path, monkeypatch):
    folder, _ = frozen(tmp_path, monkeypatch)
    assert release.verify(folder)["integrity"] == "PASS"
    (folder / "nested").mkdir()
    (folder / "nested/RELEASE.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        release.verify(folder)


@pytest.mark.parametrize(
    "case",
    [
        "misnamed",
        "duplicate",
        "orphan",
        "wrong_SHA",
        "reserved_name",
        "nested",
        "non_JSON",
        "orphan_checkpoint",
    ],
)
def test_invalid_manifest_listed_oracle_rejected(tmp_path, monkeypatch, case):
    files = {"office-oracles/office-a.json": oracle()}
    if case in {"misnamed", "duplicate"}:
        files["office-oracles/alias.json"] = oracle()
        if case == "misnamed":
            del files["office-oracles/office-a.json"]
    elif case == "orphan":
        files = {"office-oracles/missing.json": {**oracle(), "source_id": "missing"}}
    elif case == "wrong_SHA":
        files["office-oracles/office-a.json"]["source_sha256"] = "b" * 64
    elif case == "reserved_name":
        files["office-oracles/RELEASE.json"] = oracle()
    elif case == "nested":
        files["office-oracles/nested/office-a.json"] = oracle()
    elif case == "non_JSON":
        files["office-oracles/notes.txt"] = {}
    else:
        files["office-oracles/missing.checkpoint.json"] = {}
    folder, supplied = frozen(tmp_path, monkeypatch, files)
    with pytest.raises(ValueError):
        ev.score(folder, supplied)


@pytest.mark.parametrize("mode", ["changed", "missing", "unhashed"])
def test_oracle_bytes_and_inventory_checked_when_verifier_passes(tmp_path, monkeypatch, mode):
    folder, supplied = frozen(tmp_path, monkeypatch, {"office-oracles/office-a.json": oracle()})
    path = folder / "office-oracles/office-a.json"
    if mode == "changed":
        path.write_text(json.dumps({**oracle(), "observations": {"sheets": []}, "extra": 1}))
    elif mode == "missing":
        path.unlink()
    else:
        (folder / "office-oracles/extra.json").write_text(json.dumps(oracle()))
    monkeypatch.setattr(release, "verify_runtime", lambda path: {"integrity": "PASS"})
    with pytest.raises(ValueError):
        ev.score(folder, supplied)


def test_runtime_guard_is_not_bypassed(tmp_path, monkeypatch):
    folder, supplied = frozen(tmp_path, monkeypatch)

    def denied(path):
        raise ValueError("active scoring code differs from frozen release")

    monkeypatch.setattr(release, "verify_runtime", denied)
    with pytest.raises(ValueError, match="active scoring code"):
        ev.score(folder, supplied)


def pdf_source(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "ROOT", tmp_path)
    path = tmp_path / "original.pdf"
    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    writer.write(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "id": "c1-0031",
        "sha256": digest,
        "format": "pdf",
        "split": "dev",
        "rights": {"local_evaluation": True},
        "source_reference": {
            "path": "original.pdf",
            "sha256": digest,
            "size_bytes": path.stat().st_size,
            "format": "pdf",
        },
    }


def supplied(row, page=1, bbox=None):
    locator = {"page": page}
    if bbox is not None:
        locator["bbox"] = bbox
    return ev.Predictions.model_validate(
        {
            "version": "readiness-predictions-1.0",
            "model_identity": "synthetic",
            "predictions": [
                {
                    "source_id": row["id"],
                    "source_sha256": row["sha256"],
                    "status": "success",
                    "failure": None,
                    "observations": [
                        {"kind": "pdf_text", "locator": locator, "fields": {"text": "synthetic"}}
                    ],
                }
            ],
        }
    )


def test_missing_matrix_bounds_use_SHA_bound_original(tmp_path, monkeypatch):
    row = pdf_source(tmp_path, monkeypatch)
    assert ev.compare([row], supplied(row, bbox=[0, 0, 10, 10]), {})["prediction_documents"] == 1
    with pytest.raises(ValueError, match="outside original"):
        ev.compare([row], supplied(row, page=999999), {})


@pytest.mark.parametrize(
    "case",
    [
        "no_original",
        "missing_file",
        "changed_bytes",
        "wrong_SHA",
        "invented_count",
        "invented_geometry",
    ],
)
def test_unavailable_or_untrusted_PDF_bounds_fail_closed(tmp_path, monkeypatch, case):
    row = pdf_source(tmp_path, monkeypatch)
    page, box = 1, None
    if case == "no_original":
        del row["source_reference"]
    elif case == "missing_file":
        (tmp_path / "original.pdf").unlink()
    elif case == "changed_bytes":
        (tmp_path / "original.pdf").write_bytes(b"changed")
    elif case == "wrong_SHA":
        row["source_reference"]["sha256"] = "b" * 64
    elif case == "invented_count":
        row["pdf_page_count"] = 999999
        page = 999999
    else:
        row["pdf_page_count"] = 1
        row["pdf_page_geometry"] = {"1": {"width": 999999, "height": 999999, "rotation": 0}}
        box = [0, 0, 101, 10]
    with pytest.raises(ValueError):
        ev.compare([row], supplied(row, page, box), {})


def anchor_reference(boxes):
    return {
        "independent_gold": False,
        "human_reviewed": False,
        "anchors": [
            {
                "reference_id": f"a{i}",
                "page": 1,
                "literal": "£",
                "tier": "SOURCE",
                **({"bbox": box} if box is not None else {}),
            }
            for i, box in enumerate(boxes)
        ],
    }


def anchor_prediction(boxes, texts=None):
    return ev.Prediction.model_validate(
        {
            "source_id": "source",
            "source_sha256": "a" * 64,
            "status": "success",
            "failure": None,
            "observations": [
                {
                    "kind": "pdf_text",
                    "locator": {"page": 1, "bbox": box, "ordinal": i},
                    "fields": {"text": texts[i] if texts else "£"},
                }
                for i, box in enumerate(boxes)
            ],
        }
    )


def test_one_currency_occurrence_vs_115_unlocated_anchors():
    result = pdf.compare(anchor_prediction([[0, 0, 1, 1]]), anchor_reference([None] * 115))
    assert result["literal_anchor_presence"]["observed"] == 1
    assert result["literal_anchor_presence"]["unit"] == "unique_page_literal"
    recovery = result["literal_anchor_occurrences"]
    assert recovery["status"] == "NOT_EVALUATED"
    assert recovery["matched"] == 0 and recovery["not_evaluated"] == 115


def test_distinct_genuine_occurrences_match_one_to_one():
    boxes = [[0, 0, 10, 10], [20, 0, 30, 10]]
    ref = anchor_reference(boxes)
    one = pdf.compare(anchor_prediction(boxes[:1]), ref)["literal_anchor_occurrences"]
    both = pdf.compare(anchor_prediction(boxes), ref)["literal_anchor_occurrences"]
    assert (one["expected"], one["matched"], both["matched"]) == (2, 1, 2)


@pytest.mark.parametrize(
    "case",
    [
        "same_box_predictions",
        "broad_prediction",
        "wrong_region",
        "multi_literal_text",
        "no_prediction_bbox",
    ],
)
def test_one_physical_occurrence_never_reused(case):
    boxes = [[0, 0, 10, 10], [10, 0, 20, 10]]
    prediction = anchor_prediction(boxes[:1])
    if case == "same_box_predictions":
        prediction = anchor_prediction([boxes[0], boxes[0]])
    elif case == "broad_prediction":
        prediction = anchor_prediction([[0, 0, 20, 10]])
    elif case == "wrong_region":
        prediction = anchor_prediction([[80, 80, 90, 90]])
    elif case == "multi_literal_text":
        prediction = anchor_prediction([boxes[0]], ["£ £"])
    else:
        prediction.observations[0].locator.pop("bbox")
    result = pdf.compare(prediction, anchor_reference(boxes))["literal_anchor_occurrences"]
    assert result["matched"] <= (1 if case == "same_box_predictions" else 0)


def test_overlapping_variants_cannot_duplicate_one_physical_occurrence():
    prediction = anchor_prediction([[0, 0, 19, 10], [1, 0, 20, 10]])
    result = pdf.compare(prediction, anchor_reference([[0, 0, 10, 10], [10, 0, 20, 10]]))
    assert result["literal_anchor_occurrences"]["matched"] == 0


def test_identical_prediction_boxes_collapse_to_one_occurrence():
    result = pdf.compare(
        anchor_prediction([[0, 0, 10, 10]] * 2), anchor_reference([[0, 0, 10, 10], [20, 0, 30, 10]])
    )
    assert result["literal_anchor_occurrences"]["matched"] == 1


def test_conflicting_literals_cannot_reuse_one_physical_region():
    ref = anchor_reference([[0, 0, 10, 10], [10, 0, 20, 10]])
    ref["anchors"][1]["literal"] = "$"
    result = pdf.compare(anchor_prediction([[0, 0, 20, 10]] * 2, ["£", "$"]), ref)
    assert result["literal_anchor_occurrences"]["matched"] == 0


@pytest.mark.parametrize(
    "boxes",
    [
        [None, None],
        [[0, 0, 10, 10], [0, 0, 10, 10]],
        [[0, 0, 10, 10], [5, 0, 15, 10]],
    ],
)
def test_ambiguous_reference_locators_are_NOT_EVALUATED(boxes):
    result = pdf.compare(anchor_prediction([[0, 0, 10, 10]]), anchor_reference(boxes))
    assert result["literal_anchor_occurrences"]["status"] == "NOT_EVALUATED"
    assert result["literal_anchor_occurrences"]["not_evaluated"] == 2


def test_missing_prediction_and_partial_reference_locators():
    result = pdf.compare(None, anchor_reference([[0, 0, 10, 10], None]))
    recovery = result["literal_anchor_occurrences"]
    assert recovery["expected"] == 1 and recovery["matched"] == 0
    assert recovery["not_evaluated"] == 1 and recovery["status"] == "PARTIALLY_EVALUATED"
