"""Public synthetic assets exercise Corpus v2 integrity and leakage boundaries."""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError
from pypdf import PdfWriter

from doclens_ai.eda import corpus_v2 as v2


def sample(tmp_path, **changes):
    path = tmp_path / "source.pdf"
    if not path.exists():
        writer = PdfWriter()
        writer.add_blank_page(300, 200)
        writer.write(path)
    values = {
        "sample_id": "e2-public-1",
        "dataset": "public-fixture",
        "release": "fixture-1",
        "revision": "fixture-1",
        "source_record_id": "public-1",
        "cohort": "synthetic",
        "disposition": "admitted",
        "original": v2.Asset(
            path=path.name, sha256=v2.sha256(path), size_bytes=path.stat().st_size, format="pdf"
        ),
        "rights": v2.Rights(
            dataset_license="fixture",
            original_license="fixture",
            local_evaluation=True,
            annotation_use=True,
            redistribution=True,
            references=("synthetic-fixture",),
            sensitivity="public",
        ),
        "languages": ("en",),
        "document_type": "synthetic",
        "difficulty": ("blank",),
        "family_id": "public-family",
        "family_review": "unknown",
        "split": "dev",
        "publicly_exposed": False,
    }
    values.update(changes)
    if values["family_review"] == "human":
        values["family_review_reference"] = "synthetic-family-review-fixture"
    return v2.Sample(**values)


def manifest(*samples):
    return v2.Corpus(
        revision="public-1",
        selection_seed="extraction-v2-1",
        split_revision="family-1",
        targets=(),
        samples=samples,
    )


def test_roundtrip_schema_and_success(tmp_path):
    value = manifest(sample(tmp_path))
    path = tmp_path / "manifest.json"
    path.write_text(value.model_dump_json(), encoding="utf-8")
    assert v2.load(path) == value
    report = v2.audit(value, tmp_path)
    assert report["native_eligible"] == 1
    assert report["independent_gold"] == 0
    assert report["qg_00"] == "NOT_EVALUATED"
    assert report["family_completeness"] == "NOT_EVALUATED"
    assert v2.Corpus.model_json_schema()["additionalProperties"] is False


@pytest.mark.parametrize("change", ["missing", "hash", "size", "signature"])
def test_bad_assets_never_eligible(tmp_path, change):
    value = sample(tmp_path)
    path = tmp_path / "source.pdf"
    if change == "missing":
        path.unlink()
    elif change == "hash":
        raw = path.read_bytes().replace(b"PDF", b"BAD", 1)
        path.write_bytes(raw)
    elif change == "size":
        path.write_bytes(path.read_bytes() + b"x")
    else:
        path.write_bytes(b"not a PDF")
        value = sample(tmp_path)
    report = v2.audit(manifest(value), tmp_path)
    assert report["native_eligible"] == 0
    assert "asset_integrity_failed" in report["rows"][0]["issues"]


@pytest.mark.parametrize(
    "path",
    [
        "../x.pdf",
        "/x.pdf",
        "C:/x.pdf",
        "a\\x.pdf",
        "a/./x.pdf",
        "a//x.pdf",
        "x.pdf:stream",
        "file.json",
    ],
)
def test_asset_paths_fail_closed(path):
    with pytest.raises(ValidationError):
        v2.Asset(path=path, sha256="0" * 64, size_bytes=1, format="pdf")


def test_duplicate_json_keys_and_limit(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"nested":{"a":1,"a":2}}')
    with pytest.raises(ValueError, match="duplicate JSON"):
        v2.read_json(path)
    with pytest.raises(ValueError, match="limit"):
        v2.read_json(path, max_bytes=1)


@pytest.mark.parametrize(
    "field", ["local_evaluation", "original_license", "references", "sensitivity"]
)
def test_unknown_rights_or_sensitivity_not_admitted_for_execution(tmp_path, field):
    value = sample(tmp_path)
    rights = value.rights.model_dump()
    rights[field] = () if field == "references" else "unknown" if field == "sensitivity" else None
    value = value.model_copy(update={"rights": v2.Rights(**rights)})
    assert v2.audit(manifest(value), tmp_path)["native_eligible"] == 0


def test_review_and_pair_binding(tmp_path):
    with pytest.raises(ValidationError):
        v2.Review(status="independent_human", reviewer="Codex")
    with pytest.raises(ValidationError):
        v2.Review(status="automatic", independent=True)
    value = sample(tmp_path)
    annotation = v2.Annotation(
        asset=v2.Asset(path="a.json", sha256="0" * 64, size_bytes=1, format="json"),
        kind="pubtables_pdf",
        revision="1",
        provenance="automatic",
        coordinate_system="publisher_pymupdf_top_left",
        source_sha256="1" * 64,
        review=v2.Review(status="automatic"),
    )
    with pytest.raises(ValidationError, match="binding"):
        v2.Sample(**(value.model_dump() | {"annotation": annotation}))


