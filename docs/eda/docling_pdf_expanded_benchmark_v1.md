# Expanded Docling PDF benchmark v1

## Pre-registration before inference

Frozen on 2026-10-15, before either expanded candidate invocation, at baseline
`c37eb003ca47439888a915e54a6efb28ee2429a5`. The initial worktree was clean.
Hypothesis: the existing CPU Docling table/layout candidate generalizes beyond
the four previously evaluated PDFs without new anchor losses, fresh eligibility
regressions or degraded reviewed structure/provenance.

Primary population (eight fresh PDFs): c1-0031, c1-0032, c1-0033, c1-0035,
c1-0040, c1-0043, c1-0048, c1-0049. Previously observed controls (four):
c1-0041, c1-0044, c1-0045, c1-0050. Fresh table-labelled PDFs are exactly
c1-0033, c1-0040, c1-0048, c1-0049. No source may be replaced, dropped or
selected using candidate outcomes. Both arms use identical frozen bytes/labels
and the unchanged extraction contract and scorer. All 90 originals are verified
before selecting the twelve PDF records and again after processing.

Acceptance for **ACCEPT_FOR_FURTHER_OFFLINE_ENGINEERING** requires all of:

1. No required anchor present in paired pypdf becomes absent in Docling, on any
   of the twelve PDFs. Compare per-anchor presence, not only aggregate counts;
   a new found anchor cannot cancel a newly lost one. Failed/unknown evidence
   cannot establish this criterion.
2. No reviewed-metric degradation on the four controls versus both paired pypdf
   and the frozen previous Docling control expectations. Historical c1-0050
   success-to-needs_review is separately unresolved, never production acceptance.
3. No new success-to-needs_review or success-to-failed transition among the eight
   fresh PDFs, comparing the paired extraction statuses.
4. At least two of the four newly table-labelled PDFs measurably improve a
   table-cell/span, relationship or provenance count versus paired pypdf.
5. No fresh per-document regression in table relationships, cell/spans, reading
   order or provenance. Zero-label dimensions remain NOT_EVALUATED.
6. Complete paired observations in both repetitions, without uncontained
   infrastructure failures. Controlled document failures/resource limits remain
   measured outcomes with full Gold denominators and unknown scores explicit;
   they are not silently excluded or automatically called infrastructure absence.

An observed violation supports REJECT; insufficient/unknown or non-reproducible
evidence supports INCONCLUSIVE. Missing essential artifacts/infrastructure means
BLOCKED, not model-quality rejection. Production promotion is not an available
decision. No criterion, label, threshold or inference parameter may be tuned
after results. Every non-runtime report field must be compared between runs.

## Frozen implementation, inputs and resources

The runner defaults to legacy-v1: eleven approved records, four original PDFs,
same extraction/scoring and report shape. Explicit expanded-v1 pins nineteen
approved records and all twelve PDFs, separates fresh/control populations, and
adds only privacy-safe warning counts, status eligibility, per-anchor presence
booleans and label denominators. Both profiles reject unknown/snapshot-mismatched
inputs and duplicate JSON keys before inference. No label text or locators enter
the metadata report. A monitored timeout/memory limit after a baseline observation
is a measured unsuccessful expanded attempt; missing candidate scores stay null.
Legacy CLI resource-failure classification and default budgets are unchanged.

Preflight verified strict nineteen-record Gold, duplicate-key guard, all ninety
source identities and identical local model inventory/revision pins. No dependency
install, model download or external inference is permitted.

| Identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Ninety-source identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Twelve selected source identities | `ec69b55db7e66298e509c51632432d60b861c7b76845a631ea7f60f6d4cddf68` |
| Eight fresh source identities | `4a856010bd8307f1d150916b63ab689d1792b92ac7128faf6a410895c343ad85` |
| Four control source identities | `d9404bd6b7fc67bf7d65c2747f4fe69f25774b529368b5543d02f3654afd522e` |
| Expanded Gold bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Expanded normalized Gold | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Legacy Gold bytes | `30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353` |
| Legacy normalized Gold | `896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c` |
| Existing five-file model inventory | `3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71` |
| Frozen modified candidate runner | `68c15cabb65f48c26fc531d0efb91900bf6ad5e9beaa9228fcf4005709b81b23` |
| Frozen candidate tests | `23d130cc70a1f655994b3311bafba16dbb78deffd9cdbb119f10020c4f7f81ed` |
| Unchanged pypdf parser | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| Unchanged extraction models | `0725bb86ebeea07926ab813e91625857fb68e97f3b35e30ecf8d9cb3c7259876` |
| Unchanged scorer/corpus verifier | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Unchanged Fidelity Gold validator | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |

Docling 2.55.1, docling-core 2.48.2, docling-ibm-models 3.15.0, torch 2.8.0,
pypdf 6.20.0, psutil 7.1.0; Windows Python 3.12.3. Existing optional environment,
not the production dependency set. Layout revision
`8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`; table revision
`fc0f2d45e2218ea24bce5045f58a389aed16dc23`. Local files match the previous
benchmark inventory byte-for-byte. Full public artifact hashes are retained in
ignored metrics; no weights enter Git.

Unchanged prepared configuration: CPU, two threads, FAST tables, cell matching;
OCR, enrichment, external services and plugins disabled. Exactly 600 seconds
per paired worker and 3072 MiB monitored process memory, 200 PDF pages, 50 MiB
source size, 100000 blocks/cells and 5000000 characters. No budget increase on
failure. Serial fresh child per document, baseline first, cold candidate second.
Candidate time includes initialization; measured peak belongs to the paired
child, not independently attributed baseline/candidate peaks. Sampled working-set
monitoring is not a hard OS security sandbox or a throughput/SLA benchmark.

Read-only AST comparison with the baseline HEAD confirms unchanged CandidateConfig defaults,
converter/options, normalizer, extract_candidate, offline guard and artifact
inventory. Focused final tests: 105 passed; complete unit suite: 557 passed,
1 skipped (Windows symlink privilege). Ruff and changed-Python formatting passed
before inference. Real runs will use two new ignored output directories, with
no overlapping benchmark repetitions or unit-test load.

## Execution and decision

**Execution: PASS. Candidate quality: REJECT.** Both real expanded CLI commands
returned exit 0 / evaluated, with twelve complete paired observations per run.
All non-runtime fields match exactly, including every per-anchor presence map,
score, warning/status/eligibility field, extraction fingerprint and frozen identity.
There were zero extraction failures, timeouts, memory-limit events or infrastructure
failures in either run. No required source or score was excluded.

The candidate violates pre-registered no-new-anchor-loss, fresh eligibility and
fresh structure/provenance non-regression criteria. Table gains on three fresh
sources do not override those failures. No criterion or parameter was changed;
no tuning or production promotion follows from this result. At pre-registration
there was no expanded quality conclusion; the decision follows the two measured
repetitions below.

## Verification and interpretation contract

Actual pre-inference commands from repository root:

```powershell
git rev-parse HEAD
git status --short
.venv/Scripts/python.exe -m ruff check src tests alembic
.venv/Scripts/python.exe -m ruff format --check src/doclens_ai/extraction/docling_candidate.py tests/unit/test_docling_candidate.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
git diff --check
```

Final focused result: 105 passed in 7.64 s. Full unit suite: 557 passed,
1 skipped in 20.80 s (physical Windows symlink privilege unavailable). Earlier
test iterations preceded the added per-anchor swap/failure tests; the reported
final runs include them. Ruff/formatting: PASS. No Python code will change between
the two benchmark runs. Synthetic tests never serve as real corpus results.

The regression suite exercises both profiles, exact memberships and label counts,
default-vs-explicit legacy equivalence, byte/normalized Gold pins, malformed/draft
and duplicate-key inputs, missing/changed sources, post-run mutation, unknown
profiles, worker limits/failure isolation, opaque anchor swaps at equal recall
counts, warning/status metadata and no raw-content output. The actual legacy
default remains 180 seconds/2048 MiB; only the reproducible benchmark commands
explicitly request the prepared 600-second/3072-MiB configuration.

