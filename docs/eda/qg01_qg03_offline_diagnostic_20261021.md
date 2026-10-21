# Native Extraction → Cleaning → Chunking diagnostic

Engineering execution: **PASS**, at HEAD
`aa8e9a40ab2b6c89b512221452dccce7ca5fd4b3`, branch `main`.
This is a measurement of unchanged native algorithms, not optimization or release
qualification. The existing data-quality gate returns **FIX** for six native
extraction failures. No QG is declared PASS.

| Quality boundary | Verdict in this diagnostic |
| --- | --- |
| QG-01 legacy labelled checks | **FAIL in the measured scope**: missing required text, order and structured evidence; independent comprehensive qualification remains unavailable |
| QG-02 | **NOT_EVALUATED overall**; captured non-whitespace preservation and supported TextBlock mapping checks pass |
| QG-03 | **NOT_EVALUATED overall**; conditional character coverage and explicitly defined legacy evidence co-retention are measured below |

## Inputs, permission and label coverage

The [fidelity protocol](extraction_fidelity_protocol_v1.md),
[ML-DATA/ML-CHUNK](../../DocLens_AI_ML_Quality_Strategy.md#ML-CHUNK),
[Extraction Strategy](../../DocLens_AI_Extraction_Strategy.md#EX-ARCH) and
[QG-01–03](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES)
govern interpretation. Extraction-benchmark, data-quality and ML-experiment skills
were applied. No parser, cleaner, chunker, Gold, threshold or existing report changed.

All **90/90 originals**, 30 per format, matched the frozen SHA-256/size/extension
map before and after both final runs. No missing, extra, duplicate or substituted
original was accepted. The existing strict Corpus v2 control manifest also audited
90/90 as admitted/native-eligible for local evaluation, with zero declared split
leakage, zero independent Gold and family completeness **NOT_EVALUATED**.

The acquisition protocol records OGL v3.0 declarations and attribution for all 90
rows. Each row has source/publisher/licence-basis references. The retained control
rights records explicitly authorize `local_evaluation=true`, public sensitivity,
and development split for 90/90. Their annotation-use and redistribution fields
are null; those permissions are **not inferred**. This run only reads existing
documents/legacy labels locally. It creates no new source annotations, approvals
or redistribution. Source-specific QG-00 annotation-use decisions, including the
blocked candidate, remain unchanged. Publisher terms were not fetched again.

| Frozen identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Corpus v1 manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| 90-source identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Expanded Gold bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Expanded Gold normalized | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Gate's unchanged 11-record Gold bytes | `30cfdcf31f1036f1e6f813fad34266fa347b5368ee140be7304eb942f0e0d353` |
| Gate's unchanged normalized Gold | `896ce2c0e99b74683a8b15869c7ab72b94a27dd06fce66896db4ec8652c75b6c` |
| Retained local-evaluation rights manifest bytes | `d90b343a648bd9b73f193914329e22291b4a77d5290264159742cf4ec2414a08` |

Gold schema `1.0`, dataset revision `corpus-v1-fidelity-v1`, contains **19 real
legacy reviewed attestations**, each declaring original-document review. Strict
schema/source validation and the duplicate-key guard pass; these do not establish
independent reviewer activity. All 11 gate records equal their expanded-set records.
No machine-assisted QG-00 proposal or synthetic label enters these measurements.

| Format | Corpus | Gold-labelled | Without Gold | Labelled with nonfailed extraction | Labelled/default-chunked |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF | 30 | 12 | 18 | 12 | 9 |
| DOCX | 30 | 3 | 27 | 3 | 1 |
| XLSX | 30 | 4 | 26 | 2 | 1 |
| All | 90 | 19 | 71 | 17 | 11 |

Exact uncovered opaque IDs are retained in each private diagnostic's format
slices. The manifest declares 88 EN / 2 CY documents; reviewed coverage is 18 EN /
1 CY. RU/KK, family completeness, exhaustive text/number correctness, independent
spatial locator precision, header/value/unit/period semantics and displayed XLSX
fidelity are **NOT_EVALUATED**. This is an exposed development corpus, not sealed test.

## Current native extraction

Each final run invokes native extraction exactly **90 times**, serially, without
candidate parsers. The evaluator captures each unchanged result. Cleaning, both
chunkers and the data-quality gate reuse those same in-memory results; no later
stage reparses a document. Captures are fingerprinted before/after downstream work.

| Format | Attempted | Success/default eligible | Needs review | Failed | Fixed / structure-aware chunks |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF | 30 | 27 | 3 | 0 | 284 / 325 |
| DOCX | 30 | 11 | 19 | 0 | 33 / 41 |
| XLSX | 30 | 13 | 11 | 6 | 1,476 / 1,689 |
| All | 90 | 51 | 33 | 6 | 1,793 / 2,055 |

Six XLSX inputs return `corrupt_document`: c1-0063, c1-0067, c1-0070, c1-0081,
c1-0084 and c1-0085. Two, c1-0067 and c1-0081, have Gold. Rejection is recorded
without repairing inputs or assuming that historical success was safe/correct.
All failures and holds stay in the 90-source denominator. `success` is not fidelity.

Below, cells are **passed / expected** assertions. The unchanged fidelity scorer
counts empty failed outputs against full expected label totals. A separate
nonfailed-output column makes the unobserved population explicit, rather than
treating failed-document content as observed incorrect text. NE is a null score.

| Metric | PDF | DOCX | XLSX | All expected | Observed nonfailed only | Unobserved labels |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Required text | 79/90 | 15/15 | 10/21 | 104/126 | 104/115 | 11 |
| Partial reading order | 31/46 | 6/6 | 4/6 | 41/58 | 41/56 | 2 |
| Table cell/span | 0/24 | 7/7 | 10/21 | 17/52 | 17/41 | 11 |
| Same-row/column relationships | 0/20 | 3/3 | 6/10 | 9/33 | 9/29 | 4 |
| Provenance | 55/90 | 14/15 | 17/34 | 86/139 | 86/122 | 17 |
| Exact stored values | NE | NE | 7/13 | 7/13 | 7/7 | 6 |
| Exact formulas, including null | NE | NE | 7/13 | 7/13 | 7/7 | 6 |
| Exact caches, including null | NE | NE | 7/13 | 7/13 | 7/7 | 6 |
| Displayed values | NE | NE | NE | NE | NE | 0 requested |

There are **22 unmatched required anchors in the full expected denominator**:
11 missing from nonfailed observations plus 11 unobserved on failed sources.
Among nonfailed outputs, 104 anchors have global text presence, but only 79 resolve
at the frozen expected locator. There are no native PDF structured table outputs
that satisfy the 24 reviewed cell/span assertions. One present DOCX ancillary
anchor cannot be resolved by the frozen scorer's body-only locator semantics.

All 13 stored-value labels are non-null. The five non-null formula expectations
and six non-null cache expectations are **all unobserved in failed sources**.
The seven observed formula and cache expectations are all null. Consequently,
7/7 observed equality does not demonstrate formula/cache recovery or calculation.

| Disjoint labelled cohort | Sources: success / review / failed | Required text | Order | Cells/spans | Relationships | Provenance |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Original eight difficult priorities | 1 / 5 / 2 | 24/44 | 6/14 | 13/28 | 5/11 | 22/53 |
| Three approved regression controls | 3 / 0 / 0 | 11/11 | 8/8 | 4/4 | 4/4 | 15/15 |
| Eight expanded PDFs | 7 / 1 / 0 | 69/71 | 27/36 | 0/20 | 0/18 | 49/71 |

Difficulty is not independently relabelled for the other documents. These named
cohorts preserve historical denominators rather than manufacturing hard-case classes.
Warnings include PDF table structure not preserved on 30/30 sources; DOCX ancillary,
footnote, drawing, nested-table and unsupported-body warnings on 19 documents;
and XLSX drawing/error/formula-definition/comment warnings on 11 documents.
Detailed per-source warning events and occurrence counts remain private.

## Cleaning and source-offset traceability

Across all nonfailed captures, **100,393 field observations** include 3,057
whitespace-only fields and **97,336 non-empty fields**. All 97,336 have a precise
downstream field rendering with identical non-whitespace characters; **zero
non-empty fields lack rendering**. Matching is confined to real fields: generated
cell labels, coordinates and metadata cannot satisfy an anchor. This is mechanical
preservation of extracted output, not correctness against the original document.

All **92,935 distinct-per-cell XLSX value/formula/cache field observations** retain
their exact captured literals. Value/cache duplicates are deduplicated as in the
existing scorer. These observations mostly lack reviewed value labels.

| TextBlock mapping population | PDF | DOCX | Total |
| --- | ---: | ---: | ---: |
| Extracted TextBlocks | 143 | 2,383 | 2,526 |
| Nonempty mapped units | 137 | 1,295 | 1,432 |
| Verified normalized code points | 300,093 | 171,607 | 471,700 |
| Trimmed outer whitespace from nonempty blocks | 480 | 307 | 787 |
| Empty/whitespace-only blocks | 6 | 1,088 | 1,094 |
| Whitespace characters in those empty blocks | 2 | 153 | 155 |

Every map's UTF-8 original-text hash, original length, normalized range, original
range and chunk placement was independently checked, including each range's text
correspondence and full contiguous coverage. In these real captures, CRLF collapse
count is zero; synthetic regressions exercise CRLF/CR transformations explicitly.
The 472,642 original TextBlock characters reconcile to 471,700 emitted normalized
characters + 787 outer-whitespace characters + 155 whitespace-only characters.

Tables, XLSX rendering and generated note-reference units have no original
TextBlock map: **96,150 units** carry an explicit unavailable map. Their existing
locators and normalized/rendered source-unit intervals remain separate. No range
is represented as a RAW-byte, PDF-glyph or XML offset. Full-map checks also cover
needs-review outputs; default chunking does not silently admit them.

## Chunking on the same captures

Both unchanged configurations use contract `1.3`, 1,200 characters, 120 overlap,
`allow_needs_review=false`, formula-plus-stored-cache policy, 5M source-character
and 100,000 chunk bounds. No tokenization, embeddings or indexing is performed.

| Metric | Fixed-size | Structure-aware |
| --- | ---: | ---: |
| Chunked / skipped documents | 51 / 39 | 51 / 39 |
| Skip reasons: review / extraction failure | 33 / 6 | 33 / 6 |
| Chunking failures | 0 | 0 |
| Chunks | 1,793 | 2,055 |
| Unique represented source characters / eligible characters | 1,877,393 / 1,877,393 | 1,877,393 / 1,877,393 |
| Emitted source characters, including overlap | 2,082,598 | 1,908,147 |
| Duplicate source characters | 205,205 | 30,754 |
| Emitted / unique duplication ratio | 1.109303 | 1.016381 |
| Oversized emitted chunks | 0 | 0 |
| Oversized-element split chunks | 0 flagged by this strategy | 330 |
| Length min / P50 / P95 / max | 142 / 1200 / 1200 / 1200 | 8 / 945 / 1200 / 1200 |
| Chunks with provenance / all chunks | 1,793/1,793 | 2,055/2,055 |
| Emitted TextBlock code points with verified maps, including overlap | 349,753 | 340,266 |

Fixed-size's zero split flags is its existing flag convention, not absence of
element cuts. Across the 84 nonfailed captures there are 7,403,275 rendered
source-unit characters; the 33 held documents contain **5,525,882** of them.
Those are policy exclusions, not chunk truncation. Content in six failed sources
is unknown. Thus 100% conditional coverage is not 100% corpus evidence retention.

### Reviewed evidence survival and attribution

A retained anchor must match the frozen locator/occurrence, map to an actual
cleaned field interval, and fit wholly in one chunk. Pair checks additionally
require a common chunk after native order/relationship checks. A spanning-cell
check also requires its existing span rendering/merge metadata in that chunk.
Non-null cell bundles require all available reviewed non-null fields together;
null absence has no character interval. These definitions do not infer missing
header/unit/period semantics or require every distant order pair to be an answer.

| Expected assertion population | Total | Upstream missing text | Upstream structure/order/locator | Ancillary scorer unsupported | Failed extraction/unobserved | Eligibility excluded | Cleaning field loss | Fixed: separated / survives | Structure: separated / survives |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Anchors | 126 | 11 | 24 | 1 | 11 | 23 | 0 | 0 / 56 | 0 / 56 |
| Order-pair co-retention | 58 | 6 | 9 | 0 | 2 | 9 | 0 | 13 / 19 | 14 / 18 |
| Row/column relationship co-retention | 33 | 0 | 20 | 0 | 4 | 5 | 0 | 0 / 4 | 0 / 4 |
| Table cell plus span | 52 | 0 | 24 | 0 | 11 | 13 | 0 | 0 / 4 | 0 / 4 |
| Non-null cell field bundle | 13 | 0 | 0 | 0 | 6 | 3 | 0 | 0 / 4 | 0 / 4 |

All **56/56 eligible located anchors** survive wholly. Of the 32 otherwise
available eligible order-pair assertions, fixed retains 19 together and structure
retains 18. Separation is a measured co-location result, not evidence of incorrect
global order or a semantic quality ranking. Unique character coverage alone would
hide this distinction. The 71 unreviewed documents contribute no Gold completeness
denominator; full semantic evidence-bundle survival remains NOT_EVALUATED.

## Historical comparability

The retained 11-record baseline has identical corpus bytes, source map, Gold subset,
dependency versions, extraction limits and disabled-experiment setting. AST checks
verify unchanged normalization, observations, location matching and metric counting.
The only `score_record` AST change is stricter relationship scope (adding part/block).
That historical metric is **NOT_COMPARABLE**. Comparable extraction counts below
use the same 11 labels, including the same failed-output counting definition:

| Metric | Historical 11-record baseline | Current same 11 records |
| --- | ---: | ---: |
| Required text | 45/55 | 35/55 |
| Partial order | 16/22 | 14/22 |
| Cell/span | 28/32 | 17/32 |
| Provenance | 54/68 | 37/68 |
| Stored value / formula / cache, each | 13/13 | 7/13 |

The rejected XLSX sources explain the new unobserved expectations; current DOCX
global recall also differs. These are count changes across native implementations,
not a controlled causal attribution or a percentage improvement claim.

On the identical 12-PDF expanded subset, comparable native counts are unchanged:
required text 79/90, order 31/46, cells/spans 0/24, provenance 55/90. Relationship
counts are 0/20 in both reports but retain NOT_COMPARABLE definition status.
Current whole-19 rates must not be compared with old whole-11 rates. Historical
chunking contract `1.0` versus current `1.3`, changed eligibility and rendered units
make whole-pipeline improvement/regression **NOT_COMPARABLE**. No percentage gain is claimed.

## Reproduction, determinism and checks

Private evidence lives under ignored
`evaluation-output/qg01-qg03-diagnostic-20261021/`. `protocol.json` records scope,
definitions, budgets and configuration; `run.py` imports existing implementations
and captures one result per source. `final-1/` and `final-2/` contain source captures,
source units/maps, both chunk sets, native fidelity metrics, gate/rights audits,
per-assertion attribution and completion manifests. `verification.json` records
all-file equality, identity rechecks and historical comparison proof.

The preliminary `run-1/`, `run-initial.py` and `protocol-initial.json` are retained.
Before the final repetitions, instrumentation was clarified to expose empty versus
unrendered fields, unobserved labels and ancillary scorer limitations. No source,
algorithm, selected label, chunk setting or threshold changed. Total extraction
work was three 90-source captures: one preliminary and two final.

Both final runs produce **365 byte-identical non-runtime files each**, including
all private captures/annotations and completion hashes. Only `runtime.json`
differs. No timing is removed from a deterministic evidence file after comparison.

| Deterministic identity | Fingerprint |
| --- | --- |
| Combined diagnostic | `e09d1eec45ca762c15720dcaf2e0b58ff51d18311dfb9be7a8b2dd8e15e389a8` |
| Existing expanded fidelity evaluator | `5ce45c41fe7c63966382d1427fe38e1d93bbd6dc5aaeabcd9cd76136072f4885` |
| Existing data-quality gate | `24223b2c932421582252c8dbdaedb2de121ad018bf913e0879d8e90a35075ca1` |
| Fixed-size configuration | `86c4bb2ad8837204f98a585ec44a60b7bedf90f4cad28a9c424b95d38d337d02` |
| Structure-aware configuration | `345a4392f5676681a15f3921bf479f0e36a9044d61643ba667b9cae5aa7d3279` |
| Fixed-size chunk-set identity | `cf515d5ce9a20d942c1958da648b1e3655271f3a7114ac0724021ae28feb76da` |
| Structure-aware chunk-set identity | `bda156d798164f49cfa4e33e27b66d0c3ce7308ad97eee8404f2ff4c9720be21` |
| Private diagnostic runner bytes | `0383c036a095bbdb2c7bedc384bcd122332865ed73a6da74545ce4668143046c` |

Actual commands, repository root, existing `.venv`:

```powershell
$env:PYTHONPATH=(Get-Location).Path
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.venv/Scripts/python.exe -B evaluation-output/qg01-qg03-diagnostic-20261021/run.py --output evaluation-output/qg01-qg03-diagnostic-20261021/run-1
.venv/Scripts/python.exe -B evaluation-output/qg01-qg03-diagnostic-20261021/run.py --output evaluation-output/qg01-qg03-diagnostic-20261021/final-1
.venv/Scripts/python.exe -B evaluation-output/qg01-qg03-diagnostic-20261021/run.py --output evaluation-output/qg01-qg03-diagnostic-20261021/final-2
.venv/Scripts/python.exe -B evaluation-output/qg01-qg03-diagnostic-20261021/verify.py
.venv/Scripts/python.exe -B -m pytest tests/unit/test_extraction_fidelity.py tests/unit/test_data_quality_gate.py tests/unit/test_chunking.py tests/unit/test_safe_cleaning.py tests/unit/test_textblock_offsets.py tests/unit/test_evidence_regressions.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg01-qg03-diagnostic-20261021/tests --junitxml=evaluation-output/qg01-qg03-diagnostic-20261021/tests.xml
.venv/Scripts/python.exe -B -m pytest evaluation-output/qg01-qg03-diagnostic-20261021/test_diagnostic.py -q --tb=short -p no:cacheprovider
.venv/Scripts/ruff.exe check src tests tools alembic
git diff --check
git diff --cached --name-only
git status --short
```

All three captures completed (exit 0); final evidence verification passed (exit 0).
Existing tests: **285 passed, 1 skipped** in 10.53 s. The skip is the Windows
symlink-privilege check, not a passing symlink test. Seven additional local synthetic
instrumentation tests passed: interval survival/fragmentation under both strategies,
wrapper false-positive prevention, explicit unrendered-value accounting and rejection
of changed text identity/incomplete maps. They create no real review attestations.
Ruff and diff/privacy/scope checks pass. Nothing is staged.

Environment: Windows x86-64, Python 3.12.3; pypdf 6.20.0, python-docx 1.2.0,
openpyxl 3.1.5, Pydantic 2.14.0. Native extraction is serial CPU work. Interpreter
and dependency imports precede per-document timers; file-system caches were not
flushed. Peak RSS/hard resource containment is NOT_EVALUATED. No GPU, model,
training, indexing or production E2E runs occurred. The final harness audit hook
denies network access and records **zero network attempts** in both final runs.

| Native extract latency, 30 observations per format | Final 1 P50 / P95 ms | Final 2 P50 / P95 ms |
| --- | ---: | ---: |
| PDF | 46.836 / 948.105 | 45.562 / 967.554 |
| DOCX | 22.078 / 631.602 | 22.806 / 627.714 |
| XLSX | 14.060 / 1046.711 | 14.087 / 1044.004 |

Total diagnostic durations were 43.288 / 43.348 seconds. These include capture,
hashing, scoring, gate replay, cleaning, chunking and local serialization; the
per-document extraction timers exclude those downstream costs. They are local
diagnostics, not throughput/SLA or cold-start qualification.

Only this sanitized report is a new Git-visible task file. Private originals,
Gold, detailed evidence and the existing independent audit remain unstaged and
unchanged. No commit or push is performed. Missing independent coverage, current
rejections and unsupported dimensions remain outstanding; no follow-up optimization
is started by this diagnostic.
