# ML-18 selective PDF OCR pilot v1

Date: 2026-10-19. **Execution: PASS.**
**Candidate: PROMOTE_FOR_FURTHER_OFFLINE_EVALUATION**, limited to this registered pilot.
**Production authorization: false.** Production pypdf and the frozen Docling REJECT
verdict remain unchanged. This is measured recovery of reviewed evidence, not a
production parser promotion or an exhaustive OCR-accuracy certification.

## Result and population

The missing runtime was resolved and the same ML-18 experiment completed. The final
frozen pair is **runs 3/4**. Earlier runs 1/2 are retained: review found an output-budget
bug in the new runner, reproduced it synthetically, fixed it and repeated both real
paired evaluations. No source, Gold, OCR model, selection threshold, resource ceiling
or acceptance criterion was tuned. Only the runner hash changed between registrations.

All four attempts completed with the same extracted results and per-anchor outcomes.
Final pair: **8/8 paired document observations, 38 anchor observations** over **4 unique
PDFs / 19 unique anchors**. All attempts: **16 paired document observations / 76 anchor
observations**, 32 raw extraction captures and 32 resource journals. Repetitions are
not independent new labels or a fresh sealed test. Both needs_review documents remain
in denominators. No extraction failure or page/tool failure occurred in these runs.

| Source | Unchanged baseline text | Run 3 candidate | Run 4 candidate | Recovered identities, each repetition | Lost | Status, baseline -> candidate |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| c1-0041, primary | 0/4 | 4/4 | 4/4 | a1, a2, a3, a4 | 0 | needs_review -> needs_review |
| c1-0044, labels only | 0/5 | 5/5 | 5/5 | a1, a2, a3, a4, a5 | 0 | needs_review -> needs_review |
| c1-0045, numeric/table control | 6/6 | 6/6 | 6/6 | None | 0 | success -> success |
| c1-0050, ordinary narrative control | 4/4 | 4/4 | 4/4 | None | 0 | success -> success |
| Total per repetition | **10/19** | **19/19** | **19/19** | **9** | **0** | 2 success, 2 needs_review, 0 failed |

| Dimension | Baseline | Candidate, each final repetition | Interpretation |
| --- | ---: | ---: | --- |
| Required text | 10/19 | 19/19 | Literal whitespace-only scorer, case/digits unchanged |
| Reviewed provenance | 6/19 | 15/19 | Nine recovered anchors at reviewed locations |
| Reviewed reading order | 4/10 | 9/10 | Remaining control failure unchanged |
| Table cells | 0/4 | 0/4 | No table/grid reconstruction attempted |
| Table relationships | 0/2 | 0/2 | Existing c1-0045 failures unchanged |
| Reviewed numeric-bearing text anchors | 9/9 | 9/9 | Existing native evidence preserved, not OCR-number accuracy |
| Diagram relationships | NOT_EVALUATED | NOT_EVALUATED | Label recognition does not establish graph edges |

Recovered provenance: c1-0041 a1/a2 are on page 1, a3 page 2, a4 page 4;
c1-0044 a1-a5 are on page 1. These are unchanged reviewed page expectations,
independently reconciled against capture locations, not locators derived from
predictions. New OCR blocks contain page_number only; block/table/row/column and
cell locators are null. Existing native blocks retain their text and sources.
Global output order is renumbered when OCR blocks are inserted; this is distinct
from source coordinates. Both control ExtractionResults are completely identical
to their baseline captures, including order, warnings and fingerprints.

All 50 source pages are accounted for in each repetition: **5 OCR pages** (four in
c1-0041, one in c1-0044), **45 native pages**, no blank skips or resource failures.
The two controls are not OCRed. c1-0045 numeric-bearing anchors a2-a6 remain 5/5;
c1-0050 a1-a4 remain 4/4. Primary/secondary anchors have no numeric-bearing reviewed
labels: numeric accuracy of their unlabelled OCR content is **NOT_EVALUATED**.
No new numeric Gold, exhaustive visual review or semantic correctness claim is made.

## Runtime installation and provenance

Experiment execution HEAD and review starting HEAD:
`ffca8d43a76bea73a82778c33739bd363f601523`, branch `main`.
Starting status contained only the existing untracked ML-18 report. Applicable root
AGENTS.md and extraction-benchmark / ML-experiment skills were read; no nested
AGENTS.md was found on requested ancestor paths. The 2026-10-18 blocked report was
preserved byte-for-byte in ignored storage and verified against its original hash.
The subsequent explicit installation authorization superseded that runtime blocker.

