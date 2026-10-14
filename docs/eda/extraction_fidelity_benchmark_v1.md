# Extraction Fidelity Benchmark v1

## Decision and evidence boundary

**Automated baseline reproduced. Reviewed extraction fidelity: NOT_EVALUATED.**
No human-reviewed Fidelity Gold was locally available for this step. An eight-source PRIVATE draft
template was generated, with no excerpts, no asserted reviews and no fabricated labels. The 48
reviewed Retrieval Gold questions / 80 anchors are a different instrument: they do not establish
missing-content, reading-order, table or display-value rates. Do not import them as Fidelity Gold.

The Data quality workflow separates completeness/integrity/contract observations from semantic
labels and ties each issue to downstream risk. The protocol and executable evaluator/tests are the
inspectable evidence path required for this repository task; no extra dashboard or notebook was
created outside its allowed scope. No production behavior, dependency, migration or corpus changed.

## Frozen reproduction and identities

Baseline commit: `d4c978c5ae9932d8c49038ce43ea947aaf6cc414`.
All 90 original documents matched the unchanged committed manifest by hash, size and extension;
90 unique SHA-256 values, zero missing/extra/duplicate/changed sources, 30 per format.
Total source size: 10,431,532 bytes. Existing manifest permission/provenance remains the approved
GOV.UK / OGL v3.0 acquisition basis; this step neither reacquired sources nor re-certified licences.

Windows Python 3.12.3; pypdf 6.20.0, python-docx 1.2.0, openpyxl 3.1.5, Pydantic 2.14.0.
Hashes (SHA-256):

- Manifest bytes: `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0`.
- Canonical source identity map: `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8`.
- Unchanged parser: `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8`.
- Unchanged extraction contract: `0725bb86ebeea07926ab813e91625857fb68e97f3b35e30ecf8d9cb3c7259876`.
- Unchanged chunking core: `6a6f8f4feac9076a27ed178e00049c85c27afb89a077cb22658e6c2350ca6a80`.
- Fidelity evaluator: `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c`.
- Fidelity Gold contract: `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af`.

The existing extraction CLI reproduced its historical structured-baseline content fingerprint
`9731990eb079537823183e80d652f6c6e67b110cec4ccb7ff2ca0b137ea73ec9` exactly.
This is not the older count-only profiler fingerprint from corpus_v1_assessment.md.
Fidelity report uses opaque manifest IDs and extra checks, so it has its own deterministic identity:
`874bf2ee1aefdf6e26adef077feb8269952763bf1d1fc1b7804e0451d4216809`.
All non-runtime fields are compared across repeated identical runs, not just the fingerprint field.

Default extraction limits remain unchanged: 50 MiB/file, 2,000 PDF pages, 20,000 Office entries,
100 MiB/member, 500 MiB decompressed/archive, 200x compression ratio, 5M extracted characters,
100,000 blocks, 1M table-grid/stored-XLSX cells, 256 sheets, 100,000 merges, 10,000 XLSX tables.
PDF review threshold is 20 non-whitespace characters/page. No limit was relaxed for the corpus.
Structure-aware chunking 1.0: 1,200 characters, 120 overlap, review skipped, 5M source characters,
100,000 chunks/document, formula plus cache without execution. Config fingerprint:
`a7c53272ac7baa3f916e43dc4b96a455fa0daa1437cafe04fd7c90b2840edc4c`.

## Automatic observations (not fidelity scores)

| Format | Documents | success | needs_review | failed | Extract p50 / p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF | 30 | 27 | 3 | 0 | 62.584 / 1,357.535 |
| DOCX | 30 | 14 | 16 | 0 | 24.496 / 573.374 |
| XLSX | 30 | 15 | 15 | 0 | 9.816 / 466.213 |
| Total | 90 | 56 | 34 | 0 | Not pooled |

Timing is one serial pass on the local Windows environment with concurrent regression activity;
30 observations/format, nearest-rank percentiles. Excludes auditing, chunking and experiments.
It is not a production latency SLO or a candidate-speed comparison.

