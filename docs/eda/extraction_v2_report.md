# Extraction v2 — executed evidence and remaining prerequisites

21 October 2026. **Local offline engineering milestone: PASS.** The same 19
new files were reviewed, confirmed defects were reproduced and corrected, and
the local acceptance checks passed. **Full EX-01…EX-07 program: BLOCKED** on
external original/reference pairs and real RU/KK evaluation inputs. QG-00 and
QG-01: **NOT_EVALUATED**; candidate experiments: **INCONCLUSIVE**; production
release: **NOT AUTHORIZED**. One focused Conventional Commit is authorized by
the follow-up request. No new extraction/OCR/model experiment or training was run
during engineering review. The measurements below remain the original frozen runs.

The actual new corpus contains **30 additional DOCX + 30 additional XLSX** (60
attempted, 60 admitted, 21,413,089 bytes). Separately, 90 immutable v1 development
controls were measured. The unchanged native parser ran twice on all 150 inputs:
67 success, 66 needs_review, 17 failed in each pass. These states describe parser
outcomes, not factual fidelity. English selective OCR recovered nine selected
legacy anchors; 185 of 491 real proposed cells had machine source support.

## Scope, source authority and implementation boundary

Started on `main`, HEAD `1d291899e19ecae778f7c29b9a2a7a1872c8187d`.
The pre-existing untracked `independent_engineering_audit_20261020.md` was preserved.
Recent context was the current HEAD CI repair, `9e1f56f` and `5bf709d`.
Root AGENTS.md/source-map routing, the extraction/data-quality/ML-experiment skills,
[Extraction Strategy](../../DocLens_AI_Extraction_Strategy.md),
[ML Strategy](../../DocLens_AI_ML_Quality_Strategy.md),
[Quality Policy](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md), and
[ML-31](ml31_external_table_gold_feasibility.md) govern these observations.
The current v4 architecture remains the owner contract; no architecture migration
was repeated. Existing table/glyph/OCR experiments are historical controls only.

All implementation is isolated under `eda` and offline tools. Production parsers,
parser selection, ingestion, API/DB/migrations, ACTIVE publication/indexing and
deployment were not changed. No dependencies or model weights were added.
Originals, annotation payloads, source URLs/filenames, raw text/captures, detailed
acquisition decisions and resource journals remain in ignored local storage.

The [protocol](extraction_v2_protocol.md) records selection, budgets, scoring,
unsupported dimensions and H1/H2 before their real paired runs. Numerical budgets,
80/10/10 split sampling and diagnostic IoU/Jaccard settings are engineering settings,
not approved quality thresholds. Approved new acceptance thresholds remain TBD.
Schema validation, machine glyph support and successful extraction do not establish
human verification, independent Gold, QG-00/QG-01 PASS or release readiness.

## Stage verdicts

| Stage | Execution | Executed / blocked boundary |
| --- | --- | --- |
| EX-01 | BLOCKED | Bounded adapter, geometry tests, overlay/manual packet generator. No qualified original DocLayNet PDF/annotation/PNG pairs; representative real coverage and discrepancy report unavailable |
| EX-02 | PASS | Two native passes over all 60 eligible v2 Office documents plus 90 separately labelled legacy controls. New external PDF baseline and independent fidelity metrics NOT_EVALUATED |
| EX-03 | BLOCKED | Isolated matching/paired-text guard interface; layout candidate metadata investigated. Qualified paired PDF/layout cohort absent; no weights or inference executed |
| EX-04 | BLOCKED | PubTables/FinTabNet.c adapters and exact topology/literal diagnostic comparator. Qualified original table/reference pairs and independent Gold absent; no TSR weights/inference; GriTS/TEDS NOT_EVALUATED |
| EX-05 | PASS | Two identical real source-ruling/glyph alignment runs; ownership and conflict guards. Human independent verification and semantic header/unit/period relationships unavailable |
| EX-06 | BLOCKED | PDF routing diagnostics; twice-paired English OCR on four exposed controls; CER/WER/numeric/KK evaluators. Real RU/KK documents, rus/kaz traineddata and reviewed full transcripts absent; CER/WER and exhaustive duplication/source-alignment metrics NOT_EVALUATED |
| EX-07 | BLOCKED | Consolidated paired native/OCR/alignment evidence and comparison guardrails. Predecessor layout/table qualification and independent evaluation cohorts absent; no combined candidate executed |
| dataset | BLOCKED | 60 additional Office documents; five external metadata/card qualifications; integrity/family tooling. Five external payload cohorts not eligible; Own 50 RU/KK documents and independent Gold unavailable |

Every row has quality NOT_EVALUATED, experiment INCONCLUSIVE and production
authorization false. EX-02 PASS means complete measurement of all eligible admitted
v2 inputs and separately identified controls; it does not qualify unavailable new
PDF cohorts. EX-05 PASS means implemented/tested machine evidence verification,
not performed human adjudication. EX-06's English sub-run executed PASS; the
requested multilingual/full-transcript stage remains BLOCKED. Unexecuted layout,
TSR and combined comparisons are NOT_EVALUATED, not REJECT.

## Separate sampling targets and qualification

| Source | Target unit | New admitted | Verdict |
| --- | --- | --- | --- |
| DocLayNet | 100 PDF pages | 0 | BLOCKED: qualified original/PNG/auxiliary pairs and source rights |
| PubTables-1M | 100 table PDF pages | 0 | BLOCKED: original matching/rights; automatic reference is not independent Gold |
| FinTabNet.c | 50 tables | 0 | BLOCKED: original matching/rights; automatic reference is not independent Gold |
| OmniDocBench | 50 pages | 0 | BLOCKED: use scope and original/image-PDF pairing |
| Own RU/KK | 50 documents | 0 | BLOCKED: no authorized local source/Gold set |
| Additional DOCX | 30–50 documents | 30 | Minimum met; independent fidelity NOT_EVALUATED |
| Additional XLSX | 30–50 documents | 30 | Minimum met; independent fidelity NOT_EVALUATED |

