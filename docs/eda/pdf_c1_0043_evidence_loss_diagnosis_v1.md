# c1-0043 PDF evidence-loss diagnosis v1

**Current ML-12 diagnosis/resource verification: PASS after the explicitly
authorized scratch-monitor repair below. Frozen Docling quality: REJECT.**
Two diagnostic conversions exist: the original completed conversion with UNKNOWN
peak, and exactly one authorized repair conversion with measured resources.
Their private extraction captures are byte-identical. This establishes neither
a parser improvement nor production acceptance.

## Original pre-registration

ML-12 diagnosis only, registered on 2026-10-17 at HEAD
`f1b018d6ce0750543361313637da20bb24a633f7`, before the additional conversion.
Question: at which observed boundary do the six reviewed anchors diverge from
the frozen production pypdf extraction? No implementation or quality improvement
is authorized. The four unrelated untracked rag_sufficiency_dev entries are
preserved and excluded.

Preflight verified all 90 original identities, strict approved 19-record Gold,
both expanded-v1 and both picture-text-v1 report fingerprints, unchanged scorer
and production parser, and the local five-file model inventory. All four frozen
c1-0043 document records agree: pypdf needs_review, 6/6 anchors; Docling success,
0/6 anchors. Earlier native exact-string absence does not establish semantic
omission or an internal decoding cause.

Reuse frozen metadata first. At most one additional c1-0043 conversion is allowed,
in an isolated spawned worker with the frozen CPU/two-thread, FAST/cell-matching
configuration, local pinned models, OCR/enrichment/services/plugins disabled.
Keep the existing 600-second and 3221225472-byte monitored process guards, with
memory checked before time and terminate/join/kill cleanup. Sample the actual
spawned conversion PID at approximately 50 ms using peak_wset, RSS fallback;
record observed descendants separately. This is a sampled guard, not a hard OS
memory sandbox. Stop after completion or a guard failure; no conversion retry.

Read-only hooks copy backend textline/word cells, layout-cluster lines and page
assembly output without changing arguments or returned objects. Capture native
text/orig and actual page provenance, then the unchanged adapter observations.
Keep private text only in verified ignored scratch. Independently compare each
anchor across these boundaries and frozen extraction fingerprints/full scores.

Matching alternatives are diagnostic only: pagewise joins, whitespace removal,
NFC/NFKC (including ligatures), soft/line-ending hyphens, vendor punctuation
substitutions and bounded sequence alignment with sanitized edit-category counts.
They must never change Gold, scorer or candidate outputs or be called recovered
production evidence. Classify each anchor as missing before native construction,
present upstream but lost in native construction, identified transformed
representation, locator mismatch, or UNKNOWN. Do not cross an uncaptured boundary
by inference; exact-string absence alone does not prove semantic evidence absence.
Shared causation requires separate supporting observations for all six anchors.

The complete registration and read-only probe are in verified ignored
`evaluation-output/docling-c1-0043-evidence-v1-20261017/` (called `$scratch`
below). Only this sanitized report is an intended tracked change. Root AGENTS.md
and the extraction benchmark skill were applied; no nested docs AGENTS.md exists.

## Original decision and evidence boundary

**Diagnosis: identified transformed representations for all six anchors.
Original completion/resource verification: BLOCKED. Docling quality: REJECT, unchanged.**
The one authorized conversion completed and reproduced both frozen extraction
fingerprints, complete score objects, statuses and warning counts. However, the
scratch parent's closed-pipe failure prevented persistence of its resource
summary. Its peak and complete monitoring history are UNKNOWN. Do not substitute
historical resource values or claim that this additional conversion passed every
resource gate. Under that original authorization, no second conversion or
completion commit was permitted. The later explicit resource-repair exception
is recorded separately below; it cannot recover the original missing peak.

Earliest observed divergence is already in DoclingParseV4's textline/word output,
before layout/page assembly, native-document construction and the project adapter.
Pagewise sequence alignment against the unchanged pypdf page text identifies
equal-length counterparts with substituted characters. Every transformed span
then exists intact in assembled elements, native text, native orig and an actual
adapter observation on its expected page. All six have region=body, occurrence=1.

