# Autonomous audit closure — 24 October 2026

STATUS: **PASS for the scoped engineering closure and executed checks.**
Quality QG-00/QG-01: **NOT_EVALUATED**. Independent TEST: **TEST_NOT_READY**.
No production release or model promotion is authorized by these results.

## Scope, sources and initial state

The supplied closure request enumerates the findings addressed here. A separate
full 24 October audit document was not attached; the existing untracked 20 October
audit is historical context, not evidence about today's HEAD. No unavailable
attachment is claimed as read. The scope is confirmed engineering gaps in research
integration, evidence completeness/fidelity, family coverage and regression checks.

Requirements: root `AGENTS.md`, `README_SOURCE_MAP.md`, architecture upload/jobs/index
and security contracts, Extraction Strategy, ML-DATA/ML-CHUNK and Quality Policy
QG-00/01/02/03/05/06. Ingestion-change and data-quality skills applied. No nested
AGENTS.md exists in affected paths. No instruction, dependency, model, migration,
quality threshold, historical report, corpus, Gold or existing review queue changed.

Initial branch: `codex/extraction-research-20261023`.
Initial HEAD: `1366558dc89708c1a7ed719d9a396d64752ba267`, 19 commits ahead of
`main` at `f83def0969a7d14b9d08ac88760e1a0b9b4b188c`.
Consolidation branch: `codex/extraction-consolidation-20261024` at
`5019301fd24957e278975e80247e56e55940d044`.

Created `codex/audit-closure-20261024` from the research HEAD. Compared both branches
against their integration ancestor `2bbcbdc`. Reused only the compatible eight-file
capability-routing delta from consolidation. Preserved all 19 research commits,
including readiness tooling and frozen decisions absent from consolidation.
No merge, rebase, cherry-pick, reset, push or shared-resource deletion occurred.

The initial tree contained one modified and eleven untracked files (listed at the
end). Their initial HEAD/status/SHA-256 receipt is private under
`evaluation-output/audit-closure-20261024/initial-state.json`. All twelve files are
excluded from this task's commits and checked for byte-for-byte preservation.

## Finding classification and work deliberately not repeated

| Finding group | Initial classification | Evidence / action |
| --- | --- | --- |
| Historical baseline and research divergence | PARTIAL | Research already contains integration foundation; reuse only missing router delta |
| DocumentIR v2, adapters, validation, reconciliation | DONE_VERIFIED except partial-state bug | Existing source/wire tests reused; preserve observed partial state |
| Bounded execution/process faults | DONE_UNVERIFIED for this HEAD | Reuse implementation and existing actual OS tests; no replacement executor |
| Immutable artifacts and reprocessing | DONE_UNVERIFIED for this HEAD | Existing artifact and real-service tests reused; reject incomplete publication |
| Migrations 0008/0009 and lifecycle fencing | DONE_UNVERIFIED for this HEAD | Preserve migration bytes; run disposable-database migration and lifecycle tests |
| Silent publication after evidence rejection/holding | PARTIAL | Reproduced four accepted incomplete cases; require complete result before canonical persistence |
| Previously persisted IR subsets / pre-rollout candidates | PARTIAL | Both index preparation and cutover accepted old IR subsets; require current complete-admission pins at both boundaries |
| Formula `None`, lexical values, atomic relations, offsets | PARTIAL | Fix renderer, reading-order grouping and dropped native text-offset maps; reuse numeric/table tests |
| Corpus/RAW/family manifests and held-out reservations | DONE_VERIFIED | Existing manifests, components and strict loaders reused; no EDA/acquisition campaign |
| Format/language/difficulty coverage | PARTIAL | Existing EDA retained; add reusable family-grain facets to existing metadata-only readiness report |
| Licensing and operation-specific rights | DONE_VERIFIED tooling / EXTERNAL_BLOCKED clearance | Existing rights ledger/quarantines preserved; no broadened data use |
| Human review queues/adjudication | DONE_VERIFIED infrastructure / EXTERNAL_BLOCKED decisions | Reuse frozen reviewer queue and adjudication fields; no fabricated human approvals |
| Dataset/configuration/Gold fingerprints | DONE_VERIFIED | Existing frozen release integrity verified read-only |
| Exact/near/template/version/translation isolation | DONE_VERIFIED declarations / EXTERNAL_BLOCKED completeness | Reuse components and leakage regressions; no invented human family completeness |
| Sealed independent TEST and approved QG thresholds | EXTERNAL_BLOCKED | TEST_NOT_READY; QG-00/01 NOT_EVALUATED |
| Competing evaluation or CI framework | OBSOLETE | Existing evaluator and CI unit discovery cover new regressions |
| Fresh model/GPU benchmarks or parser rewrite | OBSOLETE for closure | Existing results/rejected configurations retained; none repeated |
| Performance optimization | No demonstrated new bottleneck | No optimization or performance improvement claimed |

