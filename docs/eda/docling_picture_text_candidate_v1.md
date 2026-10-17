# Docling picture-descendant text candidate v1 (ML-11)

## Pre-registration before inference

Registered on 2026-10-17 at HEAD
`d20fb21ffe2f1834b2b08b4e56e55a3df248b3fa`, which includes ML-10
`9b39846e3c968a54b2dc80703637c11dc4e4238c` (ancestor check exit 0).
Only the offline adapter and its synthetic tests may change. Initial status has
four unrelated untracked `rag_sufficiency_dev` paths; they are untouched.

Hypothesis: enabling native picture-child traversal recovers the nine omitted
c1-0032 anchors a2–a10 with valid reviewed provenance, using the existing
normalization/identity deduplication path. No OCR, inference configuration,
model, Gold, scorer, production routing or resource budget changes are permitted.
Native tree order and existing whitespace-gap-only provenance span validation
remain authoritative; no invented locators or text concatenation.

This is a reused, exposed purposive evaluation sample, not a fresh sealed test.
Evaluate all twelve previously measured PDFs: eight primary sources c1-0031,
c1-0032, c1-0033, c1-0035, c1-0040, c1-0043, c1-0048, c1-0049; four controls
c1-0041, c1-0044, c1-0045, c1-0050. Preserve every failed/needs_review outcome
and its label denominators; unknown observations are not fabricated zero scores.

Narrow acceptance requires all nine targeted anchors and their valid provenance,
zero newly lost required anchors versus the frozen Docling candidate, zero new
per-document order/table-cell/relationship/provenance regression, no new status
eligibility downgrade, preserved drawing warnings/failure isolation, passing
regressions, and two reproducible complete runs within unchanged budgets.
Check anchor identities independently of aggregate recall. Compare pypdf as well,
but inherited ML-10 losses do not become new ML-11 regressions. Any observed new
critical regression forces REJECT; missing/non-reproducible evidence supports
INCONCLUSIVE, absent essential inputs BLOCKED. A narrow pass means only
ACCEPT_FOR_FURTHER_OFFLINE_ENGINEERING. Overall production quality remains REJECT.
Do not tune after results. c1-0043, c1-0049 and c1-0040 causes are out of scope.

Unchanged configuration: CPU/two threads, FAST table structure/cell matching;
OCR, enrichment, plugins and remote services disabled. Serial fresh child for
each source, pypdf first then cold Docling. Limits: 600 seconds per paired worker,
3221225472 process bytes (3072 MiB), 52428800 source bytes, 200 pages,
100000 blocks/cells, 5000000 characters. No retries with larger budgets.
Memory is sampled paired-child peak_wset (RSS fallback) approximately every
50 ms, not a hard OS sandbox or independent arm peak. The runner monitors the
actual multiprocessing child, not a Windows Python launcher. Descendant memory
is not separately aggregated; native in-process inference is the expected scope.

Two new ignored output directories are reserved:
`evaluation-output/docling-picture-text-v1-20261017-run1` and `-run2`.
Run serially without concurrent tests or inference. Compare every non-runtime
field and deterministic fingerprint, retaining actual timing and memory.

## Verified frozen inputs before inference

All 90 original SHA/size/format identities verified locally. Strict duplicate-key
Gold loading and normalized membership verification passed: 19 reviewed records,
12 selected PDFs. Both historical reports independently rehashed and equal in
all non-runtime fields. Original adapter and unchanged dependency code hashes
match those reports. Models match the captured five-file inventory exactly.

| Identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| 90-source identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Selected twelve | `ec69b55db7e66298e509c51632432d60b861c7b76845a631ea7f60f6d4cddf68` |
| Expanded Gold bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Expanded Gold normalized | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Model inventory | `3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71` |
| Historical run 1 metrics bytes | `dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48` |
| Historical run 2 metrics bytes | `3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a` |
| Both historical deterministic reports | `d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24` |

