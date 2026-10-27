# EX-01 native failure root-cause triage

27 October 2026. **STATUS: PASS for diagnosis: 8/8 CONFIRMED, 0 UNRESOLVED.**
All eight remain failed observations; no parser fix or successful extraction is claimed.
Independent Gold, semantic quality and QG-01 remain **NOT_EVALUATED**.

## Scope and evidence

Sources: root `AGENTS.md`, the extraction-benchmark skill's diagnosis-only
procedure, [Extraction Strategy](../../DocLens_AI_Extraction_Strategy.md), and
the [EX-01 report](extraction_native_dev_baseline_20261027.md). Starting branch
`main`, HEAD `fea77486db6c31872854a292ffeca490d63614c0`.

The existing baseline verifier returned PASS with 199 attempted/accounted in
each pass, zero deterministic mismatches and evidence fingerprint
`a1ea7e53acedb2bfc1dde7e6db434ffb8dc02b20b2fb71c2631dde53155d3dab`.
Both saved manifests contain exactly the same eight failed opaque identities,
matching native captures, categories and source SHA/size/format. Every source
is evaluation-admitted DEV, outside reserved QA/sealed components. The existing
readiness release verifier, rights/family checks and source asset validator were
reused. No filesystem discovery selected documents.

All 16 saved failed-document console logs are empty. Every corresponding worker
completed, returned native status `failed`, and has no worker `error.json`.
The logs therefore cannot establish the inner exception or exact limit trigger.

The focused `native_failure_triage.py` helper adds source ZIP/OOXML inspection,
failure reconciliation and bounded exception tracing. It uses the unchanged
`extract_file`, default `ExtractionLimits`, existing archive/XML helpers and
`tools.pdf_ocr_candidate.benchmark.command` resource monitoring. It does not
relax guards, alter parser results, execute formulas or add dependencies.

Only the two previously unresolved limit cases and one DOCX case were replayed,
once each. Every replay's entire native `ExtractionResult` fingerprint matches
the saved failed capture from both passes. The five unsupported-sheet cases
were diagnosed without replay. There was no full-corpus extraction rerun.

## Diagnosis table

All rows are CONFIRMED. IDs below are the exact EX-01 opaque manifest identities.

| Opaque document ID | Format / observed error | Confirmed trigger | Confidence |
| --- | --- | --- | --- |
| nd-1c3d30c3335d0426b8f9c8c9 | XLSX / limit_exceeded | Character counter 5,000,025 exceeds 5,000,000 | Direct default-limit exception and full capture agreement |
| nd-416be68468a91d5054e764ed | XLSX / unsupported_format | Whole-workbook rejection at a chart sheet | Original relationship/root and unique rejection branch |
| nd-5a3bd131f298ff118fd45d6f | XLSX / unsupported_format | Whole-workbook rejection at a chart sheet | Original relationship/root and unique rejection branch |
| nd-6b5329af6d7cca70304b186a | XLSX / unsupported_format | Whole-workbook rejection at a dialog sheet | Original relationship/root and unique rejection branch |
| nd-948533983e76836d3065a621 | XLSX / limit_exceeded | Character counter 5,000,008 exceeds 5,000,000 | Direct default-limit exception and full capture agreement |
| nd-c0bcd0ec83a8f0a82275fc5f | XLSX / unsupported_format | Whole-workbook rejection at a chart sheet | Original relationship/root and unique rejection branch |
| nd-d9e5216c2a50346a1ed54de7 | XLSX / unsupported_format | Whole-workbook rejection at a dialog sheet | Original relationship/root and unique rejection branch |
| nd-ea8ddac53634dab4ab330820 | DOCX / extraction_failed | First body child is an XML comment whose tag lacks `rsplit` | Original `_Comment`, exact AttributeError and full capture agreement |

All eight pass the current Office archive validator. The unsupported-sheet
workbooks contain ordinary worksheets alongside the chart/dialog sheet: one
worksheet in each chart-sheet workbook, three in each dialog-sheet workbook.
`_extract_xlsx` explicitly rejects those matching relationship/root types at
parser line 799. This establishes the rejection mechanism, not that extracting
the remaining worksheets would produce correct output.

Both limit cases fail at `_extract_xlsx`, line 859. They are not archive/compression
failures, stored-cell-limit failures or measured OOMs. The character counter includes
value, formula, repeated number-format strings and formula attributes, as implemented
at lines 852-859. It is not visible prose alone. The precise cost split was not measured.

The DOCX fails at `_extract_docx`, line 320, before any body text is emitted.
Its first body child (ordinal 0) is an XML `_Comment`, not a Word reviewer-comment
annotation. Its non-string tag has no `rsplit` method. The body traversal calls
`child.tag.rsplit`; the generic outer catch converts this `AttributeError` to
`extraction_failed`. The source contains one such non-element body child.
Later extraction behavior past this first trigger has not been evaluated.

## Ranked mechanisms and exactly one next fix

| Rank | Mechanism | Affected documents | Interpretation |
| --- | --- | ---: | --- |
| 1 | Whole-workbook rejection of unsupported sheet kinds | 5: three chart, two dialog | Explicit capability/policy limitation |
| 2 | Default extracted-character guard | 2 | Confirmed safety-guard activation |
| 3 | DOCX body XML-comment tag handling | 1 | Confirmed implementation defect |

**The single next bugfix candidate is DOCX XML-comment handling in
`_extract_docx`, around parser line 320.** Skip XML comment and other non-element
nodes before element-tag string operations. Preserve physical XML ordinals and
warnings for real unsupported elements. Add a comment-before-paragraph regression
and verify preserved text/provenance under native defaults. This task includes a
synthetic diagnostic reproduction of the current failure; it does not implement
the fix or claim recovery.

