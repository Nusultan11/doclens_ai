# Corpus v1 acquisition and review protocol

## Purpose

Corpus v1 is the first real-document data quality gate for the DocLens AI
extraction baseline. It is intentionally evaluated before embeddings, Qdrant,
OCR, or RAG. The raw corpus is local-only; the repository retains only public
provenance metadata, hashes, and aggregate or manually assessed findings.

## Frozen corpus requirements

- Exactly 90 genuine public-sector documents: 30 PDF, 30 DOCX, and 30 XLSX.
- Every document has an opaque `c1-NNNN` identifier, direct source URL, source
  page, publisher, license, SHA-256 digest, and byte size in
  `corpus_v1_manifest.csv`.
- The corpus contains no synthetic fixtures, generated documents, private
  documents, or extracted text.
- A byte-changing replacement is a new corpus revision, even if it is served
  from the same URL.

## Approved source and permission basis

Corpus v1 uses only attachments hosted on
`assets.publishing.service.gov.uk` and linked from `www.gov.uk` pages.

GOV.UK states that content published on the site may be reused under the Open
Government Licence (OGL), subject to the stated conditions and exceptions:

- [GOV.UK terms and conditions](https://www.gov.uk/help/terms-conditions)
- [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
- [GOV.UK Content API reference](https://content-api.publishing.service.gov.uk/reference.html)
- [GOV.UK Search API documentation](https://docs.publishing.service.gov.uk/repos/search-api/using-the-search-api.html)

On 2026-10-11, all 74 source pages represented by the 90 selected attachments
returned successfully, displayed the OGL v3.0 footer, and contained no detected
page-specific alternative-rights phrase in their Content API metadata. Each
manifest row records both the license and the page used as its license basis.
The required attribution for reuse is: "Contains public sector information
licensed under the Open Government Licence v3.0."

## Acquisition procedure

1. Query the public GOV.UK Search API separately for `pdf`, `docx`, and `xlsx`,
   requesting at most 500 results and the title, page path, content type, and
   publication timestamp.
2. Resolve every result through the Content API and enumerate its attachment
   metadata.
3. Accept an attachment only when:
   - its URL host is exactly `assets.publishing.service.gov.uk`;
   - its extension and declared MIME type agree with PDF, DOCX, or XLSX;
   - its declared size is greater than zero and no more than 50 MiB;
   - its source page is available and shows the OGL v3.0 footer;
   - the page does not state an alternative or more restrictive license.
4. Prefer different publishers and GOV.UK document types, then different file
   sizes and structures. Stop after 30 unique byte streams per format.
5. Validate `%PDF-` for PDF. For DOCX/XLSX, validate the ZIP container,
   `[Content_Types].xml`, and the expected `word/document.xml` or
   `xl/workbook.xml` member.
6. Compute SHA-256 and actual byte size after download. Reject duplicate hashes.
7. Store raw files only below ignored `local-corpus/`; never stage raw files,
   extracted text, renderings, or the profiler's local output.
8. Freeze the accepted source URLs, sizes, and hashes in
   `corpus_v1_manifest.csv`.

The initial search returned 500 PDF, 158 DOCX, and 404 XLSX page results. The
Content API yielded 16,387 eligible PDF attachments, 381 DOCX attachments, and
465 XLSX attachments before final curation. Corpus v1 contains 90 distinct
SHA-256 values.

## Replaying the frozen corpus

For each manifest row, download `download_url` to an ignored local directory
using `document_id` plus the declared extension. Verify `size_bytes` and
`sha256` before profiling. Do not silently substitute a changed or unavailable
file; report it and create a new corpus revision if a replacement is approved.

Run the repository profiler with runtime metrics enabled:

```powershell
.\.venv\Scripts\python -m doclens_ai.eda `
  --input-dir local-corpus `
  --output-dir .eda-output\corpus_v1
```

The evaluated environment was Python 3.12.3 with pypdf 6.20.0,
python-docx 1.2.0, and openpyxl 3.1.5. Version changes can alter extraction and
latency and therefore require a newly recorded run.

## Coverage design

The corpus spans 19 to 30 distinct publishers per format and includes forms,
guidance, official and national statistics, policy papers, consultations,
research, transparency releases, correspondence, reports, and decisions.
File sizes range from 1,732 bytes to 3,487,671 bytes. PDF length ranges from 1
to 38 pages; DOCX files range from 1 to 431 paragraphs and 0 to 126 tables;
successful XLSX files range from 1 to 12 worksheets and 4 to 37,496 populated
cells.

The source-page locale is English for all 90 rows. Two attachments are
explicitly identified by their publisher as Welsh and are marked `cy` in the
manifest; all other language labels come from the source-page locale. The set
is therefore English-dominant and is not a multilingual benchmark.

The sample is also weighted toward smaller PDF and DOCX files. That limitation
is retained in v1 rather than hidden by post-hoc substitution; a later corpus
revision should use explicit size strata.

## Manual quality review

Manual review is separate from automated metrics. Select cases that cover:

- a normal narrative PDF, a dense PDF table, and low-text/scan candidates;
- a paragraph-only DOCX and DOCX files with many interleaved tables;
- a formula/merged-cell XLSX, a multi-sheet XLSX, and any failed XLSX.

For PDF, render representative pages and compare visible content with
`pypdf.PageObject.extract_text()`. Review missing text, reading order, and table
or diagram fidelity.

For DOCX and XLSX, compare the original OOXML structure with the exact objects
read by python-docx/openpyxl: body block order, headers and notes, unique versus
merged cells, worksheet dimensions, stored cells, formulas, merges, tables, and
sheet order. Visual rendering is preferred when LibreOffice or an equivalent
renderer is available; if it is unavailable, record that limitation and do not
claim visual fidelity.

## Gate criteria

The acquisition portion passes only when format counts, source availability,
permission basis, signatures, unique hashes, and local integrity all verify.
The evaluation portion is complete only when the existing profiler runs on the
full corpus and the assessment distinguishes automated measurements from
manual observations.

Extraction issues found by the gate are not repaired in this step. They become
measured requirements for the subsequent extraction baseline. Raw documents
and extracted content remain uncommitted.