Python 3.12.3; Docling 2.55.1, docling-core 2.48.2, docling-ibm-models 3.15.0,
torch 2.8.0, pypdf 6.20.0, psutil 7.1.0 in the existing isolated environment.
Layout revision `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`; table revision
`fc0f2d45e2218ea24bce5045f58a389aed16dc23`. No dependencies/downloads added.

## Engineering evidence

Direct references: ML-10 [root-cause report](pdf_regression_root_cause_v1.md),
the [frozen protocol](docling_pdf_expanded_benchmark_v1.md), repository
`normalize_document`/unchanged fidelity scorer, and pinned vendor
docling-core 2.48.2 `DoclingDocument.iterate_items` / `_iterate_items_with_stack`
(installed `types/doc/document.py`, lines 4035–4120). Vendor source inspection
confirms preorder identity references, default body-layer filtering, captions
visible without picture traversal, and recursion into picture children when
enabled. Furniture remains outside this change. No current-version web API
assumptions or private documents were sent to external tools.

Synthetic reproduction before changing the flag:
`.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py -k picture_descendant`
returned exit 1: **7 failed, 3 passed, 71 deselected in 0.58 s**. Hidden descendants
were omitted, including invalid provenance and nested cell-limit checks. This is
the expected pre-fix reproduction, not the final verification verdict.

The executable adapter delta was checked with Python ASTs from `git show HEAD`
and the working file: changing the old `traverse_pictures` constant to True made
the entire modules identical. All other executable logic/configuration is fixed.
Candidate SHA-256 during both evaluations:
`b0b872bb131b393b9338f135e353994c5213550c57e62ef92b49aee903d968fe`.
Pinned native iteration source SHA-256:
`1d92d230815ada82f1d0a09b787452f3e6367738901e8f92d69659096797b36f`.
The pre-inference preregistration/report snapshot SHA-256 was
`902269a243af378419280bba249c701378c20318491e966de72da4d2e8a86136`.

Native identity is used for deduplication, and multi-provenance character spans
drive validated slicing into page-located blocks. The frozen TextBlock contract
does not serialize native self_ref, bounding boxes or raw charspan coordinates.
No field or locator was invented to expand that contract. Synthetic coverage
includes nested pictures/captions, repeated references versus equal text with
different identities, order/pages, missing/ambiguous/overlapping/gapped spans,
limits and content-free failure isolation followed by a successful next source.
Block/character boundary tests were strengthened during the first inference run;
adapter/configuration bytes remained unchanged and final tests run after inference.

## Results and decision

**Engineering checks passed; candidate acceptance REJECT. Production quality
remains REJECT.** Both genuine commands returned exit 0 / `evaluated` with twelve
attempts each. Each has eleven complete scored pairs and one controlled
`memory_limit` outcome on c1-0045. The runner deliberately treats a controlled
limit with an available baseline as an evaluated unsuccessful attempt; exit 0
does not mean every candidate conversion completed or passed quality gates.

The targeted text-recovery mechanism is confirmed in both runs: all nine opaque
identities c1-0032/a2–a10 change false -> true. All ten anchors have valid reviewed
provenance (10/10), independently supporting the nine recoveries rather than
relying on aggregate recall alone. Order rises 0/4 -> 3/4; the remaining pair is
not fixed. Status stays needs_review with two drawing warnings. No full drawing
extraction is claimed.

Among eleven scored pairs there are **nine recovered and zero observed newly
lost anchors**, and no new measured order/table/provenance or status downgrade.
The six c1-0045 anchors are UNKNOWN, not zero or proven unchanged. Its previously
successful/eligible candidate now has a controlled unavailable result in both
runs. This operational regression violates the complete-within-budget gate and
prevents clearing the complete-population non-regression/eligibility gates.
The registered decision is therefore REJECT, even though text recovery works.
Do not infer that the traversal flag caused the resource increase: termination
metadata has no conversion-versus-normalization phase attribution. That cause is
UNKNOWN; no budget increase, third run or corrective tuning was attempted.