@pytest.mark.parametrize("link", ["family", "related", "near", "normalized", "exact"])
def test_transitive_leakage_across_dataset_splits(tmp_path, link):
    a = sample(tmp_path, cohort="pilot", family_review="human", publicly_exposed=False)
    second = tmp_path / "second.pdf"
    second.write_bytes((tmp_path / "source.pdf").read_bytes() + b"\n")
    changes = {
        "sample_id": "e2-public-2",
        "dataset": "another-dataset",
        "split": "test",
        "family_id": "another-family",
        "cohort": "pilot",
        "family_review": "human",
        "original": v2.Asset(
            path="second.pdf",
            sha256=v2.sha256(second),
            size_bytes=second.stat().st_size,
            format="pdf",
        ),
    }
    if link == "family":
        changes["family_id"] = a.family_id
    elif link == "related":
        changes["related_families"] = (a.family_id,)
    elif link == "exact":
        changes["original"] = a.original
    elif link == "near":
        a = a.model_copy(update={"near_duplicate_group": "near-1"})
        changes["near_duplicate_group"] = "near-1"
    else:
        digest = hashlib.sha256(b"normalized text").hexdigest()
        a = a.model_copy(update={"normalized_text_sha256": digest})
        changes["normalized_text_sha256"] = digest
    b = sample(tmp_path, **changes)
    result = v2.audit(manifest(a, b), tmp_path)
    assert result["leaking_components"] == 1
    assert result["native_eligible"] == 0
    assert result["qg_00"] == "FAIL"
    assigned = v2.assign_splits((a, b), "1")
    assert assigned[a.sample_id] == assigned[b.sample_id]
    assert assigned == v2.assign_splits((b, a), "1")


def test_exposed_test_not_new_sealed_and_unreviewed_families_stay_dev(tmp_path):
    with pytest.raises(ValidationError):
        sample(tmp_path, split="test", publicly_exposed=True, cohort="pilot", family_review="human")
    a = sample(tmp_path, cohort="pilot", family_review="human", publicly_exposed=True)
    assert v2.assign_splits((a,), "1")[a.sample_id] == "exposed_test"
    b = sample(tmp_path, cohort="pilot", family_review="unknown", publicly_exposed=False)
    assert v2.assign_splits((b,), "1")[b.sample_id] == "dev"


def test_deterministic_selection_and_near_duplicate_diagnostics():
    ids = ["a", "b", "c"]
    assert v2.selected_ids(ids, "source", "seed", 2) == v2.selected_ids(
        ids[::-1], "source", "seed", 2
    )
    with pytest.raises(ValueError):
        v2.selected_ids(["a", "a"], "source", "seed", 1)
    assert v2.near_duplicate_pairs(
        {"a": "one two three four five six", "b": "ONE two three four five six", "c": "unrelated"}
    ) == [("a", "b")]
    assert v2.near_duplicate_pairs({"a": "", "b": ""}) == []
    assert v2.near_duplicate_pairs({"a": "Short", "b": "short"}) == [("a", "b")]
    ledger = v2.selection_ledger(ids, "source", "seed", 1)
    assert len(ledger) == 3
    assert sum(r["disposition"] == "attempted" for r in ledger) == 1
    assert sum(r["disposition"] == "excluded" for r in ledger) == 2


def test_actual_page_identity_is_checked(tmp_path):
    from doclens_ai.extraction.evidence_v2 import Page

    value = sample(
        tmp_path,
        page=Page(
            number=1,
            media_box=(0.0, 0.0, 301.0, 200.0),
            crop_box=(0.0, 0.0, 300.0, 200.0),
            rotation=0,
        ),
    )
    report = v2.audit(manifest(value), tmp_path)
    assert "page_identity_mismatch" in report["rows"][0]["issues"]
    assert report["native_eligible"] == 0
    assert report["qg_00"] == "FAIL"


def test_committed_template_and_schema_agree():
    from tools.extraction_quality.extraction_v2 import ROOT

    template = v2.load(ROOT / "docs/eda/extraction_corpus_v2_manifest.json")
    assert len(template.samples) == 60
    assert all(s.cohort == "pilot" and s.split == "dev" for s in template.samples)
    assert sum(s.original.format == "docx" for s in template.samples) == 30
    assert sum(s.original.format == "xlsx" for s in template.samples) == 30
    assert all(s.languages == ("unknown",) for s in template.samples)
    assert len(template.targets) == 7
    assert json.loads((ROOT / "docs/eda/extraction_corpus_v2_schema.json").read_text()) == (
        v2.Corpus.model_json_schema()
    )


def test_same_source_record_cannot_be_counted_twice(tmp_path):
    a = sample(tmp_path)
    b = a.model_copy(update={"sample_id": "e2-other-id"})
    with pytest.raises(ValidationError, match="duplicate source"):
        manifest(a, b)


def test_distinct_records_in_one_family_remain_valid(tmp_path):
    a = sample(tmp_path)
    b = a.model_copy(update={"sample_id": "e2-other-id", "source_record_id": "second-record"})
    assert v2.audit(manifest(a, b), tmp_path)["leaking_components"] == 0


def test_synthetic_human_review_cannot_count_as_real_independent_gold(tmp_path):
    from tests.unit.test_dataset_adapters_v2 import pair

    value = pair(tmp_path)
    reviewed = v2.Review(
        status="independent_human",
        reviewer="Fixture reviewer",
        reviewed_on="2026-01-01",
        original_inspected=True,
        independent=True,
        attestation="fixture-attestation",
    )
    value = value.model_copy(
        update={
            "annotation": value.annotation.model_copy(update={"review": reviewed}),
        }
    )
    assert v2.audit(manifest(value), tmp_path)["independent_gold"] == 0


@pytest.mark.parametrize(
    "kind,coordinates",
    [
        ("doclaynet_coco", "none"),
        ("pubtables_pdf", "pdf_unrotated"),
    ],
)
def test_annotation_kind_rejects_false_coordinate_basis(kind, coordinates):
    with pytest.raises(ValidationError):
        v2.Annotation(
            asset=v2.Asset(path="a.json", sha256="0" * 64, size_bytes=2, format="json"),
            kind=kind,
            revision="1",
            provenance="automatic",
            coordinate_system=coordinates,
            source_sha256="1" * 64,
            review=v2.Review(status="automatic"),
        )
