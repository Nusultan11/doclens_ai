# Native PDF development diagnostic — 22 October 2026

**Engineering execution: PASS. Extraction-quality gate: NOT_EVALUATED.**
Both originals extracted successfully in both repetitions. The principal observed
limitation is **missing native table topology and cell provenance**: each document
produces one page-text block, zero native tables and zero native cells. The frozen
reference contains 536 cells and six logical grids. Text presence cannot establish
which original cell supplied a repeated value or symbol.

This is a development diagnostic on two exposed, AI-assisted reference documents,
with limited user confirmation of their source-comparison report. It is not an
independent Gold evaluation, parser promotion, QG-00/QG-01 PASS or release decision.
No parser behavior, configuration, limits, annotations or frozen labels changed.

## Identity, eligibility and reproducibility boundary

Starting branch `main`; HEAD `cae91d6a9c5e537e0ebaf69ba8d5f3e0127b9e9f`.
Native engine `pypdf 6.20.0`; extraction schema `1.1`; Python `3.12.3`,
Pydantic `2.14.0`, psutil `7.1.0`. Offline diagnostic method
`pdf-native-dev-diagnostic-1.0`.

Frozen development reference `pdf-dev-reference-20261022-v1`:
`64fa75b779854918fc50df38bc3e3cb3bf0069c8cb6c76e775bf6c35f8e1c9dc`.
The existing strict dev-reference validator passed before measurement and before
and after each repetition. It verifies the accepted proposal package, source
identities, eligibility evidence, source correspondence and held-out-family guard.
The 1,154 original proposal IDs remain accounted for: 719 items contribute admitted
fields, and 435 remain unresolved-only context. All 719 admitted field items appear
in each diagnostic, including original item IDs for the six grid proposals.

| Source ID | Original SHA-256 | Bytes | Pages | Existing eligibility |
| --- | --- | ---: | ---: | --- |
| c1-0033 | `081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd` | 29,702 | 1 | Local dev annotations/evaluation admitted |
| c1-0040 | `18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344` | 64,968 | 1 | Local dev annotations/evaluation admitted |

The extractor read exact frozen copies of the authoritative originals; returned
SHA/size/format identities were checked again. The existing source-bound
eligibility-v2 decisions were reused. Both selected control records passed the
existing Retrieval/RAG test-family guard. Declared-family completeness remains
unreviewed; exposure precludes treating this subset as fresh independent test data.
No other source or annotation-rights decision is revised.

