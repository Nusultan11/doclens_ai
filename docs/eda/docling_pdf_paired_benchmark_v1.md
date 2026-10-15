# Docling PDF paired benchmark v1

## Pre-registration (before inference)

Frozen at 2026-10-15 14:32 UTC, checkout
`d96322ba3a736fee5e8ed60367c336e802d969de`.
Hypothesis: local CPU Docling table/layout extraction may recover reviewed PDF
structure without losing required anchors or regressing the narrative control.
This is an offline experiment, not production promotion or parser tuning.

The unchanged pypdf 6.20.0 baseline and existing Docling 2.55.1 / docling-core
2.48.2 candidate use identical original bytes, approved labels and `score_record`.
The full 90-source corpus is integrity-checked before selecting exactly
`c1-0041`, `c1-0044`, `c1-0045`, `c1-0050`; no failed/review cases are filtered out.
The approved combined eleven-source Gold is unchanged. No labels, thresholds,
candidate code or production configuration may change after observing results.

Acceptance for expanded evaluation requires all of:

- No new required-anchor losses on any evaluated PDF.
- No regression on any reviewed c1-0050 metric.
- No regression on relevant c1-0045 metrics.
- At least one measurable c1-0045 table-cell/span, relationship or provenance gain.
- No uncontained failures, resource-limit violations or fabricated source metadata.
- Full paired completion in both repetitions.

Infrastructure/model problems mean BLOCKED, not quality rejection. Otherwise,
classify ACCEPT_FOR_EXPANDED_EVALUATION, REJECT or INCONCLUSIVE against these
criteria. Unsupported dimensions remain NOT_EVALUATED.

Before inference the existing optional environment and five model artifacts were
found locally. Inventory equals the prior frozen local pin, not a newly chosen
post-result pin. No dependency installation or model download is permitted.
Layout revision: `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`;
table revision: `fc0f2d45e2218ea24bce5045f58a389aed16dc23`.
Artifact inventory fingerprint:
`3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71`.
CPU, two inference threads, serial document execution, FAST tables, cell matching;
OCR, external services/plugins and enrichment disabled. Each fresh paired child
has the existing prepared-run budget of 600 seconds and 3072 MiB monitored process
memory (explicit overrides of CLI defaults), 200 pages, 50 MiB source bytes,
100,000 blocks/cells and 5,000,000 characters. No budget will change during runs.

The worker measures baseline first, then candidate with cold model initialization;
candidate latency is not conversion-only. Peak working set covers the shared paired
child, not independent baseline/candidate peaks. The sampled guard is not a hard OS
sandbox. Repeat into two new ignored output directories, compare every non-runtime
field and deterministic fingerprint, and retain both runtime observations.

ML-1 readiness was rerun before inference: PASS, fingerprint
`b8b10368a897bd45b066ec3b6eb9384484da0a6d869e23bc88656041160d9e75`.
Frozen manifest SHA-256:
`c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0`.
Corpus identity-map fingerprint:
`d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8`.
Gold normalized fingerprint:
`896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c`.
Gold byte SHA-256:
`30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353`.

## Execution and decision

**Execution: PASS. Candidate: ACCEPT_FOR_EXPANDED_EVALUATION.** Both CLI commands
returned exit 0 / evaluated with all four pairs complete (eight paired cases total).
Every pre-registered criterion passed in both runs. No quality decision was made
at pre-registration, and acceptance is only for an expanded offline experiment,
not production adoption. The c1-0050 status downgrade and resource cost remain
explicit caveats; no post-result criterion or threshold was changed to hide them.

### Paired fidelity (identical in both repetitions)

Every cell is baseline -> candidate, passed/evaluated. NE means NOT_EVALUATED,
not a perfect or zero score. Missing counts are required anchors absent globally.

| Source | Required text | Reading order | Table cells/spans | Relationships | Provenance | Missing anchors |
| --- | --- | --- | --- | --- | --- | --- |
| c1-0041 | 0/4 -> 0/4 | 0/3 -> 0/3 | NE | NE | 0/4 -> 0/4 | 4 -> 4 |
| c1-0044 | 0/5 -> 0/5 | 0/2 -> 0/2 | NE | NE | 0/5 -> 0/5 | 5 -> 5 |
| c1-0045 | 6/6 -> 6/6 | 1/2 -> 2/2 | 0/4 -> 4/4 | 0/2 -> 2/2 | 2/6 -> 6/6 | 0 -> 0 |
| c1-0050 | 4/4 -> 4/4 | 3/3 -> 3/3 | NE | NE | 4/4 -> 4/4 | 0 -> 0 |
| Pooled four PDFs | 10/19 -> 10/19 | 4/10 -> 5/10 | 0/4 -> 4/4 | 0/2 -> 2/2 | 6/19 -> 10/19 | 9 -> 9 |

