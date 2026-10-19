# ML-20 extraction scenario coverage v1

Date: 2026-10-19. **Execution: PASS. Extraction quality/readiness: HOLD.**
**Production authorization: false.** This is a deterministic metadata/label/capture
audit, not a new extraction experiment or a claim of parser improvement.

Starting HEAD: `0a6dba3d686a3c1588474491b9ae425426f9e999`, branch main, clean
`git status --short`. Applicable root AGENTS.md and extraction-benchmark,
ML-experiment and data-quality skills were read; no applicable nested instructions
were found. Only the new audit, synthetic tests and this report are in scope.

## Method and denominators

`tools/extraction_quality/coverage_audit.py` reads the frozen manifest, original
source identities, strict reviewed Fidelity Gold, the existing 90-source baseline
pair and existing ML-18/19 final captures. It invokes no extraction function,
OCR executable, layout model, Office formula, macro or external relationship.
Office ZIP/XML elements are inventoried read-only; their text/values are not exported.
No dependencies, parameters, Gold, historical reports or captures were changed.

The separate populations are:

| Population | PDF | DOCX | XLSX | Total |
| --- | ---: | ---: | ---: | ---: |
| Metadata/technical documents | 30 | 30 | 30 | **90** |
| Reviewed Extraction Gold documents | 12 | 3 | 4 | **19** |
| Required text anchors | 90 | 15 | 21 | **126** |
| Partial-order pairs | 46 | 6 | 6 | **58** |
| Table-cell/span checks | 24 | 7 | 21 | **52** |
| Table relationships | 20 | 3 | 10 | **33** |
| Value/formula/cache checks, each | 0 | 0 | 13 | **13** |
| Numeric-bearing anchors, literal digit flag | 22 | 5 | 8 | **35** |

Provenance has **139 labels**: 126 anchors + 13 cell checks, not 139 unique
physical cells. Seventy-one sources have no reviewed Extraction Gold. Empty
labels yield NOT_EVALUATED/null, never perfect quality. Missing captures retain
their label totals and UNKNOWN counts. PARTIALLY_EVALUATED metrics have a null
overall score; no rate silently excludes unknown observations.

The 19-record snapshot contains the unchanged reviewed 11-record snapshot, which
contains the earlier reviewed eight; raw hashes and strict validators were checked.
Human review is the existing supplied attestation, not a new review by this audit.
Extraction Gold has no family/split fields. All current evaluation evidence is
exposed DEV; independent test availability is NOT_ESTABLISHED. No Retrieval Gold,
sealed TEST, new split or training data was read or created.

Every scenario counts a set of document identities once. Scenario rows overlap:
body, table, ancillary, language and status counts must not be summed. Their label
denominators mean all reviewed labels in those member documents, not only labels
about the feature. Separate anchor facets select actual region/digit labels;
order/relationship checks enter those facets only when both referenced anchors enter.
This avoids attributing every label in a footnote-bearing document to footnotes.

## Scenario matrix

Numbers below are directly reproduced by both final audit runs. U is the number
of applicable documents whose structural flag is UNKNOWN; zero U does not imply
semantic correctness. T/R/V are table cells / relationships / value checks.

