# PDF extraction regression root causes v1

Analysis date: 2026-10-17. **Analysis verification: PASS. Frozen candidate
quality: REJECT, unchanged.** PASS applies only to this diagnosis and its
reconciliation; no parser improvement or production quality PASS is claimed.

## Scope and evidence

Analysis HEAD: `60674add625b85e0f436ef641060a5f1f8f28c20`.
Expanded experiment pre-registration baseline:
`c37eb003ca47439888a915e54a6efb28ee2429a5`.
Initial status contained four unrelated untracked entries, preserved throughout:

```text
?? docs/evaluation/rag_sufficiency_dev_v1.md
?? tests/integration/test_kaggle_rag_sufficiency_dev.py
?? tests/unit/test_kaggle_rag_sufficiency_dev.py
?? tools/kaggle_gpu/rag_sufficiency_dev/
```

Read the root AGENTS.md, extraction benchmark skill, expanded benchmark report,
and relevant candidate normalization/worker/configuration, scorer/observations,
Gold validation and production PDF extraction/status functions. No nested
AGENTS.md was found under docs, src or tests. Only this report is created.

The architecture v3 section 7 and sections 12–14 requirements were supplied by
the user in this chat; the external documents were not independently accessed.
They require retaining production pypdf, treating Docling as experimental,
preserving evidence/provenance and frozen inputs, failure-inclusive evaluation,
and distinguishing status from fidelity. No production code, tests, Gold,
configuration, weights, outputs or split assignments changed.

Both ignored expanded-v1 metrics files were read, independently fingerprinted and
compared field-for-field after removing runtime. All 90 originals passed the
existing SHA-256/size/format/identity verifier. Strict Gold and duplicate-key
validation passed for all 19 reviewed records. The twelve PDFs are eight fresh
sources plus four historical controls; all remain in every applicable denominator.
There are zero failed arms, blocked records, missing scores or unknown label
observations in either frozen run. Needs-review sources are included.

## Independent reconciliation

Each run's baseline and candidate hit maps were compared by opaque anchor ID,
not by recall differences. Every map has exactly its Gold anchor keys, and its
true count agrees with the unchanged scorer. Both runs give the following values.
S = success; R = needs_review. Each metric entry is baseline passed -> candidate
passed / fixed denominator. NE means zero labels, not a perfect or failed score.

| Population / ID | Status | Anchors | Order | Cells/spans | Relationships | Provenance | New losses / recoveries |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fresh c1-0031 | S -> S | 7 -> 7 / 7 | 4 -> 4 / 5 | NE | NE | 7 -> 7 / 7 | 0 / 0 |
| fresh c1-0032 | S -> R | 10 -> 1 / 10 | 3 -> 0 / 4 | NE | NE | 10 -> 1 / 10 | 9 / 0 |
| fresh c1-0033 | S -> S | 9 -> 9 / 9 | 0 -> 3 / 3 | 0 -> 8 / 8 | 0 -> 8 / 8 | 1 -> 9 / 9 | 0 / 0 |
| fresh c1-0035 | S -> S | 6 -> 7 / 8 | 4 -> 5 / 5 | NE | NE | 6 -> 7 / 8 | 0 / 1 |
| fresh c1-0040 | S -> S | 8 -> 8 / 8 | 2 -> 2 / 3 | 0 -> 0 / 4 | 0 -> 0 / 4 | 4 -> 4 / 8 | 0 / 0 |
| fresh c1-0043 | R -> S | 6 -> 0 / 6 | 4 -> 0 / 4 | NE | NE | 6 -> 0 / 6 | 6 / 0 |
| fresh c1-0048 | S -> R | 11 -> 11 / 11 | 6 -> 6 / 6 | 0 -> 3 / 3 | 0 -> 1 / 1 | 8 -> 11 / 11 | 0 / 0 |
| fresh c1-0049 | S -> S | 12 -> 11 / 12 | 4 -> 3 / 6 | 0 -> 5 / 5 | 0 -> 5 / 5 | 7 -> 11 / 12 | 1 / 0 |
| control c1-0041 | R -> R | 0 -> 0 / 4 | 0 -> 0 / 3 | NE | NE | 0 -> 0 / 4 | 0 / 0 |
| control c1-0044 | R -> R | 0 -> 0 / 5 | 0 -> 0 / 2 | NE | NE | 0 -> 0 / 5 | 0 / 0 |
| control c1-0045 | S -> S | 6 -> 6 / 6 | 1 -> 2 / 2 | 0 -> 4 / 4 | 0 -> 2 / 2 | 2 -> 6 / 6 | 0 / 0 |
| control c1-0050 | S -> R | 4 -> 4 / 4 | 3 -> 3 / 3 | NE | NE | 4 -> 4 / 4 | 0 / 0 |

