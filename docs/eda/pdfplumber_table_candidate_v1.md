# ML-24 offline pdfplumber table comparator v1

2026-10-19. Continuation execution **PASS**, candidate **REJECT** for the tested
configuration. Production authorization **false**; QG-01 remains unqualified.
Sections before Continuation describe the initial BLOCKED attempt only. They are
historical, retained without rewriting results; final metrics follow.

## Initial BLOCKED attempt (before provisioning)

Execution was BLOCKED at dependency preflight; candidate quality was
INCONCLUSIVE / NOT_EVALUATED. No candidate implementation, simulated output,
new extraction or paired inference was performed in that attempt. Its original
report is preserved privately as previous-blocked-report.md.

## Scope and verified starting point

Branch main; HEAD `b76f494250e08851a0ebf78d1c020713fdcec2a3`, the completed ML-23
commit. Initial `git status --short --untracked-files=all` was empty. No nested
AGENTS.md was found under src/tools/tests/docs. Read the relevant root instructions,
source map, extraction/experiment skills, EX-PDF/EX-EXPERIMENT, QG-00/QG-01,
ML-23 protocol and existing parser/result/Gold/scoring contracts.

Verified the same five reviewed table PDFs without filtering by candidate results:
c1-0033, c1-0040, c1-0045, c1-0048, c1-0049. All 90 original SHA/size/format
identities and all 19 strict reviewed Gold records pass existing validation.
License/provenance fields are present for all 90 manifest entries; this preserves
the recorded legal basis, not a new legal review. The 39-entry ML-23 terminal
manifest reconciles unchanged. Both completed ML-23 capture sets (run-1/run-3)
remain intact and their baseline results independently rescore identically under
the unchanged scorer. This is capture replay, not fresh extraction.

| Frozen identity | SHA-256 / canonical fingerprint |
| --- | --- |
| Corpus manifest | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Reviewed Gold | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Source map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |

| Metric | Frozen pypdf baseline | ML-24 pdfplumber |
| --- | --- | --- |
| Required text | 46/46 | NOT_EVALUATED |
| Provenance | 22/46 | NOT_EVALUATED |
| Reading order | 13/20 | NOT_EVALUATED |
| Reviewed cells | 0/24 | NOT_EVALUATED |
| Reviewed row/column relationships | 0/20 | NOT_EVALUATED |
| Digit-bearing anchor presence | 13/13 | NOT_EVALUATED |
| Status: success / needs_review / failed | 5 / 0 / 0 | UNKNOWN |

Five documents are planned; zero candidate documents attempted. Their 46 text/
provenance, 20 order, 24 cell, 20 relationship and 13 numeric-presence labels remain
the planned denominators. No missing candidate observation is counted as a wrong
cell, successful extraction or preserved fact. Numeric presence is not exhaustive
numeric fidelity. Semantic header roles are NOT_EVALUATED.

## Blocking prerequisite and actual checks

Python 3.12.3 is available. Both `pdfplumber` and its `pdfminer` import are absent
in the existing isolated docling-v1-runtime, production .venv and system Python.
There is no installed pdfplumber version, installed license file or loaded package
hash to verify. No installation, network package download, environment modification
or production dependency change was attempted. The user explicitly requires
BLOCKED when the dependency is unavailable.

