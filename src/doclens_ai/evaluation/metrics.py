from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from doclens_ai.evaluation.gold import (
    GOLD_SCHEMA_VERSION,
    DatasetSplit,
    EvidenceAnchor,
    EvidenceLocator,
    GoldDataset,
    GoldExample,
    Language,
    QuestionCategory,
    _enum,
    _int_at_least,
    _load_jsonl,
    _mapping,
    _parse_locator,
    _require_exact_keys,
    _sha256,
    _stable_id,
    _string,
)
from doclens_ai.extraction.models import DocumentFormat


class EvaluationError(ValueError):
    """Raised when ranked results or evaluation configuration are invalid."""


@dataclass(frozen=True, slots=True)
class EvaluationConfig:
    hit_recall_cutoffs: tuple[int, int] = (5, 10)
    ndcg_cutoff: int = 10
    max_rank: int = 1_000
    require_workspace_scope: bool = False

    def __post_init__(self) -> None:
        if self.hit_recall_cutoffs != (5, 10) or any(
            type(value) is not int for value in self.hit_recall_cutoffs
        ):
            raise ValueError("required retrieval cutoffs are exactly 5 and 10")
        if type(self.ndcg_cutoff) is not int or self.ndcg_cutoff != 10:
            raise ValueError("required nDCG cutoff is exactly 10")
        if type(self.max_rank) is not int or self.max_rank < 10:
            raise ValueError("max_rank must be at least 10")
        if type(self.require_workspace_scope) is not bool:
            raise ValueError("require_workspace_scope must be a boolean")

    def to_dict(self) -> dict[str, object]:
        return {
            "hit_recall_cutoffs": list(self.hit_recall_cutoffs),
            "ndcg_cutoff": self.ndcg_cutoff,
            "ndcg_gain": "binary_new_evidence",
            "ndcg_ideal": "one_result_per_gold_anchor",
            "max_rank": self.max_rank,
            "require_workspace_scope": self.require_workspace_scope,
        }


@dataclass(frozen=True, slots=True)
class RetrievedAnchor:
    document_sha256: str
    document_format: DocumentFormat
    locator: EvidenceLocator
    source_start: int | None = None
    source_end: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "document_sha256": self.document_sha256,
            "document_format": self.document_format.value,
            "locator": self.locator.to_dict(),
        }
        if self.source_start is not None:
            payload["source_start"] = self.source_start
            payload["source_end"] = self.source_end
        return payload


@dataclass(frozen=True, slots=True)
class RankedResult:
    rank: int
    evidence: tuple[RetrievedAnchor, ...]
    runtime_chunk_id: str | None = None
    workspace_id: str | None = None


@dataclass(frozen=True, slots=True)
class QueryResults:
    schema_version: str
    dataset_revision: str
    question_id: str
    results: tuple[RankedResult, ...]
    authorized_workspace_id: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return self.payload


def load_ranked_results_jsonl(
    path: str | Path,
    *,
    config: EvaluationConfig | None = None,
) -> tuple[QueryResults, ...]:
    active_config = config or EvaluationConfig()
    try:
        records = _load_jsonl(path, kind="ranked results")
        parsed = tuple(
            _parse_query_results(record, line_number=index, config=active_config)
            for index, record in enumerate(records, start=1)
        )
    except (ValueError, TypeError) as exc:
        if isinstance(exc, EvaluationError):
            raise
        raise EvaluationError(str(exc)) from exc
    question_ids = [item.question_id for item in parsed]
    if len(question_ids) != len(set(question_ids)):
        raise EvaluationError("ranked results contain duplicate question records")
    return tuple(sorted(parsed, key=lambda item: item.question_id))


