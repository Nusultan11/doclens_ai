# Extraction Fidelity Gold and benchmark protocol v1

## Boundary and population

This is an offline measurement protocol, not a production parser change. The unit of analysis is
one original document from frozen Corpus v1, identified by opaque `c1-NNNN`, SHA-256, byte size and
format. Match sources by bytes, never by filenames or worksheet names. The committed manifest is
the authority; reject missing, extra, duplicate, changed, mis-suffixed or symlinked files before
measurement. A subset manifest is useful for explicitly synthetic tests, not an approved90 result.
Do not silently reacquire, replace or relabel sources. Record parser/model/configuration hashes,
dependency/Python versions and deterministic fingerprints alongside results.

Prior `corpus_v1_assessment.md` concerns an older count-only profiler; the structured baseline in
`extraction_baseline_v1.md` is the reproduction target. Prior visual/OOXML review may prioritize new
labels but is not new Fidelity Gold. Retrieval Gold establishes selected retrieval evidence, not
complete extraction fidelity. Evaluate review-status documents too; do not select only successes.

## Private Gold contract

Use UTF-8 JSONL under ignored `local-evaluation/`. One record per reviewed source, maximum 90
records/20 MiB. `fidelity_gold.load_gold` is the public strict validation boundary and sanitizes
errors rather than echoing Pydantic input excerpts. Unknown fields, coercions, wrong versions,
empty evidence, duplicate identities/assertions, invalid references, cyclic order, impossible
coordinates, cross-format locators and mismatched source identities are rejected.

Required record fields:

- `schema_version="1.0"`, `dataset_revision="corpus-v1-fidelity-v1"`.
- `dataset_kind="real"` and `review_basis="original_document"` for genuine annotations.
  Explicit synthetic unit fixtures use `synthetic` / `synthetic_fixture`; loading them requires
  `--allow-synthetic`, and the report retains that kind. Never cite their scores as real quality.
- `document_id`, `source_sha256` (lowercase 64-hex), positive `source_size_bytes`,
  `document_format` (`pdf`, `docx`, `xlsx`), all matching the manifest.
- `review_status="reviewed"`, actual `reviewer_count` (1..10), non-future ISO `reviewed_on`.
  No reviewer names, guessed review dates or auto-approval. Review is a human assertion, not
  something schema validation can prove. Drafts are intentionally rejected.
- Lists `anchors`, `order_pairs`, `table_cells`, `table_relationships`, `cells`, maximum 500 each.
  At least one anchor or cell expectation is required. Empty lists mean uncovered dimensions.

Anchor: unique `anchor_id` (`a1`, `a2`, ...), nonblank `text` (maximum 10,000 characters), `source`
locator, positive `occurrence` (default 1). Annotate distinctive short excerpts from the ORIGINAL,
including absent content; copying only parser output creates circular recall labels. Review
repeated text carefully: occurrence selects a non-overlapping match within the specified location.

Locators never need private names. `region` is body/header/footer/footnote/endnote/comment/drawing.
PDF requires one-based `page_number`; body can additionally specify zero-based `block_index`,
`table_index`, `row_index`, `column_index`. DOCX body requires zero-based `block_index`; table
checks also require `table_index` and paired grid indices. Ancillary DOCX regions use `part_index`
and currently cannot resolve to the frozen body-only extraction contract. XLSX requires zero-based
`sheet_index` plus uppercase `cell_coordinate`; optional paired grid indices must agree with the
coordinate. Do not invent PDF table coordinates from a flat extraction: annotate them on the
original and let the baseline fail the structured check.

`order_pairs` contain `before` / `after` anchor references. They establish a reviewed partial order,
not a complete reading-order claim. Include adjacent and non-adjacent blocks and within-page
anchors. `table_cells` contain `anchor_id`, positive `row_span` and `column_span` (defaults 1).
`table_relationships` contain `left`, `right`, and `relationship` (`same_row` or `same_column`).
Expected scopes/grid relationships must be consistent. Current PDF text cannot pass a structured
table check merely because both labels appear. XLSX merged-range anchors supply cell spans;
no expanded rectangular worksheet iteration or duplicate merged cells is necessary.

XLSX `cells` contain a cell `source` and REQUIRED nullable strings `value`, `formula`,
`cached_value`. Null is an explicit reviewed absence, not an omitted check. Formula text follows
the frozen extractor's no-leading-`=` convention. Stored values are strings from OOXML, with
existing boolean conversion; caches are historical stored results, never proof of current formula
correctness. Shared formula followers may have a cache but no resolved formula definition.
Never execute a formula, refresh external links or save a source workbook during annotation.
`check_display=true` requires `displayed_value`; otherwise displayed_value must be null/absent.
The baseline has no rendered display field, so display checks remain explicitly unsupported.

## Annotation acquisition and review

