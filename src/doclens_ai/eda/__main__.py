"""Command-line entry point for the offline EDA profiler."""

from __future__ import annotations

import argparse
from pathlib import Path

from doclens_ai.eda.profiling import ProfilingError, profile_corpus


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile a local PDF, DOCX, and XLSX corpus without retaining content."
    )
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--omit-runtime-metrics",
        action="store_true",
        help="omit latency so repeated reports are byte-for-byte reproducible",
    )
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        result = profile_corpus(
            args.input_dir,
            args.output_dir,
            measure_latency=not args.omit_runtime_metrics,
        )
    except ProfilingError as exc:
        parser.error(str(exc))

    aggregate = result["aggregate"]
    print(
        "Profiled "
        f"{aggregate['document_count']} files; "
        f"{aggregate['successful_extraction_count']} extracted successfully."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
