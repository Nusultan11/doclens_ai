# Dataset and Gold readiness inventory — 21 October 2026

STATUS: **PASS for the scoped audit closure.** All 150 RAW identities and frozen
Gold remain unchanged. Cross-collection test-family exclusions are enforced by a
metadata admission guard, and the original ICDAR qualification validator has been
reproduced against its exact historical implementation. External pair eligibility
remains BLOCKED; independent Gold and QG-00/QG-01 remain **NOT_EVALUATED**. Known
extraction-fidelity failures are retained, not waived.

Requested inventory revision: 20261021. Work continued into 22 October 2026
(Asia/Qyzylorda). Baseline: `main`, HEAD
`5580bb62a877c29df305bb41f8e91692a278cfa7`. This is an audit of existing local
evidence, not a fresh legal opinion, human review or parser experiment.

CHANGED: this consolidated report, `tools/extraction_quality/dataset_readiness.py`
and `tests/unit/test_dataset_readiness.py`. The small offline validator adds the
missing join between declared source families and both QA Gold test assignments;
it does not change native-parser eligibility, source manifests or frozen splits.
Ignored closure receipts and an isolated historical replay are under
`evaluation-output/dataset-readiness-closure-20261022/`. No completed EDA, parser
experiment, dataset acquisition or annotation workflow was repeated. Originals,
labels, existing packets, previous reports and production code remain unchanged.

DESIGN: [source map](../../README_SOURCE_MAP.md),
[QG-00 and coverage](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA), and the
[data-quality skill](../../.agents/skills/doclens-data-quality/SKILL.md).
Authoritative corpus/Gold protocols and source-bound rights decisions govern their
own populations. Automated integrity, declared review, independent review,
permitted use, parser outcomes and evaluation quality have separate verdicts.

## Accounted population and registrations

| Collection | Manifested population / local verified | Use established by existing evidence | Outstanding boundary |
| --- | ---: | --- | --- |
| Legacy Corpus v1 | 90 / 90; 30 PDF, 30 DOCX, 30 XLSX | Existing local development/evaluation provenance; 74 declared source-page families | Source-specific annotation rights mostly unassessed; English-dominant, exposed controls |
| Additional Office v2 | 60 / 60; 30 DOCX, 30 XLSX | Existing local development/evaluation provenance; 26 declared families; all dev | Languages unreviewed; no Extraction/Retrieval/Answer Gold |
| Extraction Gold | 19 distinct reviewed-source attestations / 19 valid | Historical local regression comparator; 12 PDF, 3 DOCX, 4 XLSX | Partial assertions only; 131/150 sources lack it; no independently verified whole-document Gold |
| Retrieval Gold | 48 questions / 48 valid; 15 sources | Historical single-reviewer relevance/answerability pilot | 135/150 sources uncovered; nominal 36 dev / 12 test; no test negatives |
| RAG Answer Gold | 20 questions / 20 valid; same 15 sources | Historical single-reviewer answer pilot | Nominal 15 dev / 5 test; no test negatives; no independent semantic certification |
| Five-PDF independent packet | 5 sources / 5 verified; 34 pages | Preserved independent-review templates | 0/5 completed; 110 assertions and 19 region mappings unresolved |
| Rights-admitted independent packet | 2 sources / 2 verified; 2 pages | Blank local-dev review sheets for c1-0033/c1-0040 | No independent reviewer available; no signed draft |
| AI-assisted review package | 2 sources / 2 verified; 536 proposed cells, 1,154 items | Source-bound, user-verifiable development proposals | All 1,154 decisions pending; not human Gold |
| External candidates | 13 candidate families accounted below; 0 admitted original/reference pairs | Metadata qualification or historical reference leads only | Per-item rights, exact source pairing and/or qualification absent |
| Own RU/KK target | 0 available of 50 target documents | None | Authorized real originals, languages and reviewed Gold unavailable |
| Committed synthetic Retrieval fixture | 4 valid examples | Software tests only; EN 2 / RU 1 / KK 1 | No real multilingual document or quality evidence |

There are **150 distinct original byte streams, 31,844,621 bytes**, range
1,732–3,487,671 bytes. No missing source, duplicate original SHA, changed source,
wrong size/suffix/signature, source symlink or inaccessible manifested original was
found. Every one receives an explicit outcome in the source tables below. Missing
external sources and unfilled targets remain visible; targets with different units
(pages, tables, documents) are not added to the 150-document denominator.

The filename inventory examined 130,992 matching source/JSONL/manifest/review paths
under `docs`, `tests`, `local-corpus`, `local-evaluation`, `.eda-output` and
`evaluation-output`, excluding dependency/cache directories. It found 11,197
manifest-named files: 11,128 in test/fixture/snapshot paths, 47 artifact digest lists,
and 22 other manifest registrations listed below. These are file registrations,
not 11,197 datasets. Artifact manifests and profiler/chunk manifests describe
derived outputs; they are not new original corpora.

Outside paths classified as fixtures/snapshots, 237 PDF/DOCX/XLSX files reconcile
to 150 canonical originals, **39 exact original copies**, 46 generated PDF
reproductions and two installed python-docx default templates. The generated PDFs
belong to the existing bfrange, Type0, filled-ruling and geometry public
reproductions; none is admitted as a real corpus source. Test trees contain further
synthetic/runtime copies and are excluded from real-data counts. No additional
unregistered real original collection was identified in this inventory.

Multiple registrations of the Office corpus (current manifest, preparatory and
replayed manifests, review backup) and legacy controls are the same 150 originals.
The acquisition CSV copy is the legacy manifest again. Repeated packets, draft
workspaces, model-input exports, profiler outputs and source copies do not increase
Gold coverage. There is no distinct source registration for an external payload
because no external original/reference payload is admitted. Darmm is registered
in the qualification ledger without a frozen extraction quota; it remains a
separate synthetic OCR lead. Historical catalog leads have no qualified
record-level manifest; this is a visible qualification gap, not an acquired cohort.

### Manifest register

Paths identify metadata only. Raw filenames, download URLs, private labels and
document text are intentionally omitted. All source manifests below parse with
the current strict Corpus v2 loader; their populated identities reference the
verified 150-source union. Historical snapshots are preserved, not promoted.

