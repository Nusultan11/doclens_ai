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

## Slice 2: independent validation and atomic evidence chunks

Added `extraction/ir_validation.py`, `chunking/ir.py` and
`tests/unit/test_ir_evidence.py`; hardened malformed native wire decoding in
`extraction/ir.py`. This standalone boundary requires a caller-owned review
record bound to the complete IR, exact element/relation digests, source/version/
workspace, and engine/reviewer allowlists. Engine verification claims alone do
not authorize evidence. No public API accepts those review/policy inputs.
Production ingestion is not connected yet; its legacy PDF rejection is unchanged.

Validation checks actual supported element/relation kinds, native locators,
geometry, table ownership/overlap/bounded grid expansion, formula/cache availability,
negative states, review coverage and unresolved/conflicting relations. Linked
evidence is held as a group if any member is unsafe. Exact text/sign/precision,
formula/cache strings and full observed geometry remain in searchable units;
existing Chunk spans retain genuine source locations and element digest references.
Oversized groups are held intact. Document budget failure returns no partial prefix.
Durable resolution of those references is a later artifact-integration requirement.

Executed:

- Red test before implementation: `python -m pytest tests/unit/test_ir_evidence.py
  -q -p no:cacheprovider` — collection FAIL, missing `chunking.ir`.
- First implementation run: **1 failed, 23 passed**. A synthetic fixture reused
  the same page-only address for three text observations, correctly triggering
  ambiguous ownership. Assigned distinct genuine synthetic block addresses.
- IR/evidence targeted checks: **62 passed** (16 IR + 46 evidence cases).
- Broader final command (outside the Windows sandbox):
  `.venv/Scripts/python.exe -m pytest tests/unit/test_document_ir.py tests/unit/test_ir_evidence.py tests/unit/test_extraction.py tests/unit/test_evidence_regressions.py tests/unit/test_ingestion.py tests/unit/test_processing_state.py tests/unit/test_chunking.py tests/unit/test_safe_cleaning.py tests/unit/test_textblock_offsets.py tests/unit/test_worker.py tests/unit/test_indexing.py tests/unit/test_retrieval.py --basetemp=.pytest_cache/engine-slice2-final -q -p no:cacheprovider`
  — **385 passed**.
- Ruff check and format check on the four changed/new Python files — PASS.

Service preflight follow-up: Docker was stopped even outside the sandbox. Starting
the installed Docker Desktop runtime succeeded; `docker info --format
'{{.ServerVersion}}'` now reports **29.8.2**. Existing PostgreSQL, MinIO and Qdrant
images are available locally. No previously running containers were found. The
initial service limitation is resolved far enough to attempt isolated fixtures;
real-service verification is still pending, not passed.

## Slice 3: immutable route pins, registry and ingestion integration

New `extraction/engines.py` selectively reuses PR #1's registry/native-adapter
design, with exact name/revision/implementation pins and an application-owned
allowlist. There is no engine-supplied production approval flag. All routes are
resolved before extraction; no implicit fallback/preprocessing is supported.
The native parser remains the only default registration. Parser limits moved
unchanged to `extraction/limits.py`, re-exported through the existing parsers
import, so API-side pin creation does not import optional parser libraries.

New ProcessingRun configuration version 1.2 stores the full immutable route,
effective native options, runtime package/Python/code manifest, contract versions
and route fingerprint inputs. Migration `0008_extraction_route` adds a nullable
JSONB snapshot and immutable-update trigger. Historical rows remain NULL rather
than receiving invented pins; the new worker rejects them. Existing ACTIVE
revisions/chunks remain untouched. Deploy migration before new application code.
Downgrade removes route snapshots; it is a rollback mechanism verified only on
disposable databases, not a way to preserve new-run reproducibility for old workers.

