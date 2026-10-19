# ML-19 expanded selective PDF OCR evaluation v1

Date: 2026-10-19. **Execution: PASS. Candidate: INCONCLUSIVE** for expanded
OCR generalization. **Production authorization: false.** All observed regression
guardrails passed, but none of the eight additional documents invoked Tesseract.
The ML-18 pilot's narrower PROMOTE_FOR_FURTHER_OFFLINE_EVALUATION verdict is
unchanged. Production pypdf and the frozen Docling REJECT decision are unchanged.

## Frozen protocol and scope

Starting HEAD: `5a2cf7af94d65c9d9b6c005e438a1019b6a93f55`, `main`,
`feat: add offline selective PDF OCR benchmark`. Starting `git status --short`
was empty. Root AGENTS.md and extraction-benchmark / ML-experiment skills were
read; no applicable nested AGENTS.md was found on the affected ancestor paths.
Only this report is created in Git; scripts and captures remain ignored locally.

Before inference, the runner's freeze command and a separate ML-19 `protocol.json`
fixed exactly c1-0031, c1-0032, c1-0033, c1-0035, c1-0040, c1-0043, c1-0048,
c1-0049. No cohort changes, new labels, human-review claim, parameter tuning,
dependency installation or production integration occurred. The existing Gold
review attestation is reused. These are previously exposed, purposively selected
DEV documents, not an independent sealed TEST. Document-family independence is
NOT_ESTABLISHED; no new split, GroupKFold, fitting or training was performed.

H1: the unchanged selective OCR candidate preserves baseline evidence and source
provenance across these additional reviewed PDF layouts without critical regressions.

Preregistered primary guardrail: **zero newly lost required anchors**. REJECT if
any native block text/source/multiplicity is lost, any previously passed reviewed
provenance/order/table/numeric check is lost, a new extraction failure or eligibility
downgrade occurs, or provenance/privacy is fabricated or violated. Missing observations
remain UNKNOWN with their original populations retained. Advancement additionally
requires at least one additional English document with genuine OCR and a reviewed
anchor attributable to a new OCR block at its reviewed page. Otherwise coverage is
INCONCLUSIVE. Execution PASS requires two unchanged paired runs, deterministic replay,
input/resource/privacy/cleanup verification and focused tests. These criteria preceded
all 32 captures; local file ordering also confirms that sequence.

The runner retains its historical `ML-18-v1` profile and ML-18 `gate` metadata.
Those fields were not rewritten or used as ML-19 acceptance criteria. The separately
hashed ML-19 protocol supplies the new decision gate. Neither inference nor page
selection consumes Gold labels; unchanged scoring uses them only after extraction.

The cohort has **7 English PDFs and 1 Welsh PDF, c1-0043**. English-only OCR remains
fixed; native Welsh evidence preservation is measured, Welsh OCR accuracy is not.
All eight manifest licenses are Open Government Licence v3.0. Read-only verification
matched **90/90 original files** by SHA-256, size and format and validated all
**19 frozen reviewed Gold records**. No RAW, Gold, previous report or capture changed.

## Unchanged candidate and runtime

The committed ML-18 runner, production parser, models, scorer and Gold validator have
identical hashes to the final ML-18 profile. Selection remains fewer than 20 native
non-whitespace characters; qualifying pages render at 300 dpi. OCR requires at least
0.001 of validated grayscale pixels below 245. Tesseract stays **eng / OEM 1 / PSM 3 /
one thread**, with no seed option, correction, fuzzy matching or retries. Whole-page
whitespace-only duplicate suppression is unchanged. Actual page provenance is retained;
no row/column/table/diagram coordinates are synthesized.

Runtime rechecked locally: **Tesseract 5.4.0.20240606**, Leptonica 1.84.1,
installed languages eng/osd, **Poppler 26.07.0**, Python 3.12.3, pypdf 6.20.0,
Pydantic 2.14.0 and psutil 7.1.0. Executable, English traineddata, interpreter,
51 Tesseract DLL and 121 renderer DLL pins exactly match ML-18. These are distribution
file hashes, not a traced loaded-module graph. The bundled model's separate upstream
Git revision remains UNKNOWN; its exact installed bytes are pinned. The existing
engine license text is Apache-2.0; no new package or model was downloaded.