| Metadata path | Kind / records | Relationship |
| --- | --- | --- |
| `docs/eda/corpus_v1_manifest.csv` | CSV / 90 | authoritative legacy source manifest |
| `docs/eda/extraction_corpus_v2_manifest.json` | Corpus v2 / 60 | Office 60 registration |
| `docs/eda/icdar2013_v2_extension_manifest.json` | Corpus v2 / 0 | empty ICDAR extension |
| `.eda-output/chunking-v1/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/chunking-v1-det-1/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/chunking-v1-det-2/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/chunking-v1-final-a/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/chunking-v1-final-b/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/cli-repeat-a/manifest.csv` | CSV / 5 | derived profiler/chunk/smoke output |
| `.eda-output/cli-repeat-b/manifest.csv` | CSV / 5 | derived profiler/chunk/smoke output |
| `.eda-output/cli-runtime/manifest.csv` | CSV / 5 | derived profiler/chunk/smoke output |
| `.eda-output/corpus_v1/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/extraction-v1/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/extraction-v1-final/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `.eda-output/fidelity-baseline-reproduction/manifest.csv` | CSV / 90 | derived profiler/chunk/smoke output |
| `evaluation-output/extraction-v2-20261021/control-manifest-final.json` | Corpus v2 / 90 | legacy 90 control registration |
| `evaluation-output/extraction-v2-20261021/control-manifest.json` | Corpus v2 / 90 | legacy 90 control registration |
| `evaluation-output/extraction-v2-20261021/office-manifest-replayed.json` | Corpus v2 / 60 | Office 60 registration |
| `evaluation-output/extraction-v2-20261021/office-manifest.json` | Corpus v2 / 60 | Office 60 registration |
| `evaluation-output/extraction-v2-review-20261021/office-manifest-replayed.json` | Corpus v2 / 60 | Office 60 registration |
| `evaluation-output/pdfplumber-table-v1-20261019/wheel-manifest.json` | runtime package digests | dependency artifacts, not document data |
| `evaluation-output/qg00-annotation-rights-20261021/acquisition-manifest.csv` | CSV / 90 | same legacy manifest, rights acquisition copy |

## Original integrity, structure, language and limits

Fresh read-only checks used `fidelity_eval._read_sources` / `verify_corpus`,
`corpus_v2.load` / `audit` / `asset_path`, PDF page metadata and bounded OOXML
structural inventory. No text-extraction run, OCR, model inference, formula
execution, external-link refresh or Office save occurred. Source identity checks
reconciled all 60 Office acquisition events with frozen attachment metadata,
MIME, source URLs, URL-derived IDs, family IDs and hashed OGL capture pairs. All
90 legacy rows retain complete source/license references and expected hosts/MIME.
No live source availability or fresh online license reassessment is claimed.

| Cohort / format | Sources | Language metadata | Original structural observations |
| --- | ---: | --- | --- |
| Legacy PDF | 30 | EN 29, CY 1 | 143 physical pages total; all readable, unencrypted; table completeness not inferred |
| Legacy DOCX | 30 | EN 29, CY 1 | 2,318 body paragraphs; 292 body tables in 17 sources; 8 nested tables in 4; ancillary text in 14 |
| Legacy XLSX | 30 | EN 30 | 158,474 stored XML cells; 6,561 formula elements in 8 sources; 735 missing formula caches in 3 |
| Office DOCX | 30 | unknown 30 | 2,442 body paragraphs; 73 body tables in 23 sources; no nested table observed; ancillary text in 21 |
| Office XLSX | 30 | unknown 30 | 941,479 stored XML cells; 41,107 formula elements in 9 sources; 25,112 missing formula caches in 4 |

EN labels for legacy documents mostly derive from publication-page locale; two
CY labels are publisher declarations. These are not fresh human language reviews.
There are **0 verified real RU/KK originals**. The 60 Office language fields stay
unknown. Synthetic RU/KK questions do not fill that gap. XML table/formula counts
are observations of packages, not reviewed topology, literal fidelity, display
values, formula correctness or source semantics. Missing caches are retained as
observations, not automatically classified as parser defects.

All 150 sources satisfy the 50 MiB file ceiling. All 120 Office containers satisfy
20,000 entries, 100 MiB per entry, 500 MiB total uncompressed and the 200:1
compression-ratio ceiling; required package members and Content Types are present,
with no encrypted ZIP entry observed. All PDF page counts satisfy the 2,000-page
ceiling. The 60-source acquisition also satisfies its existing 2 MiB/source and
30 MiB aggregate budget. No limit was raised. Structural accessibility does not
certify active content, security suitability or complete extraction.

### Existing parser evidence, reused without new experiments

The source- and code-pinned stabilization captures are the latest applicable
measurements: `evaluation-output/stabilization-complete-20261021/pipeline-{1,2}`
and `office-final/run-{1,2}`. Captured source identities and all listed pipeline
and Office code pins match current files. Pipeline diagnostic fingerprints agree;
the two fresh integrity/Gold audits also agree. Parser states below are historical
executed observations at runtime snapshot `c05ea8b`, still code-matched at HEAD
`5580bb6`; this audit did not execute the parsers again.

| Population | Attempted | Success | Needs review | Failed |
| --- | ---: | ---: | ---: | ---: |
| Legacy PDF | 30 | 27 | 3 | 0 |
| Legacy DOCX | 30 | 10 | 20 | 0 |
| Legacy XLSX | 30 | 15 | 15 | 0 |
| Office DOCX | 30 | 6 | 24 | 0 |
| Office XLSX | 30 | 11 | 15 | 4 |
| Complete original population | **150** | **69** | **77** | **4** |

`success` is not factual fidelity or production/index admission. `needs_review`
is an intentional hold with existing warnings, retained in every denominator.
All 150 remain useful as byte-stable local regression inputs under their recorded
evaluation provenance, including failure controls; the c1-0045 source restriction
below is not cleared by that historical admission. Independent evaluation requires
additional rights/review/split evidence. PDF evidence is not automatically trusted
or indexable. Safe failure cases are not candidates for partial publication.

The four Office failures are all retained:

| Source | Diagnosis from existing verified evidence | Readiness consequence |
| --- | --- | --- |
| e2-office-081ca479f8d7eebf | unsupported_format: three worksheets plus a dialogsheet | Unsupported content; not corrupt; no partial workbook |
| e2-office-545836d5b9807326 | unsupported_format: same supported/unsupported part composition | Unsupported content; not a success target |
| e2-office-51bd4fd25d37dd92 | limit_exceeded at 5,000,008 characters; 236,261 stored cells in the limit-triggering sheet | Protective rejection at unchanged 5,000,000-character ceiling |
| e2-office-969193c6e25c5c79 | limit_exceeded at 5,000,025 characters; 208,461 stored cells in the limit-triggering sheet | Protective rejection; do not bypass to raise counts |

## Rights and sensitivity: separate permissions

`L` = existing documented local-evaluation admission; `A` = source-specific scoped
new-annotation admission; `B` = BLOCKED; `N` = NOT_EVALUATED/not established.
Absence of an affirmative grant is not a categorical denial. A dataset-card license,
public URL, corpus access or structural validator cannot fill missing source rights.

| Source scope | Local evaluation | New annotations/adaptation | External-label reuse | Redistribution | External processing |
| --- | --- | --- | --- | --- | --- |
| c1-0033 | L | A: institutional role/department table, local dev only | N; explicit no inference of unrelated annotation authorization | N, outside admitted use scope | N; no transfer authority added |
| c1-0040 | L | A: government blank budget template, local dev only | N; explicit no inference | N | N |
| c1-0045 | L historically recorded; restriction unresolved | **B: UKHO-specific reproduction/adaptation permission unresolved** | N | N | N |
| c1-0048, c1-0049 | L | **N: prior exclusion was budget, not a rights decision** | N | N | N |
| Other 85 legacy sources | L under frozen acquisition policy | N per source | N | N | N |
| Office 60 | L under bound acquisition/OGL policy | N per source | N | N | N |
| External candidates | B or N as detailed below | N/B until exact sources qualified | N/B separately from original rights | N | N |

The two annotation admissions reuse eligibility revision
`qg00-annotation-eligibility-20261021-v2`, fingerprint
`7aec430b7b41cc1e172ffe866d30f8520c8a02df0a281b61e752bb84e2e2274b`.
All referenced captures, exact attachment bytes, pages, declared families and OGL
offers pass the existing eligibility validator. The admitted use preserves OGL
attribution: "Contains public sector information licensed under the Open Government
Licence v3.0." Personal information/identifying people is outside c1-0033 scope;
future completed applications are outside c1-0040 scope. No third-party exception
was identified in the admitted content; that documentary finding is not a human
Gold attestation or an unlimited legal clearance.

The c1-0045 restriction remains intact. Generic OGL footer evidence does not
resolve the specific reproduction/adaptation policy. No new processing of it is
authorized by this report. c1-0048/c1-0049 remain NOT_EVALUATED for annotation
rights, as explicitly confirmed by the user. Of 150 originals, **2 have this
affirmative new-local-annotation admission, 1 is blocked and 147 are unassessed**.
Existing single-reviewer Gold is preserved with its historical provenance; its
presence does not establish a new annotation/redistribution/transfer grant.

All 150 manifest entries declare public sensitivity, but source-specific inspection
evidence is narrower. This audit did not perform a full PII, third-party IP or
sensitivity review of the remaining content. Previous remote model experiments
retain their historical task-specific authorization; that is not blanket transfer
permission for any source, Gold collection or future experiment.

## Gold validation and evidence classes

Strict current loaders validate all six reviewed local snapshots, reject all five
draft snapshots as expected, and validate the committed synthetic fixture. Draft
rejection is a successful safety check, not corrupted approved Gold. Multiple
Extraction snapshots overlap; the combined unique population is 19, not 41.

| Private metadata filename | Records | Current loader outcome | Evidence class / relationship |
| --- | ---: | --- | --- |
| `extraction_fidelity_controls_v1_draft.jsonl` | 3 | EXPECTED_REJECT_DRAFT | unreviewed draft; not usable as reviewed Gold |
| `extraction_fidelity_controls_v1_reviewed.jsonl` | 3 | PASS | historical user-supplied single-reviewer attestation |
| `extraction_fidelity_v1_controls_reviewed.jsonl` | 11 | PASS | historical user-supplied single-reviewer attestation |
| `extraction_fidelity_v1_draft.jsonl` | 8 | EXPECTED_REJECT_DRAFT | unreviewed draft; not usable as reviewed Gold |
| `extraction_fidelity_v1_expanded_approved.jsonl` | 19 | PASS | historical user-supplied single-reviewer attestation |
| `extraction_fidelity_v1_reviewed.jsonl` | 8 | PASS | historical user-supplied single-reviewer attestation |
| `pdf_gold_expansion_v1_draft.jsonl` | 8 | EXPECTED_REJECT_DRAFT | unreviewed draft; not usable as reviewed Gold |
| `rag_gold_v1_approved.jsonl` | 20 | PASS | historical user-supplied single-reviewer attestation |
| `rag_gold_v1_candidates.jsonl` | 20 | EXPECTED_REJECT_DRAFT | unreviewed draft; not usable as reviewed Gold |
| `retrieval_gold_v1.jsonl` | 48 | PASS | historical user-supplied single-reviewer attestation |
| `retrieval_gold_v1_candidates.jsonl` | 48 | EXPECTED_REJECT_DRAFT | unreviewed draft; not usable as reviewed Gold |

The 8-record pilot and 3-record controls are unchanged subsets of the combined
11; all 11 are unchanged in expanded 19. RAG candidate-to-approved changes are
exactly reviewer_status/count on each of 20 records. Retrieval changes are review
metadata on 48 records and the one historically approved question correction;
source/evidence/answerability/split data remain unchanged. No labels were repaired
to match current implementation.

Historical review evidence is documented in
[Extraction pilot](extraction_fidelity_pilot_v1.md),
[PDF expansion](pdf_gold_expansion_v1.md),
[Retrieval pilot](../evaluation/retrieval_gold_v1_pilot_report.md), and
[RAG review packet](../evaluation/rag_gold_v1_review_packet.md).
These record user approvals in October 2026, one reviewer and no independent
second review. This audit does not authenticate that person's actions, create a
reviewer identity/date, or reinterpret prepared candidates as blind human labels.
Original-document review is declared, not independently verified here. AI/machine
assistance in current workspaces/proposal packages is explicitly a separate class.

| Collection | Coverage / assertion denominator | Fresh metadata/locator check | Limits |
| --- | --- | --- | --- |
| Expanded Extraction | 19/150 sources; 126 anchors, 58 order pairs, 52 cell/span checks, 33 relationships, 13 value/formula/cache checks | 114/139 anchor/value locators structurally supported; 25 NOT_EVALUATED; 0 invalid. Relationships 13 supported / 20 NOT_EVALUATED / 0 invalid | Partial labels; 5 PDF table sources; legacy ancillary mapping remains unverified; displayed values unlabelled |
| Retrieval | 15/150 sources, 48 questions, 45 answerable / 3 negative; 80 evidence anchors | 80/80 supported locators and bounded normalized offsets; strict source references valid | No semantic relevance or negative-scope re-review; EN only |
| RAG Answer | Same 15 sources; 20 questions, 17 positive / 3 negative; 28 anchors | 28/28 quotes exactly match one captured normalized source-unit slice, with valid source identity/bounds | Exact quote matching does not prove answer correctness or implication; EN only |
| Synthetic Retrieval | 4 examples; zero reviewers; explicit fixture revision | Strict schema PASS | Software correctness only; not real RU/KK evidence |

Thirty distinct originals have any of these three historical Gold types;
**120/150 have none**. No Office v2 source has any of them. Extraction has no split
field; a split check is NOT_APPLICABLE, not an invented test assignment. Retrieval
and RAG declared family/source checks pass internally and agree with each other;
their broader exposure issue is described separately below.

The fresh audit does not rescore extraction quality. Existing final fidelity
diagnostics remain 115/126 anchors, 43/58 order pairs, 28/52 cells, 13/33
relationships and 103/139 provenance checks; stored values/formulas/caches each
13/13. Those are partial historical label scores, not full corpus quality. The
25 structurally unevaluated locators and 20 relationships remain in denominators;
unsupported structure cannot be turned into an invalid human label merely to
improve apparent readiness. Whole-table geometry, complete cell inventory, exact
all-content text, displayed spreadsheet values and semantic header/value/unit/
period relationships remain unverified dimensions.

### Source and Gold fingerprints

| Identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Legacy manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Office manifest bytes | `8e40445669b209af568d81c20c41c34257cd41f3cbc19ced2a5eebc77ccc8b54` |
| Expanded Extraction bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Expanded Extraction normalized | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Retrieval normalized | `d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94` |
| RAG Answer normalized | `66e84c335da8c6fd51468bed623e24ed7dc276e8dfc051f2a0261274105f00ee` |
| Fresh repeated inventory audit | `6bea9a8f995bd5b2eaf62dea34cad9231c8a8db09585826fb55aca87dec3db4a` |

## Families, duplicate isolation and exposure

All 150 original SHAs are distinct. The union has **75 declared source-page
families**: legacy 74, Office 26, with 25 shared across corpora. Publication-family
membership is not a near-duplicate judgment. Human family completeness is
NOT_EVALUATED. No new translation/version/semantic-duplicate labels were invented.
The recorded latest Office-only native-text screen has zero near-duplicate pairs;
the earlier cross-cohort screen found zero among 131 nonempty native outputs,
leaving 19 empty/failed outputs outside that text screen. That older availability
denominator predates stabilization and is not updated by inference. No new
near-duplicate experiment was run. Scans, translations and broad template
relationships remain unresolved; zero observed lexical pairs is not zero leakage.

Within each historical QA Gold, no declared family or identical source crosses
dev/test. However, comparing those QA assignments with the complete source
registrations exposes an important boundary:

- Four test originals shared by Retrieval and RAG: **c1-0009, c1-0038, c1-0062,
  c1-0086**; four declared source-page families.
- Additional legacy members of those families: **c1-0025, c1-0028, c1-0078**.
- Office dev siblings in those families: **e2-office-3377338b6feaa700,
  e2-office-42093d9dd7c328b7, e2-office-5fe8e22215112bcf,
  e2-office-86e500b1938eca3f, e2-office-ef9bb253eef287c8**.

All legacy controls and Office samples remain dev/exposed in their original
source manifests. The exact Office-to-test bindings are verified against the
strictly loaded Retrieval and RAG Answer Gold and the SHA/size/format/source-page
bindings of the legacy reference manifest:

| Excluded Office source | Format | Declared source-page family | Test original in both QA Gold |
| --- | --- | --- | --- |
| e2-office-3377338b6feaa700 | docx | `f-c90c5cf2ef3cd307c831ed24` | c1-0009 |
| e2-office-42093d9dd7c328b7 | xlsx | `f-c90c5cf2ef3cd307c831ed24` | c1-0009 |
| e2-office-5fe8e22215112bcf | xlsx | `f-5bfd3ebb0ecf7a6efc413b7c` | c1-0086 |
| e2-office-86e500b1938eca3f | docx | `f-c90c5cf2ef3cd307c831ed24` | c1-0009 |
| e2-office-ef9bb253eef287c8 | xlsx | `f-c90c5cf2ef3cd307c831ed24` | c1-0009 |

The root cause was a scope gap: the Corpus v2 native/source audit checks families
inside its supplied source population, which is all dev, while the QA Gold test
assignments live in separate collections. Native eligibility therefore admitted
all five for regression measurement; that boolean never established independence
against QA test families. The previous inventory identified the conflict but had
no executable selection guard.

`tools.extraction_quality.dataset_readiness` now loads both Gold snapshots with
their existing strict loaders, binds reference identities/families to the legacy
CSV, and reserves all connected components containing any QA test source. It uses
the existing family-component logic, including declared related families, exact
source hashes and normalized-text hashes. A missing/unbound test source or invalid
input fails closed. The whole requested selection is BLOCKED if it contains any
excluded or unknown record. No source identity, disposition or frozen split is
rewritten. The old parser/native audit still measures all sources; this separate
guard owns admission for development against these QA test families.

### Exact development subset after exclusions

| Scope | Complete population retained | Excluded from dev against the QA test families | Isolation-eligible development inputs |
| --- | ---: | ---: | ---: |
| Office DOCX | 30 | 2 | 28 |
| Office XLSX | 30 | 3 | 27 |
| Office total | **60** | **5** | **55** |
| Legacy reference controls | **90** | **7** | **83** |
| Complete inventory | **150** | **12** | **138** |

The exact usable Office subset for this isolation scope is the frozen 60-record
manifest **minus precisely the five Office IDs above**. The exact 83-source legacy
subset is all 90 sources minus **c1-0009, c1-0025, c1-0028, c1-0038, c1-0062,
c1-0078, c1-0086**. This also excludes the four test originals themselves and their
three additional legacy family members. The full eligible/excluded ID lists are
deterministically emitted by the validator and marked on every source row below.

The 55 Office inputs retain 17 success / 34 needs_review / 4 failed outcomes from
the existing capture. The full 138 isolation-eligible inputs retain 65 success /
69 needs_review / 4 failed. Failures and review holds are useful regression cases,
not newly accepted indexable content. Complete-population counts stay 150 and
69 success / 77 needs_review / 4 failed. No quality denominator is silently shrunk.

**Isolation-eligible is not independent Gold or blanket experimental permission.**
The 138 sources still have their previously recorded rights, exposure, language
and review limitations; the c1-0045 annotation restriction remains BLOCKED.
All are exposed controls. No fresh sealed holdout or new annotation/transfer
grant is created. The guard prevents use of the five overlapping Office records
as independent dev/evaluation samples against the reserved test families. They
remain available only as explicitly exposed, overlapping regression controls in
the full population. Historical QA splits/results remain unchanged.

## Review packets and workspaces

The five-source packet copies each have 25 files / 23 artifact-manifest entries,
byte-identical and hash-valid. The two-source admitted packet copies each have
13 files / 11 entries, also byte-identical and hash-valid. All source copies match
the original manifests. Packet existence is not review completion.

| Source | Pages | Existing assertions | Region mappings | Annotation rights | Independent completion |
| --- | ---: | ---: | ---: | --- | --- |
| c1-0033 | 1 | 28 | 2 | ADMIT scoped local dev | 0; unsigned |
| c1-0040 | 1 | 19 | 2 | ADMIT scoped local dev | 0; unsigned |
| c1-0045 | 7 | 14 | 2 | BLOCKED | 0; unsigned |
| c1-0048 | 17 | 21 | 8 | NOT_EVALUATED; outside prior budget | 0; unsigned |
| c1-0049 | 8 | 28 | 5 | NOT_EVALUATED; outside prior budget | 0; unsigned |
| Complete selected population | **34** | **110** | **19** | 2 admitted / 1 blocked / 2 unassessed | **0/5** |

All 110 legacy assertion decisions and all 19 region mappings are explicitly
UNRESOLVED in the preserved packet. They comprise 46 anchors, 24 cell/span checks,
20 order checks and 20 relationships (13 same-row, 7 same-column). No disagreements
have been adjudicated; absence of decisions is not agreement. The original
`REVIEW.md` source-first blinding rule remains applicable: independent drafts must
be finalized before legacy assertions/predictions are disclosed to that reviewer.
The user confirmed that no real independent reviewer is currently available.

Ten workbench states referencing real sources were found outside generic fixture
paths: the independent and machine c1-0040
workspaces, ML29 intake-only and human-review workspaces, ML30b assisted workspace,
four ML30b proposal-check copies, and the current two-source admitted workspace.
All have zero seals and zero populated reviewer attestations. Some older states
contain one inspection marker/table; the c1-0040 machine state contains assistance
metadata and five proposed tables. These are unsigned saved states, not evidence
of a completed human source review. The fresh admitted workspace is blank and
legacy-locked by its existing workflow. Workspace labels such as "human-review"
do not confer an evidence class. Temporary copies are accounted, not independent
reviewers or additional documents.

The accepted AI-assisted package and its recorded reproductions remain separate
from independent drafts. Existing `validate_items` accepts all source/geometry/
reference fingerprints; all packet artifact hashes match. Its six physical
regions contain 536 proposed cells (291 empty, 13 spanning, 60 uncertain), 62 text
anchors and other role/order/unit/relationship proposals: **1,154 CSV rows, all
pending**. Machine-supported does not mean human-verified. All reviewer/approval
fields remain unset. Geometry-plan/user-requested partition history is retained
as assisted provenance, not an independent annotation. No package was rebuilt.

DOCX ancillary locator review packets also remain draft diagnostic evidence for
c1-0006/c1-0007/c1-0008. Their source-bound XML observations do not resolve the
legacy `part_index` convention by themselves; no human-selected mapping or new
Gold revision is claimed. Existing packet and source-map evidence, rather than
matching text alone, must govern a future authorized locator review.
Four preserved run directories each have 11 hash-valid artifacts and three
source-matched draft records (12 draft copies, three unique sources); all remain
`review_status=draft`.

## External candidate register and unresolved evidence

The register combines [engineering catalog D1–D7](../../DocLens_AI_Engineering_Sources.md#CATALOG),
[five pinned qualifications](extraction_v2_dataset_qualification.json),
[ML-31 feasibility](ml31_external_table_gold_feasibility.md), and
[ICDAR qualification](icdar2013_qualification.json).
Names below identify public datasets; no private source title is included.
Facts are the recorded qualification snapshots, not newly checked upstream terms.
Repeated names across catalog, feasibility and targets are one candidate family.

| Candidate family / registration | Existing evidence class and local payload | Missing source/rights/annotation evidence; verdict |
| --- | --- | --- |
| DocLayNet — D2, v2 target 100 pages | Pinned card/tree; publisher expert layout annotations and PDF-generated auxiliary text; 0 pairs | CDLA-Permissive-1.0 declaration does not resolve parent-document rights; exact PDF/PNG/COCO/auxiliary pairs absent. Local admission BLOCKED; annotation reuse/redistribution/transfer unestablished |
| PubTables-1M — v2 target 100 table pages; ML-31 | Pinned card/tree; automatic XML/PDF alignment/canonicalization; 0 pairs | Item-specific PMC original rights and exact original/annotation matching unresolved; CDLA-Permissive-2.0 declaration is not independent human Gold. BLOCKED |
| FinTabNet / FinTabNet.c — v2 target 50 tables; ML-31 | `.c` pinned card/tree; automatic corrections/filtering; 0 pairs | Company source-report bytes/rights, original grant scope, pairing and external annotation reuse unresolved. `.c` declaration does not clear originals. BLOCKED |
| OmniDocBench — v2 target 50 pages | Pinned card/tree; mixed manual/intelligent annotations and expert/model checks; 0 pairs | Research/noncommercial scope unresolved; pinned tree has images, no verified matched original PDFs; no per-item local independent attestation. BLOCKED |
| Darmm OCR Kazakh v2 — qualification ledger | Pinned card/tree; synthetic Wikipedia rendering; 0 payload | Original text/font obligations and source pairing unresolved despite Apache card declaration; no source PDFs or real-document Gold. BLOCKED for current admission; not own RU/KK quota |
| ICDAR-2013 family — organizer original, manual-corrected release and automatically aligned `.c`; extension 3 slots | Metadata/rights/XSD/corrected/aligned cards captured; 0 pairs/0 payload; no local human review | Per-item original and upstream annotation rights, individual exact original/annotation endpoints and coordinate transforms unresolved; frozen schema lacks ICDAR XML kind. 3/3 slots BLOCKED, quality NOT_EVALUATED; validator drift below |
| SciTSR — ML-31 | Literature/repository feasibility only; automatically generated LaTeX/PDF structure; no admitted pair | Software MIT license does not establish corpus/arXiv-item annotation/redistribution scope; per-item original pairing and human review absent. NOT_EVALUATED |
| DocVQA — D1 | Historical visual-QA lead; no qualified local records | Release/revision, underlying document permissions, source pairing, annotation license/sensitivity and suitability not qualified. NOT_EVALUATED |
| TAT-QA — D3 | Historical table/text-QA lead; no qualified local records | Underlying report rights, exact source/label pairs and complete usage scopes not established. NOT_EVALUATED |
| SQuAD 2.0 — D4 | Historical answerability-smoke lead; no qualified local records | Revision/rights/annotation qualification absent; text QA is not document provenance/Gold. NOT_EVALUATED |
| KazQAD — D5 | Historical Kazakh-QA lead; no qualified local records | Access/revision/rights/annotation suitability and document-source pairs unresolved. NOT_EVALUATED |
| MIRACL — D6 | Historical retrieval lead; no qualified local records | Revision, license/source/annotation scope and applicability not qualified; no proof of PDF/XLSX/KK coverage. NOT_EVALUATED |
| Zerde QA 50K — D7 | Historical synthetic-QA lead; no qualified local records | Revision/rights/source lineage/human verification unqualified; not reviewed Gold or automatic SFT approval. NOT_EVALUATED |

All five v2 card/metadata byte hashes and recorded metadata sizes are bound to
their qualification records. Their payload acquisition remains **0 attempts,
0 bytes, 0 admitted samples**, not five attempted documents. Four unavailable
v2 PDF/table quotas remain separate (100/100/50/50 in their own units). Own RU/KK
50 is a separate absent internal target. ICDAR has 3 requested coverage slots,
0 identified source-bound pair IDs and 0 admitted pairs; an unknown candidate
population cannot be invented from those slots.

ICDAR's 20 recorded HTTP events (17 metadata GET, 3 archive HEAD) reconcile to
the preserved ledger and captured body hashes. Its archives were not downloaded;
the source-pair rights fields remain null. The organizer archive HEAD reachability
is recorded as successful in that snapshot; an older fetch failure is not a
current 403 claim. No blocked acquisition was retried during this audit. Existing
metadata is sufficient to explain the blocker; it cannot establish source geometry,
literal fidelity or semantic relations without the actual pairs and permissions.

### Historical reproducibility resolved without repinning

The current-worktree invocation of the old ICDAR validator correctly rejects a
different implementation. Its frozen expected `corpus_v2.py` SHA remains
`4b46bacb9a99999f3c2d931dd6b0b5cff8c633b490225a4ca1e619230dcd73f7`;
the later corrected implementation is
`e68762667ad9d3e59763294f6f2e5983a053f1a1a8e584603e209854d1551699`.
Git verifies the expected code at `b816531`, retained in the qualification commit
`670b59d2160c6a6c70ca192a19f15b917d9bdbfd`. The newer integrity-guard correction
`3d64cfb` explains the mismatch. Six entries in the historical 130-file protection
list are code/test/tool changes; the other 124 still match. This was historical
snapshot drift, not a changed source or a broken hash validator.

The original implementation **is reproducible**. The closure restored an isolated,
ignored archive of `670b59d`, restored the six historical code/test/tool entries
from Git to their exact recorded byte hashes, and copied only unchanged pinned
inputs/captures into that snapshot. All 130 protected entries and the three frozen
base pins match there. The original `validate_qualification.py` was copied
byte-for-byte without edits; its imported `corpus_v2` was verified to originate
from the historical snapshot. No monkeypatch, ignored assertion, edited pin or
modified qualification record was used.

Running that unchanged validator in the isolated snapshot returned **exit 0**.
Its complete result equals the preserved `validation-1.json`, including fingerprint
`2e296ab3e11e128702898c1372f844c0c2f733396908d014f3687e8afc58358c`.
It verifies the recorded 20 metadata events / 303,546 body bytes / 130 protected
files and zero pair acquisition. The live worktree, original evidence and private
sources remain unchanged. This is successful replay of a **non-admitting historical
qualification**, not qualification against the newer implementation.

| Verification dimension | Final outcome |
| --- | --- |
| Historical pinned implementation + original validator | PASS; exact preserved result reproduced |
| Historical validator applied to newer code | Expected pin rejection, exit 1; not historical replay failure |
| Qualification fingerprint | Unchanged: `373dd60c718399f71ad6ed821ab185a605524cec1b791acdb4bd5f40e98c1610` |
| ICDAR source/annotation pairs admitted | 0; pair qualification **BLOCKED** |
| Gold readiness / QG-00 | **NOT_EVALUATED** |

No archive payload download, source-pair inference or parser experiment was needed.
The pinned SHA and all original qualification evidence remain historical authority
for that snapshot. A future source-pair admission still requires its own permission,
pairing and coordinate evidence; replay does not supply those missing facts.

## Per-source readiness ledger

All 150 rows have **Integrity PASS** from fresh SHA/size/format/container/access
checks. Full authoritative digests remain in the manifests and ignored `run-1.json`;
source identity is not inferred from names. Family IDs are declared source-page
groups, with human family review unknown. Table/formula observations are not labels.

Column key: `p` paragraphs (DOCX) or physical pages (PDF), `t` body tables, `n`
nested tables, `a` ancillary text present, `c` stored XML cells, `f` formula
elements, `mc` missing formula caches. PDF table inventory is NE. `E/R/A` =
Extraction reviewed record present (0/1) / Retrieval question count / Answer
question count. E=1 is partial assertions, never completeness. Rights order is
local evaluation / new annotations / external annotations / redistribution /
external processing; `L*` preserves c1-0045's historical admission plus restriction.
`T` marks membership in one of the four QA test-source families. The added
`Dev isolation` column enforces the explicit 12-source exclusion above. Every row is
development/exposed in the source registry; no row is a fresh independent test.

| Opaque source | Format / language | Bytes | Integrity | Structure | Parser | E/R/A | Rights | Dev isolation | Declared family / issue |
| --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| c1-0001 | docx / en | 8058 | PASS | p=13;t=0;n=0;a=0 | success | 0/4/3 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / E missing |
| c1-0002 | docx / en | 13284 | PASS | p=21;t=10;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-1eb5ba415012e4716949bd17` / review hold, E missing |
| c1-0003 | docx / en | 20535 | PASS | p=48;t=0;n=0;a=0 | success | 0/4/1 | L/N/N/N/N | eligible | `f-fce07b8d72c52b100618cc04` / E missing |
| c1-0004 | docx / en | 21319 | PASS | p=38;t=4;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-752bfac464bb11ff1b7bf945` / review hold, E missing |
| c1-0005 | docx / en | 55766 | PASS | p=431;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-2050a2281354ed16f308bdba` / review hold, E missing |
| c1-0006 | docx / en | 77583 | PASS | p=388;t=126;n=0;a=1 | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-b43749e2b2fe64bab4359460` / review hold |
| c1-0007 | docx / en | 308445 | PASS | p=382;t=10;n=4;a=1 | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-86bdd44ccee832630f8045d3` / review hold |
| c1-0008 | docx / en | 16713 | PASS | p=19;t=3;n=0;a=0 | success | 1/3/1 | L/N/N/N/N | eligible | `f-0209294c95551f8fe8e17d3f` |
| c1-0009 | docx / en | 17570 | PASS | p=4;t=1;n=0;a=0 | needs_review | 0/3/1 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, review hold, E missing |
| c1-0010 | docx / en | 18716 | PASS | p=36;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-b20e7fd26dd5a5868b1ac0b7` / E missing |
| c1-0011 | docx / cy | 22841 | PASS | p=15;t=10;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-747914e405d404dfc72f4dc0` / review hold, E missing |
| c1-0012 | docx / en | 26428 | PASS | p=41;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-fe06b6e1c3b69e9155489b9a` / review hold, E missing |
| c1-0013 | docx / en | 32246 | PASS | p=18;t=3;n=0;a=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-d3058af293f4192cb9ec6026` / review hold, E missing |
| c1-0014 | docx / en | 32945 | PASS | p=18;t=1;n=0;a=0 | success | 0/3/1 | L/N/N/N/N | eligible | `f-40f6b76bf973908880846006` / E missing |
| c1-0015 | docx / en | 41312 | PASS | p=29;t=4;n=1;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-9ffa9209f565a182cd9d9fde` / review hold, E missing |
| c1-0016 | docx / en | 41570 | PASS | p=45;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-6a4a9a2c14438e5d54b34127` / review hold, E missing |
| c1-0017 | docx / en | 65000 | PASS | p=3;t=1;n=0;a=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-baa2ba7d76be9f2547f111d8` / review hold, E missing |
| c1-0018 | docx / en | 81163 | PASS | p=135;t=63;n=0;a=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-77adba97419c827e9f5d3495` / review hold, E missing |
| c1-0019 | docx / en | 218689 | PASS | p=12;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-22bc6982834554021c1b16a1` / review hold, E missing |
| c1-0020 | docx / en | 17247 | PASS | p=33;t=19;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-8b4c1fb3c8555c034010efbf` / review hold, E missing |
| c1-0021 | docx / en | 31738 | PASS | p=62;t=23;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-50915f31b6e0769bfd9d853c` / review hold, E missing |
| c1-0022 | docx / en | 606051 | PASS | p=362;t=12;n=2;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-b99eb463bad5ffc6433cbd73` / review hold, E missing |
| c1-0023 | docx / en | 10610 | PASS | p=17;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| c1-0024 | docx / en | 15459 | PASS | p=21;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / E missing |
| c1-0025 | docx / en | 17756 | PASS | p=4;t=1;n=0;a=0 | needs_review | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, review hold, E missing |
| c1-0026 | docx / en | 18806 | PASS | p=3;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-ca0e1e1d0193fb77d75fd707` / E missing |
| c1-0027 | docx / en | 19710 | PASS | p=1;t=1;n=1;a=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-ca0e1e1d0193fb77d75fd707` / review hold, E missing |
| c1-0028 | docx / en | 20159 | PASS | p=35;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, E missing |
| c1-0029 | docx / en | 20467 | PASS | p=58;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-ca0e1e1d0193fb77d75fd707` / E missing |
| c1-0030 | docx / en | 21910 | PASS | p=26;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / E missing |
| c1-0031 | pdf / en | 1732 | PASS | p=1; tables=NE | success | 1/0/0 | L/N/N/N/N | eligible | `f-a5cc36a66167fdfb833f9778` |
| c1-0032 | pdf / en | 20617 | PASS | p=1; tables=NE | success | 1/3/1 | L/N/N/N/N | eligible | `f-7b2873808bd7865529b49476` |
| c1-0033 | pdf / en | 29702 | PASS | p=1; tables=NE | success | 1/0/0 | L/A/N/N/N | eligible | `f-de5a37738e823a8f44ec7b0f` |
| c1-0034 | pdf / en | 38249 | PASS | p=2; tables=NE | success | 0/3/2 | L/N/N/N/N | eligible | `f-81fa9b61a35cd08b54603d74` / E missing |
| c1-0035 | pdf / en | 38361 | PASS | p=1; tables=NE | success | 1/0/0 | L/N/N/N/N | eligible | `f-0ceeb6b558d37493a160996e` |
| c1-0036 | pdf / en | 39641 | PASS | p=4; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-1d5992b22bed449603220db2` / E missing |
| c1-0037 | pdf / en | 51528 | PASS | p=1; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-cbe617f453c7e79dda1aae07` / E missing |
| c1-0038 | pdf / en | 58972 | PASS | p=1; tables=NE | success | 0/3/1 | L/N/N/N/N | EXCLUDED: test family | `f-0c24a0010b06d68fd42935dc` / T, E missing |
| c1-0039 | pdf / en | 64380 | PASS | p=2; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-b43749e2b2fe64bab4359460` / E missing |
| c1-0040 | pdf / en | 64968 | PASS | p=1; tables=NE | success | 1/0/0 | L/A/N/N/N | eligible | `f-3ed94a499073bb2cc8254c6e` |
| c1-0041 | pdf / en | 77333 | PASS | p=4; tables=NE | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-830f2203363b54893438a2b6` / review hold |
| c1-0042 | pdf / en | 89882 | PASS | p=2; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-fb98f301a2d72d7e3dd3bfdc` / E missing |
| c1-0043 | pdf / cy | 91484 | PASS | p=4; tables=NE | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-7245126a39555fbc4d4d0bab` / review hold |
| c1-0044 | pdf / en | 100551 | PASS | p=1; tables=NE | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-9ba97fd12d7b243cfa892534` / review hold |
| c1-0045 | pdf / en | 107597 | PASS | p=7; tables=NE | success | 1/0/0 | L*/B/N/N/N | eligible | `f-79488c502a03ed9f4a53cc97` |
| c1-0046 | pdf / en | 221080 | PASS | p=6; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-2f6908a097fdf79c801c5958` / E missing |
| c1-0047 | pdf / en | 223701 | PASS | p=13; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-e093cfa721b4b627c7273093` / E missing |
| c1-0048 | pdf / en | 228777 | PASS | p=17; tables=NE | success | 1/3/1 | L/N/N/N/N | eligible | `f-f0bd89c34bff45a759be9ba2` |
| c1-0049 | pdf / en | 254032 | PASS | p=8; tables=NE | success | 1/0/0 | L/N/N/N/N | eligible | `f-ecde49af375b0b63304f2d97` |
| c1-0050 | pdf / en | 461365 | PASS | p=38; tables=NE | success | 1/0/0 | L/N/N/N/N | eligible | `f-8c5d8621865679e9baf0076c` |
| c1-0051 | pdf / en | 3578 | PASS | p=1; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-7d0c4f9b334a1fef27c3f4c4` / E missing |
| c1-0052 | pdf / en | 8481 | PASS | p=1; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-272b7d608e35ec69e944c9c5` / E missing |
| c1-0053 | pdf / en | 10160 | PASS | p=1; tables=NE | success | 0/4/2 | L/N/N/N/N | eligible | `f-b20e7fd26dd5a5868b1ac0b7` / E missing |
| c1-0054 | pdf / en | 16338 | PASS | p=1; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-22bc6982834554021c1b16a1` / E missing |
| c1-0055 | pdf / en | 19520 | PASS | p=1; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-6e17bd403d318d8869396577` / E missing |
| c1-0056 | pdf / en | 27418 | PASS | p=2; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-2f40a3260c85c7100ae53422` / E missing |
| c1-0057 | pdf / en | 29716 | PASS | p=5; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-8d9a68dffe84a581ec22f891` / E missing |
| c1-0058 | pdf / en | 47143 | PASS | p=2; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-baa2ba7d76be9f2547f111d8` / E missing |
| c1-0059 | pdf / en | 59079 | PASS | p=4; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-961bf414e16ad7d55adf6753` / E missing |
| c1-0060 | pdf / en | 59496 | PASS | p=10; tables=NE | success | 0/0/0 | L/N/N/N/N | eligible | `f-1e25d8381e411eea32f0d3ea` / E missing |
| c1-0061 | xlsx / en | 9053 | PASS | c=12;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-fef039fa977f1596021f445f` / E missing |
| c1-0062 | xlsx / en | 11687 | PASS | c=574;f=0;mc=0 | success | 1/3/2 | L/N/N/N/N | EXCLUDED: test family | `f-a312c4413a8e85f6923b6a18` / T |
| c1-0063 | xlsx / en | 11879 | PASS | c=137;f=0;mc=0 | success | 0/3/1 | L/N/N/N/N | eligible | `f-de545f2e78ece328353749fc` / E missing |
| c1-0064 | xlsx / en | 11998 | PASS | c=319;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-44593c084444cc503f5bc84c` / E missing |
| c1-0065 | xlsx / en | 16574 | PASS | c=531;f=0;mc=0 | success | 0/3/1 | L/N/N/N/N | eligible | `f-81fa9b61a35cd08b54603d74` / E missing |
| c1-0066 | xlsx / en | 21362 | PASS | c=1028;f=0;mc=0 | success | 0/3/1 | L/N/N/N/N | eligible | `f-0b2309fe1600779bbe082212` / E missing |
| c1-0067 | xlsx / en | 25821 | PASS | c=2023;f=110;mc=0 | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-51018aa9d847d10e9f60f476` / review hold |
| c1-0068 | xlsx / en | 29068 | PASS | c=1884;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-2cb7b77d368bcb6eab1f9b72` / E missing |
| c1-0069 | xlsx / en | 36494 | PASS | c=520;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-7a128676be9d7a4f0d895a81` / review hold, E missing |
| c1-0070 | xlsx / en | 73105 | PASS | c=77;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-50ae1cabfc389688b1c43caa` / E missing |
| c1-0071 | xlsx / en | 3487671 | PASS | c=913;f=0;mc=0 | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-cad035b845976f3a95b425d1` / review hold |
| c1-0072 | xlsx / en | 11814 | PASS | c=4;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-f063c0f4ccf9cdb51f70ed0b` / E missing |
| c1-0073 | xlsx / en | 12372 | PASS | c=33;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-baa2ba7d76be9f2547f111d8` / E missing |
| c1-0074 | xlsx / en | 14226 | PASS | c=134;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-0d93417332338976b13822b3` / E missing |
| c1-0075 | xlsx / en | 17554 | PASS | c=62;f=13;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-b3df500ce993df5f5a75ea6f` / review hold, E missing |
| c1-0076 | xlsx / en | 23402 | PASS | c=160;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-4e39f79f9165e2be0747687c` / E missing |
| c1-0077 | xlsx / en | 25657 | PASS | c=354;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-102080e40ac2f3313b49591c` / E missing |
| c1-0078 | xlsx / en | 32438 | PASS | c=754;f=94;mc=1 | needs_review | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, review hold, E missing |
| c1-0079 | xlsx / en | 78355 | PASS | c=17883;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-87e7cc96fe15f33815720e4d` / E missing |
| c1-0080 | xlsx / en | 82097 | PASS | c=332;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-eba227541d78dc993859554b` / review hold, E missing |
| c1-0081 | xlsx / en | 84308 | PASS | c=2503;f=3;mc=0 | needs_review | 1/0/0 | L/N/N/N/N | eligible | `f-2f40a3260c85c7100ae53422` / review hold |
| c1-0082 | xlsx / en | 105115 | PASS | c=5950;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a14fed00f94949a69cd39230` / review hold, E missing |
| c1-0083 | xlsx / en | 135520 | PASS | c=3230;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-5dc17ab00c3b3a3d25aab23e` / review hold, E missing |
| c1-0084 | xlsx / en | 149870 | PASS | c=266;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-f1cef1f6e66e5316d5df3933` / review hold, E missing |
| c1-0085 | xlsx / en | 162162 | PASS | c=13328;f=1519;mc=48 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-2371b76dd63b6b7fe6552dc1` / review hold, E missing |
| c1-0086 | xlsx / en | 188900 | PASS | c=14248;f=0;mc=0 | success | 0/3/1 | L/N/N/N/N | EXCLUDED: test family | `f-5bfd3ebb0ecf7a6efc413b7c` / T, E missing |
| c1-0087 | xlsx / en | 197310 | PASS | c=15385;f=3643;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-50868650d19afa8bd7f2168c` / review hold, E missing |
| c1-0088 | xlsx / en | 219237 | PASS | c=16402;f=784;mc=686 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-6eed0a598517dfddbc6e8182` / review hold, E missing |
| c1-0089 | xlsx / en | 257437 | PASS | c=2910;f=395;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-9ffa9209f565a182cd9d9fde` / review hold, E missing |
| c1-0090 | xlsx / en | 434069 | PASS | c=56518;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-4ecc50db3d88e6ffca8a3d12` / review hold, E missing |
| e2-office-06dfbd6eeae9cd9a | xlsx / unknown | 127669 | PASS | c=3237;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-b99eb463bad5ffc6433cbd73` / review hold, E missing |
| e2-office-081ca479f8d7eebf | xlsx / unknown | 735341 | PASS | c=1472;f=74;mc=1 | failed/unsupported_format | 0/0/0 | L/N/N/N/N | eligible | `f-b3df500ce993df5f5a75ea6f` / failure retained, E missing |
| e2-office-0b98928f48030222 | xlsx / unknown | 466830 | PASS | c=93210;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-0209294c95551f8fe8e17d3f` / review hold, E missing |
| e2-office-12e4e53f72de5a73 | docx / unknown | 1306807 | PASS | p=69;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-13bbfb6a6b8a1c67 | xlsx / unknown | 290275 | PASS | c=50897;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-9e44ca658a35e83a408c5864` / E missing |
| e2-office-18d8ec96e0631802 | xlsx / unknown | 185796 | PASS | c=16613;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a14fed00f94949a69cd39230` / review hold, E missing |
| e2-office-20ffd4320870b219 | docx / unknown | 820861 | PASS | p=49;t=2;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-28a174ed631cdcbb | docx / unknown | 22923 | PASS | p=15;t=10;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-747914e405d404dfc72f4dc0` / review hold, E missing |
| e2-office-2e56e6dd88e4aca5 | xlsx / unknown | 21825 | PASS | c=1808;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-0d93417332338976b13822b3` / E missing |
| e2-office-3320155211acbfd4 | xlsx / unknown | 224560 | PASS | c=33680;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-9e44ca658a35e83a408c5864` / E missing |
| e2-office-3377338b6feaa700 | docx / unknown | 115901 | PASS | p=8;t=6;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, review hold, E missing |
| e2-office-39a738041ccbbf3f | xlsx / unknown | 43305 | PASS | c=1152;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-81fa9b61a35cd08b54603d74` / review hold, E missing |
| e2-office-3e87de0bb8660f9d | docx / unknown | 784395 | PASS | p=93;t=2;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-42093d9dd7c328b7 | xlsx / unknown | 156305 | PASS | c=11918;f=3883;mc=14 | needs_review | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, review hold, E missing |
| e2-office-44bdd5c6608da5e2 | docx / unknown | 36203 | PASS | p=23;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / E missing |
| e2-office-4725927cfda086a8 | docx / unknown | 79773 | PASS | p=73;t=2;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-6a4a9a2c14438e5d54b34127` / review hold, E missing |
| e2-office-4ba25f4a6c27c9f3 | xlsx / unknown | 43406 | PASS | c=2844;f=30;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-102080e40ac2f3313b49591c` / review hold, E missing |
| e2-office-51bd4fd25d37dd92 | xlsx / unknown | 1987099 | PASS | c=237751;f=0;mc=0 | failed/limit_exceeded | 0/0/0 | L/N/N/N/N | eligible | `f-87e7cc96fe15f33815720e4d` / failure retained, E missing |
| e2-office-53215c5d4f3d1197 | docx / unknown | 608720 | PASS | p=52;t=2;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-545836d5b9807326 | xlsx / unknown | 735545 | PASS | c=1473;f=77;mc=1 | failed/unsupported_format | 0/0/0 | L/N/N/N/N | eligible | `f-b3df500ce993df5f5a75ea6f` / failure retained, E missing |
| e2-office-5770ead3a21a9a82 | docx / unknown | 57548 | PASS | p=50;t=12;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-0209294c95551f8fe8e17d3f` / review hold, E missing |
| e2-office-5b32a888891b0775 | docx / unknown | 153343 | PASS | p=450;t=4;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-fe06b6e1c3b69e9155489b9a` / review hold, E missing |
| e2-office-5fe8e22215112bcf | xlsx / unknown | 1422518 | PASS | c=1613;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-5bfd3ebb0ecf7a6efc413b7c` / T, review hold, E missing |
| e2-office-60444e0721322cfb | xlsx / unknown | 79085 | PASS | c=2591;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-86bdd44ccee832630f8045d3` / review hold, E missing |
| e2-office-609b8693b5da918b | docx / unknown | 499376 | PASS | p=99;t=2;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-63555ce938b1332e | docx / unknown | 54633 | PASS | p=13;t=6;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-9ffa9209f565a182cd9d9fde` / review hold, E missing |
| e2-office-69b2b4b38c92ace2 | docx / unknown | 580697 | PASS | p=47;t=1;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-736173b7d266e9bf | docx / unknown | 725202 | PASS | p=57;t=1;n=0;a=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-7697ba87770f74d2 | docx / unknown | 1521469 | PASS | p=96;t=2;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-77cdb15f5d2488b0 | docx / unknown | 38608 | PASS | p=18;t=1;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-40f6b76bf973908880846006` / E missing |
| e2-office-7b604ce0f3dfe336 | xlsx / unknown | 137595 | PASS | c=2369;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-5dc17ab00c3b3a3d25aab23e` / review hold, E missing |
| e2-office-7ca9cff3e9dfd9a6 | docx / unknown | 32075 | PASS | p=24;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / E missing |
| e2-office-7fc326cc7ece1efe | xlsx / unknown | 129020 | PASS | c=213;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-50ae1cabfc389688b1c43caa` / E missing |
| e2-office-81b8482e33f111e1 | xlsx / unknown | 294849 | PASS | c=50690;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-9e44ca658a35e83a408c5864` / E missing |
| e2-office-86e500b1938eca3f | docx / unknown | 25441 | PASS | p=3;t=1;n=0;a=0 | needs_review | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, review hold, E missing |
| e2-office-8f8b935a18bfab0c | docx / unknown | 87549 | PASS | p=55;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-6a4a9a2c14438e5d54b34127` / review hold, E missing |
| e2-office-901e5c14cd88ebbd | docx / unknown | 58332 | PASS | p=30;t=4;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-ca0e1e1d0193fb77d75fd707` / review hold, E missing |
| e2-office-969193c6e25c5c79 | xlsx / unknown | 1830235 | PASS | c=211023;f=35413;mc=25096 | failed/limit_exceeded | 0/0/0 | L/N/N/N/N | eligible | `f-2371b76dd63b6b7fe6552dc1` / failure retained, E missing |
| e2-office-992c609aeec890cd | xlsx / unknown | 25824 | PASS | c=2023;f=110;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-51018aa9d847d10e9f60f476` / review hold, E missing |
| e2-office-9e49b29b78824c1f | docx / unknown | 361793 | PASS | p=473;t=0;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-fe06b6e1c3b69e9155489b9a` / review hold, E missing |
| e2-office-a1e7393c6189453e | xlsx / unknown | 260230 | PASS | c=40607;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-9e44ca658a35e83a408c5864` / E missing |
| e2-office-a27e1fe462748973 | xlsx / unknown | 311231 | PASS | c=41808;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-9e44ca658a35e83a408c5864` / E missing |
| e2-office-adf5471ec3fa6f94 | docx / unknown | 507070 | PASS | p=83;t=1;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-b2d8036bbbee29c4 | docx / unknown | 998594 | PASS | p=59;t=1;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-c26ac5da4c35466d | xlsx / unknown | 75169 | PASS | c=213;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-50ae1cabfc389688b1c43caa` / E missing |
| e2-office-c492bef9daae10ca | xlsx / unknown | 84033 | PASS | c=572;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-eba227541d78dc993859554b` / review hold, E missing |
| e2-office-c6fe3682e1f6c35f | docx / unknown | 608959 | PASS | p=101;t=2;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-d2523ecbcb700848 | xlsx / unknown | 14556 | PASS | c=10;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-f063c0f4ccf9cdb51f70ed0b` / E missing |
| e2-office-d2642cf709d58d94 | docx / unknown | 83671 | PASS | p=18;t=8;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-9ffa9209f565a182cd9d9fde` / review hold, E missing |
| e2-office-d7868e62892f1951 | docx / unknown | 36057 | PASS | p=18;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / E missing |
| e2-office-d8c55470ba477011 | docx / unknown | 32432 | PASS | p=23;t=0;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / E missing |
| e2-office-dca7a02fc71408c4 | docx / unknown | 344508 | PASS | p=52;t=1;n=0;a=1 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a0dfd38d2480b58d0c7a6cc7` / review hold, E missing |
| e2-office-dcab8313148975f3 | docx / unknown | 43370 | PASS | p=280;t=1;n=0;a=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-ca0e1e1d0193fb77d75fd707` / E missing |
| e2-office-ed3233c774d78621 | xlsx / unknown | 85314 | PASS | c=351;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-eba227541d78dc993859554b` / review hold, E missing |
| e2-office-ed3246cb74092593 | xlsx / unknown | 552525 | PASS | c=82873;f=253;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-2cb7b77d368bcb6eab1f9b72` / review hold, E missing |
| e2-office-ef9bb253eef287c8 | xlsx / unknown | 76469 | PASS | c=9061;f=1250;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | EXCLUDED: test family | `f-c90c5cf2ef3cd307c831ed24` / T, review hold, E missing |
| e2-office-f0a1fbef05a3b9ba | docx / unknown | 40661 | PASS | p=11;t=1;n=0;a=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-40f6b76bf973908880846006` / review hold, E missing |
| e2-office-f0e930ab9734ecb3 | xlsx / unknown | 13545 | PASS | c=14;f=0;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-f063c0f4ccf9cdb51f70ed0b` / E missing |
| e2-office-f1ead1feca9f5f3e | xlsx / unknown | 218204 | PASS | c=31251;f=17;mc=0 | success | 0/0/0 | L/N/N/N/N | eligible | `f-9e44ca658a35e83a408c5864` / E missing |
| e2-office-f202322826064e55 | xlsx / unknown | 117760 | PASS | c=8142;f=0;mc=0 | needs_review | 0/0/0 | L/N/N/N/N | eligible | `f-a14fed00f94949a69cd39230` / review hold, E missing |

