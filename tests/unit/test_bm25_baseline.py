from __future__ import annotations

import math

import pytest

from doclens_ai.retrieval_baseline.bm25 import (
    BM25Config,
    BM25Document,
    BM25Index,
    tokenize,
)


def test_score_matches_okapi_formula_and_explicit_statistics() -> None:
    index = BM25Index(
        [
            BM25Document("chunk-a", "iris iris oak"),
            BM25Document("chunk-b", "iris oak pine"),
            BM25Document("chunk-c", "pine"),
        ]
    )
    assert index.document_count == 3
    assert dict(index.document_lengths) == {"chunk-a": 3, "chunk-b": 3, "chunk-c": 1}
    assert dict(index.document_frequency) == {"iris": 2, "oak": 2, "pine": 2}
    assert index.average_length == pytest.approx(7 / 3)
    hits = index.search("iris")
    idf = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))
    norm = 1 - 0.75 + 0.75 * 3 / (7 / 3)
    assert [hit.stable_id for hit in hits] == ["chunk-a", "chunk-b"]
    assert hits[0].score == pytest.approx(idf * 2 * 2.5 / (2 + 1.5 * norm))
    assert hits[1].score == pytest.approx(idf * 2.5 / (1 + 1.5 * norm))


def test_length_normalization_and_no_zero_score_filler() -> None:
    docs = [BM25Document("long", "iris " + "oak " * 20), BM25Document("short", "iris")]
    index = BM25Index(docs)
    assert index.search("iris")[0].stable_id == "short"
    without_norm = BM25Index(docs, config=BM25Config(b=0))
    assert without_norm.search("iris")[0].score == without_norm.search("iris")[1].score
    assert len(index.search("oak")) == 1


def test_common_terms_have_lower_idf_and_tf_saturates() -> None:
    index = BM25Index(
        [
            BM25Document("aaa", "common rare"),
            BM25Document("bbb", "common common"),
            BM25Document("ccc", "common common"),
        ],
        config=BM25Config(b=0),
    )
    assert index.search("rare")[0].score > index.search("common")[0].score
    common = {hit.stable_id: hit.score for hit in index.search("common")}
    assert common["aaa"] < common["bbb"] < common["aaa"] * 2


def test_casefold_unicode_repeated_terms_and_identifiers() -> None:
    assert tokenize("Straße СТАТЬЯ қАЗАҚ A12-007_x9 1.25") == (
        "strasse",
        "статья",
        "қазақ",
        "a12",
        "007",
        "x9",
        "1",
        "25",
    )
    index = BM25Index([BM25Document("aaa", "A12 007 Straße"), BM25Document("bbb", "A13 7")])
    assert index.search("A12 A12 a12") == index.search("a12")
    assert index.search("007")[0].stable_id == "aaa"
    assert index.search("7")[0].stable_id == "bbb"
    assert index.search("STRASSE") == index.search("Straße")
    assert index.search("007 a12") == index.search("a12 007")


@pytest.mark.parametrize("query", ["", "   ", "?!_", "absent"])
def test_empty_and_unknown_queries(query: str) -> None:
    assert BM25Index([BM25Document("aaa", "iris")]).search(query) == ()
    assert BM25Index([]).search(query) == ()
    assert BM25Index([BM25Document("aaa", "")]).search(query) == ()


def test_duplicate_identity_is_idempotent_but_conflicts_fail() -> None:
    doc = BM25Document("aaa", "iris")
    assert BM25Index([doc, doc]).fingerprint == BM25Index([doc]).fingerprint
    assert BM25Index([doc, doc]).document_count == 1
    with pytest.raises(ValueError, match="conflicting"):
        BM25Index([doc, BM25Document("aaa", "oak")])
    # Identical content at distinct source locations is not collapsed.
    assert len(BM25Index([doc, BM25Document("bbb", "iris")]).search("iris")) == 2


def test_stable_ties_top_k_fingerprints_and_input_order() -> None:
    docs = [BM25Document("bbb", "iris"), BM25Document("aaa", "iris")]
    first = BM25Index(docs, config=BM25Config(top_k=1))
    second = BM25Index(reversed(docs), config=BM25Config(top_k=1))
    assert first.search("iris") == second.search("iris")
    assert first.search("iris")[0].stable_id == "aaa"
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != BM25Index(docs).fingerprint
    with pytest.raises(TypeError):
        first.document_lengths["aaa"] = 99


@pytest.mark.parametrize(
    "kwargs",
    [
        {"k1": 0},
        {"k1": float("nan")},
        {"k1": True},
        {"b": -1},
        {"b": 1.01},
        {"top_k": 0},
        {"top_k": True},
        {"version": "2.0"},
    ],
)
def test_invalid_configuration_is_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        BM25Config(**kwargs)
