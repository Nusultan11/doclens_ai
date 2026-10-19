# ML-21 offline DOCX footnote candidate v1

Date: 2026-10-19. **Execution PASS. Candidate advancement INCONCLUSIVE.**
**Production authorization false.** H1 text recovery and native-preservation
guardrails were reproduced in final runs **5/6**. Reviewed ancillary locator
correctness remains NOT_EVALUATED; this is functioning offline candidate code,
not an approved production extraction change.

## Preregistration — before real candidate extraction

Starting HEAD: `b51e3fa09770e6109701d60cfa803936daa8577e`; main, clean,
upstream divergence 0/0. Execution and candidate verdict were PENDING at registration.
Production authorization is **false**. Only the four task-allowlisted new files
are in scope; no commit is authorized before review.

H1: bounded traversal of package relationships and ordinary WordprocessingML
footnotes can recover the one reviewed omitted footnote text while preserving
the unchanged baseline body/table evidence, statuses, numbers and order.

Freeze all three existing reviewed DOCX sources: c1-0006, c1-0007, c1-0008.
They have 15 required anchors, 6 order checks, 7 cell/span checks and 3 relations.
Historical baseline is 14/15 text and provenance, 6/6 order, 7/7 cells, 3/3
relations; the sole reviewed footnote is absent 0/1. All attempted documents,
failed and needs_review outcomes remain in denominators. Two serial isolated
paired runs use identical code/configuration and unchanged reviewed Gold.

Primary metric: exact whitespace-normalized reviewed footnote text presence,
within one complete referenced note paragraph, 0/1 -> 1/1 in both runs.
Secondary: independently verified OOXML part/note/paragraph/reference identities;
native block multiplicities, existing scorer objects, numeric-bearing labels,
status transitions, failures, time and peak sampled process-tree RSS.

Gold's ancillary `part_index` is zero-based but its relationship to a package
part, note ordinal or `w:id` is unspecified in the supplied protocol. Do not
equate these identifiers. Gold footnote-locator correctness is NOT_EVALUATED
unless an independent existing convention establishes that mapping. Do not
change Gold or the frozen scorer to make it pass. Genuine OOXML provenance and
reviewed Gold provenance are separate measurements.

Guardrails: zero baseline-present text/numeric loss; identical frozen baseline
score objects and native result before/after candidate execution; no automatic
needs_review -> success; no incomplete note counted as successful recovery;
no fabricated body/cell/page/Gold coordinates. Unsupported note structures stay
explicitly incomplete/needs_review; corrupt packages and resource failures are
failed with content-free diagnostics and no partial evidence acceptance.

Fixed candidate limits: 50 MiB input, 20,000 ZIP entries, 16 MiB per entry,
128 MiB declared expanded ZIP total, compression ratio <=200, 200,000 XML nodes,
128 XML depth, 1,000 notes, 10,000 references, 5,000 paragraphs, 500,000 output
characters, 15 s logical extraction deadline. Benchmark isolation additionally
enforces 20 s/document, 512 MiB sampled process-tree RSS and 64 MiB capture size;
samples every 0.02 s. These are bounded local R&D controls, not a hostile-upload
OS sandbox. No new dependencies are installed; no OCR, models or external links
are executed.

Execution PASS requires real paired runs, synthetic/regression tests, input/artifact
integrity and privacy checks. REJECT on a critical regression or fabricated
provenance; INCONCLUSIVE if recovery or reviewed provenance cannot be established.
PROMOTE_FOR_FURTHER_OFFLINE_EVALUATION requires recovery, all guardrails and
independently established reviewed provenance. One real footnote cannot establish
generalization or production readiness. H1 text-recovery results are reported
separately from this advancement verdict.

Frozen manifest SHA-256:
`c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0`.
Source-map fingerprint:
`d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8`.
Reviewed 19-record Gold bytes:
`f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf`.
All 90 identities/sizes/formats and license provenance fields passed preflight.
Human review remains the existing attestation, not a new review by this experiment.
Runtime: Python 3.12.3, python-docx 1.2.0, Pydantic 2.14.0. Code/configuration
and production pins will be frozen before real paired execution.