Per-source detailed warning codes, exact source digests, declared rights references
and structural counts remain in the ignored audit receipt. No warning count is
used as proof that a particular table/formula/header is correct. A zero observed
table count is not a reviewed negative statement about all visual content.

## Reconciliation with frozen reports

- [Corpus v1 assessment](corpus_v1_assessment.md): 90 originals, 30 per format,
  88 EN/2 CY and original size extrema agree. Its count-only profiler/manual
  subset findings are historical, not current structured-parser results.
- [Data-quality gate v3](data_quality_gate_v3.md): its approved11 and 48-question
  snapshots remain unchanged. Its 56 success/34 review and 11-source coverage
  concern an older implementation/snapshot; current matched evidence is
  52 success/38 review and expanded19, not a silently rewritten baseline.
- [Extraction v2 report](extraction_v2_report.md): same 60 additional originals,
  21,413,089 Office bytes, 150 unique SHAs and 75 declared families. Its original
  67 success/66 review/17 failure measurement is preserved. Stabilization later
  resolves implementation defects and updates the captured states to 69/77/4;
  no source was dropped or reacquired to get that count.
- [Current-stage stabilization](current_stage_stabilization_20261021.md): all
  latest format/state counts, four Office failure diagnoses, unchanged source
  identities, expanded Gold and partial fidelity denominators agree. Existing
  known fidelity/unsupported dimensions remain visible.
