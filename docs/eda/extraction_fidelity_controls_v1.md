# Extraction Fidelity Regression Controls v1

## Outcome and human-review boundary

Three original-document regression controls are now approved and evaluated alongside the frozen
eight-document pilot. All selected control checks pass. All eight original individual scores,
their annotations and the prior pilot report remain unchanged. This establishes a small regression
baseline, not a parser improvement or whole-corpus semantic-fidelity claim.

The user supplied both reviewed JSONL files and explicitly authorized copying them into ignored
local-evaluation/. Each copy is byte-identical to its supplied input. The three control records
declare real data, original_document review, reviewed status, one reviewer and 2026-10-14 review
date. These are user-supplied human attestations: schema validation cannot independently prove
review activity. Codex did not derive labels from parser output, invent metadata, approve drafts
or conduct a second human review. No approved annotation was edited.

The Data quality workflow separates source integrity, human-label coverage and measured parser
behavior. No source excerpts, names, worksheet names, cell coordinates, values, formulas or raw
annotations are included here. Only this sanitized report is intended for Git.

## Frozen identities

- Baseline commit: `0a919ed66589a6dbde7565c027ca49cdf4499eba` (HEAD before this step).
- Gold schema `1.0`, revision `corpus-v1-fidelity-v1`; synthetic opt-in disabled.
- Frozen eight-document normalized Gold fingerprint:
  `14571478ece0193852269c0b6001e616f9f5e32f69d9262e318c128c3b799a9c`.
- Frozen eight-document raw file SHA-256:
  `cde84f713001b1b32e8ac9c5e937a94ffb76b859c2b6255f3102f2b5b8a79636`.
- Three-control normalized Gold fingerprint:
  `98760c2283e4cd1c96085a15e1fc72b766d054ab5eec387bd85c44b7139070b2`.
- Three-control raw file SHA-256:
  `3334edb3e1f01fd3c0665183c838d8a4e9eb0009f7281f6af39565748e1a2c20`.
- Approved eleven-document normalized Gold fingerprint:
  `896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c`.
- Approved eleven-document raw file SHA-256:
  `30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353`.
- Manifest SHA-256:
  `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0`.
- Source identity-map fingerprint:
  `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8`.
- Both new evaluation runs' deterministic fingerprint:
  `43de275fa5e7eb50aab054b53812e4fccaf50df379d949d61cd015c110bb91ee`.

Both approved files pass the existing strict load_gold contract against the frozen manifest.
The combined snapshot contains exactly the original eight IDs plus the three controls, without
duplicates or other records. Its control records equal the separate control file's records.
All eight original raw JSONL record lines and validated objects are identical in the new snapshot;
the original eight-record file's bytes and fingerprint are unchanged.

All 90 originals were verified by SHA-256, size and format: 30 PDF, 30 DOCX and 30 XLSX, without
missing, extra, duplicate, changed or symlinked files. Sources were not replaced or modified.

## Control coverage

| Control | Format | Reviewed scope | Anchors | Order pairs | Table cells | Relationships | Value checks |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| c1-0050 | PDF | Narrative, two original pages, page provenance and partial order | 4 | 3 | 0 | 0 | 0 |
| c1-0008 | DOCX | Body, three original block indices and partial order | 3 | 2 | 0 | 0 | 0 |
| c1-0062 | XLSX | Four exact cell locations on one sheet; stored values and grid relationships | 4 | 3 | 4 | 4 | 4 |
| Controls only | All three | Selected source-grounded expectations | 11 | 8 | 4 | 4 | 4 |

XLSX relationships include two same_row and two same_column checks. All four stored-value
expectations are non-null; all four formula and cache expectations are explicitly null.
Passing formula/cache checks therefore verifies selected stored absence, not formula recovery,
calculation correctness or cached-result reconstruction. No formulas were executed.
Display checks requested: zero; displayed-value fidelity remains NOT_EVALUATED.

Reviewed documents by PDF/DOCX/XLSX: baseline 3/2/3; controls 1/1/1; combined 4/3/4.
The combined snapshot has 55 anchors, 22 order pairs, 32 table-cell checks, 15 relationships and
13 value/formula/cache checks. Provenance denominator is anchors plus cell checks, not unique cells.
All three controls have automated extraction status success; this status alone is not approval.

## Measured results: frozen eight-document baseline

Counts are passed / evaluated expectations, pooled by summing counters rather than averaging
rounded document percentages. NE means NOT_EVALUATED with null score, not zero or perfect fidelity.
These results reproduce the completed pilot without rewriting it.

