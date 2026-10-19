# ML-22 DOCX footnote locator review packet v1

Date: 2026-10-19. **Execution PASS. Reviewed locator fidelity NOT_EVALUATED.**
QG-01 quality PASS is not established. Production authorization false.

## Scope and acceptance, before real packet generation

Starting main HEAD: `4005adee30375e2a326d5cf8e9cba57bcc894eea`, clean,
upstream divergence 0/0. ML-21 execution PASS, candidate advancement INCONCLUSIVE.
Create only the packet generator, its synthetic tests and this sanitized report.
No existing file, candidate, Gold, scorer or production contract may change.
No staging or commit before external review.

This is QG-00/QG-01 evidence preparation. Execution PASS requires source-verified,
deterministic draft packets, explicit unresolved decisions, resource/failure
isolation, passing synthetic/regression tests and unchanged RAW/Gold. It does not
establish reviewed locator correctness, rendered fidelity or extraction readiness.

Use all existing reviewed DOCX records from the strict frozen Gold, including
controls without reviewed footnotes. Preflight verifies the complete manifest
against originals by SHA-256, size and format, with license provenance metadata.
No cohort change after examining packets. Current preflight: 90 originals,
19 reviewed Gold records, 3 reviewed DOCX, 1 reviewed footnote label.
Run twice into fresh ignored directories. Compare draft bytes and deterministic
summary fields; runtime samples are separate, not new fidelity observations.

Reuse unchanged ML-21 candidate limits and its isolated process monitor: 15 s
logical extraction deadline, 20 s worker guard, sampled process-tree RSS 512 MiB,
64 MiB output bound, 0.02 s sampling. Preparation adds a 15 s hint-building limit
and 10,000 hint entries/document; truncated hints are UNKNOWN. These are bounded
local R&D controls, not an OS hostile-input sandbox. No model, OCR, Office execution,
external-link fetch or network operation occurs in the generator.

