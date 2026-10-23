# Extraction Data Readiness — 23 October 2026

STATUS: **BLOCKED for an independently evaluator-ready release.** Scoped software
verification and private release integrity passed. Development oracles and assisted
observations are available; QG-00/QG-01 remain **NOT_EVALUATED**, independent test is
**TEST_NOT_READY**, and five-model quality evaluation is **BLOCKED**. Existing
fidelity failures are preserved. No quality gate, model improvement or production
readiness is claimed.

The run began on `codex/extraction-research-20261023`, HEAD
`a7c47090ec87a14aab68f1bf2ab9da20ed74b271`, rather than the supplied historical
`main f83def0`. Pre-existing extraction R1 changes and the untracked engineering
audit were preserved. No push, training, model benchmark, GPU/cloud transfer,
deployment, production-parser change or dependency installation occurred.

CHANGED: four offline modules under `tools/extraction_quality/` (`readiness_io`,
`readiness_release`, `office_readiness_oracle`, `readiness_evaluator`), two synthetic
unit-test modules, `readiness_predictions_v1_schema.json`, and this report. New
originals, rights captures, proposals, annotations and release receipts remain
private under ignored `evaluation-output/extraction-data-readiness-20261023-final/`.
No RAW, frozen Gold, old reference, historical report or project instruction changed.

DESIGN: [QG-00/01 and coverage](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md),
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA),
[format contracts](../../DocLens_AI_Extraction_Strategy.md), and the
[source-bound annotation handoff](qg00_review_handoff_20261021.md) govern this run.
The [data-quality procedure](../../.agents/skills/doclens-data-quality/SKILL.md)
was applied. Existing inventories, frozen native captures, fingerprints, family
guard and external qualification were reused. No repeated legacy EDA/acquisition,
parser stabilization, grid/overlay generation or external card survey was performed.

## Accounted populations and rights

| Population | Documents | PDF / DOCX / XLSX | Evidence boundary |
| --- | ---: | --- | --- |
| Immutable existing controls | 150 | 30 / 60 / 60 | Historical outcomes: 69 success, 77 needs_review, 4 failed |
| New registered Kazakhstan originals | 50 | 8 / 20 / 22 | Distinct publisher originals; no DocLens/model prediction run |
| Combined release denominator | 200 | 38 / 80 / 82 | All existing failures and missing labels retained |

The original 19 partial Extraction Gold attestations remain unchanged; 131/150
old sources and all 50 new sources lack these labels. Historical attestations
are distinct from new independent Gold, of which there are **zero**. Source-native
oracles do not reduce the independent-Gold shortfall.

The effective matrix records format, declared and source-observed/unknown language,
family, exposure, split, difficulty, prior outcome, assertion origin/counts, warnings
and separate evaluation/annotation/training/redistribution/cloud scopes. Old language
metadata is preserved rather than promoted to verified document language. All 12
reserved QA-family sources retain their exclusion from development comparison.

Source-specific interpretation admitted 17 existing Office files for new local
annotations, alongside the two previously admitted PDFs. With the 50 new originals,
69/200 have a positive new-annotation decision; 131 remain quarantined for that use.
Training and cloud scopes remain unestablished; this run exercised neither.

**A substantive rights conflict was found in original content.** A BDUK ITT
restricts reproduction outside tender-response preparation. The effective release
quarantines its three-member source-page family, including one legacy sibling,
without rewriting previous manifests or results. Another selected DOCX is held for
populated personal fields and third-party content. Consequently 196/200 retain an
established local-evaluation scope, with four quarantined. The complete 200-source
denominator is still present. Cryptographic validation binds documentary decisions;
it does not authenticate a legal conclusion or human signature.

## Existing PDF evidence and historical assertions

Both authorized original renders were inspected; existing proposals, overlays and
native/source-only findings were reused. `pdf-assisted-observations-v1.json` keeps
AI assistance separate from the automatic observation ledger and frozen reference.