Winget **1.29.380** confirmed package **UB-Mannheim.TesseractOCR**, fixed version
**5.4.0.20240606**, publisher **Tesseract-OCR community**, author Mannheim University
Library, license **Apache-2.0**. Installer source is the versioned UB-Mannheim GitHub
release, not an unpinned latest artifact. Winget verified the installer hash and
reported successful installation. No installed matching package existed beforehand.
The user-scope applicability query reported no applicable installer. The tagged
installer source declares Highest execution level and registry registration; the
standard installation path was used without bypassing Windows/UAC permissions.
No manual PATH change, unrelated package installation or repository dependency-manifest
edit occurred. Packaged auxiliary tools/OSD were included by the vendor installer;
no training, GUI/auxiliary tool, OSD inference or additional language download was used.

Real executable: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
`--version`: **tesseract v5.4.0.20240606**, Leptonica **1.84.1**.
`--list-langs`: **eng, osd**. English traineddata is present and readable in the
installed tessdata directory. The experiment uses explicit executable/tessdata paths,
so it does not depend on PATH refresh. English model bytes come from the pinned
installer; a separate upstream model Git revision is **UNKNOWN**, not fabricated.
Installed engine license text is Apache-2.0, SHA-256
`cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`.
Bundled-model provenance is pinned to that distribution; this is not a complete
license audit of every third-party DLL.

Poppler **26.07.0** is the existing renderer. The existing isolated evaluation Python
runtime supplies Python **3.12.3**, pypdf **6.20.0**, Pydantic **2.14.0**, psutil **7.1.0**.
No Python dependencies were installed. Development pytest is loaded read-only from
the existing `.venv`. No Docling conversion or model loading, OCR model training,
GPU workload, private upload, Gold change or production routing change occurred.
Host: Windows 11 / AMD64, 16 logical CPUs, 16,541,597,696 bytes physical RAM.
Runtime registration hashes the interpreter, 51 Tesseract DLLs and 121 renderer DLLs;
these are distribution-file pins, not a traced loaded-module graph.

## Preregistered protocol and implementation

H1: selective OCR on insufficient-native-text pages recovers reviewed c1-0041 evidence
without removing valid native text, changing numeric evidence or fabricating locators.
Secondary c1-0044 label recall is measured separately from diagram relations.

The initial report left the image-content signal pending. Before the first corpus
OCR, registration completed that signal: fewer than **20 native non-whitespace
characters** selects rendering; OCR runs only if at least **0.001** of validated P5
8-bit grayscale pixels are below **245**. This is a generic foreground signal,
not a semantic classifier. Selection receives no corpus IDs, Gold text or labels.
Blank renders are skipped. OCR uses **300 dpi, eng, OEM 1, PSM 3, one thread**, no
seed parameter, correction/substitution, response repair or adaptive configuration.
Repeated pages remain distinct. Only an exact whitespace-normalized whole-page
native/OCR duplicate is suppressed. Partial overlap is retained in separate fields,
without fuzzy deletion; provenance/occurrence checks stay separate from Boolean
anchor presence. Unresolved native/OCR content and OCR documents remain needs_review.

Limits, unchanged across both registrations:

- One document worker; 50 MiB source, 40 source pages, 10 rendered/OCR candidate pages.
- 20,000,000 rendered pixels/page; 5,000,000 combined output characters/document.
- 256 MiB document scratch; 3 GiB summed worker/process-tree RSS; 600 s/document.
- 60 s per renderer/OCR tool; 0.02 s sampling; memory -> timeout -> disk precedence.

Workers isolate extraction failures; per-page tool errors retain other pages/native
text. A terminated document worker has unknown candidate scores and stays in the
population. No incomplete extraction is relabelled successful. RAW and custom RAW
roots are excluded from output placement. Rendered pages/text scratch use temporary
subdirectories and are removed after each page; private extraction captures and
sanitized resource/tool journals remain ignored. Tool stdout/stderr are suppressed
rather than logging source text or native exception details. Actual tool exit codes,
durations and sampled resources are retained. These are sampled process guards,
not hard OS memory ceilings or a hostile-upload sandbox; between-sample overshoot
and transient allocations remain limitations.

