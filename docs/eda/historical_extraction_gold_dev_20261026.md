# Historical Extraction Gold: local DEV eligibility — 26 October 2026

STATUS: PASS for the complete reproducible eligibility ledger only. Independent
Gold, semantic quality, QG-00 and QG-01 remain NOT_EVALUATED. No models ran, no
Gold/RAW was edited, no human review was created, and no commit is authorized yet.
Branch `main`, starting HEAD `90bba3c3fd4e35448f1de95966ab384076f68fd0`.

CHANGED: new `tools/extraction_quality/historical_gold_eligibility.py`, focused
`tests/unit/test_historical_gold_eligibility.py`, and this sanitized report.
Existing scoring, ingestion, parser and review contracts are unchanged.

DESIGN: the [readiness v2 report](extraction_data_readiness_20261023_v2.md),
[fidelity protocol](extraction_fidelity_protocol_v1.md),
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA) and
[QG-00/QG-01](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES)
govern this step. Existing release verification recursively checks the frozen
parent, source and rights evidence. Existing strict Gold loading, 90-RAW corpus
validation, asset checks and connected-family logic are reused. The tool reads
saved parser diagnostics; it runs no extraction/model experiment or new annotation.

All **19 documents / 282 unique assertion identities** reconcile with strict Gold
and the frozen historical ledger. IDs retain `document/group/zero-based-index`;
payload, source SHA/size/format, capture digests and source-evidence bindings must
match. The previous **95 issues = 13 technically resolved + 82 unresolved**.
The other 187 saved parser matches remain historical observations, not source truth.

| Assertion group | Total | DEV_DIAGNOSTIC_ELIGIBLE | REVIEW_REQUIRED | EXCLUDED |
| --- | ---: | ---: | ---: | ---: |
| Anchors | 126 | 99 | 23 | 4 |
| Partial order pairs | 58 | 40 | 15 | 3 |
| Table-cell spans | 52 | 24 | 24 | 4 |
| Table relationships | 33 | 9 | 20 | 4 |
| XLSX cell expectations | 13 | 9 | 0 | 4 |
| **Total** | **282** | **181** | **82** | **19** |

Format totals: PDF **180 = 98 eligible + 82 review-required**; DOCX **31 eligible**;
XLSX **71 = 52 eligible + 19 excluded**. Eligible assertions occur in **16** of the
19 documents. Two nonreserved documents currently have only review-required rows;
all 19 assertions from `c1-0062` are excluded through the reserved QA/Test component.

The ledger separates historical review status/basis/count/date, technical source
support and limitations, saved parser agreement, independent-review status, current
rights, split/family component, dependencies and per-metric eligibility. Historical
review attestations are transcribed, not authenticated or upgraded. All 19 have
recorded local-evaluation permission. Unknown new-annotation rights remain unknown;
this qualification concerns existing project historical labels in local DEV only,
not new labels, third-party annotation reuse, training, redistribution or cloud use.

The 181 eligible assertions comprise **168 historical-attestation-only** checks
without source reinspection and **13 with technical literal support**. Eligibility
does not assert correctness. The 13 are eight literal/physical-cell checks, four
literal/page-box checks and one DOCX note literal/region check. The four additional
locator proposals remain unapplied. Sixteen unresolved span/alignment observations
remain partial evidence within the 82, not resolved labels. Unresolved anchor
dependencies also block downstream order/structure assertions.

Parser agreement never establishes source correctness or independently grants
eligibility. In particular, the 13 source-supported prior failures stay eligible
for supported literal checks; changing saved agreement alone does not change the
eligibility rule. Historical source reinspection was itself targeted from prior
parser issues, so evidence coverage is outcome-conditioned. Report both the full
282-assertion population and each conditional diagnostic subset; do not present
subset results as corpus Extraction Accuracy or independent model-quality evidence.

Per-metric counts below are **eligibility counts, not scores or passed checks**:

| Metric | Requested | Eligible | Review required | Excluded | Unsupported subset |
| --- | ---: | ---: | ---: | ---: | ---: |
| Literal recall | 126 | 99 | 23 | 4 | 0 |
| Provenance | 139 | 96 | 34 | 9 | 1 |
| Partial reading order | 58 | 40 | 15 | 3 | 0 |
| Cell spans | 52 | 24 | 24 | 4 | 0 |
| Table relationships | 33 | 9 | 20 | 4 | 0 |
| Stored values | 13 | 9 | 0 | 4 | 0 |
| Formula expressions | 13 | 9 | 0 | 4 | 0 |
| Historical cached values | 13 | 9 | 0 | 4 | 0 |
| Display values | 0 | 0 | 0 | 0 | 0 |