Unchanged per-document ceilings: 50 MiB input; 40 source pages; 10 eligible/rendered
pages; 20 million pixels/page; 5 million combined native/OCR characters, reserving
all native text first; 256 MiB sampled scratch; 3 GiB sampled worker-tree RSS;
600 seconds/document; 60 seconds/tool; 0.02-second polling. Memory, timeout, disk
guard precedence and cleanup are unchanged. No full Docling conversion or GPU ran.

Two fresh serial runs each launched a baseline worker then a candidate worker per
source, with fresh process initialization. They ran separately, without concurrent
test workloads. OS caches were not reset. Runtime measurements include worker startup,
native extraction and, where selected, rendering. They are not cold-cache benchmarks.

## Per-document results

Every value below is identical in runs 1 and 2 and between baseline and candidate.
N/E means no reviewed labels, not a successful zero-denominator test.

| Source | Pages | Required text | Provenance | Order | Cells | Relations | Numeric-bearing anchors | Status, baseline -> candidate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| c1-0031 | 1 | 7/7 | 7/7 | 4/5 | N/E | N/E | 2/2 | success -> success |
| c1-0032 | 1 | 10/10 | 10/10 | 3/4 | N/E | N/E | N/E | success -> success |
| c1-0033 | 1 | 9/9 | 1/9 | 0/3 | 0/8 | 0/8 | N/E | success -> success |
| c1-0035 | 1 | 6/8 | 6/8 | 4/5 | N/E | N/E | N/E | success -> success |
| c1-0040 | 1 | 8/8 | 4/8 | 2/3 | 0/4 | 0/4 | 1/1 | success -> success |
| c1-0043 | 4 | 6/6 | 6/6 | 4/4 | N/E | N/E | 3/3 | needs_review -> needs_review |
| c1-0048 | 17 | 11/11 | 8/11 | 6/6 | 0/3 | 0/1 | 3/3 | success -> success |
| c1-0049 | 8 | 12/12 | 7/12 | 4/6 | 0/5 | 0/5 | 4/4 | success -> success |
| Expanded eight | **34** | **69/71** | **49/71** | **27/36** | **0/20** | **0/18** | **13/13** | **7 success, 1 needs_review, 0 failed** |

Recovered identities: **[] for each document, each run**. Newly lost identities:
**[] for each document, each run**. The only globally missing required anchors are
**c1-0035/a2 and a7**, absent in both baseline and candidate. Their underlying cause
was not diagnosed here. Selection sees sufficient native text on that page, so this
candidate does not attempt recovery. A success status does not establish fidelity.

Reviewed provenance failures are unchanged, with no convenient global-text occurrence
substituted for the expected source locator:

| Source | Unlocated anchor IDs | Count |
| --- | --- | ---: |
| c1-0033 | a2-a9 | 8 |
| c1-0035 | a2, a7 | 2 |
| c1-0040 | a3-a6 | 4 |
| c1-0048 | a7-a9 | 3 |
| c1-0049 | a6-a10 | 5 |
| Total | All other anchors located | **22/71** |

The two absent anchors and twenty present-but-unlocated anchors remain distinct.
The pypdf flat-text outputs do not provide the structured table cells required by
the 20 cell and 18 relationship checks. This experiment neither resolves those
failures nor reinterprets ordinary text as a structured cell. Nine reading-order
checks still fail; all individual order/cell/relation outcomes, not just aggregate
counts, are unchanged. Displayed values, spreadsheet formulas/caches and diagram
relationships are NOT_EVALUATED.

All **34 native blocks/run**, including empty-page blocks, text, complete source
locators, order and warnings are preserved. Full baseline/candidate ExtractionResult
equality holds for every document; results also match between repetitions. Multiset
and per-anchor global/constrained occurrence counts were independently replayed.
There are no duplicate complete native-page text groups in this cohort; repeated
substrings still count separately. Repeated global anchor occurrences are:

| Source | Opaque IDs and occurrence counts, identical before/after and in both runs |
| --- | --- |
| c1-0031 | a2=2, a6=2 |
| c1-0032 | a1=2, a4=2, a7=2 |
| c1-0033 | a4=2, a5=5, a7=8, a9=8 |
| c1-0035 | a1=2 |
| c1-0040 | a3=4, a4=8, a5=4, a6=4 |
| c1-0043 | a6=2 |
| c1-0048 | a1=14, a3=2, a4=2, a8=2, a10=2, a11=2 |
| c1-0049 | a6=2, a7=2, a9=33, a10=43 |

These are substring counts, not claims of independently correct table relations.
Reviewed occurrence selectors and all non-null locator components remain unchanged.
Numeric-bearing identities: c1-0031/a2,a4; c1-0040/a2; c1-0043/a2,a5,a6;
c1-0048/a2,a5,a6; c1-0049/a2,a5,a9,a10. Their **13/13 native preservation**
does not measure OCR number recognition or exhaustive numerical fidelity.

## Page selection and resources

Each run accounts for all 34 pages: **33 native skips, 1 selected/rendered blank
skip, 0 OCR invocations, 0 added OCR blocks**. Only c1-0043/page 4 is eligible;
its observed rendered foreground fraction is exactly 0, below the fixed 0.001
threshold. Renderer exit code is 0 in each repetition. Pages 1-3 remain native.
All other documents are entirely native. No empty OCR, tool error, timeout,
resource-limit termination or cleanup failure occurred. The blank-render signal
is an observed image statistic, not an independent semantic review of that page.

| Source | Run 1 baseline/candidate seconds | Run 2 baseline/candidate seconds | Candidate peak RSS bytes, run 1 / run 2 |
| --- | ---: | ---: | ---: |
| c1-0031 | 1.141 / 1.109 | 1.141 / 1.109 | 60,473,344 / 60,260,352 |
| c1-0032 | 1.156 / 1.141 | 1.172 / 1.172 | 61,161,472 / 61,280,256 |
| c1-0033 | 1.125 / 1.125 | 1.109 / 1.156 | 61,079,552 / 60,882,944 |
| c1-0035 | 1.140 / 1.157 | 1.141 / 1.141 | 60,772,352 / 61,026,304 |
| c1-0040 | 1.140 / 1.141 | 1.203 / 1.140 | 61,378,560 / 61,546,496 |
| c1-0043 | 1.219 / 1.593 | 1.219 / 1.641 | 93,753,344 / 93,782,016 |
| c1-0048 | 1.485 / 1.437 | 1.468 / 1.469 | 64,413,696 / 64,950,272 |
| c1-0049 | 1.515 / 1.516 | 1.547 / 1.515 | 64,389,120 / 64,626,688 |

| Population/run | Baseline P50/P95 seconds | Candidate P50/P95 seconds | Baseline / candidate peak tree RSS bytes |
| --- | ---: | ---: | ---: |
| Expanded 1 | 1.141 / 1.515 | 1.141 / 1.593 | 64,663,552 / 93,753,344 |
| Expanded 2 | 1.172 / 1.547 | 1.156 / 1.641 | 64,458,752 / 93,782,016 |
| Historical pilot 3 | 1.157 / 3.109 | 2.687 / 9.515 | 73,981,952 / 134,033,408 |
| Historical pilot 4 | 1.234 / 2.969 | 2.500 / 11.094 | 73,850,880 / 133,857,280 |
| Descriptive 12, expanded 1 + pilot 3 | 1.156 / 3.109 | 1.437 / 9.515 | 73,981,952 / 134,033,408 |
| Descriptive 12, expanded 2 + pilot 4 | 1.203 / 2.969 | 1.469 / 11.094 | 73,850,880 / 133,857,280 |