Advancement gate, fixed before OCR: >=1/4 primary anchors recovered with reviewed page
provenance in both repetitions; no baseline-present loss, control/numeric/provenance
regression, new failure or fabricated source structure; deterministic quality fields
agree; registered resource/privacy/cleanup checks pass. Unknown measured guardrails
force INCONCLUSIVE and demonstrated violations force REJECT. Native numeric evidence
and existing reviewed numeric-bearing anchors are the numeric guardrail; unlabelled
OCR-number correctness is not silently certified.

**The final pair passes this limited gate:** primary 4/4 with pages, secondary 5/5,
zero losses, controls identical, native numbers preserved, complete matching captures,
all measured resource/cleanup/privacy checks passed. The justified next action is
review and further authorized offline coverage, including independently reviewed OCR
numeric/error labels and other document/language families. This exposed four-document
pilot cannot establish corpus-wide accuracy, multilingual coverage or production safety.
Do not automatically start another experiment or promote production.

## Correction, failed checks and repeated execution

Before inference, initial invocation from the isolated runtime could not import the
project; explicit `src` plus existing dev site-packages corrected the invocation.
An initial synthetic Locator omitted required `region`; that test fixture was fixed.
New-file Ruff line-length findings were fixed before initial registration. Initial
candidate tests subsequently passed **39 tests**; initial broader focused suite
passed **211 tests in 11.73s**.

Review after runs 1/2 found a genuine runner budget bug: OCR on an early page could
consume space required by later native pages. New regression
`test_ocr_budget_reserves_all_later_native_text` reproduced **15 > 10** characters,
**1 failed in 2.46s**. The fix reserves all native text before spending the OCR budget.
The RAW output guard was also scoped to the actual configured corpus root, with a
synthetic regression for nondefault roots. Candidate tests then passed **41 in 2.70s**.
The initial runner, report, registration and captures are archived unchanged.

The failing resource regression was executed with:

```powershell
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','tests/unit/test_pdf_ocr_candidate.py::test_ocr_budget_reserves_all_later_native_text']))"
```

Actual failure: `assert 15 <= 10`, exit 1. The final 213-test run includes this
regression passing after the fix, along with the RAW-root regression.

Only runner code hash changed in registration v2; source/Gold/runtime/selection,
limits and gate were asserted identical. Both real paired evaluations were repeated
as runs 3/4. Their extracted results agree exactly with runs 1/2; there was no observed
pilot-budget violation in the original pair. All four attempts are disclosed above.

The initial read-only artifact verifier incorrectly identified later native blocks
as new OCR when their global order shifted. Its corrected replay compares text plus
source identity to distinguish native preservation from output order. The failed
verifier and first failed output are disclosed; original artifacts were not repaired.
Executed `evaluation-output/docling-v1-runtime/Scripts/python.exe -B
evaluation-output/pdf-selective-ocr-v1-20261019/verify.py`: exit 1, AssertionError at
the new-block locator assertion. Executed the corresponding `verify-replay.py`:
exit 0, original pair replay passed with 41 then-pinned artifacts.
Final replay verifies both final captures, original comparator hashes, all 82 pinned
artifact files, and agreement across all four attempts without invoking extraction.

## Resource observations

Seconds are per-document worker wall time including process startup/imports, native
extraction, candidate rendering/OCR and capture handling; excluding corpus integrity,
registration hashing and Gold scoring. Nearest-rank P50/P95, n=4 documents per stage
per repetition. RSS is sampled summed worker plus live descendants, excluding the
orchestrating parent. Process startup is fresh; OS/file caches were not reset.
Run 2 overlapped focused tests; final runs 3/4 did not overlap those tests. Timings
are descriptive small-sample observations, not a controlled speed/SLA claim.

| Final repetition | Stage | P50 seconds | P95 seconds | Peak sampled tree RSS bytes |
| --- | --- | ---: | ---: | ---: |
| 3 | baseline | 1.157 | 3.109 | 73981952 |
| 3 | candidate | 2.687 | 9.515 | 134033408 |
| 4 | baseline | 1.234 | 2.969 | 73850880 |
| 4 | candidate | 2.500 | 11.094 | 133857280 |

| Source | Run 3 baseline / candidate seconds | Run 4 baseline / candidate seconds | Candidate peak MiB, run 3 / 4 |
| --- | ---: | ---: | ---: |
| c1-0041 | 1.125 / 9.515 | 1.094 / 11.094 | 127.824 / 127.656 |
| c1-0044 | 1.157 / 2.687 | 1.234 / 2.500 | 119.871 / 118.891 |
| c1-0045 | 3.109 / 3.047 | 2.969 / 3.109 | 69.770 / 69.957 |
| c1-0050 | 2.172 / 2.141 | 2.141 / 2.172 | 62.566 / 62.660 |