def evaluate_retrieval(
    gold: GoldDataset,
    ranked_results: tuple[QueryResults, ...],
    *,
    config: EvaluationConfig | None = None,
) -> EvaluationReport:
    active_config = config or EvaluationConfig()
    gold_by_id = gold.by_question_id()
    result_by_id: dict[str, QueryResults] = {}
    for result in ranked_results:
        if result.question_id not in gold_by_id:
            raise EvaluationError(f"unknown query_id in ranked results: {result.question_id}")
        if result.question_id in result_by_id:
            raise EvaluationError(f"duplicate ranked results: {result.question_id}")
        if result.dataset_revision != gold.dataset_revision:
            raise EvaluationError("ranked results dataset revision is incompatible with Gold")
        result_by_id[result.question_id] = result
    if active_config.require_workspace_scope:
        missing_scope = sorted(
            question_id
            for question_id in gold_by_id
            if question_id not in result_by_id
            or result_by_id[question_id].authorized_workspace_id is None
        )
        if missing_scope:
            raise EvaluationError(
                "trusted workspace scope is missing for: " + ", ".join(missing_scope)
            )

    overall = _score_examples(gold.examples, result_by_id)
    by_language = {
        language.value: _score_examples(
            tuple(item for item in gold.examples if item.language is language),
            result_by_id,
        )
        for language in Language
        if any(item.language is language for item in gold.examples)
    }
    by_category = {
        category.value: _score_examples(
            tuple(item for item in gold.examples if item.category is category),
            result_by_id,
        )
        for category in QuestionCategory
        if any(item.category is category for item in gold.examples)
    }
    by_split = {
        split.value: _score_examples(
            tuple(item for item in gold.examples if item.split is split),
            result_by_id,
        )
        for split in DatasetSplit
        if any(item.split is split for item in gold.examples)
    }
    security = _security_report(gold.examples, result_by_id)
    normalized_results = _normalized_results(result_by_id)
    results_fingerprint = hashlib.sha256(
        json.dumps(normalized_results, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    payload_without_fingerprint: dict[str, object] = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "dataset_revision": gold.dataset_revision,
        "gold_fingerprint": gold.fingerprint,
        "results_fingerprint": results_fingerprint,
        "configuration": active_config.to_dict(),
        "overall": overall,
        "by_language": by_language,
        "by_category": by_category,
        "by_split": by_split,
        "security": security,
        "evaluation_basis": (
            "synthetic_fixture_only"
            if all(example.synthetic_fixture for example in gold.examples)
            else "reviewed_gold"
        ),
    }
    report_fingerprint = hashlib.sha256(
        json.dumps(
            payload_without_fingerprint,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return EvaluationReport(
        payload={**payload_without_fingerprint, "report_fingerprint": report_fingerprint}
    )


def render_summary(report: EvaluationReport) -> str:
    payload = report.to_dict()
    overall = payload["overall"]
    security = payload["security"]
    if not isinstance(overall, dict) or not isinstance(security, dict):
        raise EvaluationError("report payload is malformed")
    lines = [
        f"Dataset revision: {payload['dataset_revision']}",
        f"Gold fingerprint: {payload['gold_fingerprint']}",
        f"Results fingerprint: {payload['results_fingerprint']}",
        f"Queries: {overall['query_count']}",
        _summary_metric("Hit@5", overall["hit_at_5"]),
        _summary_metric("Hit@10", overall["hit_at_10"]),
        _summary_metric("Recall@5", overall["recall_at_5"]),
        _summary_metric("Recall@10", overall["recall_at_10"]),
        _summary_metric("MRR", overall["mrr"]),
        _summary_metric("nDCG@10", overall["ndcg_at_10"]),
        _summary_metric("Missing-result rate", overall["missing_result_rate"]),
        _summary_metric("Query coverage", overall["query_coverage"]),
        f"Security violations: {security['violation_count']}",
        f"Security status: {security['status']}",
        "Synthetic fixtures do not establish retrieval quality.",
    ]
    return "\n".join(lines) + "\n"


def _score_examples(
    examples: tuple[GoldExample, ...],
    result_by_id: dict[str, QueryResults],
) -> dict[str, object]:
    answerable = tuple(item for item in examples if item.answerable)
    unanswerable = tuple(item for item in examples if not item.answerable)
    total_queries = len(examples)
    covered_queries = sum(
        bool(result_by_id.get(item.question_id) and result_by_id[item.question_id].results)
        for item in examples
    )
    matched_at: dict[int, int] = {5: 0, 10: 0}
    hit_at: dict[int, int] = {5: 0, 10: 0}
    reciprocal_rank_sum = 0.0
    ndcg_sum = 0.0
    total_relevant = sum(len(item.evidence) for item in answerable)
    for example in answerable:
        query_results = result_by_id.get(example.question_id)
        ranked = query_results.results if query_results is not None else ()
        matched_by_rank = _matched_evidence_by_rank(example.evidence, ranked)
        for cutoff in (5, 10):
            matched_ids = {
                evidence_id
                for rank, ids in matched_by_rank.items()
                if rank <= cutoff
                for evidence_id in ids
            }
            matched_at[cutoff] += len(matched_ids)
            hit_at[cutoff] += bool(matched_ids)
        relevant_ranks = sorted(rank for rank, ids in matched_by_rank.items() if ids)
        if relevant_ranks:
            reciprocal_rank_sum += 1 / relevant_ranks[0]
        ndcg_sum += _ndcg(example.evidence, matched_by_rank, cutoff=10)

    unanswerable_with_results = sum(
        bool(result_by_id.get(item.question_id) and result_by_id[item.question_id].results)
        for item in unanswerable
    )
    return {
        "query_count": total_queries,
        "answerable_query_count": len(answerable),
        "unanswerable_query_count": len(unanswerable),
        "positive_evidence_count": total_relevant,
        "hit_at_5": _metric(hit_at[5], len(answerable)),
        "hit_at_10": _metric(hit_at[10], len(answerable)),
        "recall_at_5": _metric(matched_at[5], total_relevant),
        "recall_at_10": _metric(matched_at[10], total_relevant),
        "mrr": _metric(reciprocal_rank_sum, len(answerable)),
        "ndcg_at_10": _metric(ndcg_sum, len(answerable)),
        "missing_result_rate": _metric(total_queries - covered_queries, total_queries),
        "query_coverage": _metric(covered_queries, total_queries),
        "unanswerable": {
            "query_count": len(unanswerable),
            "queries_with_results": unanswerable_with_results,
            "result_presence_rate": _metric(
                unanswerable_with_results,
                len(unanswerable),
            ),
        },
    }


def _matched_evidence_by_rank(
    gold_evidence: tuple[EvidenceAnchor, ...],
    ranked: tuple[RankedResult, ...],
) -> dict[int, set[str]]:
    matches: dict[int, set[str]] = {}
    already_matched: set[str] = set()
    for result in ranked:
        result_matches = {
            gold_anchor.evidence_id
            for gold_anchor in gold_evidence
            if gold_anchor.evidence_id not in already_matched
            and any(
                _anchor_matches(gold_anchor, returned_anchor) for returned_anchor in result.evidence
            )
        }
        matches[result.rank] = result_matches
        already_matched.update(result_matches)
    return matches


def _anchor_matches(gold: EvidenceAnchor, returned: RetrievedAnchor) -> bool:
    if (
        gold.document_sha256 != returned.document_sha256
        or gold.document_format is not returned.document_format
    ):
        return False
    returned_locator = returned.locator.to_dict()
    if any(returned_locator.get(key) != value for key, value in gold.locator.to_dict().items()):
        return False
    if gold.source_start is None:
        return True
    return (
        returned.source_start is not None
        and returned.source_end is not None
        and returned.source_start <= gold.source_start
        and returned.source_end >= gold.source_end
    )


def _ndcg(
    evidence: tuple[EvidenceAnchor, ...],
    matched_by_rank: dict[int, set[str]],
    *,
    cutoff: int,
) -> float:
    gains = [float(bool(matched_by_rank.get(rank))) for rank in range(1, cutoff + 1)]
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(len(evidence), cutoff) + 1))
    return dcg / ideal if ideal else 0.0


def _security_report(
    examples: tuple[GoldExample, ...],
    result_by_id: dict[str, QueryResults],
) -> dict[str, object]:
    violations: list[dict[str, object]] = []
    evaluated_queries = 0
    for example in examples:
        query_results = result_by_id.get(example.question_id)
        if query_results is None or query_results.authorized_workspace_id is None:
            continue
        evaluated_queries += 1
        for result in query_results.results:
            if result.workspace_id is None:
                violations.append(
                    {
                        "question_id": example.question_id,
                        "rank": result.rank,
                        "reason": "missing_result_workspace",
                    }
                )
            elif result.workspace_id != query_results.authorized_workspace_id:
                violations.append(
                    {
                        "question_id": example.question_id,
                        "rank": result.rank,
                        "reason": "workspace_scope_violation",
                    }
                )
    return {
        "evaluated_query_count": evaluated_queries,
        "unchecked_query_count": len(examples) - evaluated_queries,
        "violation_count": len(violations),
        "passed": not violations if evaluated_queries else None,
        "status": ("failed" if violations else "passed" if evaluated_queries else "not_evaluated"),
        "violations": violations,
        "aggregation_policy": "security violations are never averaged into quality metrics",
    }


def _normalized_results(result_by_id: dict[str, QueryResults]) -> list[dict[str, object]]:
    return [
        {
            "question_id": query.question_id,
            "dataset_revision": query.dataset_revision,
            "authorized_workspace_id": query.authorized_workspace_id,
            "results": [
                {
                    "rank": result.rank,
                    "workspace_id": result.workspace_id,
                    "evidence": [anchor.to_dict() for anchor in result.evidence],
                }
                for result in query.results
            ],
        }
        for query in sorted(result_by_id.values(), key=lambda item: item.question_id)
    ]


def _parse_query_results(
    value: object,
    *,
    line_number: int,
    config: EvaluationConfig,
) -> QueryResults:
    try:
        record = _mapping(value, context=f"ranked results line {line_number}")
        _require_exact_keys(
            record,
            required={"schema_version", "dataset_revision", "question_id", "results"},
            optional={"authorized_workspace_id"},
            context=f"ranked results line {line_number}",
        )
        schema_version = _string(record["schema_version"], "schema_version")
        if schema_version != GOLD_SCHEMA_VERSION:
            raise EvaluationError(f"unsupported results schema_version: {schema_version}")
        dataset_revision = _string(record["dataset_revision"], "dataset_revision")
        question_id = _stable_id(record["question_id"], "question_id")
        authorized_workspace_id = (
            _string(record["authorized_workspace_id"], "authorized_workspace_id")
            if "authorized_workspace_id" in record
            else None
        )
        values = record["results"]
        if not isinstance(values, list):
            raise EvaluationError("results must be a list")
        results = tuple(_parse_ranked_result(item, config=config) for item in values)
        ranks = [item.rank for item in results]
        if len(ranks) != len(set(ranks)):
            raise EvaluationError(f"duplicate rankings for query: {question_id}")
        runtime_ids = [item.runtime_chunk_id for item in results if item.runtime_chunk_id]
        if len(runtime_ids) != len(set(runtime_ids)):
            raise EvaluationError(f"duplicate runtime chunk IDs for query: {question_id}")
        return QueryResults(
            schema_version=schema_version,
            dataset_revision=dataset_revision,
            question_id=question_id,
            results=tuple(sorted(results, key=lambda item: item.rank)),
            authorized_workspace_id=authorized_workspace_id,
        )
    except EvaluationError:
        raise
    except (ValueError, TypeError) as exc:
        raise EvaluationError(str(exc)) from exc


def _parse_ranked_result(value: object, *, config: EvaluationConfig) -> RankedResult:
    record = _mapping(value, context="ranked result")
    _require_exact_keys(
        record,
        required={"rank", "evidence"},
        optional={"runtime_chunk_id", "workspace_id"},
        context="ranked result",
    )
    rank = _int_at_least(record["rank"], "rank", 1)
    if rank > config.max_rank:
        raise EvaluationError("rank exceeds configured max_rank")
    evidence_values = record["evidence"]
    if not isinstance(evidence_values, list) or not evidence_values:
        raise EvaluationError("ranked result evidence must be a non-empty list")
    evidence = tuple(_parse_retrieved_anchor(item) for item in evidence_values)
    normalized = [json.dumps(item.to_dict(), sort_keys=True) for item in evidence]
    if len(normalized) != len(set(normalized)):
        raise EvaluationError("ranked result contains duplicate evidence anchors")
    runtime_chunk_id = (
        _string(record["runtime_chunk_id"], "runtime_chunk_id")
        if "runtime_chunk_id" in record
        else None
    )
    workspace_id = (
        _string(record["workspace_id"], "workspace_id") if "workspace_id" in record else None
    )
    return RankedResult(
        rank=rank,
        evidence=evidence,
        runtime_chunk_id=runtime_chunk_id,
        workspace_id=workspace_id,
    )


def _parse_retrieved_anchor(value: object) -> RetrievedAnchor:
    record = _mapping(value, context="retrieved evidence")
    _require_exact_keys(
        record,
        required={"document_sha256", "document_format", "locator"},
        optional={"source_start", "source_end"},
        context="retrieved evidence",
    )
    document_sha256 = _sha256(record["document_sha256"], "document_sha256")
    document_format = _enum(DocumentFormat, record["document_format"], "document_format")
    locator = _parse_locator(record["locator"], document_format=document_format)
    source_start = record.get("source_start")
    source_end = record.get("source_end")
    if (source_start is None) is not (source_end is None):
        raise EvaluationError("retrieved source_start/source_end must be paired")
    if source_start is not None:
        source_start = _int_at_least(source_start, "source_start", 0)
        source_end = _int_at_least(source_end, "source_end", 0)
        if source_end <= source_start:
            raise EvaluationError("retrieved source_end must be greater than source_start")
    return RetrievedAnchor(
        document_sha256=document_sha256,
        document_format=document_format,
        locator=locator,
        source_start=source_start,
        source_end=source_end,
    )


def _metric(numerator: int | float, denominator: int) -> dict[str, int | float | None]:
    value = numerator / denominator if denominator else None
    return {
        "value": round(value, 12) if value is not None else None,
        "numerator": round(numerator, 12) if isinstance(numerator, float) else numerator,
        "denominator": denominator,
    }


def _summary_metric(label: str, metric: object) -> str:
    if not isinstance(metric, dict):
        raise EvaluationError("report metric is malformed")
    value = metric.get("value")
    rendered = "n/a" if value is None else f"{float(value):.6f}"
    return f"{label}: {rendered} ({metric.get('numerator')}/{metric.get('denominator')})"
