"""CLI for deterministic, metadata-only chunking evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from doclens_ai.chunking.core import EvaluationConfigurationError, evaluate_corpus


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare deterministic offline DocLens chunking baselines."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-characters", type=int, default=1_200)
    parser.add_argument("--overlap-characters", type=int, default=120)
    parser.add_argument(
        "--include-needs-review",
        action="store_true",
        help="chunk extraction results marked needs_review instead of skipping them",
    )
    parser.add_argument(
        "--omit-runtime-metrics",
        action="store_true",
        help="omit non-deterministic extraction and chunking latency values",
    )
    arguments = parser.parse_args()

    try:
        payload = evaluate_corpus(
            arguments.input_dir,
            arguments.output_dir,
            max_characters=arguments.max_characters,
            overlap_characters=arguments.overlap_characters,
            allow_needs_review=arguments.include_needs_review,
            measure_latency=not arguments.omit_runtime_metrics,
        )
    except (EvaluationConfigurationError, ValueError) as exc:
        parser.error(str(exc))

    print(f"documents={payload['document_count']}")
    for name, aggregate in payload["strategies"].items():
        print(
            f"{name}: chunks={aggregate['chunk_count']} "
            f"statuses={aggregate['document_status_counts']}"
        )
    print(f"output={arguments.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
