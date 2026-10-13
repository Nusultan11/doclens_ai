from __future__ import annotations

import json
import math
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from doclens_ai.evaluation.__main__ import main
from doclens_ai.evaluation.gold import (
    GoldValidationError,
    load_gold_jsonl,
    validate_corpus_manifest_references,
)
from doclens_ai.evaluation.metrics import (
    EvaluationConfig,
    EvaluationError,
    evaluate_retrieval,
    load_ranked_results_jsonl,
    render_summary,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPOSITORY_ROOT / "docs/evaluation/synthetic_retrieval_gold_fixture.jsonl"
MANIFEST_PATH = REPOSITORY_ROOT / "docs/eda/corpus_v1_manifest.csv"


def _gold_records() -> list[dict[str, object]]:
    return [json.loads(line) for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()]


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> Path:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def _retrieved_anchor(
    document_sha256: str,
    document_format: str,
    locator: dict[str, object],
    *,
    source_start: int | None = None,
    source_end: int | None = None,
) -> dict[str, object]:
    anchor: dict[str, object] = {
        "document_sha256": document_sha256,
        "document_format": document_format,
        "locator": locator,
    }
    if source_start is not None:
        anchor["source_start"] = source_start
        anchor["source_end"] = source_end
    return anchor


def _ranked_records(*, runtime_suffix: str = "a") -> list[dict[str, object]]:
    return [
        {
            "schema_version": "1.0",
            "dataset_revision": "synthetic-retrieval-gold-v1",
            "question_id": "synthetic-q-001",
            "authorized_workspace_id": "workspace-alpha",
            "results": [
                {
                    "rank": 1,
                    "runtime_chunk_id": f"runtime-wrong-{runtime_suffix}",
                    "workspace_id": "workspace-alpha",
                    "evidence": [_retrieved_anchor("9" * 64, "pdf", {"page_number": 9})],
                },
                {
                    "rank": 2,
                    "runtime_chunk_id": f"runtime-first-{runtime_suffix}",
                    "workspace_id": "workspace-alpha",
                    "evidence": [
                        _retrieved_anchor(
                            "1" * 64,
                            "pdf",
                            {"page_number": 1, "block_index": 0},
                            source_start=0,
                            source_end=25,
                        )
                    ],
                },
                {
                    "rank": 6,
                    "runtime_chunk_id": f"runtime-second-{runtime_suffix}",
                    "workspace_id": "workspace-alpha",
                    "evidence": [
                        _retrieved_anchor(
                            "1" * 64,
                            "pdf",
                            {"page_number": 2, "block_index": 1},
                        )
                    ],
                },
            ],
        },
        {
            "schema_version": "1.0",
            "dataset_revision": "synthetic-retrieval-gold-v1",
            "question_id": "synthetic-q-002",
            "authorized_workspace_id": "workspace-beta",
            "results": [
                {
                    "rank": 1,
                    "runtime_chunk_id": f"runtime-table-{runtime_suffix}",
                    "workspace_id": "workspace-outside-scope",
                    "evidence": [
                        _retrieved_anchor(
                            "2" * 64,
                            "docx",
                            {
                                "block_index": 2,
                                "table_index": 0,
                                "row_index": 1,
                                "column_index": 1,
                            },
                        )
                    ],
                }
            ],
        },
        {
            "schema_version": "1.0",
            "dataset_revision": "synthetic-retrieval-gold-v1",
            "question_id": "synthetic-q-004",
            "results": [
                {
                    "rank": 1,
                    "runtime_chunk_id": f"runtime-unanswerable-{runtime_suffix}",
                    "evidence": [_retrieved_anchor("4" * 64, "pdf", {"page_number": 1})],
                }
            ],
        },
    ]


def test_valid_reviewed_gold_and_multiple_evidence_locations() -> None:
    gold = load_gold_jsonl(FIXTURE_PATH)

    assert len(gold.examples) == 4
    assert gold.dataset_revision == "synthetic-retrieval-gold-v1"
    assert len(gold.fingerprint) == 64
    first = gold.by_question_id()["synthetic-q-001"]
    assert first.answerable is True
    assert len(first.evidence) == 2
    assert first.evidence[0].locator.page_number == 1
    assert gold.by_question_id()["synthetic-q-004"].answerable is False


@pytest.mark.parametrize(
    "mutation",
    [
        "invalid_sha",
        "unsupported_language",
        "unsupported_category",
        "answerability_conflict",
        "draft_as_gold",
        "review_state_conflict",
        "malformed_locator",
        "unknown_revision",
    ],
)
def test_invalid_and_conflicting_gold_labels_are_rejected(
    tmp_path: Path,
    mutation: str,
) -> None:
    records = _gold_records()
    first = records[0]
    if mutation == "invalid_sha":
        first["source_document_sha256"] = "not-a-sha"
    elif mutation == "unsupported_language":
        first["language"] = "de"
    elif mutation == "unsupported_category":
        first["category"] = "opinion"
    elif mutation == "answerability_conflict":
        first["answerable"] = False
    elif mutation == "draft_as_gold":
        first["review_status"] = "draft"
        first["reviewer_count"] = 0
        first["adjudication_state"] = "pending"
    elif mutation == "review_state_conflict":
        first["review_status"] = "adjudicated"
        first["reviewer_count"] = 1
        first["adjudication_state"] = "resolved"
    elif mutation == "malformed_locator":
        first["evidence"][0]["locator"] = {"block_index": 0}  # type: ignore[index]
    else:
        first["dataset_revision"] = "unknown-revision"

    with pytest.raises(GoldValidationError):
        load_gold_jsonl(_write_jsonl(tmp_path / "invalid.jsonl", records))


def test_duplicate_ids_and_document_family_split_leakage_are_rejected(
    tmp_path: Path,
) -> None:
    duplicate = _gold_records()
    duplicate[1]["question_id"] = duplicate[0]["question_id"]
    with pytest.raises(GoldValidationError, match="duplicate question_id"):
        load_gold_jsonl(_write_jsonl(tmp_path / "duplicate.jsonl", duplicate))

    leakage = _gold_records()
    leakage[2]["document_family_id"] = leakage[0]["document_family_id"]
    with pytest.raises(GoldValidationError, match="crosses dev/test"):
        load_gold_jsonl(_write_jsonl(tmp_path / "leakage.jsonl", leakage))


def test_exact_metrics_answerable_unanswerable_and_breakdowns(tmp_path: Path) -> None:
    gold = load_gold_jsonl(FIXTURE_PATH)
    results = load_ranked_results_jsonl(_write_jsonl(tmp_path / "results.jsonl", _ranked_records()))
    report = evaluate_retrieval(gold, results).to_dict()
    overall = report["overall"]

    assert overall["query_count"] == 4  # type: ignore[index]
    assert overall["answerable_query_count"] == 3  # type: ignore[index]
    assert overall["unanswerable_query_count"] == 1  # type: ignore[index]
    assert overall["hit_at_5"] == {  # type: ignore[index]
        "value": pytest.approx(2 / 3),
        "numerator": 2,
        "denominator": 3,
    }
    assert overall["hit_at_10"]["value"] == pytest.approx(2 / 3)  # type: ignore[index]
    assert overall["recall_at_5"]["value"] == pytest.approx(0.5)  # type: ignore[index]
    assert overall["recall_at_10"]["value"] == pytest.approx(0.75)  # type: ignore[index]
    assert overall["mrr"]["value"] == pytest.approx(0.5)  # type: ignore[index]
    q1_ndcg = (1 / math.log2(3) + 1 / math.log2(7)) / (1 + 1 / math.log2(3))
    assert overall["ndcg_at_10"]["value"] == pytest.approx((q1_ndcg + 1) / 3)  # type: ignore[index]
    assert overall["missing_result_rate"]["value"] == pytest.approx(0.25)  # type: ignore[index]
    assert overall["query_coverage"]["value"] == pytest.approx(0.75)  # type: ignore[index]
    assert overall["unanswerable"]["queries_with_results"] == 1  # type: ignore[index]
    assert set(report["by_language"]) == {"en", "ru", "kk"}  # type: ignore[arg-type]
    assert set(report["by_category"]) == {  # type: ignore[arg-type]
        "fact",
        "table",
        "number",
        "unanswerable",
    }
    assert "Synthetic fixtures do not establish retrieval quality." in render_summary(
        evaluate_retrieval(gold, results)
    )


def test_runtime_uuid_changes_do_not_change_evidence_matching_or_fingerprints(
    tmp_path: Path,
) -> None:
    gold = load_gold_jsonl(FIXTURE_PATH)
    first = load_ranked_results_jsonl(
        _write_jsonl(tmp_path / "first.jsonl", _ranked_records(runtime_suffix="first"))
    )
    second = load_ranked_results_jsonl(
        _write_jsonl(tmp_path / "second.jsonl", _ranked_records(runtime_suffix="second"))
    )

    first_report = evaluate_retrieval(gold, first).to_dict()
    second_report = evaluate_retrieval(gold, second).to_dict()

    assert first_report == second_report
    assert first_report["results_fingerprint"] == second_report["results_fingerprint"]
    assert first_report["report_fingerprint"] == second_report["report_fingerprint"]


def test_workspace_scope_violations_are_separate_hard_failures(tmp_path: Path) -> None:
    gold = load_gold_jsonl(FIXTURE_PATH)
    results = load_ranked_results_jsonl(_write_jsonl(tmp_path / "results.jsonl", _ranked_records()))
    report = evaluate_retrieval(gold, results).to_dict()
    security = report["security"]

    assert security["passed"] is False  # type: ignore[index]
    assert security["evaluated_query_count"] == 2  # type: ignore[index]
    assert security["violation_count"] == 1  # type: ignore[index]
    assert security["violations"] == [  # type: ignore[index]
        {
            "question_id": "synthetic-q-002",
            "rank": 1,
            "reason": "workspace_scope_violation",
        }
    ]
    with pytest.raises(EvaluationError, match="trusted workspace scope is missing"):
        evaluate_retrieval(
            gold,
            results,
            config=EvaluationConfig(require_workspace_scope=True),
        )


def test_empty_malformed_duplicate_and_unknown_results_are_rejected(
    tmp_path: Path,
) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(EvaluationError, match="empty"):
        load_ranked_results_jsonl(empty)

    malformed = tmp_path / "malformed.jsonl"
    malformed.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(EvaluationError, match="malformed"):
        load_ranked_results_jsonl(malformed)

    duplicate_rank = _ranked_records()
    duplicate_rank[0]["results"][1]["rank"] = 1  # type: ignore[index]
    with pytest.raises(EvaluationError, match="duplicate rankings"):
        load_ranked_results_jsonl(_write_jsonl(tmp_path / "duplicate-rank.jsonl", duplicate_rank))

    gold = load_gold_jsonl(FIXTURE_PATH)
    unknown = _ranked_records()
    unknown[0]["question_id"] = "synthetic-q-unknown"
    parsed = load_ranked_results_jsonl(_write_jsonl(tmp_path / "unknown.jsonl", unknown))
    with pytest.raises(EvaluationError, match="unknown query_id"):
        evaluate_retrieval(gold, parsed)


def test_invalid_evaluation_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="cutoffs"):
        EvaluationConfig(hit_recall_cutoffs=(1, 5))
    with pytest.raises(ValueError, match="nDCG"):
        EvaluationConfig(ndcg_cutoff=5)
    with pytest.raises(ValueError, match="max_rank"):
        EvaluationConfig(max_rank=9)


