# PDF Gold expansion v1: ML-3 approved freeze

## Status and boundary

**PASS: ML-3 reviewed Gold expansion validated and frozen.** The user explicitly
confirmed original-document review and approval of all eight proposed PDF records
on 2026-10-15 and supplied the approved annotations. The supplied records declare
reviewed status, one reviewer, that date, real data and original_document basis.
These are human attestations, not a new independent review performed by Codex.
No reviewer, review date, anchor, locator or expectation was generated or corrected.

The separate approved snapshot contains nineteen records: twelve PDF, three DOCX
and four XLSX. Both the prior eleven records and the new eight are unchanged down
to their original JSONL bytes. The old snapshot and original identity draft remain
untouched. No candidate inference, benchmark, scoring, tuning, model acquisition
or production change is performed here. All NEW extraction-quality results remain
NOT_EVALUATED; approved-label coverage is not measured model quality.

Starting HEAD: `cec7630a9e9a4da799f4ce1b03827e2f3d3be13b`.
At preparation start, `git status --short` and staged paths were empty. At ML-3
finalization start, only this preparation report was untracked; staging was empty.
All 90 original sources were verified with unchanged
`fidelity_eval._read_sources` / `verify_corpus`,
including hashes, sizes, suffixes, presence, unique identities/hashes and no
symlink/extra sources. Counts remain 30 PDF, 30 DOCX, 30 XLSX. Existing approved
eleven-record Gold passes unchanged `fidelity_gold.load_gold` and its file bytes
retain the frozen hash. It was read only, never rewritten.

The ML-1 readiness report authorizes a narrowly controlled experiment, not new
human labels. The earlier four-PDF result permits expanded offline evaluation
only. In particular, **c1-0050 success -> needs_review is an unresolved production
eligibility regression**, despite unchanged reviewed scores. This expansion does
not fix, waive or conceal it.

## Selection rule, evidence and exclusions

This is a purposive coverage sample, not a random or statistically representative
sample. No Docling outcome on any of the 26 eligible PDFs exists in this step or
is used for selection. Previously evaluated c1-0041, c1-0044, c1-0045 and c1-0050
are excluded before triage and selection, including the prior successful table.

Original metadata: physical PDF page counts, byte sizes, top-level image-bearing
page counts and Widget annotation counts. Metadata is read with existing pypdf
6.20.0; text extraction does NOT establish tables or reference evidence.
Retained pre-candidate pypdf baseline status, character counts and warning counts
come from the fingerprint-verified frozen 90-source control evaluation at
`evaluation-output/fidelity-controls-v1-approved-run1/metrics.json`, not the
Docling benchmark. The generic pdf_table_structure_not_preserved warning is
present across the pool and is NOT a table detector.

Local Poppler rendered the first physical page of every eligible PDF (26/26).
Codex visually inspected those original-page renders for layout triage only.
The frozen observations are:

- visible grid on first page: c1-0033, c1-0040, c1-0049, c1-0058;
- visible form: c1-0035, c1-0051;
- diagram: c1-0032;
- unclassified column arrangement: c1-0052;
- text-or-cover proxy: the other 18 eligible PDFs.

These are original-render observations, not parser-derived categories, human
approval, complete inventories or a claim that an entire document lacks tables.
The later user-supplied review is separate from this triage. Ambiguous columns
are deliberately not asserted to be a table. No author/source text is copied into
this report.

Apply the following rules in order, without replacement; all ties use ascending
opaque ID, and final records use ascending opaque ID:

1. First three IDs in the visually observed grid pool.
2. Form with the largest original Widget count.
3. First ID in the diagram pool.
4. Smallest byte size in the text-or-cover pool.
5. Largest page count among remaining baseline-success text-or-cover sources.
6. First remaining baseline-needs_review ID from all eligible PDFs.

