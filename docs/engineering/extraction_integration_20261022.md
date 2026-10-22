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

## Slice 4: durable extraction snapshots and re-chunking

Added `models/extraction_artifact.py`, `services/extraction_artifacts.py`, migration
`0009_extraction_artifacts` and real artifact fault tests. S3 keys are server-created
under workspace/version scope and contain the immutable payload checksum. Conditional
PutObject IfNoneMatch is supported by the installed boto3 service model and was
exercised against real MinIO, including rejection of replacement content.
Snapshots retain the entire original per-engine IR (including native metadata),
reconciled IR, source, route and all issues/states. No model weights or private
corpus/Gold is included. The route pins artifact version/byte limit and exact IR
chunk options. Those byte/chunk ceilings are operational safeguards, not QG thresholds.

PG reserves staging identity before S3 work, then checksum readback precedes fenced
available publication. DB triggers enforce source/workspace, current lease and
allowed state transitions and reject identity edits/deletes. Interrupted staging
snapshots are recovered under a fresh lease. Divergent output for the same reserved
run/configuration raises a conflict instead of replacing observations. Available
artifacts are retained. Cleanup considers only staging/discarded snapshots belonging
to terminal failed jobs, checks canonical references, and retains a retryable PG
reservation. A late stale upload can be removed by repeating discarded-row cleanup;
no unknown/shared prefix is deleted.

Canonical span provenance now carries artifact ID/checksum, checked against the
available artifact's version/workspace at publication. `ingest_from_artifact`
supports a new pinned run/chunk budget without an engine or RAW download. It checks
source/scope and original extraction pins; it does not substitute a parser. Native
extraction/chunking semantics remain the default. Published index cutover is unchanged.

Executed:

- First targeted artifact-backed ingestion: **5 passed**, real PG/S3.
- First artifact fault suite: **7 passed**, including no-extraction replay, immutable
  PUT, stale lease, interruption/recovery, corrupted bytes, scoped cleanup, re-chunking
  with changed pinned chunk identity, and two clean schema upgrade/check/downgrade cycles.
- Added a partial-page fixture: failed page/reasons remain in the snapshot while
  only the independently approved page becomes a canonical chunk.
- Existing canonical suite first stopped at **1 failed, 24 passed**: its fault-injection
  wrapper did not forward the new optional artifact provenance arguments. Updated
  the wrapper to forward kwargs; retained the rollback assertion unchanged.
- A new all-failed reconciliation regression first **FAILED** (`partial` instead of
  `failed`). Fixed top-level state while retaining original observations. Targeted
  rerun: **69 passed** across engine/evidence/ingestion units.
- `.venv/Scripts/python.exe .pytest_cache/run_engine_services.py tests/integration/test_extraction_artifacts.py tests/integration/test_engine_ingestion.py tests/integration/test_extraction_routes.py tests/integration/test_canonical_chunks.py tests/integration/test_processing_jobs.py tests/integration/test_worker.py tests/integration/test_production_indexing.py -q --basetemp=.pytest_cache/engine-slice4-services -p no:cacheprovider --tb=short`
  — **82 passed**, real PG/S3/Qdrant, 219.57 seconds.
- The slice 3 broad unit command plus `tests/unit/test_storage_config.py`, using
  `--basetemp=.pytest_cache/engine-slice4-unit`: **408 passed**.
- Ruff checks on all affected modules/migration/tests — PASS; new-file format checks
  and `git diff --check` — PASS. Existing unrelated formatting was preserved.
- Final typed repository/native smoke:
  `.venv/Scripts/python.exe .pytest_cache/run_engine_services.py tests/integration/test_extraction_artifacts.py::test_available_artifact_is_immutable_scoped_and_retry_does_not_extract tests/integration/test_worker.py::test_upload_ingestion_handoff_and_embedding_filter -q --basetemp=.pytest_cache/artifact-typed-final -p no:cacheprovider --tb=short`
  — **2 passed** after final type annotations/formatting cleanup.

Heavy-engine process isolation and complete fake-engine authorized search/fault
coverage remain subsequent slices. Artifact availability is not evidence eligibility,
factual correctness, QG acceptance or production authorization.

## Slice 5: bounded engine processes and cancellation