| Scenario | Confirmed metadata documents | U | Reviewed documents | Anchors | T/R/V labels |
| --- | ---: | ---: | ---: | ---: | --- |
| PDF any native text proxy, including whitespace | 29/30 | 0 | 11 | 86 | 24/20/0 |
| PDF insufficient-native-text warning proxy | 3/30 | 0 | 3 | 15 | 0/0/0 |
| PDF reviewed table scope | 5/30 | N/A | 5 | 46 | 24/20/0 |
| PDF scanned, mixed, complex-layout classes, each | 0 confirmed/30 | 30 | 0 classified | 0 classified | NOT_EVALUATED |
| DOCX body paragraph elements | 30/30 | 0 | 3 | 15 | 7/3/0 |
| DOCX table elements | 17/30 | 0 | 3 | 15 | 7/3/0 |
| DOCX footnote elements, excluding separators | 16/30 | 0 | 2 | 12 | 7/3/0 |
| DOCX endnote elements, excluding separators | 15/30 | 0 | 2 | 12 | 7/3/0 |
| DOCX ancillary parts/elements | 19/30 | 0 | 2 | 12 | 7/3/0 |
| XLSX formula elements | 8/30 | 1 | 2 | 11 | 11/4/6 |
| XLSX formula with nonempty stored cache | 8/30 | 1 | 2 | 11 | 11/4/6 |
| XLSX formula with absent/empty cache | 3/30 | 1 | 0 | 0 | 0/0/0 |
| XLSX merge declarations | 17/30 | 1 | 2 | 11 | 11/4/6 |
| XLSX sparse-dimension proxy | 0 confirmed/30 | 1 | 0 in confirmed subset | 0 | 0/0/0 |

Native text/low-text signals do not establish textual/scanned/mixed document
subtype. The generic PDF table warning is not a table detector. Reviewed table
scope means supplied labels exist; the other 25 PDFs are not certified table-free.
Partial-order labels are not an independent complex-layout classification. No
IDs, titles, publisher names or Gold answer strings drive classification.

Office flags are element/part presence, not proof of nonempty or lost evidence.
For example, 16 DOCX have non-separator footnote elements, but the captured baseline
reports non-extracted footnote content on only **3 documents**. The single reviewed
footnote anchor is a separate one-label facet. Headers, footers, endnotes, comments
and drawing-region anchors have **zero reviewed labels**. Endnote elements alone
do not establish fifteen measured endnote omissions.

The sparse proxy is declared dimension area >=1,000 and stored-cell occupancy <1%;
it is not a semantic sparse-workbook label or cell-value fidelity measurement.
c1-0071 has a 63,918,519-byte XML entry, above the audit's 16 MiB entry cap.
Its seven selected XML entries total 63,954,689 bytes. All its structural flags
remain UNKNOWN; the archive was not decompressed past that bound. Zero confirmed
sparse proxies therefore does not establish absence. This is an audit coverage
limit, not a newly demonstrated extraction failure or license to relax parser limits.

Language metadata is **88 English source-page locales and 2 explicitly Welsh
attachment declarations**. Gold covers 18/1 respectively. RU, KK and mixed have zero
declared metadata examples or reviewed language-specific labels. Actual content
language, code-switching and semantic multilingual fidelity remain UNKNOWN: an
English page locale is not independent verification of document language.

Digit-bearing anchors: 35 labels; literal PDF presence is **22/22 observed**, with
**13 remaining UNKNOWN** because the DOCX/XLSX raw captures needed for that slice
are unavailable. PDF numeric-bearing provenance is 16/22, not perfect. Typed
numbers versus units, dates and identifiers are not fields in this Gold schema;
their semantic correctness is NOT_EVALUATED. No unreviewed numeric or OCR-number
accuracy is inferred from those digit matches.

## Baseline quality, status and unsupported boundaries

The retained current structured baseline covers all 90 documents:

| Format | Success | Needs review | Failed | Reviewed documents |
| --- | ---: | ---: | ---: | ---: |
| PDF | 27 | 3 | 0 | 12 |
| DOCX | 14 | 16 | 0 | 3 |
| XLSX | 15 | 15 | 0 | 4 |
| Total | **56** | **34** | **0** | **19** |

All 34 review-status sources remain in the denominator. Success is not fidelity
or production indexing approval. The older count-only profiler's 89/90 result
and sparse-workbook rejection are historical, not the current baseline's outcome.

Captured warning-document counts include PDF table-structure-not-preserved 30 and
insufficient text 3; DOCX footnotes 3, headers 9, footers 8, drawings 6, nested
tables 4, text boxes 2 and unsupported body content 5; XLSX missing formula definition
7, missing formula cache 3, drawings 11 and comments 1. Warning rows overlap and
are not semantic failure rates. In particular, a reviewed null formula/cache can
correctly match despite an unsupported reconstruction warning.