Lost identities: c1-0032 `a2`–`a10`; c1-0043 `a1`–`a6`;
c1-0049 `a4`. Recovered: c1-0035 `a7`. **16 losses and one recovery confirmed;
no discrepancy.** The other c1-0035 missing anchor remains missing.

| Population | Anchors | Order | Cells/spans | Relationships | Provenance | Known missing | Eligible by status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fresh (8) | 69 -> 54 / 71 | 27 -> 23 / 36 | 0 -> 16 / 20 | 0 -> 14 / 18 | 49 -> 50 / 71 | 2 -> 17 | 7 -> 6 / 8 |
| Controls (4) | 10 -> 10 / 19 | 4 -> 5 / 10 | 0 -> 4 / 4 | 0 -> 2 / 2 | 6 -> 10 / 19 | 9 -> 9 | 2 -> 1 / 4 |
| All (12) | 79 -> 64 / 90 | 31 -> 28 / 46 | 0 -> 20 / 24 | 0 -> 16 / 20 | 55 -> 60 / 90 | 11 -> 26 | 9 -> 7 / 12 |

Anchor arithmetic: `79 - 16 + 1 = 64`; missing `11 + 16 - 1 = 26`.
The c1-0032/0043/0049 order passed-count losses are 3/4/1, offset by gains
elsewhere; pooled provenance also conceals individual regressions. Fresh status
downgrades are c1-0032 and c1-0048; c1-0043's upgrade cannot cancel either.
Historical c1-0050's downgrade remains present.

Baseline warnings are one informational table-structure warning per PDF, plus
insufficient-text counts c1-0043:1, c1-0041:4, c1-0044:1. Candidate drawing
warning counts are c1-0032:2, c1-0048:3, c1-0041:3, c1-0044:1, c1-0050:15;
c1-0041 and c1-0044 additionally have insufficient-text:1 each. All other
candidate warning sets are empty. These counts and status/eligibility fields
match both frozen runs exactly.

## Bounded private inspection

Frozen metrics retain no parsed payload: the worker serializes metadata only.
To establish causes, one additional conversion of each of the four focus PDFs
was performed, serially in fresh local processes. Originals and Gold were opened
read-only; native documents, baseline results and normalized results stayed in
memory. No benchmark runner was invoked and no extraction output was persisted.

The optional runtime used Python 3.12.3, Docling 2.55.1, docling-core 2.48.2,
docling-ibm-models 3.15.0, torch 2.8.0, pypdf 6.20.0 and psutil 7.1.0,
independently checked against captured versions. The exact frozen CandidateConfig
was loaded from run 1, including its 600-second converter timeout. The unchanged
converter used CPU/two threads, FAST tables/cell matching, local pinned artifacts,
and disabled OCR, enrichment, remote services and plugins. The existing private
offline guard suppressed network access and third-party logs. No download,
GPU operation, tuning or alternative normalization was performed.

The diagnostic compared normalized anchor substrings against individual adapter
observations, their whitespace-joined sequence, individual observations with all
whitespace removed, native body iteration, picture-descendant iteration, and all
native text/table-cell fields. Joined searches were diagnostic only: they did not
alter scoring. For all four PDFs, baseline and candidate extraction fingerprints
and the complete candidate score object exactly matched the frozen run. All
focus Gold anchors have region=body and occurrence=1. No anchor text or source
locator is reproduced here; opaque IDs and equality/count checks suffice.

| ID | Pages | Native text / tables / pictures | Adapter text blocks / tables | Baseline / adapter characters | Diagnostic wall seconds |
| --- | ---: | --- | --- | --- | ---: |
| c1-0032 | 1 | 31 / 0 / 2 | 2 / 0 | 3385 / 393 | 16.451 |
| c1-0043 | 4 | 23 / 0 / 0 | 24 / 0 | 5681 / 5497 | 23.512 |
| c1-0049 | 8 | 107 / 7 / 0 | 98 / 7 | 23733 / 23366 | 38.016 |
| c1-0040 | 1 | 3 / 5 / 0 | 1 / 5 | 1100 / 790 | 37.932 |

