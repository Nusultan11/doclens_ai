# Real Retrieval Gold v1 pilot report

## Purpose and review status

Dataset revision: `corpus-v1-retrieval-gold-v1`; schema version: `1.0`.
Human review completed and explicitly confirmed by the user on 2026-10-14 (Asia/Qyzylorda).
This is a small offline reference-label pilot prepared from frozen Corpus v1 before a real
retriever is introduced. It establishes reviewed questions, source identities and evidence labels.

The user personally reviewed the original source documents and confirmed 47 unchanged approvals,
one correction (q021), and zero rejections. All 48 accepted examples are `reviewed`, with
`reviewer_count=1` and `adjudication_state=not_required`. No reviewer identity, second reviewer,
or independent adjudication is claimed. All three unanswerable labels were included in that review.

Private Gold, review decisions and validation artifacts remain in ignored local directories.
No question text, source excerpt, original document or private reviewer details are in this report.

## Snapshot identities

Approved candidate snapshot SHA-256:

`359f51363219eb48677a6cb7cb0b0fc3e1eec345d1e6e0040a95fafbe0fb38eb`

Final normalized Gold fingerprint, produced by the repository's strict validator:

`d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94`

The candidate file still contains the original 48 drafts and is byte-unchanged. The final local
Gold contains the same IDs, source hashes, evidence anchors, categories, answerability, families
and splits. Only the approved review-state fields and q021 question wording changed. Records are
ordered deterministically by question ID. Two CLI validations produced the same Gold fingerprint
and byte-identical metadata JSON reports.

## Coverage

There are 48 unique questions from 15 selected documents, all with extraction `success`.
There are 45 answerable and 3 unanswerable questions, 80 positive evidence anchors, and no synthetic
examples, drafts or pending reviews in final Gold.

| Source format | Selected documents | Questions |
| --- | ---: | ---: |
| PDF | 5 | 16 |
| DOCX | 5 | 17 |
| XLSX | 5 | 15 |
| Total | 15 | 48 |

All 48 questions are English queries grounded in original English source content. There are no
validated Russian, Kazakh, cross-lingual, or native RU/KK document cases.

| Category | Questions |
| --- | ---: |
| Fact | 12 |
| Number | 13 |
| Table | 8 |
| Identifier | 10 |
| Version | 2 |
| Unanswerable | 3 |

| Split | Documents | Families | Answerable | Unanswerable | Questions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dev | 11 | 10 | 33 | 3 | 36 |
| Held-out test | 4 | 4 | 12 | 0 | 12 |
| Total | 15 | 14 | 45 | 3 | 48 |

All three unanswerable questions are in dev. This test set cannot evaluate held-out abstention
quality. No extra questions were generated and no split was changed to conceal this limitation.

## Source integrity and anchor compatibility

All 90 local corpus files match the committed Corpus v1 manifest by SHA-256 and byte size:
30 PDF, 30 DOCX and 30 XLSX, with 90 distinct hashes and no missing, extra or changed files.
Every final Gold source hash is in that manifest; original bytes remain unchanged.

All 80 positive anchors resolve to exactly one actual normalized extraction source unit. Locations
and span bounds are valid. All 80 are contained in frozen structure-aware chunk spans; for each
of the 45 answerable questions, the complete evidence set fits in at least one single chunk.
There were zero unresolved anchors and zero questions whose complete evidence required multiple
chunks in this snapshot. These checks verify source/chunk compatibility, not retrieval performance.

Chunking configuration: structure-aware version 1.0, maximum 1,200 characters, overlap 120,
`allow_needs_review=false`. Configuration fingerprint:

`a7c53272ac7baa3f916e43dc4b96a455fa0daa1437cafe04fd7c90b2840edc4c`

Offsets use normalized source-unit Python character coordinates, not file-byte positions. Source
locators and hashes are independent of ProcessingRun, CanonicalChunk or vector-store runtime UUIDs.
PDF layout/table reconstruction and rendered Office display-value fidelity are not established
by successful extraction or by the automated anchor checks.

## Family isolation

Selected documents form 14 recorded publication families, with 10 dev and 4 test families.
Assignments were checked against source hashes, manifest publication relationships, recorded
siblings, the local review table and coverage metadata. No selected family crosses dev/test,
and no source hash is assigned to conflicting families.