c1-0045 absolute changes: required text +0/6 (0 percentage points); order
+1/2 (+50 pp); table cells +4/4 (+100 pp); relationships +2/2 (+100 pp);
provenance +4/6 (+66.67 pp). All other source-level measured deltas are zero.
Pooled deltas: recall 0 pp, order +10 pp, table cells +100 pp, relationships
+100 pp, provenance +21.05 pp. All four failed baseline table-cell checks now
resolve with their reviewed spans; this does not measure all table cells.

Stored values, formulas, cached values and displayed values are NE (0 supported
labels) for every evaluated PDF. Unreviewed dimensions and the other 86 sources
are not given inferred quality scores. The DOCX/XLSX controls remain frozen but
are not rerun through a PDF-only candidate.

### Status and eligibility

| Source | pypdf | Docling |
| --- | --- | --- |
| c1-0041 | needs_review | needs_review |
| c1-0044 | needs_review | needs_review |
| c1-0045 | success | success |
| c1-0050 | success | needs_review |

Both arms: zero failed extractions, zero error categories, no worker failures,
timeouts or memory-limit events in either repetition. All eight baseline and eight
candidate score objects are present. Original source identities, bytes and sizes
were verified before and after each run; reviewed table/provenance gains use the
unchanged strict scorer, not Gold-dependent manufactured cells or locator fallback.
Candidate status eligibility drops from two successes to one; the c1-0050
reviewed metrics remain perfect but its new needs_review status is a real
operational limitation, not hidden by pooled fidelity gains. No production
gating is relaxed. The frozen acceptance rule concerns reviewed control metrics,
not an assertion of unchanged status/ingestion eligibility.

### Runtime observations

Four serial fresh children per repetition; one baseline and candidate observation
per source per run. Milliseconds below are rounded to three decimals. Candidate
time includes local artifact hashing, imports, cold initialization, conversion,
normalization and source checks; it excludes parent-side corpus hashing and Gold
scoring. Baseline time is `extract_file` only. Parent wall time additionally covers
spawn, both arms, scoring, IPC and monitoring. Their delta is not a pure conversion
speed ratio. Run 1 partially overlapped unit checks; no paired benchmark runs overlap.

| Run | Source | Baseline ms | Candidate ms | Candidate minus baseline ms | Paired wall ms | Paired peak bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | c1-0041 | 4.064 | 24897.315 | 24893.251 | 26144.224 | 2472673280 |
| 1 | c1-0044 | 4.015 | 13797.928 | 13793.913 | 15173.190 | 940077056 |
| 1 | c1-0045 | 2654.402 | 522985.090 | 520330.687 | 527191.431 | 3134619648 |
| 1 | c1-0050 | 1374.634 | 113749.996 | 112375.362 | 116894.038 | 2607857664 |
| 2 | c1-0041 | 5.061 | 19495.286 | 19490.225 | 20925.735 | 2520326144 |
| 2 | c1-0044 | 4.110 | 11639.526 | 11635.416 | 12789.777 | 943325184 |
| 2 | c1-0045 | 2171.556 | 513915.344 | 511743.787 | 517560.793 | 2873638912 |
| 2 | c1-0050 | 1223.353 | 83652.234 | 82428.881 | 86386.488 | 2619277312 |

Sums over four observations, not p50/p95: baseline 4037.115 / 3404.080 ms,
candidate 675430.329 / 628702.390 ms, paired wall 685402.883 / 637662.793 ms
(run 1 / run 2). Largest observed child peak: 3134619648 / 2873638912 bytes
(2989.406 / 2740.516 MiB), below the fixed 3072 MiB guard. Largest paired
wall: 527191.431 / 517560.793 ms, below 600000 ms. These are observations,
not safe production capacity estimates or hard upper bounds.