Metric denominators overlap assertions and must not be summed as label counts.
Unsupported is included in excluded. The DOCX note's provenance cannot be resolved
by the frozen body-only scorer, although its literal recall remains eligible.
Eleven technically supported PDF literals still need logical-grid mapping review
for provenance. Native PDF table omission is a baseline limitation, not proof that
the structured metric is unsupported. Display checks are unsupported by this scorer
and unrequested in this Gold. No display, semantic order or formula recalculation
truth is inferred; quality scores remain null.

Private outputs: `evaluation-output/historical-gold-dev-20261026/run-{1,2}/`.
Each contains the complete `eligibility.json`, sanitized `summary.json` and
completion hashes. Both builds have **three byte-identical files** and ledger
fingerprint `0eb11e9a882eae73433c950babc8d61566d8bfd1d84ca0b25437689c16cd465d`.
Gold SHA-256: `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf`;
normalized Gold fingerprint:
`50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e`.
Frozen readiness fingerprint:
`f480f4fad5b46eaf037b67d7ca77db2e37f93f1aa0172405fd7f493d44489b55`.
Ledger bindings include 116 input identities and seven code digests.

VERIFIED — commands executed from the repository root:

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv/Scripts/python.exe -B -m tools.extraction_quality.historical_gold_eligibility build --output evaluation-output/historical-gold-dev-20261026/run-1
.venv/Scripts/python.exe -B -m tools.extraction_quality.historical_gold_eligibility build --output evaluation-output/historical-gold-dev-20261026/run-2
.venv/Scripts/python.exe -B -m tools.extraction_quality.historical_gold_eligibility verify --output evaluation-output/historical-gold-dev-20261026/run-1
.venv/Scripts/python.exe -B evaluation-output/historical-gold-dev-20261026/verify_reproduction.py
.venv/Scripts/python.exe -B -m pytest tests/unit/test_historical_gold_eligibility.py tests/unit/test_extraction_fidelity.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_fidelity_relationship_scope.py tests/unit/test_dataset_readiness.py tests/unit/test_readiness_partitions.py tests/unit/test_readiness_release.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/historical-gold-tests-final --junitxml=evaluation-output/historical-gold-tests-final.xml
.venv/Scripts/python.exe -m ruff check tools/extraction_quality/historical_gold_eligibility.py tests/unit/test_historical_gold_eligibility.py
.venv/Scripts/python.exe -m ruff format --check tools/extraction_quality/historical_gold_eligibility.py tests/unit/test_historical_gold_eligibility.py
git diff --check
git diff --cached --stat
git status --short
```

Results: both builds succeeded; reconstruction verification returned PASS for the
ledger only. **122 tests passed, one skipped, 6.16 seconds**. The skip is the
existing Windows symlink-privilege case. Rights denial/unknowns, changed RAW/SHA,
Test/related/exact/normalized/near-duplicate family leakage, duplicate identities,
missing/changed evidence, unsupported dimensions, forged review and resealed ledger
tampering ran and passed. Tests also prove parser agreement is informational,
logical-grid uncertainty persists, summaries omit private payloads, and input order
does not change classification. Ruff/format/whitespace checks passed.

All **236 preservation hashes** still match, including **217 original files**,
existing local Gold files, frozen readiness records and the four unrelated evaluation
reports. Python 3.12.3; pydantic 2.14.0, pypdf 6.20.0, openpyxl 3.1.5,
pytest 9.1.1, ruff 0.17.0. No dependencies changed. Private preservation/runtime
evidence is `evaluation-output/historical-gold-dev-20261026/verification.json`;
JUnit evidence is `evaluation-output/historical-gold-tests-final.xml`.

REMAINING: 82 assertions need source/semantic review; 11 additional provenance
dimensions need grid mapping review and one is unsupported. Independent review,
complete semantic family isolation and new-annotation permissions are not inferred.
Existing Test/independent-quality release gates remain unchanged. This ledger is
not independent Gold, quality acceptance, production authorization or a model run.

COMMIT: Not created; review required. The unrelated Kaggle deletion and four
untracked `docs/evaluation` files remain untouched and unstaged.

Final `git status --short`:

```text
 D tools/kaggle_gpu/extraction_remote.py
?? docs/eda/historical_extraction_gold_dev_20261026.md
?? docs/evaluation/final_qg_qualification_20261024.md
?? docs/evaluation/final_qg_qualification_20261024_evidence.json
?? docs/evaluation/qg_qualification_20261024.md
?? docs/evaluation/qg_qualification_20261024_evidence.json
?? tests/unit/test_historical_gold_eligibility.py
?? tools/extraction_quality/historical_gold_eligibility.py
```
