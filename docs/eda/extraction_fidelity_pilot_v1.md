# Human-reviewed Extraction Fidelity Pilot v1

## Decision and human-review boundary

The first reviewed pilot is complete on eight difficult Corpus v1 documents. This is an offline
measurement of the unchanged baseline, NOT a parser improvement or whole-corpus fidelity claim.
PDF missing text/table provenance and one DOCX footnote omission remain measured failures.

The user supplied the private reviewed Gold and explicitly confirmed the correction of
`c1-0067/a5` to `row_span=1`, `column_span=3`. All eight records declare `reviewed`,
`review_basis=original_document`, `dataset_kind=real`, one reviewer and review date 2026-10-14.
These are user-supplied human-review attestations. Codex did not generate source annotations,
approve drafts, assign dates or perform an independent second human review/adjudication.
At the user's request the approved file was copied byte-for-byte into ignored local-evaluation/;
original input and copied Gold were not edited. No raw annotation, excerpt, source name, worksheet
name, value, formula, original document or private absolute path is included in this report.

The Data quality workflow keeps source integrity, automatic contract status and reviewed
expectations separate. Literal matching and schema validation do not prove exhaustive semantic
coverage or independently certify the reviewer's decisions.

## Frozen identities and reproduction

- Baseline commit: `3b7e5c32ece19b45ea5aa5fc061c0b7c8b856fc6`.
- Gold schema `1.0`, revision `corpus-v1-fidelity-v1`.
- Corrected normalized Gold fingerprint:
  `14571478ece0193852269c0b6001e616f9f5e32f69d9262e318c128c3b799a9c`.
- Approved raw Gold bytes SHA-256:
  `cde84f713001b1b32e8ac9c5e937a94ffb76b859c2b6255f3102f2b5b8a79636`.
- Manifest SHA-256:
  `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0`.
- Source identity-map fingerprint:
  `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8`.
- Unchanged parser SHA-256:
  `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8`.
- Unchanged evaluator / Gold contract SHA-256:
  `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` /
  `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af`.
- Repeated corrected-run deterministic fingerprint:
  `9fc311d65122b6c2d859843b84a141b47ff506c0c87ab7397830d3067e9fa043`.

Both new runs verified all 90 original files against the unchanged manifest: 30 PDF, 30 DOCX,
30 XLSX, matching SHA-256, size and extension, with no missing, extra, duplicate or changed files.
Every Gold source identity matches the manifest. All non-runtime JSON fields were identical,
including per-document extraction/chunk fingerprints and reviewed scores; comparison was not
limited to the fingerprint field. No corpus replacement or production-state write occurred.

Environment: Windows Python 3.12.3, pypdf 6.20.0, python-docx 1.2.0, openpyxl 3.1.5,
Pydantic 2.14.0. Existing ExtractionLimits were unchanged. Existing structure-aware chunking 1.0
uses 1,200 characters / 120 overlap, review skipped, formula+stored cache without execution;
config fingerprint `a7c53272ac7baa3f916e43dc4b96a455fa0daa1437cafe04fd7c90b2840edc4c`.
Experiments and synthetic opt-in were disabled. Logical resource bounds are not hard CPU/RSS caps.

## Corpus status versus reviewed coverage

| Format | Corpus n | success | needs_review | failed | Reviewed pilot n |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF | 30 | 27 | 3 | 0 | 3 |
| DOCX | 30 | 14 | 16 | 0 | 2 |
| XLSX | 30 | 15 | 15 | 0 | 3 |
| Total | 90 | 56 | 34 | 0 | 8 |

The eight sources are c1-0041, c1-0044, c1-0045; c1-0006, c1-0007; c1-0067, c1-0071, c1-0081.
Seven have extraction needs_review; only c1-0045 is success. Gold scoring evaluates these review
cases without relaxing production chunk eligibility. Extraction success is not a fidelity score.

| Format | Text anchors | Order pairs | Table cells | Table relationships | Cell value/formula/cache checks |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF | 15 | 7 | 4 | 2 | 0 |
| DOCX | 12 | 4 | 7 | 3 | 0 |
| XLSX | 17 | 3 | 17 | 6 | 9 |
| Total | 44 | 14 | 28 | 11 | 9 |