def test_corpus_manifest_reference_validation() -> None:
    known_hash = "d3c67356804b2c0b29bf5456fe0e1bdf3810b20824ecf1a7616ee73e7ca84855"
    validate_corpus_manifest_references({known_hash}, MANIFEST_PATH)

    with pytest.raises(GoldValidationError, match="absent"):
        validate_corpus_manifest_references({"f" * 64}, MANIFEST_PATH)


def test_gold_and_report_generation_are_deterministic(tmp_path: Path) -> None:
    first_gold = load_gold_jsonl(FIXTURE_PATH)
    second_gold = load_gold_jsonl(FIXTURE_PATH)
    records = _ranked_records()
    first_results = load_ranked_results_jsonl(_write_jsonl(tmp_path / "repeat-a.jsonl", records))
    second_results = load_ranked_results_jsonl(
        _write_jsonl(tmp_path / "repeat-b.jsonl", deepcopy(records))
    )

    assert first_gold.fingerprint == second_gold.fingerprint
    assert (
        evaluate_retrieval(first_gold, first_results).to_dict()
        == evaluate_retrieval(
            second_gold,
            second_results,
        ).to_dict()
    )


def test_unchecked_security_is_not_reported_as_passed() -> None:
    gold = load_gold_jsonl(FIXTURE_PATH)
    report = evaluate_retrieval(gold, ()).to_dict()
    assert report["security"]["passed"] is None
    assert report["security"]["status"] == "not_evaluated"


