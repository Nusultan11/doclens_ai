# ML-23 offline vector-ruled PDF table candidate v1

Date: 2026-10-19. Execution PASS; candidate REJECT; production authorization false.
Starting main HEAD `a03b0b76d3bfa97761e09920c115e0335f3d49ec`, clean, no staging.
Only four new allowlisted files. No production, Gold, scorer or existing module edits.

## Frozen protocol before candidate evaluation

H1: native PDF vector geometry can recover reviewed cell structure and geometric
header/value relationships missed by unchanged pypdf. Same-row/column checks are
not independently inferred semantic header roles; those roles remain NOT_EVALUATED.

Select all and only reviewed PDF records with cell/relationship labels:
c1-0033, c1-0040, c1-0045, c1-0048, c1-0049. Five exposed DEV documents,
46 anchors/provenance labels, 24 cells, 20 relations, 20 order pairs, 13 ASCII
digit-bearing anchors. No family-safe blind test or new human review is claimed.
Reviewed baseline captures were independently replayed before candidate inspection:
text 46/46, provenance 22/46, order 13/20, cells 0/24, relations 0/20, five success.
Native numeric-bearing presence 13/13; this is not exhaustive numeric accuracy.

PROMOTE only for further offline evaluation if at least one additional reviewed
cell AND relation pass, with zero lost text/numeric evidence, zero reduced frozen
provenance/order scores, unchanged native output and no resource failures or unsafe
geometry. REJECT on a critical regression or complete paired measurement with no
cell/relation gain. INCONCLUSIVE for missing/inconsistent evidence. Execution PASS
requires working bounded code, positive/negative synthetic tests, two genuine
reproducible paired runs and source/artifact/privacy checks. No QG-01 quality PASS:
general coverage, semantic roles and release thresholds are not established.

No tuning after real results. Reuse pypdf 6.20.0, no OCR/Docling/LLM/downloads.
Freeze narrow support: upright axis-aligned paths with positive scale/translation;
complete grids of at least 2x2 cells, no gap completion or merged-cell inference;
one literal ASCII text-show run per occupied cell with explicit simple-font widths,
FontBBox and identity-compatible encoding, no ToUnicode/custom encoding assumption.
Only actual stroke geometry, source-declared conservative font bounds and strict
containment may establish association. Multiple/overlapping/boundary text runs,
complex operators/fonts, rotated/clipped/forms/images and incomplete grids stay
needs_review. No guessed text positions, whitespace, spans or semantic header links.

Page-local table index is the top-to-bottom/left-to-right ordinal of detected valid
grids; it is not derived from Gold or asserted equivalent to ambiguous historical
table indexing. Row/column indices rank actual grid boundaries. Cells are span 1x1
only, with real page provenance. Preserve every native block; supplemental tables
are an explicit second representation, never automatic chunking/indexing input.

Budgets: input 50 MiB; 100 pages; 8 MiB decoded stream/page; 50,000 operations/page;
500 stroked segments/page; 10,000 text runs/page; 500,000 text characters/document;
10,000 cells/document; stack depth 64; logical 15 s. Isolated paired worker:
20 s, sampled process-tree RSS 512 MiB, 64 MiB capture, 0.02 s samples. Decompression
and PDF object loading precede some logical checks; sampled guards are local R&D
controls, not an OS hostile-input sandbox. Failures discard incomplete candidate
evidence and remain in full denominators. No status promotion clears native review.

Verify all 90 source SHA/size/format/license provenance fields and 19 reviewed Gold
records before/after. Pin original baseline captures, code/config/runtime and Gold.
Two serial paired runs include native before/candidate/native after and retain
private outputs only in fresh ignored storage. Match normal-mode deterministic
quality fields; timing is separate. Synthetic controls remain separate observations.

## Sources and boundaries

Requested `Doclens_AI-architecture.md` and its named anchors are unavailable.
The source map identifies the canonical DOCX instead; its extraction section 7
and roadmap section 20 were read, without creating a second architecture.
Local EX-PDF/EX-EXPERIMENT and QUALITY-GATES govern this candidate. Their historical
snapshot and editorial provenance are retained; no missing gate threshold invented.

