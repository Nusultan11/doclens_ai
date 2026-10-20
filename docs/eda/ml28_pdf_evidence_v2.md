# ML-28 — offline PDF evidence v2 and qualification workflow

20 October 2026. **STATUS: BLOCKED for full qualification.** The combined offline
implementation is ready for review. Automated implementation/regression checks
pass; independent human Gold, actual candidate engine execution, and service
qualification remain unavailable. No quality improvement, production readiness,
or promotion is claimed. No commit was created.

## Scope, starting evidence, and design

Starting branch `main`, HEAD `5c5a19270f9ab05b3eb79f54e6f5c774b49df7d0`.
The pre-existing untracked `docs/eda/independent_engineering_audit_20261020.md`
is preserved. There were no staged changes. No instructions, dependencies,
migrations, frozen RAW, legacy Gold, historical reports, production parser,
worker, ingestion service, or existing v1 chunker were modified.

Owners: [architecture](../../Doclens_AI-architecture.md),
[extraction](../../DocLens_AI_Extraction_Strategy.md),
[ML data/chunks/experiments](../../DocLens_AI_ML_Quality_Strategy.md),
[QG-00–03](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES).
Previous evidence was read from ML-20 coverage, ML-25 diagnosis, ML-26 synthetic
normalization, and [ML-27](pdf_table_gold_review_packet_v1.md). ML-27 prepared a
packet, with 0/5 independently completed reviews and 0/110 independently verified
assertions. That historical preparation PASS is not a fidelity PASS.

The production boundary remains extraction/chunking v1. New v2 modules are
offline imports only, with no persistence, worker routing, index publication,
DB migration, or production activation adapter. `production_authorized=false`
is a literal contract. The offline merge defaults to `enabled=False`.

## CHANGED — exact review scope

| New file | Purpose |
| --- | --- |
| `src/doclens_ai/extraction/evidence_v2.py` | Strict additive source, page, locator, cell/span, relationship, review, proposal and merge contracts; deterministic evidence identities; intact v1 snapshot |
| `src/doclens_ai/extraction/hybrid_pdf.py` | Disabled-by-default offline native-first merge; observed original page inventory checks; isolated candidate outcome handling |
| `src/doclens_ai/chunking/table_v2.py` | Reverified table evidence bundles, complete semantic dependency closure, bounded whole-bundle context diagnostic |
| `tools/extraction_quality/pdf_review_validation.py` | ML-27 worksheet validation, pending-decision coverage, discrepancy reporting, guarded reviewed v2 export |
| `tools/extraction_quality/table_comparison.py` | Three-arm normalized capture contract, local isolated runner protocol, frozen paired scoring, failures/full denominator, timing/resource reports |
| `tools/extraction_quality/native_table_runner.py` | Real isolated unmodified pypdf baseline |
| `tools/pdf_ocr_candidate/enrichment.py` | Page/region diagnostic OCR bridge, local language artifacts, literal overlap/numeric checks, independent OCR provenance |
| `tests/unit/test_ml28_evidence.py` | Synthetic schema, source isolation, merge, literal fidelity and chunk contracts |
| `tests/unit/test_ml28_review.py` | Synthetic completed and incomplete independent-review workflow contracts |
| `tests/unit/test_ml28_comparison.py` | Paired scoring, unknowns, pins, actual subprocess success/timeout/RSS/output/failure probes |
| `tests/unit/test_ml28_ocr.py` | OCR selection, local language availability, conflict/deduplication, page/region transform and failure contracts |
| `docs/eda/ml28_pdf_evidence_v2.md` | This sanitized implementation/evaluation report |

All examples and test review identities are explicitly synthetic. Codex has not
filled a real independent draft, impersonated a reviewer, or exported real Gold.

## Five requested areas

### 1. Independent Gold readiness

The validator reuses ML-27 `preflight`, frozen manifest/Gold SHA-256 identities,
all 90 RAW source size/hash checks, 19 legacy records, and the entire five-PDF
population. Real CLI validation additionally requires exactly 110 assertions and
19 legacy source scopes. Those scopes are not claimed to be 19 independently
observed physical table regions. Page MediaBox, CropBox and rotation are reread
from originals; permissions retain the existing manifest declarations, with a
separate explicit annotation-authorization attestation required from the reviewer.

The new reader accepts completed copies of `independent.json` and
`adjudication.json`; it does not mutate the packet. Requirements include:

