"""Offline retrieval Gold validation and deterministic scoring."""

from doclens_ai.evaluation.gold import (
    CORPUS_V1_DATASET_REVISION,
    GOLD_SCHEMA_VERSION,
    SYNTHETIC_DATASET_REVISION,
    EvidenceAnchor,
    EvidenceLocator,
    GoldDataset,
    GoldExample,
    GoldValidationError,
    load_gold_jsonl,
)
from doclens_ai.evaluation.metrics import (
    EvaluationConfig,
    EvaluationError,
    EvaluationReport,
    evaluate_retrieval,
    load_ranked_results_jsonl,
)

__all__ = [
    "CORPUS_V1_DATASET_REVISION",
    "GOLD_SCHEMA_VERSION",
    "SYNTHETIC_DATASET_REVISION",
    "EvaluationConfig",
    "EvaluationError",
    "EvaluationReport",
    "EvidenceAnchor",
    "EvidenceLocator",
    "GoldDataset",
    "GoldExample",
    "GoldValidationError",
    "evaluate_retrieval",
    "load_gold_jsonl",
    "load_ranked_results_jsonl",
]