| Metric | PDF (3) | DOCX (2) | XLSX (3) | Pooled (8) |
| --- | ---: | ---: | ---: | ---: |
| Required-text recall | 6/15 | 11/12 | 17/17 | 34/44 (77.27%) |
| Reading order | 1/7 | 4/4 | 3/3 | 8/14 (57.14%) |
| Table-cell/span fidelity | 0/4 | 7/7 | 17/17 | 24/28 (85.71%) |
| Table relationships | 0/2 | 3/3 | 6/6 | 9/11 (81.82%) |
| Stored-value equality | NE | NE | 9/9 | 9/9 |
| Formula equality, including null | NE | NE | 9/9 | 9/9 |
| Cache equality, including null | NE | NE | 9/9 | 9/9 |
| Provenance correctness | 2/15 | 11/12 | 26/26 | 39/53 (73.58%) |
| Missing required anchors | 9 | 1 | 0 | 10 |

## Measured results: controls only

| Metric | PDF (1) | DOCX (1) | XLSX (1) | Pooled (3) |
| --- | ---: | ---: | ---: | ---: |
| Required-text recall | 4/4 | 3/3 | 4/4 | 11/11 (100%) |
| Reading order | 3/3 | 2/2 | 3/3 | 8/8 (100%) |
| Table-cell/span fidelity | NE | NE | 4/4 | 4/4 (100%) |
| Table relationships | NE | NE | 4/4 | 4/4 (100%) |
| Stored-value equality | NE | NE | 4/4 | 4/4 |
| Formula equality, including null | NE | NE | 4/4 | 4/4 |
| Cache equality, including null | NE | NE | 4/4 | 4/4 |
| Provenance correctness | 4/4 | 3/3 | 8/8 | 15/15 (100%) |
| Missing required anchors | 0 | 0 | 0 | 0 |

PDF and DOCX controls have no table labels: those dimensions are NOT_EVALUATED for these controls.
The XLSX control alone supplies the additional table checks.

## Measured results: combined eleven-document snapshot

| Metric | PDF (4) | DOCX (3) | XLSX (4) | Pooled (11) |
| --- | ---: | ---: | ---: | ---: |
| Required-text recall | 10/19 | 14/15 | 21/21 | 45/55 (81.82%) |
| Reading order | 4/10 | 6/6 | 6/6 | 16/22 (72.73%) |
| Table-cell/span fidelity | 0/4 | 7/7 | 21/21 | 28/32 (87.50%) |
| Table relationships | 0/2 | 3/3 | 10/10 | 13/15 (86.67%) |
| Stored-value equality | NE | NE | 13/13 | 13/13 |
| Formula equality, including null | NE | NE | 13/13 | 13/13 |
| Cache equality, including null | NE | NE | 13/13 | 13/13 |
| Provenance correctness | 6/19 | 14/15 | 34/34 | 54/68 (79.41%) |
| Missing required anchors | 9 | 1 | 0 | 10 |

Displayed-value fidelity is NOT_EVALUATED for every format and population. Combined formula
equality includes five non-null expectations and eight reviewed nulls; cache equality includes
six non-null expectations and seven reviewed nulls. These are not thirteen evaluated calculations.
The higher pooled rates result only from adding passing controls and changing denominators;
they must not be reported as a parser improvement over the eight-source pilot.

## Frozen individual-score regression comparison

Each original record was scored with the unchanged score_record against the same current
extraction using both old and combined Gold. Full metric objects (status, passed, evaluated,
unsupported and score) and missing counts matched for all eight. Counters also matched the
prior pilot audit, and their aggregate equaled the retained pilot CLI report. All 90 per-document
extraction/chunk metadata and code/configuration identities match that prior report exactly.

| Original source | Recall | Order | Table cells | Relationships | Provenance | Missing | Comparison |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| c1-0006 | 5/5 | 2/2 | 3/3 | 1/1 | 5/5 | 0 | Unchanged |
| c1-0007 | 6/7 | 2/2 | 4/4 | 2/2 | 6/7 | 1 | Unchanged |
| c1-0041 | 0/4 | 0/3 | NE | NE | 0/4 | 4 | Unchanged |
| c1-0044 | 0/5 | 0/2 | NE | NE | 0/5 | 5 | Unchanged |
| c1-0045 | 6/6 | 1/2 | 0/4 | 0/2 | 2/6 | 0 | Unchanged |
| c1-0067 | 5/5 | 1/1 | 5/5 | 2/2 | 8/8 | 0 | Unchanged |
| c1-0071 | 6/6 | 1/1 | 6/6 | 2/2 | 9/9 | 0 | Unchanged |
| c1-0081 | 6/6 | 1/1 | 6/6 | 2/2 | 9/9 | 0 | Unchanged |