def test_cli_reports_security_failure_and_writes_private_deterministic_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = _write_jsonl(tmp_path / "results.jsonl", _ranked_records())
    output = tmp_path / "report.json"
    arguments = [
        "evaluate",
        "--gold",
        str(FIXTURE_PATH),
        "--results",
        str(results),
        "--json-output",
        str(output),
    ]
    assert main(arguments) == 1
    first = output.read_bytes()
    assert main(arguments) == 1
    assert output.read_bytes() == first
    payload = json.loads(first)
    assert payload["security"]["violation_count"] == 1
    for example in _gold_records():
        assert example["question"] not in first.decode()
    for private_value in ("Synthetic", "workspace-alpha", "runtime-first-a", str(tmp_path)):
        assert private_value not in first.decode()
    assert "Security status: failed" in capsys.readouterr().out


def test_duplicate_json_fields_and_source_family_aliases_are_rejected(tmp_path: Path) -> None:
    duplicate_fields = tmp_path / "duplicate-fields.jsonl"
    duplicate_fields.write_text('{"schema_version":"1.0","schema_version":"2.0"}\n')
    with pytest.raises(GoldValidationError, match="duplicate JSON field"):
        load_gold_jsonl(duplicate_fields)

    aliases = _gold_records()
    aliases[3]["source_document_sha256"] = aliases[0]["source_document_sha256"]
    with pytest.raises(GoldValidationError, match="multiple document families"):
        load_gold_jsonl(_write_jsonl(tmp_path / "aliases.jsonl", aliases))