This selects eight PDFs. No table cell, anchor, span or expected extraction result
is inferred by this algorithm. One needs_review source is deliberately retained;
failed/needs-review status never substitutes for a human fidelity judgement.
Unselected eligible sources are c1-0034, c1-0036, c1-0037, c1-0038, c1-0039,
c1-0042, c1-0046, c1-0047, c1-0051, c1-0052, c1-0053, c1-0054, c1-0055,
c1-0056, c1-0057, c1-0058, c1-0059, c1-0060. They are not failures or removals
from Corpus v1; the eight-document review workload is the current budget.

| ID | Selection stratum | Pages | Bytes | Retained baseline status | Original-render triage scope |
| --- | --- | ---: | ---: | --- | --- |
| c1-0031 | Short text control | 1 | 1732 | success | Page 1: short sectional narrative |
| c1-0032 | Diagram/layout | 1 | 20617 | success | Page 1: multi-column diagram with arrows and coloured regions |
| c1-0033 | Table | 1 | 29702 | success | Page 1: simple two-column bordered grid |
| c1-0035 | Form | 1 | 38361 | success | Page 1: boxes, labels and checkboxes; 34 Widget annotations |
| c1-0040 | Table | 1 | 64968 | success | Page 1: wide dense grid, grouped headers and coloured markers |
| c1-0043 | Needs-review control | 4 | 91484 | needs_review | Pages 1-3: narrative; page 4 visually blank |
| c1-0048 | Long text control | 17 | 228777 | success | Pages 1, 3, 9, 17: cover, contents, body/footnotes, sparse closing page |
| c1-0049 | Table/mixed-layout | 8 | 254032 | success | Pages 1, 4, 8: mixed grid, narrative and another grid |

Selected page denominator: 34, range 1-17 pages; size range 1732-254032 bytes.
Codex inspected 16/34 selected pages (plus first-page triage of the remaining
pool); the other 18 selected pages are NOT_INSPECTED. This is not 16 reviewed
Gold pages or a human annotation count. Seven selected sources have retained
baseline success, one needs_review, zero failed. Distinct table layouts are
observed on three source PDFs, not inferred from pypdf table counts. All eight
have distinct source-page references and file hashes, but neither source-page
URL uniqueness nor these layout observations prove full document-family
independence, semantic independence or near-duplicate absence.

## Historical draft and frozen sampling fingerprints

Private draft: `local-evaluation/pdf_gold_expansion_v1_draft.jsonl`.
It remains ignored, unchanged and must never be staged. It was not automatically
promoted: the human supplied a separate annotated reviewed input. Current approved
identities and coverage are recorded in the ML-3 freeze section below.

| Identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Frozen manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Full corpus identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Approved eleven-record Gold normalized | `896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c` |
| Approved eleven-record Gold bytes | `30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353` |
| Pre-candidate baseline report | `43de275fa5e7eb50aab054b53812e4fccaf50df379d949d61cd015c110bb91ee` |
| Eligible 26-PDF metadata | `9b88eaecd4dfb2b4c34328e370143cbcfedf2b4cfd6593e0dad5fe717e880c0b` |
| Sampling identity below | `0ab903e7a5a701e703282412f30a9d28f1bcacfa431122891206a11368774f40` |
| New eight-record draft normalized | `52ce97733f2f7e2d936d406c6fd234c9cb54e8fe65396884235a4b4231f0f7af` |
| New draft bytes | `bc989b9bcd48bb10f790e8b53a0fb814cc19966d217b4d58ea5e0b07585c2f7d` |

Normalized fingerprints use the existing `fidelity_gold.fingerprint` (sorted
keys, compact JSON, ensure_ascii=True). Draft fingerprint hashes the ordered
plain draft dictionaries, NOT validated FidelityRecord objects and NOT approved
Gold. The byte hash describes the current UTF-8 JSONL/LF serialization.

