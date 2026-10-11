"""Command-line entry point for privacy-safe offline extraction runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from doclens_ai.extraction.parsers import ExtractionConfigurationError, extract_corpus


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the standalone DocLens structured extraction baseline."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--omit-runtime-metrics",
        action="store_true",
        help="omit non-deterministic per-file latency values",
    )
    arguments = parser.parse_args()

    try:
        payload = extract_corpus(
            arguments.input_dir,
            arguments.output_dir,
            measure_latency=not arguments.omit_runtime_metrics,
        )
    except ExtractionConfigurationError as exc:
        parser.error(str(exc))

    aggregate = payload["aggregate"]
    print(f"documents={aggregate['document_count']}")
    print(f"statuses={aggregate['status_counts']}")
    print(f"output={arguments.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