@pytest.mark.parametrize("max_rank", [True, 10.5, "10"])
def test_config_requires_integer_max_rank(max_rank: object) -> None:
    with pytest.raises(ValueError, match="max_rank"):
        EvaluationConfig(max_rank=max_rank)


@pytest.mark.parametrize("mutation", ["missing_span", "partial_span", "wrong_page"])
def test_unresolved_source_evidence_is_never_counted(tmp_path: Path, mutation: str) -> None:
    records = _ranked_records()[:1]
    records[0]["results"] = [records[0]["results"][1]]
    anchor = records[0]["results"][0]["evidence"][0]
    if mutation == "missing_span":
        del anchor["source_start"]
        del anchor["source_end"]
    elif mutation == "partial_span":
        anchor["source_end"] = 19
    else:
        anchor["locator"]["page_number"] = 3
    ranked = load_ranked_results_jsonl(_write_jsonl(tmp_path / "unresolved.jsonl", records))
    report = evaluate_retrieval(load_gold_jsonl(FIXTURE_PATH), ranked).to_dict()
    assert report["overall"]["hit_at_10"]["numerator"] == 0
    assert report["overall"]["recall_at_10"]["numerator"] == 0


def test_standard_discount_and_duplicate_evidence_credit(tmp_path: Path) -> None:
    gold = load_gold_jsonl(_write_jsonl(tmp_path / "gold.jsonl", _gold_records()[:1]))
    records = _ranked_records()[:1]
    relevant = records[0]["results"][1:]
    relevant[0]["rank"] = 1
    relevant[1]["rank"] = 2
    duplicate = deepcopy(relevant[0])
    duplicate["rank"] = 3
    duplicate["runtime_chunk_id"] = "new-runtime-same-source"
    records[0]["results"] = relevant + [duplicate]
    ranked = load_ranked_results_jsonl(_write_jsonl(tmp_path / "perfect.jsonl", records))
    overall = evaluate_retrieval(gold, ranked).to_dict()["overall"]
    assert overall["ndcg_at_10"]["value"] == 1
    assert overall["recall_at_10"]["numerator"] == 2

    combined = deepcopy(relevant[0])
    combined["evidence"] += relevant[1]["evidence"]
    records[0]["results"] = [combined]
    ranked = load_ranked_results_jsonl(_write_jsonl(tmp_path / "combined.jsonl", records))
    overall = evaluate_retrieval(gold, ranked).to_dict()["overall"]
    assert overall["recall_at_10"]["value"] == 1
    assert overall["ndcg_at_10"]["value"] == pytest.approx(1 / (1 + 1 / math.log2(3)))