### Per-document reconciliation

Each metric cell gives **pypdf / frozen Docling / new Docling**, with a shared
denominator after the semicolon. These values hold in both repetitions.
NE means no reviewed labels; U means unavailable, retaining the full denominator.
S = success, R = needs_review, L = memory_limit (a runner outcome, not a fabricated
ExtractionStatus.failed value).

| ID | Anchors | Order | Table cells | Relationships | Provenance | Status |
| --- | --- | --- | --- | --- | --- | --- |
| c1-0031 | 7/7/7; 7 | 4/4/4; 5 | NE | NE | 7/7/7; 7 | S/S/S |
| c1-0032 | 10/1/10; 10 | 3/0/3; 4 | NE | NE | 10/1/10; 10 | S/R/R |
| c1-0033 | 9/9/9; 9 | 0/3/3; 3 | 0/8/8; 8 | 0/8/8; 8 | 1/9/9; 9 | S/S/S |
| c1-0035 | 6/7/7; 8 | 4/5/5; 5 | NE | NE | 6/7/7; 8 | S/S/S |
| c1-0040 | 8/8/8; 8 | 2/2/2; 3 | 0/0/0; 4 | 0/0/0; 4 | 4/4/4; 8 | S/S/S |
| c1-0041 | 0/0/0; 4 | 0/0/0; 3 | NE | NE | 0/0/0; 4 | R/R/R |
| c1-0043 | 6/0/0; 6 | 4/0/0; 4 | NE | NE | 6/0/0; 6 | R/S/S |
| c1-0044 | 0/0/0; 5 | 0/0/0; 2 | NE | NE | 0/0/0; 5 | R/R/R |
| c1-0045 | 6/6/U; 6 | 1/2/U; 2 | 0/4/U; 4 | 0/2/U; 2 | 2/6/U; 6 | S/S/L |
| c1-0048 | 11/11/11; 11 | 6/6/6; 6 | 0/3/3; 3 | 0/1/1; 1 | 8/11/11; 11 | S/R/R |
| c1-0049 | 12/11/11; 12 | 4/3/3; 6 | 0/5/5; 5 | 0/5/5; 5 | 7/11/11; 12 | S/S/S |
| c1-0050 | 4/4/4; 4 | 3/3/3; 3 | NE | NE | 4/4/4; 4 | S/R/R |

For the eleven available candidates all warning maps match the frozen candidate:
drawing counts c1-0032=2, c1-0041=3, c1-0044=1, c1-0048=3, c1-0050=15;
c1-0041/0044 retain insufficient_text=1. Others have no warnings. c1-0045
warnings/status/eligibility and fidelity are unobserved after the limit.

### Full denominators, including unknown coverage

Entries below are passed/total; `+U n` is unresolved coverage within that same
total, never added to passed or excluded. New results match between runs.

| Population / arm | Anchors | Order | Cells | Relationships | Provenance | Known eligible |
| --- | --- | --- | --- | --- | --- | --- |
| Eight primary / pypdf | 69/71 | 27/36 | 0/20 | 0/18 | 49/71 | 7/8 |
| Eight primary / frozen | 54/71 | 23/36 | 16/20 | 14/18 | 50/71 | 6/8 |
| Eight primary / new | 63/71 | 26/36 | 16/20 | 14/18 | 59/71 | 6/8 |
| Four controls / pypdf | 10/19 | 4/10 | 0/4 | 0/2 | 6/19 | 2/4 |
| Four controls / frozen | 10/19 | 5/10 | 4/4 | 2/2 | 10/19 | 1/4 |
| Four controls / new | 4/19 +U 6 | 3/10 +U 2 | 0/4 +U 4 | 0/2 +U 2 | 4/19 +U 6 | 0/4; 1 limit |
| All twelve / pypdf | 79/90 | 31/46 | 0/24 | 0/20 | 55/90 | 9/12 |
| All twelve / frozen | 64/90 | 28/46 | 20/24 | 16/20 | 60/90 | 7/12 |
| All twelve / new | 67/90 +U 6 | 29/46 +U 2 | 16/24 +U 4 | 14/20 +U 2 | 63/90 +U 6 | 6/12; 1 limit |

