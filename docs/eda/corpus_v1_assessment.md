# Corpus v1 data quality assessment

## Decision

**Corpus gate: PASS. Extraction readiness for embeddings/RAG: HOLD.**

The corpus itself meets the v1 acquisition gate: 90 genuine GOV.UK documents,
30 per supported format, with verified source pages, OGL v3.0 permission basis,
valid file signatures, matching sizes and SHA-256 hashes, and no duplicates.

The current profiler completed the real-corpus run, but the extraction baseline
is not yet suitable as input to embeddings or RAG. Two image/diagram PDFs lose
almost all visible text, one legitimate XLSX is rejected because of an inflated
worksheet dimension, and current outputs do not preserve reading order or table
structure.

## Evidence boundary

- **Automated:** one profiler run over all 90 documents with runtime metrics;
  source, license-footer, signature, size, and SHA-256 verification.
- **Manual:** four PDFs visually compared on selected rendered pages; three
  DOCX and three XLSX files structurally compared against their original OOXML.
- **Not evaluated:** OCR quality, semantic chunking, embeddings, retrieval,
  RAG, production throughput, or sensitive/private documents.

No raw document, extracted text, page image, or local profiler output is stored
in the repository.

## Corpus composition

| Format | Documents | Publishers | Source-page types | Size range | Language evidence |
|---|---:|---:|---:|---:|---|
| PDF | 30 | 30 | 21 | 1,732–461,365 B | 29 English page-locale; 1 explicitly Welsh attachment |
| DOCX | 30 | 19 | 10 | 8,058–606,051 B | 29 English page-locale; 1 explicitly Welsh attachment |
| XLSX | 30 | 30 | 10 | 9,053–3,487,671 B | 30 English page-locale |

The 90 documents have 90 unique SHA-256 hashes. Publication timestamps range
from 2011-07-11 through 2026-10-09. Coverage includes prose, forms, dense
tables, multi-sheet workbooks, statistics, policy and consultation documents,
and two low-text PDF cases. The corpus is English-dominant and biased toward
small PDF/DOCX files.

## Automated profiler results

| Measure | Result |
|---|---:|
| Supported files | 90/90 |
| Successful extraction | 89/90 (98.89%) |
| PDF success | 30/30 (100.00%) |
| DOCX success | 30/30 (100.00%) |
| XLSX success | 29/30 (96.67%) |
| Empty extracted text | 1/89 successful (1.12%) |
| Possible scanned PDFs | 2/30 (6.67%) |
| Duplicate copies | 0/90 (0.00%) |
| Extracted characters | min 0; p50 3,082; p95 100,953; max 515,758 |
| File size | min 1,732 B; p50 32,438 B; p95 308,445 B; max 3,487,671 B |
| Deterministic content fingerprint | `4db822b0734d111a09a91339c99d06765266224ff2cf16785df643f55f12cd64` |

### Structure

- PDF: 1–38 pages; p50 2, p95 17; 2 documents met the profiler's possible-scan
  heuristic.
- DOCX: 1–431 paragraphs, 0–126 tables, and 0–3,372 table-cell positions.
- Successful XLSX: 1–12 worksheets, 4–37,496 populated cells, and 1–2,864
  rows containing data.

The single failed document, `c1-0071`, is a valid seven-sheet XLSX. One sheet
declares `A1:P1048576` even though its XML stores 549 cells and the meaningful
content observed by openpyxl ends at row 140. Row-major iteration therefore
crosses the profiler's 1,000,000-cell safety cap and returns `limit_exceeded`.
This is a reproducible false rejection caused by an inflated used range, not a
corrupt file.

The run also emitted openpyxl warnings that data-validation and conditional-
formatting extensions are unsupported by its reader. The profiler does not save
the workbooks, so it did not rewrite the source files, but those structures are
not measured or preserved by the current baseline.

### Processing latency

Latency is from one local run and is operational, not a benchmark.

| Format | n | Mean | p50 | p95 | Maximum |
|---|---:|---:|---:|---:|---:|
| PDF | 30 | 210.938 ms | 53.171 ms | 1,080.437 ms | 1,954.622 ms |
| DOCX | 30 | 63.843 ms | 11.707 ms | 482.975 ms | 636.659 ms |
| XLSX | 30 | 95.180 ms | 24.098 ms | 450.384 ms | 513.157 ms |
| Overall | 90 | 123.320 ms | 25.612 ms | 482.975 ms | 1,954.622 ms |

The slowest case was `c1-0045`, a seven-page dense PDF table. The next slowest
was `c1-0050`, a 38-page narrative PDF. Latency generally rose with page/cell
work, but the single run is insufficient for performance thresholds.

## Manual extraction-quality review

These findings apply only to the listed cases and must not be generalized as
corpus-wide rates.

### PDF: four cases

- `c1-0041` (4 pages): rendered pages contain clearly visible prose, while
  pypdf returned 0 characters on every page. Missing-text result: **fail**.
  Reading order and table fidelity cannot be assessed without OCR because the
  current extractor sees no text.
- `c1-0044` (1 page): the original is a flowchart with labels in connected
  shapes; extraction returned only 2 whitespace characters. Missing-text
  result: **fail**. Diagram labels and branch order are absent.
