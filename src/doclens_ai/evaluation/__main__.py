from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from doclens_ai.evaluation.gold import GoldDataset, GoldValidationError, load_gold_jsonl
from doclens_ai.evaluation.metrics import (
    EvaluationConfig,
    EvaluationError,
    evaluate_retrieval,
    load_ranked_results_jsonl,
    render_summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and score offline retrieval Gold data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a Gold JSONL snapshot")
    _add_gold_arguments(validate)
    validate.add_argument("--json-output", type=Path)

    evaluate = subparsers.add_parser("evaluate", help="evaluate ranked retrieval JSONL")
    _add_gold_arguments(evaluate)
    evaluate.add_argument("--results", required=True, type=Path)
    evaluate.add_argument("--json-output", type=Path)
    evaluate.add_argument(
        "--require-workspace-scope",
        action="store_true",
        help="require trusted workspace metadata for every Gold query",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    exit_code = 0
    try:
        gold = load_gold_jsonl(
            arguments.gold,
            corpus_manifest_path=arguments.corpus_manifest,
        )
        if arguments.command == "validate":
            payload = _validation_payload(gold)
            summary = (
                f"Valid Gold snapshot: {payload['example_count']} examples\n"
                f"Dataset revision: {payload['dataset_revision']}\n"
                f"Gold fingerprint: {payload['gold_fingerprint']}\n"
            )
        else:
            config = EvaluationConfig(require_workspace_scope=arguments.require_workspace_scope)
            ranked = load_ranked_results_jsonl(arguments.results, config=config)
            report = evaluate_retrieval(gold, ranked, config=config)
            payload = report.to_dict()
            summary = render_summary(report)
            if payload["security"]["passed"] is False:
                exit_code = 1
        if arguments.json_output is not None:
            _write_json(arguments.json_output, payload)
    except (GoldValidationError, EvaluationError, ValueError) as exc:
        parser.error(str(exc))
    sys.stdout.write(summary)
    return exit_code


def _add_gold_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument(
        "--corpus-manifest",
        type=Path,
        help="required for the Corpus v1 Gold revision",
    )


def _validation_payload(gold: GoldDataset) -> dict[str, object]:
    examples = gold.examples
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "dataset_revision": gold.dataset_revision,
        "gold_fingerprint": gold.fingerprint,
        "example_count": len(examples),
        "answerable_count": sum(item.answerable for item in examples),
        "unanswerable_count": sum(not item.answerable for item in examples),
        "languages": sorted({item.language.value for item in examples}),
        "categories": sorted({item.category.value for item in examples}),
        "splits": sorted({item.split.value for item in examples}),
    }
    payload["validation_fingerprint"] = _fingerprint(payload)
    return payload


def _fingerprint(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, payload: dict[str, object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise EvaluationError("unable to write JSON report") from exc


if __name__ == "__main__":
    raise SystemExit(main())