- [QG-00 handoff](qg00_review_handoff_20261021.md): pool 5 / attempted 3 /
  admitted 2 / blocked 1 / excluded-budget 2 remains unchanged. Budget exclusions
  for c1-0048/c1-0049 are not annotation-rights refusals.
- [Assisted reproducibility report](qg00_assisted_review_reproducibility_20261021.md):
  536 cells, 1,154 items, six regions and 60 uncertain cells agree. Existing
  proposals, partitions and user decisions were not regenerated or approved.
- ICDAR's frozen engineering execution was historical PASS with zero admitted
  pairs; the exact pinned implementation now reproduces that result. Applying the
  historical validator to newer code remains an expected rejection. Neither result
  supplies source-pair admission, independent Gold or QG-00 PASS.

Private RAG export/staging and historical remote-input copies are derived
experiment inputs, not external source datasets or additional Gold. Runtime/model
packages, GGUF/HF caches, kernels, ranked results, generated responses and resource
journals are execution artifacts. Their presence does not authorize new external
processing. No remote privacy/availability check or model-asset qualification was
performed for this local dataset audit.

## Prioritized eligible human-assisted subset and blockers

1. **c1-0033 first, then c1-0040**, using the existing local AI-assisted package.
   Exact bytes and the recorded annotation rights are verified; two pages/six
   proposed regions/536 cells/1,154 items are ready for user inspection. Review
   literal values, blanks, coordinates, spans, topology, printed units and every
   uncertain/semantic proposal against the original. Record actual decisions and
   corrections in a new authorized working copy; do not mark the current package
   complete. This yields assisted development annotations only, with assistance
   and reviewer provenance retained. No new labels are created by this audit.