Maintained contracts: [PDF extraction](../../DocLens_AI_Extraction_Strategy.md#EX-PDF),
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA),
[QG-00/QG-01](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
and the [assisted-review handoff](qg00_review_handoff_20261021.md).

## Measurement rules fixed before extraction

`registration.json` and each repetition's `pins.json` were written before its
first extraction. There is one unchanged native arm, no candidate or tuned variable,
no models, OCR, table reconstruction, Gold export or semantic scoring.

- Exact matching preserves Unicode, signs, decimal separators, case and whitespace.
  The existing `extraction_v2.exact_positions` token-boundary guard is reused for
  cell literals and anchors. Raw substring presence is retained separately;
  substring-only cases are ambiguous. Printed symbols are counted literally,
  including adjacency to digits, without assigning currency codes.
- An occurrence is only a **page-text candidate**. A unique candidate requires
  both one exact occurrence and one reference item with that literal within the
  source/kind. Repeated references or repeated occurrences remain ambiguous;
  matching does not consume or assign one occurrence to multiple verified cells.
- Whitespace-only differences are classified separately as fragmentation. No
  punctuation, digits or signs are repaired. If no candidate exists, absent required
  codepoints support an omission classification; otherwise the cause stays unknown.
  Search never bridges separate native blocks or different pages/documents.
- Empty cells are explicit non-text-scorable cases, never successful empty-string
  searches. They stay in the full cell denominator. Failed/needs_review captures
  likewise retain all expected fields; unavailable observations are not successes.
- Only extractor-emitted page/block locators are native provenance. Candidate ranges
  are offsets in the extracted string, not original PDF glyph offsets or bbox evidence.
  Reference boxes, logical row/column assignments and spans are never copied into
  native output or used to invent cell associations.

The private per-item findings record source/item identity, occurrence counts,
reference multiplicity, ambiguity/cause, native locator availability and candidate
evidence fingerprint. Neither a unique page match nor schema validity is counted
as verified cell fidelity. No per-item human approvals are recorded.

## Measured population and results

Both documents remain in all attempted denominators. Each returned `success`, with
one informational `pdf_table_structure_not_preserved` warning and no failure or
review-severity warning. Each native source locator is genuinely
`page_number=1, block_index=0`; table/row/column locators are absent. The native
SourceLocation contract provides no PDF bbox or glyph-range locator.

| Observation | c1-0033 | c1-0040 | Aggregate |
| --- | ---: | ---: | ---: |
| Attempted / successful documents per repetition | 1 / 1 | 1 / 1 | 2 / 2 |
| Native text blocks | 1 | 1 | 2 |
| Native tables / native cells | 0 / 0 | 0 / 0 | 0 / 0 |
| Reference cells, full denominator | 44 | 492 | 536 |
| Nonempty reference cell literals | 44 | 201 | 245 |
| Nonempty cell literals present as raw page substrings | 44 | 201 | 245 |
| Cell literals with boundary-guarded exact page candidates | 42 | 201 | 243 |
| Unique exact page candidates for cell literals | 18 | 8 | 26 |
| Ambiguous exact page candidates for cell literals | 24 | 193 | 217 |
| Substring-only ambiguous cell literals | 2 | 0 | 2 |
| Empty cells, non-text-scorable | 0 | 291 | 291 |
| Whitespace-fragmented / missing cell-literal page observations | 0 / 0 | 0 / 0 | 0 / 0 |
| Reference anchors / exact page presence | 25 / 25 | 37 / 37 | 62 / 62 |
| Unique / ambiguous exact anchor page candidates | 23 / 2 | 12 / 25 | 35 / 27 |
| Reference printed symbols / native literal occurrences | 0 / 0 | 115 / 115 | 115 / 115 |
| Symbol items without a unique source-cell association | 0 | 115 | 115 |
| Reference logical grids / available native grids | 1 / 0 | 5 / 0 | 6 / 0 |
| Cell items lacking native topology | 44 | 492 | 536 |
| Admitted field items / native page context available | 70 / 70 | 649 / 649 | 719 / 719 |

The unique, ambiguous, substring-only and empty cell categories partition all 536
cells. No native cell binding is verified; cell-level fidelity is **NOT_EVALUATED**,
not an inferred 0% or 100% accuracy. Page-level literal presence is a weaker measured
observation. Zero missing/fragmented page-literal observations does not prove zero
cell omissions: repeated text could have come from a different original cell.

All 115 symbol proposals share an ambiguous page-level candidate population; the
observed 115 printed symbols are not 115 verified value-to-cell or unit relationships.
All six logical-grid occupancy checks are unavailable from native output because
no grid topology is emitted. Empty-cell coverage, spans and physical cell identities
cannot be established from the page string.

### Opaque findings and mechanism classification

All 719 item findings are retained in each ignored `diagnostic.json`, with their
complete original admitted-ID population checked against the frozen inventory.
This report publishes counts and opaque identities only, without literal excerpts,
reference annotations or bbox values.

| Observation population | Classification and evidence |
| --- | --- |
| 217 cell items, 27 anchors, 115 symbols | `ambiguous_match`: repeated literal references and/or multiple exact native occurrences; no verified assignment |
| `c1-0033-p1-t0-r19-c0` | `ambiguous_match`: two raw substring occurrences, zero token-boundary-qualified exact candidates; no text omission inferred |
| `c1-0033-p1-t0-r20-c0` | `ambiguous_match`: one raw substring occurrence, zero token-boundary-qualified exact candidates; no text omission inferred |
| 291 empty cells | Explicit empty-cell case; native topology unavailable, so emptiness at the corresponding physical cell is not verified |
| 536 cells, 115 symbol-to-cell observations, six grids | `missing_topology`: no structured native tables/cells; symbol associations and grid occupancy unavailable |
| All 719 admitted field items | `locator_limitation`: page context exists, PDF bbox/cell/glyph provenance does not |
| Page-literal omission / whitespace fragmentation / unknown missing-text cause | Zero observations in this run under the registered matching rules; this is not an assertion of cell-level completeness |

Missing topology is an intentionally unsupported native-baseline capability,
explicitly disclosed by its warning. These observations do not demonstrate a new
parser defect or justify changing production behavior.

## Repeat equality, fingerprints and runtime

Evidence fingerprint, identical across both repetitions:
`a7a46c79f2e61fc496897d654273c7ed5a0307f9c015851473adf43669e3eed2`.

Native extraction fingerprints:

- c1-0033: `332aa3f7c032b0ca4bb3d7ebf44166686758ed23615f4002f0943e3c48bf64cf`.
- c1-0040: `7a5c30d77b9b3ca0933d5a39fc699d4fdf5af9ed4b839ca525355a6ee990898c`.

Every deterministic output was compared byte-for-byte: `pins.json`,
`diagnostic.json` and both native `result.json` captures, four equal files.
Both COMPLETE manifests independently verify all files. Their differences are
confined to hashes of the separately retained runtime.json and resource journals.
`repeat-validation.json` records the exact deterministic-file hashes.

| Source | Run 1 seconds | Run 2 seconds | Run 1 sampled peak tree RSS bytes | Run 2 sampled peak tree RSS bytes |
| --- | ---: | ---: | ---: | ---: |
| c1-0033 | 2.281 | 2.218 | 120,610,816 | 120,926,208 |
| c1-0040 | 2.265 | 2.234 | 121,188,352 | 120,811,520 |

Timing covers fresh spawned-worker startup/imports, unchanged native extraction
and result persistence/polling, not isolated parser-function latency. Workers run
serially on Windows 11 / AMD64, 16 logical CPUs; OS cache was not reset. RSS is
20 ms sampled process-tree resident memory, not an exact allocation high-water mark.
Worker guards are 60 seconds, 1 GiB RSS and 16 MiB output per document; all completed
with successful cleanup and no guard failures. These are offline execution guards,
not new parser limits or an OS security sandbox. Parser defaults remain unchanged,
including 50 MiB input, 2,000 PDF pages, 5,000,000 extracted characters and low-text
threshold 20 non-whitespace characters per page. Inherited OCR-related worker
configuration fields are inactive because every invocation uses `candidate=False`.

Pinned implementation SHA-256:

- Native parser: `6f68e0d08cf640e253bdef05815568c6bfca898379f44b7a80af811b82272167`.
- Native models: `eb8c242decab88df3765634e6ba689ba41863969aa4c3952fd30279b48327e24`.
- Diagnostic: `2b1026723588a670033eda6f0db9d2d3a9c67df125e8eb7f530c6733ad53f80a`.

Full code/config/dependency/host identities are in each pins.json. The diagnostic
and synthetic tests were uncommitted at measurement; HEAD identifies the unchanged
baseline, while the explicit diagnostic hash identifies the measured added code.

## Exact reproduction and verification

Run from repository root with the existing private accepted inputs available.
The unchanged validator accepts the same argument values recorded in the private
validation-config.json; those values identify existing manifests, eligibility,
geometry plan, confirmation and Gold. It is data only, not an executable script.

```powershell
.venv/Scripts/python.exe -m tools.extraction_quality.pdf_native_dev_diagnostic --snapshot local-evaluation/pdf-dev-reference-20261022-v1 --validation-config evaluation-output/pdf-native-dev-diagnostic-20261022/validation-config.json --output evaluation-output/pdf-native-dev-diagnostic-20261022/run-1
.venv/Scripts/python.exe -m tools.extraction_quality.pdf_native_dev_diagnostic --snapshot local-evaluation/pdf-dev-reference-20261022-v1 --validation-config evaluation-output/pdf-native-dev-diagnostic-20261022/validation-config.json --output evaluation-output/pdf-native-dev-diagnostic-20261022/run-2
```

Both commands exited 0 with the evidence fingerprint above. Destinations must be
fresh and ignored; existing output cannot be overwritten. A later reproduction
must use new destinations while retaining the same source/reference/config pins.

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_pdf_native_dev_diagnostic.py -q --basetemp=evaluation-output/pdf-native-dev-diagnostic-20261022/unit-tests
.venv/Scripts/python.exe -m pytest tests/unit/test_pdf_native_dev_diagnostic.py tests/unit/test_pdf_dev_reference.py tests/unit/test_extraction.py tests/unit/test_extraction_v2.py tests/unit/test_dataset_readiness.py -q --basetemp=evaluation-output/pdf-native-dev-diagnostic-20261022/regression-tests
.venv/Scripts/ruff.exe check src tests tools alembic
.venv/Scripts/ruff.exe format --check tools/extraction_quality/pdf_native_dev_diagnostic.py tests/unit/test_pdf_native_dev_diagnostic.py
git diff --check
```

Focused diagnostic tests: **19 passed in 1.58 s**. Combined focused suite:
**108 passed in 9.53 s**, no skipped/deselected tests. Includes duplicate-reference
and occurrence ambiguity, numeric/sign/decimal boundaries, fragmentation, empty
cells, failed/needs_review populations, source/page mismatch, missing original
grid-item identity, config/CLI rejection, reference source drift, malformed decisions,
Gold/test promotion rejection and existing test-family isolation checks.
Ruff passed; both new Python files are formatted; whitespace checks passed.

Before/after SHA receipts verify **12,929 protected files unchanged**, including
originals, the nine-file frozen reference, accepted proposals/decision CSV, frozen
Gold, production extraction code, existing review artifacts and the unrelated audit.
Private evidence remains only in the ignored diagnostic root. No private source
text, PDF payload, literal annotation or source geometry is included in tracked
code/tests/report. Tests use synthetic literals and public synthetic fixtures.

## Remaining dimensions and Git boundary

Semantic roles, header/period relationships, semantic reading order, exact border
fidelity, ambiguous/unruled boundary meaning, currency-code interpretation,
language review, family completeness and reviewer independence remain
**NOT_EVALUATED**. Physical cell alignment, symbol-to-cell association and grid
fidelity are unsupported by these native captures; page matching does not resolve them.

Changed scope: new offline diagnostic, synthetic unit tests and this sanitized
report. No production parser change, feature promotion, Gold promotion or release.
No commit created before review; no push. Existing tracked files and staging area
remain unchanged. Final `git status --short` for this diagnostic step:

```text
?? docs/eda/independent_engineering_audit_20261020.md
?? docs/eda/pdf_native_dev_diagnostic_20261022.md
?? tests/unit/test_pdf_native_dev_diagnostic.py
?? tools/extraction_quality/pdf_native_dev_diagnostic.py
```