For reproducibility, the eligible metadata list is sorted by ID and each row has
document_id, size_bytes, pages, top_level_image_pages, widget_annotations,
baseline_status, baseline_text_characters, baseline_warning_counts and
source_page_group. The last field is the first 12 hex digits of SHA-256 of the
manifest source_page_url UTF-8 bytes, not an independently established family.
Image counts inspect only top-level page Resources/XObject Subtype=Image;
nested Form images can be missed. Widget counts inspect page Annots/Subtype=Widget;
they do not measure visual form correctness. Baseline warnings are unchanged
warning-count dictionaries. Recomputing this list and selection twice gave
identical complete results, not only identical hash strings.

The exact sanitized sampling-identity payload is below. Reconstruct it as JSON
and apply the existing fingerprint function; source bytes are independently
matched against the unchanged manifest, not guessed from local filenames.

```json
{
  "baseline_report_fingerprint": "43de275fa5e7eb50aab054b53812e4fccaf50df379d949d61cd015c110bb91ee",
  "corpus_fingerprint": "d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8",
  "excluded_pdf_ids": ["c1-0041","c1-0044","c1-0045","c1-0050"],
  "manifest_sha256": "c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0",
  "metadata_fingerprint": "9b88eaecd4dfb2b4c34328e370143cbcfedf2b4cfd6593e0dad5fe717e880c0b",
  "selected": [
    {"document_format":"pdf","document_id":"c1-0031","pages":1,"source_sha256":"1179d9f2925a83d6503608b8049b2a23b8e81f15a42d60e7bdd0bce52d6cc253","source_size_bytes":1732,"stratum":"short_text_control"},
    {"document_format":"pdf","document_id":"c1-0032","pages":1,"source_sha256":"5f9082eabbb52eaf71510592a043958cb7f67b955158f7d9d12435783bc52471","source_size_bytes":20617,"stratum":"diagram"},
    {"document_format":"pdf","document_id":"c1-0033","pages":1,"source_sha256":"081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd","source_size_bytes":29702,"stratum":"table_first_page"},
    {"document_format":"pdf","document_id":"c1-0035","pages":1,"source_sha256":"94a5b7cdc01f39d482683e7480f4f593089c54731d333d60544558db903b8c3a","source_size_bytes":38361,"stratum":"form"},
    {"document_format":"pdf","document_id":"c1-0040","pages":1,"source_sha256":"18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344","source_size_bytes":64968,"stratum":"table_first_page"},
    {"document_format":"pdf","document_id":"c1-0043","pages":4,"source_sha256":"b70a5d33160ee12eba6b5f66e305df69b6d504389c11c142657c41d2be45c3ce","source_size_bytes":91484,"stratum":"needs_review_control"},
    {"document_format":"pdf","document_id":"c1-0048","pages":17,"source_sha256":"5928ffa7f5f8d44678a56d810794f4263e4a3db9a7d87422ec8d3c6907186f4f","source_size_bytes":228777,"stratum":"long_text_control"},
    {"document_format":"pdf","document_id":"c1-0049","pages":8,"source_sha256":"fa821b92dde14335883c0327f70851d9b5813feea8584136eb125fe8833a9240","source_size_bytes":254032,"stratum":"table_first_page"}
  ],
  "selection_rules": ["three_lowest_grid_ids","max_widget_form_then_id","lowest_diagram_id","min_bytes_text_or_cover_then_id","max_pages_remaining_success_text_or_cover_then_id","lowest_remaining_needs_review_id"],
  "selection_version": "pdf-gold-expansion-v1",
  "triage_pools": {"diagram_on_first_page":["c1-0032"],"form_on_first_page":["c1-0035","c1-0051"],"grid_on_first_page":["c1-0033","c1-0040","c1-0049","c1-0058"],"text_or_cover_on_first_page":["c1-0031","c1-0034","c1-0036","c1-0037","c1-0038","c1-0039","c1-0042","c1-0043","c1-0046","c1-0047","c1-0048","c1-0053","c1-0054","c1-0055","c1-0056","c1-0057","c1-0059","c1-0060"],"unclassified_columns_on_first_page":["c1-0052"]}
}
```

