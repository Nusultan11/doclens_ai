# Extraction integration execution record

Starting point: `main`, `f83def0969a7d14b9d08ac88760e1a0b9b4b188c`.
The existing untracked independent audit is user-owned and excluded from commits.
This record concerns engineering contracts, not QG-00..09 acceptance, model
fidelity, an experiment promotion, or a production release.

## Source and PR comparison

The maintained v4 architecture, extraction strategy, ML chunking contract and
quality policy govern this work. PR #1, head
`9eebdca7b5910107c09994600b3d79124c849b34`, was read through the GitHub connector.
Its registry/native adapter design is useful, but its engine version and
self-declared production flag do not pin implementation/configuration or prove
evidence trust. It does not integrate ingestion or isolate execution. No merge or
cherry-pick was performed; downstream slices must strengthen those boundaries.

The supplied request does not include a separate numbered extraction audit.
For reporting only, its requirements are mapped to ten workstreams: (1) IR,
(2) native and incompatible adapters, (3) independent validation/PDF trust,
(4) evidence chunks, (5) registry/ingestion routing, (6) pinned run configuration,
(7) reconciliation, (8) durable artifacts, (9) bounded execution, (10) authorized
real-service path/fault verification. This mapping is not attributed to the
untracked audit, whose findings use different identifiers.

## Slice 1: additive DocumentIR v2

Added `extraction/ir.py`, `extraction/adapters.py` and
`tests/unit/test_document_ir.py`. The existing ExtractionResult API and native
runtime behavior are unchanged. Optional typed observations include text,
sections/layout, table cells/spans, images/figures and formulas, explicit
coordinate systems, genuine native locators, source/engine identities, relation
observations and partial/failed/unsupported/unresolved issues. Missing evidence
remains unknown. The complete native result is retained losslessly. No adapter
grants verification. Two incompatible synthetic engine payloads exercise this
contract; they are not real models or factual verification evidence.

Executed:

- New contract tests initially: **4 failed, 12 passed**, revealing a v1 derived
  `kind` discriminator round-trip defect. Fixed by validating/removing only that
  constructor-incompatible derived field. Rerun: **16 passed**.
- Initial sandbox regression attempt stalled at asyncio and was interrupted;
  exit 1, not a passing check.
- First unsandboxed regression attempt used a nonexistent temporary parent:
  **42 passed, 54 setup errors**. Created that parent and reran: **96 passed**.
- Broader command (outside the Windows sandbox):
  `.venv/Scripts/python.exe -m pytest tests/unit/test_document_ir.py tests/unit/test_extraction.py tests/unit/test_evidence_regressions.py tests/unit/test_ingestion.py tests/unit/test_processing_state.py tests/unit/test_chunking.py tests/unit/test_safe_cleaning.py tests/unit/test_worker.py tests/unit/test_indexing.py --basetemp=.pytest_cache/engine-slice1 -q -p no:cacheprovider`
  — **248 passed**.
- `.venv/Scripts/python.exe -m ruff check src/doclens_ai/extraction/ir.py src/doclens_ai/extraction/adapters.py tests/unit/test_document_ir.py`
  — PASS. Format check on the same three files — PASS. `git diff --check` — PASS.

Environment preflight: no TEST_* settings are present; `docker info --format
'{{.ServerVersion}}'` fails because the Docker Desktop Linux engine pipe is
absent. Real PostgreSQL/S3/Qdrant checks cannot currently run. This does not
prevent standalone contract work, but it is essential for later persistence
and production-path acceptance. No service or shared resource was modified.