| Anchor | Actual Gold / counterpart page | Unchanged baseline / candidate hit | Counterpart length | Changed characters | Classification |
| --- | ---: | --- | ---: | ---: | --- |
| a1 | 1 / 1 | true / false | 55 | 5 | Present in transformed representation before native construction |
| a2 | 1 / 1 | true / false | 11 | 6 | Present in transformed representation before native construction |
| a3 | 1 / 1 | true / false | 10 | 1 | Present in transformed representation before native construction |
| a4 | 2 / 2 | true / false | 20 | 1 | Present in transformed representation before native construction |
| a5 | 2 / 2 | true / false | 56 | 19 | Present in transformed representation before native construction |
| a6 | 3 / 3 | true / false | 54 | 12 | Present in transformed representation before native construction |

Across these spans, 44 characters differ: 11 lowercase Latin characters become
different lowercase Latin characters, 20 become uppercase Latin characters, and
13 decimal digits become combining marks. Uppercase substitutions are not assumed
to be ordinary casing differences. No characters are inserted/deleted in these
aligned spans. a2/a5/a6 contain the digit-to-combining-mark changes; a1/a3/a4
contain letter substitutions only. No conflicting source-to-counterpart character
mapping was found within a page among the six aligned spans. This identifies a
shared observed transformation class, not proof that a single internal function
causes every change.

a1 spans multiple backend text lines; its transformed counterpart is contiguous
after assembly. The other five transformed spans occur within individual backend
lines. Searches against joined backend words/lines identify every counterpart;
the original strings remain absent even after joining. Thus ordinary line
fragmentation alone does not explain the losses. Per-anchor page alignment and
unchanged global recall also exclude a locator-only explanation. All four reviewed
order relationships pass **only in diagnostic counterpart matching**; official
scores remain 0/4. No visual-layout correctness or new production recovery follows.

| Page identity | pypdf characters | Backend text lines | Normalized characters / blocks |
| ---: | ---: | ---: | --- |
| 1 | 848 | 55 | 762 / 10 |
| 2 | 2950 | 54 | 2888 / 10 |
| 3 | 1883 | 32 | 1847 / 4 |
| 4 | 0 | 0 | 0 / 0 |
| Total | 5681 | 141 | 5497 / 24 |

Native output has four pages, 23 text items, zero tables and zero pictures. One
multi-provenance item accounts for the adapter's additional block. Native fields
were examined across all content layers, including orig; furniture/picture
filtering does not explain these six strings. Native items spanning pages were
not counted twice in these normalized per-page totals. The fourth page's zero
extracted characters do not establish its visual contents.

## Confirmed, inferred and unknown

**Confirmed:** exact-character fidelity diverges by the backend textline/word
boundary; the identified altered spans survive subsequent construction and
normalization. Native orig already contains the altered forms, so restoring orig
in the adapter cannot recover these anchors. No semantic evidence absence is
established: recognizable aligned counterparts remain, with demonstrated numeric
character corruption in three anchors. Their semantic equivalence and full
document numerical fidelity are not certified.

NFC, NFKC/compatibility ligatures, whitespace removal, pagewise joins, soft-hyphen
removal, line-ending-hyphen removal and the installed assembly punctuation
substitutions each recover **zero of six original strings** at the inspected
candidate boundaries. They remain diagnostic checks only. No alternate matching
was used to change official scores or reviewed labels.

Read-only pypdf text visitors exactly reproduced the page text and associated
every anchor character with a known source font. All six use embedded Type0 fonts
with ToUnicode maps. a1/a3/a4/a6 use one map identity; a2/a5 use a second. These
observations support investigating font/Unicode interpretation, but do not prove
that ToUnicode is ignored or that the maps themselves are defective. No actual
glyph/CID-to-Unicode correspondence or rendered glyph alignment was established.

**Inference:** upstream font/encoding interpretation is a narrower plausible
cause than adapter traversal, reading order or whitespace normalization.
**UNKNOWN:** the responsible compiled decoder rule, font-map precedence, whether
one internal mechanism explains both font groups, and the exact transformation
before word/textline output. The backend keeps no char cells under the frozen
keep_chars=False setting; an empty captured char_cells list is not evidence of
missing source glyphs. No options were changed to expose them. Native compiled
code was not instrumented. OCR need, rendered semantic fidelity and unlabelled
content are NOT_EVALUATED.