Only one ancillary-region anchor is present (DOCX footnote). Headers, footers, nested ancestry,
diagram graph relations, drawing-only spreadsheet evidence and display formatting are not broadly
covered. No synthetic fixtures enter these real-source scores. Control labels are absent.

## Measured fidelity: passed / evaluated expectations

Metrics use the unchanged score_record implementation and protocol v1 denominators. Per-format
results sum counters by format, not rounded document percentages; their totals were asserted equal
to the CLI aggregate. Provenance denominator is anchors plus cell checks, not unique source cells.

| Metric | PDF | DOCX | XLSX | Pilot pooled |
| --- | ---: | ---: | ---: | ---: |
| Required-text recall | 6/15 (40.00%) | 11/12 (91.67%) | 17/17 (100%) | 34/44 (77.27%) |
| Reading-order correctness | 1/7 (14.29%) | 4/4 (100%) | 3/3 (100%) | 8/14 (57.14%) |
| Table-cell/span fidelity | 0/4 (0%) | 7/7 (100%) | 17/17 (100%) | 24/28 (85.71%) |
| Table-relationship fidelity | 0/2 (0%) | 3/3 (100%) | 6/6 (100%) | 9/11 (81.82%) |
| Stored-value equality | NOT_EVALUATED | NOT_EVALUATED | 9/9 (100%) | 9/9 (100%) |
| Formula equality (including null) | NOT_EVALUATED | NOT_EVALUATED | 9/9 (100%) | 9/9 (100%) |
| Cached-value equality (including null) | NOT_EVALUATED | NOT_EVALUATED | 9/9 (100%) | 9/9 (100%) |
| Provenance correctness | 2/15 (13.33%) | 11/12 (91.67%) | 26/26 (100%) | 39/53 (73.58%) |
| Display-value fidelity | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED |
| Missing required anchors | 9 | 1 | 0 | 10 |

Text recall is literal whitespace-normalized presence anywhere in extracted fields, NOT semantic
entailment or location-aware recall. Provenance is scored separately. Four present PDF table
anchors fail structured locators despite passing text recall. Table relationships cannot pass
merely because both strings occur in flat page text.

Formula equality includes five non-null formula expectations and four reviewed nulls. Cache
equality includes six non-null caches and three reviewed nulls. Thus 9/9 is NOT nine successfully
reconstructed formulas or nine verified calculations. An expected null shared-formula definition
tests stored absence, not recovery of a resolved follower formula. No formulas were executed.
No display checks were requested; the frozen contract also lacks a display-value field.
Absent/unsupported labels remain NOT_EVALUATED, never a zero or perfect inferred score.

## Missing evidence and high-impact cases

| Source | Required text present | Missing anchors | Main measured failure |
| --- | ---: | ---: | --- |
| c1-0041 | 0/4 | 4 | Required PDF text absent |
| c1-0044 | 0/5 | 5 | Required PDF labels absent |
| c1-0045 | 6/6 | 0 | Structured table cells 0/4, relationships 0/2, provenance 2/6 |
| c1-0006 | 5/5 | 0 | No failed selected checks; ancillary coverage not established |
| c1-0007 | 6/7 | 1 | One reviewed footnote anchor absent; selected body/table checks pass |
| c1-0067 | 5/5 | 0 | Corrected merged-cell span passes; selected table cells 5/5 |
| c1-0071 | 6/6 | 0 | No failed selected checks; sparse/display/drawing completeness not certified |
| c1-0081 | 6/6 | 0 | No failed selected checks; unannotated sheets/display/drawings not certified |

Diagnostic classification found six failed order pairs with unresolved evidence/locations:
three in c1-0041, two in c1-0044, one in c1-0045. There were zero inversions among resolved pairs.
The low PDF order score therefore must not be described as six demonstrated text permutations.

The former c1-0067/a5 mismatch was an incorrect Gold column_span=1. Original OOXML merge and
baseline output both indicate 1x3; the user confirmed column_span=3. XLSX table-cell score changes
from the prior provisional 16/17 to 17/17 exclusively because the expectation was corrected.
The earlier normalized Gold fingerprint was
`fc00a80d4f622bf1ea20d08b075bbbd967f63a7d24288b6867e5c7ea24d96705`.
This is a label correction, NOT a parser quality gain or a comparable candidate experiment.