## Original-document human-review checklist (preparation protocol)

The following checklist is retained as the acquisition protocol, not an outstanding
approval gate. The user has now supplied and approved eight annotated records;
Codex validates their contracts without claiming to repeat the human review.

Work locally from the originals matched by SHA-256, not from extracted text,
pypdf/Docling exports or model suggestions. Do not compare candidate outcomes
while creating labels. Review the entire selected source for context even when
only a small set of distinctive expectations is recorded.

1. Verify identity/hash/size first. Check physical page number versus any printed
   page label. Confirm the proposed stratum, table boundaries and language with
   a competent reviewer; record ambiguities privately rather than guessing.
2. Required anchors: choose about 4-6 useful, distinctive short ORIGINAL excerpts
   per document, adapted to actual content, including hard-to-extract content.
   Preserve original case/digits/punctuation; never translate to match a parser.
   Use unique anchor_id values, source page and actual occurrence. This is a
   workload target, not fabricated anchors or an enforced metric denominator.
3. Reading order: add a few reviewed before/after pairs within a page and, for
   multi-page sources, across pages. Use only unambiguous human reading order.
   Repeated header/footer text and diagram branches need special care; do not
   invent a total order for a non-linear graph.
4. Tables: on each of c1-0033, c1-0040 and c1-0049, verify at least one distinct
   table and aim for a small set of header/body cells across multiple rows and
   columns. Count headers and blank grid slots consistently from zero. Record
   true row_span/column_span, not defaults chosen to fit a parser. Use several
   same_row and same_column pairs with both endpoints in the same page/table.
   Include a merged/group header only if its original span is genuinely clear.
5. Provenance: PDF page_number is one-based; optional block_index follows the
   frozen page-slot convention (page_number - 1). Table indices are page-local,
   zero-based recognition order; choose visually unambiguous table scopes from
   the original, never from Docling output. Record zero-based row/column together.
   PDF table cells require explicit block/table/grid scope. If the original does
   not support an unambiguous locator, leave that assertion unresolved, not guessed.
6. Missing evidence: include original content even if a parser might omit it.
   A blank page/box is not automatically missing text. Do not delete an approved
   expectation after observing an extraction failure. No expansion missing-anchor
   counts exist until independent annotations are approved and evaluated.
7. Unsupported dimensions: identify graphical arrows/colour semantics, checkbox
   state, widget behaviour, image content, bounding boxes, rendered appearance,
   ambiguous multi-page tables and region distinctions that the frozen schema
   cannot express. Do not encode invented cells or alternative fields to force
   coverage. Record limitations privately and report NOT_EVALUATED separately.

Per-source review priorities (not reference annotations):

| Source | Priority observations to check in the original |
| --- | --- |
| c1-0031 | Distinct heading, sectional body anchors and short-document order |
| c1-0032 | Text in multiple diagram regions, readable page provenance; distinguish visible text order from unsupported arrow/colour semantics |
| c1-0033 | Header/body cells in both columns; same-row and same-column relationships; verify actual spans |
| c1-0035 | Labels near upper/lower form boxes and checkboxes; no invented entries in blank fields, no field filling or source saving |
| c1-0040 | Legible grid/header anchors in separate groups and columns; resolve header spans from the original; colour-only meaning remains unsupported |
| c1-0043 | Anchors/order across nonblank pages; independently confirm the blank page and language competence, do not assume scanned content |
| c1-0048 | Representative early/middle/late body anchors, contents-versus-body occurrences, footnote text, cross-page order and sparse closing page |
| c1-0049 | Several distinct page-local tables and narrative content; verify spans/scopes and relationships without joining separate tables across pages |

