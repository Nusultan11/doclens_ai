# Document EDA and extraction baseline

This tool profiles an explicitly selected local corpus of PDF, DOCX, and XLSX files. It is an
offline engineering baseline, not the production ingestion pipeline. It never calls the DocLens
API, PostgreSQL, object storage, an LLM, or a network service.

## Run

Install the optional parser set, then select both directories explicitly:

```bash
python -m pip install -e ".[dev,eda]"
python -m doclens_ai.eda --input-dir ./local-corpus --output-dir ./eda-output
```

The output directory must differ from the input directory. If it is nested below the input, it is
excluded from discovery so old reports are not profiled as documents. Files are processed in a
stable relative-path order and receive opaque identifiers such as `document-000001`; paths and
names are never written to reports.

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