Original pair candidate P50/P95: run 1 **2.296 / 8.313 s**, run 2 **2.375 / 8.328 s**;
peak RSS **134000640 / 134078464 bytes**. All attempts stayed within registered sampled
budgets. Final pair peak sampled scratch: **8749869 bytes**. Final pair has 10 real
Tesseract invocations and 10 render invocations, all exit 0. All attempts total 20 OCR
and 20 render invocations. Cleanup checks passed; no remaining renderer/OCR processes
or rendered image/PDF scratch files were found. No resource-limit outcome occurred
in the corpus; synthetic tests exercise actual timeout/memory/disk termination.

## Frozen identities

All **90/90** originals were verified by SHA-256/size/format before/after execution;
all **19/19** strict reviewed Gold records match source identities. Only the four
registered PDFs were parsed/OCRed. Review is the supplied existing human attestation;
no new human review is claimed. The four manifest entries retain English and OGL v3
license provenance. No Gold, split, threshold or prior benchmark was modified.

| Identity | SHA-256 / canonical fingerprint |
| --- | --- |
| Manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Expanded Gold bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Expanded Gold normalized | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| c1-0041 source, 77333 bytes | `daef7ef6b8dd4200817d1342dfdb480ace0f4a0a3f921165f777ee294bf0485a` |
| c1-0044 source, 100551 bytes | `43a961d9f86849a18ddf680a77ed4e4d38dd8f7b4c0e795dc5a51ec9ff255410` |
| c1-0045 source, 107597 bytes | `04358ce617249f170d38ea302cbc96a35701987507e61fb87ea2be30da2cfddc` |
| c1-0050 source, 461365 bytes | `f1ac87dc692b4e6a48f821a06457e6ee09023ddc83c6e121af60b521d14b9524` |
| pypdf parser module | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| Fidelity scorer | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Gold validator | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |
| Extraction models | `0725bb86ebeea07926ab813e91625857fb68e97f3b35e30ecf8d9cb3c7259876` |
| Both frozen expanded benchmark fingerprints | `d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24` |
| Expanded benchmark run-1 bytes | `dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48` |
| Expanded benchmark run-2 bytes | `3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a` |
| Tesseract installer | `c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9` |
| Tesseract executable | `babb405f4366b480d02cd8ff2bac8d497170f6c1711ce6f3d5d8bf0fb7fa6ed9` |
| Bundled eng.traineddata | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` |
| pdftoppm executable | `bbb9d17eae3d4c4219ef062924989d0305c82223b3ea7a4d7558d327f9aae2f5` |
| Initial runner / archived code | `19d96dca8260f95236f51921ede307c169f70011b5f403240befae658b80251a` |
| Final runner | `d0676b4aec8eb660e50b909b00f4ad57963439e78d876495386e9a13f59f5aec` |
| Experiment-time unit tests | `cfd5e762ba5f3b0b8a1f09e5fd60c51285af0807bc9c7751fc90069f9db19867` |
| Commit-review unit tests | `bff09941d5c06514755bd47a19cc0da40d654bff53b14b5c3489f4b055fcb17c` |
| Initial registration canonical | `052502383b34b5006dac57e33d9e68a5832a396fb19dc586fc60cf7678b12e2b` |
| Initial registration bytes | `344873ce08dbf8374420762e6e532eff9973dbfe254fe9f9ee2dbe3510a01d88` |
| Final registration canonical | `f5f2ab64914e664d2faf04caa31ca1ab3f0be11497da3b1f9e0d2f48310c0384` |
| Final registration bytes | `a45e73698c72f3bcd41c1b71a1f70e2faa6e91541597806e54d83dbc431add2f` |
| Runs 1/2 quality fingerprint | `e6c8dc7236ed65db04d333c75a02ca8da15ce2f25ae0a08791822c9ec5b07b53` |
| Runs 3/4 quality fingerprint | `160a5e6962a0114b06ea59282ed5114847415ec7c4c3774e100045494c1f740a` |
| Run 1 metrics bytes | `fae92f913db855579b340df0a63418278ac3deb173f77bcf830702b38206b8bd` |
| Run 2 metrics bytes | `109095851a1b5192547c1d5678d458b2eeedb50ccb3d6fd456c915e0589f4f63` |
| Run 3 metrics bytes | `7fc18672829316edb527750ac8bb95e8e2dc6094888e07338ff5820be2ec4ce8` |
| Run 4 metrics bytes | `e6b4ab665fb8ac889ce15d1e1fd8885b6c368076d52d0e07fdde189039338b42` |
| Runtime provenance JSON | `fd2aa44dc5d301310273bee9ad273131709df9da863a21bbb36d0315952464e1` |
| Final artifact manifest, 82 entries | `4086c46dde4a8e4722720218b84ed876180d701eb7f2e018173339afaf5901ee` |
| Final read-only verifier | `5ff3e9fc51e8ed09838843834509cfd5d26d65f1aa5acca1f6090e5581806c93` |
| Original blocked report archive | `745514211bb7ae93dca939edcfde8d405528726709cb2038e7ff2a6a55e14482` |

Fresh baseline fingerprints, scores and anchor hits match both frozen expanded
reports for all four sources. All non-runtime quality fields in final runs match,
including per-document text/locations/page states/statuses and extraction hashes;
comparison is not limited to the top-level fingerprint. Old/new quality fingerprints
differ only because registration fingerprints include the changed runner hash.

## Actual commands and verification

Commands ran at repository root. Winget execution needed sandbox escalation because
the app-execution alias could not run inside the restricted sandbox. Read-only package
queries and the authorized standard installation succeeded outside it; no Windows
permission bypass was attempted. Exact material commands:

```powershell
winget --version
winget show --id UB-Mannheim.TesseractOCR --exact --source winget --versions --accept-source-agreements
winget list --id UB-Mannheim.TesseractOCR --exact --accept-source-agreements
winget show --id UB-Mannheim.TesseractOCR --exact --version 5.4.0.20240606 --source winget --accept-source-agreements
winget show --id UB-Mannheim.TesseractOCR --exact --version 5.4.0.20240606 --source winget --scope user --accept-source-agreements
winget download --id UB-Mannheim.TesseractOCR --exact --version 5.4.0.20240606 --source winget --download-directory evaluation-output/pdf-selective-ocr-v1-20261019/install --skip-dependencies --accept-source-agreements --accept-package-agreements --disable-interactivity
winget install --id UB-Mannheim.TesseractOCR --exact --version 5.4.0.20240606 --source winget --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
```

Actual outputs: winget v1.29.380; fixed version listed; no installed matching package;
user-scope query "no applicable installer"; installer hash verified; "Successfully
installed" (localized output). Package/license/runtime verification exited 0; package
list had exit 1 because no matching prior installation was found.

```powershell
$ocrExe = Join-Path $env:ProgramFiles 'Tesseract-OCR/tesseract.exe'
& $ocrExe --version
& $ocrExe --list-langs
Get-FileHash -Algorithm SHA256 -LiteralPath $ocrExe,(Join-Path $env:ProgramFiles 'Tesseract-OCR/tessdata/eng.traineddata')
Get-Content (Join-Path $env:ProgramFiles 'Tesseract-OCR/doc/LICENSE') -TotalCount 8
```

Outputs: engine and languages above; executable/model hashes above; Apache License
Version 2.0. Poppler was checked with `pdftoppm -v`, `pdfinfo -v`, both 26.07.0.

The following exact setup/commands froze and ran the initial pair:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
$ocrPath = Join-Path $env:ProgramFiles 'Tesseract-OCR/tesseract.exe'
$rendererPath = (Get-Command pdftoppm).Source
$tessdataPath = Join-Path $env:ProgramFiles 'Tesseract-OCR/tessdata'
$benchArgs = @('tools/pdf_ocr_candidate/benchmark.py','--documents','c1-0041','c1-0044','c1-0045','c1-0050','--tesseract',$ocrPath,'--renderer',$rendererPath,'--tessdata',$tessdataPath,'--registration','evaluation-output/pdf-selective-ocr-v1-20261019/registration.json')
evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --freeze
evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --output evaluation-output/pdf-selective-ocr-v1-20261019/run-1
evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --output evaluation-output/pdf-selective-ocr-v1-20261019/run-2
```

