# Historical Extraction baseline on qualified local DEV — 26 October 2026

STATUS: PASS for offline saved-capture scoring, reproducibility and scoped checks.
Independent Gold, semantic quality and QG-00/QG-01 remain NOT_EVALUATED. No new
corpus parsing, model inference, GPU or cloud work ran. No RAW, Gold, release or
historical eligibility artifact was edited. No commit created; review required.
Branch `main`; starting HEAD `185ca25aa7cfeb5b8e1dfe86f7b09a6704f762c8`.

CHANGED: new `tools/extraction_quality/historical_dev_baseline.py`, focused
`tests/unit/test_historical_dev_baseline.py`, and this sanitized report. Private
results remain ignored. Existing scorers, parsers and admission contracts are unchanged.

DESIGN: [historical DEV eligibility](historical_extraction_gold_dev_20261026.md),
[fidelity protocol](extraction_fidelity_protocol_v1.md),
[Extraction Strategy](../../DocLens_AI_Extraction_Strategy.md#EX-EXPERIMENT) and
[ML experiment controls](../../DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT)
govern this step. `historical_gold_eligibility.verify` reconstructs frozen
eligibility and recursively verifies release/source/rights/family bindings before
scoring. The just-read eligibility payload must also reproduce the verified
fingerprint, closing a verification/read mutation window. Saved capture SHA and
source SHA/size/format must match; missing captures abort rather than invent scores.

All **282 identities / 19 documents** remain in coverage. Only **181 assertions /
16 documents** have permitted metrics: **168 historical-attestation-only** and
**13 technically supported literal checks**. The other **82 REVIEW_REQUIRED** and
**19 EXCLUDED** assertions are retained unscored with reason codes. The excluded
19 belong to the reserved QA/Test component. The saved captures used here have
**10 success / 6 needs_review / 0 failed** statuses; needs_review is not filtered out.

The tool invokes existing `fidelity_eval.score_record` on in-memory assertion views.
Order/span/relation views keep their original dependency anchors, occurrence and
locators. Cell provenance isolates the selected cell and excludes unrelated anchors.
No locator corrections are applied. Every permitted dimension must yield exactly
one supported check, and all metric denominators must reconcile with eligibility.
Failed checks remain in the denominator. Unsupported and unresolved dimensions have
null measurements, not artificial failures or passes.

Literal recall retains whitespace-only normalization and case-sensitive substring
matching from the existing scorer. It is not exact-token numeric accuracy. Signs,
punctuation and digits are not rewritten; stored values, formulas and cached values
use exact nullable string equality. No formula execution, cache refresh, rounding,
case folding, cross-field matching or rendered-value inference is added.

## Actual conditional metric results

These are diagnostic rates over permitted dimensions, not corpus Extraction Accuracy.
Requested includes all historical dimensions; excluded includes unsupported checks.
Counts overlap assertions and must not be pooled into one quality score.

| Metric | Passed / evaluated | Rate | Requested | Review required | Excluded | Unsupported subset |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Literal recall | 98 / 99 | 98.99% | 126 | 23 | 4 | 0 |
| Provenance | 95 / 96 | 98.96% | 139 | 34 | 9 | 1 |
| Partial reading order | 40 / 40 | 100% | 58 | 15 | 3 | 0 |
| Cell spans | 24 / 24 | 100% | 52 | 24 | 4 | 0 |
| Table relationships | 9 / 9 | 100% | 33 | 20 | 4 | 0 |
| Stored values | 9 / 9 | 100% | 13 | 0 | 4 | 0 |
| Formula expressions | 9 / 9 | 100% | 13 | 0 | 4 | 0 |
| Historical cached values | 9 / 9 | 100% | 13 | 0 | 4 | 0 |
| Display values | 0 / 0 | NOT_EVALUATED | 0 | 0 | 0 | 0 |

### Format breakdown

Each fraction is passed/evaluated. A dash means zero eligible labels and null score.
Full attempted historical coverage remains visible alongside the eligible subset.

| Format | Eligible / full assertions | Recall | Provenance | Order | Spans | Relations | Stored | Formula | Cache |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PDF | 98 / 180 | 66/67 | 55/56 | 31/31 | — | — | — | — | — |
| DOCX | 31 / 31 | 15/15 | 14/14 | 6/6 | 7/7 | 3/3 | — | — | — |
| XLSX | 52 / 71 | 17/17 | 26/26 | 3/3 | 17/17 | 6/6 | 9/9 | 9/9 | 9/9 |

PDF table metrics are NOT_EVALUATED here: no permitted labels remain for them.
The 100% span/relation rates concern DOCX/XLSX only, not native PDF table capability.

### Assertion group breakdown

| Group | Eligible / full assertions | Permitted metric numerator / denominator |
| --- | ---: | --- |
| Anchors | 99 / 126 | Recall 98/99; provenance 86/87 |
| Partial order pairs | 40 / 58 | Order 40/40 |
| Table-cell spans | 24 / 52 | Spans 24/24 |
| Table relationships | 9 / 33 | Relations 9/9 |
| XLSX cells | 9 / 13 | Provenance 9/9; stored 9/9; formula 9/9; cache 9/9 |

### Evidence tiers

| Tier | Eligible / full assertions | Recall | Provenance | Other permitted dimensions |
| --- | ---: | ---: | ---: | --- |
| Historical attestation only | 168 / 187 | 86/86 | 95/95 | Order 40/40; spans 24/24; relations 9/9; stored/formula/cache each 9/9 |
| Technically supported literal | 13 / 13 | 12/13 | 0/1 | No other permitted dimensions |
| Unresolved source evidence | 0 / 82 | — | — | All unscored |

One retained failure, `c1-0035/anchors/6`, fails literal recall and provenance in
the saved capture. This is one assertion with two failed dimensions. The other
12 technically supported literals pass recall. Eleven of their provenance checks
still need logical-grid review; the DOCX ancillary provenance check is unsupported.
Historical attestations are not authenticated anew. Source reinspection was
conditioned on prior parser problems; all historical-only labels had previously
matched saved diagnostics. Their high conditional rates are selection-biased and
do not establish independent fidelity, semantic correctness or generalization.

## Frozen outputs and reproduction

Authoritative private outputs:
`evaluation-output/historical-dev-baseline-20261026/verified-{1,2}/`.
Each contains `scores.json`, `summary.json` and `COMPLETE.json`; all three are
byte-identical between builds. Earlier development snapshots are not authoritative.
The private result retains every assertion, admission/reason, scored dimension,
capture fingerprint/status, all format/group/tier/document breakdowns and bindings.
No private excerpts, values, source filenames or worksheet names enter this report.

Contract: `historical-dev-saved-baseline-1`.
Result fingerprint: `1d593eff69528dff0552d518e568ba0995a7a0e36b4c5a811d2ee049729b180f`.
Eligibility fingerprint: `0eb11e9a882eae73433c950babc8d61566d8bfd1d84ca0b25437689c16cd465d`.
Gold fingerprint: `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e`.
The result pins eligibility SHA, frozen input/code digests and scoring dependencies.
Git HEAD is recorded as execution context here and in private verification evidence;
code digests identify the uncommitted scorer additions. Later Git metadata changes
alone do not invalidate frozen data; changing pinned scoring/input contracts does.

VERIFIED — executed commands from repository root:

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv/Scripts/python.exe -B -m tools.extraction_quality.historical_gold_eligibility verify --output evaluation-output/historical-gold-dev-20261026/run-1
.venv/Scripts/python.exe -B -m tools.extraction_quality.historical_dev_baseline build --output evaluation-output/historical-dev-baseline-20261026/verified-1
.venv/Scripts/python.exe -B -m tools.extraction_quality.historical_dev_baseline build --output evaluation-output/historical-dev-baseline-20261026/verified-2
.venv/Scripts/python.exe -B -m tools.extraction_quality.historical_dev_baseline verify --output evaluation-output/historical-dev-baseline-20261026/verified-1
.venv/Scripts/python.exe -B evaluation-output/historical-dev-baseline-20261026/verify_reproduction.py
.venv/Scripts/python.exe -B -m pytest tests/unit/test_historical_dev_baseline.py tests/unit/test_historical_gold_eligibility.py tests/unit/test_extraction_fidelity.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_fidelity_relationship_scope.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/historical-baseline-tests-verified --junitxml=evaluation-output/historical-baseline-tests-verified.xml
.venv/Scripts/python.exe -m ruff check tools/extraction_quality/historical_dev_baseline.py tests/unit/test_historical_dev_baseline.py
.venv/Scripts/python.exe -m ruff format --check tools/extraction_quality/historical_dev_baseline.py tests/unit/test_historical_dev_baseline.py
git diff --check
git diff --no-index --check -- /dev/null tools/extraction_quality/historical_dev_baseline.py
git diff --no-index --check -- /dev/null tests/unit/test_historical_dev_baseline.py
git diff --no-index --check -- /dev/null docs/eda/historical_extraction_dev_baseline_20261026.md
git diff --cached --stat
git status --short
```

Results: eligibility verification, both builds and result reconstruction succeeded.
**108 tests passed, no skips, 4.55 seconds**, including **32 new focused cases**.
Negative cases cover ineligible/reserved labels, unsupported/display inflation,
changed source/capture SHA/size/format, missing/extra capture, denominator/identity
drift, dependency loss, eligibility mutation, resealed result forgery and incomplete
output. Existing strict Gold, rights/family isolation and scorer regression tests
also passed. Tests use public synthetic fixtures; existing scorer regression tests
include fixture extraction, not new corpus parsing. Ruff and format checks passed.
Tracked diff whitespace check returned zero. Each new-file `--no-index --check`
returned one for the added-file difference, with no whitespace diagnostics; Git
printed only its existing LF-to-CRLF configuration warnings.

All **619 pre-snapshotted protected file hashes** remain unchanged, including the
prior 236-file preservation set, RAW/Gold, frozen continuation, both historical
eligibility outputs and the four unrelated evaluation reports. Input verification
recursively checks frozen parent release bindings too. Private preservation and
reproduction evidence: `evaluation-output/historical-dev-baseline-20261026/verification.json`.
JUnit: `evaluation-output/historical-baseline-tests-verified.xml`.

REMAINING: no execution blocker. The 82 unresolved assertions, 19 excluded
assertions, 11 unconfirmed PDF logical-grid dimensions and unsupported ancillary/
display dimensions remain outside scored denominators. Complete semantic family
isolation, independent review, rendered fidelity and model comparisons remain
NOT_EVALUATED. No thresholds, parser promotion or production authorization follow.
Extraction latency/RAM are not remeasured by this saved-capture scoring step.

COMMIT: Not created; review required. Unrelated Kaggle deletion and four untracked
`docs/evaluation` files remain untouched and unstaged. All new task files are unstaged.
