# Repository remediation pass — 21 October 2026

Engineering execution: **PASS** for the fixes and available checks below. This is
not QG-00…QG-09 qualification, experimental promotion, or production authorization.
Started on `main` at `670b59d2160c6a6c70ca192a19f15b917d9bdbfd`. The existing untracked
`independent_engineering_audit_20261020.md` was preserved and excluded from staging.
The authorized Git action is one Conventional Commit, without a push.

## Sources and scope

The [source map](../../README_SOURCE_MAP.md),
[quality gates](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[ML data/experiment contracts](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA),
[native extraction contract](../../DocLens_AI_Extraction_Strategy.md#EX-ARCH), and
[architecture](../../Doclens_AI-architecture.md#ARCH-STATUS) govern this pass.
Only the root AGENTS.md applies; no nested AGENTS.md was found. The data-quality,
extraction and ingestion procedures were applied. No new model experiment,
acquisition, migration, infrastructure, or parser promotion was needed.

The previous [Corpus v2 report](extraction_v2_report.md) records a bounded engineering
PASS with external evaluation prerequisites still BLOCKED. The latest
[ICDAR qualification](icdar2013_eligibility_report.md) records zero admitted pairs.
Both are historical evidence, rather than current-HEAD quality acceptance.

## Reproduced defects and corrections

| Defect | Reproduction and smallest correction | Files |
| --- | --- | --- |
| Family exposure could disappear behind rejection/unavailability | A rejected, unavailable or excluded exposed family member left an admitted sibling eligible for sealed test. Exposure now follows the complete transitive family component, independently of admission. A contaminated test row is ineligible and QG-00 is FAIL. | `src/doclens_ai/eda/corpus_v2.py`, `tests/unit/test_corpus_v2.py` |
| Annotation hashes could authenticate invalid JSON as eligible | Hash-matched non-JSON, duplicate keys, NaN and overflowing float literals all remained eligible. JSON assets now pass the bounded JSON reader; duplicate/nonfinite numbers are rejected. JSON validity still does not establish semantic annotation correctness. | Same files |
| Publisher topology validation expanded untrusted integer ranges | A two-element row/column list with an extreme gap raised OverflowError; smaller gaps could allocate huge lists. Contiguity now checks only the bounded input elements without expanding the numeric range. Existing empty-cell/span/literal behavior remains tested. | `src/doclens_ai/eda/dataset_adapters_v2.py`, `tests/unit/test_dataset_adapters_v2.py` |
| Known source-integrity FAIL became NOT_EVALUATED in native reports | Changed bytes correctly failed the integrity audit, but both repeated reports and the consolidated quality result lost that failure. The runner now propagates the audit FAIL; execution remains separately BLOCKED. | `tools/extraction_quality/extraction_v2.py`, `tests/unit/test_extraction_v2.py` |
| Pilot records could receive legacy Gold through a record-ID collision | A pilot record sharing a control ID was counted/scored as a second legacy-labelled document. Labels now require the legacy-control cohort. Ambiguous duplicate legacy identities, including unavailable records without original bytes, are rejected before capture instead of overwriting a dictionary entry. | Same files |
| Orphan DOCX vertical continuations silently discarded facts | A synthetic second cell containing a different value was replaced by the cell above and returned success. Original OOXML merge chains and matching spans are now validated before python-docx resolves continuations. Malformed inputs fail without partial blocks. | `src/doclens_ai/extraction/parsers.py`, `tests/unit/test_evidence_regressions.py` |
| DOCX grid expansion preceded its resource budget | `row.cells` expanded declared spans before the limit check, including through header/footer presence probes. Raw spans are now checked first. Presence probes traverse source paragraphs without expanding table grids. | Same files |

Eighteen added parameterized regression cases cover these corrections. The first
13 failed against the pre-fix implementation; follow-up probes reproduced the two
header/footer bypasses and three legacy-label collision cases. All now pass, alongside
existing positive merge/locator, malformed-input, formula/cache, evidence-preserving
chunk and supported-ingestion regressions.

No frozen RAW, Gold, manifest/schema, experiment output, historical denominator,
license, review attestation or quality threshold was changed. Native parser code
changes intentionally change the existing implementation-hash processing fingerprint.
Older queued configurations therefore retain the documented fail-closed
`configuration_mismatch` behavior; existing published runs/chunks are not rewritten.

## Existing implementation and unresolved dependencies

The current code already fixes several older audit findings: DOCX omitted-grid
columns, encoding-independent XML DTD rejection, malformed XLSX shared-string and
boolean/numeric rejection, PDF ingestion review holds, parser implementation hashes,
and oversized table-chunk publication holds. Relevant regression tests passed;
these were not reimplemented.

Inspection of upload identity, lease/fencing, embedding identity, vector verification,
ACTIVE cutover, retrieval scope and packed-source revalidation found no additional
reproduced defect requiring a downstream change in this pass. Their available
unit/API contracts passed. Real-service persistence/concurrency behavior was not
requalified: service-backed tests skipped for explicit missing configuration.

| Gate | Current evidence and remaining boundary |
| --- | --- |
| QG-00 | Byte/manifest checks pass for 60 pilot files and 90 controls. Zero independent Gold records; family completeness and language coverage remain NOT_EVALUATED. External original-document/annotation rights and independent review remain blockers. ICDAR has zero acquired/admitted pairs and three desired coverage slots. |
| QG-01 | The scoped synthetic DOCX corruption/resource defects are fixed. Independent real PDF table cells/spans/header-value relations, reading order and source-coordinate fidelity remain NOT_EVALUATED. Existing rejected Docling/vector-grid/pdfplumber configurations stay rejected; OCR remains inconclusive in its recorded scope. |
| QG-02/03 | Existing preservation/offset/header and oversized-evidence regressions pass. Broad independently reviewed cleaning/chunk quality remains NOT_EVALUATED. |
| QG-04/05 | Fingerprint, vector validation and publication unit contracts pass. No real model inference, PostgreSQL/Qdrant cutover, crash/concurrency or rebuild qualification was performed. |
| QG-06/07 | Available authorization, source revalidation and packing contracts pass. Real-service revocation/freshness/context-survival quality remains unqualified; the final-check/delivery race remains documented. |
| QG-08 | Exact quote/offset/citation coverage is structural validation, not semantic entailment. Historical unsafe accepted/rejected generator configurations remain FAIL in their tested scope; broader independent answer/refusal quality remains NOT_EVALUATED. No speculative semantic heuristic or model was added. |
| QG-09 | Delete/tombstone, full reindex/rebuild/reconciliation, hard parser containment, enabled-dependency readiness, restore, load/fault drills and release authorization remain TARGET or missing qualification evidence. |

None of these incomplete gates is claimed PASS. Schema validity, corpus eligibility,
synthetic fixtures and successful test execution do not replace independent review.

## Verification

The failing regression probes were executed before their corresponding fixes:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_corpus_v2.py tests/unit/test_dataset_adapters_v2.py tests/unit/test_extraction_v2.py tests/unit/test_evidence_regressions.py -q -k 'exposed_family_member or annotation_json_is_validated or sparse_extreme_topology or known_integrity_failure or orphan_vertical or grid_span_budget' --basetemp=evaluation-output/remediation-20261021-failing --junitxml=evaluation-output/remediation-20261021-failing.xml
# 13 failed, 140 deselected
.venv/Scripts/python.exe -m pytest tests/unit/test_evidence_regressions.py tests/unit/test_extraction_v2.py -q -k 'grid_span_budget or pilot_record_id_collision or ambiguous_legacy' --basetemp=evaluation-output/remediation-20261021-second-reproduce --junitxml=evaluation-output/remediation-20261021-second-reproduce.xml
# 2 failed (header/footer), 1 passed, 85 deselected; legacy probes were added next
.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_v2.py -q -k 'pilot_record_id_collision or ambiguous_legacy' --basetemp=evaluation-output/remediation-20261021-labels-reproduce --junitxml=evaluation-output/remediation-20261021-labels-reproduce.xml
# 2 failed, 33 deselected
.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_v2.py -q -k ambiguous_legacy --basetemp=evaluation-output/remediation-20261021-unavailable-reproduce
# 1 failed (unavailable duplicate), 1 passed, 34 deselected
```

Commands ran in the existing `.venv` (Python 3.12.3). For pytest, the repository
root was set as `PYTHONPATH`; `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` were set
for the broad runs. The directories below were fresh task-owned ignored scratch.

```powershell
$env:PYTHONPATH = (Get-Location).Path
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
.venv/Scripts/python.exe -m pytest tests/unit/test_corpus_v2.py tests/unit/test_dataset_adapters_v2.py tests/unit/test_extraction_v2.py tests/unit/test_evidence_regressions.py tests/unit/test_extraction.py tests/unit/test_extraction_fidelity.py tests/unit/test_chunking.py tests/unit/test_ingestion.py -q --strict-config --strict-markers --basetemp=evaluation-output/remediation-20261021-accepted-targeted --junitxml=evaluation-output/remediation-20261021-accepted-targeted.xml
# 225 passed in 10.32s
.venv/Scripts/python.exe -m pytest -q --strict-config --strict-markers -o faulthandler_timeout=60 --basetemp=evaluation-output/remediation-20261021-accepted-full --junitxml=evaluation-output/remediation-20261021-accepted-full.xml
# 1622 passed, 157 skipped in 179.17s; no failed tests
.venv/Scripts/python.exe -m ruff check src tests tools alembic
# All checks passed
.venv/Scripts/python.exe -m ruff format --check src/doclens_ai/eda/corpus_v2.py src/doclens_ai/eda/dataset_adapters_v2.py tools/extraction_quality/extraction_v2.py tests/unit/test_corpus_v2.py tests/unit/test_dataset_adapters_v2.py tests/unit/test_extraction_v2.py tests/unit/test_evidence_regressions.py
# 7 files already formatted
.venv/Scripts/python.exe -m ruff format --check --range=440-500 src/doclens_ai/extraction/parsers.py
.venv/Scripts/python.exe -m ruff format --check --range=1270-1290 src/doclens_ai/extraction/parsers.py
# Both changed parser ranges already formatted
git diff --check
# No whitespace errors
```

The full-file parser format probe also found existing unrelated formatting
differences. A read-only `git show HEAD:src/doclens_ai/extraction/parsers.py` piped
to Ruff's stdin format check likewise exited 1. Those unrelated lines were left
unchanged; formatting checks above cover all edits.

The initial broad/focused sandbox runs stalled in Windows `socket.socketpair`
while creating an asyncio event loop, before ingestion logic. Timed stack traces
identified that boundary; stalled runs were interrupted and are not counted as
passing. Rerunning with local permissions completed. An intermediate unit run
passed 1584 tests with four skips before the final five parameterized cases were
added; the final full run above supersedes it.

The 157 final skips include unconfigured PostgreSQL/S3/Qdrant integration tests,
explicitly opted-out private/GPU capture replays, three browser tests lacking
`ML30_NODE`/`ML30_NODE_MODULES`, and one Windows symlink-privilege test. Read-only
`docker ps --format '{{.Names}} {{.Status}}'` succeeded with local permissions and
returned no running containers. No service was started or shared database modified.
No static type-check command is configured in pyproject/CI; none was invented.

Read-only corpus/report checks also executed:

```powershell
.venv/Scripts/python.exe -m tools.extraction_quality.extraction_v2 validate --manifest docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --output evaluation-output/remediation-20261021-office-validation.json
.venv/Scripts/python.exe -m tools.extraction_quality.extraction_v2 validate --manifest evaluation-output/extraction-v2-20261021/control-manifest-final.json --root local-corpus --output evaluation-output/remediation-20261021-control-validation.json
.venv/Scripts/python.exe -m tools.extraction_quality.extraction_v2 verify-results --results docs/eda/extraction_v2_results.json --csv docs/eda/extraction_v2_results.csv
```

Both manifest audits returned execution PASS: respectively 60/60 and 90/90
admitted/native-eligible, zero detected split leakage, zero independent Gold,
QG-00 and family completeness NOT_EVALUATED. JSON/CSV reconciliation passed for
150 recorded documents with unchanged consolidated fingerprint
`6d7cf294a2575d4f998a140dddd2d59e19d62bbcc7648b94da919c830243a0c7`.
The ICDAR extension loaded through the strict Corpus model: zero samples,
three desired slots. This does not change its BLOCKED qualification decision.

The final diff/staged scope and Git status were inspected; seven document links
and explicit anchors validated. The only intentionally remaining worktree item is
the pre-existing untracked audit report. No push or subsequent experiment is part
of this pass.
