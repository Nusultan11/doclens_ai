"""Private read-only RAG evaluator; only aggregate metadata is written."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from uuid import UUID

from doclens_ai.core.rag_config import RagSettings
from doclens_ai.evaluation.rag_gold import RagGoldExample, load_rag_gold, validate_rag_gold
from doclens_ai.evaluation.rag_metrics import EvaluationCase, OutputReview, evaluate_rag
from doclens_ai.llm.provider import GeneratorUnavailable, strict_json
from doclens_ai.services.rag import PROMPT_HASH, PROMPT_VERSION, AnswerInput, RagService
from doclens_ai.services.retrieval import (
    SearchResult,
    SearchUnavailable,
    SourceLocator,
    VerifiedResult,
)


def synthetic_gold():
    """Clearly synthetic, hand-coded mechanics fixtures, never real human-reviewed labels."""
    examples = []
    for number, question in enumerate(("Synthetic count?", "Unrelated?", "Empty?", "Invalid?"), 1):
        positive = number == 1
        examples.append(
            RagGoldExample.model_validate(
                {
                    "dataset_revision": "synthetic-rag-gold-v1",
                    "synthetic_fixture": True,
                    "question_id": f"syn-{number:03}",
                    "document_family_id": "syn-family",
                    "split": "dev",
                    "language": "en",
                    "category": "number" if positive else "unanswerable",
                    "question": question,
                    "answerable": positive,
                    "source_document_sha256": ["a" * 64],
                    "accepted_answers": ["7"] if positive else [],
                    "reference_answer": None,
                    "evidence": [
                        {
                            "evidence_id": "syn-anchor",
                            "document_sha256": "a" * 64,
                            "document_format": "pdf",
                            "locator": {"page_number": 1},
                            "source_start": 0,
                            "source_end": 18,
                            "verified_quote": "Synthetic count: 7",
                        }
                    ]
                    if positive
                    else [],
                    "required_citation_refs": ["syn-anchor"] if positive else [],
                    "reviewer_status": "fixture",
                    "reviewer_count": 0,
                }
            )
        )
    return validate_rag_gold(examples)


class SyntheticRetrieval:
    async def search(self, *, user_id, request):
        hits = (
            ()
            if request.query == "Empty?"
            else (
                VerifiedResult(
                    UUID(int=1),
                    UUID(int=2),
                    UUID(int=3),
                    UUID(int=4),
                    request.workspace_id,
                    1.0,
                    "Synthetic count: 7",
                    SourceLocator.model_validate(
                        {
                            "document_format": "pdf",
                            "spans": [
                                {
                                    "source": {"page_number": 1},
                                    "source_start": 0,
                                    "source_end": 18,
                                    "source_length": 18,
                                }
                            ],
                        }
                    ),
                    "a" * 64,
                ),
            )
        )
        return SearchResult(hits, 0, 0, 0, 0)

    async def revalidate(self, **kwargs):
        return True


class SyntheticGenerator:
    async def generate(self, messages):
        data = strict_json(messages[1]["content"])
        if data["question"] == "Invalid?":
            return "not JSON"
        if data["question"] != "Synthetic count?":
            return json.dumps(
                {
                    "answerable": False,
                    "answer": None,
                    "citations": [],
                    "reason": "insufficient_evidence",
                }
            )
        item = data["evidence"][0]
        return json.dumps(
            {
                "answerable": True,
                "answer": "7",
                "reason": None,
                "citations": [
                    {
                        "chunk_id": item["chunk_id"],
                        "document_version_id": item["document_version_id"],
                        "quote": item["text"],
                        "quote_start": 0,
                        "quote_end": len(item["text"]),
                        "answer_start": 0,
                        "answer_end": 1,
                    }
                ],
            }
        )

    async def aclose(self):
        pass


async def run_cases(gold, service, user_id, workspace_id):
    cases = []
    for example in gold.examples:
        before = time.perf_counter()
        try:
            result = await service.answer(
                user_id=user_id,
                request=AnswerInput(workspace_id=workspace_id, question=example.question),
            )
            cases.append(EvaluationCase(example.question_id, result, result.latency_ms))
        except (GeneratorUnavailable, SearchUnavailable) as error:
            cases.append(
                EvaluationCase(
                    example.question_id,
                    None,
                    (time.perf_counter() - before) * 1000,
                    True,
                    "model" if isinstance(error, GeneratorUnavailable) else "retrieval",
                )
            )
    return cases


async def evaluate(args):
    database = retrieval = service = None
    try:
        if args.synthetic:
            gold, settings = synthetic_gold(), RagSettings(_env_file=None)
            service = RagService(SyntheticRetrieval(), SyntheticGenerator(), settings)
            user_id, workspace_id = UUID(int=5), UUID(int=6)
            generator_metadata = {"provider": "deterministic_synthetic_fixture_not_model"}
            retrieval_metadata = {"provider": "synthetic_fixture_not_production_retrieval"}
        else:
            if not args.gold or not args.user_id or not args.workspace_id:
                raise ValueError("real evaluation requires approved Gold and trusted scope")
            gold = load_rag_gold(args.gold, manifest_path=args.manifest)
            if gold.examples[0].synthetic_fixture:
                raise ValueError("synthetic Gold requires explicit --synthetic mode")
            from doclens_ai.core.config import get_settings
            from doclens_ai.core.search_config import SearchSettings
            from doclens_ai.db.session import Database
            from doclens_ai.rag_runtime import build_rag_runtime
            from doclens_ai.search_runtime import build_search_runtime

            database = Database(get_settings().database_url)
            retrieval = await build_search_runtime(database.session_factory, SearchSettings())
            settings = RagSettings()
            service = build_rag_runtime(retrieval, settings)
            user_id, workspace_id = args.user_id, args.workspace_id
            generator_metadata = service.generator.metadata()
            retrieval_metadata = {"embedding_fingerprint": retrieval.encoder.fingerprint}
        cases = await run_cases(gold, service, user_id, workspace_id)
        experiment = {
            "prompt_version": PROMPT_VERSION,
            "prompt_hash": PROMPT_HASH,
            "generator": generator_metadata,
            "retrieval": retrieval_metadata,
            "candidate_top_k": 20,
            "max_evidence_chunks": settings.max_evidence_chunks,
            "max_context_chars": settings.max_context_chars,
            "max_chunk_chars": settings.max_chunk_chars,
            "budget_unit": "unicode_characters_not_tokens",
        }
        reviews = []
        if args.reviews:
            if args.synthetic:
                raise ValueError("synthetic fixtures cannot claim human quality review")
            reviews = [
                OutputReview.model_validate(strict_json(line))
                for line in args.reviews.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        report = evaluate_rag(gold, cases, experiment=experiment, reviews=reviews)
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "metrics.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "query_count": report["query_count"],
                    "evaluation_basis": report["evaluation_basis"],
                    "human_quality_status": report["human_quality"]["status"],
                }
            )
        )
        return 1 if any(case.failure for case in cases) else 0
    finally:
        if service is not None:
            await service.aclose()
        if retrieval is not None:
            await retrieval.aclose()
        if database is not None:
            await database.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--synthetic", action="store_true")
    mode.add_argument("--gold", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("docs/eda/corpus_v1_manifest.csv"))
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--user-id", type=UUID)
    parser.add_argument("--workspace-id", type=UUID)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        return asyncio.run(evaluate(args))
    except Exception:
        print("RAG evaluation failed; check approved local configuration and inputs")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
