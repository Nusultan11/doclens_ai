# ML-17: c1-0040 PDF table locator alignment v1

STATUS: PASS (bounded diagnostic execution and reconciliation).
H1: INCONCLUSIVE under the preregistered criteria.
Frozen Docling quality remains REJECT; production pypdf remains the baseline.

The failing locator components are now measured. All 15 anchor-cell substring
matches disagree with reviewed table identity; 12 also disagree on row and five
on column. Page/block agree throughout. Native-to-DocLens normalization preserves
all 180 cells, including text, grid coordinates and spans. A normalization repair
is not justified. Source/Gold table/title-counting conventions remain unresolved,
and the first source occurrence of a6 is partitioned across two native cells.
These are distinct issues; global 8/8 text recall conceals the latter.

## Scope, preflight and registered H1

2026-10-18, branch `main`, clean initial worktree, HEAD
`60288ef04fbc58d4ea8ea4fb1880b429813dc08c`. Root AGENTS.md and extraction/experiment
skills applied; the PDF skill guided independent source-geometry inspection.
No more-specific AGENTS.md applied. Read only the requested reports/protocol,
relevant extraction/normalization/scoring/Gold interfaces, focused test sections
and required frozen inputs. External GOAL, QG-01, EVALUATION and ENGINEERING policy
definitions are UNAVAILABLE; no unavailable policy gate is claimed passed.

Preflight verified all 90 source SHA/size/format identities, strict 19-record
reviewed Gold including duplicate-key rejection, both expanded-v1 metrics byte
hashes and independently recomputed deterministic fingerprints. Both reports
are field-for-field identical excluding runtime, with twelve complete paired
observations. All failures/needs_review remain in original denominators.
Gold review is an existing attestation, not new human review in this task.

The c1-0040 original is 64,968 bytes, SHA-256
`18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344`.
Five existing local model artifacts and exact frozen configuration were verified.
Current candidate bytes differ from the expanded benchmark following earlier
authorized work; AST comparisons confirm identical CandidateConfig, converter,
offline guard, inventory, integer validation and table-normalization branch.
The complete c1-0040 extraction fingerprints and scores reproduced exactly, so
no byte-identical-current-runner claim is made.

Registered before Gold locator/native-grid inspection, at
`2026-10-18T05:22:10.061566+00:00`:

> The four c1-0040 table failures may originate from native-to-DocLens table/grid
> locator mapping rather than absent text or cell content.

Unchanged decision criteria:

- REPRODUCED: all four failures have exact native structured content faithful to
  independently source-supported reviewed locators, but normalization changes or
  loses required locator components/spans; demonstrate each without guessed
  coordinates or altered Gold.
- NOT_REPRODUCED: all four mappings are faithful, and independent source/Gold
  assessment demonstrates incompatibility already in native recognition or the
  source/Gold contract, permitting complete attribution outside normalization.
- INCONCLUSIVE: incomplete captures, ambiguous duplicate alignment, unresolved
  source/Gold interpretation, mixed causes without complete attribution or a
  failure to reproduce frozen results. Retain per-anchor UNKNOWN categories.

The normalization-loss prediction is unsupported, but unresolved canonical
table/title counting and the additional native a6 partition meet the registered
INCONCLUSIVE criterion. This is not a newly selected acceptance threshold.

All temporary code, private inputs/captures/locators, original-page rendering,
geometry projection, failures and resource journals are ignored under
`evaluation-output/pdf-c1-0040-locator-v1-20261018/` (`$scratch`). Only this report
is an intended Git change. No Gold, source, previous capture/report, production
code, tests, scoring, limits, configuration or models changed. Gold never enters
the converter; it is used only for read-only post-conversion comparison.

## Why one additional conversion was necessary

The prior root-cause report explicitly retained c1-0040 native/normalized payloads
in memory only. The inspected frozen benchmark directories contain metrics only;
available c1-0043 captures cannot establish c1-0040 grids. Exactly one authorized
c1-0040 conversion was therefore performed, protected by an exclusive attempt
marker and existing crash-isolated monitor. No retry, full-corpus conversion,
OCR, GPU operation, dependency installation or model download.