| PDF measure | Count / interpretation |
| --- | --- |
| Original proposal items accounted | 1,154 |
| Existing limited admitted-field items | 719; unchanged |
| Proposed cells | 536 |
| Suspected blank cells | 291; all remain unverified |
| Cells with original uncertainty flags | 60; flags retained |
| Existing source-glyph correspondences | 112; not independently verified cells |
| New AI-assisted visible-literal observations | 116 (44 role/department cells, 72 budget headers) |
| Proposed corrections | 2 trailing-whitespace changes, visible-literal scope only |
| New human item decisions / independent Gold | 0 / 0 |

All 1,154 items have original identity, source evidence, correction and uncertainty
slots. The 1,038 items without a new assisted literal decision remain unanswered;
all 1,154 still require authentic independent review for Gold. Empty literals,
ambiguous borders/spans, signs and numerical literals, semantic order and
header/value/unit/period links are not certified by source-only matches. The two
whitespace proposals do not establish exact source-glyph spacing. No existing
decision CSV, proposal package or reference was overwritten.

Saved native captures were joined to the 19 historical Gold records without new
extraction or a replacement Gold audit: 282 assertions, 187 observation matches,
24 locator/parser mismatches, 12 loss-or-source ambiguities and 59 unsupported
native table/order cases. The **95 outstanding assertions** have targeted packets
by format, containing original references and exact capture bindings. Their
remaining source reinspection is explicitly outstanding; capture absence is not
proof that the original lacks the fact. These classifications are diagnostics,
not independent adjudications or newly measured quality PASS.

## Office source-native oracles

Twenty existing Office candidates were selected from prior structural metadata.
Three were excluded after source-content/rights inspection. The result is **7 DOCX
and 10 XLSX** oracles; the approximate 8–12 DOCX target has a one-document shortfall.
The four existing Office failures remain negative controls in the full matrix.
Files with missing formula caches that are QA-held or failed were not silently
promoted to positive annotation coverage.

DOCX observations preserve physical XML order within each part, actual part/path,
paragraph tokens, styles/headings, tables, rows/cells, merge declarations, section
and note/reference IDs. The seven sources contain 44 parts, 1,241 paragraph
elements, 43 table elements, 601 table-cell elements, 53 gridSpan declarations and
18 vMerge declarations. These are XML-element counts, not verified visible pages,
semantic headings, active note references or independent structural Gold. Nested
table handling is covered by a synthetic regression; real selected nested-table
coverage is not established. Drawing text, inherited style interpretation,
tracked-change visibility and Word pagination remain unsupported.

The ten XLSX oracles cover 46 sheets, 30,588 stored XML cells and 349 merge ranges.
They preserve stored types and exact lexical values, formula text/attributes,
cache state, explicit/custom number formats, sheet identity and date-system
metadata. There are 666 lexical zero values, 7,550 cells without a v element and
110 formula cells with present caches. Missing/empty-cache behavior is tested
synthetically; no such positive real-cache coverage is claimed for this subset.
No formula was calculated. Numeric serial dates were not converted, display
values were not guessed, and absent physical cells remain distinct from stored
blank cells. The v1 Gold reader and frozen schemas remain unchanged.

## New real-language acquisition and test preparedness

