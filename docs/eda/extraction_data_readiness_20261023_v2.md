# Extraction Data Readiness — autonomous continuation v2

STATUS: **BLOCKED for independent quality/Test acceptance. Engineering PASS for
the limited development data candidate and its executed validation scope.**
QG-00: **NOT_EVALUATED**. QG-01: **NOT_EVALUATED**. TEST_NOT_READY.
No candidate-model experiment, training, GPU/cloud inference, deployment or push.

The run started at `97ca3bf86818db172f9ad3252b5301f5f5c88c76`, on
`codex/extraction-research-20261023`. It preserved the existing R1/Kaggle/audit
work. This report supersedes the earlier readiness report only for the new
candidate; historical measurements and frozen inputs remain historical.

## CHANGED and DESIGN

Requirements came from root `AGENTS.md`, `README_SOURCE_MAP.md`, the data-quality
skill, Quality Policy QG-00/QG-01, ML Strategy ML-DATA and Extraction Strategy
EX-PDF/EX-DOCX/EX-XLSX. The implemented scope is source preparation, rights,
isolation, integrity and candidate-neutral diagnostic evaluation. Independent
review, approved quality thresholds and production qualification are separate.

- `office_readiness_oracle.py`: namespace-qualified physical DOCX paths,
  ancillary-part root validation, style validation and bounded selection of
  actual XLSX cells. No rendered DOCX pages, formula execution or inferred display.
- `readiness_source_checks.py`: original SHA-bound PDF glyph/ruling/raster checks
  over existing proposals, literal signs/repetition and genuine OOXML resolution.
  It generates no replacement PDF geometry and asserts no human review.
- `readiness_pdf_metrics.py` / `readiness_evaluator.py`: separate geometry,
  literal, row/column/span and anchor denominators by reference tier. Missing
  fields earn no credit. Failure reasons and all registered sources are retained.
  Wrong format/source, invalid spans, out-of-page boxes, reserved families and
  sealed candidates are rejected. Model identity does not change scoring rules.
- `readiness_io.py` / `readiness_release.py`: atomic checkpoints, frozen-directory
  write rejection, parent verification using archived code, source-specific rights
  changes and existing family-component checks. Scoring additionally requires the
  active code to match the frozen code. Freeze validates actual Office/PDF bindings.
- Focused regression tests cover the discovered defects and negative scenarios.
  Private originals, annotations, receipts and release artifacts remain ignored.

## Actual population and tiers

| Population | Count |
| --- | ---: |
| Original legacy corpus, preserved | 150 |
| Previous new registrations, preserved without reacquisition | 50 |
| Continuation registrations | 17 |
| Total distinct original SHA-256 identities | **217** |
| PDF / DOCX / XLSX | **52 / 80 / 85** |
| Historical parser success / needs_review / failed | **69 / 77 / 4** |
| Newly registered sources without parser runs | **67 NOT_ATTEMPTED** |

Of the 17 additions, 14 are publisher-version-bound scientific PDFs, two are
small newly acquired statistical XLSX originals, and one is an already held,
previously unregistered Kazakh XLSX. Sixteen new originals were downloaded;
there was no replacement or reacquisition of the existing 200 registrations.

All 53 Kazakhstan registrations have source-content language evidence:
**RU 26, KK 19, mixed 8**. The three additions are KK 2 / mixed 1. The bilingual
workbook was identified from actual Russian and Kazakh clauses, despite its
Kazakh publication metadata. Existing 50 language decisions were preserved and
their source identities/evidence checked. These are source-native language
observations, not independent human language attestations.

The complete matrix's retained language labels are **EN 102, CY 2, unknown 60,
RU 26, KK 19, mixed 8**. In particular, the 60 historical unknowns were not silently
called English. The historical corpus was not subjected to another full EDA.

| Evidence tier | Actual count and limit |
| --- | --- |
| Historical partial extraction Gold | 19 documents / 282 assertions; unchanged |
| New independent human Gold | **0** |
| DOCX source-native oracles | **10**, up from 7 |
| XLSX source-native oracles | **11**, reusing the existing 10 |
| Office observation records | **45,049**, including sheet records |
| Assisted PDF proposals | **1,154**, unchanged geometry/proposal identities |
| Inherited agent visual observations | **116**, preserved separately |
| Inherited whitespace correction proposals | **2**, not applied to historical Gold |
| Source-native PDF references | 2 documents |
| Publisher automatic table references | 25 tables / 14 originals / 20 distinct pages |
| Approved independent Test | **0** |

The 10 DOCX contain 14,396 independently source-resolved physical XML locators,
6,274 paragraphs, 77 table nodes, 1,423 grid-span nodes, 43 vertical merges,
40 footnotes and 22 endnote nodes. Literal XML and attributes were checked against
the original elements, including ancillary parts. Physical part order is not
rendered or global semantic reading order. Additional originals cover genuine
nested tables and notes; no page numbers were invented.