## Implemented changes and boundaries

1. Capability routing: exact-pin registration, explicit capabilities and format
   selection, pre-execution rejection, historical v1.0/v1.1 artifact readers, v1.2
   route fingerprints and re-chunk capability compatibility. This is reused work
   from the consolidation branch, not a newly invented engine framework.
2. Completeness: `EvidenceChunks.status` distinguishes `complete`,
   `partial_review_required` and `blocked`. Diagnostic safe subsets may still be
   inspected offline. Ingestion accepts only complete outcomes. Partial observations
   without issue records retain their partial state through reconciliation. Failed
   candidates keep immutable diagnostics and the previous ACTIVE revision.
3. Fidelity: absent formula fields are omitted instead of rendered as literal
   `None`; empty/zero/negative/precision/identifier distinctions remain lexical.
   Only containment and semantic relationships join atomic groups. Reviewed
   outgoing reading-order relations remain attached to their original source unit.
   Table/cell identity and semantic links survive the unchanged IR wire format and
   retained snapshots. Native TextBlock maps now survive canonical JSON persistence;
   generated rendered offsets retain their separate `rendered_source_unit` basis.
   IR without a native map gains no claimed native offsets. Validator/chunker
   versions are 2.1/2.2; incompatible old execution pins fail closed while historical
   artifacts and already persisted canonical rows remain readable.
4. Publication compatibility: a shared guard rejects obsolete verified-IR route or
   canonical chunker pins during index preparation and transactional ACTIVE cutover.
   It also stops candidates verified by an older worker from bypassing ingestion.
   Existing native/unpinned processing retains its prior contract. Historical data
   is not rewritten or deleted; earlier ACTIVE data is retained, not retrospectively
   certified. Old verified-IR pending work needs explicit compatible reprocessing.
5. Readiness: existing isolation report v2 adds connected-family/document counts
   before and after eligibility, format/language cross-facets, declared difficulty
   facets, unknowns and zero-eligible gaps. It consumes the existing component graph
   and never reads RAW, reclassifies language, creates Gold or changes admission.
   Facets overlap and must not be summed. Eligibility is the existing declared dev
   isolation/local-use result, not independent quality or other data permissions.

On the existing 150-document metadata cohort: 75 connected families; 138 documents
and 71 families dev-isolation eligible; 12 documents excluded. Of 60 Office
candidates, 55 remain eligible and five excluded. Its declared language facets
contain EN 88, CY 2, unknown 60, RU/KK/mixed zero. This is the historical 150-source
cohort only: the separate existing 217-source continuation includes additional
RU/KK/mixed observations and is not replaced or relabelled by this report.
Verified content language and independent Gold remain NOT_EVALUATED.

## Verification

All commands run from `C:/Users/nurs/doclens_ai` using existing
`.venv/Scripts/python.exe` (abbreviated PY). PYTHONPATH contains the repository root
and src. PYTHONDONTWRITEBYTECODE=1; final unit checks also set HF_HUB_OFFLINE=1 and
TRANSFORMERS_OFFLINE=1. No dependency/model/image was installed or downloaded.
Private JUnit/receipts/output paths are under evaluation-output/audit-closure-20261024.