## Status policy and fixed denominators

All four frozen c1-0043 records and this capture agree:

| Measure | Production pypdf | Offline Docling |
| --- | --- | --- |
| Status | needs_review | success |
| Required anchors | 6/6 | 0/6 |
| Provenance | 6/6 | 0/6 |
| Reviewed order | 4/4 | 0/4 |
| Missing anchors | 0 | 6 |
| Warnings | insufficient_text:1; pdf_table_structure_not_preserved:1 | none |

The production parser checks each page against 20 non-whitespace characters;
page 4 triggers review. The table warning is informational. The candidate checks
total normalized text, not each page or Gold coverage; 5497 characters and no
pictures produce no review notices. Neither native conversion success nor adapter
success tests these six evidence strings. This status transition is explained
separately from upstream character substitutions and was not changed.

All six anchors and all four order pairs remain in denominators. Table/cell/value
dimensions have zero labels and remain NOT_EVALUATED. Each existing benchmark
still attempts 12 PDFs with 90 anchor and 46 order labels; no failed or
needs_review document was dropped, rescored or overwritten. This diagnosis is
one document, not a new population result or a fresh sealed evaluation.

## Smallest justified future step

Recommend a **synthetic backend regression fixture** with embedded Type0 fonts,
explicit ToUnicode mappings, mixed letter cases and digits, and assertions on the
word/textline output before native construction. Test font-map precedence there
before proposing an upstream decoding correction. This targets the demonstrated
boundary without embedding private strings or learning replacement rules from
Gold. The exact runtime correction is not yet justified: the decoder owner/rule
is UNKNOWN. No adapter fallback, blanket substitution, OCR, normalization/scorer
change, model retuning or parser promotion is proposed as an established fix.
Nothing was implemented.

## Reproducibility fingerprints

All inputs below passed preflight and post-capture rechecks. The current candidate
differs from the original expanded runner by the already committed picture
traversal and observability changes; identical c1-0043 extraction fingerprints
and full scores establish relevance of this capture, not source-hash equality.

| Identity | SHA-256 / fingerprint |
| --- | --- |
| Analysis HEAD / required ancestor | `f1b018d6ce0750543361313637da20bb24a633f7` |
| Manifest bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| All 90 source identities | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| c1-0043 source, 91484 bytes | `b70a5d33160ee12eba6b5f66e305df69b6d504389c11c142657c41d2be45c3ce` |
| Approved Gold bytes, 19 records | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Normalized reviewed Gold | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Expanded run 1 bytes | `dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48` |
| Expanded run 2 bytes | `3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a` |
| Both expanded deterministic reports | `d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24` |
| Picture-text run 1 bytes | `f78aaf265e0fa065f81a7d9b6472ad42f02ce9e956ff703083203b48428c8aeb` |
| Picture-text run 2 bytes | `2ece0ad6c59dab7770a97891ed4569f33a745ed5e615c1e29a0a49b319f4f13c` |
| Both picture-text deterministic reports | `faaef99c1e9bf5be6aa76c92159aee6fa5dd1dfa13bd24a10dab088a6523597d` |
| Baseline extraction, all four frozen runs and capture | `888d2e1c96f1fdeba16f1b5b2a05897e8dee9d5920f4031040ee7ebf52056019` |
| Candidate extraction, all four frozen runs and capture | `ad67f845f2a04b7fc7bb1d14fd1018550345a141f91a49292d453ed5c68464ed` |
| Five-file model inventory | `3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71` |
| Frozen configuration | `562fc3ca48fa26d464d5c17151f2f61a88a78e376663708127eaf7cce32531b7` |
| Current candidate runner | `8b9bbcdcc4a3951da27107fc4ef9cca4ef3a5bcee99e37ec9f8dc14018038973` |
| Production parser | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| Scorer | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Gold validator | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |
| Extraction contract | `0725bb86ebeea07926ab813e91625857fb68e97f3b35e30ecf8d9cb3c7259876` |
| Pre-registration JSON | `812ddef5573ac0a685867b22d906a91eb8ceea4eca46bf68e6c40b59e2d2b86d` |
| Unchanged one-conversion probe | `4164c67bb13c02f342425b2750fa30bf0473432c5b862a6478b24b9f1eced7ec` |
| Private ignored capture | `7a3ba4fe49d5afa6a990be07da5c8ba16e5ad7e9db93107fd8eba5ebaea22510` |