The earlier frozen four-control report is the regression reference. Its expected
candidate required-text/order/table/relationship/provenance numerators are:
c1-0041 = 0/0/NE/NE/0; c1-0044 = 0/0/NE/NE/0;
c1-0045 = 6/2/4/2/6; c1-0050 = 4/3/NE/NE/4. Their denominators remain
4/3/NE/NE/4, 5/2/NE/NE/5, 6/2/4/2/6 and 4/3/NE/NE/4, respectively.
Compare full score objects and extraction fingerprints with that reference,
not whole report fingerprints across different runner/Gold versions.

For failed or absent candidate observations, scores and missing-anchor counts
remain unknown, not manufactured zeroes. Every document and its required-label
denominators remain in population totals. Aggregates must distinguish known
passed/evaluated labels from unresolved labels rather than silently averaging
only successful cases. Known missing anchors are separate from unknown coverage.
All per-anchor identity comparisons use metadata booleans built from the existing
observation/whitespace helpers, checked against unchanged score_record counters.

Human labels are supplied attestations, not a new independent review in this step.
Purposive twelve-PDF coverage does not establish whole-corpus fidelity, multilingual
quality, complete family independence, near-duplicate absence or table generalization
beyond reviewed checks. Diagram semantics, checkbox behaviour, display fidelity,
unlabelled regions, rich/multipage tables and bounding boxes remain unsupported or
NOT_EVALUATED. Status eligibility is only success-based offline gating, not proof
of production ingestion or search readiness. No retrieval/RAG claim is supported.

The extraction-benchmark skill determined frozen paired conditions, failure-inclusive
denominators, explicit runtime scope and conservative advancement. No external
documentation or private upload was needed; existing implementation and pinned
local APIs remain the authority.

Hardware observed locally: Windows 11 AMD64, processor family 25/model 80/stepping 0
(AuthenticAMD), 8 physical and 16 logical CPUs, 16541597696 bytes system RAM. This
is a shared desktop, not a dedicated throughput environment. Peak measurement is
psutil Windows peak_wset, polled around 50 ms; parent and independent arm peaks
are not measured. Gold denominators are fresh 71/36/20/18 and controls 19/10/4/2
for anchors/order/cells/relationships. PDF provenance denominators equal anchors.
Stored values, formulas, caches and displayed-value fidelity have zero labels here
and remain NOT_EVALUATED in both populations.

The first actual expanded invocation uses the existing optional environment and
scoped offline variables (the project package is exposed through PYTHONPATH, not
installed or rebuilt):

```powershell
$env:PYTHONPATH='src'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
evaluation-output/docling-v1-runtime/Scripts/python.exe -m doclens_ai.extraction.docling_candidate --profile expanded-v1 --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --artifacts evaluation-output/docling-v1-models --artifact-fingerprint 3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71 --timeout-seconds 600 --max-process-mib 3072 --output-dir evaluation-output/docling-expanded-v1-20261015-run1
```

The second actual invocation used the same scoped variables and changed only
the new output directory; no previous results were overwritten:

```powershell
evaluation-output/docling-v1-runtime/Scripts/python.exe -m doclens_ai.extraction.docling_candidate --profile expanded-v1 --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --artifacts evaluation-output/docling-v1-models --artifact-fingerprint 3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71 --timeout-seconds 600 --max-process-mib 3072 --output-dir evaluation-output/docling-expanded-v1-20261015-run2
```

Both commands returned exit 0, evaluated, twelve PDFs. Runtime observations from
both repetitions are retained below; no timing or memory value is substituted.

## Paired results (identical in both repetitions)

All twelve pairs per repetition completed with returned extraction scores, zero
failed extractions, zero error categories, zero timeouts and zero memory-limit
events. Eight fresh PDFs and four controls remain fully included in each run.
These per-document and population results are equal across both repetitions.

### Primary fresh PDFs

Baseline -> Docling, passed/evaluated. NE is a zero-label dimension, not 0% or
100%. New losses count baseline-present opaque anchors that become absent;
missing is the total absent required evidence, not only new losses.