Use existing schema keys unchanged: schema_version=1.0,
dataset_revision=corpus-v1-fidelity-v1, dataset_kind=real,
review_basis=original_document, frozen source identity fields and the five
annotation lists. PDF records keep cells=[] (spreadsheet checks are not PDF
checks). TextAnchor uses text, source and optional occurrence; table_cells
references anchor_id with spans; order_pairs and table_relationships reference
existing distinct anchor IDs. Unknown fields, inconsistent coordinates, cycles
and cross-format locators must remain errors.

PDF schema supports body/drawing regions, not arbitrary footer/footnote region
values. Visible ancillary text may be checked at its genuine PDF page/body
location, without claiming a separate ancillary-region classifier. The frozen
contract cannot capture every graphical or visual dimension.

The original identity-only draft records still keep review_status=draft,
reviewer_count=0, reviewed_on=null, with ALL annotation lists empty.
Preparation checks compare their exact keys,
identity and review fields with the existing _template shape; they do NOT relax
FidelityRecord or construct a fake approved model. The actual unchanged
load_gold rejects this draft with GoldError, as required.

Only after genuine original-document review may the human populate evidence,
set reviewed with the actual positive reviewer count and non-future review date,
and explicitly approve a snapshot. Do not auto-promote empty drafts. Prefer a
second reviewer/adjudication for ambiguous grids and diagram ordering, but never
invent that participation. Preserve all eleven existing approved record lines
and bytes in their original file; a later approved combined snapshot must retain
those records exactly and append only genuinely reviewed new records. No approved
snapshot was generated at the preparation gate. The later explicitly authorized
ML-3 merge below uses the separately supplied reviewed records without editing them.

## ML-3 reviewed approval and byte-preserving merge

The supplied reviewed-eight input exists and has the exact user-pinned SHA-256.
Its suggested local-evaluation copy was absent. The attached input was therefore
read directly, without creating an additional unapproved copy. Its machine-specific
attachment path is intentionally omitted. The new private output is
`local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl`.

For all eight selected identities, review_status=reviewed, reviewer_count=1,
reviewed_on=2026-10-15, dataset_kind=real and review_basis=original_document.
The identities exactly match the frozen selection; none intersects the original
eleven. Approval is the user's explicit attestation, not proof of a second reviewer,
inter-reviewer agreement or independent semantic verification by the validator.

Before loading each of the old, new and combined files, the existing
`evaluation.gold._load_jsonl` rejects duplicate JSON keys, including nested keys.
The unchanged `fidelity_gold.load_gold` then checks the complete strict schema,
manifest SHA/size/format references, unique document/anchor identities, nonempty
evidence, locator types, positive spans, paired grid coordinates, table scopes,
consistent row/column relationships, order references and absence of order cycles.
Synthetic opt-in is disabled. No validator or schema is weakened or modified.

All ninety originals pass the existing corpus verifier. Read-only PDF page counts
also bound every reviewed PDF anchor's page and confirm any block_index uses the
page-slot convention. Schema consistency and page bounds are not independent
visual verification of every table grid, literal anchor or reading-order label;
that ground truth is the supplied original-document human review. No extraction
output or candidate result was used to repair or manufacture annotations.

Merge rule: the exact eleven-record file bytes followed by the exact reviewed-eight
file bytes, in that order. The old file already has a terminating LF; no separator,
JSON reserialization, newline normalization, annotation rewrite or sorting was
needed. A CreateNew binary stream prevented overwriting a pre-existing snapshot.
Both inputs remained read-only. Assertions check the complete concatenation, all
nineteen original record lines including line endings, and validated model equality.
Each of the nineteen raw records is byte-identical to its corresponding input.

The combined strict loader returns exactly nineteen unique document IDs and the
expected 12/3/4 format distribution. Repeating the complete read-only freeze audit
produced identical hashes, normalized fingerprints, membership and coverage counters.
The original frozen eleven-record file retains both its SHA and normalized fingerprint.

### Approved identities

| Identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Reviewed eight input bytes (user pin, verified) | `f71cadd434ace91aa573dc2bef38a58e2298a4ebf154a5a7f04ff2c2282637f6` |
| Reviewed eight normalized Gold | `69b3a6bfd5c2f7673aa3cff71b18cc163a6a980d28b972f9f3a39a53a470cac2` |
| Combined nineteen snapshot bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Combined nineteen normalized Gold | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Preserved eleven snapshot bytes | `30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353` |
| Preserved eleven normalized Gold | `896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c` |
| New eight source identity map | `4a856010bd8307f1d150916b63ab689d1792b92ac7128faf6a410895c343ad85` |
| Expanded nineteen source identity map | `81b2eb741cbd7b887cddfacf03bed9f305ac1ad66ced07358e6519e173499cb9` |
| Full ninety-source identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Unchanged Fidelity Gold validator source | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |
| Unchanged corpus verifier / evaluator source | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Unchanged duplicate-key guard source | `b7083c69d1f9f16dae2cabd51ed3161ec79110c91e2ef1aafa19e32513d31ad4` |

Gold normalization uses exactly `fingerprint([r.model_dump(mode="json") for r in
load_gold(snapshot, sources)])`; load_gold returns records sorted by document ID.
Input/output byte hashes do not use normalization. Source-map fingerprints hash
the ID-to-(SHA-256, size, format) mapping obtained from the existing corpus reader.

### Actual reviewed-label coverage, not fidelity scores

| Population | Documents | Anchors | Order pairs | Table-cell/span checks | Relationships | XLSX cell checks | Provenance labels |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Preserved eleven | 11 | 55 | 22 | 32 | 15 | 13 | 68 |
| New eight PDFs | 8 | 71 | 36 | 20 | 18 | 0 | 71 |
| Combined nineteen | 19 | 126 | 58 | 52 | 33 | 13 | 139 |
| PDF subset | 12 | 90 | 46 | 24 | 20 | 0 | 90 |
| DOCX subset | 3 | 15 | 6 | 7 | 3 | 0 | 15 |
| XLSX subset | 4 | 21 | 6 | 21 | 10 | 13 | 34 |

Provenance labels count anchors plus XLSX cell checks, not unique locations or
successfully extracted evidence. XLSX cells retain thirteen stored-value, formula
and cache expectations each; no formula was executed. Display checks remain zero.
Nineteen of ninety sources (21.11%) now have reviewed labels, leaving 71 unreviewed:
12/30 PDF, 3/30 DOCX, 4/30 XLSX. Every source remains in the ninety-source corpus.

Four new PDFs have table-cell labels: c1-0033, c1-0040, c1-0048 and c1-0049;
combined PDF table-label coverage is five source documents. c1-0048 was selected
as a long-text control but its human-supplied record also includes table checks.
The selection strata and labels were not altered to force the originally proposed
coverage. Label presence is not proof of complete table reconstruction or independence.

ML-3 closes the approval/identity-freeze step only. Family/near-duplicate completeness,
whole-document fidelity, semantic correctness independently verified by Codex,
inter-reviewer agreement, and all new parser quality/latency/memory comparisons remain
NOT_EVALUATED. The c1-0050 eligibility regression remains unresolved. A subsequent
separately scoped paired experiment must use these frozen labels without tuning
or relabelling against model outcomes; no such experiment is run here.

## Preparation verification (historical)

Executed from repository root:

```powershell
git rev-parse HEAD
git status --short
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_extraction_fidelity.py tests/unit/test_data_quality_gate.py tests/unit/test_docling_candidate.py
git check-ignore local-evaluation/pdf_gold_expansion_v1_draft.jsonl
git diff --check
git diff --no-index --check -- NUL docs/eda/pdf_gold_expansion_v1.md
git diff --cached --name-only
```