2,461 text blocks, 292 DOCX tables plus 13 XLSX table definitions (305 total), 4,931 logical DOCX
table cells, 88 sheets and 98,006 meaningful XLSX cells. 1,077 text blocks are whitespace-empty,
mostly empty DOCX paragraphs; this is not 1,077 failed documents. The two near-empty PDF cases
below contain five whitespace-empty pages between them.

107,425 text/unique-cell-field observations have a basic locator present (107,425/107,425).
That check does NOT prove that the locator is semantically correct. Default chunking processes 56
documents and skips all 34 review cases; 1,092 chunks, 1,071,696 normalized source characters,
all represented in provenance spans. These are contract-coverage measures, not original-document
recall or retrieval quality. No extraction failures/resource-limit outcomes occurred in this run.

| Warning category | Documents | Occurrences/count units |
| --- | ---: | ---: |
| pdf_table_structure_not_preserved (informational) | 30 | 30 |
| spreadsheet_drawings_not_extracted | 11 | 20 |
| headers_not_extracted | 9 | 10 |
| footers_not_extracted | 8 | 13 |
| formula_definition_unavailable | 7 | 3,797 cells |
| drawings_not_extracted | 6 | 24 |
| unsupported_body_content_not_extracted | 5 | 20 |
| nested_tables_not_extracted | 4 | 7 |
| insufficient_text | 3 | 6 pages |
| footnotes_not_extracted | 3 | 3 |
| formula_cached_value_missing | 3 | 735 cells |
| text_boxes_not_extracted | 2 | 6 |
| spreadsheet_comments_not_extracted | 1 | 1 |

Occurrences have category-specific units and must not be summed into a semantic error rate.
Shared-formula definition gaps and missing caches are the largest observed cell-level warnings.
PDF table limitation is informational, so `success` can coexist with absent structured tables.

## Reviewed label coverage and metrics

Reviewed Fidelity documents: PDF 0, DOCX 0, XLSX 0; anchors 0, order pairs 0, table checks 0,
cell checks 0. Human review performed in this step: **none**. Synthetic unit cases test arithmetic
and contracts only and are not included in the real-corpus report.

Required-text recall, missing-evidence count, reading-order correctness, table-cell fidelity,
table-relationship fidelity, stored-value/formula/cache fidelity and semantic provenance:
**NOT_EVALUATED** (zero reviewed denominators). Display-value fidelity: **NOT_EVALUATED**, also
unsupported by the frozen extraction contract. No zero-score or perfect-quality inference.

## Priority errors: new automated evidence vs historical review

All counts/inventories below were newly measured; original visual-fidelity statements are explicitly
historical findings from corpus_v1_assessment.md / extraction_baseline_v1.md, NOT new human labels.

### PDF

- `c1-0041`: preserves four page locators, zero text characters; four low-text warnings, review
  skipped. Historical visual review found visible prose. Automatically measurable: near-empty
  output, not visible-text recall. High risk: no searchable evidence. Candidate: separate bounded
  OCR feasibility study after rendered-page labels and explicit dependency approval.
- `c1-0044`: one page, two whitespace characters, one low-text warning, review skipped.
  Historical review identified a labeled flowchart. Automatically measurable: empty normalized
  extraction; diagram labels/branch semantics need review. High risk: missing branch evidence.
  Candidate: OCR plus diagram-specific ordering/relationship labels, not plain layout alone.
- `c1-0045`: seven page blocks, 39,260 characters, success, 38 chunks, zero structured tables.
  Historical page-1 review found row/column association loss in a dense table. Automatically
  measurable: no table output; relationship accuracy requires reviewed cells. High risk: numbers
  retrieved without their correct row/header. Candidate: isolated table-aware PDF experiment.

### DOCX

- `c1-0006`: retains 388 top-level paragraphs, 126 interleaved tables, 542 logical cells;
  footer warning leads to review skip. Original OOXML inventory: 41,938 main-part text characters,
  two ancillary characters, no nested tables. Historical comparison found order/merged-cell
  preservation in the structured baseline. New counts do not re-certify all text/order.
  Risk: footer evidence missing, entire document excluded. Candidate: explicit ancillary blocks
  with separate region locators; do not blindly append header/footer strings to every section.