| ID | Recall | Order | Cells/spans | Relationships | Provenance | Missing | New losses |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| c1-0031 | 7/7 -> 7/7 | 4/5 -> 4/5 | NE -> NE | NE -> NE | 7/7 -> 7/7 | 0 -> 0 | 0 |
| c1-0032 | 10/10 -> 1/10 | 3/4 -> 0/4 | NE -> NE | NE -> NE | 10/10 -> 1/10 | 0 -> 9 | 9 |
| c1-0033 | 9/9 -> 9/9 | 0/3 -> 3/3 | 0/8 -> 8/8 | 0/8 -> 8/8 | 1/9 -> 9/9 | 0 -> 0 | 0 |
| c1-0035 | 6/8 -> 7/8 | 4/5 -> 5/5 | NE -> NE | NE -> NE | 6/8 -> 7/8 | 2 -> 1 | 0 |
| c1-0040 | 8/8 -> 8/8 | 2/3 -> 2/3 | 0/4 -> 0/4 | 0/4 -> 0/4 | 4/8 -> 4/8 | 0 -> 0 | 0 |
| c1-0043 | 6/6 -> 0/6 | 4/4 -> 0/4 | NE -> NE | NE -> NE | 6/6 -> 0/6 | 0 -> 6 | 6 |
| c1-0048 | 11/11 -> 11/11 | 6/6 -> 6/6 | 0/3 -> 3/3 | 0/1 -> 1/1 | 8/11 -> 11/11 | 0 -> 0 | 0 |
| c1-0049 | 12/12 -> 11/12 | 4/6 -> 3/6 | 0/5 -> 5/5 | 0/5 -> 5/5 | 7/12 -> 11/12 | 0 -> 1 | 1 |

| Aggregate metric | Baseline | Docling | Absolute passed-count delta | Percentage-point delta |
| --- | --- | --- | ---: | ---: |
| required_text_recall | 69/71 | 54/71 | -15 | -21.13 |
| reading_order | 27/36 | 23/36 | -4 | -11.11 |
| table_cells | 0/20 | 16/20 | +16 | 80.00 |
| table_relationships | 0/18 | 14/18 | +14 | 77.78 |
| provenance | 49/71 | 50/71 | +1 | 1.41 |

Known missing anchors: 2 -> 17; newly lost 16, newly found 1.
No failed or unknown-label population is omitted from these totals in either run.

### Separate historical controls

Baseline -> Docling, passed/evaluated. NE is a zero-label dimension, not 0% or
100%. New losses count baseline-present opaque anchors that become absent;
missing is the total absent required evidence, not only new losses.

| ID | Recall | Order | Cells/spans | Relationships | Provenance | Missing | New losses |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| c1-0041 | 0/4 -> 0/4 | 0/3 -> 0/3 | NE -> NE | NE -> NE | 0/4 -> 0/4 | 4 -> 4 | 0 |
| c1-0044 | 0/5 -> 0/5 | 0/2 -> 0/2 | NE -> NE | NE -> NE | 0/5 -> 0/5 | 5 -> 5 | 0 |
| c1-0045 | 6/6 -> 6/6 | 1/2 -> 2/2 | 0/4 -> 4/4 | 0/2 -> 2/2 | 2/6 -> 6/6 | 0 -> 0 | 0 |
| c1-0050 | 4/4 -> 4/4 | 3/3 -> 3/3 | NE -> NE | NE -> NE | 4/4 -> 4/4 | 0 -> 0 | 0 |

| Aggregate metric | Baseline | Docling | Absolute passed-count delta | Percentage-point delta |
| --- | --- | --- | ---: | ---: |
| required_text_recall | 10/19 | 10/19 | +0 | 0.00 |
| reading_order | 4/10 | 5/10 | +1 | 10.00 |
| table_cells | 0/4 | 4/4 | +4 | 100.00 |
| table_relationships | 0/2 | 2/2 | +2 | 100.00 |
| provenance | 6/19 | 10/19 | +4 | 21.05 |