`extraction/bounded.py` runs registered adapters in fresh spawn processes. Trusted
adapter deserialization/invocation waits for an OS-limit gate. Inputs contain only
trusted application objects, path and pinned route; engine output is bounded JSON,
never pickle. Adapters must stay lightweight at registration and load their heavy
dependencies/models inside `extract`, after the gate. This task loads no real model.
The trusted Python/application spawn bootstrap precedes the gate and is not presented
as an untrusted-code sandbox. Parent decoding and artifact work are separate from
the engine-process memory budget. No egress/OS security sandbox is claimed.

Route snapshots now pin executor version and budgets: wall 60 seconds, CPU 30 seconds,
committed/address-space memory 1 GiB, output 64 MiB, trusted request 1 MiB, one engine
in flight per executor by default. These configurable engineering defaults require
workload qualification before release; they are not approved QG/SLO thresholds.
Windows Job Objects enforce process/job memory, job **user-mode** CPU time, one
process, and kill-on-close; installed limits are read back. Linux unprivileged
workers use read-back-verified prlimit AS/CPU/FSIZE/CORE/NPROC limits and process-group
termination. Unsupported/root Linux execution fails closed. Cleanup joins up to two
seconds after termination, separately from the engine wall budget. Thread environment
defaults are pinned by executor implementation identity; CPU workers hide CUDA devices.
GPU requests are explicitly rejected: no VRAM hard limit, GPU queue, or GPU qualification
is claimed. Capacities are per executor/worker, not a cluster-wide quota.

All ingestion engine calls use this boundary, including the unchanged default native
adapter. Worker cancellation now cancels ingestion and waits for process cleanup;
it cannot hand off or fail an uncertain lease. Engine faults produce sanitized
classifications and use existing bounded retry policy. One duplicate same-lease call
may wait for an artifact replay; further duplicates get retryable backpressure.
Independent source/lease validation is not blocked by that duplicate-call guard.