Private per-document recommendations also record that unsupported XLSX sheets
could be considered for explicit `needs_review` handling while retaining supported
worksheets, subject to output/status-policy verification. The two character guards
should remain intact pending bounded representation-cost analysis. These are
triage notes, not additional next bugfix candidates or implemented changes.

## Execution and private evidence

The three diagnostic workers used existing sampled controls: 2 GiB process-tree
RSS, 90 seconds wall, 32 MiB output, 20 ms sampling. These are sampled research
guards, not an OS sandbox or hard commit cap. Timing includes child startup and
tracing overhead; it is not a performance result.

| Replayed case | Diagnostic wall seconds | Sampled tree peak RSS bytes | Native result |
| --- | ---: | ---: | --- |
| nd-1c3d30c3335d0426b8f9c8c9 | 7.188 | 256348160 | Same limit_exceeded capture |
| nd-948533983e76836d3065a621 | 6.937 | 352915456 | Same limit_exceeded capture |
| nd-ea8ddac53634dab4ab330820 | 2.360 | 172953600 | Same extraction_failed capture |

No diagnostic timeout, resource-limit or worker failure occurred. A subsequent
source-causal refinement reread the eight bound packages and sealed traces with
**zero additional extraction replays**. The private ledger retains source assets,
package relationships, trace functions/lines, confidence, unresolved boundaries,
recommendations and both baseline capture/log references and hashes.
Repeating this metadata-only refinement into a fresh private directory produced
two byte-identical artifacts (`ledger.json` and `COMPLETE.json`) and the same final
fingerprint, again with zero extraction replays.

Original trace evidence fingerprint:
`09cf449815ed575240274163fe6514dde65d128e7032cc6f172bd207264138b9`.
Final diagnostic evidence fingerprint:
`ebcb73fdc6529cdd0a67853614db1a9574e95c7658f1004451e772af1b5cb2e0`.
Runtime/package inputs and native implementation match EX-01's pins. The final
preservation check verifies the prior baseline's complete artifact inventory,
all eight original identities, diagnostic artifacts and ignored/untracked outputs.
Source names, text, values, worksheet names and exception payloads are not published.
The exact private ledger location is in the task handoff.

## Executed verification

Commands from repository root:

```powershell
.venv/Scripts/python.exe -B -X utf8 -m tools.extraction_quality.native_dev_baseline verify --output evaluation-output/extraction-native-dev-baseline-20261027/run-1
.venv/Scripts/python.exe -B -X utf8 -m tools.extraction_quality.native_failure_triage run --output evaluation-output/ex01-native-failure-triage-20261027/run-1
.venv/Scripts/python.exe -B -X utf8 -m tools.extraction_quality.native_failure_triage refine --input evaluation-output/ex01-native-failure-triage-20261027/run-1 --output evaluation-output/ex01-native-failure-triage-20261027/final
.venv/Scripts/python.exe -B -X utf8 -m tools.extraction_quality.native_failure_triage refine --input evaluation-output/ex01-native-failure-triage-20261027/run-1 --output evaluation-output/ex01-native-failure-triage-20261027/final-reproduction
.venv/Scripts/python.exe -m pytest tests/unit/test_native_failure_triage.py -q --basetemp evaluation-output/ex01-triage-tests-final --junitxml evaluation-output/ex01-triage-tests-final.xml
.venv/Scripts/ruff.exe check tools/extraction_quality/native_failure_triage.py tests/unit/test_native_failure_triage.py
.venv/Scripts/ruff.exe format --check tools/extraction_quality/native_failure_triage.py tests/unit/test_native_failure_triage.py
.venv/Scripts/python.exe -B -X utf8 evaluation-output/ex01-native-failure-triage-20261027/verify_final.py
git diff --check
git diff --cached --check
git status --short
```

Results: saved baseline PASS; targeted diagnostic and refinement exited 0, each
accounting for 8/8 with CONFIRMED classifications. Focused tests: **18 passed,
0 failed, 0 skipped, 3.68 seconds**. Ruff check/format passed. Tests cover paired
denominators, missing/duplicate/TEST/excluded/drifted inputs, absent captures,
operational failures, source-sheet/root binding, exact limit evidence, source
drift, actual worker invocation, XML-comment reproduction and artifact tampering.
The final verification returned PASS: eight confirmed, zero unresolved, three
native diagnostic replays; all sources, prior baseline artifacts, pinned native
code and dependencies unchanged; private outputs ignored and untracked. The two
refinement outputs were compared byte-for-byte and agreed. Git whitespace checks
passed, including `git diff --no-index --check -- NUL <file>` on each new task file;
Git emitted only LF-to-CRLF notices. The staged diff is empty.

Initial tests had three synthetic-fixture setup failures (missing OOXML relationship
namespace and a non-ZIP fixture rejected by source admission); corrected before the
passing suite. Initial unused imports/line length were corrected. An early diagnostic
launch was interrupted during read-only saved-evidence verification, before output
creation or any original replay, to correct its worker module invocation. The final
run above completed without dropped cases.

## Completion boundary

There are no unresolved observed triggering mechanisms. Correct post-fix extraction,
XLSX partial-output policy, full character-cost breakdown, independent semantics and
quality acceptance remain unverified/out of scope. All original native failures
stay in the baseline denominator. No production parser, Gold, frozen release or
previous baseline artifact was modified. No corpus preparation or cloud work.

CHANGED: diagnostic helper, focused tests and this sanitized report; detailed evidence
is ignored locally. COMMIT: **Not created; user requested no commit.** The pre-existing
Kaggle deletion and four untracked evaluation reports remain outside this task.