- Reviewer identity/date, independent human kind, original-page inspection,
  no parser-output or pre-draft legacy exposure, prior-exposure description,
  viewer/version/render settings, annotation permission reference/attestation.
- Independently authored literal cells, page/bbox/coordinate basis, rows,
  columns, spans, roles, semantic relationships, visual evidence and explicit
  completion/uncertainty. Table bounds and page crops must contain the cells.
- All legacy assertion and region decisions retained with exact populations,
  dates, rationale, source evidence, mappings and corrections. Confirmed claims
  must match the independent annotation; revisions remain explicit.
- Disagreements/missing/extra assertions require resolution by a distinct
  human adjudicator, original-page inspection, resolution and date. Disputed
  evidence remains blocked. Conflicting family/split declarations block export.

Human identity/permissions are **supplied attestations**, not authenticated
signatures or a legal-rights determination. The signed draft fingerprint is a
content checksum, not proof of who signed or when the legacy file was opened.
Technical blinding and cryptographic reviewer identity are not established.
The validator cannot turn machine annotation into independent human evidence.

Worksheet extensions, without altering the ML-27 frozen templates:

```text
reviewer.kind = independent_human
reviewer.annotation_authorized = true
reviewer.annotation_permission_reference = human-supplied permission reference
state = REVIEWED
completion.all_pages_inspected = true
completion.all_tables_inventoried = true
completion.signed_review_fingerprint = draft_fingerprint(draft)
text_anchors = [{anchor_id, literal, locator:{page,bbox,coordinate_basis},
                 occurrence, category:text|numeric|sign|date|period|unit}]
order_pairs = [[independent_before_anchor_id, independent_after_anchor_id]]
adjudication.state = ADJUDICATED
decision.state = RESOLVED
anchor decision.independent_anchor_id = independent draft anchor ID
cell_span decision.independent_cell_ref = {table_id, cell_id}
relationship decision.independent_relation_ref = {table_id, index}
order decision.independent_order_index = index in independent order_pairs
```

The adjudication draft fingerprint must equal the signed independent snapshot.
For value cells, `value_unit_period_links` contains `[target_cell_id, kind]`
pairs matching the independently authored unit/period relationships. Semantic
relations point from value to header/unit/period; merged headers can chain.
Known merges require explicit complete merge decisions and source-linked spans;
ambiguous merges remain blocked. Multi-page table cells can carry `page_number`
and explicit per-page `source_regions`; continuation is never inferred.

Actual local validation: **5/5 originals, 34 pages, 46 anchors, 24 cell/spans,
20 relationships, 20 order pairs, 19 scopes; no exclusions.** All 129 decisions
remain pending. Export was refused with exit 2; no reviewed-Gold file was written.
QG-00/QG-01 remain NOT_EVALUATED.

### 2. Reproducible table-engine comparison

Three arms are always required: `pypdf`, `mineru_basic`, `pp_structure_v3`.
Every arm has the same document IDs/scopes, even on timeout, unavailable models,
worker failure or unknown output. Omitted/extra documents, scope mismatch and
inconsistent capture/proposal pins are rejected. No Gold is passed to runners.
Missing observations are `None`; an empty known table set is distinct from an
unknown table dimension. Repeated literal text without verified disambiguation
remains unknown. Scoring never requires a candidate to know reviewer-assigned IDs.

Measurements include exact required literals/anchors; numeric/sign/date/period/unit
categories when independently labelled; cells/spans and roles; row/column/header/
value/unit/period/merged relationships; source page/bbox; reading order; false
observations/duplicates; per-document deltas and baseline-present losses; status
counts; P50/P95, sampled process-tree RSS bytes and explicitly unknown GPU memory.
Critical measured native-anchor loss/new execution failure produces REJECT.
Other quality thresholds remain TBD; no automatic PROMOTE is implemented.

The generic engine runner protocol is:

```text
PINNED_PYTHON -B PINNED_LOCAL_RUNNER RAW_PATH OUTPUT_CAPTURE_JSON
```

The runner can read parent-authored `request.json` beside its output, containing
only Scope and Pin. It must emit a validated Capture. The parent checks executable
and runner hashes, model artifact hashes, version/config consistency, source
hash before/after, successful exit, bounds and valid output. Default diagnostic
caps: 60 seconds, 1 GiB sampled tree RSS, 16 MiB output, 20 ms sampling. These are
tool safety caps, not approved quality/resource release thresholds. Cold Python
startup, imports, extraction, serialization and sampling are included in wall time.