The audit replays all twelve PDF baseline results against current reviewed Gold:

| Replay subset | Text | Provenance | Order | Cells | Relations |
| --- | ---: | ---: | ---: | ---: | ---: |
| 12 reviewed PDF | 79/90 | 55/90 | 31/46 | 0/24 | 0/20 |
| 5 PDF with table labels | 46/46 | 22/46 | 13/20 | 0/24 | 0/20 |
| 3 insufficient-text-warning PDF | 6/15 | 6/15 | 4/9 | N/E | N/E |

All five table-labelled PDFs have status success while all their cell/relationship
checks fail. Present text does not establish structured association, span or locator
correctness. Failed order checks are not automatically demonstrated permutations:
missing or unlocated evidence can also prevent an order check from passing.

For DOCX/XLSX there are no retained full ExtractionResults in the supplied baseline
captures. The machine audit reports their replay scores UNKNOWN, retaining **15/21
anchor totals**, **15/34 provenance totals**, **6/6 order totals**, **7/21 cell totals**,
**3/10 relation totals**, and **13 XLSX value/formula/cache totals**. It does not
re-extract sources or allocate pooled historical failures to individual scenarios.

Separately, the verified published `extraction_fidelity_controls_v1.md` table records
historical DOCX text/provenance **14/15**, order **6/6**, cells **7/7**, relations
**3/3**; XLSX text **21/21**, provenance **34/34**, order **6/6**, cells **21/21**,
relations **10/10**, value/formula/cache equality **13/13 each**. Its source/Gold/code
pins agree with the baseline. Its eleven-source pooled 45/55 text, 54/68 provenance,
16/22 order, 28/32 cells and 13/15 relations remain a separate historical aggregate
in machine output, not nineteen-document scenario measurements.

The historical pilot explicitly identifies **one reviewed omitted DOCX footnote
anchor, 0/1**. Current structural inspection confirms the scenario, while granular
raw-output replay of that DOCX label remains NOT_EVALUATED here. Formula equality
includes only five non-null formula expectations and eight nulls; cache equality
includes six non-null caches and seven nulls. These are not thirteen calculated
or reconstructed formulas. Display fidelity, diagram relations and exhaustive
ancillary-content fidelity remain NOT_EVALUATED.

## OCR evidence reconciliation

Unchanged ML-18 final captures 3/4 and ML-19 captures 1/2 were replayed, not rerun.
All underlying artifact hashes, current parser/scorer/Gold-validator fingerprints,
registration configuration equality, capture source identities, native block
multiplicities, per-anchor recovery/loss and sampled resource/cleanup records were
checked. Per-document scores/statuses match the unchanged scorer and frozen baseline.

| Distinct PDF population | Text baseline -> OCR candidate | Provenance | Order | Cells/relations | Actual OCR pages | Recovered/lost |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| ML-18 pilot 4 | 10/19 -> 19/19 | 6/19 -> 15/19 | 4/10 -> 9/10 | 0/4, 0/2 | 5/50 | 9/0 |
| ML-19 additional 8 | 69/71 -> 69/71 | 49/71 -> 49/71 | 27/36 -> 27/36 | 0/20, 0/18 | 0/34 | 0/0 |
| Descriptive unique 12 | 79/90 -> 88/90 | 55/90 -> 64/90 | 31/46 -> 36/46 | 0/24, 0/20 | 5/84 | 9/0 |