Initial regression evidence:

- Four incomplete-document scenarios accepted ingestion before the fix: all four
  failed the expected-rejection regression (`DID NOT RAISE IngestionFailure`).
- Partial reconciliation without issues returned complete before the fix.
- Fidelity regressions: six failed, nine passed before corrections (three absent
  formula-field cases, reading-order sizing/propagation, dropped native offset map).
- Family summary regressions: two failed, fourteen passed before the extension.
- Legacy persisted-subset regressions: both preparation and already-verified
  cutover failed their expected rejection before the final publication guard.

Executed focused checks:

```powershell
PY -m pytest tests/unit/test_engine_router_contracts.py tests/unit/test_artifact_contracts.py tests/unit/test_extraction_engines.py tests/unit/test_processing_state.py tests/unit/test_document_ir.py tests/unit/test_ir_evidence.py -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/integration-contracts --junitxml=evaluation-output/audit-closure-20261024/integration-contracts.xml --tb=short
PY evaluation-output/audit-closure-20261024/run_services.py tests/integration/test_engine_ingestion.py tests/integration/test_extraction_artifacts.py tests/integration/test_extraction_routes.py -x -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/routing-services --junitxml=evaluation-output/audit-closure-20261024/routing-services.xml --tb=short
PY -m pytest tests/unit/test_ir_publication.py tests/unit/test_ir_evidence.py tests/unit/test_extraction_engines.py tests/unit/test_artifact_contracts.py -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/publication-final --junitxml=evaluation-output/audit-closure-20261024/publication-final.xml --tb=short
PY -m pytest tests/unit/test_ir_chunk_fidelity.py tests/unit/test_ir_evidence.py tests/unit/test_document_ir.py tests/unit/test_textblock_offsets.py tests/unit/test_ingestion.py -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/fidelity-green --junitxml=evaluation-output/audit-closure-20261024/fidelity-green.xml --tb=short
PY -m pytest tests/unit/test_ir_publication.py tests/unit/test_ir_chunk_fidelity.py tests/unit/test_artifact_contracts.py tests/unit/test_engine_router_contracts.py -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/fidelity-versioned --junitxml=evaluation-output/audit-closure-20261024/fidelity-versioned.xml --tb=short
PY -m pytest tests/unit/test_dataset_readiness.py tests/unit/test_corpus_v2.py tests/unit/test_readiness_partitions.py tests/unit/test_readiness_release.py tests/unit/test_readiness_evaluator.py tests/unit/test_readiness_continuation.py tests/unit/test_readiness_source_metrics.py tests/unit/test_readiness_scoring_fixes.py -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/readiness --junitxml=evaluation-output/audit-closure-20261024/readiness.xml --tb=short
PY -B -m tools.extraction_quality.dataset_readiness --manifest docs/eda/corpus_v1_manifest.csv --reference evaluation-output/extraction-v2-20261021/control-manifest-final.json --candidates docs/eda/extraction_corpus_v2_manifest.json --retrieval-gold local-evaluation/retrieval_gold_v1.jsonl --answer-gold local-evaluation/rag_gold_v1_approved.jsonl --output evaluation-output/audit-closure-20261024/isolation-v2.json
PY -m tools.extraction_quality.readiness_release verify --output evaluation-output/extraction-readiness-continuation-20261023-v2
PY -m ruff check src tests tools alembic
git diff --check
git diff --cached --check
git status --short
```

Results respectively: 104 unit passed; 19 routing real-service passed; 66 publication
unit passed; 147 fidelity unit passed; 52 versioned-contract unit passed; 167
readiness passed with one unavailable Windows symlink-privilege check skipped;
metadata CLI exit 0; frozen release integrity PASS/exit 0; repository Ruff PASS.
These runs overlap; their counts are not summed as unique tests.