P50/P95 use nearest-rank over 8, 4 or 12 document durations respectively; for eight
documents P95 is the maximum. Combined resource rows mix the historical pilot with
new captures and are descriptive only. Peak sampled candidate disk is 8,708,040 /
8,708,115 bytes in expanded runs 1/2; baseline 40,070 / 40,089 bytes. Journals
reconcile to reported peaks. Polling can miss short spikes; summed process-tree RSS
can count shared memory more than once. These are sampled guards, not a hard OS
sandbox. Every worker has a final zero-RSS sample after exit; nonfinal samples and
observed peaks are positive. All upper bounds hold, all 32 worker cleanups report
true, no page-image residue or live Tesseract/renderer process remains.

## Separate and combined populations

The existing ML-18 final runs 3/4 were replayed read-only, not rerun. Their 82 pinned
artifacts, earlier attempts 1/2 and resource-budget correction history remain unchanged.
The old execution HEAD differs from ML-19's committed HEAD, as expected; code,
runtime/model, limits, OCR configuration, manifest and Gold pins are identical.

| Population, unique documents | Pages | Text, baseline -> candidate | Provenance | Order | Cells | Relations | Numeric |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ML-18 pilot, 4 | 50 | 10/19 -> 19/19 | 6/19 -> 15/19 | 4/10 -> 9/10 | 0/4 -> 0/4 | 0/2 -> 0/2 | 9/9 -> 9/9 |
| ML-19 expanded, 8 | 34 | 69/71 -> 69/71 | 49/71 -> 49/71 | 27/36 -> 27/36 | 0/20 -> 0/20 | 0/18 -> 0/18 | 13/13 -> 13/13 |
| Descriptive combined, 12 | 84 | **79/90 -> 88/90** | **55/90 -> 64/90** | **31/46 -> 36/46** | **0/24 -> 0/24** | **0/20 -> 0/20** | **22/22 -> 22/22** |

Pilot statuses remain 2 success / 2 needs_review / 0 failed; expanded 7 / 1 / 0;
combined 9 / 3 / 0. All documents and original labels stay in denominators.
Expanded: 16 paired document attempts, 142 anchor comparisons, 32 raw captures and
32 resource journals. Combined final pairs: 24 paired document attempts and 180
anchor comparisons over **12 unique documents and 90 unique anchors**, not 24/180
new independent examples. Baseline and candidate each contribute their own score
observations; repetitions are not pooled into the unique denominators.

All nine combined recovered identities originate exclusively in ML-18: c1-0041/a1-a4
and c1-0044/a1-a5. No combined new loss. Combined page accounting is **78 native,
5 actual OCR, 1 blank-render skip / 84 pages** per repetition pairing. ML-19 adds
zero OCR recoveries. Pilot controls c1-0045 and c1-0050 remain unchanged, including
the four known c1-0045 provenance failures. Diagram relations and RU/KK accuracy
remain NOT_EVALUATED; there is no new Welsh OCR or unreviewed numeric claim.

## Reproducibility fingerprints

All values are SHA-256 unless described as a canonical quality fingerprint.
Ignored root: `evaluation-output/pdf-selective-ocr-expanded-v1-20261019`.