Combined page accounting: 78 native, 5 OCR, 1 blank-render skip. ML-19's 33 native
pages and one blank-render skip imply **zero Tesseract invocations**. It tests
native preservation, not additional OCR recovery or multilingual/numeric OCR
accuracy. Numeric-bearing reviewed anchors are unchanged native evidence (pilot
9/9, expansion 13/13); recovered pilot anchors have no digit-bearing labels.
Repeated runs are verification, never new documents/labels. The pilot's limited
advancement verdict and expansion's INCONCLUSIVE verdict are preserved; neither
grants production authorization. The frozen Docling configuration remains REJECTED.

## Family, split and coverage risks

There are zero duplicate source hashes among 90 verified originals. **10 exact
source-page-URL groups cover 26 documents**; these are possible shared-origin/version
family risks, not proven duplicate documents. URLs and family names are not exported.
All **90 extraction-family identities remain UNKNOWN**; family split crossings are
null/NOT_EVALUATED, not a verified zero. Near-duplicates, translations and complete
version grouping remain NOT_EVALUATED. The earlier data gate's declared retrieval
families do not establish extraction-family assignments; no retrieval TEST was read.
No family-safe split or independent generalization is claimed.

Remaining Gold needs: independent family/version/translation adjudication; reviewed
RU/KK/mixed evidence; explicit PDF subtype/layout metadata; additional DOCX footnote
and other ancillary labels; sparse/large-XML, missing-cache and display cases; and
OCR numeric/units/date/identifier labels with mixed native/image pages. Additions
would need separately authorized reviewed revisions, never silent Gold corrections.

## Prioritized backlog and exactly one recommendation

This ranking is engineering judgment, not a fitted score or measured cost estimate.
It weighs factual loss risk, affected coverage, actual Gold strength, generality,
mechanism certainty and implementation/runtime burden.

| Rank | Gap/work item | Evidence and coverage | Generality/cost assessment |
| --- | --- | --- | --- |
| **1** | **DOCX footnote evidence and ancillary locator contract** | One reviewed omission; 3 baseline warning documents, 16 with structural note elements; only 1 targeted Gold anchor | Direct unsupported boundary, reusable OOXML structure; modest runtime, additive model/scorer work; weak real-label breadth |
| 2 | PDF table/grid provenance and relationships | 5 reviewed sources, 24 cell and 20 relation failures despite 46/46 text | High factual-association risk and stronger labels; native recognition/Gold-grid alignment unresolved, high implementation/validation burden; no justified remapping shortcut |
| 3 | OCR generalization/numeric coverage | 9 recovered pilot anchors; no additional OCR invocation in ML-19 | Existing candidate has narrow evidence; needs reviewed coverage before another engineering change, no threshold tuning justified |
| 4 | Large/sparse XLSX and cache/display coverage | 1 structural inventory UNKNOWN, 3 missing-cache-warning sources with no confirmed-scenario Gold; historical selected equalities pass | Resolve evidence/streaming inventory and labels first; no current parser defect established |
| 5 | Language/family qualification | 90 families UNKNOWN; RU/KK/mixed real reviewed coverage unavailable | Data prerequisite, not evidence for a parser/model replacement |

**Recommend exactly one next extraction improvement:** a separately reviewed offline
DOCX footnote candidate that preserves footnote text and its genuine ancillary
part identity. Do not implement it here. The current `SourceLocation` lacks ancillary
region/part fields, and `_located` rejects non-body locators. Merely appending text
to a body block would misrepresent provenance and would not solve the contract gap.

Baseline: historical DOCX 14/15 required text and provenance, with the supplied
footnote label absent 0/1; selected order 6/6, cells 7/7, relations 3/3. Hypothesis:
bounded generic footnote-part traversal plus explicit ancillary provenance recovers
the missing reviewed evidence without altering native body/table evidence. Proposed
gain gate: footnote presence and reviewed locator 1/1 in both paired repetitions,
DOCX text/provenance 15/15; this is a future target, not a result or generalization
claim. Require independent public synthetic cases with multiple notes, separator
notes, repeated text, links, Unicode and resource failures, followed by separately
reviewed additional real footnote labels before broader advancement.