Frozen release fingerprint remained
`f480f4fad5b46eaf037b67d7ca77db2e37f93f1aa0172405fd7f493d44489b55`.
Historical source/native references, originals and Gold remain protected. No
historical model benchmark or scoring campaign was rerun.

Final real-service command:

```powershell
PY evaluation-output/audit-closure-20261024/run_services.py tests/integration/test_ir_publication.py tests/integration/test_engine_search.py tests/integration/test_search_api.py tests/integration/test_bounded_worker.py tests/integration/test_extraction_artifacts.py tests/integration/test_engine_ingestion.py tests/integration/test_extraction_routes.py tests/integration/test_canonical_chunks.py tests/integration/test_processing_jobs.py tests/integration/test_worker.py tests/integration/test_production_indexing.py tests/integration/test_domain_migrations.py tests/integration/test_auth_membership_migrations.py tests/integration/test_authenticated_upload.py tests/integration/test_upload_storage.py -x -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/services-final --junitxml=evaluation-output/audit-closure-20261024/services-final.xml --tb=short
PY -m pytest tests/unit -q --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/unit-final --junitxml=evaluation-output/audit-closure-20261024/unit-final.xml --tb=short
```

Real-service result: **107 passed, zero skips**, 433.30 seconds, exit 0. Services
were new loopback-only containers labelled `codex.task=doclens-audit-closure-20261024`,
using cached postgres:16-alpine, doclens_ai-minio:latest and qdrant/qdrant:v1.15.4
images, temporary data and private fixture credentials. Tests create/drop only
UUID-named disposable databases and test-owned objects/collections. Original
containers were neither started nor changed. The ignored runner checks exact IDs,
labels and loopback bindings before use or cleanup. No real model/private corpus
or production service participates in these synthetic engineering tests.

The 107 passing cases include complete/incomplete extraction, failed reprocessing
preserving ACTIVE, partial Qdrant writes, atomic retry/cutover, membership denial
and revocation, stale-owner fencing, bounded-worker crashes/hangs/cancellation,
artifact scope/checksum/immutability/recovery, no-engine replay, canonical native
JSON replay and existing domain/job/index constraints. Migration fixtures execute
upgrade/check/downgrade/re-upgrade paths, including legacy unpinned rows and
0008/0009 compatibility; applied migration files remain unchanged.

The final legacy-publication increment was checked separately after the first
complete unit run (2247 passed, six skipped, 312.41 seconds). Three real-file wire
roundtrip cases were also added after that run had collected its tests; their
18-case fidelity file passed. Exact additional commands:

```powershell
PY -m pytest tests/unit/test_ir_chunk_fidelity.py -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/source-roundtrip --junitxml=evaluation-output/audit-closure-20261024/source-roundtrip.xml --tb=short
PY -m pytest tests/unit/test_processing_state.py tests/unit/test_indexing.py tests/unit/test_ingestion.py tests/unit/test_ir_publication.py tests/unit/test_ir_chunk_fidelity.py tests/unit/test_retrieval.py tests/unit/test_worker.py -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/legacy-unit --junitxml=evaluation-output/audit-closure-20261024/legacy-unit.xml --tb=short
PY evaluation-output/audit-closure-20261024/run_legacy_services.py tests/integration/test_legacy_ir_publication.py tests/integration/test_ir_publication.py tests/integration/test_engine_search.py tests/integration/test_production_indexing.py tests/integration/test_processing_jobs.py tests/integration/test_worker.py -x -q -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/legacy-services-final --junitxml=evaluation-output/audit-closure-20261024/legacy-services-final.xml --tb=short
PY -m pytest tests/unit -q --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/audit-closure-20261024/unit-current --junitxml=evaluation-output/audit-closure-20261024/unit-current.xml --tb=short
```

