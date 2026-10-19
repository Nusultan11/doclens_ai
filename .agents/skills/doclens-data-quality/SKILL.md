---
name: doclens-data-quality
description: Audit or change DocLens corpus/Gold provenance, review, coverage, duplicates, family splits or evaluation-readiness gates. Not for executing parser/RAG comparisons, business analytics or training.
---

# DocLens data quality gates

## Apply and inspect

Use before dataset preparation/model changes or for a dataset-readiness audit.
Read AGENTS.md, the task-selected corpus/Gold protocol, manifest schema and existing
gate/report. Relevant entrypoints are src/doclens_ai/eda/data_quality_gate.py and
docs/eda/data_quality_gate_v3.md; inspect only the validators/labels in scope.
Use [ML data contracts](../../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA) and
[QG-00](../../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES). Private inputs stay local.

## Invariants and workflow

1. Establish immutable RAW provenance, legal/license/usage scope, sensitivity,
   SHA-256/size/format, source version and annotation permission. Missing rights or
   required originals is an explicit gate, not an assumption of eligibility.
2. EDA precedes training or model changes. Audit grain, missing/corrupt/unsupported
   records, format/language/size/structure distributions, exact hashes, near-duplicates,
   translations and document families. Preserve valid differing versions.
3. Keep Extraction Fidelity Gold, Retrieval Gold and RAG Answer Gold distinct.
   Strictly validate review status/source anchors and locators; generated drafts
   never become reviewed labels without human review. Train data stays separate.
4. Check document-family-safe train/dev/test assignments, including versions,
   translations and near-duplicates. Record split revision/seed and human decisions.
   No train/test leakage, sealed-test tuning or reuse of exposed tests as fresh blind data.
5. Build coverage by RU/KK/EN, format, tables/numbers/identifiers, negatives,
   difficult/long/corrupt/scanned inputs and families. Do not infer multilingual
   coverage from a multilingual model or semantic truth from schema validation.
6. Issue separate source-integrity, extraction-fidelity, evaluation-readiness and
   index-eligibility decisions. Keep all failed/needs_review records in coverage
   denominators; report unresolved labels and automatic versus human attestations.

## Failure modes and acceptance

Reject changed/unmatched bytes, invalid review/source linkage, leakage or silent
cohort exclusion. Missing essential inputs means BLOCKED; unresolved automatic
geometry or absent labels is NOT_EVALUATED, never manufactured PASS. Use new
dataset versions for authorized corrections; never silently rewrite frozen Gold.

## Verify and report

Run applicable existing strict validators/gate and focused tests only within the
task's resource/scope budget. Verify no Gold/original mutation before/after.
Report cohort counts, coverage gaps, fingerprints, review provenance, leakage
findings, actual commands/results and separate readiness verdicts. Do not perform
new extraction/model experiments merely to audit metadata.