[PAR-01: pypdf 6.20.0 extraction](https://pypdf.readthedocs.io/en/6.20.0/user/extract-text.html)
warns about complex coordinate and memory limitations; this motivates explicit
unsupported states, operator-level checks and independent synthetic controls.
[EXP-03: Datasheets for Datasets](https://arxiv.org/abs/1803.09010) informs provenance
and coverage reporting; [TST-02: pytest](https://docs.pytest.org/en/stable/how-to/parametrize.html)
informs the synthetic matrix. Documentation is not measured quality evidence.

## Implementation and measured results

The new standalone candidate interprets a bounded subset of pypdf content operators,
connected stroked segments, complete grids and conservative literal-run bounds.
Every emitted synthetic cell has actual vector bounds and an operator identity for
nonempty text. Normalized block_index is its actual appended block ordinal, separate
from the page-local grid ordinal. No Gold coordinate is copied into predictions.
Filled paths are unsupported because they can obscure strokes/text. Composed
coordinates must stay finite and bounded. Fatal errors discard partial geometry;
unsupported pages retain native text and add no table. No production import,
ExtractionResult/SourceLocation change, routing or indexing activation was added.

Both completed runs have the following identical scores. All five documents remain
in every applicable denominator; all labels are evaluated, none are silently dropped.

| Source | Text B/C | Provenance B/C | Order B/C | Cells B/C | Relations B/C | Digit-bearing B/C | Pages |
| --- | --- | --- | --- | --- | --- | --- | --- |
| c1-0033 | 9/9 | 1/9 | 0/3 | 0/8 | 0/8 | 0/0 N/E | 1 |
| c1-0040 | 8/8 | 4/8 | 2/3 | 0/4 | 0/4 | 1/1 | 1 |
| c1-0045 | 6/6 | 2/6 | 1/2 | 0/4 | 0/2 | 5/5 | 7 |
| c1-0048 | 11/11 | 8/11 | 6/6 | 0/3 | 0/1 | 3/3 | 17 |
| c1-0049 | 12/12 | 7/12 | 4/6 | 0/5 | 0/5 | 4/4 | 8 |
| Unique total | 46/46 | 22/46 | 13/20 | 0/24 | 0/20 | 13/13 | 34 |

B/C means the same count for baseline and candidate, not doubled observations.
Recovered identities: empty. Newly lost identities: empty. Every native block,
duplicate occurrence, warning and original page locator is byte/value equivalent
before/after; the historical baseline fingerprints also match. No candidate grids
or cells were emitted on this cohort. Reviewed text inside cells: 0/24. Reviewed
table/locator and relation fidelity therefore remain 0/24 and 0/20, with no evidence
of geometry correctness on real tables. Spans and semantic header roles on real
sources are NOT_EVALUATED. Numeric result is unchanged reviewed whole-anchor
presence, not independent OCR, visual numeric fidelity or a check of all values.

Baseline: attempted 5, success 5, needs_review 0, failed 0. Candidate: attempted 5,
success 0, needs_review 5, failed 0. Each transition is success -> needs_review;
native success is not evidence that table extraction is complete. No review result
is promoted to success. Runtime-failed/unknown documents: zero in each completed run.

All 34 pages stop with fixed diagnostic `unsupported_operator`. A separate bounded
read-only operator inventory confirms the first operator outside the supported set:
c1-0033 W* (1 page), c1-0040 TJ (1), c1-0045 W (7), c1-0048 BDC (17), c1-0049 BDC (8).
This is an observed coverage boundary, not proof that these operators are malformed
or that vector geometry cannot work. Later font/grid/text conditions remain UNKNOWN
because the candidate stops early. No support was broadened after seeing results.

The registered advancement gate fails: zero reviewed cell/relation gains and five
new review outcomes. Candidate REJECT applies to this frozen configuration. H1 has
not been demonstrated on reviewed sources; the wider geometry hypothesis remains
unresolved. Positive synthetic extraction does not close QG-01. Production
authorization is false; frozen Docling rejection and current pypdf remain unchanged.

## Repetitions, failures and resources

Completed repetitions are original run-1 and run-3, not relabelled run-2. Their five
result captures are byte-identical and all deterministic quality fields agree.
Between them, run-2 printed the sanitized BLOCKED diagnostic and stopped after two
saved pairs, without metrics.json. Those two captures match run-1. Preserve the
incomplete directory: 2 captured / 5 planned, 3 UNKNOWN/unattempted, no claim of a
completed repetition or complete resource/cleanup journal for that attempt. The
underlying harness exception was not captured and remains UNKNOWN. No output was
repaired or combined with another run. No candidate/configuration change followed.
The next serial attempt added parent-only exception tracing, which recorded no
exceptions and exit 0. This retry is an explicit execution deviation, not new data.
There are five unique evaluated sources, ten completed paired source executions,
plus two saved source executions in the incomplete attempt; repeated observations
do not enlarge the reviewed population. No ML-22/other historical result is rewritten.

| Completed run | P50 seconds | P95 seconds | Maximum tree RSS bytes | Samples | Cleanup |
| --- | --- | --- | --- | --- | --- |
| run-1 | 2.078 | 4.640 | 84,889,600 | 533 | 5/5 |
| run-3 | 2.063 | 4.640 | 83,361,792 | 532 | 5/5 |

P50/P95 use nearest rank over five documents per repetition. Timing includes fresh
Python worker startup and native-before/candidate/native-after, not isolated table
algorithm latency. Serial local CPU execution, Windows AMD64, Python 3.12.3,
pypdf 6.20.0, psutil 7.1.0; 8 physical / 16 logical CPUs, 16,541,597,696 bytes RAM.
No GPU/model, external process inside a worker or downloads. Sampled process-tree
RSS can miss short peaks; it is not allocator profiling. Both completed runs have
zero timeout/memory/output failures, no partial files or remaining candidate workers.
The incomplete run's peak and terminal cleanup are not inferred from the final runs.

## Reproducibility and integrity

The preregistered report snapshot and registration were written before real runs.
Code and nine code/helper pins, Python/pypdf source hashes, cohort, budgets and
decision are immutable across all attempts. Baseline replay preceded inference.

| Fingerprint | SHA-256 / canonical fingerprint |
| --- | --- |
| Manifest, 90 sources | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Reviewed Gold, 19 records | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Source map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Baseline preflight file | `cc902efbab940ba8bf73a6381f927bff8115649378d6f43ef4c86ab2dd7c0866` |
| Protocol snapshot | `d4d743be58bb71ecc95edb809c26fb017d02c742a33e1ffb52319adb5de28830` |
| registration.json file | `74f07cbdfb55d8b5445c100a0ee9b71fcc64232741eb81ebae184218f85270b7` |
| Canonical registration | `da1f5a84faf4dac8863bfa814ff4c5dbaa974292a9b99ddda6619be0fdc69002` |
| Both completed quality fingerprints | `a21104b3beaaabeeb9191a14834a487394b40b6879f9d168727455b825834247` |
| Candidate source | `d2236a7e01350be7552ceb8a51f4fbc18633a302d31f5c1c43455a710f824de0` |
| Runner source | `03229855d34528030a565b79e8dbebcf369c636c8a04b092e6d5f5502a18210d` |
| Synthetic tests | `6a0be33a3e48feaba526ddc460819dac4f5446a2cf86e1f3886e23d9f90dfe93` |
| run-1 manifest, 12 artifacts | `9365b5a7eca021279aa209857917ed5f947e9b6b4d56fd1edd0c1ee9c65a64f7` |
| run-3 manifest, 12 artifacts | `d592e140f2b6e4341c800eefa72b7879cbb103ce3fcecf2fe9f401e5099d2aa6` |
| Read-only verifier | `e47b3bcbaea5e3678006afa1b29438df09e628f0406856c2140529ea71a34a8d` |

| Cohort source | SHA-256 |
| --- | --- |
| c1-0033 | `081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd` |
| c1-0040 | `18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344` |
| c1-0045 | `04358ce617249f170d38ea302cbc96a35701987507e61fb87ea2be30da2cfddc` |
| c1-0048 | `5928ffa7f5f8d44678a56d810794f4263e4a3db9a7d87422ec8d3c6907186f4f` |
| c1-0049 | `fa821b92dde14335883c0327f70851d9b5813feea8584136eb125fe8833a9240` |

Verified all 90 RAW byte hashes/sizes/formats before and after, all 19 reviewed Gold
identities, license/license URL/provenance fields, historical baseline capture SHA,
and existing ML-18/19 manifests (82/78 artifacts). License verification preserves
recorded provenance; this is not a fresh legal assessment. Existing four production
modules and two imported helpers match starting HEAD bytes. No dependency changes.
Synthetic PDFs use constructed literal data and a standard Courier font reference,
no embedded private/public font file or downloaded font. PDFium independently
extracts all four known literals and renders the 400x300 synthetic page; rendered
dimensions are not a visual audit of real private tables.

All scratch scripts, captures, journals and experiment metadata remain in verified
Git-ignored evaluation-output/pdf-table-v1-20261019; immutable RAW/Gold remain in
their original ignored storage. Only four allowlisted source/
test/report files are Git-visible. No private source text or Gold-derived excerpts,
real filenames, absolute private paths, credentials, PDFs, weights or captures are
included in the reviewed change. Gold is used only by the unchanged scorer after
extraction, never to construct candidate output.

## Executed commands and results

PowerShell from the repository root. The explicit runtime already exists; no install.

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
.venv/Scripts/ruff.exe check src/doclens_ai/extraction/pdf_table_candidate.py tools/pdf_table_candidate/benchmark.py tests/unit/test_pdf_table_candidate.py
.venv/Scripts/ruff.exe format --check src/doclens_ai/extraction/pdf_table_candidate.py tools/pdf_table_candidate/benchmark.py tests/unit/test_pdf_table_candidate.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/pdf-table-v1-20261019/test-tmp-4','tests/unit/test_pdf_table_candidate.py','tests/unit/test_extraction.py','tests/unit/test_extraction_fidelity.py','tests/unit/test_docling_candidate.py','tests/unit/test_pdf_ocr_candidate.py']))"
Copy-Item -LiteralPath docs/eda/pdf_table_candidate_v1.md -Destination evaluation-output/pdf-table-v1-20261019/protocol-before-evaluation.md
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/pdf_table_candidate/benchmark.py --preregister --output evaluation-output/pdf-table-v1-20261019/registration
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/pdf_table_candidate/benchmark.py --registration evaluation-output/pdf-table-v1-20261019/registration/registration.json --output evaluation-output/pdf-table-v1-20261019/run-1
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/pdf_table_candidate/benchmark.py --registration evaluation-output/pdf-table-v1-20261019/registration/registration.json --output evaluation-output/pdf-table-v1-20261019/run-2
```

Outputs: Ruff `All checks passed!`; format `3 files already formatted`;
pytest `264 passed, 1 warning in 12.39s` (45 candidate tests + 219 existing regressions,
zero skipped/failed). The warning is PDFium's documented default text-range redirect.
Preregister stdout `status=FROZEN`, canonical registration above. run-1 stdout
`status=PASS candidate=REJECT`, quality fingerprint above. run-2 stdout
`BLOCKED: frozen PDF table experiment input, resource or output boundary rejected`;
it did not produce a successful summary. The captured exit from the PowerShell
command was nonzero. No retry/tuning of individual extraction responses occurred.

The exact run-3 invocation used a short stdin diagnostic wrapper (not a code edit):

```python
import json,sys
from tools.pdf_table_candidate import benchmark as b
from pathlib import Path
issues=[]
def trace(frame,event,arg):
 if event=='exception' and frame.f_code.co_filename.endswith('benchmark.py') and frame.f_code.co_name in ('main','monitor'):
  exc=arg[1]
  issues.append({'function':frame.f_code.co_name,'line':frame.f_lineno,'type':type(exc).__name__,'errno':getattr(exc,'errno',None),'winerror':getattr(exc,'winerror',None)})
 return trace
sys.argv=['benchmark.py','--registration','evaluation-output/pdf-table-v1-20261019/registration/registration.json','--output','evaluation-output/pdf-table-v1-20261019/run-3']
sys.settrace(trace)
code=b.main()
sys.settrace(None)
Path('evaluation-output/pdf-table-v1-20261019/attempt-3-diagnostics.json').write_text(json.dumps({'exit':code,'exceptions':issues},sort_keys=True)+'\n',encoding='utf-8')
print('HARNESS_DIAGNOSTICS',json.dumps({'exit':code,'exceptions':issues}))
raise SystemExit(code)
```

Piped to `evaluation-output/docling-v1-runtime/Scripts/python.exe -B -`: run-3 stdout
`status=PASS candidate=REJECT`, same quality fingerprint;
`HARNESS_DIAGNOSTICS {"exit": 0, "exceptions": []}`. Trace applies only to parent;
the isolated worker command/code/configuration are identical to run-1.

```powershell
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-table-v1-20261019/verify.py
```

Actual output (exit 0):

```text
PASS originals=90 reviewed_Gold=19 historical_artifacts=82,78 unchanged_production=6
PASS replay=2x5 paired captures=byte_identical native=verbatim deterministic_quality=a21104b3beaaabeeb9191a14834a487394b40b6879f9d168727455b825834247
PASS text=46/46 provenance=22/46 order=13/20 cells=0/24 relations=0/20 numeric_presence=13/13 lost=0 recovered=0
PASS pages=34 needs_review=5 success=0 failed=0 UNKNOWN_dimensions_preserved cleanup=10/10
```

Earlier executed checks are retained, not rewritten as first-pass success:
initial synthetic run `36 passed, 4 failed in 2.23s`; tests exposed missing normalized
block identity / incomplete synthetic locator and unsupported PDFium context-manager
usage. Fixed actual block ordinals and explicit close/finally; repeat `40 passed,
1 warning in 1.61s`. Initial Ruff found import sorting, missing zip(strict=True),
an ambiguous local name and a long literal; corrected within scope. Extended suite
then passed 263 tests. Self-review separated glyph advance from graphics line width,
rejected filled/obscuring paths and bounded composed coordinates; corresponding
positive/negative regressions precede registration and the final 264-test result.
Coverage includes malformed PDFs, missing metrics/positions, incomplete/merged/
rotated structures, duplicate text, signed numeric literals, mixed pages, native
review preservation, timeout/memory/worker failures, unknown denominators, cleanup
and sanitized output. No candidate logic changed after registration.

The first private-string scan flagged two single-word overlaps with a reviewed
non-PDF label. Both are an ordinary CLI/code identifier independently present as a
function name in the unchanged, tracked OCR runner at starting HEAD. The scan now
reports these public-identifier overlaps separately (2) and still rejects private
phrases, filenames and secrets. No private answer text is printed by the scanner.

An initial scratch-only operator inventory used ContentStream truthiness and
incorrectly printed NONE; pypdf streams can be false-valued while containing data.
Corrected the ignored inventory to test `is not None`. The candidate already used
the correct None test; benchmark scores and frozen captures were unaffected. Both
scratch inventories remain available, with the corrected inventory SHA-256
`386d0708dd982c0baccbfa3ab0f66769be63849ea1b4026b3d7d8b8350b57bc0`.

Final scoped review commands executed:

```powershell
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-table-v1-20261019/privacy.py
git diff --check
git add -- src/doclens_ai/extraction/pdf_table_candidate.py tools/pdf_table_candidate/benchmark.py tests/unit/test_pdf_table_candidate.py docs/eda/pdf_table_candidate_v1.md
git diff --cached --check
git diff --cached --stat
git diff --cached -- src/doclens_ai/extraction/pdf_table_candidate.py
git diff --cached -- tools/pdf_table_candidate/benchmark.py tests/unit/test_pdf_table_candidate.py
git diff --cached -- docs/eda/pdf_table_candidate_v1.md
git status --short --untracked-files=all
```

Privacy output: `PASS privacy files=4 private_Gold_text_matches=0 private_filenames=0
secrets=0 absolute_private_paths=0 public_identifier_overlaps=2`; UTF-8/LF, no
source-specific branches, no production edits, exact four-file scope. Both Git
whitespace checks exited 0 without output. The complete staged diff was inspected:
only the four allowlisted additions, no binaries or generated artifacts. Initial
sandboxed git add could not create index.lock; the authorized scoped Git operation
then succeeded with elevated file access. Git warns that autocrlf could write CRLF
on a future checkout; staged blobs and current files are identical UTF-8/LF. No
repository line-ending setting was changed. Staged status is A for each allowed
file, with no other changes. Commit authorization is the current task; no push.
The final ignored terminal manifest verifies 39 experiment/protocol/verifier files
(including the incomplete attempt, excluding synthetic pytest temporary files),
SHA-256 `9a5544ac5d4fb1ff13b6fdef14e97e9514acdd36bb9e400814dd4b86bac2034f`.
Its immediate read-only hash reconciliation returned True for all 39 files.

## Limits and next recommendation

This small, previously exposed DEV cohort is not independent generalization or a
sealed test; family-safe test evidence is unavailable. No reviewed geometric gain
was established. Do not promote or wire this implementation into production.
The smallest justified future investigation is public synthetic support/validation
of clipping and positioned text arrays before any separately preregistered coverage
extension. Do not remap known Gold indices or relax exact locator scoring. Resolve
the incomplete harness attempt's UNKNOWN exception separately if it recurs.