Each diagnostic process returned exit 0, with no captured stderr or timeout.
The outer monitor sampled around 50 ms with nominal 120-second/3072-MiB limits.
**Memory limitation:** its reported peaks (5038080, 5038080, 5033984, 5042176
bytes respectively) cover the Windows runtime launcher, not the conversion
process tree. They cannot establish conversion memory consumption or an enforced
tree-wide memory ceiling. Actual diagnostic conversion peak is UNKNOWN; these
values are not substituted for frozen benchmark resource observations. The
transient stdin diagnostic program was not saved as another repository artifact.

## Confirmed causes and limits

**c1-0032: adapter omission of already extracted picture-descendant text.**
Every lost anchor (`a2`–`a10`) exists intact in native text items in the body
content layer. None appears with `traverse_pictures=False`; every one appears
with picture traversal enabled. Native matching labels are section_header/text.
`normalize_document` uses the former traversal and skips picture items. Thus all
nine losses occur at the adapter traversal boundary, rather than being proven
native text recognition failures. The two drawing warnings are consistent with
this boundary but were insufficient alone to establish the cause. Neither joined
adapter text nor removal of whitespace recovers these anchors. All four candidate
order pairs lack an endpoint; there is no evidence of an independent reversal
among located endpoints. Provenance loses the same nine anchors. Why layout
placed these text items beneath pictures, and diagram semantics, remain UNKNOWN.

**c1-0043: confirmed upstream exact-evidence absence; underlying cause UNKNOWN.**
All six anchors are absent from native text/table-cell fields, ordinary body
iteration, picture traversal and adapter observations. There are no native tables
or pictures. Joining adapter observations or removing whitespace within individual
observations recovers none. This excludes the demonstrated c1-0032 picture
traversal mechanism and c1-0049 furniture mechanism for these six exact strings.
It does not distinguish omitted characters, altered text, nontrivial fragmentation,
backend decoding, layout selection or font/language handling. No glyph-stream,
font-map, backend-token or visual source alignment was performed; those causal
categories remain UNKNOWN/NOT_EVALUATED. No OCR need is established. All four
order pairs lack an endpoint; zero order/provenance scores do not independently
prove reversal or coordinate corruption.

The **R -> S despite 6/6 -> 0/6** mismatch is separately explained by code.
Production pypdf checks every page for fewer than 20 non-whitespace characters;
one of the four baseline pages triggers that rule. The candidate has 5497 emitted
characters and no pictures: its normalizer adds insufficient_text only when total
`chars` is zero, and otherwise succeeds when it has no notices. A successful
native conversion and nonempty normalized output never consult Gold or check
evidence coverage. Candidate per-page adequacy was NOT_EVALUATED here. Its empty
warning set and generic success therefore establish neither fidelity nor readiness.

**c1-0049: adapter omission of native furniture text.** Lost `a4` exists intact
in one native page_header item in the furniture content layer. It is absent in
both ordinary body iteration and body iteration with picture traversal. The
adapter starts at body with default content layers and does not emit this item.
This is global text omission from normalized output, not a recall failure caused
only by a bad locator. Native semantic classification versus the reviewed body
expectation also needs architectural review; do not relabel Gold. No joined or
whitespace-only recovery occurs. The five reviewed cell/span and relationship
checks pass. Two of six candidate order pairs lack an endpoint; of four remaining
pairs, three pass and one fails ordering. Which backend ordering decision causes
that remaining failure is UNKNOWN; do not attribute the whole order deficit to
the single newly omitted anchor.

**c1-0040: confirmed table locator incompatibility, not missing anchor text.**
All eight anchors are globally present. The four table-check anchors `a3`–`a6`
each appear in native/normalized structured cells, with respectively 3/6/4/2
global structured matches. None matches the reviewed source locator, so all four
cell/span checks and all four relationships fail before spans or relationships
can be validated. The other four anchors are located. The native conversion and
adapter each contain five tables on one page. This disproves a claim that no
table representation exists. It does not identify which page/block/table/row/column
component causes each mismatch, or prove table splitting, a table-index offset,
bad cell geometry or span errors. These are UNKNOWN hypotheses requiring a
separate, bounded source-to-grid alignment. The adapter assigns page-local table
indices by recognition order; that is a plausible compatibility risk, not a
demonstrated error. One of three order pairs lacks an endpoint; the other two
pass. Never fabricate coordinates to force a match.

