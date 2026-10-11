# Structured extraction baseline v1

## Scope and decision

This report evaluates the standalone `doclens_ai.extraction` baseline against the frozen Corpus
v1 described in `corpus_v1_protocol.md` and `corpus_v1_assessment.md`. The run used the 90 approved
documents (30 PDF, 30 DOCX, and 30 XLSX) already acquired under that protocol. Raw documents,
filenames, worksheet names, extracted text, table contents, and cell values remain local and are
not included here or in Git.

Decision: the contract is suitable for controlled, offline text-first chunking experiments when
the caller gates on extraction status. It is **not** a universal pass for production ingestion or
RAG. The 34 `needs_review` documents must not silently enter a quality-sensitive downstream
pipeline, scanned/low-text PDFs still require a separately justified OCR path, and PDF table
structure is deliberately unavailable.

## Reproduction

Environment used on 2026-10-11:

- Python 3.12.3
- pypdf 6.20.0
- python-docx 1.2.0
- openpyxl 3.1.5 (fixture/test construction only; XLSX extraction reads bounded OOXML directly)

Commands:

```powershell
.\.venv\Scripts\python -m pytest tests\unit\test_extraction.py -q
.\.venv\Scripts\python -m doclens_ai.extraction `
  --input-dir local-corpus `
  --output-dir .eda-output\extraction-v1
```

The output directory is ignored by Git. The run persisted only privacy-safe metadata and
aggregates. Its deterministic content fingerprint was
`9731990eb079537823183e80d652f6c6e67b110cec4ccb7ff2ca0b137ea73ec9`.

## Aggregate results

All 90 documents completed without a `failed` outcome. A `needs_review` outcome means extraction
returned a bounded partial/structured result plus an explicit warning; it is not counted as an
unqualified success.

| Format | Documents | `success` | `needs_review` | Failed | P50 latency | P95 latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DOCX | 30 | 14 | 16 | 0 | 16.456 ms | 371.899 ms |
| PDF | 30 | 27 | 3 | 0 | 41.915 ms | 1,091.766 ms |
| XLSX | 30 | 15 | 15 | 0 | 7.836 ms | 393.666 ms |
| **Total** | **90** | **56** | **34** | **0** | — | — |

The run emitted 2,461 PDF/DOCX text blocks, 305 DOCX/XLSX tables, 88 worksheets, and 98,006
meaningful XLSX cells. Total parser time measured serially was 11,292.274 ms. Latency is a local
single-run engineering measurement, not a production throughput benchmark.

Review warnings occurred on 16 DOCX, 3 PDF, and 15 XLSX files. The most common detected classes
were unsupported headers (9 documents), footers (8), drawings (6 DOCX and 11 XLSX), nested DOCX
tables (4), unsupported DOCX body containers (5), footnotes (3), insufficient PDF page text (3),
missing formula definitions for shared formula followers (7), missing cached formula values (3),
text boxes (2), and XLSX comments (1).
Every PDF also carries the informational `pdf_table_structure_not_preserved` limitation.

## Frozen difficult cases

The corpus identifiers below refer to the frozen manifest. Automated counts come from the new
extractor; visual/structural observations are the limited manual findings already recorded during
the Corpus v1 assessment.

| Case | Measured baseline result | Assessment |
| --- | --- | --- |
| `c1-0041` | 4 page blocks, 0 extracted characters, 4 insufficient-text page warnings | Correctly routed to `needs_review`; the prior visual review found visible text on all four pages, so this remains an OCR/parser gap. |
| `c1-0044` | 1 page block, 2 characters, insufficient-text warning | Correctly routed to `needs_review`; the flowchart content is not usable without a separate OCR/layout capability. |
| `c1-0045` | 7 page blocks, 39,260 characters, `success` plus the PDF-table limitation | Narrative text is available, but the previously observed dense table loses row/column structure. It is unsafe for table-sensitive chunking. |
| `c1-0050` | 38 ordered page blocks, 72,876 characters, no low-text warning | Page provenance and narrative text are available; the prior manual review found the title-page reading order acceptable. This does not establish universal PDF reading-order fidelity. |
| `c1-0006` | 514 ordered body blocks: 388 paragraphs and 126 tables; 542 logical cells | Body paragraph/table interleaving is preserved and merged positions are no longer double-counted. A detected footer keeps the result in `needs_review`. |
| `c1-0007` | 392 ordered body blocks: 382 paragraphs and 10 tables; 1,467 logical cells | Merged text is emitted once per logical cell. Headers, footers, footnotes, drawings, nested tables, and unsupported body containers are explicitly reported, so the result is `needs_review`. |
| `c1-0067` | 1 sheet, 294 meaningful cells, 44 merged ranges; 110 formula cells have cached values | 107 formula definitions are directly present; 3 shared-formula followers have cached values but no local definition and are explicitly flagged. Result: `needs_review`. |
| `c1-0081` | 12 sheets, 1,088 meaningful cells, 45 merged ranges; 3 formulas and 3 cached values | Sheet separation, formula/cache pairs, and merges are preserved. A worksheet drawing is explicitly unsupported, so the result is `needs_review`. |
| `c1-0071` | 7 sheets, 512 meaningful cells, 5 merged ranges, 4 table definitions | Completed in 2,298.860 ms without walking the declared `A1:P1048576` rectangle. Two worksheet drawings require review; the inflated dimension no longer triggers a false cell-scan limit. |

## Contract and known limitations

The in-memory contract preserves ordered PDF page text, ordered DOCX body text/table blocks,
logical DOCX table cells with merge spans, and sparse XLSX sheet/cell/table structures. Each
result includes source SHA-256 and size, format, status, sanitized warnings, and a sanitized error
category. Corpus processing isolates every file, and CLI output contains no extracted content.

Known limitations are intentional and measurable:

- no OCR, PDF layout reconstruction, or PDF table extraction;
- no DOCX headers, footers, notes, comments, drawings, text boxes, or nested-table extraction;
- XLSX values are preserved as stored OOXML values rather than rendered display values; styles,
  charts, drawings, comments, and external content are not interpreted;
- shared-formula followers without their own formula text retain cached values but require review;
- warning detection establishes known incompleteness, not semantic correctness;
- the latency sample is one local run and does not provide concurrency or production capacity
  evidence.

## Recommendation for the next stage

Use only `success` results for an initial deterministic text-first chunking baseline. Preserve
page/block/sheet/cell provenance in every derived chunk, and keep `needs_review` documents out of
quality claims until the relevant warning is handled or explicitly accepted. For PDF tables and
low-text pages, run a fixed-corpus parser/OCR comparison before adding dependencies. For DOCX and
XLSX, decide whether ancillary content is in scope based on measured downstream misses rather
than silently dropping the warnings.

This baseline does not authorize embeddings, Qdrant, RAG, production ingestion integration, or a
claim that all Corpus v1 content is extraction-complete.
