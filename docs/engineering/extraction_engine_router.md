# Extraction engine routing foundation

Status: implementation scaffolding on an isolated feature branch. **Not a production model integration or extraction-quality improvement.**

## Current API

`doclens_ai.extraction.engines` supplies a simple, explicit boundary between format-specific extraction engines and consumers:

- `EngineDescriptor`: stable engine name, version, supported formats, declared capabilities and production review flag.
- `ExtractionEngine`: `descriptor` and `extract(Path) -> ExtractionResult`.
- `EngineRegistry`: explicit registration; rejects duplicate/unknown engines, mismatched formats/capabilities and unreviewed production routes.
- `NativeEngine`: compatibility adapter for the existing `extract_file`, with lazy import of optional native parser libraries.
- `extract_routed`: opt-in dispatch for standalone experiments; **not yet used by production ingestion**.

The default registry contains only `native`. No OCR, Docling, VLM or layout model is installed, enabled, trained, downloaded, or permitted as an implicit fallback.

## Extension contract

A future OCR/layout/table engine must:

1. Implement the `ExtractionEngine` protocol, declare its format/capability contract and supply stable model/config/artifact identities before production selection.
2. Preserve original source identity and **genuine** evidence locators. Never assign fabricated PDF cells, glyph IDs, page coordinates or spreadsheet values.
3. Distinguish a candidate result from validated evidence; `ExtractionStatus.SUCCESS` alone is not sufficient for trusted indexing.
4. Be evaluated against frozen, permission-qualified source/Gold sets and native baseline with critical-loss guardrails.
5. Receive its own bounded subprocess and resource policy. The registry is **not** a process sandbox.
6. Be explicitly approved and wired through a versioned processing configuration before the ingestion worker can route to it. Its versions and hashes must be included in the processing fingerprint and deterministic chunk lineage. Historical jobs must not silently change engines.

## Next implementation boundary

Next step after review: integrate the registry into the ingestion worker with a pinned engine-selection configuration, process isolation, review-only candidate handling, worker lifecycle tests and fingerprint/version upgrade strategy. Avoid mixing this change with PDF OCR/model experiments or relaxing `evidence_is_indexable`.

References: `AGENTS.md`, `DocLens_AI_Extraction_Strategy.md`, `Doclens_AI-architecture.md`, `src/doclens_ai/extraction/validation.py`.

## Local verification

```bash
python -m pytest tests/unit/test_extraction_engines.py tests/unit/test_extraction.py -q
ruff check src/doclens_ai/extraction/engines.py tests/unit/test_extraction_engines.py
ruff format --check src/doclens_ai/extraction/engines.py tests/unit/test_extraction_engines.py
```

These commands are proposed checks, not a claim of successful local execution.