Affected units: **129 passed**, 7.07 seconds. Final affected real services:
**47 passed, zero skips**, 264.12 seconds. This second isolated phase used the label
`codex.task=doclens-audit-closure-20261024-legacy` and the same cached images, new
tmpfs data, separate exact container identities and a separate receipt. Both phases'
six service fixtures were removed only after ID/label checks; both filtered
inventories are empty, and all original exited containers were preserved.

Complete final-code unit result: **2253 passed, six skipped**, 309.92 seconds,
exit 0. Skips are two Windows symlink-privilege checks in test_data_quality_gate
and test_readiness_release, and four optional actual-browser paths in
test_pdf_assisted_review, test_pdf_grid_proposals, test_pdf_proposal_review and
test_pdf_review_visual. Node/Playwright/Edge inputs were unavailable. These checks
were not counted as passed; none concerns the changed publication/coverage logic.

Actual Linux resource checks ran serially after other resource workloads, using
an existing cached image, an unprivileged user, no network and read-only mounts:

```powershell
docker run --pull never --rm --network none --user 1000:1000 --mount 'type=bind,source=C:/Users/nurs/doclens_ai/src,target=/workspace/src,readonly' --mount 'type=bind,source=C:/Users/nurs/doclens_ai/tests,target=/workspace/tests,readonly' --mount 'type=bind,source=C:/Users/nurs/doclens_ai/.venv/Lib/site-packages,target=/host-deps,readonly' --workdir /workspace --env PYTHONPATH=/workspace/src:/workspace --env PYTHONDONTWRITEBYTECODE=1 --env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 --entrypoint python doclens-search-1791968383266-smoke-api:latest -c "import sys; sys.path.append('/host-deps'); import pytest; raise SystemExit(pytest.main(['tests/unit/test_bounded_engines.py','-q','--basetemp=/tmp/audit-closure-linux-resource','-p','no:cacheprovider']))"
```

**Nine passed**, 21.08 seconds, exit 0; exact stdout is retained in
`linux-resource.log`. The same nine actual Windows resource/process cases passed
in the complete unit run. These cover successful execution, timeout, crash,
memory/CPU/output limits, cancellation, backpressure, unavailable controls and GPU
rejection. No budgets or assertions were weakened. This is engineering resource
isolation evidence, not an OS security sandbox or parser/model quality evaluation.

Final repository-wide Ruff, selected-file/range formatting, Python execution, diff,
scope and sensitive-key checks passed. No applied migration changed. Private
JUnit and runtime receipts remain outside Git; no private datasets or generated
model/artifact files enter the commits.

```powershell
PY -m ruff format --check src/doclens_ai/chunking/ir.py src/doclens_ai/extraction/ir.py src/doclens_ai/extraction/ir_validation.py src/doclens_ai/extraction/reconciliation.py src/doclens_ai/extraction/engines.py src/doclens_ai/services/extraction_artifacts.py src/doclens_ai/services/processing.py src/doclens_ai/services/indexing.py tests/unit/test_engine_router_contracts.py tests/unit/test_artifact_contracts.py tests/unit/test_ir_publication.py tests/unit/test_ir_chunk_fidelity.py tests/unit/test_dataset_readiness.py tests/unit/test_processing_state.py tests/integration/test_engine_ingestion.py tests/integration/test_extraction_artifacts.py tests/integration/test_ir_publication.py tests/integration/test_legacy_ir_publication.py tools/extraction_quality/dataset_readiness.py
PY -m ruff format --check --range=824-854 src/doclens_ai/services/ingestion.py
```

Runtime receipt: Python 3.12.3, pytest 9.1.1, Ruff 0.17.0, Pydantic 2.14.0,
SQLAlchemy 2.1.4, asyncpg 0.32.0, pypdf 6.20.0, python-docx 1.2.0,
openpyxl 3.1.5 and lxml 6.1.3. Installed versions were inspected directly.

## Self-review and corrections

