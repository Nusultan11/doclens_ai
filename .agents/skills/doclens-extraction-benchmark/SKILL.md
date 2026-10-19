---
name: doclens-extraction-benchmark
description: Compare frozen DocLens PDF, DOCX or XLSX parser fidelity, or diagnose extraction benchmark regressions. Not for ingestion implementation, database migrations or retrieval/RAG evaluation.
---

# DocLens extraction fidelity

## Apply and inspect

Read AGENTS.md, the selected protocol/baseline report and relevant extraction
contract, scorer, Gold validator and candidate functions. [Extraction Strategy](../../../DocLens_AI_Extraction_Strategy.md) defines methods;
[Quality Policy](../../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES) owns acceptance;
[ML protocol](../../../DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) owns shared controls.
Read private originals/Gold only locally as authorized; never export their text.

## Invariants and workflow

1. Verify immutable corpus manifest, original SHA/size/format/identity and strict
   human-reviewed Extraction Fidelity Gold. Freeze byte and normalized hashes,
   cohort, independent regression controls, scoring rules, models/configurations
   and split provenance.
   Missing critical inputs means BLOCKED; never derive approved labels from output.
2. For a new experiment, pre-register one hypothesis, thresholds and CPU/RAM/time
   budgets. Compare baseline/candidate on identical inputs. Keep pypdf as production
   PDF baseline; optional Docling/OCR remains offline until separate approval.
   Keep candidate dependencies and model artifacts isolated from production runtime.
3. Measure required-anchor presence by opaque identity, reading order, table cells/
   spans/relationships and exact locators/provenance. For DOCX expose ancillary
   content limitations; for XLSX separate stored values, formulas, caches and display.
   Never execute formulas or fabricate unavailable locators or table links.
4. Keep all failed/needs_review sources in denominators; missing observations are
   UNKNOWN, not invented zero scores. Extraction success is not evidence fidelity.
   Report per-document/difficult/control results and full attempted/eligible coverage.
5. New paired comparisons run twice into new ignored directories. Compare every
   non-runtime field and deterministic fingerprint; retain both actual timings.
   Record dependencies/model revisions/hashes, Git SHA, seeds, hardware/concurrency,
   cold initialization/conversion scope and peak-memory method/units/process tree.
6. For diagnosis-only tasks, reuse captured metadata first. Perform only explicitly
   bounded read-only inspections if needed; do not rerun full experiments or tune.
   Compare inspected extraction fingerprints to frozen outputs. Separate observed
   omission/fragmentation/order/locator/status mechanisms from hypotheses/UNKNOWN.

## Failure modes and acceptance

Critical baseline-present anchor loss, control regression, new eligibility/failure
regression, fabricated provenance or unsafe behavior forces REJECT under the
registered gate. Pooled table gains cannot cancel critical evidence loss.
Use INCONCLUSIVE for insufficient/non-reproducible evidence and NOT_EVALUATED for
unlabelled dimensions. Unknown measurements are never guessed. Distinguish
execution success from candidate quality and from production approval.

## Verify and report

Run existing focused extraction/candidate tests; recheck input/code/model pins and
per-anchor score agreement. No subjective examples establish generalization.
Report counts, status transitions, fingerprints, resources, actual commands/results,
regressions and advancement verdict. Keep originals, raw annotations and extracted
content ignored; publish only sanitized aggregates/opaque IDs, never filenames,
private paths, excerpts or values. No parser promotion is implied.