The official upstream [pdfplumber license](https://raw.githubusercontent.com/jsvine/pdfplumber/stable/LICENSE.txt)
is MIT. That upstream file does not establish an installed/pinned artifact license
or runtime identity. Official [pdfplumber documentation](https://github.com/jsvine/pdfplumber/blob/stable/README.md)
describes its pdfminer.six basis, character geometry and detected table cell/bbox
interfaces. Consulted via Context7 /jsvine/pdfplumber; no private data was sent.
These are feasibility references, not measurements or version-matched execution.

Actual dependency commands from the repository root:

```powershell
@'
import importlib.util,sys
print('runtime',sys.version.split()[0])
for name in ('pdfplumber','pdfminer','pypdf','psutil'):
 print(name,'AVAILABLE' if importlib.util.find_spec(name) else 'UNAVAILABLE')
'@ | evaluation-output/docling-v1-runtime/Scripts/python.exe -B -
@'
import importlib.util,sys
print('production_runtime',sys.version.split()[0])
for name in ('pdfplumber','pdfminer'):
 print(name,'AVAILABLE' if importlib.util.find_spec(name) else 'UNAVAILABLE')
'@ | .venv/Scripts/python.exe -B -
@'
import importlib.util,sys
print('system_runtime',sys.version.split()[0])
for name in ('pdfplumber','pdfminer'):
 print(name,'AVAILABLE' if importlib.util.find_spec(name) else 'UNAVAILABLE')
'@ | python -B -
```

Each interpreter reports Python 3.12.3, pdfplumber UNAVAILABLE, pdfminer UNAVAILABLE.
The R&D interpreter additionally reports pypdf AVAILABLE and psutil AVAILABLE.
`py -0p` printed `No installed Pythons found!`; direct interpreter checks above
worked. The launcher inventory is not mistaken for an unavailable Python runtime.

Read-only integrity/replay was executed as Python stdin using existing ML-23
helpers, verify_corpus, load_gold, score_record and restore, with the current
source/.venv/root PYTHONPATH. Actual exit-0 output included:

```text
PASS HEAD=b76f494250e08851a0ebf78d1c020713fdcec2a3
PASS originals=90 reviewed_Gold=19 licenses_present=90 ML23_artifacts=39
COHORT c1-0033,c1-0040,c1-0045,c1-0048,c1-0049
BASELINE_STATUS success=5 needs_review=0 failed=0 numeric_presence=13/13
```

The same command printed exact matching frozen fingerprints and aggregate baseline
counts shown above, and asserted equality of both historical quality dictionaries.

## Work not executed and unblock condition

NOT_RUN: pdfplumber source-only vector/character/image-region feasibility inspection,
configuration freeze, candidate construction, synthetic regressions, two paired
runs, timing/RSS/worker cleanup measurements and candidate Ruff/format checks.
Their results are unavailable, not inherited from ML-23. No new source classification,
character coordinates, image-only areas, geometry correctness or table recovery is
claimed. No settings were selected using Gold. Gold was used only for unchanged
historical baseline replay; no candidate has seen it as an extraction input.

Unblock with an available pinned pdfplumber distribution and compatible dependency
closure in an ignored isolated offline R&D environment, recording versions, package
SHA-256 and licenses. Select a concrete version only after compatibility/artifact
verification. Keep production dependencies unchanged. Then perform source-only
triage and freeze exactly one geometry/text-association configuration, resource
budgets and the user-specified cell-plus-relationship advancement gate before any
candidate scoring. No configuration or candidate-quality verdict is fabricated now.

In the initial attempt only this allowlisted report was created. The candidate/runner/test files were
not created as placeholders. No production, Gold, ML-23 capture or unrelated file
changes. No staging, commit or push: successful implementation and mandatory
verification, required for the authorized commit, have not occurred.

## Continuation: protocol frozen before real candidate scoring

Continuation started at the same HEAD with only the existing ML-24 report untracked;
its original bytes were preserved before updating it. No unrelated edits were present.

H1: pdfplumber's source geometry can recover reviewed table cells and same-row/
same-column relations missed by frozen native text, without losing native facts.
Retain all five PDF sources and all existing denominators. Exposed DEV only;
no blind/family-safe generalization claim, new Gold review, OCR or model inference.

Dependency provisioning is authorized only in the Git-ignored
evaluation-output/pdfplumber-table-v1-20261019/runtime. Existing caches were tried
first; the restricted network attempt failed DNS. Authorized elevated download
then used cached wheels except Pillow, pluggy and pypdfium2. All 25 wheels, 26
R&D distributions (including pip) and workspace project metadata are pinned by SHA-256.
The isolated environment has no production-site-packages access. pypdf 6.20.0,
pydantic 2.14.0, psutil 7.1.0 match the existing baseline; pdfplumber 0.11.9 pins
pdfminer.six 20251230. Existing DOCX/XLSX dependencies are copied by pinned package
installation only into this environment for shared scorer imports.

Source-only inspection before settings selection found 34 pages with native
characters, zero rotated/nonupright characters, zero invalid character bounds and
zero duplicate character/box identities. Two image regions on c1-0048 have no
overlapping native characters; this does not establish complete image semantics.

| Source | Pages | Characters | Lines | Rectangles | Images |
| --- | --- | --- | --- | --- | --- |
| c1-0033 | 1 | 945 | 0 | 185 | 0 |
| c1-0040 | 1 | 851 | 0 | 150 | 0 |
| c1-0045 | 7 | 29,268 | 0 | 7 | 0 |
| c1-0048 | 17 | 29,646 | 127 | 154 | 2 |
| c1-0049 | 8 | 23,286 | 0 | 439 | 0 |

One configuration: vertical/horizontal strategies lines (including rectangle
sides), snap/join/intersection tolerances 0, edge_min_length 3,
edge_min_length_prefilter 1. No text-inferred boundaries, gap completion, per-source
settings or Gold-derived indices. Resolved library defaults are frozen in full.
Text: layout false, x/y tolerance 3, expand_ligatures false. Only whitespace may be
inserted; the complete non-whitespace character sequence must equal the independently
ordered source-character sequence (geometric line clusters, then x coordinates).
Signed numbers, leading zeros and units receive literal synthetic regressions.

Only complete rectangular grids with at least two rows and columns are accepted.
Every cell boundary requires continuous original page edges at the exact coordinate;
every character requires full strict interior containment in exactly one cell.
Retain actual table/cell bboxes, page coordinate frame, original character indices
and boundary-edge indices in offline evidence. Reject overlapping tables, merged/
incomplete cells, overlapping duplicate text, rotated/unmapped characters and
unverified bounds as needs_review. Never deduplicate or substitute unknown text.
Page-local table identity ranks all detected tables by actual geometry, including
rejected ones. Normalized block index is the actual appended block ordinal.
No production SourceLocation field or semantic header role is invented. Supplemental
tables are a separate offline representation; native blocks/warnings stay verbatim.

Budgets: input 50 MiB, 100 pages, 500,000 characters/document, 5,000 edges/page,
100 detected tables/document, 10,000 cells/document, logical 15 seconds. Parent
isolated worker: 20 seconds, 512 MiB sampled tree RSS, 64 MiB output, 0.02-second
samples. Fatal errors discard incomplete geometry. Parsing/materialization precedes
some logical checks; sampling is a local R&D guard, not a hostile-input OS sandbox.

PROMOTE only for further offline evaluation with at least one additional strictly
correct reviewed cell AND relation, no native/text/numeric/provenance/order loss,
no fabricated geometry or unsafe/resource failures. REJECT critical regression or
complete measurement with no structural gain. INCONCLUSIVE for insufficient or
inconsistent evidence. Preserve/report all needs_review/failed outcomes and unknown
scores. Two fresh serial paired runs include native before, candidate, native after;
compare quality fields and raw captures without treating repetitions as new sources.
No tuning after real scores. QG-01/semantic headers/production remain separate.

Preregistration and the completed source-only triage precede all real candidate
scores. The historical BLOCKED report is never presented as successful inference.

### Safety correction and final freeze

Initial runs 1/2 completed with identical REJECT results and no structural gains.
Subsequent independent synthetic numeric-spacing review reproduced a safety defect:
geometric word spacing could split one source numeric literal into several tokens
while passing the non-whitespace sequence check. The targeted regression failed
before the fix. Added an explicit comparison of signed numeric tokens against
source-character line sequences; ambiguous splitting/merging now produces
needs_review without emitting that table. No table/text settings, reviewed labels,
thresholds or source-specific branches changed. This is a reproduced validation
fix, not tuning for the known real scores. Preserve runs 1/2 and their original
registration; final registration-v2 and two new runs use finalized code. The
synthetic correction does not establish general numeric fidelity.

## Final paired results and failure accounting

Final runs 3/4 use identical finalized code, settings, package fingerprints and
input bytes; all five raw captures and every deterministic quality field agree.
No responses or captures were repaired. Initial completed runs 1/2 remain separate
historical captures; their real-corpus quality counts were the same, but they
precede the reproduced numeric-safety fix. Four repetitions are not 20 independent
documents: the evaluated population is five exposed DEV PDFs.

Each B/C entry below is the identical baseline and candidate count, not their sum.

| Source | Text B/C | Provenance B/C | Order B/C | Cells B/C | Relations B/C | Numeric-bearing B/C |
| --- | --- | --- | --- | --- | --- | --- |
| c1-0033 | 9/9 | 1/9 | 0/3 | 0/8 | 0/8 | 0/0 N/E |
| c1-0040 | 8/8 | 4/8 | 2/3 | 0/4 | 0/4 | 1/1 |
| c1-0045 | 6/6 | 2/6 | 1/2 | 0/4 | 0/2 | 5/5 |
| c1-0048 | 11/11 | 8/11 | 6/6 | 0/3 | 0/1 | 3/3 |
| c1-0049 | 12/12 | 7/12 | 4/6 | 0/5 | 0/5 | 4/4 |
| Unique total | 46/46 | 22/46 | 13/20 | 0/24 | 0/20 | 13/13 |

All labels retain their original denominators, including needs_review documents.
Required anchors recovered: empty; newly lost: empty. Native blocks, duplicate
occurrence counts, warnings and original page provenance are preserved verbatim.
The 13/13 result measures unchanged reviewed digit-bearing anchor presence; it is
not exhaustive numeric, OCR or multilingual accuracy. No new numeric fact is
accepted from an unverified table. Real table spans, semantic header roles and
correctness of new cell locators are NOT_EVALUATED because no grid was accepted.

All five baseline statuses are success. All five candidate statuses are needs_review:
success 0, needs_review 5, failed 0; zero runtime-failed/unknown sources in either
final repetition. No review status is promoted to success. No production eligibility
or indexing decision was made. Table text/structure alone cannot establish readiness.

| Source | Native detected tables | Native cell boxes | Accepted tables/cells | Observed rejection |
| --- | --- | --- | --- | --- |
| c1-0033 | 0 | 0 | 0/0 | no supported table on 1 page |
| c1-0040 | 4 | 2,448 | 0/0 | merged_or_incomplete_grid on 1 page |
| c1-0045 | 0 | 0 | 0/0 | no supported table on 7 pages |
| c1-0048 | 2 | 36 | 0/0 | irregular grid, insufficient grid; 16 pages without supported tables; 2 image pages |
| c1-0049 | 0 | 0 | 0/0 | no supported table on 8 pages |

Native cell boxes are geometry proposals, not reviewed correct cells. Bounded
source-grid reconciliation under unchanged settings found c1-0040 proposed cell
counts 856/526/460/606 versus complete-boundary lattice counts 1672/722/646/798.
c1-0048 proposals have 33 boxes versus 150 lattice positions, and a three-cell
single-column structure. These fail the frozen complete-grid/minimum-size rules.
The diagnostic name does not prove that the original PDF has merged cells: parser
segmentation, thin rectangle borders or true layout complexity remain possible,
unresolved explanations. No candidate table index was replaced by a Gold index.
No strict score was weakened into text-only matching.
The second source-grid pass uses the same pinned pdfminer/pdfplumber geometry;
it checks source linkage and reproducibility, not independent visual ground truth.

The registered advancement gate is not met: zero cell AND relationship gains.
Candidate **REJECT**, limited to this configuration; the broader hypothesis and
other pdfplumber settings are not falsified or evaluated. Six native detections
do not establish six correct tables. Source-linked evidence and independent public
synthetic controls establish functioning code, not real-table quality or QG-01 PASS.
Do not promote this candidate or integrate it into production.

## Resources

| Source | Run 3 seconds / sampled tree RSS bytes | Run 4 seconds / sampled tree RSS bytes |
| --- | --- | --- |
| c1-0033 | 1.437 / 73,732,096 | 1.422 / 74,190,848 |
| c1-0040 | 1.797 / 70,356,992 | 1.797 / 71,262,208 |
| c1-0045 | 10.156 / 87,191,552 | 10.328 / 86,822,912 |
| c1-0048 | 3.281 / 79,511,552 | 3.234 / 79,728,640 |
| c1-0049 | 3.469 / 80,011,264 | 3.469 / 80,269,312 |

Run 3 P50/P95 3.281/10.156 seconds; run 4 3.234/10.328 seconds (nearest rank,
five documents each). Maxima 87,191,552 / 86,822,912 bytes; 930/934 RSS samples.
Timings include cold Python worker startup and native-before/candidate/native-after,
not separate baseline or table-only service latency. Serial local Windows AMD64,
Python 3.12.3, no GPU/models/OCR. Sampled RSS may miss short peaks; it is not a
continuous allocator high-water measurement. Both final runs have zero timeout,
memory/output-limit failures, no partial files, cleanup 10/10. Five additional
bounded read-only source-grid audits also completed within the same resource guards.
Source feasibility and geometry-audit timings are not pooled into benchmark latency.

## Final fingerprints and runtime provenance

| Item | SHA-256 / canonical fingerprint |
| --- | --- |
| Original BLOCKED report | `fcea345ab901de34cd1a45a1b31fb40715b3902534feafabaa43b8002fd1fc30` |
| Runtime packages/file/license manifest | `74f4a08ed7d153fd2a0bcbd01d016bff528625f99c7d73aa3d7bc068fdd56352` |
| 25-wheel manifest | `86f44b61cdb8db821095ca3455391cf585b079bb13ec3965fd0cbd3c7450256c` |
| Source-only triage | `83a3ed4b0b02840a6963f7cdd5d3c368b1db3cb37301f87219efafc49b1c1c76` |
| Final protocol snapshot | `bb36a74d430fcb977fcae2efafaec4d8950203c9036a0fd5136d861c2d87b6af` |
| Final registration file | `f9fcd5baa36fefe57996bbccc6fe7263dd6f9034669ba8dc15271a3348b9df40` |
| Final canonical registration | `2751b7f4269e44cadd8c0b0104f8069fb83d57c090d0fa9b1db5f82a54ccd56f` |
| Both final quality fingerprints | `a69ce6db008ee921182d2c9065483e2f4f0ffc9b6b64eb5e45cc19ce5b4d869e` |
| Candidate source | `c1b72bcb7ab7ea2a7ec7b5c4d7afec4e347726b8537ba94bb5afde1d99f8d3c3` |
| Runner source | `f07194a8e6f572eeb9c4e7caae8c971a95820bf0cf069e2c97e6ed2e169a1559` |
| Synthetic tests | `b7f8b4605a1830b3f41f197e52c6bba3765015ae42e4974dbe0f07efe5f8c5a6` |
| Run 3 manifest, 12 artifacts | `cef8a7e82982c18e301a9241d2dfd169efb76d379d016d1bf31376de8becdd17` |
| Run 4 manifest, 12 artifacts | `2acbba2164d912d96fc70b6f7e905925bdd0875230b278c4541d84804053c3c3` |

Core runtime: pdfplumber 0.11.9 (installed MIT license file), pdfminer.six 20251230
(MIT), pypdf 6.20.0 and psutil 7.1.0 (BSD-3-Clause); all installed license/notice
files and complete dependency versions are pinned, including Pillow 13.0.0,
pypdfium2 5.14.0, cryptography 50.0.2, charset-normalizer 3.5.2. The distribution
inventory has 27 visible entries: 26 installed R&D distributions plus workspace
doclens-ai metadata, not 27 installed runtime wheels. Imported pdfplumber/pdfminer
paths are verified under the isolated runtime. No production package was installed,
removed or upgraded. Modules, metadata and wheel hashes reconcile before/after.

## Actual completion commands and checks

PowerShell from repository root; ignored scratch paths contain no uploaded data.

```powershell
python -m pip cache list pdfplumber
python -m pip cache list pdfminer
python -m venv evaluation-output/pdfplumber-table-v1-20261019/runtime
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -m pip download --index-url https://pypi.org/simple --only-binary=:all: --dest evaluation-output/pdfplumber-table-v1-20261019/wheels pdfplumber==0.11.9 pypdf==6.20.0 psutil==7.1.0 pydantic==2.14.0 pytest==9.1.1
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -m pip install --no-index --find-links evaluation-output/pdfplumber-table-v1-20261019/wheels pdfplumber==0.11.9 pypdf==6.20.0 psutil==7.1.0 pydantic==2.14.0 pytest==9.1.1
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -m pip download --index-url https://pypi.org/simple --only-binary=:all: --dest evaluation-output/pdfplumber-table-v1-20261019/wheels python-docx==1.2.0 openpyxl==3.1.5 lxml==5.4.0 et-xmlfile==2.0.0
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -m pip install --no-index --find-links evaluation-output/pdfplumber-table-v1-20261019/wheels python-docx==1.2.0 openpyxl==3.1.5 lxml==5.4.0 et-xmlfile==2.0.0
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -m pip check
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdfplumber-table-v1-20261019/preflight.py
.venv/Scripts/ruff.exe check src/doclens_ai/extraction/pdfplumber_table_candidate.py tools/pdfplumber_table_candidate/benchmark.py tests/unit/test_pdfplumber_table_candidate.py
.venv/Scripts/ruff.exe format --check src/doclens_ai/extraction/pdfplumber_table_candidate.py tools/pdfplumber_table_candidate/benchmark.py tests/unit/test_pdfplumber_table_candidate.py
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B -m pytest -q --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/pdfplumber-table-v1-20261019/test-tmp-4 tests/unit/test_pdfplumber_table_candidate.py tests/unit/test_pdf_table_candidate.py tests/unit/test_extraction.py tests/unit/test_extraction_fidelity.py tests/unit/test_docling_candidate.py tests/unit/test_pdf_ocr_candidate.py
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B tools/pdfplumber_table_candidate/benchmark.py --preregister --output evaluation-output/pdfplumber-table-v1-20261019/registration-v2
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B tools/pdfplumber_table_candidate/benchmark.py --registration evaluation-output/pdfplumber-table-v1-20261019/registration-v2/registration.json --output evaluation-output/pdfplumber-table-v1-20261019/run-3
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B tools/pdfplumber_table_candidate/benchmark.py --registration evaluation-output/pdfplumber-table-v1-20261019/registration-v2/registration.json --output evaluation-output/pdfplumber-table-v1-20261019/run-4
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdfplumber-table-v1-20261019/verify.py
```

Actual results: pip check `No broken requirements found.`; Ruff `All checks passed!`;
format `3 files already formatted`; pytest **296 passed in 13.47s**, zero failed or
skipped (32 new candidate tests plus 264 existing extraction/candidate regressions).
The existing public synthetic PDFium test independently extracted all four literal
strings and rendered the fixture; this does not visually validate private tables.
Both final CLI runs printed status PASS, candidate REJECT, the final fingerprint
above and the complete 46/22/13/0/0 metric counts. Verifier exit 0:

```text
PASS originals=90 reviewed_Gold=19 ML23_artifacts=39 runtime_distributions=27 wheels=25
PASS final_replay=2x5 raw_captures=byte_identical text=46/46 provenance=22/46 order=13/20 cells=0/24 relations=0/20 numeric_presence=13/13
PASS native_blocks_warnings_duplicate_counts=verbatim lost=0 recovered=0 statuses=0_success,5_needs_review,0_failed
PASS resource_journals=10/10 cleanup=10/10 source_geometry_audits=5 frozen_settings_unchanged
```

Earlier failed/partial checks are disclosed: the sandboxed download failed DNS
(its provisional older test-tool pins were never installed); authorized cache/
network download then succeeded using the actual baseline tool versions. Initial
preflight import failed on missing docx; installed the baseline DOCX/XLSX dependency
closure solely in R&D, then preflight passed. Initial pytest collection failed on
the root DB conftest's SQLAlchemy import; isolated unit tests use confcutdir=tests/unit
to avoid unrelated DB fixtures/dependencies, with no tests deselected. Candidate
tests passed 26 initially, then the extended suite passed 295. The deliberately
added numeric-spacing regression failed 1/1 before the fix and is included in the
final 296 passing tests. Ruff import sorting and one long synthetic literal were
corrected before the relevant freezes. A metadata diagnostic used incorrect Pillow
key casing; corrected the scratch lookup, verified licenses/import isolation; no
runtime package or experimental result was changed by that diagnostic error.

## Remaining limits and next recommendation

Only the frozen conservative configuration was evaluated. No gain is established;
absence of accepted grids prevents a real-locator/header-role fidelity claim.
Do not interpret source character counts, native detections or synthetic passes as
reviewed table correctness. Family identities/generalization and all unreviewed
language/numeric/visual dimensions remain UNKNOWN/NOT_EVALUATED.

The smallest future investigation is independent source-geometry review of rectangle
border segmentation on public synthetic equivalents, before separately preregistering
any broader grid policy. Do not tune tolerances on these exposed Gold answers,
remap reviewed table indices, repair Gold or integrate this comparator in production.
All RAW, Gold, production/scoring modules, previous captures and tracked dependency manifests
remain unchanged; only the four authorized ML-24 files enter the completion commit.

Final scope/privacy checks: only four allowed additions; no tracked production or
dependency-manifest changes. The ignored privacy verifier checks UTF-8/LF, no private
filenames, Gold-derived excerpts, secrets, absolute private paths or document-ID
branches. It reports two public-identifier overlaps with Gold separately: a common
CLI identifier already present in tracked baseline code, not exported private text.
No private content is sent to documentation/package services. Source documents,
Gold, package wheels/binaries, PDFs, captures, licenses and runtime journals stay
ignored. Synthetic literals in tests are independently authored public data.

```powershell
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdfplumber-table-v1-20261019/privacy.py
git diff --check
git status --short --untracked-files=all
```

Actual output: `PASS privacy files=4 private_Gold_text_matches=0 private_filenames=0
secrets=0 absolute_private_paths=0 public_identifier_overlaps=2`; LF/UTF-8/scope
checks pass; git diff --check exits 0. Pre-stage status contains exactly the four
allowed untracked files; no unrelated changes. Unit-only confcutdir excludes root
DB fixture imports, not extraction tests; integration/API/DB services were NOT_RUN
because this step changes only offline extraction comparison.
Final ignored terminal manifest verifies 84 protocol/capture/journal/verifier files,
including all four paired attempts, source-only and geometry audits. Runtime files,
25 wheels and pytest scratch fixtures are excluded from that count; runtime/wheel
manifests separately pin their exact bytes. Terminal SHA-256:
`05c42b11fbc432ee21dc2d1bf113c77c8c42f53b3f26a19b4a0dfca6dd7a0d3d`.
Immediate read-only reconciliation returned True for all 84 entries. All snapshots
and dependency files remain ignored; none are completion-commit payloads.

Git completion review executed git add with only the four allowlisted paths,
git diff --cached --check, git diff --check, git diff --cached --stat, and the full
staged diff for all four files. Both whitespace checks exit 0; staged content matches
current UTF-8/LF files and contains no artifacts or unrelated changes. Git's existing
autocrlf setting warns about potential CRLF on future checkout; no setting changed.
Only the authorized Conventional Commit is created; no push or history rewrite.