Guardrails: no body/table/number/order regression, no fabricated body coordinates,
no automatic needs_review -> success transition, all failed/review sources retained,
unchanged source/Gold, bounds on archive/XML/output/RAM/time, and identical paired
quality fields. Likely review surface: extraction models, DOCX parser, observation/
locator adapter and focused tests; the reviewed locator schema already expresses
ancillary regions. Any additive source-contract change requires architectural review.
Keep the candidate offline; rollback disables it and restores the unchanged production
baseline, without rewriting historical captures or frozen Gold. No such change,
candidate implementation or next experiment was started in ML-20.

## Reproducibility and actual verification

Final read-only audit runs are **11/12**, with identical JSON bytes and every
non-runtime field equal. The initial CLI invocation was BLOCKED by a mismatched
initial/final ML-18 registration profile. Development audit runs 1/2 are retained:
review found that the loader still selected an initial ML-18 manifest (41 entries)
instead of the final 82-entry manifest. Both selection bugs were corrected with
synthetic regression tests. Runs 3/4 verified the corrected
selection; runs 5/6 also verified sanitized unsupported-warning counters. Final 7/8 additionally
use allowlisted historical counter fields instead of forwarding captured dictionaries;
a privacy regression verifies that injected extra fields cannot be exported.
Runs 9/10 follow comment/docstring wording corrections during exact-text privacy
review; comparison with 7/8 confirms that only code/fingerprint fields changed. Final 11/12 also suppress Git boundary
stdout/stderr so rejected outside-repository paths cannot appear in diagnostics;
a negative CLI regression verifies both redirection and privacy. No historical
benchmark run/capture was rewritten and no extraction/OCR inference was repeated.
An initial Ruff E501 failure in two new synthetic XML strings was corrected; checks
were rerun. All corrections stayed in the two new Python files.

| Input/output | SHA-256 or canonical fingerprint |
| --- | --- |
| Manifest | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Reviewed Gold 19 bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Reviewed Gold 11 bytes | `30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353` |
| Reviewed Gold 8 bytes | `cde84f713001b1b32e8ac9c5e937a94ffb76b859c2b6255f3102f2b5b8a79636` |
| Frozen baseline metrics 1 | `aad82fe7567b40a6efef187b9cd7473cc417153ff862a6ecb1968f7d1c178f3c` |
| Frozen baseline metrics 2 | `fbb56c327228463d3af5aa2055446860185b5524de53a9a0a5897b31b805ffd4` |
| ML-18 final 82-entry manifest | `4086c46dde4a8e4722720218b84ed876180d701eb7f2e018173339afaf5901ee` |
| ML-19 78-entry manifest | `bf7d429b21b340ef4f8ff9dde9bdbb0f30302e9bf137e7e8480995f3da5136b8` |
| Published per-format controls report | `d3428132e4613144fe58280ca207acee4708262a7225fad0caa14199a54b8878` |
| Audit Python | `95f53ef20151f7f51fdcc933f75e223e05a6a4faa3a05d2fc6b55cdc42563486` |
| Synthetic test Python | `5d481cdde501b6e750d51aa3cbc04cbfa61ce3027cee88b65bfd2e3dc93d6e02` |
| Both final audit canonical fingerprints | `cddfa45cee0518fad31d7cbeb12d5f5b67c3f4de15df7844ab8964cb207281bb` |
| Both final metrics byte hashes | `46bb51c644f3ed4e443767b9d0cd84d233b27c73b639492f7d0bb1058ad4de3f` |

All 90 source hashes/sizes/formats and all license provenance fields were checked;
all manifest license declarations remain Open Government Licence v3.0. This verifies
the frozen provenance, not a new independent legal assessment. Baseline source-map,
parser/model/scorer/Gold-validator hashes, both repetitions and unchanged Gold subset
identity are checked by the tool. Raw private text stays local; exported JSON contains
only fixed counters, status codes and hashes, not original names, URLs or values.

