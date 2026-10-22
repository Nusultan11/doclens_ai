"""Public synthetic family reservations; no real data or reviewer claims."""

from __future__ import annotations

import pytest

from doclens_ai.eda import corpus_v2 as v2
from doclens_ai.evaluation.gold import load_gold_jsonl
from doclens_ai.evaluation.rag_gold import RagGoldExample, validate_rag_gold
from doclens_ai.extraction.fidelity_gold import fingerprint
from tools.extraction_quality import dataset_readiness as readiness


def sample(identity, digest, family, **changes):
    return v2.Sample(
        sample_id=identity,
        dataset="public-synthetic-fixture",
        release="fixture-1",
        revision="fixture-1",
        source_record_id=identity,
        cohort="synthetic",
        disposition="admitted",
        original=v2.Asset(path=identity + ".pdf", sha256=digest * 64, size_bytes=1, format="pdf"),
        rights=v2.Rights(
            dataset_license="fixture",
            original_license="fixture",
            local_evaluation=True,
            annotation_use=None,
            redistribution=None,
            references=("synthetic-fixture",),
            sensitivity="public",
        ),
        languages=("unknown",),
        document_type="synthetic",
        difficulty=("fixture",),
        family_id=family,
        family_review="unknown",
        split="dev",
        publicly_exposed=True,
        **changes,
    )


def corpus(*samples):
    return v2.Corpus(
        revision="fixture-1",
        selection_seed="fixture-1",
        split_revision="fixture-1",
        targets=(),
        samples=samples,
    )


def test_excludes_test_family_sibling_and_preserves_population():
    reference = corpus(sample("e2-ref", "1", "test-family"))
    candidates = corpus(
        sample("e2-overlap", "2", "test-family"), sample("e2-safe", "3", "other-family")
    )
    before = (reference.model_dump_json(), candidates.model_dump_json())
    report = readiness.isolation_report(reference, candidates, frozenset({"1" * 64}))
    assert report["population"] == 3
    assert report["eligible_ids"] == ["e2-safe"]
    assert report["excluded_ids"] == ["e2-overlap", "e2-ref"]
    assert report["candidate_population"] == 2
    assert report["candidate_eligible"] == 1
    assert report["independent_gold"] == "NOT_EVALUATED"
    assert before == (reference.model_dump_json(), candidates.model_dump_json())


@pytest.mark.parametrize("binding", ["related_family", "identical_source", "normalized_text"])
def test_propagates_test_reservations_through_existing_family_components(binding):
    reference = sample("e2-ref", "1", "test-family")
    candidate = sample("e2-candidate", "2", "other-family")
    if binding == "related_family":
        candidate = candidate.model_copy(update={"related_families": ("test-family",)})
    elif binding == "identical_source":
        candidate = candidate.model_copy(update={"original": reference.original})
    else:
        reference = reference.model_copy(update={"normalized_text_sha256": "a" * 64})
        candidate = candidate.model_copy(update={"normalized_text_sha256": "a" * 64})
    report = readiness.isolation_report(corpus(reference), corpus(candidate), frozenset({"1" * 64}))
    assert report["eligible_ids"] == []
    assert all("held_out_test_family" in row["exclusion_reasons"] for row in report["rows"])


@pytest.mark.parametrize("reserved", [frozenset(), frozenset({"f" * 64})])
def test_unbound_or_absent_test_sources_fail_closed(reserved):
    with pytest.raises(ValueError, match="Held-out source binding"):
        readiness.isolation_report(corpus(sample("e2-ref", "1", "family")), corpus(), reserved)


def test_selection_rejects_reserved_and_unknown_records():
    report = readiness.isolation_report(
        corpus(sample("e2-ref", "1", "family")),
        corpus(sample("e2-safe", "2", "other-family")),
        frozenset({"1" * 64}),
    )
    assert readiness.selection(report, {"e2-safe"})["status"] == "PASS"
    assert readiness.selection(report, {"e2-ref"})["status"] == "BLOCKED"
    assert readiness.selection(report, {"e2-absent"})["status"] == "BLOCKED"
    assert readiness.selection(report, {"e2-safe", "e2-ref"})["status"] == "BLOCKED"


def test_rights_and_disposition_do_not_become_eligible_through_isolation():
    safe = sample("e2-no-rights", "2", "other-family")
    safe = safe.model_copy(
        update={"rights": safe.rights.model_copy(update={"local_evaluation": None})}
    )
    absent = sample("e2-absent", "3", "third-family").model_copy(
        update={"disposition": "unavailable", "original": None, "reasons": ("missing",)}
    )
    report = readiness.isolation_report(
        corpus(sample("e2-ref", "1", "family")), corpus(safe, absent), frozenset({"1" * 64})
    )
    assert report["population"] == 3
    assert report["eligible_ids"] == []
    assert report["candidate_excluded"] == 2


def test_duplicate_cross_collection_identity_fails_closed():
    value = sample("e2-ref", "1", "family")
    with pytest.raises(ValueError, match="Duplicate sample identity"):
        readiness.isolation_report(corpus(value), corpus(value), frozenset({"1" * 64}))


def test_reserves_test_sources_from_both_gold_collections():
    retrieval = load_gold_jsonl("docs/evaluation/synthetic_retrieval_gold_fixture.jsonl")
    answers = validate_rag_gold(
        [
            RagGoldExample(
                dataset_revision="synthetic-rag-gold-v1",
                synthetic_fixture=True,
                question_id="fixture-question",
                document_family_id="fixture-family",
                split="test",
                language="en",
                category="unanswerable",
                question="Synthetic missing-evidence question?",
                answerable=False,
                source_document_sha256=["f" * 64],
                accepted_answers=[],
                reference_answer=None,
                evidence=[],
                required_citation_refs=[],
                reviewer_status="fixture",
                reviewer_count=0,
            )
        ]
    )
    expected = {"f" * 64}
    for example in retrieval.examples:
        if example.split == "test":
            expected.add(example.source_document_sha256)
            expected.update(a.document_sha256 for a in example.evidence)
    assert readiness.held_out_sources(retrieval, answers) == frozenset(expected)


@pytest.mark.parametrize("changed", ["none", "family", "identity", "population"])
def test_reference_binding_is_required(tmp_path, changed):
    path = tmp_path / "manifest.csv"
    source_page = "https://example.org/public-synthetic-fixture"
    path.write_text(
        "document_id,sha256,size_bytes,format,source_page_url\n"
        + "c1-0001,"
        + "1" * 64
        + ",1,pdf,"
        + source_page
        + "\n",
        encoding="utf-8",
    )
    value = sample("e2-ref", "1", "f-" + fingerprint(source_page)[:24]).model_copy(
        update={"source_record_id": "c1-0001"}
    )
    if changed == "family":
        value = value.model_copy(update={"family_id": "wrong-family"})
    elif changed == "identity":
        value = value.model_copy(update={"source_record_id": "c1-0002"})
    reference = corpus() if changed == "population" else corpus(value)
    if changed == "none":
        readiness.validate_reference(reference, path)
    else:
        with pytest.raises(ValueError, match="Reference"):
            readiness.validate_reference(reference, path)