Model revisions remain layout `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`
and table `fc0f2d45e2218ea24bce5045f58a389aed16dc23`. Python 3.12.3;
Docling 2.55.1, core 2.48.2, ibm-models 3.15.0, docling-parse 4.7.3,
pypdfium2 4.30.0, torch 2.8.0, pypdf 6.20.0, psutil 7.1.0 match the frozen
environment. Host: Windows 11, AMD64, 16 logical CPUs; converter fixed to two CPU
threads. Limits also remain 52428800 source bytes, 200 pages, 100000 blocks/cells
and 5000000 characters. No dependency or weight download occurred.

Direct engineering evidence is repository parser/scorer/candidate code and exact
installed vendor functions: DoclingParseV4PageBackend._ensure_parsed,
PdfDocument.get_page/_to_cells, PageAssembleModel.__call__/sanitize_text, and
ReadingOrderModel._handle_text_element. The backend wrapper hashes to
`c4205b69a5e334dace6a877db6606e09b7b998bfe2a664cd1b65cec556c61b7c`;
page assembly to
`4ef3759da7b3edd52874bc69514073a6e302a6a6414dfe984a97b0c608f39ab8`.
Other inspected vendor hashes are retained in ignored preflight metadata. No
external guidance is used to infer undocumented decoder behavior.
Additional inspected wrapper `docling_parse/pdf_parser.py` hashes to
`3851bb66444b72b6c5aca6ca27d61b2fdc5d4a9363ff4bad89f2f7a7109db52f`;
the installed native parser binary hashes to
`1dc5839ceabd8576b51ebdd035382c5515e79b8dcdde7169bb83a7da2fe768e1`.
No native binary was changed or exported.

## Actual commands, results and resource limitation

Executed from repository root. Diagnostic commands used PYTHONPATH=src,
PYTHONDONTWRITEBYTECODE=1, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1 and
HF_HUB_DISABLE_TELEMETRY=1; the worker additionally used the existing private
offline guard. `$scratch` below denotes the ignored directory above, and
`$runtime` denotes `evaluation-output/docling-v1-runtime/Scripts/python.exe`.
These aliases abbreviate the identical literal command paths actually executed.