Start with the eight priority opaque IDs, then expand to narrative controls, complex tables,
merges, ancillary content, missing caches, dates/numeric formats, language and size strata.
Confirm every hash/size before review. View the original locally: PDF rendered pages for visual
order/table relationships; DOCX body plus headers/footers/notes/nested tables; XLSX visible values,
formula bar and stored caches with recalculation disabled. OOXML inspection alone is structural
evidence, not rendered Office fidelity. Record only expectations actually reviewed. A second
reviewer and adjudication are recommended for ambiguous tables, but not falsely claimed.

The CLI can create an eight-record private draft identity template. It contains no generated
anchors, zero reviewers, null review date and `draft` status. Populate expectations, remove
unreviewed records, then set review fields only after genuine review. Do not mechanically change
drafts to reviewed. Freeze the validated Gold fingerprint before comparing parser candidates.

## Metric definitions and limitations

Separate populations and denominators:

- Automated: status/error counts by format, warning-bearing documents and warning occurrences,
  block/table/sheet/cell counts, locator PRESENCE, default chunk eligibility/counts/source coverage.
  This is extraction-contract behavior, not semantic quality. Status success is not a fidelity score.
- Reviewed text recall: fraction of required anchors whose whitespace-normalized text is present
  in at least one extracted text/value/formula field; missing evidence is the absent-anchor count.
  This tests literal presence, not entailment. Case, digits and punctuation are unchanged. Matching
  does not cross fields or cells; duplicate value/cache fields are not separate occurrences.
- Reviewed provenance: anchors found at expected locations and uniquely resolved cell expectations
  divided by all reviewed anchors/cells. Text at a wrong location may pass recall and fail provenance.
- Reading order: satisfied strictly increasing `(observation ordinal, normalized text offset)` pairs
  divided by reviewed pairs. Missing anchors fail pairs; unannotated order is not measured.
- Table cells: located structured cells with expected spans divided by reviewed checks. Relations:
  both located structured cells retain the reviewed common table/sheet scope and row/column.
- Stored value/formula/cache fidelity: exact equality (including null), separately counted, over
  reviewed cell checks. A missing cell fails all three. Display fidelity: unsupported in this frozen
  contract, `NOT_EVALUATED`, with requested unsupported checks counted separately.

Zero supported labels means `NOT_EVALUATED` and null score, NEVER zero or 100% fidelity.
Coverage reports reviewed documents by format and anchors; each metric retains its own denominator.
Unreviewed documents do not enter semantic rates. Report biases and partial review; no corpus-wide
semantic claim from eight hard cases. No retrieval, citation, answer or semantic-superiority score.

Processing latency is per-document extract_file wall time, excluding integrity hashing, chunking,
Gold scoring and experiments. Use nearest-rank p50/p95, state observation count and environment.
One serial pass is not a throughput/SLA benchmark. Fingerprint the full deterministic report before
adding runtime observations. Runtime timings alone may differ between identical runs.

## Controlled candidates and resource boundary

`--experiments` inspects only the eight priorities and never feeds candidates into chunking.
PDF: installed pypdf plain baseline vs layout defaults and layout with rotated text retained;
maximum 10 pages, 10 MiB decoded stream/page and 5M characters/candidate. Record counts and
fingerprints, not text. XML inventory: only relevant original DOCX parts/XLSX sheet XML, after
successful bounded production extraction/archive validation; reject DTD/entity declarations.
Inventory counts do not serve as human labels. Candidate errors are isolated and sanitized.

All default ExtractionLimits and ChunkingConfig ceilings are recorded unchanged. Frozen-corpus
integrity violations fail the run; normal extraction/candidate failures are isolated per document.
These are logical file/archive/page/cell/character bounds, NOT hard RSS or CPU deadlines. Decoding
a PDF stream allocates memory before its length can be checked. Run unfamiliar/untrusted corpora
in a separately resource-capped disposable environment; this offline tool is not a hostile-upload
sandbox. Peak RSS, adversarial resource safety, display rendering and semantic candidate scores
are NOT_EVALUATED unless separately measured/annotated. Do not silently upgrade dependencies.

## Reproduction, privacy and decision gate

Run from the repository root with `[eda]` and existing dev dependencies installed; see README.
Outputs must be new and outside the corpus. Retain metadata reports in ignored evaluation-output/;
draft/Gold in local-evaluation/. No source paths, filenames, sheet names, excerpts, formulas or
cell values are serialized to metrics. Third-party logs/warnings/stdout are suppressed inside
document parsing/experiments. Only aggregate counts, opaque IDs and fingerprints enter Git docs.

Repeat identical evaluation, compare deterministic fingerprints and all non-runtime JSON fields;
verify source integrity and inspect diff/status/privacy before committing sanitized artifacts.
Require reviewed missing-text/order/table/value labels and bounded regression tests before adopting
any candidate. Keep production ingestion, canonical identities, PostgreSQL/Qdrant, indexing,
authorization and RAG unchanged. Prioritize actual error evidence, not library count.