Memory uses psutil memory_info: Windows peak_wset when present, otherwise sampled
RSS, polled about every 50 ms. It includes both arms in one child and their imports,
not the parent, all system processes or an independently attributed candidate peak.
Independent baseline-only/candidate-only peaks and conversion-only latency are
NOT_EVALUATED. Native allocations are included in the process working-set measure;
sampling and a native-library network guard are not hard OS containment.

### Deterministic comparison

Both deterministic fingerprints:
`6fd9f1f042a3eb73b64dc09128a555d3666f505069673a68a6793dbfffed7a14`.
Full parsed JSON objects with only `runtime` removed are equal, including the
fingerprint field, every per-document extraction fingerprint, score, status,
configuration, code/model hash and dependency version. Recomputing each fingerprint
without `runtime` and the fingerprint field yields the recorded value. This is
stronger than comparing aggregate metrics or the fingerprint strings alone.

Complete metrics byte SHA-256 differs as expected because runtime is retained:

- Run 1: `e4a96c7c51c2c00438f5b942609be96a9fbfb6fd3d5ac724c0a15d89abf431f7`.
- Run 2: `93db2ac1f701a8b2b7794a725c638eda8e7f358cfe1c05f54607c0fbdc5ed3e7`.

All four baseline extraction fingerprints and statuses equal the retained frozen
control evaluation, with the same parser/models/scoring hashes. All eight original
Gold records and their normalized fingerprint remain unchanged:
`14571478ece0193852269c0b6001e616f9f5e32f69d9262e318c128c3b799a9c`.
Determinism is observed on this hardware/environment in two runs, not guaranteed
across dependency versions, CPUs or operating systems. The existing candidate's
initialization/seed behavior was not modified.

## Frozen source and implementation identities

All 90 originals are present with unique identities and hashes: 30 PDF, 30 DOCX,
30 XLSX. The fresh ML-1 report equals the retained verified report field-for-field.
Corpus-wide unchanged baseline status is 56 success, 34 needs_review, zero failed;
all 90 remain in the integrity denominator. Only four reviewed PDFs enter paired
fidelity rates; this is not ninety-document semantic evaluation.

| PDF ID | Bytes | Original SHA-256 |
| --- | ---: | --- |
| c1-0041 | 77333 | `daef7ef6b8dd4200817d1342dfdb480ace0f4a0a3f921165f777ee294bf0485a` |
| c1-0044 | 100551 | `43a961d9f86849a18ddf680a77ed4e4d38dd8f7b4c0e795dc5a51ec9ff255410` |
| c1-0045 | 107597 | `04358ce617249f170d38ea302cbc96a35701987507e61fb87ea2be30da2cfddc` |
| c1-0050 | 461365 | `f1ac87dc692b4e6a48f821a06457e6ee09023ddc83c6e121af60b521d14b9524` |

| Implementation file | SHA-256 |
| --- | --- |
| docling_candidate.py | `aa16ec9e885ed4c99685e6b342b8815f2d628d47431ba4f7d73ae44ea21e6f3c` |
| parsers.py | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| models.py | `0725bb86ebeea07926ab813e91625857fb68e97f3b35e30ecf8d9cb3c7259876` |
| fidelity_eval.py | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| fidelity_gold.py | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |

| Model artifact (public inventory identity) | SHA-256 |
| --- | --- |
| Layout config | `fdea30805ce2f5666b147fca941dcdd27ad468e27d6ed21902207d3da056a97d` |
| Layout preprocessor config | `cd38cd59999e7a95d68e487fbe5132df3d4e5c32a0836add57e6126ba0c4eaf1` |
| Layout weights | `00333a43451945aaf89db8ca9c0a17e75d1537c17db60fdb91aa95f4c7929e0c` |
| Table FAST config | `dca6762508dddfae6d57d6cb4ef822c6000119dff0f3b6489db7413118c2622a` |
| Table FAST weights | `3119563aab5a7c96fda4d621119b63fd8806272b86c30936d15507616422f718` |

Environment: Windows 11 AMD64; Python 3.12.3; 8 physical / 16 logical CPUs,
16,541,597,696 bytes RAM; processor family 25, model 80, stepping 0 (AuthenticAMD).
Optional environment: torch 2.8.0, docling-ibm-models 3.15.0, psutil 7.1.0,
Pydantic 2.14.0. Complete dependency inventory remains in ignored metrics.
The production development environment does not have Docling installed; it is
not modified. Read-only CIM hardware queries were denied by the local runtime;
platform/psutil supplied the reported hardware metadata instead.