```powershell
git rev-parse HEAD
git merge-base --is-ancestor f1b018d6ce0750543361313637da20bb24a633f7 HEAD
git status --short
rg --files docs src/doclens_ai/extraction tests -g AGENTS.md
git check-ignore evaluation-output/docling-c1-0043-evidence-v1-20261017/probe.py
& $runtime -B "$scratch/probe.py" preflight
& $runtime -B "$scratch/probe.py" run
& $runtime -B "$scratch/analyze.py"
& $runtime -B "$scratch/align.py"
& $runtime -B "$scratch/fonts.py"
& $runtime -B "$scratch/check_monitor.py"
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

HEAD printed the SHA above; ancestor check exit 0. Nested-instruction search
printed nothing (rg exit 1: no matching file). Ignore check printed the exact
scratch probe path. Preflight exit 0: 90 verified originals, 19 reviewed records,
all four report byte/deterministic identities, identical focus records and
model/config/code pins. The single model command exited 1 and printed
`DIAGNOSTIC_CHECK_FAILED_CONTENT_SUPPRESSED`; its saved worker completion is true
and both arm results exactly match the frozen records. Analysis exit 0 printed
`frozen_arms_exactly_reproduced: true` and
`input_model_code_pins_unchanged: true`, with the counts above. Alignment exit 0:

```text
TRANSFORMED_COUNTERPART_ORDER {"diagnostic_only": true, "located_endpoints": 4, "passed": 4, "scoring_unchanged": true, "total": 4}
PER_PAGE_OBSERVED_SUBSTITUTION_CONFLICTS 0
```

The first font inspection exited 1 on page 4's absent font dictionary:
`AttributeError: 'dict' object has no attribute 'get_object'`. Correcting only that
ignored read-only script's empty-dictionary handling and descending through Type0
font descriptors yielded exit 0, all four visitor/page equality checks and the
font associations above. It performed no Docling conversion. Optional fontTools
was unavailable; it was not installed and no glyph-map claim depends on it.

The model-free synthetic monitor command also exited 1, reproducing the closed
Windows pipe problem without a conversion:

```json
{"exception_type": "BrokenPipeError", "frames": [{"function": "<module>", "line": 26}, {"function": "run", "line": 161}, {"function": "poll", "line": 257}, {"function": "_poll", "line": 344}]}
```

The probe drain does not catch OSError from poll after its worker closes the pipe.
This explains the independently reproduced scratch-monitor failure mode; the
real run's original exception type/trace was suppressed, so its exact exception
is not independently retained. Application `_received_phase` already catches
OSError/EOFError; no production IPC defect is inferred or changed here.

The configured resource guards and cleanup are present in the preserved probe,
but its in-memory peak, phase sequence, exit code, descendant inventory and final
wall duration were lost when the parent raised before writing resource.json.
Last reliably captured milestone is completed extraction/capture, not a guessed
internal phase. Marker creation to completion-file write is 16.601752 seconds
from filesystem metadata; this is **not** a substitute for process wall/peak
measurement or proof of the memory ceiling. No resource breach was recorded;
absence of a persisted breach is not a passed resource check. Frozen expanded
run 1 c1-0043 measured 1990070272 peak bytes / 22391.17320004152 ms; picture-text
run 1 measured 2525077504 bytes / 14656.794100010302 ms. Those historical numbers
remain separate and cannot fill this diagnostic's UNKNOWN resource fields.

Focused tests actually passed:

```text
159 passed in 6.64s
```

No focused test failed or skipped. The broader unit suite, Ruff and formatting
were not run for this documentation-only change. No full benchmark, second
conversion, OCR, GPU execution, tuning, exposed-data sealed test or promotion ran.

Original blocked-checkpoint read-only verifier command:

```powershell
& $runtime -B "$scratch/verify_report.py"
```

At that checkpoint, exit 0: source/model/Gold/frozen-report/code pins PASS;
six-anchor arithmetic and frozen scores/statuses PASS; tracked scope PASS;
ignored private scratch PASS;
all six focus Gold strings and all 90 real source filenames/paths absent from the
report; no additional conversion. Resource verification explicitly BLOCKED.
The initial privacy scan failed on incidental short substrings in measured counts
and an environment-variable name. After manual review, the scanner checks every
focus string plus other Gold strings of at least eight characters; short incidental
matches are not represented as quoted Gold. That corrected verifier passed.
No raw source text, Gold answers, real source filenames, absolute private source
paths, credentials, native payloads or model weights are staged.

No production/experimental source, tests, configuration, previous report, frozen
metrics, Gold, corpus or split assignment changed. Temporary diagnostic scripts
and private capture are ignored, never staged. Other PDF defects remain outside
scope: c1-0049 furniture/order, c1-0040 table locator checks, and c1-0045 native
memory allocation owner UNKNOWN. ML-11's candidate remains REJECT. No next ML
step was started. At the original blocked checkpoint, this report recorded a useful
evidence boundary and a genuine resource-verification blocker; no commit was
created. The subsequent repair below preserves that failed-monitor evidence.

Original blocked-checkpoint Git checks actually executed:

```powershell
git add -- docs/eda/pdf_c1_0043_evidence_loss_diagnosis_v1.md
git diff --cached -- docs/eda/pdf_c1_0043_evidence_loss_diagnosis_v1.md
git diff --check
git diff --cached --check
git diff HEAD --name-only
git diff --cached --stat
git status --short
git rev-parse HEAD
```

Both whitespace checks returned exit 0 with no output. Full staged diff was
reviewed for privacy and scope: one new report only. Git emitted its normal
LF-to-CRLF working-copy warning during staging. At that checkpoint the report
remained staged for review with no new commit. HEAD was the analysis SHA above.
The four initial unrelated entries remain untracked and unread:

```text
A  docs/eda/pdf_c1_0043_evidence_loss_diagnosis_v1.md
?? docs/evaluation/rag_sufficiency_dev_v1.md
?? tests/integration/test_kaggle_rag_sufficiency_dev.py
?? tests/unit/test_kaggle_rag_sufficiency_dev.py
?? tools/kaggle_gpu/rag_sufficiency_dev/
```

## Resource-verification repair: pre-registration

The user explicitly authorized one further c1-0043 conversion to repair this
existing ML-12 verification gap, conditional on successful model-free tests.
This is an exception to the original conversion limit, not a new parser experiment
or ML-13. Repair HEAD is still `f1b018d6ce0750543361313637da20bb24a633f7`.
The original report and all original scratch files/captures are preserved; the
new ignored directory is
`evaluation-output/docling-c1-0043-evidence-v1-20261017-fix/` (`$fix`).

Before new inference: reproduce BrokenPipeError without models; test corrected
parent ownership/persistence, closed/unavailable IPC, sanitized allowlist handling,
missing checkpoints, worker failure, parent exception, real memory and timeout
termination, memory-first precedence, identity and owned-descendant cleanup.
Only then permit one fresh isolated conversion with the exact same original
capture worker, changing its ignored output directory only. Keep 600 seconds,
3221225472 process bytes, CPU/two threads, FAST/cell matching and all frozen
source/Gold/model/configuration/dependency pins and offline restrictions.

Parent samples are journaled and flushed independently of the child; finally
performs cleanup and atomically persists the summary, including explicit UNKNOWN
when nothing was measured. Poll and recv share the same EOF/OSError handler.
Pipe closure never substitutes for process completion. Guard monitoring continues
until actual child exit, including after receipt of a completion message.
Stop on any resource breach or verification failure; no retry or budget change.
Compare the whole new private capture and completion metadata to the original,
then recheck each anchor classification/count, official scores, diagnostic order
and immutable fingerprints. The suspected decoder/font-map mechanism remains
UNKNOWN absent new direct evidence; no text repair or scorer change is authorized.

## Repair results and trustworthy resource evidence

**Exact scratch lifecycle error:** the original drain's try/except covered recv
only. Windows poll raises BrokenPipeError after a completed sender closes the
pipe. That exception exited the monitoring try; cleanup ran, but resource.json
was written after finally and was skipped. Peak/samples/exit metadata lived only
in parent memory. A deterministic model-free sender/closed-pipe reproduction now
observed BrokenPipeError after receiving complete; child exit 0, no live child,
zero model calls. The old real run's suppressed exception remains unretained;
this reproduction identifies the code defect without inventing its old trace.

**Scratch correction:** catch EOFError/OSError around both poll and recv, retain
only fixed sanitized phase/control messages, and continue monitoring process exit
after pipe closure. Parent owns every PID-identified sample and flushes its JSONL
journal. A nested finally cleans up owned processes and atomically persists the
resource summary, including on unexpected parent failures. Exceptions and invalid
IPC payloads are never serialized. The original scratch files are untouched;
the new runner reuses the original worker and capture hooks, with its output
directory changed only. Application IPC, extraction, scoring and configurations
remain unchanged. The guard still compares process bytes first, then elapsed time.

**Model-free corrected monitor self-test: 10 passed, 0 failed, 0 skipped; model
calls 0.** Cases: successful close; missing checkpoint (UNKNOWN); private IPC;
closed pipe while worker remains alive; memory breach; timeout with descendants;
worker failure; IPC unavailable; unexpected parent exception retaining samples;
simultaneous memory/time breach with memory-first precedence. Every case retained
real process identity, positive measured peak, sample journal, wall time and exit
status, with no surviving owned processes or synthetic private sentinel output.
The lower limits below apply only to synthetic test workers, never Docling:

| Synthetic case | Actual outcome | Peak bytes | Wall seconds | Exit / cleanup |
| --- | --- | ---: | ---: | --- |
| Closed-pipe worker, 0.9-second limit | timeout | 24018944 | 0.9633523999946192 | -15; terminated, none alive |
| Allocating worker, 64-MiB limit | memory_limit | 158138368 | 0.2096904999925755 | -15; terminated, none alive |
| Worker with descendants, 1.5-second limit | timeout | 24195072 | 1.5553166000026977 | -15; worker and 3 observed descendants cleaned |
| Parent exception | monitor_failure, as expected | 4481024 | 0.07758849998936057 | -15; one sample persisted, UNKNOWN phase |

Cleanup duration is included in wall time; crossing a synthetic deadline causes
termination, not a promise of zero termination overhead. Missing checkpoints
remain UNKNOWN; unavailable IPC alone never implies success. The self-test pass
record pins the exact monitor source used by the real run and gates its launch.

**New controlled conversion: complete, exit 0.** The guard did not fire; no retry.

| New run measurement | Observed value |
| --- | --- |
| Parent PID / actual spawned worker PID | 13172 / 25596 |
| Worker creation time, Unix seconds | 1792249922.5751886 |
| Runtime executable SHA-256 | `15b41a488c356c0e331facdea6c836a6cec021f12d5fde9844e7ca4a1aa0361a` |
| Executable identity | matches Python base runtime; worker's PPID is monitored parent |
| Parent-owned resource samples | 272 |
| Peak process working set | 2526875648 bytes = 2409.81640625 MiB |
| Wall, including start/exit/cleanup | 16.0444748000009 seconds |
| Maximum observed sample interval | 0.06746020000719 seconds |
| Unchanged process guard / timeout | 3221225472 bytes / 600 seconds |
| Worker outcome / exit | complete / 0 |
| Last received processing checkpoint | source_integrity |
| Completion received / monitor error | true / none |
| Terminate / kill needed | false / false; normal join completed |
| Observed descendants / survivors | 0 / 0 |

The sampled PID is the actual Python conversion process, not the Windows venv
launcher. Memory is psutil peak_wset with RSS fallback, covering the paired
worker's baseline, initialization, conversion and capture; it is not a separate
Docling-stage allocation measurement or a sum of the process tree. Sampling is
not a hard OS cap and may miss activity between observations. No independent
stage peak or native allocation owner is inferred. Original run peak, final wall,
exit status, phase sequence and descendants remain UNKNOWN as originally recorded;
new measurements do not retroactively recover them.

Actually received checkpoint sequence: baseline_extraction,
model_initialization, input_validation, model_initialization, conversion,
normalization, source_integrity; completion then received separately. The outer
worker's initialization notice precedes the extract_candidate input-validation
checkpoint, explaining the repeated initialization label. No exact native_build
checkpoint or internal decoder phase is claimed.

The new raw private capture SHA is still
`7a3ba4fe49d5afa6a990be07da5c8ba16e5ad7e9db93107fd8eba5ebaea22510`;
its complete bytes and completion metadata match the original. Independent reruns
of the original saved-text analysis/alignment scripts against the new capture
also produce identical analysis, anchor matches and diagnostic-order objects.
a1–a6 retain classifications above and changed-character counts **5/6/1/1/19/12**;
all four diagnostic order relationships still pass. Official pypdf/Docling scores
remain 6/6 -> 0/6 anchors, 6/6 -> 0/6 provenance and 4/4 -> 0/4 order; statuses
remain needs_review -> success. All input/model/configuration/code and four frozen
benchmark fingerprints above passed checks before and after conversion. No
nondeterministic evidence difference was observed. The suspected decoder/font-map
mechanism remains UNKNOWN; the 13 digit substitutions still demonstrate numeric
character-fidelity damage rather than a repaired candidate.

## Repair commands and verification

Executed with PYTHONPATH=src, PYTHONDONTWRITEBYTECODE=1 and the same three offline
environment flags. Each scratch command uses the unchanged optional runtime:

```powershell
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0043-evidence-v1-20261017-fix/reproduce.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0043-evidence-v1-20261017-fix/selftest.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0043-evidence-v1-20261017-fix/run.py preflight
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0043-evidence-v1-20261017-fix/run.py run
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0043-evidence-v1-20261017-fix/verify_run.py
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

