# Document EDA and extraction baselines

This tool profiles an explicitly selected local corpus of PDF, DOCX, and XLSX files. It is an
offline engineering baseline, not the production ingestion pipeline. It never calls the DocLens
API, PostgreSQL, object storage, an LLM, or a network service.

## Run

Install the optional parser set, then select both directories explicitly:

```bash
python -m pip install -e ".[dev,eda]"
python -m doclens_ai.eda --input-dir ./local-corpus --output-dir ./eda-output
python -m doclens_ai.extraction --input-dir ./local-corpus --output-dir ./extraction-output
```

The output directory must differ from the input directory. The EDA profiler excludes a nested
output directory from discovery; the structured extractor requires its output directory to be
outside the input tree. Files are processed in a stable relative-path order and receive opaque
identifiers such as `document-000001`; paths and names are never written to reports.

Use `--omit-runtime-metrics` when byte-for-byte reproducibility matters. Normal runs measure
parser latency, which necessarily varies by machine and run. The `deterministic_content_sha256`
field excludes latency and can compare all content-derived metrics across normal runs.

## Outputs

- `metrics.json` contains limits, per-document privacy-safe metrics, aggregates, explicit rate
  numerators and denominators, and the deterministic content fingerprint.
- `manifest.csv` contains one privacy-safe row per discovered file.
- `eda_report.md` is a concise aggregate human-readable summary.

No output includes filenames, directory paths, extracted text, worksheet names, paragraph text,
cell values, parser exception messages, credentials, or document metadata that can expose source
content. SHA-256 is retained because exact-byte duplicate detection is a required corpus-quality
metric; it should still be handled as internal analysis data.

The structured extraction command writes `metrics.json`, `manifest.csv`, and `report.md` with the
same privacy boundary. Its in-memory result contains the actual extracted blocks and cells, but
the CLI persists only format, status, sanitized warning/error categories, SHA-256, byte size,
structural counts, latency, configured limits, and a deterministic fingerprint. Use
`--omit-runtime-metrics` to omit latency values from its per-document output.

## Structured extraction contract

`doclens_ai.extraction` is a standalone baseline for future chunking experiments. It is not a
production ingestion stage and does not mutate the API, PostgreSQL, object storage, or upload
state. Each file returns one of `success`, `needs_review`, or `failed`; failures use a fixed
sanitized category and cannot stop later files.

- PDF emits one ordered text block per page with a one-based page number. Pages below 20
  non-whitespace characters require review. No OCR is attempted, and an informational warning
  states that table structure is not preserved.
- DOCX emits body paragraphs and tables in document order. A merged logical cell is emitted once
  with its anchor coordinate and row/column span. Headers, footers, footnotes, endnotes, comments,
  drawings, text boxes, nested tables, and unsupported body containers are not extracted;
  detected occurrences require review.
- XLSX reads stored cells rather than iterating each coordinate inside a declared worksheet
  rectangle. It preserves sheet order/state, meaningful cell coordinates and raw values, formula
  definitions and cached values when present, merged ranges, and table names/references/columns.
  Missing shared-formula definitions or cached results and detected drawings/comments require
  review. Formulae and external content are never executed.

The parser bounds corpus file count, input bytes, office archive entries and expansion, PDF pages,
extracted characters, document blocks, DOCX table grid positions, worksheets, stored spreadsheet
cells, merged ranges, and spreadsheet table definitions. XML document type/entity declarations
are rejected.
These safeguards are application-level limits, not a substitute for OS/container resource
isolation when processing hostile documents.

## Confidential documents

- Use only a deliberately selected, access-controlled local input directory.
- Write reports to an access-controlled location and do not treat SHA-256 values as public data.
- Inspect the privacy checks before sharing a report, and delete local reports under the source
  retention policy when analysis is complete.
- Never add source documents or generated reports to Git. The standard `eda-output/`,
  `.eda-output/`, and `reports/eda/` locations are ignored, but a custom output path remains the
  operator's responsibility.

## Metrics and methodology

Every readable file at or below the selected input directory is counted. Supported files are
identified only by a case-insensitive `.pdf`, `.docx`, or `.xlsx` extension. Each file is isolated:
a corrupt, encrypted, unsupported, oversized, or otherwise failing document records a sanitized
error category and does not stop later files.

Common metrics include byte size, format, SHA-256, success/error status, parser latency, extracted
character count, empty-text status, and duplicate relationship. Format-specific metrics are:

- PDF: page count, pages with and without meaningful extracted text, page extraction failures,
  possible image-only page count, and a possible-scan flag.
- DOCX: paragraph count, table count, table cell count, and populated table cell count.
- XLSX: worksheet count, populated cell count, rows with data, and populated cells per worksheet.

A PDF page is considered to have meaningful extracted text at 20 or more non-whitespace
characters. A PDF is a possible scan when at least 80% of its pages fall below that threshold.
This is a triage heuristic, not OCR or proof that a page is image-only. OCR becomes a candidate
only after a representative corpus shows a material possible-scan rate and a reviewed sample
confirms that valuable content is missing from text extraction.

A more advanced parser is justified only when a representative, reviewed sample demonstrates a
material and measurable shortfall in this baseline, such as failed supported documents, missing
tables, unacceptable reading order, or insufficient extraction coverage. Compare candidates on
the same fixed corpus and metrics before adopting one; isolated anecdotes are not sufficient.

Rates always retain their numerator and denominator. Extraction success excludes unsupported
formats from its denominator. Empty-text rate uses successfully parsed documents with an
applicable text metric. Possible-scan rate uses successfully parsed PDFs. Duplicate-copy rate is
the number of repeated files after the first occurrence divided by files with a SHA-256. P50 and
P95 use nearest-rank percentiles and are omitted for fewer than five observations.

## Safety limits

Defaults reject more than 10,000 files, files above 50 MiB, PDFs above 2,000 pages, office ZIPs
above 10,000 entries or 200 MiB uncompressed, any office entry above 100 MiB, ZIP compression
ratios above 1,000:1, more than 5,000,000 extracted characters, more than 256 worksheets, or more
than 1,000,000 scanned spreadsheet cells. Symlinks are recorded as rejected and never followed.

DOCX and XLSX archives are inspected before parser loading. XLSX workbooks use read-only and
`data_only` modes with external links disabled. Formulae, macros, external links, and embedded
objects are not executed. Macro-enabled formats are unsupported. Encrypted PDFs are not
decrypted. The parsers may still consume substantial CPU or memory within the limits, so untrusted
corpora should be profiled in a resource-constrained environment.

## Interpreting the baseline

Parser success means only that basic structural extraction completed. It does not establish
semantic completeness, table fidelity, reading order, formula correctness, OCR quality, language
coverage, production throughput, or retrieval quality. The baseline does not mutate documents,
create upload state, or imply any production ingestion decision.

No representative corpus is included with the repository, and generated fixtures validate only
tool behavior. Do not claim representative EDA from fixtures. Before selecting production parsers
or introducing OCR, use an approved, privacy-reviewed corpus with at least 30 documents per
supported format and deliberate coverage of small/large, text-rich/empty, table-heavy, scanned,
encrypted, malformed, duplicate, and multilingual examples. Record corpus provenance and known
sampling bias outside the generated privacy-safe reports.
