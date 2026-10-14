---
name: doclens-extraction-benchmark
description: Benchmark DocLens PDF, DOCX or XLSX extraction fidelity, or compare an offline parser candidate against a frozen baseline. Not for ingestion implementation, retrieval/RAG evaluation or database migrations.
---

# Extraction fidelity benchmark

Use the existing extraction contract and fidelity evaluator; evaluate candidates
offline without promoting them into production. Read only the relevant protocol,
baseline report and evaluator interfaces needed for the requested experiment.

## Freeze the comparison

1. Validate the task-selected, independently human-reviewed Gold with the strict
   Gold contract and frozen corpus manifest. Verify source hashes, sizes, formats
   and identities; record Gold and corpus fingerprints. Preserve the approved
   records byte-for-byte. If reviewed labels or originals are unavailable, stop
   at the review/data gate; never derive approved labels from parser output.
2. State the hypothesis, acceptance criteria and resource budgets before running.
   Pair baseline and candidate on identical originals, Gold, scoring rules and
   evaluation conditions. Include unsuccessful and needs-review sources, plus
   independent regression controls. Do not select only favorable successes.
3. Record code revision, parser/dependency versions, configuration, model revisions
   and hashes, seeds where applicable, hardware and concurrency. Isolate optional
   candidate dependencies and model artifacts from the production environment.

## Measure and reproduce

4. Use the unchanged evaluator to report required-text recall, reading order,
   table-cell/span and relationship fidelity, value/formula/cache fidelity where
   relevant, provenance, missing evidence and extraction failures. Never execute
   spreadsheet formulas. Show numerators and denominators per format and source
   group; mark metrics without sufficient labels as NOT_EVALUATED.
5. Measure baseline and candidate latency and memory, specifying sample counts,
   cold initialization versus conversion/end-to-end time, peak-memory method,
   units and process scope. Record timeouts and resource failures. Mark unavailable
   measurements explicitly; never substitute zero or guessed values.
6. Run the paired evaluation twice into new ignored output directories. Compare
   deterministic fingerprints and every non-runtime report field; report any
   nondeterminism. Keep timing and memory observations separate from equality
   checks and retain both runs' actual measurements.
7. Compare per-record scores and failure/status/eligibility behavior against the
   frozen baseline, separately for difficult cases and controls. Verify unchanged
   labels and applicable unit/regression tests. Pooled gains must not hide a
   control regression; narrative controls alone do not establish table fidelity.

## Report the decision

8. Report paired deltas, coverage, resource trade-offs, regressions, limitations
   and actual commands/results. Conclude accept, reject or inconclusive against
   the stated criteria; label environmental blockers explicitly. A pilot does
   not establish whole-corpus semantic fidelity or retrieval/RAG superiority.
9. Keep originals, raw annotations and extracted content in ignored local storage.
   Share only sanitized metadata and measured aggregates: no source excerpts,
   private paths, filenames, worksheet names or sensitive cell values. Send only
   public library/version questions to documentation MCP servers, never Gold or
   document content. Follow AGENTS.md for verification, Git and completion format.