Across these focus cases, fragmentation is not established by the searches
performed. Bounding-box correctness, full visual reading order, numerical-value
fidelity beyond the existing anchors, rich/multipage tables and unlabelled regions
are NOT_EVALUATED. Zero PDF value/formula/cache/display labels remain NE. The
mechanism of the c1-0035 recovery was not inspected. Controls were reconciled
from metadata, not reconverted or independently relabelled.

## Reproducibility fingerprints

All values below were rechecked locally against existing artifacts; normalized
fingerprints use the repository's canonical JSON fingerprint function.

| Identity | SHA-256 / normalized fingerprint |
| --- | --- |
| Manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| 90-source identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Selected twelve | `ec69b55db7e66298e509c51632432d60b861c7b76845a631ea7f60f6d4cddf68` |
| Fresh eight | `4a856010bd8307f1d150916b63ab689d1792b92ac7128faf6a410895c343ad85` |
| Control four | `d9404bd6b7fc67bf7d65c2747f4fe69f25774b529368b5543d02f3654afd522e` |
| Expanded Gold bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Expanded normalized Gold | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Run 1 metrics bytes | `dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48` |
| Run 2 metrics bytes | `3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a` |
| Both runs, independently recomputed deterministic report | `d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24` |
| Five-file model inventory | `3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71` |
| Candidate runner | `68c15cabb65f48c26fc531d0efb91900bf6ad5e9beaa9228fcf4005709b81b23` |
| Production parsers | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| Extraction models | `0725bb86ebeea07926ab813e91625857fb68e97f3b35e30ecf8d9cb3c7259876` |
| Scorer/corpus verifier | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Gold validator | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |

Model revisions: layout `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`;
table `fc0f2d45e2218ea24bce5045f58a389aed16dc23`. Frozen limits remain 600 seconds,
3221225472 process bytes, 52428800 source bytes, 200 pages, 100000 blocks/cells,
5000000 characters. No seed change. Same serial baseline-first/cold-candidate
design; no model/configuration, candidate, parser, scorer or Gold hash drift.

## Resource evidence from the frozen runs

These are captured observations, not new performance measurements. Each row is
8 fresh or 4 control paired processes, not independent arm-memory samples.
Candidate latency includes initialization. Baseline and candidate time columns
are sums in milliseconds; memory is maximum paired-process peak_wset in bytes.

| Run / population | Baseline ms | Candidate ms | Paired wall ms | Maximum paired peak bytes |
| --- | ---: | ---: | ---: | ---: |
| 1 / fresh | 1250.483 | 184046.963 | 195600.293 | 2594955264 |
| 1 / controls | 3573.432 | 655111.565 | 664177.696 | 2872725504 |
| 2 / fresh | 1269.844 | 173628.334 | 184773.301 | 2595135488 |
| 2 / controls | 3472.587 | 616066.966 | 624859.609 | 3063615488 |

Neither frozen run records a timeout, memory-limit event, infrastructure failure
or failed extraction. No such event explains the regressions. Peak sampling
around 50 ms is not a hard OS sandbox; independent arm peaks and parent peaks
are unavailable. Captured hardware: Windows 11 AMD64, 8 physical/16 logical CPUs,
16541597696 bytes RAM, shared desktop. No throughput/SLA claim is supported.

## Ranked future changes for architectural review (not implemented)

1. **Recommended first: preserve native located text beneath pictures in the
   offline adapter.** Review a narrow traversal change that visits those text
   descendants, retains native provenance/charspans, deduplicates by item identity,
   and keeps picture/diagram review warnings. Nine losses have direct evidence
   for this mechanism. Add a synthetic nested-picture regression before a separate
   frozen comparison; do not concatenate arbitrary blocks or invent locators.
   This proposal has not been tested and is not an improvement claim.
2. Review explicit native furniture-text handling for the single c1-0049 loss.
   Preserve source semantics and page provenance; decide contract compatibility
   before emitting furniture as body. Avoid indiscriminate header/footer merging.
3. Review candidate per-page adequacy/status warnings independently of fidelity
   scoring. This can address the demonstrated status-policy mismatch but cannot
   restore c1-0043 evidence or establish that it would flag this exact document.
4. Diagnose c1-0040 source-to-grid mapping before proposing any coordinate fix;
   diagnose c1-0043 native backend/text alignment before proposing decoding or
   OCR changes. There is insufficient evidence for a concrete repair to either.