## Verification commands and boundaries

Actual commands from repository root (local runtime locations are operational
instructions, not paths to individual private documents):

```powershell
.venv/Scripts/python.exe -m doclens_ai.eda.data_quality_gate --output-dir evaluation-output/docling-paired-v1-readiness-20261015
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
.venv/Scripts/python.exe -m ruff check src tests alembic
$env:PYTHONPATH='src'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
evaluation-output/docling-v1-runtime/Scripts/python.exe -m doclens_ai.extraction.docling_candidate --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_controls_reviewed.jsonl --artifacts evaluation-output/docling-v1-models --artifact-fingerprint 3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71 --timeout-seconds 600 --max-process-mib 3072 --output-dir evaluation-output/docling-paired-v1-20261015-run1
evaluation-output/docling-v1-runtime/Scripts/python.exe -m doclens_ai.extraction.docling_candidate --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_controls_reviewed.jsonl --artifacts evaluation-output/docling-v1-models --artifact-fingerprint 3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71 --timeout-seconds 600 --max-process-mib 3072 --output-dir evaluation-output/docling-paired-v1-20261015-run2
git diff --name-only d96322ba3a736fee5e8ed60367c336e802d969de -- src tests alembic pyproject.toml
git diff --cached --name-only
git diff --check
git status --short
```

Readiness: PASS/exit 0. Candidate plus fidelity regressions: **68 passed** in
3.19 seconds. Full existing unit regressions: **520 passed, 1 skipped** in
24.07 seconds; physical symlink creation requires unavailable Windows privileges.
Ruff: all checks passed. The candidate unit tests use synthetic objects and test
containment/contracts; only the paired real runs provide model-quality evidence.

The first CLI invocation without PYTHONPATH failed before inference with
ModuleNotFoundError for the project package. The optional venv already contained
dependencies but not an installed project package. Scoped PYTHONPATH=src resolved
that execution setup; no installation, source change or output overwrite occurred.
The authoritative repetitions both use the same explicit PYTHONPATH and offline
environment. No user-level settings or runtime model mounts were changed.

Read-only Python stdin assertions validate the strict eleven-record Gold, preserve
the eight-record subset/fingerprint, compare artifact hashes with the previously
frozen inventory, compare the fresh ML-1 report with the prior verified report,
recompute report fingerprints and compare baseline extraction fingerprints/statuses
with the prior control evaluation. No approved bytes or review metadata are edited.

Final read-only assertions rechecked all 90 sources, strict Gold, model inventory,
report code hashes and unchanged Git baseline source content. Both metadata reports
and this Markdown passed privacy checks for original filenames, machine paths,
credential patterns and distinctive approved excerpts; report trees contain no
raw text/question/quote/value/formula, private locator or reviewer-date fields.
Corpus, labels, weights and generated metrics remain ignored. Only this sanitized
Markdown is part of the requested change; production code/tests/dependencies and
previous outputs are unchanged. No service, integration or production E2E claim is
made by this offline benchmark.

## Limitations and next boundary

The extraction-benchmark skill determined the pre-registration, frozen paired
conditions, independent control checks, explicit unsupported dimensions and runtime
scope disclosure. No external documentation query, private upload, dependency
installation or model acquisition was needed.

Only four purposively selected PDFs and one PDF table source have reviewed labels.
The narrative control cannot prove table generalization. Nine required anchors
remain absent in both arms; OCR is disabled and no recovery claim is made for
unobserved text. Human review is the supplied attestation, not a fresh independent
re-review. Literal anchor recall is not semantic fidelity. Whole-document order,
unlabelled cells, rendered appearance, bounding boxes, furniture, pictures, complex
multipage/rich tables and multilingual quality are not established by these scores.
The adapter preserves page-slot block indices and page-local table indices rather
than native Docling item identity; reviewed checks cannot certify every locator.

CPU cost, near-budget peak memory and the c1-0050 status downgrade need explicit
attention before any production consideration. Two local passes do not establish
an SLA, throughput, adversarial safety or memory attribution. There is no evidence
here about chunking, retrieval, citations or RAG quality. No production parser,
ingestion, database, index, retrieval or RAG code is changed or promoted.
