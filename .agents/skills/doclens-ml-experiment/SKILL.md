---
name: doclens-ml-experiment
description: Design or audit a DocLens ML comparison protocol, model experiment or reproducibility/promotion decision. Stage-specific extraction and RAG skills own their scoring; this skill owns shared experiment controls.
---

# DocLens ML experiment protocol

## Apply and inspect

Read AGENTS.md, the previous step verdict, selected baseline report and only the
runner/configuration/Gold interfaces required by the changed stage. Architecture
sections 13–15 define experiment and training gates. Do not load all earlier reports.
Delegate GPU mechanics to doclens-kaggle-gpu only when actual GPU work is authorized.

## Invariants and workflow

1. Require appropriate EDA/data-quality readiness before model changes. Define
   one hypothesis and change one pipeline stage/registered variable at a time.
2. Pre-register champion/candidate, fixed corpus/manifests/Gold/family-safe split,
   primary/guardrail metrics, thresholds, stopping rules and resource budgets.
   Freeze prompt/packing/retrieval when another stage is tested; document unavoidable
   model differences. Never tune on sealed test or reuse exposed data as blind test.
3. Record Git SHA, source/configuration fingerprints, exact model revision and
   loaded artifact hashes, dependencies, seeds, hardware, concurrency and resource
   scope. A declared model name/revision is not verified loaded provenance.
4. Pair comparable observations and preserve repetitions/captures. Include failures,
   missing observations and needs_review cases in denominators; separate execution,
   quality and production-release outcomes.
5. Localize errors to source/extraction, chunk evidence, retrieval, context survival,
   output contract, factual support or refusal. Report sample size and uncertainty;
   small purposive samples and zero observed errors do not establish general safety.

## Metrics and decisions

- Extraction: fidelity, opaque anchors, order, tables and exact locators/provenance.
- Retrieval: Hit@5/10, Recall@5/10, MRR, nDCG@10 and evidence-in-chunk coverage.
- Generation: correctness, groundedness, supported citations, unsupported claims,
  refusal precision/recall and unsafe acceptance; structure is measured separately.
- Operations: P50/P95 latency, RAM/VRAM, cold versus steady scope and failures.

Use PROMOTE, REJECT or INCONCLUSIVE against registered thresholds; essential input
or runtime absence means BLOCKED. PROMOTE is only advancement within the named
experimental scope; production requires separate authorization, safety/quality/
operational gates and rollback. Critical evidence/security regressions force REJECT.
No LoRA/QLoRA without baseline/RAG evaluation and documented error analysis.

## Verify and report

Run stage-focused regressions plus the preregistered comparison, retaining original
failed attempts and actual resource observations. Verify frozen input/model/config
identity before/after, reproducibility and complete population accounting.
Report hypothesis, exact commands/results, pins, metrics/uncertainty, failure causes,
decision and limitations. Do not start the next experiment automatically.