The new anchor-recall bound is 67/90–73/90 (74.44%–81.11%), with 17 known
missing anchors and six unknown. This is not complete measured recall of 73/90.
Statuses: baseline 9 S / 3 R; frozen candidate 7 S / 5 R; new candidate
6 S / 5 R / 1 controlled limit per run. Zero-label stored-value/formula/cache/
display dimensions remain NOT_EVALUATED.

Against pypdf, seven known inherited losses remain: c1-0043/a1–a6 and
c1-0049/a4. The earlier c1-0035/a7 gain persists. The six baseline-present
c1-0045 anchors now have unknown candidate availability; they are not claimed
as textual losses. All twelve baseline score/status/warning/anchor/fingerprint
objects are identical to both historical runs. New document metadata differs
from frozen only for c1-0032, c1-0045 and c1-0048. c1-0048 has a changed extraction
fingerprint with identical measured scores/status/warnings; its unlabelled
content changes were not independently inspected and remain NOT_EVALUATED.

### Repetition and resource evidence

Both new reports independently recompute to deterministic fingerprint
`faaef99c1e9bf5be6aa76c92159aee6fa5dd1dfa13bd24a10dab088a6523597d`.
Every non-runtime field is identical, including the repeated controlled limit.
Compared with frozen reports, configuration, models/revisions, dependency
versions, population, manifest/Gold, scorer/parser/models/validator hashes,
limitations and table mode are unchanged. Only adapter hash and the document
metadata above change. The existing `pictures_not_represented` limitation still
describes drawing/image semantics, not the now-preserved native child text.

| New artifact | SHA-256 |
| --- | --- |
| Run 1 metrics bytes | `f78aaf265e0fa065f81a7d9b6472ad42f02ce9e956ff703083203b48428c8aeb` |
| Run 2 metrics bytes | `2ece0ad6c59dab7770a97891ed4569f33a745ed5e615c1e29a0a49b319f4f13c` |
| Final synthetic tests | `f4997810cee55b85802e686f8b17792159c5c146aa84afbb6a5abde5cfb7869f` |

Runtime fields differ as expected: 12/12 baseline timings, 11/11 completed
candidate timings, 12/12 paired wall times and 12/12 memory peaks. The c1-0045
candidate timing is absent in both runs, not zero. Hardware: Windows 11
10.0.26200, AMD64, 8 physical / 16 logical CPUs, RAM 16541597696 bytes.
No seed or concurrency setting changed.

Times below are sums in milliseconds; peaks are maximum paired-child bytes.
Candidate sums include only the eleven completed conversions; no total candidate
time, speedup or SLA claim is inferred from the truncated control attempt.

| Run / cohort | Baseline ms | Completed candidate ms | Paired wall ms | Peak bytes |
| --- | ---: | ---: | ---: | ---: |
| 1 / primary | 1031.798 | 138989.983 | 147303.793 | 2596839424 |
| 1 / controls | 2828.363 | 89939.538 (3/4) | 477491.546 | 3226775552 |
| 1 / all | 3860.161 | 228929.521 (11/12) | 624795.339 | 3226775552 |
| 2 / primary | 1024.355 | 137731.831 | 146241.280 | 2595692544 |
| 2 / controls | 2857.970 | 88680.634 (3/4) | 465466.352 | 3221475328 |
| 2 / all | 3882.325 | 226412.465 (11/12) | 611707.632 | 3221475328 |