The user verified seven related documents and accepted the selected assignments. Same-publication
siblings are conservatively grouped; this is not a claim that every related document is a near
duplicate or a version of the same file. Preparation also screened 105 selected-document pairs
using normalized text fingerprints and 5-token shingles. Such lexical screening cannot prove
semantic independence.

Review is bounded by the relationships actually inspected. There was no independent human
adjudication of every possible near duplicate across all 90 corpus documents. Any later expansion
must revisit family membership and preserve family-level split isolation.

## q021 correction

The approved correction asks for a month and year rather than an exact date. The expected answer
is unchanged. The existing evidence ID, source SHA-256, PDF page 2 / block 1, answer-bearing span
`[773,832)`, family and split are preserved.

The reviewer also verified the broader corrected-paragraph span `[494,832)`, but selected the
narrow span for retrieval scoring so matching does not unnecessarily require the whole paragraph.
No duplicate or additional anchor was introduced.

## Reproduction and executed verification

Local validation environment: Python 3.12.3, pytest 9.1.1, pypdf 6.20.0, python-docx 1.2.0,
openpyxl 3.1.5. Existing code and dependency declarations were unchanged.

From the repository root, with the approved private local Gold available:

```powershell
.\.venv\Scripts\python -m ruff check src tests alembic
.\.venv\Scripts\python -m pytest -q tests/unit/test_retrieval_eval.py
.\.venv\Scripts\python -m doclens_ai.evaluation validate --gold local-evaluation/retrieval_gold_v1.jsonl --corpus-manifest docs/eda/corpus_v1_manifest.csv --json-output evaluation-output/retrieval_gold_v1_validation.json
git diff --check
git diff
git status --short
```

- Ruff: all checks passed.
- Targeted retrieval-evaluation tests: 31 passed.
- Strict Gold CLI: 48 valid reviewed examples; no invalid hashes, locators or family leakage.
- Repeated CLI validation: same Gold fingerprint and byte-identical metadata JSON output.
- Read-only snapshot/source diagnostic: 90/90 corpus hashes and sizes matched; candidate unchanged;
  only approved final-record changes; 80/80 source-resolvable and chunk-contained anchors.
- Full regression command inside a disposable application-compatible Docker test container:
  `python -m pytest -q -p no:cacheprovider` -- 156 passed, 0 skipped, including PostgreSQL,
  MinIO and migration integration tests. PostgreSQL and MinIO ran on an isolated Docker network
  with no published ports; source files were mounted read-only. Windows localhost:5432 was not used.
  Existing test dependencies were installed only in the disposable runtime.

Generated validation JSON remains under ignored `evaluation-output/`. The final reviewed JSONL
and human review table remain under ignored `local-evaluation/`; they must never be staged.

## What is measured and what remains

This pilot verifies reviewed reference correctness, schema validity, stable source identities,
selected-family split isolation, reproducibility and source/chunk compatibility.
It does not measure Hit@k, Recall@k, MRR, nDCG, abstention, retrieval latency or answer quality:
no real ranked retrieval results exist for this step. Synthetic metric unit tests verify arithmetic
and contracts only; their scores are not real retrieval-quality measurements.

Limitations and subsequent evaluation requirements:

- Only 15 documents and 48 English questions; not a complete production evaluation benchmark.
- Held-out test has just 12 answerable questions and no unanswerable cases. Add genuinely reviewed
  held-out unanswerable cases in a future version before evaluating test-set abstention.
- RU/KK and cross-lingual coverage require independently reviewed examples, not automatic translation.
- Family review and near-duplicate screening are bounded; review new relationships before expansion.
- Two version questions concern revision history stated inside sources, not a paired-version benchmark.
- Character-based chunks and extraction status do not establish semantic completeness or layout fidelity.
- One human reviewer was confirmed; no multi-reviewer agreement or adjudication statistic exists.
- Future retrieval comparisons must use a frozen reviewed snapshot, identical corpus and reproducible
  configurations, reporting scope/security failures separately from quality scores.

This report records the completed pilot review. The companion protocol's initial pre-pilot status
prose is historical; it was not modified because this step authorizes only this tracked report.
