---
name: doclens-rag-evaluation
description: Evaluate DocLens changes to retrieval-affecting chunking, embeddings, dense/sparse/hybrid retrieval, metadata filters, top-k, fusion, reranking, context construction, grounded generation, or quality-sensitive RAG prompts. Do not use for unrelated LLM or document work.
---

# DocLens RAG evaluation

Define the quality hypothesis and failure modes before changing the pipeline. When claiming improvement, compare before and after on a fixed evaluation dataset with identical corpus, queries, relevance judgments, environment, and measurement settings except for the variable under test.

Use metrics appropriate to the changed stage:

- retrieval Recall@k or hit rate;
- MRR or nDCG when graded or ranked judgments exist;
- citation precision/recall and source traceability;
- unsupported-claim or faithfulness rate;
- abstention/refusal behavior for insufficient evidence;
- latency, with ingestion/query costs separated where useful.

Include regressions and relevant workspace/metadata-filter isolation checks. Record dataset/version, configuration, model revisions, seeds where applicable, sample size, and commands so the comparison is reproducible.

Qualitative examples may explain measured results but cannot establish improvement by themselves. Diagnose retrieval failures in retrieval; do not start fine-tuning to compensate for missing or irrelevant evidence. State uncertainty and tradeoffs when metrics disagree.
