---
name: doclens-rag-evaluation
description: Evaluate DocLens retrieval, embeddings/chunking effects, context packing, grounded generation or quality-sensitive prompts. Not for parser fidelity, dataset readiness alone or GPU execution mechanics.
---

# DocLens retrieval and RAG evaluation

## Apply and inspect

Read AGENTS.md, the changed stage, its focused tests, selected Gold protocol and
baseline report. Relevant code is services/retrieval.py and services/rag.py under
src/doclens_ai; inspect packing/validators only as needed. [ML Strategy](../../../DocLens_AI_ML_Quality_Strategy.md#ML-RETRIEVAL) separates
retrieval, evidence and semantic methods; [Quality Policy](../../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES) owns acceptance. Use the data-quality
skill for dataset readiness and the experiment skill for a new comparison protocol.

## Invariants and workflow

1. Freeze reviewed Retrieval Gold separately from RAG Answer Gold, corpus/chunks,
   families/splits, champion/configuration/model revisions and authorized scope.
   Gold selects scoring/splits, never retrieval filters, packed evidence or answers.
2. State one hypothesis and stage-specific thresholds. Compare identical conditions
   except the registered variable. Keep failures, invalid output and refusals in
   denominators. Do not tune on sealed test or relabel exposed data as fresh test.
3. Diagnose six separate stages:
   - Candidate discovery: Hit/Recall@5/10, MRR, nDCG@10 and bounded ranking horizon.
   - Relevant evidence inside retrieved chunks: complete anchors/relationships,
     including numbers, table headings and provenance, not chunk presence alone.
   - Packing survival: retrieved -> packed anchors, truncation, deduplication,
     character versus tokenizer budget, with fixed candidate pools for packing A/B.
   - Answer factual correctness against independently reviewed evidence.
   - Groundedness/semantic citation support and unsupported claims.
   - Correct refusals, refusal precision/recall and unsafe accepted answers.
4. Separate HTTP/runtime, strict JSON, ModelAnswer, citation identity/offset/coverage,
   semantic support and production-release counts. Structural validity or exact
   quotes never proves entailment; invalid output is not a correct refusal.
5. Include negative and adversarial cases: insufficient evidence, negation,
   conflicting sources, wrong entity and document prompt injection. Preserve
   document-scoped negative labels; do not infer workspace-wide truth from them.
6. Preserve backend-derived Qdrant filters and PostgreSQL source/ACL/ACTIVE
   verification before context and after inference. Test revocation, stale revisions
   and cross-tenant attempts; document the residual post-validation delivery race.

## Failure modes and acceptance

Reject unsafe accepted answers, critical evidence loss or authorization regressions.
No model/prompt/binder promotion solely from schema, quote offsets or citation
coverage. Human-reviewed semantics and AI-assisted diagnostics are different
evidence classes. Mark unsupported semantic/language slices NOT_EVALUATED.
Diagnose upstream retrieval/context failures before fine-tuning or adding rerankers.

## Verify and report

Run changed-stage tests and fixed offline evaluation when claiming quality change.
Report numerators/denominators by split/language/format/category, negative safety,
context survival, citations, P50/P95/resources, actual commands, pins and limits.
Qualitative examples only explain measurements. Separate experiment decision
from production promotion/rollback; follow AGENTS.md completion format.