Read-only Python stdin audits invoked _read_sources, verify_corpus, load_gold,
fingerprint, _template and pypdf PdfReader. The metadata/selection audit ran twice;
all complete returned objects matched. Draft-only assertions check eight unique
identities, exclusion of the four old PDFs, exact existing template fields,
zero reviewers/null date/empty lists, manifest references and expected fingerprint.
Strict approved-Gold rejection is an expected PASS of the safety boundary, NOT
a validation failure to bypass. All 90 originals and approved eleven Gold records
remain intact.

Focused existing validation/regressions: **103 passed, 1 skipped** in 5.78 s in
the normal Windows runtime. The first sandboxed attempt had 102 passed, 1 failed,
1 skipped because Windows denied a SYNTHETIC fixture rename (WinError 5);
rerunning the same unchanged tests outside that sandbox passed. The skipped
physical-symlink fixture requires unavailable Windows privilege. No source/test
fix, dependency install or system permission change was made. Ruff is not
required/run because no Python file is changed. No service/E2E, new candidate
inference or quality evaluation is claimed.

Original pages were rendered read-only with local pdftoppm (-f/-l, -singlefile,
-scale-to, -png); disposable contact sheets enabled visual layout triage. No raw
text was printed or inserted into the draft/report. Private render intermediates
were outside the checkout, not deliverables or Git inputs. All 40 temporary PNGs
were removed after verifying the exact task-owned directory and PNG-only content;
the first short-lived sandbox render directory was already absent. Original PDFs
were not deleted or changed; renders are reproducible from those originals.
At the preparation gate only this report and the ignored identity draft were
retained. Privacy assertions passed for original filenames/paths, credential
patterns and distinctive approved excerpts; the then-new draft records contained
no annotations or reviewer approval data. Tracked-file diff and staged paths were
empty; the sole untracked non-ignored file was this report. No secret, model
artifact, raw PDF or private draft was staged.

The extraction-benchmark skill supplied the frozen-Gold/approval gate; the PDF
skill supplied original-render inspection instead of treating extracted text as
layout evidence. Neither inspection constituted genuine human approval; approval
now comes from the user's explicitly supplied reviewed-eight snapshot.

## ML-3 finalization verification and privacy

Actual commands include:

```powershell
git rev-parse HEAD
git status --short
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_extraction_fidelity.py tests/unit/test_data_quality_gate.py tests/unit/test_retrieval_eval.py
git check-ignore local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl local-evaluation/extraction_fidelity_v1_controls_reviewed.jsonl local-evaluation/pdf_gold_expansion_v1_draft.jsonl
git diff --check
git diff --cached --name-only
```

Read-only Python stdin audits call _load_jsonl, load_gold, _read_sources,
verify_corpus and fingerprint against the actual files, and use PdfReader only
for page metadata. Strict validation: PASS on all three snapshots (11/8/19).
Pinned reviewed-input SHA: PASS. Full corpus integrity: 90/90, zero missing or
changed sources. Nineteen exact raw record lines, both entire input byte blocks,
and all validated record objects are preserved. The freeze audit was run twice
and every reported field matched. In-memory synthetic probes confirmed rejection
of top-level and nested duplicate JSON keys without creating extra data files.

Relevant existing unit regressions: **100 passed, 1 skipped in 7.07 s**. The only
skip is the physical Windows symlink fixture, requiring unavailable privilege.
Tests ran in the normal Windows runtime to avoid the previously observed sandbox
synthetic-rename restriction. No tests, Python code, dependencies, production
settings or validators were changed. Ruff is not required for this report/data-only
step. No benchmark, scoring, external inference or model download was performed.

All private corpus, draft and approved snapshot files stay outside Git. Only this
sanitized Markdown is eligible for the requested commit. Final privacy/diff review
checks no raw annotations, original document names/paths, private excerpts,
credentials, model artifacts or unrelated files are staged. User approval and
review metadata are reported as sanitized attestations, without reviewer identity.
