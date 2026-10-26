# Frozen blind Extraction review batch — 26 October 2026

STATUS: PASS for preparation and validation of reviewer inputs only. Human Gold,
semantic quality, QG-00/QG-01 quality and production authorization remain
NOT_EVALUATED. Starting branch `main`, HEAD
`cc1f05f2074a2219d4bc249003b4207d396d93f4`. No commit before review.

CHANGED: `tools/extraction_quality/blind_review_batch.py` adds only a local batch
packager/validator; `tests/unit/test_blind_review_batch.py` adds focused negative
and reproduction checks; this report records the handoff. Existing production
parsers, Gold, rights decisions and prepared PDF workspace were not changed.

DESIGN: [ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA),
[QG-00/QG-01](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[fidelity protocol](extraction_fidelity_protocol_v1.md) and the
[existing PDF handoff](qg00_review_handoff_20261021.md) govern this step.
The existing data-quality skill was applied. Frozen release integrity,
`corpus_v2` assets/family components/JSON checks, Office package safety,
physical XML resolution, locator validation and PDF workbench **read-only resume**
validation are reused. No model/parser comparison, new acquisition or Gold export.

The Office preselection uses only existing source metadata, rights and connected
families, before reading selected Office content. No prediction or oracle values
are used for selection. Require explicit local evaluation and new annotation use;
exclude every reserved-QA/non-dev connected component, including sealed candidates.
Rank DOCX by descending nested tables, body tables and ancillary text count.
Rank XLSX by descending stored-cell count within a 20,000-cell packaging bound;
break ties by opaque ID. This bound is a preparation budget, not a quality threshold.
The four selected components must differ; exact/normalized hashes, near duplicates
and declared related families participate in isolation. Semantic/translation family
completeness still requires independent review. These are exposed **dev** sources,
not fresh sealed-test data.

| Source | Format | Bytes | Recorded family | Source/coverage basis |
| --- | --- | ---: | --- | --- |
| c1-0033 | PDF | 29,702 | f-de5a37738e823a8f44ec7b0f | Reused original-only workspace; one real page |
| c1-0040 | PDF | 64,968 | f-3ed94a499073bb2cc8254c6e | Reused original-only workspace; one real page |
| c1-0007 | DOCX | 308,445 | f-86bdd44ccee832630f8045d3 | Metadata: 10 body tables, four nested tables, ancillary content |
| e2-office-18d8ec96e0631802 | XLSX | 185,796 | f-a14fed00f94949a69cd39230 | Metadata: 16,613 stored cells |

Original SHA-256 identities, in table order:

```text
081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd
18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344
c9403e37962ed5dbb0e598495636f9e0d550c6f0aaa76037d9d3bae4fdc44026
c3587abd1de6cf7774d6181df18b20b77a93294665f3cd91461246cc6e92c666
```

Rights reuse the source-bound admissions in the verified readiness release and
PDF eligibility v2. Scope is new local source literal/structure annotations of
government material, excluding logos, third-party material and populated personal
data. Source/publisher links and OGL attribution accompany the private originals.
No rights to unrelated annotations, training or cloud processing are inferred.
Documentary admission is not an authenticated legal or human-review attestation.

All **217 registrations** remain in the private selection ledger: four selected,
213 excluded/not selected. Overlapping exclusion reasons: annotation rights
unresolved 128; local evaluation unresolved 4; reserved/non-dev family 14;
outside the reused PDF pair 22; ranked below selected coverage 16; same selected
family 1; stored-cell budget 1; unavailable structural metadata 43.

The DOCX checklist contains 4,256 physical locators across 20 related package
parts, including paragraphs, nested table/cell elements, sections and notes.
Physical XML order is not rendered reading order; foreign-namespace wrappers,
drawing text and full layout are outside this checklist. The XLSX checklist has
16,613 genuine cell addresses, without sheet-name or cell-value sidecars.
Source-only inspection **after selection** found six sheets and 20 merge ranges,
zero stored formulas and zero error cells. No replacement was drawn: formula/cache
and stored-error coverage remain absent from this batch. No Word pages, display
values, logical spans, roles or semantic relationships were inferred.

Only the private `reviewer/` directory is a handoff: four originals, four unsigned
blank worksheets, instructions and attribution. Coordinator selection/freeze
records stay outside it. Existing validators may read protected historical Gold
to validate PDF lineage; those labels never enter the handoff. No Office oracle
is loaded/generated. Review templates preserve null unknown fields, not reviewed
absence. Completed responses must be separate from these frozen blank inputs.

VERIFIED — final private batch:
`evaluation-output/blind-extraction-review-20261026-v3/`.
Fingerprint `cd6db1ad5a80c11d6a2ce1135cb1bf00eee19eb89af53a190613d8d451cf80c9`.
Parent readiness fingerprint
`f480f4fad5b46eaf037b67d7ca77db2e37f93f1aa0172405fd7f493d44489b55`.
The `-v3-reproduction/` directory is a second copy of this same logical batch.
Earlier development preparations are superseded and are not reviewer handoffs.
Private originals, worksheets, manifests and test artifacts remain ignored.

Commands run from the repository root:

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv/Scripts/python.exe -B -m tools.extraction_quality.blind_review_batch prepare --output evaluation-output/blind-extraction-review-20261026-v3
.venv/Scripts/python.exe -B evaluation-output/blind-batch-verification-20261026/verify_frozen.py
.venv/Scripts/python.exe -B -m pytest tests/unit/test_blind_review_batch.py tests/unit/test_pdf_review_eligibility.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_pdf_review_workbench.py tests/unit/test_ml28_review.py tests/unit/test_readiness_release.py tests/unit/test_readiness_partitions.py tests/unit/test_dataset_readiness.py tests/unit/test_readiness_source_metrics.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/blind-batch-tests-complete --junitxml=evaluation-output/blind-batch-tests-complete.xml
.venv/Scripts/python.exe -m ruff check tools/extraction_quality/blind_review_batch.py tests/unit/test_blind_review_batch.py
.venv/Scripts/python.exe -m ruff format --check tools/extraction_quality/blind_review_batch.py tests/unit/test_blind_review_batch.py
git diff --check
git diff --cached --stat
git status --short
```

The verification helper verifies the primary, creates/verifies a fresh reproduction,
compares every batch file and checks existing PDF preparation files unchanged.
Result: **12 byte-identical files**, including the freeze manifest; **12,796 existing
PDF preparation files unchanged**. Both builds returned the fingerprint above,
zero reviews and quality NOT_EVALUATED. The complete focused suite returned
**204 passed, 1 skipped, zero failures, 70.99 seconds**. The single skip is the
existing Windows symlink-privilege test; link/path rejection checks otherwise ran.
Ruff check and format check passed; Git whitespace check passed; staged diff empty.
Runtime: Python 3.12.3, pydantic 2.14.0, pypdf 6.20.0, openpyxl 3.1.5,
pytest 9.1.1 and ruff 0.17.0; no dependencies installed or changed. Private evidence:
`evaluation-output/blind-batch-verification-20261026/verification-v3.json` and
`evaluation-output/blind-batch-tests-complete.xml`.

Source integrity and recorded-family isolation: PASS. Reproducible reviewer-input
readiness: PASS. Extraction fidelity and independent Gold readiness: NOT_EVALUATED.
Strict reconstruction rejects changed bytes/SHAs, forged review claims, unknown
fields, prediction/legacy sidecars, invented locators and hidden exclusions even
when an attacker refreshes artifact digests. Tests also cover all connected-family
link types and reserved/sealed/unknown-rights exclusions. This proves input
integrity, not authentic reviewer identity or semantic truth.

Earlier development runs exposed synthetic-fixture setup errors (immutable release
write order and PDF signature), corrected before final tests. An initial existing
subprocess test lacked the documented `PYTHONPATH`; rerunning fixed that environment
issue. Six existing HTTP tests encountered sandbox `WinError 10013`; the final
suite ran with local loopback access. These were environmental failures, not
silently excluded cases.

REMAINING: Actual humans must inspect originals, declare prior exposure and
independence, supply permission/viewer/inspection attestations, annotate source
literals and physical/semantic structure, resolve family/language/ambiguities,
freeze independent PDF drafts before disclosure and adjudicate in a separate
revision. The batch validator never accepts completed answers as Gold. Human Gold
count remains zero. No parser-quality or production-readiness claim is made.

COMMIT: Not created; review required. Pre-existing deleted Kaggle tooling and four
untracked qualification reports are preserved and outside this task.

GIT STATUS — exact final `git status --short`:

```text
 D tools/kaggle_gpu/extraction_remote.py
?? docs/eda/blind_extraction_review_batch_20261026.md
?? docs/evaluation/final_qg_qualification_20261024.md
?? docs/evaluation/final_qg_qualification_20261024_evidence.json
?? docs/evaluation/qg_qualification_20261024.md
?? docs/evaluation/qg_qualification_20261024_evidence.json
?? tests/unit/test_blind_review_batch.py
?? tools/extraction_quality/blind_review_batch.py
```