All six commands returned exit 0. Reproduction output:

```json
{"child_alive": false, "child_exitcode": 0, "model_calls": 0, "observed_exception": "BrokenPipeError", "received": ["complete"]}
```

Self-test: passed=10, failed=0, skipped=0, model_calls=0. Preflight:
`PREFLIGHT_PASS: corpus=90 reviewed_gold=19 frozen_reports=4 input_model_code_pins=unchanged selftests=10/10`.
New-run postflight:
`POSTFLIGHT_PASS: frozen_pins=unchanged completion_and_full_private_capture=identical original_missing_peak=UNKNOWN`.
Independent verification: resource_validation=PASS, parent_owned_samples=true,
full_private_capture_identical=true, classifications_and_all_boundary_matches_identical=true,
model_calls_new=1, cleanup=PASS. Resource values are recorded above from the real
parent summary and independently cross-checked against every journal sample.
Focused unit tests: **159 passed in 7.18s**, none failed/skipped.
Broader unit suite, Ruff and formatting were not run for this report/scratch-only
repair. No full benchmark, production/parser/test change, model download, OCR,
GPU operation, new evaluation split or promotion occurred.

| Repair artifact (ignored) | SHA-256 |
| --- | --- |
| Original blocked report snapshot | `c779681f85edf4d2eb6eb51de8921637ed8f998bb62bed4408c6633174880f99` |
| Monitor | `104f7329f34b4cc4e68d2fc0bd1d7e4402bb3aede85ae03c742db502b1b0aa67` |
| Model-free self-test source | `3593552b3eddfe752037297003c164062f591a46cb8bf9562985a703ddad3ca6` |
| Model-free pass record | `b62eb7e21fec6c527956003a6a06f6aac09de39dbe78864331627a5042c6a83b` |
| One-conversion runner | `f28e20a76844a54eee9b6894a15025d3965262d61a8add85e6528436bf6b7e71` |
| Repair pre-registration | `ec317aeb59f7068f28aeba0ddfb84ce72162491da16faf241ce4a52fcb6bbbc0` |
| New parent resource summary | `c8f77dba25d2557cbd37719e99fad53769f819d5763bc4bc0ba00006cb9dc465` |
| New parent sample journal | `2b461b82488eeff7602cdaccbc826f61be893afc966e52de21e63d65b118078c` |
| Independent run verification | `2a8f690003810865d78eb35a6e69896f1e983da61f6cd2d65c861e297385e923` |