The final pair repeated that setup with these exact arguments and invocations:

```powershell
$benchArgs = @('tools/pdf_ocr_candidate/benchmark.py','--documents','c1-0041','c1-0044','c1-0045','c1-0050','--tesseract',$ocrPath,'--renderer',$rendererPath,'--tessdata',$tessdataPath,'--registration','evaluation-output/pdf-selective-ocr-v1-20261019/registration-v2.json')
evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --freeze
evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --output evaluation-output/pdf-selective-ocr-v1-20261019/run-3
evaluation-output/docling-v1-runtime/Scripts/python.exe -B @benchArgs --output evaluation-output/pdf-selective-ocr-v1-20261019/run-4
```

All four run commands exited 0, each printed documents=4 and its registered quality
fingerprint above. No inference output was edited or reissued selectively.

```powershell
.venv/Scripts/python.exe -B -m ruff check tools/pdf_ocr_candidate/benchmark.py tests/unit/test_pdf_ocr_candidate.py
.venv/Scripts/python.exe -B -m ruff format --check tools/pdf_ocr_candidate/benchmark.py tests/unit/test_pdf_ocr_candidate.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','tests/unit/test_pdf_ocr_candidate.py','tests/unit/test_extraction.py','tests/unit/test_extraction_fidelity.py','tests/unit/test_docling_candidate.py']))"
$env:PYTHONPATH = "$(Join-Path (Get-Location) 'src');$(Get-Location)"
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-selective-ocr-v1-20261019/verify-final.py
```