References used to verify OS/API contracts:
[Windows extended job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information),
[Windows basic job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information),
[job assignment](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
[Python 3.12 resource](https://docs.python.org/3.12/library/resource.html),
[Python 3.12 multiprocessing](https://docs.python.org/3.12/library/multiprocessing.html).

Executed so far:

- Windows `.venv/Scripts/python.exe -m pytest tests/unit/test_bounded_engines.py tests/unit/test_worker.py -x -q --basetemp=.pytest_cache/bounded-final -p no:cacheprovider --tb=short`
  — **31 passed**, actual OS hang/crash/OOM/CPU/output limits and cancellation,
  including observed crash exit 73 and proof hang/CPU fixtures entered engine code.
- Linux same nine executor tests: **9 passed**, unprivileged UID 1000 in the existing
  offline image, network disabled and only src/tests plus existing test dependencies
  mounted read-only. The image lacked pytest initially; reused the existing host's
  pure-Python test packages by appending them after Linux site-packages. No install,
  image/model download or private corpus mount was performed. Repeated final run:
  **9 passed** in 16.17 seconds.
- Real native/fake/artifact process smoke: **7 passed**.
- Initial real-worker hang test **FAILED** because its 1 ms test backoff made the
  same failed job immediately eligible before unrelated work. Used the existing
  production 30-second backoff and explicitly advanced retry timestamps; no coordinator
  policy or acceptance assertion was weakened. Final real-worker faults: **2 passed**,
  proving three same-pin attempts, healthy-job progression, cancellation and no publication.
- Broad unit run and rerun after replay-guard changes: **417 passed** each.
- First full services run: **1 failed, 83 passed** (311.49 seconds): concurrent calls
  for one lease hit new process backpressure instead of idempotent replay. Added a
  one-waiter per-lease lock; original concurrent assertions passed.
- Second full run: **1 failed, 83 passed** (309.01 seconds): an early global caller
  gate blocked independent lease validation. Removed that gate; the executor remains
  the authoritative heavy-process cap. Both original regressions plus actual worker
  faults reran together: **4 passed**. The previous targeted replay/fake/worker set:
  **8 passed**. Final full service acceptance is pending below.

Rollout constraint: drain/stop old workers before producing new configuration
snapshots. Old/unavailable pins fail closed; no queued run is silently rewritten or
backfilled, and no rolling mixed-version queue compatibility is promised.

Final slice 5 compatibility check found a separate defect: reading an old route
through the newly extended v1.0 model injected executor defaults and changed the
stored route fingerprint. `test_artifact_contracts.py` first **FAILED** and demonstrated
that mismatch. New executable routes now have explicit version **1.1**; the exact
`StoredEngineRouteV1` reader preserves original v1.0 snapshots, without inventing
historical execution budgets. Artifact decoding uses an explicit version discriminator.
New workers reject old executable run configurations; old artifacts remain readable
for explicit re-chunking. Targeted compatibility/routing/process checks: **18 passed**.

Current-code final unit command:
`.venv/Scripts/python.exe -m pytest tests/unit/test_artifact_contracts.py tests/unit/test_bounded_engines.py tests/unit/test_document_ir.py tests/unit/test_ir_evidence.py tests/unit/test_extraction_engines.py tests/unit/test_extraction.py tests/unit/test_evidence_regressions.py tests/unit/test_ingestion.py tests/unit/test_processing_state.py tests/unit/test_chunking.py tests/unit/test_safe_cleaning.py tests/unit/test_textblock_offsets.py tests/unit/test_worker.py tests/unit/test_indexing.py tests/unit/test_retrieval.py tests/unit/test_upload_service.py tests/unit/test_storage_config.py --basetemp=.pytest_cache/engine-slice5-versioned-unit -q -p no:cacheprovider --tb=short`
— **418 passed**. Final explicit-v1.1 Linux OS fault tests — **9 passed** in 21.46 seconds.
Ruff check and new-file format checks — PASS; `git diff --check` — PASS.

Final slice 5 real-service command:
`.venv/Scripts/python.exe .pytest_cache/run_engine_services.py tests/integration/test_bounded_worker.py tests/integration/test_extraction_artifacts.py tests/integration/test_engine_ingestion.py tests/integration/test_extraction_routes.py tests/integration/test_canonical_chunks.py tests/integration/test_processing_jobs.py tests/integration/test_worker.py tests/integration/test_production_indexing.py -x -q --basetemp=.pytest_cache/engine-slice5-versioned -p no:cacheprovider --tb=short`
— **84 passed**, 313.23 seconds, after the explicit historical/current route split.

## Slice 6 — authorized search and final integration acceptance

Goal: exercise both incompatible adapters through the same bounded extraction,
immutable artifact, canonical chunk, real index and authorized HTTP search path.
READ: existing engine ingestion/artifact, production indexing, search API and
authenticated-upload test helpers; MODIFY/CREATE: focused tests and this report,
plus only demonstrated extraction-contract corrections if final negatives expose
them. Constraints remain the architecture's verified ACTIVE/ACL contract and the
extraction/ML strategies' evidence and exact-location rules. Sources:
`Doclens_AI-architecture.md`, `DocLens_AI_Extraction_Strategy.md`,
`DocLens_AI_ML_Quality_Strategy.md`, and the current services/tests cited above.
Acceptance: neither canonical nor verified-candidate data is searchable before
ACTIVE; JWT/workspace/revocation checks hold; partial real Qdrant writes preserve
the previous ACTIVE revision; retry and artifact re-chunking preserve pins and
immutable source provenance. Git action: one verified Conventional Commit, no push.

The final synthetic PDF has two actual pages and matching fixture locators. Its
text is synthetic engine output, not PDF fidelity evidence. PostgreSQL, S3/MinIO,
Qdrant and HTTP application/auth decisions are real. Embeddings and extraction are
deterministic fixtures; RSA JWT signatures are checked against fixture JWKS served
by MockTransport. This is a real-service integration test with these explicit
fixtures, not full production E2E or QG-09 acceptance.

The first slice-6 command did not collect tests: the task containers had exited
with code 255 after the earlier run. Inspected their exact task labels and restarted
only the three task-owned ephemeral services; their tmpfs stores are disposable.

New search test development initially failed on nonexistent checksum aliases
(`extraction_artifact_checksum`, then `extraction_artifact_sha256`) and a nonexistent
`UploadResult.processing_run_id`; corrected the test to the actual
`artifact_checksum` field and persisted artifact/run identity. Assertions were
retained. Both engine paths then **PASSED: 2 tests**, 11.07 seconds, including partial
real upsert, old ACTIVE preservation, retry with the same route fingerprint,
re-chunking with no engine registrations, atomic cutover, and membership revocation.

Final negative contract reproduction:
`.venv/Scripts/python.exe -m pytest tests/unit/test_document_ir.py tests/unit/test_processing_state.py -q --basetemp=.pytest_cache/engine-final-negative-red -p no:cacheprovider --tb=short`
— **4 failed, 22 passed**. Three geometry cases silently coerced bool/numeric
strings into coordinates; a changed Pydantic runtime did not change the processing
fingerprint. Geometry now accepts actual numeric coordinates strictly (valid ints
remain accepted), and runtime manifests include actual `pydantic`/`pydantic-core`
versions. No parser/model dependency or quality threshold changed. The fingerprint
change intentionally rejects previously queued incompatible snapshots; the drain
and explicit reprocess rollout constraint still applies. Historical snapshot readers
continue to preserve their exact stored route manifest and fingerprint.

Targeted rerun:
`.venv/Scripts/python.exe -m pytest tests/unit/test_document_ir.py tests/unit/test_processing_state.py tests/unit/test_artifact_contracts.py tests/unit/test_extraction_engines.py tests/unit/test_ir_evidence.py -q --basetemp=.pytest_cache/engine-final-contract-green -p no:cacheprovider --tb=short`
— **81 passed**, 1.46 seconds.

## Final ten-workstream evidence map

These are the request-derived reporting IDs defined above, not a claim about an
unavailable separate numbered audit. `IMPLEMENTED` is scoped to engineering
contracts and the executed tests below, with the stated limitations.

| # | Engineering status / boundary | Main implementation | Behavioral evidence |
|---|---|---|---|
| 1 | IMPLEMENTED — additive DocumentIR v2 | `extraction/ir.py` | `test_document_ir.py`: lossless native roundtrip, typed optional elements, negative geometry/state/version cases |
| 2 | IMPLEMENTED — native plus incompatible adapters | `extraction/adapters.py` | `test_document_ir.py`, `test_extraction_engines.py`, `test_engine_search.py`: words/top-left and regions/bottom-left adapters |
| 3 | IMPLEMENTED — independent recorded evidence admission; PDF opt-in | `extraction/ir_validation.py`, `services/ingestion.py` | `test_ir_evidence.py`, `test_engine_ingestion.py`: self-claims, unknown/stale/wrong-tenant review and default PDF denied |
| 4 | IMPLEMENTED — exact, atomic evidence chunks | `chunking/ir.py` | `test_ir_evidence.py`: signs/units/formulas/header-row links, oversized groups, global budget without partial prefix |
| 5 | IMPLEMENTED — registry through production ingestion | `extraction/engines.py`, `services/ingestion.py` | `test_engine_ingestion.py`, `test_worker.py`, `test_engine_search.py`: native default and both fake routes |
| 6 | IMPLEMENTED — immutable exact run pins | `services/processing.py`, `extraction/runtime.py`, `0008_extraction_route.py` | `test_extraction_routes.py`, `test_processing_state.py`, `test_artifact_contracts.py`: DB immutability, runtime drift, historical route compatibility |
| 7 | IMPLEMENTED — source-aware observation reconciliation | `extraction/reconciliation.py` | `test_extraction_engines.py`, `test_ir_evidence.py`: conflicts/duplicates/confidences retained, contradictory numeric groups denied |
| 8 | IMPLEMENTED — scoped immutable S3/PG artifacts | `services/extraction_artifacts.py`, `models/extraction_artifact.py`, `0009_extraction_artifacts.py` | `test_extraction_artifacts.py`: checksum corruption, partial/failed pages, crash/retry, stale leases, cleanup, no-extraction re-chunk, repeated upgrade/check/downgrade |
| 9 | IMPLEMENTED — bounded CPU engines on Windows/unprivileged Linux; GPU unsupported | `extraction/bounded.py`, `services/worker.py` | `test_bounded_engines.py`, `test_bounded_worker.py`: actual hang/crash/OOM/CPU/output kills, cancellation, backpressure, retry and healthy unrelated job progression |
| 10 | IMPLEMENTED — real-service integration with explicit synthetic fixtures | `test_engine_search.py` (existing search/index/ACL services unchanged) | Two RAW PDFs through bounded extraction/artifacts/chunks/DB/Qdrant/HTTP; auth/cross-tenant/revocation, partial writes, ACTIVE isolation/cutover; broader existing search API/index tests |

Paths in this table are relative to `src/doclens_ai`, `tests/unit`,
`tests/integration`, or `alembic/versions` as appropriate. All ten statuses exclude
model fidelity, automatic semantic verification, GPU/VRAM qualification, QG-00..09
acceptance and production release authorization: **NOT_EVALUATED**.

The trusted review loader is an internal integration interface. This task does not
ship a review administration/store service or authorize arbitrary reviewers/engines.
No public upload API can request PDF trust. Actual model onboarding still requires
independent reviewed evidence, exact approved pins and the relevant quality gates.
Bounds cover engine execution; parent artifact decoding/storage is size-bounded but
is not claimed to share the child's RAM/CPU enforcement or provide an egress sandbox.

## Final verification commands and observations

Windows environment: Python **3.12.3**, Pydantic **2.14.0**, pydantic-core **2.50.0**,
pypdf **6.20.0**, python-docx **1.2.0**, openpyxl **3.1.5**, lxml **6.1.3**,
pytest **9.1.1**, Ruff **0.17.0**, SQLAlchemy **2.1.4**, boto3 **1.43.111**,
httpx **0.28.1**. No dependency, image, model or weight was installed/downloaded.

1. Real services:
   `.venv/Scripts/python.exe .pytest_cache/run_engine_services.py tests/integration/test_engine_search.py tests/integration/test_search_api.py tests/integration/test_bounded_worker.py tests/integration/test_extraction_artifacts.py tests/integration/test_engine_ingestion.py tests/integration/test_extraction_routes.py tests/integration/test_canonical_chunks.py tests/integration/test_processing_jobs.py tests/integration/test_worker.py tests/integration/test_production_indexing.py -x -q --basetemp=.pytest_cache/engine-final-services -p no:cacheprovider --tb=short`
   — **91 passed**, 389.09 seconds, no skipped integration tests.
   After formatting the new fixture file (and thus changing its computed exact
   descriptor digest), reran `tests/integration/test_engine_search.py` with the same
   wrapper, flags and `--basetemp=.pytest_cache/engine-search-formatted-final`:
   **2 passed**, 15.66 seconds.
2. Complete unit suite, initially without inherited repository import paths:
   `.venv/Scripts/python.exe -m pytest tests/unit -q --basetemp=.pytest_cache/engine-final-all-unit -p no:cacheprovider --tb=short`
   — **2 failed, 1995 passed, 5 skipped**, 250.93 seconds. Both failures were
   preexisting tool CLI subprocesses unable to import `tools` (filled ruling
   normalization and PDF table review packet). No related tool code changed.
   Explicitly set `$env:PYTHONPATH = 'C:\Users\nurs\doclens_ai;C:\Users\nurs\doclens_ai\src'`
   in a fresh shell and reran those two exact tests with the same flags and
   `--basetemp=.pytest_cache/engine-cli-path-diagnostic`: **2 passed**, 6.39 seconds.
3. Linux resource suite on current final production code:

   ```powershell
   docker run --pull never --rm --network none --user 1000:1000 --mount 'type=bind,source=C:\Users\nurs\doclens_ai\src,target=/workspace/src,readonly' --mount 'type=bind,source=C:\Users\nurs\doclens_ai\tests,target=/workspace/tests,readonly' --mount 'type=bind,source=C:\Users\nurs\doclens_ai\.venv\Lib\site-packages,target=/host-deps,readonly' --workdir /workspace --env PYTHONPATH=/workspace/src:/workspace --env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 --entrypoint python doclens-search-1791968383266-smoke-api:latest -c "import sys; sys.path.append('/host-deps'); import pytest; raise SystemExit(pytest.main(['tests/unit/test_bounded_engines.py','-q','--basetemp=/tmp/bounded-linux-complete-final','-p','no:cacheprovider']))"
   ```

   — **9 passed**, 20.39 seconds. Earlier final-code run was **1 failed, 8 passed**:
   the one-second CPU budget terminated before the fixture's engine-entry marker.
   The budget includes Python/adapter initialization. Exact unchanged fault subset
   rerun (`-k cpu`, five hang/crash/OOM/CPU/output cases): **5 passed, 4 deselected**,
   15.82 seconds, then the full nine above passed. No budget or assertion was relaxed.
   These deliberately small-budget startup probes are sensitive to machine load;
   the failed observation remains recorded and is not factual/model-quality evidence.
4. `.venv/Scripts/python.exe -m ruff check src tests tools` — **PASS**.
   `.venv/Scripts/python.exe -m ruff format --check src/doclens_ai/extraction/ir.py src/doclens_ai/extraction/runtime.py tests/unit/test_document_ir.py tests/unit/test_processing_state.py tests/integration/test_engine_search.py`
   — **5 files already formatted**, PASS. `git diff --check` — PASS.

Cleanup executed after service and Linux acceptance: verified `codex.task=01a163d8`
on each exact name, then `docker rm -f doclens-engine-pg-01a163d8 doclens-engine-s3b-01a163d8 doclens-engine-s3-01a163d8 doclens-engine-qdrant-01a163d8`.
The filtered task-container inventory is empty. No shared containers, images,
volumes, source corpus, Docker Desktop runtime or user-owned audit were removed.

The complete unit rerun with inherited `PYTHONPATH` but overlapping the separate
Linux OS fault suite had **1 failed, 1996 passed, 5 skipped**, 220.43 seconds:
the Windows CPU fixture reached its 8-second wall deadline before observing the
one-second CPU termination (`timeout` rather than `engine_crash`), although its
engine-entry marker existed. After competing workloads ended, the exact unchanged
Windows executor suite reran with inherited paths:
`.venv/Scripts/python.exe -m pytest tests/unit/test_bounded_engines.py -x -q --basetemp=.pytest_cache/engine-cpu-isolated-diagnostic -p no:cacheprovider --tb=short`
— **9 passed**, 8.77 seconds. Resource-sensitive fault suites must run serially;
wall/CPU ordering under competing CPU/OOM probes is not deterministic. Neither
production limits, fault budgets, expected classifications nor assertions changed.

Final serial unit acceptance (no competing resource-fault/service workload):

```powershell
$env:PYTHONPATH = 'C:\Users\nurs\doclens_ai;C:\Users\nurs\doclens_ai\src'
.venv/Scripts/python.exe -m pytest tests/unit -q --basetemp=.pytest_cache/engine-final-unit-serial -p no:cacheprovider --tb=short
```

— **1997 passed, 5 skipped**, 210.82 seconds, exit 0. Skips are unchanged,
out-of-scope optional checks: Windows symlink privilege (`test_data_quality_gate`)
and four actual browser paths (`test_pdf_assisted_review`, `test_pdf_grid_proposals`,
`test_pdf_proposal_review`, `test_pdf_review_visual`) requiring local
Node/Playwright/Edge inputs or ML30_NODE/ML30_NODE_MODULES. They are not reported as
passed. All scoped engine/resource tests executed successfully in this serial run.

## Completion and Git boundary

Engineering execution: **PASS** for the six requested dependency slices. All ten
request-mapped integration workstreams are IMPLEMENTED within the evidence map's
boundaries. Quality/fidelity/QG-00..09/production release: **NOT_EVALUATED**. No real
ML engine, weights, training, candidate promotion, public PDF trust switch or GPU
enforcement was introduced. Engine admission still requires an explicitly trusted
internal review provider and exact pins; legacy/default PDF remains fail-closed.
Old/unpinned queued runs require an explicit compatible reprocess, not mutation.

Verified commits before this final slice:

- `0386ad9` — `feat(extraction): add additive DocumentIR v2 contracts`
- `8d01d98` — `feat(extraction): validate and chunk reviewed IR evidence`
- `d609e87` — `feat(ingestion): pin extraction routes and reconcile observations`
- `73eb0a2` — `feat(ingestion): persist fenced immutable extraction artifacts`
- `a70f5a2` — `feat(ingestion): isolate engines with enforced process budgets`
- Final slice: this commit — `fix(extraction): verify contracts through authorized search`

Only scoped code/tests and this execution record belong to these commits. The
user-owned `docs/eda/independent_engineering_audit_20261020.md` remains untracked and
unchanged. No push, PR merge, history rewrite, instruction change, shared-resource
deletion or production authorization was performed. Temporary test outputs remain
ignored. The final response reports the actual sixth SHA and exact final status.