Ingestion now resolves engine pins from the stored run. Verified IR mode requires
an explicitly pinned policy digest and review-record ID from an internal trusted
loader; no external upload API field grants that trust. It uses the same source
download/checksum, lease fencing and atomic canonical publication boundaries.
The default native mode still uses existing native admission and chunking, including
the legacy PDF ban. `reconciliation.py` binds observations to source/tenant/version,
retains values/confidences/locators, namespaces identities, and preserves exact-address
duplicates/conflicts with unresolved ownership. It never chooses a fact by confidence
or fabricates geometry. Multi-engine raw observations require later artifact retention.

Executed findings and checks:

- Pre-change real-service baseline: **37 passed**, domain migrations, worker and
  production indexing. Docker uses task-only containers labelled `codex.task=01a163d8`,
  loopback ephemeral ports and tmpfs, using existing local images; no model downloads.
  The first MinIO fixture failed tmpfs ownership; a separate temporary fixture with
  writable data storage replaced it. No shared data/volumes were touched.
- The new migration initially failed: asyncpg forbids multiple prepared commands
  in one execution. Split function and trigger creation into separate statements.
  Interrupted the failing batch, fixed the unapplied transactional migration, and
  reran existing canonical/processing integration tests: **31 passed**.
- New exact routing/reconciliation unit tests: **6 passed**.
- New real PostgreSQL migration/route immutability tests: **2 passed**, including
  two upgrade/check/downgrade cycles retaining historical NULL routes.
- Both incompatible fake engines through real RAW S3, routing, reviewed IR and
  canonical PG publication, plus missing-review/cross-tenant/unavailable-pin negatives:
  **5 passed**. No LLM or real extraction model was invoked.
- Broader unit run initially **3 failed, 398 passed** because private source fixtures
  omitted the newly mandatory workspace/route inputs. Updated those two constructors
  without changing assertions. Final broader run: **401 passed**.

Exact final unit command:
`.venv/Scripts/python.exe -m pytest tests/unit/test_document_ir.py tests/unit/test_ir_evidence.py tests/unit/test_extraction_engines.py tests/unit/test_extraction.py tests/unit/test_evidence_regressions.py tests/unit/test_ingestion.py tests/unit/test_processing_state.py tests/unit/test_chunking.py tests/unit/test_safe_cleaning.py tests/unit/test_textblock_offsets.py tests/unit/test_worker.py tests/unit/test_indexing.py tests/unit/test_retrieval.py tests/unit/test_upload_service.py --basetemp=.pytest_cache/engine-slice3-unit-final -q -p no:cacheprovider`

Service runs use a session-local ignored helper that verifies those container
labels, derives loopback TEST_DATABASE_URL/TEST_S3_*/TEST_QDRANT_URL from Docker port
bindings, initializes only the task-owned private bucket, then invokes pytest.
The initial helper re-creation hit BucketAlreadyOwnedByYou; made its fixture setup
idempotent and reran. This was not an application test failure. The helper contains
only the already documented local test credentials; no private source/Gold is used.

Final slice 3 checks:

- `.venv/Scripts/python.exe .pytest_cache/run_engine_services.py tests/integration/test_worker.py tests/integration/test_production_indexing.py tests/integration/test_canonical_chunks.py tests/integration/test_processing_jobs.py tests/integration/test_extraction_routes.py tests/integration/test_engine_ingestion.py -q --basetemp=.pytest_cache/engine-slice3-services -p no:cacheprovider --tb=short`
  — **74 passed** in 193.39 seconds, using real PG/S3/Qdrant.
- Final inspection found that a manually constructed native route could omit
  effective limits and use implicit defaults. NativeEngine now requires every
  effective option explicitly. Added regression; reran the preceding unit command
  with `--basetemp=.pytest_cache/engine-slice3-unit-options`: **402 passed**.
- `.venv/Scripts/python.exe .pytest_cache/run_engine_services.py tests/integration/test_worker.py::test_upload_ingestion_handoff_and_embedding_filter tests/integration/test_engine_ingestion.py tests/integration/test_extraction_routes.py -q --basetemp=.pytest_cache/engine-slice3-final -p no:cacheprovider --tb=short`
  — **8 passed** after that final hardening.
- Ruff check on extraction and affected service/model/migration/test files — PASS;
  format checks on the new modules/tests — PASS; `git diff --check` — PASS.