References consulted: [PAR-07: Python 3.12 zipfile](https://docs.python.org/3.12/library/zipfile.html),
[PAR-02: python-docx tables](https://python-docx.readthedocs.io/en/latest/user/tables.html),
[EXP-03: Datasheets for Datasets](https://arxiv.org/abs/1803.09010),
[TST-02: pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html).
These support bounded package handling, structural limitations, dataset/review
documentation and synthetic test design; they do not establish measured quality.
External policy/strategy documents described in the supplied audit were not
independently accessed in this step. Any unavailable QG definition stays
UNAVAILABLE; no threshold is invented. The task and repository contracts apply.

## Private draft and locator identity convention

Draft schema: `docx-footnote-locator-review-draft-v1`.
Proposed structural address schema: `docx-footnote-ooxml-address-v1`.
Identity is bound to immutable source SHA-256 and size, actual package part URI,
original lexical `w:id`, note-element child index and paragraph child index.
Indices are zero-based XML child indices, including non-paragraph siblings;
they are not rendered page positions or Gold `part_index`.
Each real reference retains its ordinal, body-rooted XML child path, containing
paragraph path, actual body child index and baseline block index only where
established by ML-21. Repeated references and distinct notes with identical text
remain separate. Note IDs, note ordinals, part identity and Gold indices must
never be treated as interchangeable. No new SourceLocation field is introduced.

All candidate notes/references/paragraphs and issues remain in the private draft,
including incomplete and unreferenced notes. An ancillary failure retains reviewed
label denominators with unknown observations. Candidate status describes ancillary
extraction only; it does not replace the native/production document status.
Controls with no footnote labels have no reviewed locator denominator.

Each reviewed footnote anchor carries its unchanged legacy locator and occurrence
privately. Text diagnostics enumerate candidate paragraphs and non-overlapping
whitespace-normalized occurrence counts; they never select a locator. A unique
text match, duplicate/ambiguous matches, absent text and unavailable observations
all leave `mapping.state=UNRESOLVED`, every decision field null and
`review_status=draft`. The generator contains no review-approval or Gold-writing
path. Automatic XML address checks establish structural correspondence only.

## Independent human review instructions

1. Verify the packet's source SHA/size against the authorized original. Locate it
   locally through the existing private corpus mapping; never publish names/paths.
   Reject changed bytes. Do not use a parser output as the original-document oracle.
2. Open the original in a trusted local viewer with macros, external links and
   active content disabled. Inspect the body reference and displayed footnote,
   surrounding context, repeated occurrences, numbers and unsupported structures.
   Record the viewer/version and local evidence basis in a separate private working
   copy of the draft. Do not edit frozen packets or historic Gold.
3. Independently inspect package relationships and actual XML addresses. Confirm
   the source-bound part URI, original note ID, note/paragraph child indices and
   every selected body reference path. Cross-check with the original's displayed
   note and body linkage. Candidate text hints and index equality are not proof.
4. Record a proposed selected note identity, paragraph child index and reference
   ordinals only after that cross-check, plus reviewer pseudonym/date, original
   evidence basis and ambiguity notes. Multiple references are not duplicate notes;
   identical text in different notes is not one identity. If ambiguity, rendering
   limitations, unsupported content or missing evidence persists, leave unresolved
   or explicitly reject in the separate working copy; never invent coordinates.
5. A second independent reviewer/adjudication is recommended for the legacy index
   convention and ambiguous cases, not falsely claimed here. No real human review
   is performed by this generator. Review of one label cannot establish generality.

## Future Gold-version boundary

This proposed structural convention is not the existing Gold locator convention.
Independent reviewers must explicitly decide whether/how the legacy `part_index`
maps to source-bound identities, or declare it insufficient. Preserve historical
Gold unchanged. A later separately authorized schema/dataset revision would need
review provenance, adjudication, migration/compatibility rules, frozen identities
and independent scoring tests before any reviewed locator PASS. That work,
production routing and candidate advancement are outside ML-22.

## Execution and verification

The two genuine local generations completed on unchanged sources and code, in
fresh ignored directories. Each attempted all three reviewed DOCX records, with
two ancillary success / one needs_review / zero failed. This is the ancillary
candidate's status distribution, not a changed native/production status or an
extraction eligibility decision. No new fidelity scoring, native extraction,
OCR, model inference, Gold revision or human review was performed.

| Opaque source | Observed notes / references / paragraphs | Reviewed footnote labels | Unresolved / reviewed mappings | Ancillary status | Candidate issues |
| --- | ---: | ---: | ---: | --- | ---: |
| c1-0006 | 0 / 0 / 0 | 0 | 0 / 0 | success | 0 |
| c1-0007 | 7 / 7 / 7 | 1 | 1 / 0 | needs_review | 0 |
| c1-0008 | 0 / 0 / 0 | 0 | 0 / 0 | success | 0 |
| Unique total | **7 / 7 / 7** | **1** | **1 / 0** | **2 success, 1 review, 0 failed** | **0** |

The one label, c1-0007/a6, has one textual candidate paragraph. Its entire mapping
remains UNRESOLVED/null. Seven structurally checked notes are not seven reviewed
Gold labels. All three draft packets and extraction captures are byte-identical
across runs; frozen inputs and all deterministic summary fields match. The new
ancillary captures equal the original ML-21 run-5 captures for all three sources.
No note, paragraph, reference or duplicate identity was dropped from that evidence.
Structural XML checks remain distinct from independently reviewed source fidelity.

All 90 source identities and license provenance fields, 19 Gold records and the
full reviewed DOCX cohort were verified before/after. The six reused candidate,
benchmark and extraction-contract modules equal HEAD bytes. Historical pinned
artifacts also passed: ML-21 49, ML-18 82, ML-19 78 and ML-20 39. This verifies
preservation of historical measurements; it is not new inference on those cohorts.
Family-safe independent test coverage, rendered Word fidelity and broad real
RU/KK/EN footnote accuracy remain NOT_EVALUATED. Existing exposed DEV data is not
a fresh blind test. Source rights/review are existing manifest/Gold attestations,
not newly conducted legal or human reviews.

| Fingerprint | SHA-256 / canonical fingerprint |
| --- | --- |
| Manifest | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Source map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Frozen 19-record Gold bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Packet generator | `fc2942ad7d8b88ae650d175bc43ca7c3d280a18f8390d21225020f642eb8f88c` |
| Synthetic tests | `7f121b173fad121ece5acb1ab2534bf683d884ed540a7ed3b1a2cf3e8a9f9ee4` |
| Pre-run protocol snapshot | `a2996bc32144f23d6633e98be6f6a300d68baa8e18d34a614977495752bf59a6` |
| Both frozen inputs files | `f370a4872643c66eb588e388cf6d3f775121453923a1135ad2ef2128a8ada11c` |
| Both deterministic report fingerprints | `68be27905d720d229c5419291b6ea0cb645b1f65cd264051458ff68e6678d226` |
| Run-1 summary bytes | `02a6e32b227ccedb216b24c1d1ba7f2d9ffe1581cc11e44b9f7d1b32e4d755b8` |
| Run-2 summary bytes | `3dc54aae1a024f4605774c12aa47b216653a7d574b2e0b44b4a371539ec7ea8a` |
| Run-1 eleven-artifact manifest | `b00080136b33c8d944a8d0e2fa4c46daf1c76549ae67357d40d29f472d8c2154` |
| Run-2 eleven-artifact manifest | `fa07b237a01bcff7fdc18f3495810db69633d29e3a4e4f5e80bb41816333a98d` |

Runtime: existing Python 3.12.3, Pydantic 2.14.0, psutil 7.1.0, Windows AMD64.
Serial isolated CPU workers; no dependency installed or changed. Built-in XML/ZIP
and unchanged ML-21 candidate/monitor are used. Each run pins code, source/Gold,
candidate limits, guards, runtime and draft settings in `inputs.json`.

| Measured worker resource | Run 1 | Run 2 |
| --- | ---: | ---: |
| P50 / P95 seconds, nearest rank, n=3 | 1.313 / 1.500 | 1.297 / 1.485 |
| Peak sampled process-tree RSS, bytes | 88,666,112 | 89,378,816 |
| Worker / cleanup failures | 0/3 / 0/3 | 0/3 / 0/3 |

Worker time includes startup/imports, input hashing, ancillary extraction, XML
address replay and private capture writing. It excludes parent corpus verification,
draft building and summary serialization. Parent RSS and separate extraction-stage
latency are NOT_EVALUATED. Sampled 0.02 s RSS can miss spikes. No partial files
or live packet workers remained. Bounded JSON publication uses fresh owned output
directories; this is not protection against a hostile concurrent filesystem actor.

### Actual tests and corrections

The first pytest command had 1 pass / 24 fixture setup errors because its new
scratch parent did not yet exist. After verifying ignore rules and creating it,
the second command ran 24 passed / 1 failed: the new worker-stage check rejected
the monitor's existing journal. That reproduced a harness defect before real
execution. The smallest fix permits exactly the parent journal, rejects prior
captures and checks link safety. Its synthetic regression then passed.
Initial Ruff reported 10 line-length errors; only the two new Python files were
formatted. A post-fix focused run passed 134 tests. Additional missing/different
size and timeout/memory/worker-failure reporting checks brought final coverage to
**139 passed in 3.82 s**, including **30 new synthetic cases** and the unchanged
ML-21, extraction and fidelity regressions. No final failures or skips.

Synthetic coverage includes relocated parts; multiple/repeated references;
duplicate note text and repeated paragraph text; normal ID zero; unsupported note
tables; empty notes/no text match; dangling relationships/corrupt/oversized packages;
strict source hash/size/format and symlink rejection; preserved inputs; explicit
synthetic Gold opt-in; hint/output/time bounds; atomic-publication failure and
existing-partial ownership; fresh ignored output; worker staging; sanitized CLI
errors; no-label denominators; failed/timeout/memory outcomes. Synthetic cases
are separately identified and never counted as reviewed real sources.

Actual commands from the repository root; the outputs below are measured, not
expected. Existing output directories must not be reused:

```powershell
git status --short --untracked-files=all
git branch --show-current
git rev-parse HEAD
# Initially clean; main; 4005adee30375e2a326d5cf8e9cba57bcc894eea
git check-ignore evaluation-output/docx-footnote-locator-review-v1-20261019
New-Item -ItemType Directory -Path evaluation-output/docx-footnote-locator-review-v1-20261019 -ErrorAction Stop | Out-Null
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-locator-review-v1-20261019/test-tmp-4','tests/unit/test_docx_footnote_locator_review_packet.py','tests/unit/test_docx_footnote_candidate.py','tests/unit/test_extraction.py','tests/unit/test_extraction_fidelity.py']))"
# 139 passed in 3.82s
.venv/Scripts/ruff.exe check tools/docx_footnote_candidate/locator_review_packet.py tests/unit/test_docx_footnote_locator_review_packet.py
# All checks passed!
.venv/Scripts/ruff.exe format --check tools/docx_footnote_candidate/locator_review_packet.py tests/unit/test_docx_footnote_locator_review_packet.py
# 2 files already formatted
Copy-Item -LiteralPath docs/eda/docx_footnote_locator_review_v1.md -Destination evaluation-output/docx-footnote-locator-review-v1-20261019/protocol-before-run.md
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/docx_footnote_candidate/locator_review_packet.py --output evaluation-output/docx-footnote-locator-review-v1-20261019/run-1
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/docx_footnote_candidate/locator_review_packet.py --output evaluation-output/docx-footnote-locator-review-v1-20261019/run-2
# Both: status PASS, quality NOT_EVALUATED, identical 68be2790... fingerprint
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -u evaluation-output/docx-footnote-locator-review-v1-20261019/verify.py
# PASS both 11-artifact manifests, source90/Gold19, 3/3 equal captures/drafts,
# 7/7/7 XML identities, 1 unresolved / 0 reviewed, resources/cleanup,
# historical artifacts49+82+78+39, privacy, exact three-file scope, no staging
git diff --check
git status --short --untracked-files=all
```

The read-only replay performs no new candidate extraction. All final commands
above exit 0; earlier failed commands are disclosed separately. The pre-run
snapshot preserves the PENDING protocol before actual execution; the report's
later result edits do not change it. Final report generation changes only this
new Markdown file, not the frozen Python or any captured packet.

The final ignored `artifact-manifest.json` pins **26 immutable files**: both
eleven-file run contents and their two manifests, the pre-run protocol and the
read-only verifier. All 26 hashes passed. Temporary synthetic files and the
review diff are not presented as new measured observations. Manifest SHA-256:
`85099f2533c97d43648ae0075520161d2a4888df011fa6656b2b52cd3121d499`.
Verifier SHA-256:
`2ed998560ac44c754e951b885334595d70b819964781d90902981595e995d2f9`.

`git diff --check` returned exit 0 with no output. Because all three files are
new/untracked, each was additionally checked using the actual command form
`git -c core.autocrlf=false diff --no-index --check -- /dev/null <allowlisted-path>`.
Each returned exit 1 for the expected new-file difference, with no stdout/stderr
whitespace diagnostics. Full new-file contents/diffs were reviewed and retained
in ignored `full-review.diff`. No repository newline configuration was changed.
Existing tracked diff and staged diff are empty; HEAD is unchanged.

### Privacy and review handoff

Only the three authorized new text files are Git-visible. Private drafts, Gold
text, actual part identities, source captures, resource journals and verification
scratch stay in verified ignored local storage. Code review and scans cover
original basenames, reviewed anchor strings of at least 12 characters, private
path/credential patterns, UTF-8/LF and whitespace. The content-free CLI summary
also passes private text/name exclusion. Full new-file diff review supplements
automated scans; shorter/common text cannot be conclusively screened by exact
matching alone. No sources, Gold, models, PDFs, DOCX binaries or generated outputs
are staged. No credentials or private data are uploaded.

Execution PASS concerns the reproducible preparation tool and its checks only.
ML-21 advancement remains INCONCLUSIVE; reviewed locator fidelity remains
NOT_EVALUATED, reviewed mappings 0/1, production authorization false. The remaining
gate is independent original-document review and explicit adjudication of the
legacy locator convention under a separately authorized future Gold version.
Do not stage/commit before external review. Stop after ML-22.

## ML-22 FIX: assertion-dependent verifier boundary

This appendix supersedes the unrestricted execution claim for optimized Python;
the original run-1/run-2 measurements, hashes and earlier protocol above remain
historical and unchanged. **Corrective execution PASS** applies to guarded ML-22.
Locator fidelity remains NOT_EVALUATED and production authorization false.

Starting HEAD/main remains `4005adee30375e2a326d5cf8e9cba57bcc894eea`.
The three ML-22 files were already untracked. Unrelated working changes to
`AGENTS.md`, `README.md` and `README_SOURCE_MAP.md` are preserved by byte hashes;
they are not part of this fix. No file is staged and no commit is authorized.

### Reproduced defect and minimal correction

The inherited `benchmark.verify_ancillary` uses assertions for XML identity/text
validation. Python removes those checks with `-O` or `PYTHONOPTIMIZE=1`. A public
synthetic package with a deliberately changed captured note ID was rejected with
`REJECTED_ASSERTION` at optimize=0, but returned `EVALUATED` at optimize=1 for both
activation methods. No private source or Gold was used in that reproduction.
The new regression matrix, before the fix, returned **8 failed / 4 passed / 30
deselected in 38.16 s**: all optimized parent/worker API/CLI paths still succeeded.

The only generator change is an explicit `sys.flags.optimize != 0` rejection.
`generate` checks before output/preflight; worker checks before source access or
verification; CLI checks before dispatch. This is an ordinary conditional, not
an assertion. The API raises a fixed `PacketError`; the worker returns failure
code 2; CLI emits its existing content-free BLOCKED diagnostic and returns 2.
Neither source/exception details nor a successful address check are published.
No change is made to ML-21's verifier, candidate, parser, scorer or production.
Direct optimized use of the inherited ML-21 helper remains outside this correction.

Regression tests use real subprocess flags/environment across four entry points
and three modes. Parent-side pytest assertions run normally; optimized children
do not use assertions as their test oracle. Tests check exit codes, exact sanitized
output, absent preflight/verifier markers and absence of result/draft/summary files.
Normal-mode synthetic generation and worker verification must still succeed.

References: [Python 3.12 optimization flags](https://docs.python.org/3.12/using/cmdline.html#cmdoption-O),
[CODE-07: engineering review](https://google.github.io/eng-practices/review/reviewer/),
[TST-02: pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html).

### Corrective verification protocol, before real reruns

Keep source/Gold, cohort, selection, candidate limits, guards and review semantics
unchanged. Execute two fresh normal-mode generations under ignored
`fix-optimization-v1/run-1` and `run-2`; never overwrite the original captures.
PASS requires optimized rejection, focused/broader regression tests, both real
normal-mode executions, byte-identical draft/capture results versus original
ML-22, matching non-code frozen settings, unchanged source/Gold, privacy and scope.
Only generator/test code hashes and containing report fingerprints may change.
Timing/resources may differ. No new quality threshold or human review is claimed.

### Actual corrective results

The focused ML-22/ML-21/extraction/fidelity command passed **151 tests in 35.40 s**;
the broader extraction/coverage/OCR/Docling command passed **351 tests in 57.04 s**.
Both JUnit outputs contain zero failures, errors or skips and all **12/12** new
subprocess cases passed. The suites overlap and must not be summed. ML-22 now
has 42 synthetic cases, including four normal-mode positives and eight optimized
rejections in the new matrix. No successful address checks, drafts or summaries
were emitted in those eight rejected paths; neither preflight nor the inherited
verifier was reached. Ruff passed; format check reported two files already formatted.

Both genuine corrected real-corpus runs passed on all three DOCX. Each repeats
the original content-free summary: 2 ancillary success / 1 needs_review / 0 failed,
7 notes / 7 references / 7 paragraphs, 1 unresolved / 0 reviewed mappings, zero
candidate issues. Three raw captures and three draft packets are byte-identical
between corrected repetitions AND versus the original ML-22 run-1. The sole
textual candidate remains a hint, never an adjudicated locator. The code-independent
summary and all non-code frozen settings equal the original. Only the generator
and test hashes differ in the frozen code map. No quality criteria were changed.

| Corrective fingerprint | SHA-256 / canonical fingerprint |
| --- | --- |
| Guarded generator | `866b637a5083fc55efe9e8cb82790d81acc8d83ab4ae74557eedd2a35fc355a5` |
| Tests with subprocess matrix | `a02a41b07ca0d0f8a493661c4ec73a59b69176f1ddffd11f5321021a066f8071` |
| Pre-rerun protocol snapshot | `6c90ddd5153919fd79890a7502fb7532a94a6aaa2ce351dbc13a7012d9afa7b3` |
| Both corrective inputs files | `4ccf4256b3b82b6bb5e8ee99c5d9e92865e5e605da07997954cb00463d0f7d36` |
| Both corrective deterministic report fingerprints | `26225530ee6b920b9954bda40285c2a7e37e9dde079faac544516063aae3f62a` |
| Corrective run-1 summary bytes | `5ad816f3e9a5f361052dce6c9e5d9748baac2eaf25af4318482451fcdf979ad7` |
| Corrective run-2 summary bytes | `0325a1a3e5c08c94e294b133547b4fb88d1df1461aad64d4587e1147c71f8d16` |
| Corrective run-1 eleven-artifact manifest | `fa3350bf298dcbb8f704b262cbf672e4eb6b7acbe159aa7ac442e24c1c141b02` |
| Corrective run-2 eleven-artifact manifest | `9a8c8d68a17bc216eb65155780df7c5e35ccbe1646faed564c71aa2832eb139f` |

| Measured worker resource, same scope/sampling as original | Corrective run 1 | Corrective run 2 |
| --- | ---: | ---: |
| P50 / P95 seconds, nearest rank, n=3 | 1.922 / 2.250 | 1.921 / 2.016 |
| Peak sampled process-tree RSS, bytes | 89,149,440 | 89,190,400 |
| Worker / cleanup failures | 0/3 / 0/3 | 0/3 / 0/3 |

These are worker measurements, excluding parent corpus checks and draft building;
parent RSS/stage-only latency remain NOT_EVALUATED. Sampling can miss spikes.
No resource limits changed. No run partial files or live candidate workers remain.
Original sources and Gold still match the manifest/source-map/Gold hashes above.
Old pinned artifacts are unchanged: original ML-22 26, ML-21 49, ML-18 82,
ML-19 78, ML-20 39. The inherited verifier and all six reused code files equal HEAD.
The earlier verifier script/outputs are retained unchanged; a new guarded local
read-only verifier handles the corrective code hashes and pre-existing worktree.
The original verifier was not reused as if its old code/scope pins still applied.

Exact corrective commands, executed from repository root (fresh directories):

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -u evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/reproduce.py
# REPRODUCED: normal REJECTED_ASSERTION; -O and PYTHONOPTIMIZE=1 EVALUATED
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/test-before','tests/unit/test_docx_footnote_locator_review_packet.py','-k','subprocess_optimization_boundary']))"
# Before generator fix: 8 failed, 4 passed, 30 deselected in 38.16s (exit 1)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/test-focused','--junitxml=evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/focused.xml','tests/unit/test_docx_footnote_locator_review_packet.py','tests/unit/test_docx_footnote_candidate.py','tests/unit/test_extraction.py','tests/unit/test_extraction_fidelity.py']))"
# 151 passed in 35.40s (exit 0)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp=evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/test-broader','--junitxml=evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/broader.xml','tests/unit/test_docx_footnote_locator_review_packet.py','tests/unit/test_docx_footnote_candidate.py','tests/unit/test_extraction_coverage_audit.py','tests/unit/test_extraction_fidelity.py','tests/unit/test_extraction.py','tests/unit/test_pdf_ocr_candidate.py','tests/unit/test_docling_candidate.py']))"
# 351 passed in 57.04s (exit 0)
.venv/Scripts/ruff.exe check tools/docx_footnote_candidate/locator_review_packet.py tests/unit/test_docx_footnote_locator_review_packet.py
# All checks passed! (exit 0)
.venv/Scripts/ruff.exe format --check tools/docx_footnote_candidate/locator_review_packet.py tests/unit/test_docx_footnote_locator_review_packet.py
# 2 files already formatted (exit 0)
Copy-Item -LiteralPath docs/eda/docx_footnote_locator_review_v1.md -Destination evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/protocol-before-reruns.md
# Snapshot was taken before real reruns, while corrective verification was PENDING.
Remove-Item Env:PYTHONOPTIMIZE -ErrorAction SilentlyContinue
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/docx_footnote_candidate/locator_review_packet.py --output evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/run-1
# PASS / NOT_EVALUATED / 26225530... (exit 0)
Remove-Item Env:PYTHONOPTIMIZE -ErrorAction SilentlyContinue
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Join-Path (Get-Location) '.venv/Lib/site-packages') + ';' + (Get-Location).Path)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B tools/docx_footnote_candidate/locator_review_packet.py --output evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/run-2
# PASS / NOT_EVALUATED / 26225530... (exit 0)
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -u evaluation-output/docx-footnote-locator-review-v1-20261019/fix-optimization-v1/verify.py
# PASS: original-normal byte equality, both manifests, source90/Gold19,
# matrix12/12, resources, privacy, preserved unrelated changes, no staging
git diff --check
git status --short --untracked-files=all
```

The initial failing regression command is evidence of the defect, not a final
failure. All post-fix mandatory checks passed; nothing was skipped. Raw/Gold,
existing ML-21 code, original artifacts and user changes were not edited. Private
fixtures/captures/journals stay ignored; no production wiring or new dependency.
The remaining direct ML-21 optimized-helper limitation is reported, not silently
fixed beyond scope. Independent human adjudication is still required: reviewed
locator fidelity NOT_EVALUATED, 0/1 reviewed mappings, production authorization false.
No staging/commit or ML-23 is authorized by this corrective execution PASS.

The corrective ignored manifest pins **37 immutable artifacts**: two runs with
their manifests, the original three-file snapshots and starting hashes, synthetic
reproduction script/results/three packages, the pre-rerun protocol, two JUnit
outputs and the guarded read-only verifier. All 37 SHA-256 entries passed.
Temporary pytest files and review diffs are excluded from measured observations.
Corrective manifest SHA-256:
`e410fecfe9d6c42a8212f02a811c84fd3292fe9ea3337b710b19e4300669eac7`.
Corrective verifier SHA-256:
`71f49b6b8df8077b3380a2cca72a163a4709321192335cf2b34835b5a97344ee`.

Final diff/whitespace checks cover complete ML-22 untracked files, plus a focused
comparison against the saved pre-fix versions. Existing user changes remain
byte-identical to their starting hashes. The final worktree therefore contains
three ML-22 untracked files and the same three unrelated changes recorded at
preflight; it is intentionally not clean. No staged changes, commit or push.