XLSX references contain 30,595 physical cells, including stored errors, zeros,
blanks, number/date formats, merges, cached and shared formulas. There are 112
PRESENT and 2 EMPTY formula caches; **no real MISSING-cache example was found in
this selected cohort**. MISSING versus EMPTY is covered by a regression fixture,
not falsely counted as real-world coverage. Display values remain unverified;
formulas were never calculated. The large workbook contributes only seven
targeted cells covering eight observed features, not whole-workbook fidelity.

## Source checks, corrections and exclusions

Every one of the 95 previously unresolved historical assertions has an original
identity, assertion ID, source method/evidence, limitations and reviewer requirement
in `historical-assertions-v2.json`. **13 are technically source-resolved; 82 are
not fully resolved.** The 13 comprise eight literal/physical-cell checks, four
unique literal/page-box checks and one DOCX footnote literal/region check.
Sixteen of the remaining 82 have useful physical extent/alignment evidence;
their logical spans/relationships were deliberately not declared resolved.
Historical Gold was not edited. Rights fields in these diagnostic records retain
their at-capture context; `effective-matrix.json` owns the final use decisions.

The existing **536 PDF cells** were reused without regenerating geometry:

- **244** visible literal cells have reliable source ownership and supported bounds.
- **270** empty interiors have supported bounds and a uniformly white raster interior.
- **20** proposed blanks remain unresolved; shaded/dark uniform interiors are not
  accepted as empty cells. A false blank with visible glyphs is explicitly rejected.
- **2** geometries lack sufficient physical support and are excluded from scoring.

All **62 anchors and 115 printed symbols** have literal support at the bound page
region. Repeated values retain separate genuine locators. Unicode signs and
currency symbols are preserved; compact comparison removes whitespace only and
does not infer currency codes. Exact spacing, logical grid meaning, reading order
and semantic relationships remain separate. All **199 speculative semantic links**
are excluded from scoring; 224 roles and six reading-order proposals stay unreviewed.
The two inherited visual whitespace changes remain proposals, not automatic fixes.

PDF diagnostic references cover **2,642 cell boxes**, with **2,113 known compact
literal fields**. Unknown literal fields are omitted, never interpreted as blanks.
The source-only tier supplies 534 boxes / 514 literal fields. The publisher tier
supplies 2,108 boxes, 1,599 source-agreeing literal fields and separate automatic
row/column/span fields. **509 publisher/source literal disagreements** are retained
in evidence and excluded from literal scoring. No aggregate Extraction Accuracy
or factual PASS is calculated. Existing diagnostic IoU 0.5 is not a quality gate.

The final unresolved reviewer queue has **547 items/dimensions**, including the
82 historical items and two inherited correction decisions. Machine-decidable
literal observations are not simply requeued as unfinished technical work.
Independent human Gold still requires authentic review of whichever evidence
is proposed for promotion. No human identity, signature or attestation was fabricated.

## Rights, external sources and Test preparation

Final source scopes: **213 evaluation-admitted / 4 quarantined**, and
**89 annotation-admitted / 128 unknown**. Training and cloud processing are unknown
for all 217. The previous 50 redistribution admissions are preserved; no new
redistribution scope was needed. Scope-specific evidence binds original SHA,
publisher page/version, exact captured terms and conditions. The two additional
DOCX originals explicitly offer OGL reuse. Restricted and populated third-party
Office sources remain quarantined; public accessibility does not override notices.