Audit bounds: 90 sources maximum, 32 MiB JSON/capture reads, 20,000 ZIP entries,
16 MiB selected XML entry, 64 MiB selected XML total and compression ratio <=200.
XML DTD/entity declarations, including NUL-interleaved encodings, are rejected as
UNKNOWN inventory; archive failures are not silently treated as absent features.
New outputs must be ignored, outside RAW, absent beforehand and without symlinked
ancestors. Source integrity is checked before/after. A separate psutil wrapper sampled
the audit tree every 0.02 s with 120 s / 768 MiB stop bounds. Actual runs 11/12:
**2.516 / 2.437 s**, peak sampled RSS **101,179,392 / 97,095,680 bytes**. Neither
limit fired; no extraction/OCR subprocess or rendered image was created. The CLI
does invoke Git for its ignored-output check. Sampling
can miss spikes and these are not hostile-input OS sandbox guarantees. No production
resource or throughput improvement is claimed.

Actual commands, from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
$auditArgs = @('tools/extraction_quality/coverage_audit.py',
  '--manifest','docs/eda/corpus_v1_manifest.csv','--corpus','local-corpus',
  '--gold','local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl',
  '--baseline-gold','local-evaluation/extraction_fidelity_v1_controls_reviewed.jsonl',
  '--baseline','evaluation-output/fidelity-controls-v1-approved-run1/metrics.json',
  'evaluation-output/fidelity-controls-v1-approved-run2/metrics.json',
  '--ocr-bundle','evaluation-output/pdf-selective-ocr-v1-20261019',
  '--ocr-bundle','evaluation-output/pdf-selective-ocr-expanded-v1-20261019')