Known missing anchors: 9 -> 9; newly lost 0, newly found 0.
No failed or unknown-label population is omitted from these totals in either run.

### Status, warnings and eligibility

S = success (eligible_by_status=true); R = needs_review (false). No failed status
occurred. T = pdf_table_structure_not_preserved, I = insufficient_text,
D = drawings_not_extracted. Counts are contract-warning occurrences, not a capture
of all suppressed third-party logs. Blank warning sets mean no contract warnings.

| Population | ID | Baseline -> Docling status | Baseline warnings | Docling warnings |
| --- | --- | --- | --- | --- |
| fresh | c1-0031 | S -> S | T:1 | None |
| fresh | c1-0032 | S -> R | T:1 | D:2 |
| fresh | c1-0033 | S -> S | T:1 | None |
| fresh | c1-0035 | S -> S | T:1 | None |
| fresh | c1-0040 | S -> S | T:1 | None |
| fresh | c1-0043 | R -> S | I:1, T:1 | None |
| fresh | c1-0048 | S -> R | T:1 | D:3 |
| fresh | c1-0049 | S -> S | T:1 | None |
| control | c1-0041 | R -> R | I:4, T:1 | D:3, I:1 |
| control | c1-0044 | R -> R | I:1, T:1 | D:1, I:1 |
| control | c1-0045 | S -> S | T:1 | None |
| control | c1-0050 | S -> R | T:1 | D:15 |

Fresh eligibility is 7/8 -> 6/8, but that net count hides two degradations
(c1-0032, c1-0048) and one apparent upgrade (c1-0043). On c1-0043, candidate
success coexists with 0/6 required anchors and 0/6 provenance: status is NOT
fidelity. Historical controls are 2/4 -> 1/4, entirely the known c1-0050 regression.
The latter retains perfect reviewed narrative scores but fifteen drawing warnings;
it is still an unresolved production concern.

### Failure and gate analysis (both repetitions)

- No-new-anchor-loss gate fails: c1-0032 loses 9, c1-0043 loses 6, c1-0049 loses 1.
  The one newly found c1-0035 anchor cannot compensate for these sixteen losses.
- Fresh eligibility gate fails on c1-0032 and c1-0048.
- Fresh no-regression gate fails: reading order loses three reviewed pairs on
  c1-0032 (four labels), four on c1-0043 (four labels), and one on c1-0049
  (six labels). Provenance loses nine of ten and six of six checks on the first
  two. Pooled provenance increases by one despite those source regressions.
- Table-improvement gate passes on 3/4 newly labelled sources: c1-0033, c1-0048,
  c1-0049. c1-0040 stays at 0/4 cells, 0/4 relationships and 4/8 provenance.
- All control full score objects, statuses, error categories and extraction
  fingerprints match the previous frozen four-PDF evaluation in both arms.
  All twelve baseline extraction fingerprints/statuses equal the frozen
  ninety-source baseline. Legacy measured expectations are preserved in both runs.
- Execution observations are complete, with no resource or infrastructure failure.

The measured gains do not offset the pre-registered failures: final quality
classification is REJECT, supported by identical second-run outcomes, not tuning.
The c1-0032 drawing warnings are consistent with omitted diagram content, but this
experiment does not independently diagnose every missing anchor. No causal claim
about c1-0043 font/language/segmentation is inferred from aggregate metrics alone.
A focused future error analysis would need original/unit comparisons under new
explicit scope; OCR, parser repair or label adjustment is not implemented here.

## Runtime measurements: repetition 1

Each row is one paired child. Times are milliseconds, rounded to three decimals;
peak is paired-process peak working set in bytes. Delta = candidate minus baseline.
Initialization/imports/artifact hashing are included in candidate extraction time;
scoring, metadata instrumentation, process startup and IPC additionally affect paired
wall time. No independent baseline/candidate memory peaks or conversion-only time
are available. No unit tests overlapped either benchmark repetition.

### Run 1 fresh population