2. A genuinely independent reviewer is required for a separate source-first blind
   review. Reviewer identity, prior exposure and source inspection must be real;
   an exposed or machine-assisted workspace cannot supply that independence.
   Currently **BLOCKED: no independent reviewer available**.
3. Resolve c1-0045's specific permission before annotation; obtain source-specific
   decisions for c1-0048/c1-0049 and any Office/other legacy annotation expansion.
   No additional evidence was supplied, so these states remain unchanged.
4. Use the enforced 55-source Office / 138-source combined isolation subset for
   development against the reserved QA test families. Overlapping controls remain
   excluded from independent dev/evaluation against those families. Future blind
   acceptance still requires genuinely unexposed, reviewed families and sources.
5. Historical ICDAR replay is complete. Source-pair eligibility remains BLOCKED:
   obtain authorized individual original/annotation pairs and their coordinate
   evidence separately. Do not infer admission from successful replay, fetch whole
   archives or invent a supported annotation kind to remove the blocker.
6. Qualified real RU/KK originals, reviewed language labels, difficult/scanned/
   mixed and sensitive/negative coverage, broader exact-text/geometry/formula/
   display Gold and human family review remain external/data-annotation work.
   Neither parser success nor synthetic tests can fill those coverage gaps.

## Initial inventory verification (completed earlier; not rerun)