Final repair review commands:

```powershell
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0043-evidence-v1-20261017-fix/verify_report_fix.py
git add -- docs/eda/pdf_c1_0043_evidence_loss_diagnosis_v1.md
git diff --cached -- docs/eda/pdf_c1_0043_evidence_loss_diagnosis_v1.md
git diff --check
git diff --cached --check
git diff HEAD --name-only
git status --short
```

Privacy/scope verifier exit 0: privacy=PASS, ignored_scratch=PASS,
original_failed_monitor_evidence=PRESERVED, original_peak=UNKNOWN,
new_resource_evidence=PASS, six_anchor_findings=IDENTICAL,
input_gold_model_config_code_and_frozen_reports=UNCHANGED, additional_conversions=1.
Every focus Gold string and all 90 real source filenames/paths were excluded;
longer other Gold strings and credential patterns were also checked. Full staged
diff was reviewed, including the original report retained from the blocked step.
Both whitespace checks returned exit 0 with no output. Exact changed/staged-file
allowlist: this report only; all four original unrelated untracked entries remain
unchanged and unread. Only ignored scratch code was repaired; no application code
or tests changed. Root completion instructions were rechecked before committing.

ML-12's resource-verification blocker is resolved for the authorized repair run.
Original missing resource fields remain UNKNOWN. Outstanding c1-0040 table-locator
and c1-0049 furniture/order defects remain unresolved; native decoder/font-map
cause remains UNKNOWN. Docling remains a rejected production candidate. No ML-13
or other task was started.