| ID | Baseline ms | Candidate ms | Delta ms | Paired wall ms | Paired peak bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1-0031 | 4.856 | 16470.181 | 16465.326 | 17642.903 | 941514752 |
| c1-0032 | 61.821 | 11496.151 | 11434.330 | 12756.298 | 943570944 |
| c1-0033 | 28.275 | 13878.350 | 13850.075 | 15019.575 | 967647232 |
| c1-0035 | 34.950 | 11339.158 | 11304.207 | 12435.500 | 949018624 |
| c1-0040 | 36.024 | 29441.432 | 29405.408 | 30661.856 | 1008484352 |
| c1-0043 | 128.884 | 20567.206 | 20438.322 | 22391.173 | 1990070272 |
| c1-0048 | 439.891 | 47072.663 | 46632.772 | 49151.628 | 2594955264 |
| c1-0049 | 515.782 | 33781.823 | 33266.040 | 35541.362 | 2583289856 |

Sums, not percentile statistics: baseline 1250.483 ms,
candidate 184046.963 ms, paired wall 195600.293 ms;
maximum paired peak 2594955264 bytes (2474.742 MiB).

### Run 1 control population

| ID | Baseline ms | Candidate ms | Delta ms | Paired wall ms | Paired peak bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1-0041 | 4.201 | 19955.014 | 19950.813 | 21201.620 | 2128785408 |
| c1-0044 | 4.095 | 12735.380 | 12731.285 | 14082.366 | 942653440 |
| c1-0045 | 2251.598 | 541845.103 | 539593.504 | 545727.645 | 2872725504 |
| c1-0050 | 1313.537 | 80576.068 | 79262.531 | 83166.064 | 2619531264 |

Sums, not percentile statistics: baseline 3573.432 ms,
candidate 655111.565 ms, paired wall 664177.696 ms;
maximum paired peak 2872725504 bytes (2739.645 MiB).

### Model file verification

The unchanged local inventory has the following public model artifact SHA-256s.
Model revisions and aggregate inventory pin were frozen before inference.

| Public artifact identity | SHA-256 |
| --- | --- |
| ds4sd--docling-layout-heron/config.json | `fdea30805ce2f5666b147fca941dcdd27ad468e27d6ed21902207d3da056a97d` |
| ds4sd--docling-layout-heron/model.safetensors | `00333a43451945aaf89db8ca9c0a17e75d1537c17db60fdb91aa95f4c7929e0c` |
| ds4sd--docling-layout-heron/preprocessor_config.json | `cd38cd59999e7a95d68e487fbe5132df3d4e5c32a0836add57e6126ba0c4eaf1` |
| ds4sd--docling-models/model_artifacts/tableformer/fast/tableformer_fast.safetensors | `3119563aab5a7c96fda4d621119b63fd8806272b86c30936d15507616422f718` |
| ds4sd--docling-models/model_artifacts/tableformer/fast/tm_config.json | `dca6762508dddfae6d57d6cb4ef822c6000119dff0f3b6489db7413118c2622a` |

## Runtime measurements: repetition 2

Same definitions, units, process scope and budgets as repetition 1. These values
are observed runtime differences, not changed inputs or a throughput improvement.

### Run 2 fresh population

| ID | Baseline ms | Candidate ms | Delta ms | Paired wall ms | Paired peak bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1-0031 | 5.530 | 11949.044 | 11943.514 | 13003.987 | 942546944 |
| c1-0032 | 60.136 | 11332.686 | 11272.550 | 12457.994 | 944263168 |
| c1-0033 | 28.770 | 13549.289 | 13520.520 | 14678.284 | 968290304 |
| c1-0035 | 31.626 | 11098.376 | 11066.750 | 12233.945 | 948977664 |
| c1-0040 | 38.781 | 29497.516 | 29458.735 | 30704.556 | 1008328704 |
| c1-0043 | 113.180 | 16750.462 | 16637.281 | 18303.063 | 2524192768 |
| c1-0048 | 441.419 | 46385.049 | 45943.630 | 48542.886 | 2595135488 |
| c1-0049 | 550.401 | 33065.912 | 32515.511 | 34848.586 | 2582532096 |