| ID | Candidate ms run 1 / 2 | Peak bytes run 1 / 2 |
| --- | --- | --- |
| c1-0031 | 10368.930 / 8770.433 | 944324608 / 942862336 |
| c1-0032 | 8205.842 / 9238.712 | 946003968 / 944848896 |
| c1-0033 | 10777.832 / 11238.739 | 974684160 / 974925824 |
| c1-0035 | 9200.549 / 9078.095 | 949030912 / 949100544 |
| c1-0040 | 24100.650 / 23841.639 | 1008017408 / 1014624256 |
| c1-0041 | 13988.100 / 13729.755 | 2520985600 / 2520666112 |
| c1-0043 | 13606.138 / 13300.948 | 2525077504 / 2524610560 |
| c1-0044 | 9341.907 / 9035.632 | 942505984 / 943431680 |
| c1-0045 | UNKNOWN / UNKNOWN | 3226775552 / 3221475328 |
| c1-0048 | 36493.250 / 35729.005 | 2596839424 / 2595692544 |
| c1-0049 | 26236.792 / 26534.259 | 2584403968 / 2586959872 |
| c1-0050 | 66609.531 / 65915.247 | 2620698624 / 2622271488 |

c1-0045 paired wall times are 383591.671 / 372953.559 ms. Sampled peaks exceed
the 3221225472-byte guard by 5550080 / 249856 bytes before termination, consistent
with sampled rather than hard memory enforcement. Prior complete c1-0045 runs
used 541845.103 / 506161.104 candidate ms and peaked at 2872725504 / 3063615488
paired bytes. Both new runs have one controlled memory event, zero timeouts,
zero reported extraction-status failures among completed pairs and zero
uncontained worker/infrastructure failures. No extraction result/fidelity score
was manufactured for the terminated worker. The failure phase, allocator/model
contribution, effect of environment variability and causality of the code change
remain UNKNOWN. No new profiling or configuration experiment was performed.

## Actual verification commands and outputs