All twelve sources are already exposed development evidence. They cannot become
a fresh sealed test. No training, OCR, GPU experiment, model download, candidate
tuning, production adoption or promotion was authorized or performed.

## Verification and command/resource provenance

Executed from repository root in PowerShell. Python audit/inspection commands
used stdin programs; the executable invocations were:

```powershell
git rev-parse HEAD
git status --short
git check-ignore evaluation-output/docling-expanded-v1-20261015-run1/metrics.json local-corpus local-evaluation
$env:PYTHONPATH='src'
# Strict input/hit-map audit, then independent population/runtime aggregation:
.venv/Scripts/python.exe -B -
# Serial four-document diagnostic parent; child invocation was:
# [sys.executable, '-B', '-c', payload, identity]
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -
# Focus-anchor region/occurrence and installed optional-version audit:
evaluation-output/docling-v1-runtime/Scripts/python.exe -B -
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
git diff --exit-code -- src/doclens_ai/extraction tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

Results: input/hash audits exit 0, verified originals=90, reviewed records=19,
nonruntime_equal=True, profile=expanded-v1, failed=0 and blocked=0 in each run;
all per-document and aggregate values above reproduced. Diagnostic exits=0/0/0/0
and frozen_extraction_matches=True for all four. Optional versions match above.
Focused regression tests: **105 passed in 8.25s**, exit 0. Targeted code/test
diff: empty, exit 0. Ignored-path check lists all three requested entries.

Nonessential command failures: an optional process-memory probe in the production
venv failed with `ModuleNotFoundError: No module named 'psutil'`; no dependency was
installed and no measurement was inferred. Two discovery commands using POSIX-style
glob paths failed under Windows rg; file-filter discovery was used instead.
These were neither regression-test failures nor missing benchmark inputs.

Full benchmark rerun, full unit/integration suite, lint/format checks for unchanged
Python, new parser experiments, glyph/font/visual alignment and independent
arm-memory measurement: NOT RUN (outside this documentation-only diagnosis).
Final Python stdin report/assertion audit (`.venv/Scripts/python.exe -B -`)
returned exit 0 with this actual output:

```text
AUDIT PASS: 90 originals; 19 reviewed records; both frozen identities; 12 document rows/status transitions and 3 aggregate rows match both runs; 16 losses/1 recovery; zero failed/blocked observations; code/model/Gold unchanged; privacy scan clear.
```

It asserted every per-document row, status transition and aggregate table row
against both runs, exact Gold anchor-key membership and hit/score agreement,
report equality, input/code/model pins and privacy exclusions. The automated
privacy scan checked all original basenames, Gold strings of at least 12
characters and absolute-path patterns. Two initial audit attempts failed because
the drive-path regex also matched HTTPS URLs; the corrected drive-boundary regex
passed. No private filename or Gold-string collision was found. Manual full-diff
review additionally covers short strings and credentials.

Git verification commands executed: `git diff --check`,
`git diff --cached --check`, `git diff --cached -- docs/eda/pdf_regression_root_cause_v1.md`,
`git diff --cached --stat`, and `git status --short`. Both whitespace checks
returned exit 0 with empty output. The complete staged report diff was reviewed;
only this new Markdown file is staged. The four unrelated untracked entries
above remain excluded. Commit identity and final status are reported in the
completion response, avoiding a self-referential commit hash in this report.

## Sources and privacy

Primary causal evidence is repository code plus local, version-matched installed
docling-core 2.48.2 `iterate_items` / `_iterate_items_with_stack` source and the
fingerprint-matched private observations. Relevant external engineering references
are [PAR-01: pypdf Extract Text](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
and [PAR-05: Docling Documentation](https://docling-project.github.io/docling/).
PAR-01 explains why PDF text and table structure require separate assessment;
PAR-05 is the official candidate reference. Neither diagnoses these private PDFs.
Context7 returned main-branch examples rather than version-pinned evidence; these
were not used to establish pinned API behavior. The live PAR-01 page identifies
pypdf 6.21.0, so the installed 6.20.0 code and frozen outputs govern this analysis.
Architecture v3 sections 7 and 12–14 are user-supplied constraints, as noted above.

Only public library/version questions went to documentation services. No source
or Gold text, real filenames, private absolute paths, values, reviewer identities,
credentials or weights appear in this report. No private material was uploaded.
All existing ignored artifacts remain local and unchanged. UNKNOWN causes are
limits of the diagnosis, not inconsistent counts or hidden exclusions.