## Priorities and regression controls

1. First narrow parser candidate: explicit PDF table rows/columns and source provenance for
   c1-0045. It is currently eligible despite failed table checks; incorrect number/header
   associations can affect retrieval evidence. Evaluate a separately scoped, bounded candidate
   against this frozen Gold plus controls before adopting it. No new parser dependency is adopted.
2. Missing-text handling for c1-0041/c1-0044: nine absent anchors warrant a separate OCR feasibility
   proposal with explicit dependency approval and reviewed page/order/diagram labels. Do not loosen
   the review gate or assume PDF layout mode restores text.
3. DOCX footnote extraction with a clear region/provenance policy: c1-0007 supplies one concrete
   missing-evidence case. Evaluate any contract extension separately; it must not silently alter
   canonical identities or merge ancillary content into body text without traceability.
4. Extend reviewed controls and difficult XLSX formula/cache/display cases before pursuing a broad
   spreadsheet change. The nine equality checks do not establish workbook-wide formula fidelity.

Recommended controls remain c1-0050 (narrative PDF), c1-0008 (DOCX), c1-0062 (XLSX). They are not in
the submitted Gold: reviewed control documents/anchors = 0, measured control fidelity =
NOT_EVALUATED. Their earlier automatic success is not human approval. Add genuine original-based
labels in a new frozen Gold snapshot before judging candidate regression safety; do not silently
expand this pilot. This pilot measures extraction risks, not retrieval/answer performance gains.

## Executed verification and reproduction

Commands below ran from the repository root with local `.venv/Scripts/python.exe` as `python`:

```powershell
python -m ruff check src tests alembic
python -m pytest -q -p no:cacheprovider tests/unit/test_extraction_fidelity.py
python -m pytest -q -p no:cacheprovider tests/unit
python -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_reviewed.jsonl --output-dir evaluation-output/fidelity-pilot-v1-corrected-run1
python -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_reviewed.jsonl --output-dir evaluation-output/fidelity-pilot-v1-corrected-run2
git diff --check
git status --short
```

Ruff: all checks passed. Focused tests: 34 passed in 2.30 s. Full unit suite: 418 passed in 10.40 s.
Both real-corpus runs returned 90 documents, eight reviewed sources and the identical fingerprint
above. Strict load_gold ran without allow_synthetic; expected Gold fingerprint and a5 span were
asserted. Per-format counters reconciled with all CLI metric totals; corrected XLSX table cells
were explicitly asserted to be 17/17. Full non-runtime report comparison passed.

Per-format arithmetic reuses the existing functions, without editing evaluator or tests:

```python
sources = _read_sources(Path("docs/eda/corpus_v1_manifest.csv"))
originals = verify_corpus(Path("local-corpus"), sources, ExtractionLimits())
records = load_gold(Path("local-evaluation/extraction_fidelity_v1_reviewed.jsonl"), sources)
# For each reviewed record: extract_file(originals[record.document_id]), then score_record.
# Sum passed/evaluated/unsupported by document_format and metric; assert each pooled total
# equals the corresponding reviewed_fidelity metric in the CLI report. Export counters only.
```

Before commit, the report diff, Git status and staging allowlist were reviewed. Gold, raw sources,
private checklist and both runtime directories are ignored/untracked and must never be staged.
The approved Gold byte hash was checked unchanged after evaluation; only this sanitized report
belongs in the completion commit. No database/integration suite was rerun for this documentation-
only step; PostgreSQL, Qdrant, ingestion, chunking, embeddings, RAG and migrations were unchanged.

## Methodological limits

Eight deliberately difficult sources, one reviewer, 44 anchors and small selected table/value
samples are not representative whole-corpus fidelity. There is no inter-reviewer agreement,
independent visual re-review, held-out control score or exhaustively verified source coverage.
Only one footnote anchor covers ancillary content; source-region correctness outside selected
labels remains unknown. Substring recall, expected nulls and unresolved-order pairs require the
separate interpretations above. Logical parser resource bounds do not establish hostile-input
safety or peak memory guarantees. Display, OCR/candidate quality, multilingual generalization,
retrieval, citations and answer faithfulness remain NOT_EVALUATED. Production defaults are unchanged.