References: [PAR-02: python-docx tables](https://python-docx.readthedocs.io/en/latest/user/tables.html),
[PAR-07: Python 3.12 zipfile](https://docs.python.org/3.12/library/zipfile.html),
[TST-02: pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html).
The table reference explains why arbitrary tables must not be flattened into note
paragraphs. These references do not establish measured candidate quality.

## Retained development failures, before final paired runs

Initial synthetic checks: 48 passed, 2 failed because the sandbox system temporary
directory denied Windows rename/replace. An independent atomic-write probe succeeded
in the verified ignored workspace scratch directory; rerunning there gave 50/50.
Expanded synthetic/extraction/fidelity checks then passed 106 tests. Initial Ruff
line-length/import failures were corrected within the new files and rerun.

The first real attempt, run-1, stopped after the first DOCX capture: the initially
reused PDF capture-restorer assumed all blocks had text fields and raised KeyError
on a DOCX table. A bounded local reproduction identified the restoration call;
no private content or exception values were exported. The capture and resource
journal remain unchanged, with no complete-run metrics or success claimed.
The new runner now restores the existing DOCX text/table union losslessly; a public
synthetic merged-table/header-warning round-trip regression covers this correction.
This changes only the new harness, not the extractor, Gold, limits or thresholds.
The original registration/protocol and incomplete run-1 are retained. The second
registration froze the corrected restoration code before attempt 2.

Run-2 reached the target document but exposed an independent-verifier defect:
paragraph-property tab-stop declarations were incorrectly counted as literal tabs.
A content-free local check reproduced this on 1 paragraph/1 property declaration;
excluding property subtrees matched every complete captured paragraph. A separate
public synthetic tab-stop/run-tab regression covers the distinction. Candidate
text, relationship logic, limits and acceptance criteria remain unchanged.
Incomplete attempts 1/2 and registrations 1/2 remain retained. The third
registration froze the corrected verifier before the complete paired runs 3/4.

Runs 3/4 completed with identical quality fields. Final code review subsequently
identified incomplete breakdown metadata for an absent worker capture: footnote
totals were retained, but other Gold dimensions were not explicitly projected.
The harness now retains every reviewed label total with UNKNOWN results; a
synthetic regression covers missing-capture numeric/recovery semantics. It also
reports native and supplemented numeric-bearing anchor presence separately.
An ordinary diagnostic word collided with a short unrelated Gold label in the
exact-text privacy scanner; the diagnostic was rephrased. No candidate extraction
logic, threshold or input changed. Complete runs 3/4 remain unchanged historical
captures; registration 4 and runs 5/6 subsequently verified the final harness.

## Implemented offline boundary

The new frozen dataclasses implement `docx-footnotes-offline-v1` separately from
`SourceLocation`/`ExtractionResult`. No existing module, production route, package
export, chunker, scorer, ingestion or index contract was edited. No dependencies
were installed. The runner selects all reviewed DOCX records by format, with no
source-ID branch or expected-text rule in the extractor. Gold is loaded only by
the parent for preregistration and evaluation; anchor matching occurs after
extraction. No Gold content is passed to workers or used to construct their output.

Package-root officeDocument and main-part footnotes relationships establish the
actual parts, including relocated synthetic parts. The offline result preserves
actual part URI and relationship ID, original lexical `w:id`, note-element ordinal,
paragraph child ordinal and text, each reference's body-rooted XML child path,
containing paragraph path, and baseline body block index only when established
from actual recognized main-body children. XML paths are not rendered positions.
No row, column, page or Gold coordinate is invented.

One note is emitted once per unique numeric note identity, with all actual reference
ordinals, including repeated references. Identical text in distinct note IDs is
retained separately. Separator/continuation types are excluded by declared type,
not by assuming a normal note with ID zero is a separator. Duplicate numeric IDs
fail closed. Hyperlink labels, tabs, breaks, Unicode and numeric strings are
preserved; targets are neither fetched nor executed. Styling properties do not
become text. No normalization other than the existing scorer's whitespace rule
is used for anchor matching.

Tables, fields, revisions, drawings and unsupported note structures remain
explicitly incomplete/needs_review. Supported paragraphs may be retained privately,
but an incomplete or unreferenced note cannot count as recovered evidence.
Dangling/ambiguous links and unsupported reference contexts remain explicit issues.
Fatal XML/ZIP/limit failures discard partial ancillary evidence. The baseline
result is never overwritten or silently repaired. Effective offline status is at
least as conservative as baseline status; recovered notes do not clear warnings.

The benchmark restores the unchanged DOCX union losslessly, including table cells,
spans, warnings and source locations. It compares complete production results
before/after the candidate, fingerprints them against frozen historical captures,
then applies the unchanged scorer to that same native result. Supplemental footnote
presence and actual OOXML addresses are measured separately. The offline contract
has no production routing or chunking/indexing consumer.

## Real paired results — three distinct documents

Final runs 5/6 used the same registration, candidate, harness, sources and reviewed
Gold. All quality fields and all three raw paired captures match exactly between
repetitions. Repetitions are not additional reviewed sources or labels.

| Source | Frozen text | Descriptive native + ancillary presence | Frozen provenance | Order | Cells | Relations | Footnote recovery | Effective status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c1-0006 | 5/5 | 5/5 | 5/5 | 2/2 | 3/3 | 1/1 | N/E, no reviewed note label | needs_review -> needs_review |
| c1-0007 | 6/7 | 7/7 | 6/7 | 2/2 | 4/4 | 2/2 | 0/1 -> 1/1, a6 | needs_review -> needs_review |
| c1-0008 | 3/3 | 3/3 | 3/3 | 2/2 | N/E | N/E | N/E, no reviewed note label | success -> success |
| Unique total | **14/15** | **15/15** | **14/15** | **6/6** | **7/7** | **3/3** | **1 recovered, zero lost** | **1 success, 2 review, 0 failed** |

The native + ancillary column is an explicit additional presence measurement,
not a rewritten frozen-scorer result. The sole recovered identity is c1-0007/a6.
Every native block, table cell/span, duplicate occurrence, source locator, warning
and native score object is unchanged. Fourteen native anchors remain present;
all reviewed body/control checks pass. There are no new eligibility promotions.

Five reviewed anchors contain literal ASCII digits: native presence remains **4/5**;
the supplemental complete footnote recovers the remaining one, giving descriptive
presence **5/5**. c1-0006 contributes 1/1 native, c1-0007 3/4 native plus one
footnote, c1-0008 has no numeric-bearing labels. This verifies selected complete
anchor strings, not every numeric token, unit, date or identifier in these sources.
Numeric semantic accuracy outside those labels remains NOT_EVALUATED.

The independent XML-address verifier confirms **7 notes, 7 references and 7
paragraphs** in the target document; all seven are complete in the supported
subset and have real reference links. The two controls have no user-note evidence.
Seven notes are not seven reviewed Gold footnotes: only one note anchor is reviewed.
Word rendering, exhaustive semantic fidelity and uncommon OOXML constructs were
not independently reviewed. Strict-namespace WordprocessingML is outside this
candidate's transitional-namespace support and fails explicitly.
Checks cover bounded package/XML well-formedness and selected relationships,
not full OOXML XSD validation or a Word rendering oracle.

**Reviewed footnote provenance is NOT_EVALUATED: 0 evaluated / 1 label, null passed
count and score.** Gold `part_index=0`, actual part URI, note `w:id`, note-element
ordinal and reference position remain distinct. No existing supplied convention
justifies mapping the Gold index onto a prediction. The successful independent
OOXML address checks do not establish that reviewed mapping or visual correctness.
The original frozen provenance score therefore remains 14/15.

## Reproducibility, resources and invariants

| Frozen identity | SHA-256 / canonical fingerprint |
| --- | --- |
| Candidate module | `126d48f84e186624ca7ac2d403675e0e28dd8849ab3202fa6923df31565e9dab` |
| Final benchmark harness | `9dd273b50962fb6dbe95ea499bb6a430d237d8e2e53e41935d53dce0c4c0d309` |
| Synthetic tests | `149e22e933f8d9f7c122b7a3ff18a3846b1b8607450ecc9f77ac92463fb2049d` |
| Final registration bytes | `96733ee5c34270e260eefa138ffd9e9dfaf37d50b15d365247d8f1bbc7deeff1` |
| Final registration fingerprint | `ba6fa23cbec7b33d04d4efe5223a4bdf19fc388d705383d65795c9149759536f` |
| Frozen protocol snapshot | `c31ddf7734f1b8ac076812809f40e771a2fad5c4135178058e694542fe942988` |
| Both final quality fingerprints | `419a17c32a16f9e6b2c68e967f2cc7004ac6caa5acd820d394c16e71fb913f14` |
| Run-5 metrics bytes | `19277e70ea5387b3750ca608a0786d02e45f7c1921286f6f7843394c7783e8d2` |
| Run-6 metrics bytes | `a6cd25fdef774991898b9ff4412a3eec3f80f5fed57f21172f708420d6e76f51` |
| Run-5 seven-artifact manifest | `dcd0e64eb3bafa2f9e7c9775fc1fe6ae5d90da8b98b64152dba7d290a51a6d7f` |
| Run-6 seven-artifact manifest | `f9716cfdc0418d9e05714119cbb556f4c64aeb07fa7760182ca63567cd054c55` |
| Read-only replay verifier | `a595f7412ec35b1f16ab6fd6b9b6e20f4275ee17aa725a17e5e01de359c0c9ee` |

Candidate code, resource limits and acceptance criteria are identical across all
registrations. Only the disclosed harness/tests/diagnostics changed between earlier
attempts and final registration. All prior captures remain retained. Final captures
are genuine new isolated executions, not relabelled earlier outputs or repaired
model/parser results. No model or OCR was used.

Environment: Windows 11 AMD64, 16 logical CPUs, Python 3.12.3, python-docx 1.2.0,
pypdf 6.20.0, openpyxl 3.1.5, Pydantic 2.14.0 and psutil 7.1.0 from existing local
runtimes. No runtime was installed or upgraded.

| Measured resource, per isolated worker | Run 5 | Run 6 |
| --- | ---: | ---: |
| Document wall seconds, cohort order | 1.625 / 2.250 / 1.234 | 1.625 / 2.297 / 1.235 |
| P50 / P95 seconds, nearest rank, n=3 | 1.625 / 2.250 | 1.625 / 2.297 |
| Peak sampled process-tree RSS, bytes | 138,637,312 | 136,044,544 |
| Resource failures / cleanup failures | 0/3 / 0/3 | 0/3 / 0/3 |

Timing includes startup/imports, native extraction, ancillary extraction, a second
native extraction for compatibility checking and private capture serialization.
It excludes parent preflight/hash/scoring work. Separate stage latency and total
parent RSS are NOT_EVALUATED; these are not production throughput measurements.
Sampling every 0.02 s can miss spikes. Parent memory/timeout guards, bounded XML
and output serialization provide local experiment controls, not an OS-level
hostile-input sandbox. No subprocess shell, Office execution, external-link fetch,
formula evaluation, network request or generated rendered document is involved.

Resource journals reconcile sample counts and peaks. All worker processes exit,
no partial capture remains, and no live candidate worker was found after runs.
All 90 originals and frozen Gold are verified before/after; current production
parser/model/scorer/Gold-validator hashes match the frozen baseline. Historical
82 ML-18, 78 ML-19 and 39 ML-20 pinned artifacts also remain unchanged.

## Actual tests, replay and privacy checks

The final focused command passed **109 tests in 2.76 s**, including **62 synthetic
candidate cases** and existing extraction/fidelity regressions. The broader
coverage/extraction/OCR/Docling suites passed **309 tests in 12.66 s**. No final
failures or skips; these suites overlap and must not be summed as unique tests.

| Synthetic scenario group | Passed cases |
| --- | ---: |
| No notes, relocated parts, multiple/repeated references, duplicate text | 4 |
| Separator types and normal zero-ID note | 3 |
| Unicode, numbers, hyperlinks and controls | 1 |
| Unsupported note blocks / complex paragraphs | 3 / 4 |
| Dangling/orphan/separator references | 1 |
| Missing/malformed/external relationships | 6 |
| Corrupt/entity XML | 3 |
| Input/archive/XML/note/reference/paragraph/output limits | 11 |
| Logical timeout and handle release | 1 |
| Duplicate note IDs and corrupt ZIP | 1 |
| RAW/production compatibility | 1 |
| Independent addresses and altered-address rejection | 1 |
| Frozen scorer separation and unsupported Gold provenance | 1 |
| Isolated timeout / memory / worker failure cleanup | 3 |
| Capture output budget / successful worker | 1 |
| Invalid limit values | 7 |
| Body-table references without invented cell coordinates | 1 |
| Ambiguous/archive traversal/external/duplicate relationships | 4 |
| Logging restoration and atomic-publication failure cleanup | 1 |
| Journal-open failure prevents worker spawn | 1 |
| Lossless table/span/warning capture restoration | 1 |
| Tab-stop properties versus literal run tabs | 1 |
| Missing-capture denominators and UNKNOWN results | 1 |

Ruff returned `All checks passed!`; formatting returned `3 files already formatted`.
Only the three new Python files were checked for formatting; unrelated historical
formatting issues were not fixed or counted as passed.

Exact final commands, from the repository root (paths refer to retained ignored
runtime artifacts; existing outputs are never overwritten):

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/docx_footnote_candidate/benchmark.py --preregister --output evaluation-output/docx-footnote-v1-20261019/preregistration-v4
Copy-Item -LiteralPath docs/eda/docx_footnote_candidate_v1.md -Destination evaluation-output/docx-footnote-v1-20261019/preregistration-v4/protocol.md
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/docx_footnote_candidate/benchmark.py --registration evaluation-output/docx-footnote-v1-20261019/preregistration-v4/registration.json --output evaluation-output/docx-footnote-v1-20261019/run-5
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/docx_footnote_candidate/benchmark.py --registration evaluation-output/docx-footnote-v1-20261019/preregistration-v4/registration.json --output evaluation-output/docx-footnote-v1-20261019/run-6
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-v1-20261019/test-tmp-7','--junitxml=evaluation-output/docx-footnote-v1-20261019/final-synthetic-tests.xml','tests/unit/test_docx_footnote_candidate.py','tests/unit/test_extraction.py','tests/unit/test_extraction_fidelity.py']))"
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-v1-20261019/test-tmp-8','tests/unit/test_docx_footnote_candidate.py','tests/unit/test_extraction_coverage_audit.py','tests/unit/test_extraction_fidelity.py','tests/unit/test_extraction.py','tests/unit/test_pdf_ocr_candidate.py','tests/unit/test_docling_candidate.py']))"
.venv/Scripts/python.exe -B -m ruff check src/doclens_ai/extraction/docx_footnote_candidate.py tools/docx_footnote_candidate/benchmark.py tests/unit/test_docx_footnote_candidate.py
.venv/Scripts/python.exe -B -m ruff format --check src/doclens_ai/extraction/docx_footnote_candidate.py tools/docx_footnote_candidate/benchmark.py tests/unit/test_docx_footnote_candidate.py
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -u evaluation-output/docx-footnote-v1-20261019/verify.py
git diff --check
git status --short --untracked-files=all
```

Both final run commands returned PASS / INCONCLUSIVE and the same quality
fingerprint above. Read-only replay returned PASS for all captures, the original
denominators, numeric slices, OOXML addresses, status preservation, sampled
resources, unchanged historical artifacts, source/Gold integrity and exact scope.
It performs no new extraction. The private-data scan checks all four new files
against original basenames and reviewed anchor strings of at least 12 characters,
plus credential/private-path patterns; full diff review supplements that scanner.
UTF-8/LF, whitespace and ignored scratch boundaries are checked. No captures,
Gold text, original filenames, private paths, fonts, models or binaries enter Git.

The final experiment manifest pins **49 artifacts**: all four registration/protocol
snapshots, retained incomplete attempts, all complete-run captures/metrics/journals
and their manifests, the read-only verifier and two test XML summaries. Synthetic
temporary working files are ignored separately and are not presented as frozen
experiment observations. Final manifest SHA-256:
`188651f671838d0c8e4f20057c8529b0c8329614df04b3846d481c55b31e1d4e`.
All 49 hashes passed read-only checking after capture creation.

The complete four-new-file diff is retained in ignored scratch. Ordinary
`git diff` omits untracked files; each was checked with the following actual
command form (one invocation per allowlisted path):

```powershell
git -c core.autocrlf=false diff --no-index --check -- /dev/null src/doclens_ai/extraction/docx_footnote_candidate.py
git -c core.autocrlf=false diff --no-index --check -- /dev/null tools/docx_footnote_candidate/benchmark.py
git -c core.autocrlf=false diff --no-index --check -- /dev/null tests/unit/test_docx_footnote_candidate.py
git -c core.autocrlf=false diff --no-index --check -- /dev/null docs/eda/docx_footnote_candidate_v1.md
```

Each produced no whitespace diagnostics; no-index exit 1 denotes the expected
new-file difference. The command-only newline override avoids Git's future CRLF
conversion warning without modifying repository configuration or file bytes.
All actual files remain UTF-8/LF. At the experiment handoff, no tracked existing
file changed, nothing was staged and HEAD remained the starting commit. Final
review and the separately authorized commit gate are recorded below.

## Decision and next review boundary

H1's narrow text recovery/native preservation claim is supported on the three
exposed DEV sources and public synthetic cases. **Advancement INCONCLUSIVE**
follows the preregistered requirement for independently established reviewed
provenance: Gold's ancillary index convention remains unresolved. Do not call
OOXML address validity a Gold provenance PASS or general-purpose rendered fidelity.

Exactly one next recommendation: obtain a separately reviewed explicit ancillary
locator convention and its mapping to real part/note identity, then evaluate
additional independently reviewed footnotes and supported/unsupported structures
before considering broader offline advancement. Do not silently relabel current
Gold, extend production contracts or promote this candidate from one real label.
RU/KK/EN strings in synthetic cases do not establish real multilingual coverage.
No next experiment or production promotion is authorized by these results.

## Final code review and commit gate, 2026-10-19

Review re-read the candidate, harness, synthetic tests and report against the
unchanged production DOCX parser, source-location contract, Gold validation and
scorer. No confirmed defect requiring a Python change was found. Package part
resolution rejects external/escaping/ambiguous targets; hyperlink labels do not
cause target access. Repeated references and note identities remain distinct.
Unsupported content is explicit, fatal failures discard partial evidence, and
effective status cannot clear a production review/failure outcome.

The public benchmark entry point requires a new ignored output root outside RAW
and checks symlink ancestors. Worker staging is owned by that fresh benchmark
run; it is not an arbitrary untrusted output-path API. Capture publication is
bounded and atomic, subprocesses use no shell, and termination/cleanup paths are
covered by synthetic tests. Declared ZIP limits, logical deadlines and sampled
process-tree guards remain local R&D controls with the limitations stated above.
No routing, chunking, indexing, production contract or dependency changed.

Review sources: [SEC-01: OWASP file upload controls](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html),
[CODE-07: engineering review](https://google.github.io/eng-practices/review/reviewer/),
plus PAR-07 and TST-02 above. They inform the review; the captured runs and actual
tests establish the scoped measurements.

Read-only replay of original runs 5/6 passed again: three identical raw captures,
the same quality fingerprint, 14/15 frozen native text/provenance, 15/15
supplemented presence, one recovered identity and zero losses. Order 6/6, cells
7/7, relations 3/3, seven note/reference/paragraph observations and status counts
1 success / 2 needs_review / 0 failed reconcile. Reviewed ancillary provenance
remains NOT_EVALUATED. No real-source extraction or model inference was rerun
during final review; synthetic extraction executes within the test suites.

The original verifier rechecked all 90 originals, 19-record Gold, production pins,
historical 82/78/39 artifacts, resource journals, cleanup and privacy. A separate
read-only SHA-256 check passed **49/49 ML-21 artifact entries**, including earlier
incomplete attempts and final runs. The manifest still hashes to
`188651f671838d0c8e4f20057c8529b0c8329614df04b3846d481c55b31e1d4e`.
Production parser/models/scorer/Gold-validator bytes also equal starting HEAD.
Branch main and upstream divergence 0/0 were verified before staging.

Actual final-review commands and outputs (distinct from the earlier test runs):

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-v1-20261019/review-focused-tmp','tests/unit/test_docx_footnote_candidate.py','tests/unit/test_extraction.py','tests/unit/test_extraction_fidelity.py']))"
# 109 passed in 2.90s
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-v1-20261019/review-broader-tmp','tests/unit/test_docx_footnote_candidate.py','tests/unit/test_extraction_coverage_audit.py','tests/unit/test_extraction_fidelity.py','tests/unit/test_extraction.py','tests/unit/test_pdf_ocr_candidate.py','tests/unit/test_docling_candidate.py']))"
# 309 passed in 12.26s
.venv/Scripts/ruff.exe check src/doclens_ai/extraction/docx_footnote_candidate.py tools/docx_footnote_candidate/benchmark.py tests/unit/test_docx_footnote_candidate.py
# All checks passed!
.venv/Scripts/ruff.exe format --check src/doclens_ai/extraction/docx_footnote_candidate.py tools/docx_footnote_candidate/benchmark.py tests/unit/test_docx_footnote_candidate.py
# 3 files already formatted
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -u evaluation-output/docx-footnote-v1-20261019/verify.py
# PASS both runs, frozen inputs, resources, privacy and pre-stage scope
```

All commands above exited 0; no final-review test failed or was skipped. The two
pytest suites overlap. Formatting of unrelated historical files was not run or
changed. Final review preserves INCONCLUSIVE and production authorization false.
The user-authorized Git gate stages only these four ML-21 files, reviews their
complete staged diff and privacy, and requires `git diff --cached --check` before
the single commit. No push or next major step is included.
