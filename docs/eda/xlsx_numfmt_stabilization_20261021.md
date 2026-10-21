# XLSX explicit number-format rejection: one stabilization correction

STATUS: **PASS for this scoped correction.** The full stabilization stage remains
incomplete. No release gate, independent quality qualification or production
authorization is implied.

## Scope, sources and initial state

2026-10-21; branch `main`, HEAD `540dbc8871ee004aff8d3704c706fe3d9c650143`.
Initial status contained only the pre-existing untracked
`docs/eda/independent_engineering_audit_20261020.md`; it is unchanged and unstaged.
No nested AGENTS.md applied to the affected code/tests/docs.

Read root instructions/source map, the relevant extraction/ingestion skills,
[Extraction Strategy](../../DocLens_AI_Extraction_Strategy.md#EX-XLSX),
[QG-01–03](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[ML-CHUNK](../../DocLens_AI_ML_Quality_Strategy.md#ML-CHUNK),
[fidelity protocol](extraction_fidelity_protocol_v1.md), current parser/scorer,
focused regressions, and the latest
[pipeline diagnostic](qg01_qg03_offline_diagnostic_20261021.md) and
[Office diagnostic](extraction_v2_report.md).
The prior diagnostic execution PASS was not quality PASS: six legacy XLSX failures
remained and the data-quality gate returned FIX.

Goal: reproduce one upstream XLSX implementation defect, correct it minimally,
verify unchanged inputs/Gold, and stop for review. No dependencies, models,
thresholds, frozen expectations or historical reports changed.

## Issue inventory and selected cause

| Priority/component | Evidence and reproducibility | Disposition |
| --- | --- | --- |
| P0 XLSX number formats | All six named legacy failures and ten additional locally available Office inputs reproduce rejection at `_extract_xlsx → _xlsx_number_formats`, before sheet extraction | Fixed incorrect ID lower bound; downstream validation still applies |
| P0 XLSX unsupported-sheet classification | After reaching later validation, two Office packages with three worksheet relationships and one dialogsheet relationship fail at the worksheet-only type check | Separate confirmed classification issue; retained, not fixed here |
| XLSX resource bounds | Two Office inputs reach `max_extracted_characters`; one already did so before this change, the other previously stopped at number formats | Intentional rejection under existing limits; not established as a defect |
| P0 PDF evidence/locators | Current legacy evaluation still has 11 missing required anchors and 24/24 failed PDF table-cell assertions; pypdf produces no verified table structure | Unresolved native capability/evidence gaps; no invented coordinates or replacement parser |
| P1 DOCX ancillary evaluation | Frozen `_located` explicitly cannot resolve ancillary regions; prior diagnostic identifies one present ancillary anchor affected by this limitation | Unsupported scorer mapping; real part identities cannot be equated with legacy part indices without review |
| P1 cleaning/chunking | Relevant character/offset/field regressions pass; all 84 unaffected legacy extraction/chunk metadata records are unchanged | No new downstream defect reproduced in this correction |
| P0 independent evidence | Legacy Gold has 19 attested reviewed records, not newly independent review; additional Office sources have no independent Gold | Comprehensive semantic/display/family qualification remains NOT_EVALUATED |

Available [c1-0040 alignment evidence](pdf_c1_0040_table_locator_alignment_v1.md)
distinguishes native cell fragmentation and unresolved table-index conventions
from normalization: that historical diagnostic did not justify a normalization
repair. The [five-PDF review packet](pdf_table_gold_review_packet_v1.md), including
c1-0033 and c1-0040, records unresolved independent adjudication. These are existing
evidence limitations, not new PDF measurements or permission to relabel Gold.

The selected bug was the guard `numFmtId < 164`. Every legacy failure contained
explicit number-format definitions below 164: IDs 5, 6, 42, 43 or 44. Their codes
differed from the installed built-in fallback; silently substituting the fallback
would lose stored format metadata. No duplicate format IDs were found in these
six packages.

Microsoft's [ISO/IEC 29500 NumberingFormat reference](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.numberingformat)
describes implicit formats and explicit codes, including IDs below 164.
[MS-OI29500 §2.1.712](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/17d11129-219b-4e2c-88db-45844d21e528)
describes format references under numFmts and locale-dependent code differences.
The parser's blanket rejection of this entire ID range was unjustified.

## Change and regression evidence

CHANGED:

- `src/doclens_ai/extraction/parsers.py`: reject negative explicit IDs instead of
  all IDs below 164; preserve the existing explicit-code-first lookup. Duplicate
  IDs, missing codes, invalid integers, invalid cell values, relationships,
  style bounds, XML guards, archive limits and character limits retain their checks.
- `tests/unit/test_xlsx_number_formats.py`: 16 synthetic public regressions for
  explicit IDs 0/5/6/14/23/42/43/44/163/164, raw precision, formula/cache/code/style
  preservation, real cell identity, immutable input SHA/size, and malformed formats.
- This sanitized report. Detailed captures/oracles remain ignored locally.

Before the parser edit, the new suite returned **9 failed, 7 passed**: all nine
IDs below 164 failed the public extraction boundary, while ID 164 and six malformed
rejection controls passed. After correction it returned **16 passed**.

| Legacy original | Before | After | Preserved observations |
| --- | --- | --- | --- |
| c1-0063 | corrupt_document | success | 1 sheet, 123 meaningful cells |
| c1-0067 | corrupt_document | needs_review | 1 sheet, 294 cells, 44 merges, 107 definitions / 110 caches |
| c1-0070 | corrupt_document | success | 2 sheets, 46 cells, 1 merge |
| c1-0081 | corrupt_document | needs_review | 12 sheets, 1,088 cells, 45 merges, 3 definitions / 3 caches |
| c1-0084 | corrupt_document | needs_review | 3 sheets, 120 cells, 2 merges |
| c1-0085 | corrupt_document | needs_review | 6 sheets, 5,541 cells, 216 merges, 511 definitions / 1,519 caches |

Four held legacy documents remain excluded from default chunking. Missing shared
formula definitions, drawings and spreadsheet error values remain explicit
warnings. Formula followers are not reconstructed and formulas are never executed.

All **90 legacy + 60 additional Office** immutable originals were checked against
their existing manifests before/after. Each evaluator ran twice before and twice
after the change. Each pair agrees on every non-runtime field; actual runtime
observations are retained. No failed/needs_review source was removed from a
denominator. The 90-source before fingerprint reproduces the latest diagnostic.

| XLSX cohort, 30 attempted each | Before success / review / failed | After success / review / failed |
| --- | --- | --- |
| Legacy | 13 / 11 / 6 | 15 / 15 / 0 |
| Additional Office | 9 / 10 / 11 | 11 / 15 / 4 |

All **84 unaffected legacy** document records, including extraction fingerprints
and chunking metadata, agree exactly before/after. All 49 previously nonfailed
Office results retain their full extraction fingerprints; no new source fails.
Overall 52/60 Office extraction fingerprints are unchanged: seven failures recover,
and one prior corrupt_document now reaches a later limit_exceeded rejection.
The remaining two corrupt_document results now stop at the dialogsheet boundary;
their failure-result fingerprints remain unchanged.

A separate local XML oracle inspected all **13 recovered originals** without using
parser output as expected data. It reconciled **19,376 meaningful cells, 71 sheets,
5,655 formula elements/caches, 1,149 local formula definitions and 595 merges**.
It checked exact raw/value/formula/cache/type/format/style/formula-attribute tuples,
cell identities, sheet identity/state and merged ranges. Phonetic annotations do
not become cell text. This is structural byte-to-output verification, not new
human review, calculation correctness or rendered display qualification.

The unchanged reviewed records for c1-0067/c1-0081 pass respectively 5/5 and 6/6
anchors/cells, 1/1 order, 2/2 relationships, 8/8 and 9/9 provenance, and 3/3 each
stored value/formula/cache assertions. They retain needs_review status.

| Frozen 19-record metric | Before passed / expected | After passed / expected |
| --- | --- | --- |
| Required text | 104/126 | 115/126 |
| Partial order | 41/58 | 43/58 |
| Cells/spans | 17/52 | 28/52 |
| Relationships | 9/33 | 13/33 |
| Provenance | 86/139 | 103/139 |
| Stored values; formulas; caches (each) | 7/13 | 13/13 |

Gold byte SHA remains
`f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf`;
normalized Gold fingerprint, evaluator, Gold contract, cleaner/chunker and manifests
are unchanged. Display fidelity remains NOT_EVALUATED. These small labelled
denominators do not establish comprehensive XLSX correctness.

## Executed commands and results

Repository root, existing `.venv`. Private evidence base:
`evaluation-output/xlsx-numfmt-stabilization-20261021/`.

```powershell
# New synthetic suite before correction: 9 failed, 7 passed; after: 16 passed.
.venv/Scripts/python.exe -B -m pytest tests/unit/test_xlsx_number_formats.py -q --tb=short -p no:cacheprovider --basetemp=evaluation-output/xlsx-numfmt-stabilization-20261021/repro-tests
.venv/Scripts/python.exe -B -m pytest tests/unit/test_xlsx_number_formats.py -q --tb=short -p no:cacheprovider --basetemp=evaluation-output/xlsx-numfmt-stabilization-20261021/fixed-tests

# Each command exits 0; 90 attempted, 19 reviewed records, unchanged denominators.
.venv/Scripts/python.exe -B -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output-dir evaluation-output/xlsx-numfmt-stabilization-20261021/before-1
.venv/Scripts/python.exe -B -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output-dir evaluation-output/xlsx-numfmt-stabilization-20261021/before-2
.venv/Scripts/python.exe -B -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output-dir evaluation-output/xlsx-numfmt-stabilization-20261021/after-1
.venv/Scripts/python.exe -B -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output-dir evaluation-output/xlsx-numfmt-stabilization-20261021/after-2

$env:PYTHONPATH=(Get-Location).Path
# Each baseline command performs two passes, exits 0, reports deterministic equality.
.venv/Scripts/python.exe -B -m tools.extraction_quality.extraction_v2 baseline --manifest docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --output evaluation-output/xlsx-numfmt-stabilization-20261021/office-before-1
.venv/Scripts/python.exe -B -m tools.extraction_quality.extraction_v2 baseline --manifest docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --output evaluation-output/xlsx-numfmt-stabilization-20261021/office-after-1

# Local permissions: 314 passed, 1 skipped, exit 0.
.venv/Scripts/python.exe -B -m pytest tests/unit/test_xlsx_number_formats.py tests/unit/test_extraction.py tests/unit/test_evidence_regressions.py tests/unit/test_extraction_fidelity.py tests/unit/test_safe_cleaning.py tests/unit/test_textblock_offsets.py tests/unit/test_chunking.py tests/unit/test_data_quality_gate.py -q --tb=short --strict-config --strict-markers -o faulthandler_timeout=60 -p no:cacheprovider --basetemp=evaluation-output/xlsx-numfmt-stabilization-20261021/targeted-tests --junitxml=evaluation-output/xlsx-numfmt-stabilization-20261021/targeted-tests.xml
# After test formatting, local permissions: 92 passed, exit 0 (includes 16 repeated new cases).
.venv/Scripts/python.exe -B -m pytest tests/unit/test_xlsx_number_formats.py tests/unit/test_ingestion.py tests/unit/test_processing_state.py tests/unit/test_extraction_v2.py tests/unit/test_extraction_coverage_audit.py -q --tb=short --strict-config --strict-markers -o faulthandler_timeout=60 -p no:cacheprovider --basetemp=evaluation-output/xlsx-numfmt-stabilization-20261021/broader-tests --junitxml=evaluation-output/xlsx-numfmt-stabilization-20261021/broader-tests.xml

# Source oracle, frozen-file/Gold checks, repeats and unaffected-output comparisons: PASS, exit 0.
.venv/Scripts/python.exe -B evaluation-output/xlsx-numfmt-stabilization-20261021/verify.py
.venv/Scripts/ruff.exe check src tests tools alembic
.venv/Scripts/ruff.exe format --check tests/unit/test_xlsx_number_formats.py
.venv/Scripts/ruff.exe format --check --range=980-1005 src/doclens_ai/extraction/parsers.py
git diff --check
git diff --cached --stat
git status --short
```

The initial existing-suite sandbox command selected the same seven old files as
the targeted run, without the new file/JUnit/faulthandler options, and used
`--basetemp=evaluation-output/xlsx-numfmt-stabilization-20261021/existing-before-tests`.
It stalled after 54 cases at the existing asyncio ingestion test and was interrupted;
it is not a PASS or a completed baseline test suite. The repository already
[documents this Windows sandbox initialization issue](remediation_pass_20261021.md).
The complete local-permission rerun above passed. The single skip is the Windows
symlink-privilege test; no symlink qualification is claimed.

Ruff lint and final changed-file/range formatting checks pass. The initial new-test
format check requested formatting; Ruff formatted that file, and the 92-case run
then passed. Unrelated parser formatting was not changed.

Runtime samples remain in metrics JSON. Legacy XLSX first-pass P50/P95 was
15.898/1082.979 ms before and 24.964/1307.456 ms after. Office first-pass XLSX
P50/P95 was 1.625/4.953 s before and 1.781/6.109 s after; sampled peak tree RSS
was 310,738,944 / 311,562,240 bytes. Additional recovered work changes these
populations; local verification also overlapped other processes. These are not
controlled latency improvements/regressions or production SLOs. Office uses the
existing 60 s / 1 GiB isolated-worker controls; legacy direct extraction has no
hard RSS qualification. Python 3.12.3; pypdf 6.20.0, python-docx 1.2.0,
openpyxl 3.1.5, Pydantic 2.14.0, Windows. No service/GPU/model execution occurred.

## Remaining work and handoff

REMAINING: The two dialogsheet classification failures and two intentional size
limit rejections remain; additional Office semantic quality is NOT_EVALUATED.
The failed dialogsheet IDs are `e2-office-081ca479f8d7eebf` and
`e2-office-545836d5b9807326`. Limit IDs are `e2-office-51bd4fd25d37dd92`
and `e2-office-969193c6e25c5c79`. Limits were not raised.

Recommended next separate bugfix: reproduce and correct XLSX unsupported
dialogsheet classification, preserving worksheets and real identities only where
the existing trust contract permits; do not implement dialog UI interpretation or
call an unsupported part corruption without evidence. It is upstream of DOCX/PDF
scorer alignment and downstream cleaning. No follow-up implementation started.

Independent PDF table/ancillary review, displayed XLSX fidelity, full fact/semantic
coverage, family completeness and release thresholds remain unavailable or
NOT_EVALUATED. Real PostgreSQL/S3/Qdrant integration and production E2E were not
run: persistence, tenant/ACL, retries, deletion and publication code did not change.
No stage-completion or production-readiness claim is made.

COMMIT: Not created; user requires review first. Nothing staged.

GIT STATUS (final scoped files plus preserved pre-existing audit):

```text
 M src/doclens_ai/extraction/parsers.py
?? docs/eda/independent_engineering_audit_20261020.md
?? docs/eda/xlsx_numfmt_stabilization_20261021.md
?? tests/unit/test_xlsx_number_formats.py
```