def test_missing_workspace_and_incompatible_revision(tmp_path: Path) -> None:
    records = _ranked_records()
    del records[0]["results"][0]["workspace_id"]
    ranked = load_ranked_results_jsonl(_write_jsonl(tmp_path / "scope.jsonl", records))
    gold = load_gold_jsonl(FIXTURE_PATH)
    report = evaluate_retrieval(gold, ranked).to_dict()
    assert report["security"]["violation_count"] == 2
    assert report["security"]["violations"][0]["reason"] == "missing_result_workspace"
    records[0]["dataset_revision"] = "unknown-revision"
    ranked = load_ranked_results_jsonl(_write_jsonl(tmp_path / "revision.jsonl", records))
    with pytest.raises(EvaluationError, match="incompatible"):
        evaluate_retrieval(gold, ranked)


def test_real_revision_requires_manifest_and_known_references(tmp_path: Path) -> None:
    records = _gold_records()[:1]
    records[0]["dataset_revision"] = "corpus-v1-retrieval-gold-v1"
    records[0]["synthetic_fixture"] = False
    path = _write_jsonl(tmp_path / "manifest-contract-test.jsonl", records)
    with pytest.raises(GoldValidationError, match="requires its committed manifest"):
        load_gold_jsonl(path)
    with pytest.raises(GoldValidationError, match="absent"):
        load_gold_jsonl(path, corpus_manifest_path=MANIFEST_PATH)
    known_hash = "d3c67356804b2c0b29bf5456fe0e1bdf3810b20824ecf1a7616ee73e7ca84855"
    records[0]["source_document_sha256"] = known_hash
    for anchor in records[0]["evidence"]:
        anchor["document_sha256"] = known_hash
    path = _write_jsonl(tmp_path / "manifest-contract-test.jsonl", records)
    assert len(load_gold_jsonl(path, corpus_manifest_path=MANIFEST_PATH).examples) == 1


def test_empty_gold_and_duplicate_evidence_are_rejected(tmp_path: Path) -> None:
    empty = tmp_path / "empty-gold.jsonl"
    empty.write_text("\n", encoding="utf-8")
    with pytest.raises(GoldValidationError, match="empty"):
        load_gold_jsonl(empty)
    records = _gold_records()
    repeated = deepcopy(records[0]["evidence"][0])
    repeated["evidence_id"] = "synthetic-evidence-other-id"
    records[0]["evidence"].append(repeated)
    with pytest.raises(GoldValidationError, match="duplicate Gold evidence"):
        load_gold_jsonl(_write_jsonl(tmp_path / "repeated.jsonl", records))


def test_cli_subprocess_validation_and_repeatable_evaluation(tmp_path: Path) -> None:
    results = _write_jsonl(tmp_path / "results.jsonl", _ranked_records())
    output = tmp_path / "report.json"
    command = [sys.executable, "-m", "doclens_ai.evaluation"]
    validated = subprocess.run(
        command + ["validate", "--gold", str(FIXTURE_PATH)],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert "Valid Gold snapshot: 4 examples" in validated.stdout
    arguments = command + [
        "evaluate",
        "--gold",
        str(FIXTURE_PATH),
        "--results",
        str(results),
        "--json-output",
        str(output),
    ]
    first = subprocess.run(arguments, capture_output=True, text=True, timeout=15)
    first_report = output.read_bytes()
    second = subprocess.run(arguments, capture_output=True, text=True, timeout=15)
    assert first.returncode == second.returncode == 1
    assert first.stdout == second.stdout
    assert output.read_bytes() == first_report
    assert "Hit@5: 0.666667 (2/3)" in first.stdout