Unchanged settings: CPU, two threads, FAST tables, cell matching, local pinned
artifacts, OCR/enrichment/remote services/plugins disabled; 600 seconds,
3,221,225,472 process bytes, 50 MiB source, 200 pages, 100,000 blocks/cells,
5,000,000 characters. The wrapper only copies the returned native document;
convert arguments and returned object are unchanged. The existing adapter then
normalizes it. A separate later normalization replay uses that saved document
and initializes no models or converter.

The native capture and normalized extraction each contain five tables on one
page. Every native logical cell has exactly one normalized counterpart with
unchanged text, start row/column, row/column span and validated end offsets:
**180/180 faithful mappings**. Normalized page-local table indices follow native
body traversal; no numerical off-by-one or span-transformation defect is observed.
Re-normalizing the saved native document reproduces the entire normalized result.

## Per-anchor locator reconciliation

The four reviewed table anchors are a3-a6, each occurrence=1 with reviewed
single-row/single-column spans. Every matching structured field is retained;
no duplicate is selected as
the intended source merely because it produces a favorable match. Matching is
the unchanged whitespace-only normalization plus literal substring search;
whole-field equality is counted separately. Expected locators come from frozen
reviewed Gold, never from native predictions. Raw locators/text remain private.

Each mismatch count is over that anchor's native/normalized cell matches.
Counts overlap between components and anchors; 15 is an anchor-cell match count,
not a count of unique cells or reviewed checks.

| Anchor | Structured substring matches, native = normalized | Whole-field matches | Page mismatches | Block mismatches | Table mismatches | Row mismatches | Column mismatches | Matching span pairs among unlocated matches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| a3 | 3 = 3 | 3 | 0 | 0 | 3 | 3 | 0 | 3/3 |
| a4 | 6 = 6 | 3 | 0 | 0 | 6 | 5 | 3 | 6/6 |
| a5 | 4 = 4 | 2 | 0 | 0 | 4 | 3 | 1 | 4/4 |
| a6 | 2 = 2 | 2 | 0 | 0 | 2 | 1 | 1 | 2/2 |
| Total anchor-cell matches | 15 = 15 | 10 | 0 | 0 | 15 | 12 | 5 | 15/15 |

For each anchor, every literal candidate match fails at least two constrained
locator components. Ignoring any single component diagnostically recovers zero
located anchors; this does not change or rerun a relaxed official scorer. A
table-index offset alone cannot solve these failures. None of the four has a
fully located match, so actual cell/span checks remain 0/4 and relation checks
remain 0/4. Matching span pairs at other locations are not recovered Gold checks.

| Anchor | First-source occurrence assessment | Confirmed boundary / unresolved interpretation |
|---|---|---|
| a3 | Present in a native cell of the first main ruled group; copied unchanged. Page/block/column agree, table/row differ. | Native table scope and row convention already incompatible; source/Gold canonical counting UNKNOWN. No normalization change. |
| a4 | Same first-source header band; literal cell text preserved. Additional substring duplicates occur inside longer fields. | Same scope/row incompatibility; duplicate selection cannot establish intended provenance. No normalization change. |
| a5 | Present within a longer native field in that header band; copied unchanged. Its field also contains part of a6. | Same scope/row incompatibility plus native text-boundary contamination. No normalization change. |
| a6 | First-source phrase is absent as a whole field in that first main group, but split across two adjacent native fields. Whole-field matches occur in later groups. | Native cell-content partition before normalization; later duplicates do not recover the first-source occurrence. Grid-recognition versus cell-matching ownership UNKNOWN; source/Gold canonical counting also unresolved. |

## Independent source evidence and limits

Independent PDFium 126.0.6462.0 exact, case-sensitive source searches found
a3/a4/a5/a6 respectively 4/8/4/4 occurrences. Each returned character range was
checked against the unchanged Gold literal, with whitespace normalization only.
Actual character boxes and 750 source path segments were captured. A geometry
projection uses original ruling paths and opaque anchor labels only; it contains
no source/Gold words. Its visual review shows four repeated main ruled groups,
plus a separate boxed region above them, with full-width and partial heading
bands. This is geometric inspection, not new human semantic/Gold review.