All three original XLSX records retain 3/3 stored-value, formula and cache equality each;
original PDF/DOCX value metrics remain NOT_EVALUATED. No original display checks were added.
The corrected c1-0067/a5 span remains 1x3. Known nine PDF missing anchors, four failed PDF table
cells, two failed PDF relationships and one missing DOCX footnote anchor remain unresolved.
The six prior failed order pairs had unresolved locations/evidence, not proven resolved inversions.

## Evaluator reproducibility and environment

Both new runs processed all 90 originals and exactly 11 reviewed documents. Every non-runtime
JSON field matched, not merely the fingerprint string. The fingerprint was recomputed from each
report with runtime and the fingerprint field removed. All per-format counter totals reconcile
with the CLI's combined reviewed_fidelity aggregate; the baseline group reconciles with the
retained eight-source report. The separate control file and combined control subset score equally.

Unchanged environment: Windows Python 3.12.3; pypdf 6.20.0, python-docx 1.2.0, openpyxl 3.1.5,
Pydantic 2.14.0. Parser, extraction models, evaluator, Gold contract, chunking core, protocol,
manifest and pilot report bytes equal baseline commit versions. Existing extraction limits and
structure-aware chunking configuration are unchanged; experiments were disabled.
Automated corpus status remains 56 success, 34 needs_review and zero failed documents.
Production review gating, ingestion and canonical identities were not relaxed.

Runtime extraction observations only (30 per format per run; milliseconds, nearest-rank
percentiles; excludes hashing, chunking and Gold scoring):

| Format | Run 1 p50 / p95 | Run 2 p50 / p95 |
| --- | ---: | ---: |
| PDF | 44.320 / 1192.899 | 41.607 / 1134.061 |
| DOCX | 19.600 / 446.626 | 19.181 / 445.285 |
| XLSX | 8.377 / 477.038 | 8.566 / 422.018 |

Timing is not deterministic or an SLA/throughput benchmark; the first pass overlapped unit tests.

## Executed verification

Commands ran from the repository root using the existing local virtual environment:

```powershell
git rev-parse HEAD
git merge-base --is-ancestor 0a919ed66589a6dbde7565c027ca49cdf4499eba HEAD
./.venv/Scripts/python.exe -m ruff check src tests alembic
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_extraction_fidelity.py
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
./.venv/Scripts/python.exe -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_controls_reviewed.jsonl --output-dir evaluation-output/fidelity-controls-v1-approved-run1
./.venv/Scripts/python.exe -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_controls_reviewed.jsonl --output-dir evaluation-output/fidelity-controls-v1-approved-run2
git diff --check
git status --short
```

Baseline ancestry: exit 0. Ruff: all checks passed. Focused fidelity: 34 passed in 1.54 s.
Full unit suite: 418 passed in 10.53 s. Both evaluator commands: exit 0, 90 documents,
11 reviewed and the identical deterministic fingerprint recorded above.

Python stdin audits invoked existing load_gold, _read_sources, verify_corpus, extract_file,
score_record and fingerprint without code changes. Assertions verified all three Gold files,
expected fingerprints, exact membership, original raw record equality, 90 source identities,
all non-runtime fields, original individual scores, per-format/pooled arithmetic and byte-preserved
baseline files. Third-party parser output was suppressed. Metadata reports contain no content or
private locator keys, source filenames/paths or distinctive Gold excerpts. Copies were verified
with SHA-256; approved Gold files and runtime directories are ignored and excluded from staging.
Final report privacy, diff and staged-path checks must pass before the report-only commit.

No database/integration, Docker or service test was needed or run for this offline documentation
step. No new dependency, parser candidate, infrastructure or production change was introduced.

## Interpretation and next gate

The three controls provide useful narrative PDF, DOCX body and XLSX grid/value regression checks
before a separately scoped candidate experiment. Narrative PDF controls alone do not prove
generalization of PDF table reconstruction; PDF table labels still come from one difficult source.
The recommended first candidate remains bounded PDF table/provenance extraction for c1-0045,
evaluated on this frozen eleven-source snapshot without degrading any original or control score.
It has NOT been implemented or evaluated here.

One reviewer, selected partial-order pairs and eleven purposively selected sources do not
establish inter-reviewer agreement, representative corpus-wide fidelity, full document coverage
or generalization. Literal recall is not semantic entailment and can pass at a wrong location;
provenance is separate. No additional ancillary, display, OCR, rotated-table, multilingual,
retrieval or RAG quality claim is supported. Logical resource bounds are not hard CPU/RSS caps.
Keep missing evidence and unchanged failures visible when judging any future candidate.