Primary evidence includes the [OGL v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/),
[BNS reuse terms](https://stat.gov.kz/ru/description/) and individual publisher
CC BY/CC0 grants captured from original article XML. These are documentary
interpretations, not independent legal attestations or blanket dataset-card grants.

For PubTables, a pinned author archive was read through a **2 MiB HTTP range**;
no full dataset was downloaded. Thirty tables were selected before original
acquisition. The resulting pilot contains **25 automatic pairs**, with five
preselected tables excluded because three originals exceeded the 2 MiB per-file
bound. No replacement draw concealed those exclusions. Fourteen original PDFs
were obtained with publisher XML, filename, PMCID, version-1 metadata, official
MD5 and newly pinned SHA-256; original page geometry was checked with the existing
adapter. The publisher annotation records contain no historical PDF digest:
this diagnostic revision pins the retrieved originals and exact annotation bytes,
but does not claim historical byte-digest proof or independent label correctness.

The old PMC API returned unavailable responses. Current primary
[PMC distribution documentation](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/) and
the [versioned-object README](https://pmc-oa-opendata.s3.amazonaws.com/README.txt)
provided the replacement metadata/original endpoints. Source versions and
rights receipts are saved locally. DocLayNet remains **0 eligible exact page pairs**:
the bounded [primary repository](https://github.com/DS4SD/DocLayNet) sample search
exposed no matching original PDF plus annotation pair; full archives were excluded.
This is a bounded-search result, not proof that no qualifying sample exists anywhere.
OmniDocBench, FinTabNet.c and Darmm remain deferred.

There are **215 development sources**, **2 sealed-test candidates** and **199
evaluation-eligible development sources** after rights, reserved-QA and candidate
exclusions. All 12 existing reserved-QA family sources remain protected. The two
new families were selected before payload inspection/model inference. Their
originals, exposure, family links and hashes are frozen. Existing component
logic checked exact bytes, normalized hashes and declared template/version/
translation links; no new near-duplicate pair crossed the diagnostic threshold.
Cross-legacy semantic/template/translation completeness and independent family
review remain unproved. Old development sources were never relabelled as blind Test.

No Test labels exist; the development scorer rejects candidate sources. This is
preparation, not an OS-enforced label vault or TEST_READY. The 20–30 independent
Test-document target is not met. The targeted new scan requests returned **403**
or exceeded the per-file bound; aviation reuse terms returned **404**. Existing
original renders distinguish a real English scanned letter from an image-only
flowchart; zero native glyphs alone is not proof of physical scanner origin.
Both remain annotation-quarantined controls. Real RU/KK/mixed scan coverage and
verified complete OCR transcriptions remain missing. CER/WER: NOT_EVALUATED.

## Frozen release, performance and verification

Private root: `evaluation-output/extraction-readiness-continuation-20261023-v2/`.
It binds **383 artifacts and 251 protected paths**, with recursive verification
of the 441-artifact parent. All original 150 RAW, historical Gold and frozen
two-PDF-reference hashes match the parent pins. Code archives permit historical
integrity verification while active scoring still requires the frozen code.

Release fingerprint:
`f480f4fad5b46eaf037b67d7ca77db2e37f93f1aa0172405fd7f493d44489b55`.
Parent fingerprint:
`520f92f507b9f2769abaedbbf48c3fff95f62f298944bf6ec3fb88b2c786d6ce`.
Unchanged PDF-reference fingerprint:
`64fa75b779854918fc50df38bc3e3cb3bf0069c8cb6c76e775bf6c35f8e1c9dc`.

One-worker source-oracle profile, three fresh child processes per mode, same
original and exactly identical seven selected output cells; OS caches not reset:

| Mode | P50 seconds | P95 nearest-rank seconds | Selected cells/sec | Peak tree RSS bytes |
| --- | ---: | ---: | ---: | ---: |
| Materialize 211,023 cells, then select seven | 2.583141 | 2.833176 | 2.7099 | 305,512,448 |
| Materialize seven selected cells | 0.589711 | 0.703825 | 11.8702 | 139,800,576 |

RSS includes Windows launcher children and was sampled every 10 ms; brief peaks
may be missed. Three-trial P95 is the maximum, not a stable tail estimate. This
measures preparation tooling, not a production-parser speedup. The identical
21-oracle no-change run had **21 cache hits**, 7.093060 seconds including parent/
source validation, per-document P50/P95 **0.018417 / 0.069148 seconds**, throughput
**2.9606 documents/sec**, and peak tree RSS **116,957,184 bytes**. The earlier
17-document performance experiment was reused as historical evidence, not rerun.
Interrupted builds, incomplete receipts, corrupted checkpoint bytes and changed
bindings are regression-tested; incomplete work cannot become a cache hit.

VERIFIED — exact commands, from the repository root:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_v2.py tests/unit/test_office_corpus_v2.py tests/unit/test_extraction_fidelity.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_fidelity_relationship_scope.py tests/unit/test_pdf_dev_reference.py tests/unit/test_pdf_native_dev_diagnostic.py tests/unit/test_pdf_cell_recovery.py tests/unit/test_data_quality_gate.py tests/unit/test_dataset_readiness.py tests/unit/test_corpus_v2.py tests/unit/test_dataset_adapters_v2.py tests/unit/test_readiness_release.py tests/unit/test_readiness_evaluator.py tests/unit/test_readiness_continuation.py tests/unit/test_readiness_partitions.py tests/unit/test_readiness_source_metrics.py -q --basetemp evaluation-output/readiness-v2-final-regressions --junitxml evaluation-output/readiness-v2-final-regressions.xml
.venv/Scripts/ruff.exe check tools/extraction_quality/readiness_io.py tools/extraction_quality/readiness_release.py tools/extraction_quality/readiness_evaluator.py tools/extraction_quality/readiness_pdf_metrics.py tools/extraction_quality/readiness_source_checks.py tools/extraction_quality/office_readiness_oracle.py tests/unit/test_readiness_release.py tests/unit/test_readiness_evaluator.py tests/unit/test_readiness_continuation.py tests/unit/test_readiness_partitions.py tests/unit/test_readiness_source_metrics.py
.venv/Scripts/python.exe -X utf8 evaluation-output/extraction-readiness-continuation-20261023-v2/validate_sources.py
.venv/Scripts/python.exe -X utf8 evaluation-output/extraction-readiness-continuation-20261023-v2/profile_targeted.py
.venv/Scripts/python.exe -X utf8 evaluation-output/extraction-readiness-continuation-20261023-v2/profile_cache.py
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_release freeze --output evaluation-output/extraction-readiness-continuation-20261023-v2
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_release verify --output evaluation-output/extraction-readiness-continuation-20261023-v2
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_evaluator office --release evaluation-output/extraction-readiness-continuation-20261023-v2
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_evaluator score --release evaluation-output/extraction-readiness-continuation-20261023-v2 --predictions evaluation-output/readiness-v2-empty-predictions.json --metrics evaluation-output/readiness-v2-empty-metrics.json
```

The first three private preparation scripts above were executed **before freeze**
and write artifacts: do not rerun them into the frozen directory. Their inputs,
outputs and source bindings are retained for inspection. The freeze command was
executed once and now refuses modification. `verify` and `office` are repeatable
read-only checks; scoring requires a fresh metrics destination outside the release.
Future five candidates use the same schema, frozen code, partitions, reference
tiers and denominators. The five-identity test uses synthetic fixtures only.

Results: **338 passed, 2 skipped, 0 failed**; Ruff passed. Both skips require
unavailable Windows symlink privilege. Strict source validation accepted all
19 historical Gold records, resolved all 14,396 DOCX locators and revalidated the
old PDF snapshot. Release freeze/verify and frozen Office cache verification
exited 0. Empty-input software scoring retained **217 NOT_ATTEMPTED sources**,
zero predictions, 21 Office and 16 PDF reference documents; quality stayed
NOT_EVALUATED. It is not an extraction-model result.

Negative tests include wrong SHA/source/format, changed protected originals,
annotation/page/geometry mismatch, duplicate identities/JSON/ZIP, fabricated review,
illegal scope promotion, family/template/translation leakage, false blanks,
invalid spans, formula MISSING/EMPTY/zero distinctions, unsafe OOXML parts,
interruption, corrupt checkpoints and changed active scoring code.

Earlier failures were corrected: five reproduced implementation defects preceded
their fixes; an assembly key mismatch and unused validation import were fixed;
a slow validation attempt was interrupted and changed to parse each XML part once;
an initial launcher-only RSS measurement was discarded and replaced with process-tree
sampling. Superseded measurements are not the reported evidence. Acquisition
403/404/resource exclusions remain explicit data exclusions. DB/service/ACL runtime,
production qualification and model benchmarks were outside this data-only scope.

## REMAINING, COMMIT and GIT STATUS

One local package, `FINAL_OWNER_APPROVAL.md` with machine-readable JSON beside it,
contains the owner decision and four unavoidable promotion inputs: authentic
independent Gold review, publisher-specific rights clearance or continued exclusion,
independent Test-family/label acceptance, and approved QG thresholds. It identifies
the exact local evidence and what each approval would authorize. Acceptance of
this limited development candidate cannot waive those missing inputs.

Continuation implementation commits:

- `cbae71df5416c14556363d81e205bee48b0c033c` — fix source locators and failure evidence.
- `b93f57bafe2fd94cae0f2300eeb97400ce9ce291` — preserve frozen releases and enforce rights.
- `d5f026fb54109360937f34b5393a6727a39d8d95` — source-bound PDF/Office diagnostics.
- `1ee546a9c934ad44b6963214aa4a71f8110f7e86` — validate PDF references before freeze/scoring.

This report is a separate documentation commit; its actual SHA is in the final
chat and Git log. No private release assets are committed. The verified status
before this documentation commit contains the pre-existing unrelated paths below;
the final chat records the post-commit status:

```text
 M tools/kaggle_gpu/extraction_remote.py
?? .gitattributes
?? docs/eda/extraction_r1_20261023.md
?? docs/eda/extraction_r1_20261023_captures.json
?? docs/eda/extraction_r1_20261023_manifest.json
?? docs/eda/independent_engineering_audit_20261020.md
?? tests/unit/test_extraction_r1.py
?? tools/kaggle_gpu/extraction_r1.md
?? tools/kaggle_gpu/extraction_r1.py
?? tools/kaggle_gpu/extraction_r1_eval.py
?? tools/kaggle_gpu/extraction_r1_results.py
?? tools/kaggle_gpu/extraction_r1_text.py
```

Stop at this owner decision. No next experiment is authorized by this report.