- Updated one existing artifact test that explicitly expected unsafe partial
  canonical publication. It now requires no canonical chunks and retained source
  diagnostics; all nine artifact tests passed after the correction.
- The first broader publication service run had 14 passes and that one stale
  expectation failure. Final service evidence supersedes this incomplete run.
- Retained historical route shapes instead of silently injecting current fields.
  Self-review found that no-engine artifact reprocessing also needed a current
  validator-version check; added rejection tests alongside old chunker pins.
- Serialized nested offset ranges as JSON-native lists so DB roundtrips preserve
  canonical replay equality. Tests assert exact JSON roundtrip identity.
- Added actual PDF/DOCX/XLSX source-to-IR-to-wire cases where earlier wire tests
  began from constructed extraction results. The complete fidelity file passed
  all 18 cases after this test-only addition.
- Final boundary review found that old persisted canonical subsets and candidates
  verified before rollout could bypass ingestion. Both cases were reproduced on
  real services; the shared prepare/cutover guard closes them without deleting
  historical rows. The initial cutover fixture tried inserting VERIFIED directly;
  corrected it to obey the actual candidate-to-verified DB transition before
  reproducing the bypass. No constraint or assertion was weakened.
- Corrected a new overlong test line and formatting/import findings before commits.
- Local sandbox prevented asyncio's Windows loopback self-pipe from starting.
  Stopped only this task's stalled test processes and reran with loopback access.
- Initial task-only MinIO tmpfs permissions prevented startup. Recreated only that
  failed fixture with writable tmpfs, then executed actual service tests.
- Fixed the reused router document's link to a consolidation report absent from
  the research baseline; it now points to this closure record.

## External blockers, Git and completion

Engineering acceptance is separate from quality/release acceptance. Independent
human Gold, publisher-specific permission clearance, independent family/Test
acceptance and approved QG thresholds remain external. Existing reviewer queue,
rights quarantines and owner decision package are preserved. QG-00 and QG-01 are
NOT_EVALUATED; independent TEST is TEST_NOT_READY. No production release or model
promotion is authorized. Broader deletion/restore production qualification remains
outside this corrective step; no complete operational lifecycle is claimed.

No performance optimization was made; before/after performance is not measured.
CI remote execution was not triggered because no push occurred. No type-checker
job is configured in pyproject.toml or the current CI; no new checker was installed.

Implementation commits on `codex/audit-closure-20261024`:

| Commit | Subject |
| --- | --- |
| `2ed4de3` | feat(extraction): integrate capability routing with research baseline |
| `e778d43` | fix(ingestion): require complete evidence before publication |
| `94d61e2` | fix(extraction): preserve atomic evidence and native offset maps |
| `d80d5fa` | fix(indexing): block publication of legacy IR subsets |
| `696841d` | feat(data): report declared coverage by connected family |

A sixth, separate Conventional Commit records this report and the updated router
contract. Its SHA is in the final chat/Git log. Each implementation commit contains
its relevant regressions, and all final code is covered by the final complete
unit run plus real-service and platform-specific checks described above.

Final worktree contains only the twelve pre-existing paths below; task changes are
committed. Main, research and consolidation branch refs retain their initial SHAs.
The final documentation commit's SHA is recorded in the final chat and Git log
rather than embedded into its own content.

```text
 M tools/kaggle_gpu/extraction_remote.py
?? .gitattributes
?? docs/eda/extraction_r1_20261023.md
?? docs/eda/extraction_r1_20261023_captures.json
?? docs/eda/extraction_r1_20261023_manifest.json
?? docs/eda/independent_engineering_audit_20261020.md
?? tests/unit/test_extraction_r1.py
?? tools/kaggle_gpu/extraction_r1.md
?? tools/kaggle_gpu/extraction_r1.py
?? tools/kaggle_gpu/extraction_r1_eval.py
?? tools/kaggle_gpu/extraction_r1_results.py
?? tools/kaggle_gpu/extraction_r1_text.py
```