Darmm is a separate synthetic OCR source, not an interchangeable eighth quota or
proof on real Kazakh documents. The 90 controls count toward none of these targets.

Five public repository metadata responses and five UTF-8 cards were obtained with
2 MiB / 256 KiB response limits. Revisions, byte sizes, SHA-256, known distribution
files and unresolved rights are in the [qualification JSON](extraction_v2_dataset_qualification.json).
Payload acquisition for these five datasets: **zero attempts, zero bytes, zero
admitted samples**; metadata attempts are not counted as attempted PDF pages.
No full archive or remote dataset script was downloaded/executed.

| Source / publisher | Pinned repository revision | License / original source boundary |
| --- | --- | --- |
| DocLayNet / IBM Research Deep Search / DocLayNet authors | `5656dbae459cf15b3a112d46bb6b5484cabcd2d2` | CDLA-Permissive-1.0; UNRESOLVED_PER_ITEM |
| pubtables-1m / Microsoft / Brandon Smock | `35b1c097807e0b07ec5313879b85956b7b3890db` | CDLA-Permissive-2.0; UNRESOLVED_PER_ITEM |
| FinTabNet.c / Brandon Smock et al.; original IBM FinTabNet authors | `e5673a90b98d02c4832f9e836d72762f0e8933a0` | CDLA-Permissive-2.0; UNRESOLVED_PER_ITEM |
| OmniDocBench / OpenDataLab / OmniDocBench authors | `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec` | research-only, non-commercial statement; no general data license established; UNRESOLVED_PER_ITEM |
| darmm-ocr-kazakh-v2 / Darmm / R3iwan | `f5a33769714977649657de7a7f649dbb6a596558` | Apache-2.0 declared by card; UNRESOLVED_PER_ITEM |