- `c1-0007`: retains 382 paragraphs, ten tables, 1,467 logical cells, with header/footer/footnote,
  drawing, unsupported-body and nested-table warnings. New XML inventory: 45,847 main-part and
  1,125 ancillary text characters; four nested table elements, versus three frozen parser nested
  warning count units. This difference demonstrates different traversal scopes, not four proven
  missing tables. Structural inventories are automatic; exact omitted-content/order recall needs
  reviewed anchors. Risk: missing notes/ancillary/nested evidence and full review skip. Candidate:
  bounded recursive traversal with ancestor/region provenance and merge deduplication tests.

### XLSX

- `c1-0067`: one sheet, 294 meaningful cells, 44 merges, 107 formula definitions and 110 caches;
  original XML has 2,023 stored cells and 110 formula-bearing cells, three missing definitions,
  zero missing caches. All 2,023 stored cells are styled (including empty style-only cells).
  Automatic: sparse/formula/cache inventory. Not measured: rendered labels, numeric formatting
  or formula correctness. Risk: shared formulas unavailable; display ambiguity; review skip.
  Candidate: resolve shared definitions without executing formulas; reviewed display expectations.
- `c1-0071`: seven sheets, 512 meaningful cells, five merges and four table definitions; review
  warning for two drawings. Original XML stores 913 cells, 876 styled; one sheet advertises the
  maximum Excel row. Unlike the OLD profiler, the current sparse baseline does not falsely fail
  on that dimension. Automatically measurable: sparse success, dimension and structure counts.
  Risk: drawing-only evidence and display loss; no renewed false-dimension bug is claimed.
  Candidate: preserve sparse iteration and separately evaluate drawings/display semantics.
- `c1-0081`: twelve sheets, 1,088 meaningful cells, 45 merges, three formulas and three caches;
  drawing warning causes review skip. XML has 2,503 stored cells, 2,502 styled, no formula/cache
  gap. Coordinates/merges are retained; styles/display are absent from ExtractionResult.
  Risk: misleading numeric/date display interpretation or missing drawing evidence. Candidate:
  independently annotated stored-vs-displayed relationships, without recalculation.

OOXML total characters include different containers; never subtract them from emitted paragraph
counts and call that semantic missing-text rate. Style counts alone do not prove display errors.

## Controlled experiments and candidate feasibility

Only three priority PDFs were compared using installed pypdf; both layout variants use default
settings except explicit `layout_mode_strip_rotated=False` in the second. No debug/text output.

| ID | Pages | Plain chars | Layout default chars | Include rotated chars | Non-whitespace equal pages (both) |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1-0041 | 4 | 0 | 0 | 0 | 4 |
| c1-0044 | 1 | 2 | 0 | 0 | 1 |
| c1-0045 | 7 | 39,260 | 7 | 7 | 0 |

