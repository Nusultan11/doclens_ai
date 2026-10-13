from __future__ import annotations

import argparse
from pathlib import Path

from doclens_ai.dense_baseline.runner import run_dense


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen local E5 + disposable Qdrant experiment")
    parser.add_argument("--corpus-dir", type=Path, default=Path("local-corpus"))
    parser.add_argument(
        "--corpus-manifest", type=Path, default=Path("docs/eda/corpus_v1_manifest.csv")
    )
    parser.add_argument(
        "--gold", type=Path, default=Path("local-evaluation/retrieval_gold_v1.jsonl")
    )
    parser.add_argument("--bm25-dir", type=Path, default=Path("evaluation-output/bm25-v1-run-1"))
    parser.add_argument("--model-dir", type=Path, default=Path("evaluation-output/dense-v1-model"))
    parser.add_argument("--qdrant-url", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run_dense(
            corpus_dir=args.corpus_dir,
            manifest_path=args.corpus_manifest,
            gold_path=args.gold,
            bm25_dir=args.bm25_dir,
            model_dir=args.model_dir,
            qdrant_url=args.qdrant_url,
            output_dir=args.output_dir,
        )
    except ValueError as exc:
        parser.error(str(exc))
    except (OSError, KeyError, TypeError):
        parser.error("unable to read verified inputs or complete the local experiment")
    print(
        f"Indexed points: {result['qdrant']['point_count']}; model dimensions: "
        f"{result['model']['dimensions']}"
    )
    print(f"Ranked-results fingerprint: {result['results_fingerprint']}")
    print(f"Quality-report fingerprint: {result['report_fingerprint']}")
    print("Workspace security: NOT EVALUATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