Commands ran from the repository root with the existing venv. Local audit scripts
are ignored receipts, not new production tooling. The exact command arrays for
both native review-validator calls are also retained in `supplement.json`.

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-inventory-20261021/discover.py
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-inventory-20261021/audit.py run-1
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-inventory-20261021/audit.py run-2
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-inventory-20261021/supplement.py
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-inventory-20261021/bindings.py
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-inventory-20261021/replay_icdar.py
.venv/Scripts/python.exe -B evaluation-output/pdf-table-gold-review-v1-20261019/verify.py
.venv/Scripts/python.exe -B -m pytest tests/unit/test_corpus_v2.py tests/unit/test_retrieval_eval.py tests/unit/test_rag_gold.py tests/unit/test_pdf_review_eligibility.py -q --tb=short -p no:cacheprovider --basetemp=evaluation-output/dataset-readiness-inventory-20261021/tests-local --junitxml=evaluation-output/dataset-readiness-inventory-20261021/tests-local.xml
.venv/Scripts/ruff.exe check src tests tools alembic
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-inventory-20261021/check_report.py
git diff --check
git diff --cached --check
git status --short
```

| Check | Executed result |
| --- | --- |
| Discovery and registration reconciliation | PASS; 150 unique manifested sources, 13 external candidate families plus separate own RU/KK target accounted |
| Fresh RAW/schema/Gold/locator audit, twice | PASS/exit 0 both; identical full JSON and fingerprint `6bea9a8f...c3db4a`; 608 protected files unchanged each run |
| Source acquisition bindings | PASS/exit 0; 60 Office events/capture pairs and 90 legacy source metadata rows; frozen Gold subset relationships preserved |
| Five-PDF packet integrity verifier | PASS/exit 0; two identical 25-file bundles, 90 originals, 19 reviewed records, 110 assertions/19 mappings accounted |
| Admitted packet / assisted item validation | PASS/exit 0; both admitted packets hash-valid, 1,154 pending items validated; zero human completion claimed |
| Existing review validator, all five and admitted two | Expected BLOCKED/native exit 2 each; zero completed reviews, export_ready=false; no export requested or created |
| Current ICDAR existing qualification validator | **FAIL/exit 1** at frozen-base code SHA; six historical code/test/tool protected pins differ; source captures/qualification fingerprint independently match |
| Existing focused unit tests | **118 passed, 0 failed, 0 skipped, 19.82s**, local Windows runtime, exit 0 |
| Ruff over src/tests/tools/alembic | All checks passed, exit 0 |
| Final preservation/report/diff checks | PASS: all 150 source rows reconciled; 608 protected files unchanged; four DOCX packet artifact lists valid; report links/privacy/whitespace checked; tracked and staged diffs empty |

The first sandboxed test attempt stalled after partial progress and was interrupted;
it is not a pass. The same focused command completed in the normal local Windows
runtime. Initial audit-harness attempts failed on Python import configuration,
raw-versus-normalized pin handling and nested Office capture shape; those receipt
issues were corrected without changing data or production code before the two
successful identical runs. No test result or failed check is silently counted as
success. Full pipeline, parser experiments, models, OCR, GPU, production E2E and
external acquisition were not run because this is a documentation/data audit.

## Closure verification — 22 October 2026

Only the family-admission gap and historical-code replay were investigated.
The 150-source EDA, locator/text diagnostics, acquisition and parser experiments
were not repeated. A SHA/size identity check confirms all 150 RAW sources and
all frozen Gold remain unchanged; the existing 608-file preservation receipt
also still matches, including the unrelated engineering audit. Strict Gold
loaders still accept 19 Extraction / 48 Retrieval / 20 Answer records unchanged.

Exact closure commands from the repository root:

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-closure-20261022/replay_historical.py
.venv/Scripts/python.exe -B -m tools.extraction_quality.dataset_readiness --manifest docs/eda/corpus_v1_manifest.csv --reference evaluation-output/extraction-v2-20261021/control-manifest-final.json --candidates docs/eda/extraction_corpus_v2_manifest.json --retrieval-gold local-evaluation/retrieval_gold_v1.jsonl --answer-gold local-evaluation/rag_gold_v1_approved.jsonl --output evaluation-output/dataset-readiness-closure-20261022/isolation-1.json
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-closure-20261022/verify_closure.py
.venv/Scripts/python.exe -B -m pytest tests/unit/test_dataset_readiness.py tests/unit/test_corpus_v2.py tests/unit/test_retrieval_eval.py tests/unit/test_rag_gold.py tests/unit/test_pdf_review_eligibility.py -q --tb=short -p no:cacheprovider --basetemp=evaluation-output/dataset-readiness-closure-20261022/tests --junitxml=evaluation-output/dataset-readiness-closure-20261022/tests.xml
.venv/Scripts/ruff.exe check src tests tools alembic
.venv/Scripts/ruff.exe format --check tools/extraction_quality/dataset_readiness.py tests/unit/test_dataset_readiness.py
.venv/Scripts/python.exe -B evaluation-output/dataset-readiness-closure-20261022/check_final.py
git diff --check
git diff --cached --check
git status --short
```