& .venv/Scripts/python.exe -B @auditArgs --output evaluation-output/extraction-coverage-v1/run-11
& .venv/Scripts/python.exe -B @auditArgs --output evaluation-output/extraction-coverage-v1/run-12
& .venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_extraction_coverage_audit.py tests/unit/test_extraction_fidelity.py
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B -c "import sys; sys.path.extend(['src','.venv/Lib/site-packages']); import pytest; raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','tests/unit/test_extraction_coverage_audit.py','tests/unit/test_extraction_fidelity.py','tests/unit/test_extraction.py','tests/unit/test_pdf_ocr_candidate.py','tests/unit/test_docling_candidate.py']))"
& .venv/Scripts/python.exe -B -m ruff check tools/extraction_quality/coverage_audit.py tests/unit/test_extraction_coverage_audit.py
& .venv/Scripts/python.exe -B -m ruff format --check tools/extraction_quality/coverage_audit.py tests/unit/test_extraction_coverage_audit.py
& evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/extraction-coverage-v1/final-verify.py
git diff --check
git status --short
```

The two CLI invocations ran through the monitoring wrapper using these exact argv,
exited 0 and printed PASS plus the fingerprint above. Focused tests: **62 passed in
1.62 s**; broader relevant regressions: **247 passed in 11.13 s**, no skips. Twenty-eight
new synthetic tests are separate from real-source counts. They cover empty/overlapping
labels, unknown metadata, families, failures, all formats, region/numeric facets,
status promotion rejection, ZIP/XML bounds, frozen repetition/profile selection and
privacy. Existing unrelated formatting failures were not fixed or counted as passed.
Ruff returned `All checks passed!`; format --check returned `2 files already formatted`.

Final privacy/scope verification scans all three new files for original basenames,
reviewed answer strings, credentials and absolute private paths; checks UTF-8/LF,
whitespace, immutable source/artifact hashes, report arithmetic and exact allowed
file scope. Full new-file diffs were reviewed separately because ordinary Git diff
does not include untracked files. At the initial handoff, no files were staged,
committed or pushed; that handoff awaited the separately authorized final review.

The final read-only verifier exited 0 and reported:

```text
PASS denominators unique_documents=90 reviewed=19 anchors=126 order=58 cells=52 relations=33 values=13
PASS UNKNOWN_partial_score_null overlap_invariants immutable_artifacts=82,78 no_production_drift
PASS reproducible_bytes resources cleanup all_scratch_ignored staged=0 scope=exactly_three_files
```

`git diff --check` produced no errors. Initial handoff `git status --short --untracked-files=all`:

```text
?? docs/eda/extraction_scenario_coverage_v1.md
?? tests/unit/test_extraction_coverage_audit.py
?? tools/extraction_quality/coverage_audit.py
```

References: [EXP-01: pandas user guide](https://pandas.pydata.org/docs/user_guide/index.html)
provides the missing-data/grouping reference; this tool uses standard-library
aggregation without adding pandas. [EXP-02: GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)
requires non-overlapping groups; no family assignments or split are fabricated here.
[EXP-03: Datasheets for Datasets](https://arxiv.org/abs/1803.09010) motivates documenting
composition, collection, uses and limitations. None establishes measured extraction
quality. Unavailable external policy attachments were not independently inspected.

## Final review, 2026-10-19

Independent review found no critical implementation defect requiring a code change.
Classification uses structural/manifest signals and reviewed label membership,
never document-ID branches or expected answer strings. Missing granular captures
retain UNKNOWN scores; reviewed failed/review outcomes cannot become successes.
The XML entry cap and sampled resource limits remain explicit coverage limitations.
The architectural extraction and data/evaluation boundaries were checked against
sections 7 and 12–14 of the local architecture document; its historical candidate
statements do not supersede later verified offline reports.

Both audits were independently recomputed in memory using `coverage_audit.run`
with the exact frozen inputs in the CLI arguments above. Serializing each result
with sorted keys, indent 2 and a trailing LF reproduced the original run-11 and
run-12 metrics byte hash `46bb51c644f3ed4e443767b9d0cd84d233b27c73b639492f7d0bb1058ad4de3f`.
No original output was overwritten. Review replay elapsed times were 1.313/1.281 s;
peak process-tree RSS sampled every 0.02 s was 93,396,992/93,696,000 bytes. These
are metadata/capture replay resources, not extraction or OCR latency measurements.

The original ML-20 manifest still verifies all **39** pinned audit artifacts;
its SHA-256 is `b79e6fcaba35995a93edc4f2aa7525a35c4a97180f2d949d9955e72b4760b4e4`.
All **82/78** ML-18/19 artifacts, 90 original identities and 8/11/19 reviewed Gold
revisions remain unchanged. Independent subset checks confirmed 8 within 11
within 19, and 139 provenance labels. Format counts, every distinct label
denominator, UNKNOWN/partial-score handling, overlapping membership and historical
versus replayed evidence agree with the report. No new inference occurred.

The focused and broader pytest commands above were rerun: **62 passed in 1.73 s**
and **247 passed in 11.18 s**, respectively, without failures or skips. The exact
read-only `final-verify.py` command above passed again, including privacy, LF/UTF-8,
artifact/source hashes, resource journals and the three-file pre-stage scope.
Ruff again returned `All checks passed!`; format --check returned
`2 files already formatted`. `git diff --check` produced no errors. Unrelated
historical formatting failures were neither fixed nor represented as passing.
Before staging, main remained at the starting HEAD with upstream divergence 0/0.

The remaining commit gate is full staged-diff, exact three-file scope, privacy and
whitespace inspection. Execution PASS remains distinct from extraction readiness
**HOLD**, production authorization **false**, and unavailable independent-test
evidence. The sole future recommendation remains the separately reviewed offline
DOCX footnote/ancillary-locator improvement; it is not implemented in this audit.

Review references: [CODE-07: engineering code review](https://google.github.io/eng-practices/review/reviewer/)
and [TST-02: pytest documentation](https://docs.pytest.org/en/stable/) were consulted
for review and test practices; actual quality claims rest on local verified evidence.