Sums: baseline 1269.844 ms, candidate 173628.334 ms,
paired wall 184773.301 ms; maximum paired peak 2595135488 bytes
(2474.914 MiB).

### Run 2 control population

| ID | Baseline ms | Candidate ms | Delta ms | Paired wall ms | Paired peak bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| c1-0041 | 4.175 | 17257.156 | 17252.980 | 18477.560 | 2519896064 |
| c1-0044 | 3.704 | 11302.430 | 11298.726 | 12465.029 | 943603712 |
| c1-0045 | 2226.604 | 506161.104 | 503934.500 | 510095.207 | 3063615488 |
| c1-0050 | 1238.103 | 81346.275 | 80108.173 | 83821.812 | 2619305984 |

Sums: baseline 3472.587 ms, candidate 616066.966 ms,
paired wall 624859.609 ms; maximum paired peak 3063615488 bytes
(2921.691 MiB).

## Reproducibility, final verification and decision

Run 1 deterministic fingerprint:
`d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24`.
Run 2 deterministic fingerprint:
`d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24`.

Parsed reports with only runtime removed are field-for-field identical, including
the stored deterministic fingerprint. Independently recomputing each fingerprint
without runtime and the fingerprint field gives the same value. All twelve baseline
extraction fingerprints/statuses equal the frozen ninety-source reference; the
four controls' scores/status/error categories/extraction fingerprints match the
previous four-PDF reference for BOTH arms in BOTH repetitions. Actual legacy and
expanded Gold inputs also pass their respective profile pins and strict contracts.

Full metrics file SHA-256s (different because runtime is retained):

- Run 1: `dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48`.
- Run 2: `3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a`.

| Pre-registered advancement gate | Measured outcome in both runs |
| --- | --- |
| No newly missing anchors | FAIL: 16 new losses; 1 separate gain |
| Control reviewed metrics preserved | PASS: full prior control scores/fingerprints preserved |
| No fresh success eligibility downgrade | FAIL: c1-0032 and c1-0048 |
| Table-related gains in at least 2/4 new table sources | PASS: 3/4 |
| No fresh order/cell/relationship/provenance regression | FAIL: order/provenance regressions on c1-0032/0043 and order regression on c1-0049 |
| Complete pairs without uncontained infrastructure failure | PASS: 12/12 in each run, no failures or resource events |
| Identical non-runtime results | PASS: every field equal |

**Final candidate decision: REJECT under this frozen candidate/configuration and
advancement gate.** This is a reproducible negative experiment, not an infrastructure
blocker or a claim that Docling can never be useful. No production adoption and
no automatic repair/tuning follow. The known c1-0050 eligibility regression remains
separately unresolved, even though its reviewed scores and prior candidate output
are unchanged. No fresh-set failure is hidden in a pooled twelve-PDF conclusion.

Post-run Python stdin audits use the existing strict loaders/duplicate-key guard,
corpus verifier, artifact inventory and fingerprint functions. They recheck all
ninety originals, both Gold byte/normalized pins, all nineteen approved records,
twelve/fresh-eight/control-four memberships, every label denominator, per-anchor
score agreement, exact configuration/model hashes, unchanged scorer/parser/model
source hashes and the frozen modified runner hash. AST comparisons confirm that
converter options, normalization, extractor, CandidateConfig defaults, offline guard
and artifact inventory did not change. No production file outside the allowed
runner changed. Synthetic tests separately cover controlled failures; real runs
have no failed/unknown metric population and no runtime-limit event.

Final diff/privacy review includes only the runner, its test file and this
sanitized Markdown. Private originals, Gold, model files and generated metrics
remain ignored. Metadata reports contain no source text, private filenames/paths,
worksheet names, cell values, quotes or reviewer identities. Only opaque anchor
presence booleans were added for loss accounting; raw Gold evidence is never
serialized. No separate memory peaks, semantic superiority or RAG-quality claim
is made. Existing display/value/formula/cache dimensions remain NOT_EVALUATED
for these PDF-only observations.