No recovery observed for the first two cases; on c1-0045 both candidates drastically reduce output.
Cause within font/layout internals was not diagnosed and semantic candidate quality is unreviewed.
Do NOT adopt layout globally. Installed dependency can support a focused future experiment without
new library cost, but this evidence fails even a conservative content-retention prerequisite.
A synthetic blank page without `/Contents` also causes layout to fail; evaluator isolates it.
Version-matched primary reference: [pypdf 6.20.0 text extraction documentation](https://pypdf.readthedocs.io/en/6.20.0/user/extract-text.html).
It documents layout controls and limitations; it does not certify these corpus outcomes.
No documentation MCP providing pypdf was exposed; official version-matched docs were used.

Other candidates assessed, NOT installed or benchmarked:

| Priority / candidate | Expected benefit | Complexity/resource cost | Required acceptance evidence / risk |
| --- | --- | --- | --- |
| 1: Reviewed original labels | Separate missing evidence from contract success | Human review, no runtime dependency | Freeze hard cases plus controls; avoid parser-output-only labels |
| 2: Table-aware PDF (e.g. pdfplumber candidate) | Explicit rows/columns for numeric evidence | New parser dependency, geometry CPU/memory; separately cap pages/streams | Review c1-0045 rows/headers/merges, prose controls, exact source provenance; no silent fallback |
| 3: DOCX ancillary/nested traversal using installed OOXML/python-docx | Recover notes/header/footer/nested evidence | Moderate code/schema work, bounded recursion; no new library needed initially | Reviewed part/ancestor locators, no duplicated inherited headers/merged cells, reading-order policy |
| 4: XLSX style-aware display policy using installed openpyxl/OOXML | Distinguish stored serial/number from displayed date/percent/currency | Medium/high policy work; locale/date-system/custom-format ambiguity | Reviewed rendered examples, 1900/1904 date systems, null/error/cache cases; never execute formulas |
| 5: Shared formula expansion | Preserve follower formula definitions | Moderate bounded translation logic | Relative/absolute refs, unavailable bases, caches/external references, no execution |
| Separate OCR proposal (e.g. local Tesseract + PDF renderer) | Recover image/diagram labels | New approved engine/renderer/language assets, page-image RAM and CPU | Explicit approval, rendered anchors, measured character/word recall/order, caps; OCR alone not diagram semantics |

These are feasibility hypotheses, not measured benefits or adoption authorizations. Table-aware
libraries, Office renderers, OCR and layout models were not used in this experiment. No new
dependency was added. An extraction contract extension would need its own scoped implementation
and compatibility evaluation; none is bundled here.

## Retrieval implications and limitations

Seven of eight hard cases are excluded by the current review gate; c1-0045 remains eligible despite
missing structured PDF tables. This is an evidence-availability/association risk, not a measured
retrieval regression or evidence to loosen the gate. Corpus is small, GOV.UK-biased and mostly
English; prior selected retrieval labels and successful chunk coverage cannot prove complete
document recall, semantic provenance, faithful answers or multilingual quality.

All existing logical resource bounds remain; no hard RSS/CPU deadline or hostile-document safety
claim. Peak memory, candidate latency, rendered Office display, OCR, table-aware candidates,
semantic candidate superiority, retrieval and RAG quality are NOT_EVALUATED here.

## Executed reproduction and checks

Commands use the local `.venv/Scripts/python.exe` where `python` is shown:

```powershell
python -m ruff check src tests alembic
python -m pytest -q -p no:cacheprovider tests/unit/test_extraction_fidelity.py
python -m pytest -q -p no:cacheprovider tests/unit
python -m doclens_ai.extraction --input-dir local-corpus --output-dir .eda-output/fidelity-baseline-reproduction
python -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --output-dir evaluation-output/fidelity-v1-run1 --annotation-template local-evaluation/extraction_fidelity_v1_draft.jsonl --experiments
python -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --output-dir evaluation-output/fidelity-v1-verified1 --experiments
python -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --output-dir evaluation-output/fidelity-v1-verified2 --experiments
```

Ruff passed; focused tests 34 passed; unit suite 418 passed. Early synthetic-test failures (one
fixture argument, sandbox file rename, blank PDF layout expectation) were corrected/retested;
production code was not changed. Only the final evaluator identity is cited above; initial
implementation runs have different code fingerprints and are not interchangeable benchmark runs.
Metadata-only fixture tests assert no private content/filename/sheet/error/path appears in reports.
The exact full-regression command `python -m pytest -q -p no:cacheprovider` ran inside a disposable
application-compatible Docker test runtime: **554 passed in 385.21 s, zero skips**, including real
PostgreSQL, MinIO, Qdrant and migrations. Its read-only source snapshot contained tracked files plus
new evaluator/Gold/tests, no corpus/Gold/model assets; isolated service network, no published ports.
Existing pytest dev dependencies were installed only in that disposable runtime. Initial PostgreSQL
readiness was transiently negative; later readiness passed. Bucket initialization initially lacked
the local HTTP test flag, then passed with S3_SECURE=false only in the disposable test runtime.
No production settings were changed. All temporary task-owned infrastructure was removed afterward.

Repeated final real-corpus runs had identical complete non-runtime JSON and the fingerprint above.
Final Ruff and host unit regression passed again. Git diff/status/check and allowlisted staging were
inspected before the requested commit; private runtime outputs/template remain ignored, not staged.