Publisher evidence: [DocLayNet author repository](https://github.com/DS4SD/DocLayNet)
documents the core and source-PDF extras; the pinned card declares CDLA-Permissive-1.0.
The core/extra archives are approximately 28/7.5 GiB, and no bounded qualified
original/annotation quartet was established in this run. Microsoft distinguishes
the [Table Transformer code and table datasets](https://github.com/microsoft/table-transformer);
its MIT code license is not the data/original-PDF license. PubTables and corrected
FinTabNet.c automatic canonicalization remains automatic reference, consistent with
ML-31. [OmniDocBench's pinned card](https://huggingface.co/datasets/opendatalab/OmniDocBench/raw/aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec/README.md)
states research-only/non-commercial terms; its pinned HF tree contains 1,651 images
and no PDF files. The card's separately described source slices/image-converted
PDFs do not establish a matched original endpoint here.
[Darmm's pinned card](https://huggingface.co/datasets/Darmm/darmm-ocr-kazakh-v2/raw/f5a33769714977649657de7a7f649dbb6a596558/README.md)
declares Apache-2.0 and synthetic Wikipedia/font rendering; underlying text/font
obligations and real-document transfer are unresolved. No commercial, redistribution
or independent-human-Gold eligibility is inferred from these declarations.

The additional Office acquisition reused the existing v1 GOV.UK/OGL policy.
Of 50 initial source pages, 49 qualified; one metadata response exceeded the 1 MiB
cap and was retained as blocked. The official
[GOV.UK Search API](https://docs.publishing.service.gov.uk/repos/search-api/using-the-search-api.html)
query `q=xlsx&count=20&fields=link` supplied 18 unseen source pages; all 18 qualified.
The first 340 unique Office candidate URLs excluded v1 URLs; supplemental metadata
added 16 XLSX entries. Deterministic SHA ranking selected 16 DOCX + 24 XLSX with a
two-attachments/source/format cap, then a metadata-only second revision filled
14 DOCX + six XLSX. The quota revision preceded parser observations. All unselected,
duplicate-v1, unavailable and attempted decisions remain in frozen local ledgers.
All 60 payload attempts succeeded within 2 MiB/file and 30 MiB total, with valid
Office signatures, attachment MIME/suffix, page association, OGL footer and
alternative-rights checks. Twenty-six source-page families are development-only;
languages/difficulty/content fidelity and family completeness are not reviewed.
The offline preparer rechecks all 60 assets and source evidence without network;
its replay equals the published manifest. Redistribution eligibility remains unknown.
Attribution: Contains public sector information licensed under the Open Government
Licence v3.0. No original documents are included in the new repository files.

## Integrity, provenance and family boundaries

The schema/validator checks strict types, duplicate JSON keys, immutable bytes,
format signatures, confined paths (including links/junctions), source/annotation
bindings, page geometry, rights/review provenance and family/split leakage.
Family components combine declared source/version/translation links, exact hashes,
normalized text hashes and declared near-duplicate groups. Human family review is
required for sealed tests; exposed/synthetic/legacy samples stay development-only.

Final checks: 111 pre-existing protected files unchanged, all 60 new assets intact,
150 distinct original SHA-256 values, 75 declared family components, zero declared
split leakage and zero sealed-test documents. Cross-cohort native-text diagnostics
found zero near-duplicate pairs among available outputs (131 nonempty documents).
Nineteen inputs have empty/failed native text. Translations, scans, unavailable text
and broader template families are not exhaustively checked. QG-00 and family
completeness remain NOT_EVALUATED; this is not an independent holdout.

## EX-01: implemented geometry, missing real cohort

The bounded DocLayNet adapter validates original PDF/PNG/COCO/auxiliary identity,
page number, MediaBox/CropBox, nonzero origins, frame choice, anisotropic scaling
and 0/90/180/270 rotation. Non-unit UserUnit and unknown classes are unsupported;
out-of-image annotations are reported, never clamped. Auxiliary text agreement is
automatic-reference presence. The packet generator creates a self-contained overlay,
original PDF copy, discrepancy JSON and unsigned manual checklist. Synthetic tests
exercise these paths; no qualified real DocLayNet representative packet or geometry
discrepancy measurement exists. Single/multicolumn, financial and complex-layout
real coverage therefore remains zero/unknown, not an inferred PASS.

## EX-02: frozen native baseline

The existing production native parser (pypdf 6.20.0 for PDFs) was invoked unchanged
in fresh CPU workers twice per eligible input. Every measured rejection is retained;
no failed input was substituted. The serial wrapper budget was 60 seconds/input,
sampled 1 GiB process-tree RSS, 256 MiB scratch, 20 ms polls and max 2,000 PDF pages.
Existing parser limits were preserved. Input/Gold/code/config/dependency/executable
and environment fingerprints were frozen and rechecked. Both complete non-runtime
reports and native raw result payloads repeat exactly; runtime was not expected to.

| Cohort | Format | Attempted | Eligible | Success | Review | Failed | P50 s, run 1 | P95 s, run 1 | Peak sampled RSS bytes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| controls | docx | 30 | 30 | 12 | 18 | 0 | 1.360 | 2.031 | 125784064 |
| controls | pdf | 30 | 30 | 27 | 3 | 0 | 1.312 | 2.359 | 78639104 |
| controls | xlsx | 30 | 30 | 13 | 11 | 6 | 1.297 | 3.312 | 707018752 |
| office | docx | 30 | 30 | 6 | 24 | 0 | 1.344 | 1.844 | 78483456 |
| office | xlsx | 30 | 30 | 9 | 10 | 11 | 1.359 | 5.250 | 310501376 |

| Cohort | Repetition | P50 s | P95 s | Peak sampled RSS bytes |
| --- | --- | --- | --- | --- |
| controls | 1 | 1.313 | 2.359 | 707018752 |
| controls | 2 | 1.313 | 2.218 | 707330048 |
| office | 1 | 1.344 | 3.454 | 310501376 |
| office | 2 | 1.344 | 3.875 | 309571584 |

All 17 failures are XLSX native rejections: legacy controls six `corrupt_document`;
new Office ten `corrupt_document` and one `limit_exceeded`. These are parser error
categories, not an independent diagnosis that 16 original files are corrupt. No
worker timeout/source-integrity failure occurred in the final native runs. Repairing
the unchanged production parser is outside this offline program. Warning counts,
opaque failed IDs and all per-language/family/difficulty/cohort/format slices for
both repetitions are retained in the [JSON](extraction_v2_results.json) and
losslessly flattened [CSV](extraction_v2_results.csv), with all denominators.

Existing v1 Gold is separately named **legacy review attestation**, never new v2
independent Gold: 19 labelled documents, 17 scored, two failed-XLSX documents
unscored. Unobserved labels remain in expected totals. New Office Gold is zero.

| Legacy metric | Passed | Observed labels | Expected labels | Unobserved |
| --- | --- | --- | --- | --- |
| cached_values | 7 | 7 | 13 | 6 |
| displayed_values | 0 | 0 | 0 | 0 |
| exact_numeric_anchors | 29 | 31 | 35 | 4 |
| formulas | 7 | 7 | 13 | 6 |
| provenance | 86 | 122 | 139 | 17 |
| reading_order | 41 | 56 | 58 | 2 |
| required_text_recall | 104 | 115 | 126 | 11 |
| stored_values | 7 | 7 | 13 | 6 |
| table_cells | 17 | 41 | 52 | 11 |
| table_relationships | 9 | 29 | 33 | 4 |

For the 12 legacy-labelled PDFs, required text is 79/90, order 31/46,
table cells 0/24, header/value relationships 0/20, locator/provenance checks 55/90,
and exact numeric-bearing selected anchors 20/22. Thus native parser success is
demonstrably insufficient for PDF table fidelity. The new strict numeric-anchor
check preserves signs/zeros/decimal separators with literal boundaries; it is not
exhaustive numeric/sign/unit correctness. Span F1, all-content numeric exact match,
independent locator precision and semantic relationships on new v2 data are
NOT_EVALUATED. Stored/formula/cache scores do not prove displayed-value correctness.

Timing includes interpreter/worker startup; OS caches were not reset. P50/P95 are
nearest rank. RSS is sampled process-tree resident memory and may miss short peaks
or double-count shared pages. These figures are local CPU diagnostics, not service
latency or statistical generalization. VRAM is not used/measured.

## EX-03/EX-04: isolated comparison support

The layout comparator supplies deterministic one-to-one class/page/IoU matching;
reading order is explicitly separate and NOT_EVALUATED when absent. A
[DocLayNet-trained Heron layout candidate](https://huggingface.co/docling-project/docling-layout-heron)
was investigated as a possible candidate, not downloaded or evaluated. No region
mAP or current-HEAD layout quality claim is made.

PubTables/FinTabNet.c adapters preserve blank/spanning cells and automatic topology
provenance. The exact cell comparator retains row/column/span/literal semantics and
duplicate/overlap guards; it does not invent header/unit/period relationships.
[Microsoft's pretrained Table Transformer](https://huggingface.co/microsoft/table-transformer-structure-recognition)
is an identified TSR candidate only. No weights/inference or valid new source-bound
TSR comparison was executed. Cell PRF helpers are tested; real independent PRF,
GriTS/TEDS, structure gains and loss tradeoffs remain NOT_EVALUATED. Existing frozen
rejections remain scoped historical controls, not a new REJECT verdict.

## EX-05: real source glyph-to-cell evidence

The verifier independently re-reads physical source rulings/PDFium glyph ranges
for five existing proposals against original SHA
`18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344`.
All 491 proposed cells were attempted twice; full private observations, pins,
sanitized cells and summaries repeat exactly.

| Observation | Count / denominator |
| --- | --- |
| Machine source-supported cells | 185/491 |
| Needs review | 306/491 |
| Native literal and candidate comparison available | 201/491 |
| Candidate literal conflicts | 0/201 compared |
| Unknown comparison | 290/491 |
| Duplicate glyph ownership | 0 |
| Independent human-verified cells | 0 |

Sixteen cells depend on generated whitespace/separators and 290 lack reliable
native glyphs; these stay needs_review. The two whitespace reason codes describe
the same 16 cells, and the two missing-glyph reason codes the same 290 cells;
reason counts must not be summed as disjoint observations. Missing/blank cells
are unknown, not proven empty. Relationships and calibrated confidence remain
null. Source PDF/page, table/cell, actual glyph range, native coordinates,
row/column/spans, candidate method/pins and diagnostics are retained privately.
No canonical financial value is formed by concatenating unrelated parser words.
Tests cover literal/numeric conflict rejection, duplicated ownership, missing
glyphs, inferred whitespace, repeated literals, merged cells and multicolumn
separation. Machine source support is useful evidence, not human-adjudicated Gold.

## EX-06: diagnostic routing and paired English OCR

Routing examined 30 existing PDFs / 143 pages: five likely scans, one low-text
unknown, 29 mixed-resource pages and 108 with native text. These are provisional
signals, not verified scan/CMap diagnoses or automatic OCR selection. Form images,
actual visible ink and CMap semantic correctness remain inspection limitations.

The existing selective native-first English Tesseract configuration was registered
fresh and rerun twice on four exposed historical development PDFs, 50 pages total.
English 300 DPI / OEM 1 / PSM 3 / one thread; limits 600 seconds/document, 3 GiB
sampled RSS, 256 MiB scratch, 40 pages/document, at most ten OCR pages. Five pages
were OCR'd and 45 retained native routing. No new production OCR route was added.

| Legacy selected metric | Native | Selective OCR |
| --- | --- | --- |
| required_text_recall | 10/19 | 19/19 |
| provenance | 6/19 | 15/19 |
| reading_order | 4/10 | 9/10 |
| table_cells | 0/4 | 0/4 |
| table_relationships | 0/2 | 0/2 |
| Numeric-bearing selected anchors (historical normalized scorer) | 9/9 | 9/9 |

| Repetition | Arm | P50 s | P95 s | Peak sampled RSS bytes |
| --- | --- | --- | --- | --- |
| 1 | baseline | 1.156 | 2.859 | 75485184 |
| 1 | candidate | 2.391 | 8.594 | 136085504 |
| 2 | baseline | 1.171 | 2.844 | 75517952 |
| 2 | candidate | 2.391 | 8.531 | 135938048 |

Both arms have two success/two needs_review documents; candidate anchors recovered
nine, lost zero. Quality fields, extracted result payloads, page decisions and tool
exit codes repeat exactly. Render/OCR timing/RSS differ and are retained. Native
text/source/kind and relative block sequence are preserved; inserting supplemental
OCR blocks reindexes absolute `order`, so complete native blocks are not claimed
byte-identical across arms. The two native-text controls received no OCR. This
does not establish absence of partial duplicate content on all mixed pages:
the reused candidate deduplicates whole-page whitespace-normalized strings only.

Reviewed full transcripts are unavailable; EN/RU/KK CER/WER, exhaustive duplicate
rate, all-content critical numeric errors and independent OCR spatial alignment
remain NOT_EVALUATED. Only `eng` and `osd` traineddata are installed; real RU/KK
documents and `rus`/`kaz` data are absent. The calculator covers Ә Ғ Қ Ң Ө Ұ Ү Һ І
and literal CER/WER/numeric additions/loss in synthetic regression tests. Neither
those tests nor Darmm synthetic data count as real Kazakh quality evidence.
Historical normalized OCR numeric-anchor scoring is explicitly different from the
new strict native numeric-anchor diagnostic. The larger OCR P95 is a measured cost,
not grounds to erase recovered evidence or claim general improvement.

## EX-07 and quality decision

No combined layout/table/OCR pipeline was executed because EX-01/03/04 and an
independent evaluation cohort were not qualified. Paired interfaces reject missing
pages and lost required literal evidence; this does not replace the absent combined
experiment. No sealed test was tuned. Region/order, cell/span/relationships, exact
numeric fidelity, locator precision and multilingual OCR remain separate dimensions.
No unexecuted comparison is labelled REJECT and no general QG PASS is claimed.

## Frozen identities

| Identity | SHA-256 / canonical fingerprint |
| --- | --- |
| HEAD | 1d291899e19ecae778f7c29b9a2a7a1872c8187d |
| Office manifest canonical | 508425d2616f1fe510e7a57e1a8b83991c688fa3264b0619a73c927ee1d3f946 |
| Office manifest bytes | 8e40445669b209af568d81c20c41c34257cd41f3cbc19ced2a5eebc77ccc8b54 |
| Legacy control manifest canonical | 73405377316ccf669aba52f33b128795b4cb21cba6ca95774e0bd8b752c29baf |
| Legacy control native result, both passes | 36272deb6563acfae2c82e02c1f6635f5a2162822f48339e868fe170f5e57503 |
| Legacy control native pins | 27987e2cfd98c305b61b5c6ee41a5160edad728c0a189533c0ed881a167f43fb |
| New Office native result, both passes | d9f419a6b67d5b352e5d4aff2d4384c8eab818e723b80d6ca145db8bb118e32d |
| New Office native pins | 590fab8ef7ca0781e6a629f08f719759076659038ead9c3e984c7fc7e5c40225 |
| Source alignment result, both passes | 5bd3a2c22c440f52a6e03deaec92f2622d8d427626379ff7a4bf5797bcdcc196 |
| Source alignment pins | 5bf9c584d868474c6a3973e5efc1a44c1a7e59b3f75c90648c3637620af3ffba |
| OCR registration | 3458dcb9d34e09fb1608295eecebab79f72a1be4ccc005c991adf9826638b4eb |
| OCR quality result, both passes | d2d34129acac1cc46a4a7a314230e0d181bff1375f03f3e9cd4112af1088e229 |
| Historical consolidated payload, before engineering review | 19e3feea312244aaf230be60bba1d96e3f5bb6dd84f8a36163d7e0c5b7214794 |
| Current consolidated payload (excluding its fingerprint field) | 6d7cf294a2575d4f998a140dddd2d59e19d62bbcc7648b94da919c830243a0c7 |
| Current alignment captured-observation replay | d9cafcaa9d249764831ee1127f8c2fe681945d2f00fef658ae2e0b9b2603c60e |
| Office offline preparer bytes | f300968963658b79d8c9e614e3c90591f2a0cbe77bc4e98c8d2d0f67a4d7f68c |

Historical measurement environment/code inventories and engine/renderer/language pins are included
in the sanitized JSON. Python 3.12.3, Windows AMD64, 16 logical CPUs; principal
libraries: pypdf 6.20.0, pydantic 2.14.0, pypdfium2 5.14.0, psutil 7.1.0,
pdfplumber 0.11.9. At original measurement close, native pins matched the worktree.
Review corrections changed offline code; historical pins were not overwritten and
are not current-code measurement claims. Original production parser/scorer code
remains unchanged. Raw runtime journals and originals stay ignored.

## Original experiment commands and outcomes (historical; not repeated by review)

Commands run from the repository root; `.venv/Scripts/python.exe` is the actual
interpreter. Fresh output paths are required; do not overwrite completed runs.
The following measurement commands completed with exit 0:

```powershell
.venv/Scripts/python.exe -m tools.extraction_quality.office_corpus_v2 --template docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --ledger evaluation-output/extraction-v2-20261021/office-discovery/acquisition-ledger.json --ledger evaluation-output/extraction-v2-20261021/office-discovery/revision-2/acquisition-ledger.json --legacy-manifest docs/eda/corpus_v1_manifest.csv --output evaluation-output/extraction-v2-20261021/office-manifest-replayed.json
.venv/Scripts/python.exe -m tools.extraction_quality.extraction_v2 validate --manifest docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --output evaluation-output/extraction-v2-20261021/office-validation-final.json
.venv/Scripts/python.exe -m tools.extraction_quality.extraction_v2 baseline --manifest evaluation-output/extraction-v2-20261021/control-manifest-final.json --root local-corpus --legacy-gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output evaluation-output/extraction-v2-20261021/native-controls-final
.venv/Scripts/python.exe -m tools.extraction_quality.extraction_v2 baseline --manifest docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --output evaluation-output/extraction-v2-20261021/native-office-final
.venv/Scripts/python.exe -m tools.extraction_quality.ocr_diagnostics_v2 --manifest evaluation-output/extraction-v2-20261021/control-manifest-final.json --root local-corpus --output evaluation-output/extraction-v2-20261021/ocr-diagnostics
```

The Office replay fingerprint equals the public manifest; validator PASS has 60/60
eligible, no asset issues, independent Gold zero. Each baseline command itself runs
two passes and returns execution PASS. Routing diagnostics completed 30/30 PDFs.
Two source-alignment calls used the same five proposals and original SHA (only the
fresh output suffix differed):

```powershell
.venv/Scripts/python.exe -m tools.extraction_quality.source_alignment_v2 --source local-corpus/pdf/pdf-0010.pdf --source-sha256 18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344 --proposal evaluation-output/c1-0040-machine-20261020/workspace/vector-proposals/c1-0040-0.json --proposal evaluation-output/c1-0040-machine-20261020/workspace/vector-proposals/c1-0040-1.json --proposal evaluation-output/c1-0040-machine-20261020/workspace/vector-proposals/c1-0040-2.json --proposal evaluation-output/c1-0040-machine-20261020/workspace/vector-proposals/c1-0040-3.json --proposal evaluation-output/c1-0040-machine-20261020/workspace/vector-proposals/c1-0040-4.json --output evaluation-output/extraction-v2-20261021/alignment-final-1
```

The second call used `alignment-final-2`; both exit 0. The OCR freeze/run effective
arguments are shown below using variables for the machine-specific executable paths
whose hashes are frozen in registration. The actual paths resolved under this host's
USERPROFILE and Program Files; no tool installation was performed.

```powershell
$env:PYTHONPATH=(Get-Location).Path
$tesseract='C:/Program Files/Tesseract-OCR/tesseract.exe'
$renderer=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.EXE'
$tessdata='C:/Program Files/Tesseract-OCR/tessdata'
.venv/Scripts/python.exe -m tools.pdf_ocr_candidate.benchmark --documents c1-0041 c1-0044 c1-0045 c1-0050 --tesseract $tesseract --renderer $renderer --tessdata $tessdata --registration evaluation-output/extraction-v2-20261021/ocr-registration.json --freeze
.venv/Scripts/python.exe -m tools.pdf_ocr_candidate.benchmark --documents c1-0041 c1-0044 c1-0045 c1-0050 --tesseract $tesseract --renderer $renderer --tessdata $tessdata --registration evaluation-output/extraction-v2-20261021/ocr-registration.json --output evaluation-output/extraction-v2-20261021/ocr-run-1
.venv/Scripts/python.exe -m tools.pdf_ocr_candidate.benchmark --documents c1-0041 c1-0044 c1-0045 c1-0050 --tesseract $tesseract --renderer $renderer --tessdata $tessdata --registration evaluation-output/extraction-v2-20261021/ocr-registration.json --output evaluation-output/extraction-v2-20261021/ocr-run-2
```

All three OCR calls exit 0, with equal quality fingerprints and no worker failures.
Assembly command (ignored local script, not a production entry point):

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv/Scripts/python.exe evaluation-output/extraction-v2-20261021/finalize_evidence.py
```

At original close this rechecked 111 protected files, schema sync, all source assets and both native
pins/reports/raw payloads, compares full alignment evidence, compares OCR extracted
payloads/page decisions/exit codes while retaining timing differences, checks native
relative sequence, and exported the then-current JSON/CSV. Exit 0; 20,720 CSV rows.
Review found 290 omitted empty objects in that CSV; the corrected current projection
includes them. This historical assembly script is not valid for asserting current pins.
The consolidated fingerprint is over the JSON payload before adding its own field.

Verification commands/outcomes:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_corpus_v2.py tests/unit/test_dataset_adapters_v2.py tests/unit/test_extraction_v2.py tests/unit/test_office_corpus_v2.py -q -p no:cacheprovider --basetemp=evaluation-output/extraction-v2-20261021/tests-final-confirmation
# 75 passed in 6.77s
.venv/Scripts/python.exe -m ruff check src tests tools alembic
# All checks passed
.venv/Scripts/python.exe evaluation-output/extraction-v2-20261021/run_portable.py
# 1548 passed, 1 skipped, 3 deselected in 165.40s
```

The full portable wrapper invokes the configured CI unit-test scope:

```powershell
$env:PYTHONPATH=(Get-Location).Path
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.venv/Scripts/python.exe -m pytest tests/unit -q --strict-config --strict-markers -p no:cacheprovider -o faulthandler_timeout=60 --basetemp=evaluation-output/extraction-v2-20261021/tests-portable-complete --deselect=tests/unit/test_pdf_review_visual.py::test_browser_rendered_mouse_selection --deselect=tests/unit/test_pdf_grid_proposals.py::test_grid_http_security_and_browser --deselect=tests/unit/test_pdf_proposal_review.py::test_browser_confirm_correct_reject_and_export
```

The wrapper above was the executed full-suite command; the expanded command shows
its exact effective pytest arguments/environment. It required execution with local
loopback available because existing HTTP/asyncio tests cannot run inside the initial
restricted socket environment. The three Node/Playwright/browser tests are the exact
configured CI deselections. One existing symlink test skipped at
`tests/unit/test_data_quality_gate.py:432`: Windows symlink privilege unavailable.
No configured static type-check command exists in pyproject/CI; Ruff is the configured
lint check. PostgreSQL/S3/Qdrant/API integration, browser E2E, GPU and production
qualification were not run in this offline service-free scope. Synthetic unit
failure/security/HTTP/parser tests remain included.

The 75 new focused cases include incorrect/missing/changed assets, rights/review
provenance, duplicate JSON/path/link/pairing errors, family/translation/near-duplicate
leakage, rotated/cropped/nonzero-origin PDFs, unknown geometry, blank/merged cells,
glyph ownership/literal/numeric conflicts, invalid/missing locators, OCR duplication
and native loss, incomplete candidates, timeout/worker failure capture, quota and
source MIME/rights/metadata faults. Existing extraction/table/fidelity/OCR regressions
are included in the passing full portable suite.

## Failed/excluded attempts retained

- Initial external metadata requests failed sandbox DNS and web-reader access;
  bounded public retries succeeded. First card decode used cp1251 and failed;
  explicit UTF-8 retry succeeded. Five-dataset payload blockers were not hidden.
- One of 68 Office source-page metadata attempts exceeded the cap; the other 67
  qualified. Outside-budget and duplicate-v1 URL exclusions remain local. No
  replacement was selected based on parser quality; final payload attempts 60/60.
- Initial control preparation rejected unmodelled v1 Welsh labels. The schema now
  preserves them; no control language was silently changed to English.
- An initial native pair exposed a new aggregation defect (`total` versus the
  existing scorer's `evaluated`). It was fixed with a regression test; those reports
  remain in `native-final/` and are not final metric evidence. Both final native
  cohorts were rerun entirely with frozen corrected code, retaining all failures.
- Initial broad tests hung where restricted loopback prevented asyncio sockets;
  they were interrupted. An environment-only rerun without repository PYTHONPATH
  had 1,537 passed, two failed, one skipped, three deselected (tool imports). Correct
  CI PYTHONPATH yielded 1,539 passed before Office cases were added. Original complete
  run was 1,548 passed as above; no production code was changed to hide these faults.
- The first evidence-assembly assertion compared OCR runtime telemetry as well as
  deterministic fields and failed. Inspection found extracted payloads identical;
  only render/OCR seconds/RSS differed. Assembly now explicitly compares output,
  page/ink decisions and tool exit codes and retains both runtime records.
- Final native parser rejections (17) and legacy observed/missing fidelity failures
  remain measured outcomes, not removed observations. The final candidate checks
  introduced no demonstrated critical loss on their narrow exposed samples.

## Engineering review: defects, evidence and acceptance

The exact starting inventory was 19 new scoped files plus one pre-existing untracked
audit, which remains excluded and unchanged. Every source/test/protocol/report was
read; all manifest/schema/qualification/result JSON records and CSV leaves were
parsed and reconciled. Original copies/hashes remain in ignored review storage.

Confirmed corrections:

- Duplicate source-record/page identities under different opaque sample IDs are
  rejected; separate valid records in one family remain accepted. Exact/version/
  translation/near-family split guards remain in place.
  A confirmed PDF page-identity mismatch now records QG-00 FAIL rather than
  NOT_EVALUATED; valid captured inputs retain their unchanged verdicts.
- A synthetic fixture supplied with human review can no longer count as new real
  independent Gold. This is an evidence-class correction, not human identity proof.
- Negative/boolean table page indices, malformed table boxes and nonpositive/NaN
  image dimensions are rejected. Exact-cell scoring rejects invalid pages and
  unknown text (`null`); a known blank string is different and remains supported.
  Annotation kind now constrains the coordinate basis and JSON payload format;
  publisher top-left table coordinates cannot be labelled native PDF user space.
- OCR CLI enforces corpus eligibility before reading a source, retains blocked/
  failed rows, and returns BLOCKED instead of success on incomplete diagnostics.
- Alignment's former sanitized-only fingerprint could stay identical for differing
  conflicting candidates. The corrected fingerprint includes source/candidate/
  cell/geometry/native observations, and pins its numeric-tokenizer dependency.
  The historical alignment fingerprint remains historical; no old run is rewritten.
- The old CSV omitted 290 empty objects; all existing scalar values agreed with
  JSON. The canonical projection now preserves empty objects and containers. A
  committed `verify-results` command rejects incomplete repetitions/rows, corrupt
  aggregates/slices and JSON/CSV discrepancies even after a checksum is recomputed.
- Engineering PASS is now distinct from program BLOCKED, QG-00/QG-01
  NOT_EVALUATED, experiments INCONCLUSIVE and production NOT AUTHORIZED.

Before fixes the focused reproduction run had **13 failed, 68 passed**. Intermediate
focused checks passed (90 and then 95 cases). Two further coordinate-basis cases
and the existing page-identity QG assertion also failed before their correction.
Final focused checks: **98 passed**, JUnit elapsed 16.35 s.
Full configured portable unit scope: **1571 passed, 1 skipped, 3 deselected**,
JUnit elapsed 217.23 s. The original 1548/1/3 measurement is retained above as historical;
23 added regression cases explain the new pass count. The same Windows symlink
privilege skip and three CI browser deselections apply. Ruff passed. No configured
static type-check command or service integration/GPU scope was added.

The evidence audit checked **all 300 native captures**, both full reports, every
slice/summary/label denominator, recorded sampled RSS maxima and the frozen input
identities. It recomputed selected legacy scores from captures without extraction.
It confirmed 150 distinct inputs; 67/66/17 outcomes; 30 additional DOCX/30 XLSX;
111 protected files unchanged; 185/491 machine-source-supported cells, zero verified
semantic table relationships and zero new human reviews; nine English-only anchor
recoveries. This is not RU/KK OCR evidence or semantic table verification.

Read-only inspection of the 17 failed Office packages found custom number-format
IDs below 164 in all 16 `corrupt_document` cases. This is consistent with the
unchanged parser's `_xlsx_number_formats` guard rejecting such IDs; no parser was
reexecuted to claim a complete causal trace. The one `limit_exceeded` result has no
new specific cause established. All error categories, IDs and failures remain in
the results; original file corruption is not asserted. Repair is outside scope.

Current alignment guards were replayed twice over the frozen native observations;
both replays agree and preserve all 491 cell dispositions. This replay is not new
PDF glyph extraction or a new experiment. Historical code hashes match preserved
pre-review source snapshots; current code hashes are separately recorded. Production
parser/scorer hashes remain unchanged. The Office rights/source/bytes preparer
replayed all 60 assets offline and produced the same manifest fingerprint.

Exact review commands (fresh ignored destinations; repository-root PYTHONPATH):

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv/Scripts/python.exe evaluation-output/extraction-v2-review-20261021/audit_evidence.py
# PASS: 19 files, 111 protected hashes, 300 native captures, no new experiments
.venv/Scripts/python.exe -m tools.extraction_quality.office_corpus_v2 --template docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --ledger evaluation-output/extraction-v2-20261021/office-discovery/acquisition-ledger.json --ledger evaluation-output/extraction-v2-20261021/office-discovery/revision-2/acquisition-ledger.json --legacy-manifest docs/eda/corpus_v1_manifest.csv --output evaluation-output/extraction-v2-review-20261021/office-manifest-replayed.json
# PASS: 60 documents; same canonical manifest fingerprint
.venv/Scripts/python.exe -m pytest tests/unit/test_corpus_v2.py tests/unit/test_dataset_adapters_v2.py tests/unit/test_extraction_v2.py tests/unit/test_office_corpus_v2.py -q -p no:cacheprovider --basetemp=evaluation-output/extraction-v2-review-20261021/focused-accepted --junitxml=evaluation-output/extraction-v2-review-20261021/focused-accepted.xml
# 98 passed; JUnit elapsed 16.35 s
.venv/Scripts/python.exe -m ruff check src tests tools alembic
# All checks passed
.venv/Scripts/python.exe evaluation-output/extraction-v2-review-20261021/run_portable_accepted.py
# 1571 passed, 1 skipped, 3 deselected; JUnit elapsed 217.23 s
.venv/Scripts/python.exe -m tools.extraction_quality.extraction_v2 verify-results --results docs/eda/extraction_v2_results.json --csv docs/eda/extraction_v2_results.csv
# PASS: complete JSON/CSV, native repeats/slices and alignment/OCR accounting
```

The review portable wrapper uses the original CI scope/deselections/environment
shown above, replacing basetemp with
`evaluation-output/extraction-v2-review-20261021/tests-portable-accepted` and adding
`--junitxml=evaluation-output/extraction-v2-review-20261021/portable-accepted.xml`.
Local loopback was permitted for the existing HTTP/asyncio unit tests. No completed
native/OCR comparison was repeated. The pre-correction `verify-results` check
rejected the old incomplete CSV; current regenerated results pass. The five dataset
qualification request counters now distinguish one **obtained** response per
dataset from unknown total requests including failed transports/readers; missing
request history is not assigned an invented count.

JSON/CSV current canonical fingerprint: `6d7cf294a2575d4f998a140dddd2d59e19d62bbcc7648b94da919c830243a0c7`.
Current CSV leaf rows: **21156**. The previous 20,720 rows and fingerprint
refer only to the historical pre-review artifact. The engineering audit does not
create new quality thresholds or unblock external cohorts.

## Changed files and Git review

New scoped files only; no tracked production file modifications. The 19 additions:

- `src/doclens_ai/eda/corpus_v2.py`: versioned provenance schema, integrity/eligibility,
  family-safe split constraints and bounded deterministic sampling/near checks.
- `src/doclens_ai/eda/dataset_adapters_v2.py`: DocLayNet/PubTables/FinTabNet.c/
  OmniDocBench/Darmm bounded local annotation adapters and coordinate validation.
- `tools/extraction_quality/extraction_v2.py`: frozen native pair runner and scoring.
- `tools/extraction_quality/office_corpus_v2.py`: bounded offline Office reconstruction.
- `tools/extraction_quality/geometry_v2.py`: private unsigned visual review packet.
- `tools/extraction_quality/comparison_v2.py`: isolated diagnostic layout/topology/
  literal comparison and paired completeness/loss guards.
- `tools/extraction_quality/source_alignment_v2.py`: source glyph ownership/conflict
  verifier; `ocr_diagnostics_v2.py`: provisional page routes and literal OCR diagnostics.
- Four tests: `test_corpus_v2.py`, `test_dataset_adapters_v2.py`,
  `test_extraction_v2.py`, `test_office_corpus_v2.py` under `tests/unit/`.
- Seven `docs/eda` artifacts: manifest, schema, qualification, protocol, this report,
  results JSON and results CSV. No original content/Gold/model/archive was added.

The original working tree had these 19 scoped additions plus the excluded audit.
The engineering request authorizes staging only the accepted 19 files, inspecting
the complete staged diff and `git diff --cached --check`, then creating one focused
Conventional Commit. No raw documents, private corpus/Gold, original filenames,
source metadata bodies or model artifacts belong to the staged change. Final commit
SHA and exact post-commit status are reported in the completion response; the report
does not embed its own commit SHA. The excluded audit must remain the sole untracked
item after that commit. There are no production or project-instruction changes.

## Remaining prerequisites — stop at this program boundary

Final engineering acceptance also executed the following post-regeneration checks:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_v2.py -k delivered_results -q -p no:cacheprovider --basetemp=evaluation-output/extraction-v2-review-20261021/post-regeneration
# 5 passed, 27 deselected in 2.03s
.venv/Scripts/python.exe evaluation-output/extraction-v2-review-20261021/acceptance_gate.py --staged
# PASS: exactly 19 staged files, 111 protected files unchanged; complete staged
# diff and every blob inspected; public artifacts/secret/whitespace checks passed
git diff --cached --check
# exit 0, no output
```

The entire staged diff, including previously untracked files, was read and checked;
the existing audit was excluded. Git's configured `core.autocrlf=true` normalizes
line endings: staged blobs and worktree content agree after CRLF/LF normalization.
Historical raw-byte fingerprints describe their measured Windows files; canonical
JSON fingerprints do not depend on line endings. No historical byte pin was changed
to conceal normalization. Only the accepted 19-file change is authorized for commit.

Obtain bounded legally eligible original/reference quartets for DocLayNet and
source-bound table pairs for PubTables/FinTabNet.c; resolve OmniDocBench use/original
pair identity and Darmm underlying obligations. Supply the separate 50 authorized
own RU/KK documents, actual independent review/family provenance and full transcripts,
plus eligible Russian/Kazakh OCR resources. Complete representative geometry review,
then freeze/evaluate layout and TSR candidates on identical sources, and only then
run a combined independent offline comparison. None of these future experiments
was silently started. Investigate the 17 native XLSX rejections in a separate
authorized production-parser task if desired. Current numeric/semantic/locator
coverage, family completeness and quality gates remain unqualified; production
release requires its own operational/security/service gates.