Commands ran from the repository root with `PYTHONPATH=src` and
`PYTHONDONTWRITEBYTECODE=1`. The two inference commands ran serially outside the
restricted shell sandbox (the existing offline network/output guard remained
active), without concurrent unit tests or other candidate inference:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -m doclens_ai.extraction.docling_candidate --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --artifacts evaluation-output/docling-v1-models --artifact-fingerprint 3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71 --profile expanded-v1 --timeout-seconds 600 --max-process-mib 3072 --output-dir evaluation-output/docling-picture-text-v1-20261017-run1
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -m doclens_ai.extraction.docling_candidate --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --artifacts evaluation-output/docling-v1-models --artifact-fingerprint 3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71 --profile expanded-v1 --timeout-seconds 600 --max-process-mib 3072 --output-dir evaluation-output/docling-picture-text-v1-20261017-run2
```

Each printed exactly:
`{"status": "evaluated", "documents": 12, "deterministic_fingerprint": "faaef99c1e9bf5be6aa76c92159aee6fa5dd1dfa13bd24a10dab088a6523597d"}`;
both benchmark exit codes were 0. The initial quick completeness probe returned
exit 1 when its assertion encountered the controlled c1-0045 outcome; final
reconciliation explicitly accounts for unavailable scores instead.

```powershell
git rev-parse HEAD
git merge-base --is-ancestor 9b39846e3c968a54b2dc80703637c11dc4e4238c HEAD
git check-ignore evaluation-output/docling-picture-text-v1-20261017-run1/metrics.json evaluation-output/docling-picture-text-v1-20261017-run2/metrics.json
$taskPythonFiles = @(git ls-files -- src tests alembic | Where-Object { $_ -match '\.py$' })
.venv/Scripts/python.exe -B -m ruff check @taskPythonFiles
.venv/Scripts/python.exe -B -m ruff format --check src/doclens_ai/extraction/docling_candidate.py tests/unit/test_docling_candidate.py
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit --ignore=tests/unit/test_kaggle_rag_sufficiency_dev.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B "$qaRoot/ml11_audit.py"
git diff --check
git status --short
```

Final Ruff: `All checks passed!`, exit 0; formatting: `2 files already formatted`,
exit 0. Final focused suite: **116 passed in 5.93 s**, exit 0. Final broader
tracked suite: **730 passed, 1 skipped in 17.95 s**, exit 0. The skip is
`test_data_quality_gate.py:432`, Windows symlink privilege unavailable.
Integration/service/GPU/OCR tests were not run: no such behavior changed.

Earlier iterations are not hidden: the pre-fix reproduction failed as recorded
above; an initial post-fix focused suite passed 115 tests, while Ruff/format
rejected one long assertion. Formatting was corrected before inference. After
adding the isolation test, focused 116 passed in 6.31 s. Initial broad commands
in the restricted sandbox stalled without results and were stopped (first
pytest exit -1; second exit 1). The first lacked the unrelated-unit-test exclusion;
that scope error was corrected. Ruff was also rerun against tracked Python paths
only. The first successful broader run outside that sandbox passed 730 tests,
1 skipped in 16.45 s. No unrelated file was edited or staged.

`qaRoot` denotes the session scratch directory outside Git. Its read-only audit
program SHA-256 is
`cce25b5010d8f38ba2da7e32a652375d039ddc284e1ef65fd4d27a31e3b459b8`.
Invocation exited 0 and printed `REPEAT_NON_RUNTIME_EQUAL True` and
`PASS: integrity and reconciliation checks; candidate gate assessed separately with unknowns/limits retained`.
It reverified all 90 sources, strict reviewed Gold, both historical byte hashes,
all four report fingerprints, unchanged config/models/dependencies/dependency
code, twelve baseline objects, per-anchor counters, full denominators, repeated
target recovery/provenance and all available per-document guardrails. Its final
GATE output had recovered=9, observed lost=0, observed metric regressions=0,
unknown=[c1-0045]. The empty observed eligibility-downgrade list excludes that
unavailable outcome and does not clear the operational availability gate.

Final read-only report/scope/privacy verification ran as Python stdin through
`.venv/Scripts/python.exe -B -`, exit 0. Actual output:
`PASS: all 12 report rows match frozen/new metadata; private filenames/long Gold anchor text/absolute paths absent; tracked modification allowlist exact`.
It constructed every metric/status row from captured metadata, verified originals
again, compared real filenames and normalized Gold anchors of at least twelve
characters against the report, rejected absolute paths/private-key headers,
and checked the tracked modification allowlist. This bounded text scan is
supplemented by manual diff review, not claimed as a universal secrets detector.
`git diff --check` returned exit 0, with only Git's LF-to-CRLF advisories.
The intended commit contains exactly this report and the two allowlisted Python
files; frozen outputs, originals, Gold, weights and unrelated untracked work are
excluded. Commit subject:
`fix: preserve picture-descendant text in offline Docling adapter`.

## Remaining boundaries and architectural review

c1-0043 still succeeds with 0/6 anchors; generic success is not fidelity.
Its upstream exact-evidence absence has unresolved recognition/alteration causes.
c1-0049 still loses furniture anchor a4 and retains its measured order deficit.
c1-0040 still has 0/4 reviewed table cells and 0/4 relationships, with locator
incompatibility unresolved. These ML-10 problems were not incidentally fixed,
relabelled or reconverted outside the paired protocol. Full visual order,
unlabelled numerical/diagram semantics and raw coordinate fidelity remain
NOT_EVALUATED. No new human review, test split, model, OCR or dependency was added.

The nine-anchor result merits further offline investigation of this adapter
mechanism, subject first to a separately authorized bounded c1-0045 resource-phase
investigation at the same budget. That is a recommendation, not an implemented
fix or a new experiment. This step stops here. Overall Docling production quality
remains REJECT because inherited losses and eligibility issues persist as well
as the new resource outcome. Production pypdf, Gold, historical outputs,
configurations and models are preserved; promotion is unauthorized.