The historical wrapper executes the unchanged validator as:

```powershell
# cwd = evaluation-output/dataset-readiness-closure-20261022/historical-670b59d
# PYTHONPATH = that snapshot's absolute src directory; same local venv executable
python -B evaluation-output/icdar2013-qualification-20261021/validate_qualification.py --output evaluation-output/icdar2013-qualification-20261021/closure-replay.json
```

The admission command reads metadata only and must be used for selection against
these QA test families. `--select-id` is repeatable. `verify_closure.py` executes
the identical admission command three more times with fresh output destinations:
`repeat.json` (no selected IDs), `overlap.json` (the five excluded Office IDs), and
`usable.json` (all 55 allowed Office IDs). Exact argument arrays are preserved in
`evaluation-output/dataset-readiness-closure-20261022/closure-verification.json`.
Existing output paths reject overwriting; use new destinations for another replay.

| Closure check | Exact result |
| --- | --- |
| Reproduce previous scope gap | All five remain native-eligible in the preserved source audit; none consulted the separate QA test reservations |
| Authoritative relationship check | Five Office records, 2 DOCX/3 XLSX, source-bound to c1-0009 or c1-0086 test families in both Gold snapshots |
| Metadata guard, repeated | PASS/exit 0; identical output; 150 retained, 12 excluded, 138 eligible for the stated isolation scope; Office 60/5/55 |
| Proposed five-record overlapping selection | BLOCKED/exit 2; all five rejected; full 150-record ledger retained |
| Proposed complete 55-record Office subset | PASS/exit 0; 55 requested, 0 rejected; no reserved family admitted |
| Exact historical ICDAR replay | PASS/exit 0; 130 pinned entries restored, six historical code/test/tool files; entire prior result reproduced |
| RAW/Gold/preservation | PASS; 150 unchanged identities, Gold 19/48/20 unchanged, 608 protected files unchanged |
| Regression tests plus existing affected validators | **132 passed, 0 failed, 0 skipped, 19.60s**, exit 0 in the local Windows runtime |
| Ruff and formatting | PASS; final commands above; only the two new validation/test files formatted |
| Final scope/privacy/report checks | PASS; 150 source rows retain population and new admission outcomes; no private content or source/Gold artifact staged |

The first new-test collection reproduced the missing admission module. After the
guard was added, all 14 new synthetic regression cases pass. The first Ruff check
identified formatting/line-length issues; formatting corrected them and final
checks pass. These intermediate failures are not represented as successful checks.
The guard changes no production ingestion, native extraction or frozen data schema.

COMMIT: authorized scoped Conventional Commit
`fix(eda): enforce dataset test-family reservations`. The completion message
records the actual SHA after the verified files are committed.

REMAINING: **no unresolved verification issue in this closure scope**. Missing
independent reviewer, unassessed/blocked source rights, ICDAR/external source pairs,
real RU/KK coverage and other annotation gaps remain BLOCKED/NOT_EVALUATED as
documented. Historical public controls are not a fresh independent holdout.

GIT scope: only this report and the two admission validator/test files are included
in the commit. The unrelated `docs/eda/independent_engineering_audit_20261020.md`
remains untracked and unchanged. Exact final Git status and commit SHA are returned
in the completion message. No original, source text, private annotation, reviewer
identity, Gold, historical result or credential is committed.