Final actual outputs, exit 0:

```text
All checks passed!
2 files already formatted
213 passed in 12.86s
PASS all_attempts=4 paired_document_attempts=16 anchor_observations=76 initial_pair_retained final_pair=3,4
PASS originals=90 Gold=19 repetitions=2 paired_documents=8 raw_captures=16 resource_journals=16 exact_quality_equal=1
PASS recovered=9/run lost=0 native_controls_identical=2/run numeric_anchors=9/9 OCR_pages=5/50/run tool_exit_zero=20/20
PASS sampled_resource_budgets cleanup no_rendered_residue no_live_OCR_processes artifacts=82
```

The verifier is read-only: hash validation, independent literal/location replay and
unchanged scorer, resource-journal reconciliation, control identity and cleanup.
No OCR/conversion is performed by replay. Synthetic tests cover blank/native selection,
mixed pages, duplicates retained across pages, numeric strings, wrong-page evidence,
missing OCR/runtime, corrupt PDF, invalid renders, page/pixel/combined character limits,
RAW-root protection, actual subprocess resource termination and unknown scores for
terminated workers. These tests do not certify unlabelled OCR semantics.

Separate **pre-existing failure**, rerun and not fixed:

```powershell
.venv/Scripts/python.exe -B -m ruff format --check src/doclens_ai/extraction/parsers.py tests/unit/test_extraction.py
```

Exit 1: **2 files would be reformatted**. Both files are unchanged from HEAD; parser
bytes also match the frozen benchmark. This is outside the allowlist and distinct
from the passing changed-file formatting gate. No broader application/service suite
or production readiness check was run; application code was not changed.

## Final code review, 2026-10-19

Complete runner/test review and independent saved-capture reconciliation found no
critical defect in the registered offline execution. The runtime runner remains
byte-identical to the code used for runs 3/4 (hash above). No OCR inference was rerun,
no configuration/acceptance criterion was changed, and all 82 artifact hashes,
original comparator reports, 90 source identities and 19 reviewed Gold records remain
unchanged. Both manifests retain the original execution HEAD; the commit that
introduces this report is a separate provenance event, not a relabelled experiment.

The four remaining provenance failures are **c1-0045/a3, a4, a5, a6**. Each text
exists on the reviewed page with the expected native block index; each matching
flat block lacks **table_index, row_index and column_index** required by Gold.
All four therefore fail the unchanged locator predicate. They already failed in
both frozen baselines and are unchanged in both final candidates. No reviewed
location was replaced by a convenient global text occurrence. Other source/anchor
provenance passes; 19 - 4 = 15. The cause demonstrated here is absent structured
table provenance in this native-text control, not newly lost OCR evidence.

Six additional synthetic cases cover exact combined-output capacity, one-character
overflow, empty OCR at a full native budget, and timeout/missing-OCR/memory failure
at that same boundary. They verify later native text remains present exactly once,
page sources remain unchanged, inserted OCR has page-only provenance, output order
is contiguous, the total budget is respected and partial/failed OCR stays review.
Only tests and this report changed during final review; the measured runner hash
and all inference outputs are unchanged. Candidate test coverage is now 47 cases.