Only new usage rights were researched. The publisher's primary
[reuse terms](https://stat.gov.kz/ru/description/) permit reuse and modification
of official statistical information with source attribution. Captures bind exact
URLs, timestamps, revision/header metadata and hashes; decisions exclude logos,
personal information and material outside that scope. No rights were inferred
from a dataset card, public hosting or an attachment hash alone.

Metadata discovery covered 26 publisher topics and 48 publication pages. Selection
was frozen before payload inspection: 13 PDF, 20 DOCX and 27 XLSX attempts, ranked
deterministically within formats. Limits were 2 MiB/file, 30 MiB payload in total,
four metadata workers and serial payload admission. Acquired payload totals
6,856,223 bytes. Of 60 selected attempts, 50 became registered originals, five
were unavailable, two remain language-quarantined and three qualified originals
remain outside the 50-document registration. Another 125 known candidates were
excluded before payload acquisition. All dispositions remain in the private ledger.

Source-native lexical evidence gives **RU 26 / KK 17 / mixed 7**. The requested
20/20/10 distribution is not met: KK shortfall three, mixed shortfall three, RU
surplus six. The first heuristic overcalled mixed language from Kazakh proper
names and missed some Russian vocabulary; a versioned qualification record uses
actual language cues and part/page evidence instead. These remain automatic
source-language observations, not independent human language certification.
No synthetic originals or duplicated byte streams fill the target. The eight
PDFs contain 107 physical pages with native text observations; real scan coverage
and independent full-page transcription remain absent. CER/WER is NOT_EVALUATED.

Translations and repeated periods share the conservative publisher-topic family.
There are 17 declared new families/components, zero exact SHA overlaps with the
old 150, and zero diagnostic near-duplicate pairs within the new sample using
the existing shingle function at 0.9. This is not a new approved quality threshold.
Cross-topic template/translation completeness and semantic overlap with legacy
sources remain unreviewed. All new records were assigned development status
before candidate-model inference; none was promoted to blind test. Independent
sealed families: **0**, target **20–30**, readiness **TEST_NOT_READY**.

## External pilots

The existing rights/coordinate/availability qualification was reused, with no
repeated card survey or full archive download. No eligible exact original+label
pair was available under those records. PubTables-1M remains **0/30–50 tables**;
DocLayNet remains **0/30–50 pages**. Both pilots are BLOCKED on source-specific
original rights and exact pair availability. No hypothetical record is counted as
a payload attempt. The larger Extraction-v2 targets were not modified. OmniDocBench,
FinTabNet.c and Darmm were deferred as instructed. Publisher/automatic labels were
not relabelled as independently reviewed human Gold.

## Frozen release and offline CLI

The private `RELEASE.json` binds **441 artifacts** and **225 protected paths**,
including all 150 existing originals, 50 new registered originals, frozen Gold,
QA/source manifests, the two-PDF reference and final evaluator code/schema.
Fingerprint:
`520f92f507b9f2769abaedbbf48c3fff95f62f298944bf6ec3fb88b2c786d6ce`.
Unregistered/quarantined payloads and all rights receipts remain separately
accounted artifacts. Verification detects added artifacts, changed bytes, unsafe
paths and linked files. Labels remain local; the public report contains counts
and limitations rather than private text, filenames or label rows.

The immutable release contains a source matrix, rights and exposure decisions,
family seed/assignments, automatic/oracle/proposal tiers, unresolved queues,
datasheet, feature denominators and the saved local reproduction scripts.
`prepare` reconstructs the incremental legacy join in a fresh private output;
the final effective matrix adds the separate acquisition/rights revisions.
The archived preparation code binding records the earlier preparation revision;
the release separately pins the final validator/scorer code. Originals were not
reacquired for the joins or validators.

Commands below run offline from the repository root:

```powershell
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_release verify --output evaluation-output/extraction-data-readiness-20261023-final
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_evaluator office --release evaluation-output/extraction-data-readiness-20261023-final
.venv/Scripts/python.exe -X utf8 -m tools.extraction_quality.readiness_evaluator score --release evaluation-output/extraction-data-readiness-20261023-final --predictions evaluation-output/readiness-empty-predictions-20261023.json --metrics evaluation-output/readiness-metrics-NEW.json
```

Metrics require a fresh destination outside the immutable release. The prediction
schema supports PDF text/order, OCR transcripts, tables/cells/spans/relationships
and provenance; DOCX structural XML locators/order; and separate XLSX stored,
formula/cache and display observations. Strict input rejects wrong SHA, duplicate
identities, inferred DOCX pages, unknown evaluation rights and reserved/test-family
predictions. The implemented comparator scores literal Office oracle fields only.
Independent PDF metrics, CER/WER, display fidelity and semantic relationships stay
NOT_EVALUATED without suitable references. Synthetic contract smoke is not a model
run or quality result. The actual empty-input smoke retained all **200 documents**,
zero predictions, 17 oracle-reference documents and 200 NOT_ATTEMPTED outcomes.

## Measurements and verification

Same 17-document workload, one worker, fresh child per mode, unchanged source,
rights and oracle-code bindings; no dependency/model changes or cache eviction:

| Mode | Wall seconds with startup | Documents/sec | Per-document P50 / P95 seconds | Sampled peak tree RSS |
| --- | ---: | ---: | --- | ---: |
| Uncached oracle/write | 3.7993 | 4.4746 | 0.0839 / 0.7156 | 82,604,032 bytes |
| Identical no-change cache rerun | 2.1248 | 8.0008 | 0.0214 / 0.1223 | 105,164,800 bytes |

RSS was sampled every 5 ms and may miss short peaks. The warm JSON-loading path
used more peak RSS. This compares uncached generation with a SHA/version/rights
cache, not before/after production-parser quality or a general performance claim.
Atomic artifact/checkpoint writes retain incomplete work without granting cache
hits. A mismatched key or changed output is rejected rather than overwritten.

VERIFIED:

- `pytest` command in the next block: **248 passed, 2 skipped, 0 failed**.
- Ruff over the four new modules and two test modules: **All checks passed**.
- Existing `pdf_dev_reference validate`, with the saved native-diagnostic
  validation config and frozen snapshot: **exit 0**, unchanged fingerprint
  `64fa75b779854918fc50df38bc3e3cb3bf0069c8cb6c76e775bf6c35f8e1c9dc`.
- `readiness_release freeze` and `verify`: **exit 0**, same release fingerprint;
  originals/Gold/reference hashes matched. `readiness_evaluator office`: **17/17
  cache hits**, no new observations written. Empty-prediction scoring: **exit 0**,
  no factual/quality PASS.
- Targeted negatives cover wrong SHA/source, duplicate JSON/ZIP/identities,
  fabricated reviewer claims, unknown rights, QA/test leakage, malformed/unsafe
  XML/ZIP, stored zero versus missing/blank/cache, PDF blank/span ambiguity,
  unsafe paths, interrupted checkpoint, added artifact and protected-byte drift.
- Final staged scope, secret-pattern check and `git diff --check` passed.

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_v2.py tests/unit/test_office_corpus_v2.py tests/unit/test_extraction_fidelity.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_fidelity_relationship_scope.py tests/unit/test_pdf_dev_reference.py tests/unit/test_data_quality_gate.py tests/unit/test_dataset_readiness.py tests/unit/test_corpus_v2.py tests/unit/test_readiness_release.py tests/unit/test_readiness_evaluator.py -q --basetemp evaluation-output/readiness-regressions-20261023-final --junitxml evaluation-output/readiness-regressions-20261023-final.xml
.venv/Scripts/ruff.exe check tools/extraction_quality/readiness_io.py tools/extraction_quality/readiness_release.py tools/extraction_quality/office_readiness_oracle.py tools/extraction_quality/readiness_evaluator.py tests/unit/test_readiness_release.py tests/unit/test_readiness_evaluator.py
```

SKIPPED / earlier failures: two symlink tests require unavailable Windows
privilege. The first new-test run hit sandbox TEMP `os.replace` permission failure;
the same test passed with workspace `--basetemp`, without weakening atomic writes.
One mistyped test filename collected no tests and was corrected. Initial local
acquisition-script decoding failed before payloads; explicit UTF-8 fixed the run.
Five actual unavailable payloads remain in acquisition results. Service/DB/ACL
runtime, deployment and five-model benchmarks were outside this data-only scope.

REMAINING / consolidated owner inputs: authentic independent PDF/Office/Gold and
language review; adjudication of the 95 historical assertions and ambiguous cells;
clearance or permanent exclusion of the restricted document family; an additional
rights-admitted DOCX if the minimum eight is retained; missing KK/mixed and scan
coverage with full-page OCR transcripts; independently reviewed 20–30 new sealed
families; eligible bounded external original+label pairs; and approved quality
thresholds. The independently evaluator-ready objective remains BLOCKED by these
inputs; no cosmetic QG PASS substitutes for them.

COMMIT: `1b3081c` — `feat(data): bind readiness ledger and Office source oracles`;
`415cf15` — `feat(data): freeze readiness releases and validate oracle predictions`.
This report is delivered in a separate documentation commit; its SHA is recorded
in the final chat response and local Git log.

GIT STATUS: only the following pre-existing unrelated paths remain after the
report commit; no readiness source, raw data or label artifact is left unstaged:

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
