from __future__ import annotations

import argparse
from pathlib import Path

from doclens_ai.retrieval_baseline.runner import run_baseline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the frozen offline BM25 v1 experiment")
    parser.add_argument("--corpus-dir", type=Path, default=Path("local-corpus"))
    parser.add_argument(
        "--corpus-manifest", type=Path, default=Path("docs/eda/corpus_v1_manifest.csv")
    )
    parser.add_argument(
        "--gold", type=Path, default=Path("local-evaluation/retrieval_gold_v1.jsonl")
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        experiment = run_baseline(
            corpus_dir=args.corpus_dir,
            manifest_path=args.corpus_manifest,
            gold_path=args.gold,
            output_dir=args.output_dir,
        )
    except ValueError as exc:
        parser.error(str(exc))
    except OSError:
        parser.error("unable to read verified inputs or write local experiment outputs")
    corpus = experiment["corpus"]
    print(
        f"Sources: {corpus['source_count']}; eligible: {corpus['eligible_count']}; "
        f"indexed chunks: {corpus['indexed_chunk_count']}"
    )
    print(f"Questions: {experiment['query_count']}")
    print(f"Ranked-results fingerprint: {experiment['results_fingerprint']}")
    print(f"Quality-report fingerprint: {experiment['report_fingerprint']}")
    print("Workspace security: NOT EVALUATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