| Item | Fingerprint |
| --- | --- |
| Corpus manifest | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Approved Gold bytes, 19 records | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Approved Gold normalized | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| ML-19 protocol bytes | `88641843010c34c55ed29f8e98c8b8d2edaac9cb402afc13286c665eb7ee1f27` |
| Runner freeze bytes | `c7864d6195016e683ccb67a6add4afd80840114a2b9a8c08733b0e0714e87c15` |
| Runner freeze canonical | `e1f7d88a6cff6bbd1234ba32a84a8fa55ca030ffa6f242dbce2229017c158159` |
| Runner, unchanged | `d0676b4aec8eb660e50b909b00f4ad57963439e78d876495386e9a13f59f5aec` |
| Production parser, unchanged | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| Scorer, unchanged | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Tesseract executable | `babb405f4366b480d02cd8ff2bac8d497170f6c1711ce6f3d5d8bf0fb7fa6ed9` |
| English traineddata | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` |
| Poppler renderer | `bbb9d17eae3d4c4219ef062924989d0305c82223b3ea7a4d7558d327f9aae2f5` |
| Expanded run 1 metrics bytes | `fa8fc742566eb65b6ae735060c12ac09dfc953a72147ef389c6f3a512d5d7348` |
| Expanded run 2 metrics bytes | `ef7ee602b2187682b82f475a559f2656a973fef908f69be848398b60e726cf94` |
| Both expanded canonical quality fields | `561b4086a850582a75730008df7a5cbdf556af887063ee1d2b4afdabc5d33cce` |
| Expanded read-only verifier | `9f1aa50161bd3bff4f2dc6e7e454d2be1bd4fbe742776e43367f06f3ce1a2098` |
| Expanded 78-entry experiment artifact manifest | `bf7d429b21b340ef4f8ff9dde9bdbb0f30302e9bf137e7e8480995f3da5136b8` |
| Pilot 82-entry artifact manifest, unchanged | `4086c46dde4a8e4722720218b84ed876180d701eb7f2e018173339afaf5901ee` |
| Pilot final canonical quality | `160a5e6962a0114b06ea59282ed5114847415ec7c4c3774e100045494c1f740a` |

Runtime-dependent timings/disk journals differ; every non-runtime quality field,
per-anchor outcome and ExtractionResult is exactly equal across repetitions.
The 78-entry manifest covers both capture/journal sets, metrics, run logs,
preregistration, replay scripts, retained scratch-verifier revision, summary and
verification-deviation records. Terminal report/privacy checks are separate audits.

| Source | Bytes | Frozen source SHA-256 |
| --- | ---: | --- |
| c1-0031 | 1,732 | `1179d9f2925a83d6503608b8049b2a23b8e81f15a42d60e7bdd0bce52d6cc253` |
| c1-0032 | 20,617 | `5f9082eabbb52eaf71510592a043958cb7f67b955158f7d9d12435783bc52471` |
| c1-0033 | 29,702 | `081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd` |
| c1-0035 | 38,361 | `94a5b7cdc01f39d482683e7480f4f593089c54731d333d60544558db903b8c3a` |
| c1-0040 | 64,968 | `18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344` |
| c1-0043 | 91,484 | `b70a5d33160ee12eba6b5f66e305df69b6d504389c11c142657c41d2be45c3ce` |
| c1-0048 | 228,777 | `5928ffa7f5f8d44678a56d810794f4263e4a3db9a7d87422ec8d3c6907186f4f` |
| c1-0049 | 254,032 | `fa821b92dde14335883c0327f70851d9b5813feea8584136eb125fe8833a9240` |

## Executed commands and actual results

Commands below were executed from the repository root in PowerShell; paths are
repository-relative to avoid publishing machine-private paths. Scratch scripts
are local ignored reproducibility aids, not new repository dependencies.

```powershell
git rev-parse HEAD
git branch --show-current
git status --short
git check-ignore evaluation-output/pdf-selective-ocr-expanded-v1-20261019/protocol.json
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
$ocrPath = Join-Path $env:ProgramFiles 'Tesseract-OCR/tesseract.exe'
$rendererPath = (Get-Command pdftoppm).Source
$tessdataPath = Join-Path $env:ProgramFiles 'Tesseract-OCR/tessdata'
& $ocrPath --version
& $ocrPath --list-langs
pdftoppm -v
$benchArgs = @('tools/pdf_ocr_candidate/benchmark.py',
  '--documents','c1-0031','c1-0032','c1-0033','c1-0035',
  'c1-0040','c1-0043','c1-0048','c1-0049',
  '--tesseract',$ocrPath,'--renderer',$rendererPath,'--tessdata',$tessdataPath,
  '--registration','evaluation-output/pdf-selective-ocr-expanded-v1-20261019/registration.json')
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --freeze
```

Git returned the starting HEAD/main above and empty status; check-ignore returned
the exact requested ignored path. Live runtime versions/languages are as recorded
above. Freeze exited 0 with documents=8 and canonical fingerprint
`e1f7d88a6cff6bbd1234ba32a84a8fa55ca030ffa6f242dbce2229017c158159`.
Before the following run commands, local Python preflight compared all shared ML-18
pins, verified source/Gold populations, and wrote the ML-19 protocol exclusively.
Its output was `PASS unchanged code/model/runtime/config; clean HEAD; preregistered before inference`.

```powershell
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --output evaluation-output/pdf-selective-ocr-expanded-v1-20261019/run-1 | Tee-Object -FilePath evaluation-output/pdf-selective-ocr-expanded-v1-20261019/run-1.log
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --output evaluation-output/pdf-selective-ocr-expanded-v1-20261019/run-2 | Tee-Object -FilePath evaluation-output/pdf-selective-ocr-expanded-v1-20261019/run-2.log
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-selective-ocr-v1-20261019/verify-final.py | Tee-Object -FilePath evaluation-output/pdf-selective-ocr-expanded-v1-20261019/pilot-replay-corrected.log
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-selective-ocr-expanded-v1-20261019/verify.py
```

Both genuine runs exited 0, each printing documents=8 and quality fingerprint
`561b4086a850582a75730008df7a5cbdf556af887063ee1d2b4afdabc5d33cce`.
The unchanged pilot verifier passed all four retained pilot attempts and 82 hashes;
only runs 3/4 contribute to combined final metrics. Expanded verifier exited 0:

```text
PASS ML19 artifact_hashes=78
PASS originals=90 Gold=19 prior_artifacts=82 unchanged_code_runtime_model=1
PASS repetitions=2 paired_documents=16 raw_captures=32 resource_journals=32 anchor_observations=142 quality_equal=1
PASS text=69/71 provenance=49/71 order=27/36 cells=0/20 relations=0/18 numeric=13/13 lost=0 recovered=0 each_run
PASS native_blocks=68 exact_results=32 preserved_duplicate_groups=0 render_exit_zero=2 OCR_invocations=0
PASS sampled_budgets cleanup ignored_isolation no_residue no_live_tools
```

Two local invocation/check failures preceded successful replay and are retained in
ignored deviation records. First, the old pilot verifier could not import `tools`
with PYTHONPATH containing only `src`; adding the repository root fixed invocation.
Second, the new scratch verifier incorrectly required positive RSS even for the
final sample after worker exit. Inspection found one final zero in every journal,
no negative samples or exceeded bounds. It now requires positive nonfinal samples
and peak, permits final zero, and retains all upper-bound checks. The initial script
is preserved. Neither correction changed candidate code, results or decision criteria;
no inference was repeated in response to them.

```powershell
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','tests/unit/test_pdf_ocr_candidate.py','tests/unit/test_extraction.py','tests/unit/test_extraction_fidelity.py','tests/unit/test_docling_candidate.py']))" | Tee-Object -FilePath evaluation-output/pdf-selective-ocr-expanded-v1-20261019/pytest.log
& .venv/Scripts/python.exe -B -m ruff check tools/pdf_ocr_candidate/benchmark.py tests/unit/test_pdf_ocr_candidate.py
& .venv/Scripts/python.exe -B -m ruff format --check tools/pdf_ocr_candidate/benchmark.py tests/unit/test_pdf_ocr_candidate.py
```

Actual outputs: **219 passed in 10.78s**, `All checks passed!`,
`2 files already formatted`; all exit 0. No tests skipped in that suite.
The two previously reported formatting failures in old parser/extraction-test files
are historical, outside this change, and were not rerun or altered. No new tests
or code changes were needed. This suite exercises synthetic OCR failure/limit paths;
real ML-19 documents did not exercise Tesseract or resource termination.

Final scope/privacy audit checks this report against original basenames and exact
reviewed text strings of at least 12 characters, scans credentials/absolute paths and
forbidden artifacts, checks UTF-8/LF/trailing whitespace, and verifies that only this
untracked report appears in Git. Short/common-string scans are not proof of absence
of every conceivable secret; manual full-diff review complements them. Source text,
Gold answer text, original filenames, runtime binaries and captures are absent from
the tracked change. At initial evaluation handoff, nothing was staged, committed
or pushed; the final review and commit were subsequently authorized separately.

```powershell
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-selective-ocr-expanded-v1-20261019/scope-audit.py
git diff --check
git diff --cached --check
git diff --no-index --check -- NUL docs/eda/pdf_selective_ocr_expanded_eval_v1.md
git diff --stat
git status --short
git config --get core.autocrlf
git check-attr text eol -- docs/eda/pdf_selective_ocr_expanded_eval_v1.md
```

Scope audit passed privacy, fingerprints, arithmetic, UTF-8/LF and no trailing
whitespace; exactly one untracked report, zero staged files and zero tracked
modifications. Ordinary/cached whitespace checks exited 0 with no output. The
new-file no-index check exited 1 for the present diff, with only the line-ending
warning and no whitespace diagnostics. A local command wrapper initially asserted
exit 0 for that command; correcting this exit-code interpretation required no file
or experiment change. The complete new-file diff was
reviewed through `git diff --no-index -- NUL` because ordinary `git diff --stat`
is empty for an untracked file. Git reports `core.autocrlf=true`, text/eol attributes
unspecified, and warns that LF will become CRLF when Git next touches the file.
The actual report remains LF with no BOM; no Git configuration was changed.
Initial evaluation handoff `git status --short`:

```text
?? docs/eda/pdf_selective_ocr_expanded_eval_v1.md
```

## Final review verification

The authorized final review independently reconciled the original captures against
frozen Gold, rather than accepting the stored summary. Both runs retain 69/71 text,
49/71 provenance, 27/36 order, 0/20 cells, 0/18 relations and 13/13 native
numeric-bearing anchors; combined text is 79/90 -> 88/90. Missing identities remain
c1-0035/a2 and a7, with zero new losses. Statuses remain 7 success, 1 needs_review,
0 failed; none were removed from denominators. Full native results, repeated
occurrences and quality fields are unchanged. No critical discrepancy was found.

Each run contains 33 native pages and one blank-render skip, with zero Tesseract
invocations. ML-19 measures native-preservation/generalization guardrails, not new
OCR recovery, multilingual OCR accuracy or numeric OCR accuracy. The candidate
generalization verdict remains INCONCLUSIVE and production authorization false.

The same read-only verifier commands above were rerun successfully: ML-19 verified
78 pinned artifacts, ML-18 verified 82, and all 90 originals / 19 Gold records,
runtime/code/configuration pins, resource journals and cleanup checks passed.
The 84-file terminal snapshot was also verified; existing artifacts were not edited.
The same focused pytest command was rerun: **219 passed in 11.75s**, no skips.
The same Ruff commands returned `All checks passed!` and `2 files already formatted`.
No new OCR inference, parameter change, scorer/Gold edit or production change occurred.
The review starting branch was main, with local origin/main divergence 0 ahead /
0 behind, and only this report untracked. Commit identity and final clean Git status
are reported separately after the required staged-diff/privacy/whitespace gate.

## Interpretation and next recommendation

The primary no-loss guardrail is supported for all eight measured native/blank-skip
paths. H1 is not a universal OCR-fidelity result: no additional OCR output exists
to evaluate, so the preregistered advancement coverage condition is unmet and the
expanded candidate verdict is **INCONCLUSIVE**. No critical regression was observed.
Zero regressions in eight purposively selected documents is insufficient to estimate
general deployment risk; anchors within one document are not independent trials.

The combined gain of nine anchors is entirely the already exposed ML-18 pilot gain.
Table structure, c1-0035 missing text, unreviewed numbers and broader languages remain
unresolved. The narrow next recommendation is review of this report, followed only
if separately authorized by a frozen, human-reviewed English cohort that actually
exercises selective OCR, including numeric and mixed-page evidence. Keep this
candidate offline and unchanged; do not infer production authorization or tune on
these results. No next experiment was started.

Engineering references: [PAR-01: pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
explains the distinction between native extraction and OCR;
[PAR-06: Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/)
is the official engine reference. Stable documentation can advance independently
of the pinned installed versions; measured behavior here comes from code/captures.
[EXP-02: GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)
documents non-overlapping groups, but no such new partition or independent-test
claim is made here. Architectural constraints are those in the applicable project
contract; absent external ML-policy attachments are UNAVAILABLE, not independently read.