The exact focused pytest command above was rerun with these tests: **219 passed in
11.36s**, exit 0. Ruff check: **All checks passed!**, exit 0; changed-file
`format --check`: **2 files already formatted**, exit 0. The exact read-only
`verify-final.py` command above passed again, including both final captures and
all 82 pinned artifacts. Live `--version`/`--list-langs` and executable/model hashes
reconfirmed Tesseract 5.4.0.20240606, eng/osd and unchanged traineddata; `pdftoppm -v`
and `pdfinfo -v` reconfirmed Poppler 26.07.0. The known unrelated formatting command
was rerun: exit 1, two unchanged old files would be reformatted; neither was edited.

Review confirmed selection/OCR receive no Gold or corpus identity; sufficient
native text and genuine page sources are preserved; no table/diagram coordinates
are synthesized. Subprocesses use argument arrays without a shell, third-party
diagnostics are suppressed, and page scratch is scoped to ignored worker output.
Existing tests exercise worker and tool termination, preserved native content and
unknown scores for killed workers. Process-tree RSS/disk/time limits are sampled;
they are not a hard OS sandbox or exhaustive adversarial resource certification.
Full-page duplicate suppression preserves repeated evidence on separate pages;
documented partial native/OCR overlap remains review content, not inferred structure.
Unlabelled OCR semantics/numbers and broader document/language coverage remain open.

The review followed [CODE-07 review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
for functionality, concurrency, edge cases and tests, subordinate to project scope.
The user's final-review authorization now permits staging exactly the three ML-18
files and committing after the staged privacy/whitespace checks pass. The actual
commit SHA and final Git status belong in the completion message; no push is allowed.
The initial pre-stage literal privacy check flagged an incidental overlap between
new review prose and a private Gold string. The prose was paraphrased before staging
and the full check rerun; no Gold labels or captured outputs were edited or exposed.

## Privacy, scope and review gate

Only three Git-visible paths are in scope: this report, the offline runner and its
synthetic unit test. Full new-file diffs, whitespace/line endings and final status are
reviewed before staging and again as the complete staged diff. Report/code/tests are
UTF-8 LF without BOM/trailing whitespace;
Git warns that its working-copy policy may later convert LF to CRLF. No attributes or
Git configuration was changed. Source/Gold text, real document basenames, private
absolute paths, credentials, PDFs, weights, binaries and generated captures are not
included in these files. The public installed engine path is shown as requested.
All private captures, installer, journals, archived registration/report/code and
verifiers are in the verified ignored experiment directory. Automated basename,
long-Gold-string and secret/path-pattern checks complement manual diff review; they
do not constitute a universal secret detector.

Pre-staging Git/whitespace commands are `git diff --check`, `git status --short
--untracked-files=all`, `git diff --cached --name-only` and full
`git diff --no-index -- /dev/null <each-allowlisted-file>` review. Tracked and staged
diffs are empty; status lists exactly the three allowlisted files as untracked.
New-file `git diff --no-index --check` exits 1 for file differences, with no whitespace
diagnostics; only the documented LF/CRLF warning appears. Explicit byte checks also
confirm LF/no BOM/no trailing whitespace. Source files and the two pre-existing
formatting failures are byte-identical to HEAD. All 82 captured artifact hashes
remain unchanged. No generated artifact is staged or Git-visible as an addition.

Relevant official sources: [PAR-01 pypdf 6.20.0 text extraction](https://pypdf.readthedocs.io/en/6.20.0/user/extract-text.html),
[PAR-06 Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html),
[fixed Winget package manifest](https://github.com/microsoft/winget-pkgs/blob/master/manifests/u/UB-Mannheim/TesseractOCR/5.4.0.20240606/UB-Mannheim.TesseractOCR.installer.yaml),
and [tagged installer source](https://github.com/UB-Mannheim/tesseract/blob/v5.4.0.20240606/nsis/tesseract.nsi).
Tesseract CLI parameters were checked through configured documentation MCP. Attached
quality-policy documents were not independently accessed; supplied task constraints
and repository gates govern this experiment. No archive extraction workflow was added.

Finalization stages only these three files and requires `git diff --cached --check`
plus complete staged scope/privacy review before the one authorized commit,
`feat: add offline selective PDF OCR benchmark`. No push or further ML step.