`--candidate-runners` accepts a private JSON mapping for the two candidate arms:

```text
{arm: {pin: {engine, package_version, config_sha256, code_sha256,
             model_revisions, model_artifacts, license_review_reference,
             dependencies_sha256},
       executable, executable_sha256, runner, model_files, runtime_ready}}
```

`runtime_ready` is an operator attestation that the complete local runtime/models
and license review exist and egress is blocked externally. Offline environment
variables do not create a network sandbox. Dependency/model labels in a supplied
Pin are declarations; independently verified loaded-model provenance still needs
a qualified SDK runner. The harness does not fabricate missing cell geometry or
convert generated HTML/Markdown into canonical evidence.

**Actual external availability:** MinerU and PaddleOCR are absent locally; no
candidate SDK execution/normalization adapter is claimed as verified. The working
fallback is the pinned local runner/capture protocol with synthetic contracts.
Actual SDK adapters, dependency locks, complete model revisions/hashes and loaded
artifact checks remain required before a real engine comparison.

Official sources inspected, with only public queries:

- [MinerU 4.0 release](https://github.com/opendatalab/MinerU/releases): Basic is a
  parsing tier; 3.x backend assumptions must not be copied into a 4.x runner.
- [MinerU SDK](https://github.com/opendatalab/MinerU/blob/master/docs/en/usage/sdk_api.md):
  current documentation exposes local `mineru.parser.parse` with a tier argument.
  Context7 documentation was consulted; commit-specific SDK pages were unavailable,
  so version-matched execution/API compatibility remains unverified.
- [MinerU release metadata](https://github.com/opendatalab/MinerU/blob/22f5abb681c2314feffb9353fdff919d52dd8369/pyproject.toml)
  declares `LicenseRef-MinerU-Open-Source-License` and broad runtime dependencies.
  The [license at that revision](https://github.com/opendatalab/MinerU/blob/22f5abb681c2314feffb9353fdff919d52dd8369/LICENSE.md)
  includes additional terms; no deployment/license approval is inferred.
- [PaddleOCR PP-StructureV3 documentation](https://paddlepaddle.github.io/PaddleOCR/v3.0.1/en/version3.x/pipeline_usage/PP-StructureV3.html)
  documents `PPStructureV3`, `predict` and local model directories. Omitted local
  model paths can initiate downloads, so default initialization was not executed.
  [Current repository license](https://github.com/PaddlePaddle/PaddleOCR/blob/main/LICENSE)
  is Apache-2.0; version-specific dependency/model license qualification remains open.

No unapproved packages or weights were downloaded, and no private source/Gold was
transferred. Intended library versions are not recorded as actually loaded models.

### 3. Hybrid native-first table adapter

The exact `ExtractionResult.to_dict()` snapshot and fingerprint remain separate
from proposals. Disabled/unavailable/failed/OOM/timeout/oversized/malformed
candidate observations cannot modify native literals, order, warnings or locators.
Accepted table structures require an exact match to independently supplied review,
including source scope, literal, page, bbox, grid/span, roles and relationships.
This is deliberately conservative; unknown identities/conflicts need review.
Duplicate table IDs invalidate all duplicate occurrences. Evidence IDs include
workspace, document/version, RAW hash, literal and actual locator; candidate/config
and review revisions stay attached. Original-page metadata is checked by
`hybrid_pdf`. Geometry detection/proximity alone never certifies a table.

No automatic handling guesses borderless grids, merged cells, rotated coordinates,
multi-page continuation, repeated-text associations or numeric/header links.
Reviewed source-bound structures can represent them; unsupported proposals remain
untrusted. The merge consumes a bounded capture; it never launches a model inside
the production worker. New accepted bundles still have no production publisher.

### 4. Selective OCR

OCR requests carry workspace/document/version/RAW, page or real region, observed
reason/reference and explicit languages. Missing-text-layer selection checks the
actual native page; sufficient native text is not selected for that trigger.
Other triggers require source-observation references, not Gold-based routing.
The frozen EN whole-page path is reused. RU/KK/mixed paths require pre-existing
`rus`/`kaz`/`eng` artifacts, whose hashes are retained. Region rendering supports
only verified unrotated MediaBox=CropBox transforms; other transforms remain unknown.

Existing command/RSS/disk/time/pixel/output guards are reused. Native and OCR
outputs remain separate. Exact overlap diagnostics preserve OCR literals; token
boundaries prevent a sign-changing substring from being called a duplicate.
Numbers, decimal separators and date/period components are compared literally;
conflicts remain needs_review. No OCR state can be `accepted`, and confidence
never supplies factual certification. Missing languages/models, page mismatch,
timeouts and limits are explicit. No real RU/KK/EN OCR fidelity was measured in
this task because the necessary independent page/region Gold is unavailable.

### 5. Schema v2 and table-aware chunks

V2 is additive and offline. There is no automatic migration to v1 consumers.
It preserves exact raw literals, unknown fields, real locators, spans, explicit
roles/relationships, warnings and parser/candidate/config/review revisions.
The lossless v1 snapshot is revalidated against its fingerprint at trust boundaries.

The new chunker rechecks every acceptance decision against reviewed evidence;
a forged accepted state or mismatched workspace/version cannot create a bundle.
Each value bundle includes its complete explicit semantic dependency closure:
row/column/merged headers, unit, period, table/section identity, literal values,
document version, original locators and exact evidence IDs. Oversized complete
evidence is reported and omitted instead of truncated. Markdown is not canonical.

Synthetic fixed-output diagnostic: a value bundle retains all five fixture cells
and four semantic relations. Whole-bundle context survival is 1/1 at a 1200-character
budget and 0/1 at a one-character budget. This is a contract fixture, not a measured
baseline improvement, RAG quality result or evidence of optimal chunk sizes.

## VERIFIED — executed commands and results

Python 3.12.3, pypdf 6.20.0, pydantic 2.14.0. The project environment lacks psutil;
verification reused psutil 7.1.0 and existing parser packages from the previously
created offline pdfplumber runtime through PYTHONPATH. No installation was made.
Exact package inventories are retained privately in each run's
`runtime-inventory.json`; imports do not certify actual model loading.

All commands below were executed from the repository root. `evaluation-output/`
is ignored and contains private captures; its contents must not be committed.

```powershell
$env:PYTHONPATH="src;.;evaluation-output/pdfplumber-table-v1-20261019/runtime/Lib/site-packages"
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --basetemp=evaluation-output/ml28-20261020/regression-final-2 tests/unit/test_ml28_evidence.py tests/unit/test_ml28_review.py tests/unit/test_ml28_comparison.py tests/unit/test_ml28_ocr.py tests/unit/test_extraction.py tests/unit/test_extraction_fidelity.py tests/unit/test_extraction_coverage_audit.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_pdf_table_candidate.py tests/unit/test_pdf_table_geometry.py tests/unit/test_pdf_filled_ruling_normalization.py tests/unit/test_pdfplumber_table_candidate.py tests/unit/test_pdf_ocr_candidate.py tests/unit/test_chunking.py tests/unit/test_worker.py tests/unit/test_ingestion.py tests/unit/test_processing_state.py --tb=short
# 451 passed in 21.29s; 109 new synthetic contracts + 342 existing tests; no skips/failures.

.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --basetemp=evaluation-output/ml28-20261020/integration-1 tests/integration/test_canonical_chunks.py tests/integration/test_worker.py tests/integration/test_document_readiness.py --tb=short
# 54 skipped in 2.33s: TEST_DATABASE_URL is not configured. No integration PASS.

.venv/Scripts/ruff.exe check src/doclens_ai/extraction/evidence_v2.py src/doclens_ai/extraction/hybrid_pdf.py src/doclens_ai/chunking/table_v2.py tools/extraction_quality/pdf_review_validation.py tools/extraction_quality/table_comparison.py tools/extraction_quality/native_table_runner.py tools/pdf_ocr_candidate/enrichment.py tests/unit/test_ml28*.py
# All checks passed.
.venv/Scripts/ruff.exe format --check src/doclens_ai/extraction/evidence_v2.py src/doclens_ai/extraction/hybrid_pdf.py src/doclens_ai/chunking/table_v2.py tools/extraction_quality/pdf_review_validation.py tools/extraction_quality/table_comparison.py tools/extraction_quality/native_table_runner.py tools/pdf_ocr_candidate/enrichment.py tests/unit/test_ml28*.py
# 11 files already formatted.

.venv/Scripts/python.exe -B evaluation-output/ml28-20261020/prepare_and_verify.py prepare
# 5 selected sources; input identity bc90863aca943c1dafb6bb181c550c80c61746fe136b70616aa533c36f50c562
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_review_validation --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --review-dir evaluation-output/pdf-table-gold-review-v1-20261019/packet-1/review --scopes evaluation-output/ml28-20261020/scopes.json --revision ml28-v2 --output evaluation-output/ml28-20261020/review-validation --export
# Exit 2: BLOCKED: independent review incomplete; no Gold exported.

.venv/Scripts/python.exe -B -m tools.extraction_quality.table_comparison --population evaluation-output/ml28-20261020/population.json --sources evaluation-output/ml28-20261020/sources.json --output evaluation-output/ml28-20261020/run-5
.venv/Scripts/python.exe -B -m tools.extraction_quality.table_comparison --population evaluation-output/ml28-20261020/population.json --sources evaluation-output/ml28-20261020/sources.json --output evaluation-output/ml28-20261020/run-6

git diff --check
git diff --cached --check
git diff --stat
git diff --cached --stat
git status --short
```

To recreate the preparation on another permitted local checkout, use the existing
`preflight(manifest, corpus, gold, Expected())` API. Construct one Scope per selected
record: workspace `offline-corpus-v1`, document `record.document_id`, version
`record.source_sha256`, RAW `record.source_sha256`. These are offline version
identities, not claims about production DB UUIDs. Write ignored `scopes.json`
(ID-to-Scope), `population.json` (`{"scopes":[Scope...]}`), and `sources.json`
(ID-to-local-RAW-path). The local preparation script implements exactly this and
checks the same frozen identity before/after. Runners do not receive legacy Gold.
New destinations must be fresh; replays must use new directories.

Earlier attempts are retained, not counted as successful final verification:

- Initial new evidence suite: 38 passed/1 failed because its v1 compatibility
  test used the wrong positional call signature; corrected to existing keyword API.
- First worksheet suite outside the workspace: 40 passed/20 fixture failures
  because the sandbox denied temporary `.git/config` writes. Workspace basetemp
  rerun passed 60/60.
- New combined suite: 106 passed/1 failed caught the sign-changing substring
  deduplication bug; fixed with token boundaries. The 107-test rerun passed.
- Sandbox broader regression/worker diagnostic runs were interrupted while
  Windows `asyncio` initialization blocked in `socketpair/accept`, before worker
  behavior ran. A separately invoked API-import test also failed when root
  fixtures were suppressed and DATABASE_URL was absent. No production code was
  changed to accommodate either environment issue. Normal root fixtures and
  approved local socket access produced 449/449, then final 451/451 after additions.
- A strengthened capture-consistency check changed one contamination probe's
  error category: 108 passed/1 failed. The probe now supplies a coherent wrong
  version in both capture/proposal; the parent rejects the source mismatch.
- Ruff formatting/import/unused-variable findings were corrected; final checks pass.

## Actual paired measurements and verdicts

The final paired captures use all five eligible PDFs; no human-reviewed v2 labels
were supplied. All native executions succeeded; both unavailable engine arms
retain the complete 5/5 unknown denominator. All quality scores/deltas are unknown,
not zero errors. GPU memory is unknown; no GPU candidate was run. Earlier run-1/2
and run-3/4 captures are retained; run-5/6 are the final-code captures. Timings are
local diagnostics, not workload SLO measurements or evidence of candidate speed.

Final execution observations (seconds; sampled maximum process-tree RSS in bytes):

| Opaque source | Run 5 wall | Run 5 RSS | Run 6 wall | Run 6 RSS |
| --- | ---: | ---: | ---: | ---: |
| c1-0033 | 1.234 | 69,767,168 | 1.359 | 69,804,032 |
| c1-0040 | 1.266 | 70,172,672 | 1.344 | 70,139,904 |
| c1-0045 | 3.234 | 82,231,296 | 3.750 | 82,219,008 |
| c1-0048 | 1.688 | 73,338,880 | 2.047 | 73,052,160 |
| c1-0049 | 1.906 | 73,007,104 | 2.187 | 72,630,272 |

Native P50/P95: run 5 **1.688/3.234 seconds**; run 6 **2.047/3.750 seconds**.
Both candidate arms: 0/5 runtime observations, 5/5 unknown; all latency/RSS/GPU
and quality metrics unknown. Native structured-table metrics are also unknown:
plain text is not converted into asserted cells.

Host observation: Windows 11 AMD64, AMD64 Family 25 Model 80 Stepping 0,
16 logical CPUs, physical RAM 16,541,597,696 bytes. The runner executes serially
(one arm/document process at a time); no model seed or GPU execution is applicable.
No idle-host isolation or production performance threshold is claimed.

Final run-5/run-6 non-runtime equality and current comparison-code pin: verified.
Both fingerprints:
`fa3170e0b3fa673b08690049dabcaf261a49210beb5e2eb2f16c1c6f29624b6c`.
Final frozen input identity:
`bc90863aca943c1dafb6bb181c550c80c61746fe136b70616aa533c36f50c562`.
All 90 RAW and legacy Gold identities remain unchanged. No reviewed export exists.
Final local audit commands:

```powershell
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_review_validation --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --review-dir evaluation-output/pdf-table-gold-review-v1-20261019/packet-1/review --scopes evaluation-output/ml28-20261020/scopes.json --revision ml28-v2 --output evaluation-output/ml28-20261020/review-validation-final --export
.venv/Scripts/python.exe -B evaluation-output/ml28-20261020/final_audit.py
```

The audit verifies final code hashes, paired deterministic fields, pending 129
decisions, no Gold export, unchanged frozen inputs and empty staging. Privacy
scan over the 12 task files: **0** full legacy anchor matches of length >=8,
**0** original source filename matches, **0** scanned credential/private-key
patterns. This is a bounded content/pattern check, not a universal DLP guarantee.
Private captures, inventories, scopes and diagnostic logs remain Git-ignored.

## REMAINING — gates and production boundary

| Decision | Verdict | Reason |
| --- | --- | --- |
| Automated implementation/regression | PASS | 451 executed unit/contract/regression tests |
| Service integration | BLOCKED | 54 skips; TEST_DATABASE_URL absent |
| QG-00 | NOT_EVALUATED | Independent review/permissions/family coverage qualification incomplete |
| QG-01 | NOT_EVALUATED | No independent v2 Gold or actual candidate/model comparison |
| QG-02 | NOT_EVALUATED for real-source qualification | Literal preservation tested synthetically; no new independently qualified cleaning evaluation |
| QG-03 | NOT_EVALUATED for real-source qualification | Complete synthetic bundles; no reviewed real extraction/chunk Gold |
| Engine/chunk experiment | INCONCLUSIVE | Missing independent labels, engines and approved thresholds |
| Production activation | BLOCKED / false | Gold/fidelity/resource/ACL/integration/rollout gates not demonstrated |

No known failing in-scope automated test remains. Resource guards are sampled and
are not hard OS memory/egress isolation; hostile-parser sandboxing and descendant
cleanup under every adversarial process lifecycle are not qualified. OCR selection
references and reviewer identity require trustworthy human/operational inputs.
Model revisions and dependency/license qualification for MinerU/Paddle remain open.
RU/KK/mixed real OCR accuracy, broad rotated/cropped region support, independent
cell/order/semantic evidence, real ACL/revocation/service tests, persistence/index
integration, rollout/rollback and Answer Gold are still required. No RAG answer
quality gain is claimed. Stop at this combined review step.

## Git review

COMMIT: Not created; user explicitly requested review before any commit.
Staged diff inspection: empty. Existing tracked production files have no diff.
`git diff --stat` and `git diff --cached --stat` are empty because this change is
entirely new, untracked files. The 12-file review scope above excludes the user's
pre-existing untracked audit. No `git add` or intent-to-add was used.

For untracked-file review, the audit additionally executes
`git -c core.autocrlf=false diff --no-index --numstat -- NUL <each-task-file>` and
the corresponding `--check`; exit 1 denotes the expected added-file diff, and
all whitespace checks have no findings. Code/tests total 3,435 added lines;
the report is additional. No tracked file has changed.

GIT STATUS — exact final `git status --short`:

```text
?? docs/eda/independent_engineering_audit_20261020.md
?? docs/eda/ml28_pdf_evidence_v2.md
?? src/doclens_ai/chunking/table_v2.py
?? src/doclens_ai/extraction/evidence_v2.py
?? src/doclens_ai/extraction/hybrid_pdf.py
?? tests/unit/test_ml28_comparison.py
?? tests/unit/test_ml28_evidence.py
?? tests/unit/test_ml28_ocr.py
?? tests/unit/test_ml28_review.py
?? tools/extraction_quality/native_table_runner.py
?? tools/extraction_quality/pdf_review_validation.py
?? tools/extraction_quality/table_comparison.py
?? tools/pdf_ocr_candidate/enrichment.py
```