Here, first source occurrence means the topmost exact PDFium occurrence on this
page, not a reassigned Gold occurrence. These occurrences share a real vertical
interval. Independent box-overlap checks associate a3/a4/a5 with their native
cells after the declared TOPLEFT/BOTTOMLEFT origin conversion. Native recognition
starts with the separate single-cell boxed region and includes two leading rows
before the first matched header band in the next table. The original has actual
box/heading geometry: simply declaring that single-cell region a false positive,
dropping it, or stripping heading rows is not justified. The inspected Gold
schema/protocol does not specify whether that box counts as a table or whether
these title/heading bands count in canonical row origins. Reviewed scalar
locators contain no region geometry that resolves this convention. Gold is
unchanged and is not declared wrong or reapproved.

At the first source header band, a6's literal can be reconstructed diagnostically
only across two native fields: three characters, one separating space, then
eight characters. The left field also has 14 preceding normalized characters.
Neither field alone contains a6; the unchanged scorer correctly refuses a
cross-cell match. The source independently contains the complete literal there.
This demonstrates native cell text assignment/partition, without identifying the
underlying TableFormer/grid/cell-matching branch. No joined text is fed into
ExtractionResult, Gold, scorer, retrieval or production.

The other repeated headers have different native grids and exact-text coverage.
Selecting a later row with all four labels would confuse global recall with the
reviewed source identity. Canonical source/Gold adjudication is still required
before attributing every scope/row difference to recognition or to annotation
conventions. Complete page/table geometry, other cells' fidelity and semantics
are NOT_EVALUATED; no bounding-box or whole-document table-quality PASS.

## Unchanged scores, statuses and denominators

| Metric | Frozen baseline = replay | Frozen Docling = replay |
|---|---:|---:|
| Status | success | success |
| Required text | 8/8 | 8/8 |
| Provenance | 4/8 | 4/8 |
| Reading order | 2/3 | 2/3 |
| Located cells with reviewed spans | 0/4 | 0/4 |
| Same-row relations | 0/4 | 0/4 |
| Globally missing anchors | 0 | 0 |

pypdf emits page text, not structured table cells; its absent table/grid fields
are a different limitation from Docling's incompatible structured locations.
The four relationships a3-a4, a4-a5, a5-a6 and a3-a5 fail because their endpoints
are not located under Gold. Their presence elsewhere is not scored as a relation.
All four cells and four relations remain in the denominator. Standalone reviewed
span correctness at an independently adjudicated source location remains unknown.
There are zero PDF stored-value/formula/cache/display labels: NOT_EVALUATED.

Both complete frozen twelve-PDF reports remain unchanged, including status/error,
warnings, eligibility, per-anchor metadata and scores. Original aggregate
denominators are 90 text anchors, 46 order pairs, 24 table cells, 20 relations and
90 provenance anchors. There are no failed arms or missing scores in those two
frozen runs; needs_review records are retained. No full benchmark was rerun or
rescored. Execution success does not establish extraction fidelity or promotion.

## Resources and reproducibility fingerprints

Optional runtime: Python 3.12.3, Docling 2.55.1, core 2.48.2,
docling-ibm-models 3.15.0, docling-parse 4.7.3, torch 2.8.0, pypdf 6.20.0,
psutil 7.1.0, pypdfium2 4.30.0. The frozen layout/table revisions remain
`8f39ad3c0b4c58e9c2d2c84a38465abf757272d8` /
`fc0f2d45e2218ea24bce5045f58a389aed16dc23`.

One spawned conversion worker: **31.356718 s**, peak **1,019,817,984 bytes**
(972.574219 MiB), 608 samples, maximum sample gap 0.053872 s. Memory uses Windows
kernel peak_wset with RSS fallback on the actual worker, not its launcher, parent
or summed process tree. Worker executable/parent identity was verified. Four
descendants were observed; recorded cleanup leaves none alive. Worker exit 0,
no terminate/kill, no monitor/cleanup failure or invalid IPC messages; terminal
channel state is recorded as closed/unavailable. The approximately 50-ms guard is
not an OS hard cap and does not measure unobserved or summed descendant peaks.
Wall includes spawn, imports, source rendering, baseline, cold initialization,
conversion, scoring/integrity checks, capture serialization and cleanup; no
conversion-only latency or per-stage CPU/peak attribution is claimed. Analysis/
test process peaks and GPU utilization are NOT_MEASURED. No parallel test load
during the conversion; no GPU workload or repeated conversion.