- `c1-0045` (7 pages): page 1 is a dense hourly-height table. pypdf returned
  6,433 characters for the reviewed page and 39,260 for the document, so the
  visible labels and values are largely present. It emits most cells as
  separate lines, losing row/column associations; table fidelity is **fail**
  and reading order is only partially useful.
- `c1-0050` (38 pages): on the reviewed title page, the extracted heading,
  attribution, date, and publication identifier follow the visible reading
  order. This reviewed page is **acceptable for narrative text**; unreviewed
  pages were not manually certified.

### DOCX: three cases

Visual rendering was unavailable because LibreOffice is not installed. These
are structural OOXML comparisons, not visual-fidelity claims.

- `c1-0006`: 388 paragraph blocks and 126 table blocks are interleaved with 252
  paragraph/table transitions. The profiler visits all top-level paragraphs
  first and all tables second and retains only counts, so original reading
  order is not represented. It counted 648 cell positions over 542 unique
  cells; merged cells inflate the character count from 41,938 main-XML text
  characters to 47,110. Two header/footer characters are omitted.
- `c1-0007`: 382 paragraph blocks, 10 tables, and 7 drawings. The profiler
  counted 2,713 cell positions over 1,467 unique cells, producing 100,953
  counted characters versus 45,847 characters stored in the main document XML.
  It also omits 1,102 note/comment characters and 23 header/footer characters.
  This case demonstrates both merged-cell overcount and missing ancillary text.
- `c1-0019`: all 1,672 main-body characters are represented by the paragraph
  count path, but 370 header/footer characters and one drawing are outside the
  profiler. Body-text coverage is acceptable; complete-document coverage is
  not.

Because the profiler emits metrics rather than ordered blocks, DOCX table
fidelity cannot pass: cell coordinates, merges, table boundaries, and body
position are not available downstream.

### XLSX: three cases

Visual rendering was unavailable because LibreOffice is not installed. These
are workbook/OOXML structural comparisons.

- `c1-0067`: one sheet with 44 merged ranges and 110 formulas. All 110 formulas
  have cached values, so the current `data_only=True` read retains a value, but
  formulas, coordinates, merges, and layout are not represented in the output.
- `c1-0081`: 12 sheets, 45 merged ranges, and 3 formulas with cached values.
  Automated metrics report 1,088 populated cells and 295 rows with data, but
  sheet names, hierarchy, coordinates, and merges are not preserved.
- `c1-0071`: the valid workbook described above is rejected before extraction
  because one sparse sheet advertises the maximum Excel row. Four OOXML tables
  and the workbook's meaningful cells are therefore unavailable to the current
  baseline.

For the reviewed XLSX cases, value counting works when workbook dimensions are
reasonable, but table fidelity is **not represented** and sparse inflated
dimensions can cause a false failure.

## Known limitations

- GOV.UK/OGL is the only source family; the findings do not represent other
  producers or export tools.
- The set contains only two explicitly Welsh attachments and no verified
  coverage of other languages.
- PDF and DOCX are size-skewed toward smaller files; the largest file overall is
  3.49 MiB.
- DOCX/XLSX manual review was structural because no LibreOffice renderer was
  available. No visual layout or styling fidelity is claimed for those formats.
- Manual review covers 10 documents and selected PDF pages, not all 90 files.
- One latency observation per file is not a stable performance benchmark.
- Permission was verified at the official page level. The pages showed no
  alternative-rights wording, but OGL exclusions still apply if a source later
  identifies third-party material.

## Recommendations for the next extraction baseline

1. Add an explicit `requires_ocr` or equivalent non-success outcome for PDFs
   with visible content but insufficient extracted text. Keep OCR itself out of
   this step and evaluate it separately.
2. Emit ordered, traceable blocks instead of character counts alone: page and
   block provenance for PDF; document-order paragraphs/tables for DOCX; and
   sheet/cell coordinates for XLSX.
3. Preserve table structure. For PDF, evaluate a table-aware strategy on fixed
   cases such as `c1-0045`. For DOCX, avoid double-counting merged cells and
   retain table boundaries/merges. For XLSX, retain sheets, coordinates, merged
   ranges, formulas plus cached values, and OOXML table definitions.
4. Replace XLSX rectangular used-range scanning with bounded iteration over
   stored cells or another sparse-aware strategy while retaining protection
   against decompression bombs and pathological workbooks. `c1-0071` must
   become a regression case.
5. Define an explicit policy for DOCX headers, footers, footnotes/endnotes,
   comments, drawings, and text boxes; then test the selected policy.
6. Freeze a small manually annotated extraction set from these opaque IDs and
   measure missing text, order, and table reconstruction before authorizing
   embeddings or retrieval work.
7. Build a future corpus revision with explicit size strata, more long PDFs and
   DOCX files, and broader verified language coverage. Do not replace corpus v1
   silently.

## Gate conclusion

Corpus v1 is reproducible and legally reusable for the stated evaluation. The
real-corpus run successfully exposed concrete baseline failures that synthetic
fixtures did not establish. Embeddings, Qdrant, and RAG should remain blocked
until scan handling, sparse XLSX iteration, ordered block output, and table
structure have an evaluated baseline on this fixed corpus.