| Identity | SHA-256 / deterministic fingerprint |
|---|---|
| Manifest bytes | c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0 |
| Expanded Gold bytes | f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf |
| Normalized Gold | 50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e |
| Run 1 metrics bytes | dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48 |
| Run 2 metrics bytes | 3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a |
| Both deterministic reports | d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24 |
| Five-model inventory | 3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71 |
| Current candidate bytes | 8b9bbcdcc4a3951da27107fc4ef9cca4ef3a5bcee99e37ec9f8dc14018038973 |
| Historical expanded candidate bytes | 68c15cabb65f48c26fc531d0efb91900bf6ad5e9beaa9228fcf4005709b81b23 |
| Baseline extraction, frozen = replay | 85a4ce50b736473d88f152889a7b7fb005efc8cea9836d2c3f64bdb3a7da4433 |
| Docling extraction, frozen = replay | 6ebe4cfa79f8fdaeb27e53f410521a6a0af86a06ed482ca84aeca64352539bb9 |
| Preregistered protocol | 79009bdb32452dc882793caeec7c01fa009d9ef2d0626649ecdc9e8bf5e417cf |
| Capture/runtime pin manifest | 46947179f94afe12299db0cb9ae297e68499fe84596c639473d1448d5ffe408d |
| New private capture | 976bc86b43ac0a06c622203a8046baf87088529421a4b0766ccb2219fa1be972 |
| Safe analysis | 1f36db5944afc9a3f9ddc031901fce3d1345e2a555daecd3ed14a5f6eef15a4c |
| Resource journal | 8ff0d2fb9e5d9d83e530cf14c3b53eba4b30a5880a9e61f8e0886270f8f247ac |
| Samples journal | 8a4734ab101de64083f91914a6ddfd438f842a652194bbed5c0704cdc918f1cc |
| Read-only verifier | 79728427b044268fea7adf2fa004a3bf65fcc7e55a9fa54b6df25fcc9d361d58 |

The pin manifest covers 24 scratch/runtime files; 14 preregistered prior files
are also checked. Private native identities, original filenames, raw source
coordinates, evidence text and source paths remain ignored. Only opaque IDs,
hashes and safe counters appear here.

## Actual commands and verification

Repository-relative PowerShell commands:

```powershell
git status --short
git rev-parse HEAD
git branch --show-current
git check-ignore evaluation-output/pdf-c1-0040-locator-v1-20261018/protocol.json
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-c1-0040-locator-v1-20261018/preflight.py
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; $env:HF_HUB_DISABLE_TELEMETRY='1'
$env:OMP_NUM_THREADS='2'; $env:MKL_NUM_THREADS='2'
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-c1-0040-locator-v1-20261018/run.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-c1-0040-locator-v1-20261018/source_geometry.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-c1-0040-locator-v1-20261018/analyze.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-c1-0040-locator-v1-20261018/verify.py
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

Preflight exit 0: 90 originals, 19 reviewed records, two frozen reports, five
model files, identical converter/config/table branch. run.py exit 0:
`outcome=complete, exitcode=0, monitor_error=null, completion_received=true,
worker_alive=false, descendants_alive=[]`; postflight confirms frozen scores,
statuses, warnings and extraction fingerprints. source_geometry.py exit 0:
750 path segments; exact occurrences 4/8/4/4. Successful analyze.py exit 0:
normalization replay exact, 180/180 faithful cells, 15 structured matches and
the per-anchor matrix above. verify.py exit 0: PASS, H1 INCONCLUSIVE, 14 prior
pins and 24 capture/runtime pins unchanged; 22/22 scratch files ignored; one
conversion, no new conversion calls; frozen denominators and resource samples
verified. The verifier is read-only/idempotent and does not rerun a conversion.

Focused pytest: **159 passed in 8.58s**, exit 0, no failed/skipped tests. Existing
tests cover faithful table grids/spans, page-local indices, literal recall versus
provenance, unchanged table scoring, failure-inclusive denominators and privacy.
No production/service/E2E suite or candidate-quality promotion test was run.

Three scratch analysis assumptions failed before their successful corrections,
not the conversion or frozen reconciliation: (1) equal glyph-box centers were
incorrectly assumed; actual shared vertical intersection is now checked;
(2) an exact two-rule count ignored stroke edges and partial-width bands and was
discarded; (3) an initial partition preview assumed a cell equalled a final token;
exact measured substring positions instead show a 3/space/8 cross-cell split.
The first analysis command exited 1; two inline previews also exited 1. A separate
content-free trace located the analysis assertion. The initial script and a
failure journal remain ignored. No expected locator, source/capture, Gold,
acceptance criterion or model result was changed; no conversion retry occurred.

Final report checks actually executed:

```powershell
git diff --check
git diff --cached --check
git diff --no-index -- /dev/null docs/eda/pdf_c1_0040_table_locator_alignment_v1.md
git diff --no-index --check -- /dev/null docs/eda/pdf_c1_0040_table_locator_alignment_v1.md
git status --short
```

Normal whitespace checks exit 0 without output. The full new-file diff was
reviewed. No-index commands exit 1 for a new-file difference, with no whitespace
errors; Git warns of possible future LF-to-CRLF checkout conversion. Actual report
bytes are UTF-8 without BOM, LF-only, final newline, no trailing whitespace; no
Git configuration changed. Inline read-only Python privacy/scope checks exit 0:
original basenames absent, focus-anchor fragments absent outside the two public
test paths explicitly named in this task, all reviewed Gold phrases of at least
12 characters absent, token/private-key/absolute-path patterns absent. Manual
review confirms no raw evidence, locators, private filename/path or weights.
These scans do not claim exhaustive privacy detection or new Gold review.

An initial privacy invocation exited 1 because stdin Python lacked the scratch
module search path; it was corrected. Subsequent scans flagged incidental common
prose and a short fragment inside public test-path identifiers. The incidental
prose was removed; only those exact user-specified public identifiers are exempt
from the short-fragment scan. Rechecks passed without changing frozen evidence.
Source-position checks also passed: first hits are topmost exact occurrences,
and first-source a3/a4/a5 boxes intersect their corresponding native cells.

Final intended Git scope and status:

```text
?? docs/eda/pdf_c1_0040_table_locator_alignment_v1.md
```

Index empty; no unrelated changes. No stage/commit/push before ChatGPT review.

## Smallest justified next action; no extraction correction implemented

**No minimal generalizable extraction fix is justified yet.** Native-to-normalized
grid preservation is demonstrated; an adapter index shift would leave row/column
mismatches and a6's first-occurrence partition unresolved. Dropping all singleton
tables, removing heading rows, selecting later duplicates, fuzzy matching or
joining cells to satisfy Gold would invent a compatibility rule.

The smallest justified correction to the investigation is an explicit canonical
locator-contract adjudication against the unchanged source/Gold, accompanied by
a public synthetic regression scenario. Proposed future files, not modified:
`docs/eda/extraction_fidelity_protocol_v1.md` for singleton/title/row-origin
definitions, and `tests/unit/test_docling_candidate.py` /
`tests/unit/test_extraction_fidelity.py` for a boxed singleton before a ruled grid,
leading merged headings, repeated labels and a phrase split across adjacent
cells. Tests must preserve native spans/identities, distinguish first-source
occurrences from global recall and refuse unsupported cross-cell evidence.
No parser file change is proposed before this review establishes a source-backed
target and native recognition versus cell-matching ownership.

Failure risks: discarding legitimate one-cell tables, losing merged headings,
shifting valid grid coordinates, selecting a wrong repeated occurrence or
manufacturing relationships through concatenation. Keep any later experiment
offline and separately preregistered; rollback by reverting that future isolated
change and rechecking immutable captures/frozen denominators. Never roll back by
rewriting Gold or relaxing the scorer. None of this future work is implemented.

Official engineering context only: PAR-01
[pypdf 6.20.0 extraction](https://pypdf.readthedocs.io/en/6.20.0/user/extract-text.html)
explains positioned text/table ambiguity; PAR-05
[Docling documentation](https://docling-project.github.io/docling/) identifies the
candidate tooling; CODE-07
[Google code-review guidance](https://google.github.io/eng-practices/review/reviewer/)
is review context. Local pinned code/captures establish the findings, not vendor
documentation or status labels. Stop after ML-17; no fix, promotion or next step.
