# Current-stage Extraction → Cleaning → Chunking stabilization

STATUS: **PASS within the verified implementation scope.** All reproduced,
safely correctable defects identified in this pass are fixed and committed.
The implementation is stable within the executed checks below. Full extraction
fidelity, release readiness and unsupported capabilities are not declared PASS.

## Scope and authority

Started on `main`, HEAD `540dbc8871ee004aff8d3704c706fe3d9c650143`, with the
previous uncommitted numFmt correction/tests/report and an unrelated untracked
engineering audit. The audit was excluded from every commit and remains unchanged.
The user's current instruction authorizes successive verified logical commits;
the earlier one-correction review stop no longer applies to this execution.

Root AGENTS/source map and extraction-benchmark, ingestion-change and data-quality
procedures applied. No affected nested AGENTS.md exists. Owner contracts:
[Extraction Strategy](../../DocLens_AI_Extraction_Strategy.md),
[Quality Policy](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[ML cleaning/chunking](../../DocLens_AI_ML_Quality_Strategy.md#ML-CHUNK), and the
[frozen fidelity protocol](extraction_fidelity_protocol_v1.md).

CHANGED: four existing implementation/evaluation files (`extraction/parsers.py`,
`chunking/core.py`, `extraction/fidelity_gold.py`, `eda/data_quality_gate.py`), nine
focused public synthetic test files, the prior numFmt report and this report.
No dependencies, models, parser replacements, GPU experiments, schema migrations,
RAW, frozen Gold, historical results, project instructions or unrelated code changed.

## Independently reviewable fixes

Each row followed reproduction → cause → correction → regression → verification.
Counts in the final column describe overlapping focused suites, not additive totals.

| Commit | Confirmed defect and correction | Reproduction and focused verification |
| --- | --- | --- |
| `6788cc0` | XLSX explicit format IDs below 164 were falsely rejected. Preserve explicit format codes and retain malformed-ID checks. | Prior new suite: 9 failed / 7 passed; reverified 16/16 before this commit; 13-original OOXML oracle passes. |
| `6c83a5c` | Recognized dialog/chart sheet parts were reported as corruption. Validate relationship/root identity and report `unsupported_format`; discard partial output. | 2 failures reproduced; 35 passed with type/root mismatch controls. |
| `fd7d0eb` | DOCX bounded footnote-reader limits were all flattened to corruption. Retain `limit_exceeded` for resource/time guards; malformed/source failures remain corruption. | 8 limit cases failed before correction; 83 passed afterward. |
| `8797e2e` | Extraction linked decimal-equivalent note IDs, but chunking compared their lexical strings and lost reference context. Match numeric identities while preserving original lexical IDs and part identities. | 3 relationship failures reproduced; 165 chunking/cleaning/offset/context tests passed. |
| `7ba515b` | Unsupported content in textless headers/footers could return success and become indexable. Scan actual ancillary XML parts for existing unsupported-content warnings and preserve review holds. | 6 cases reproduced; 115 parser/note/fidelity tests passed. |
| `d73ac41` | PDF range verification selected a requested block but used all page blocks for length checks. Restrict verification to the selected block. | 1 false verification reproduced; 73 passed / 1 symlink skip. |
| `2997932` | Gold same-row/column assertions could cross block or ancillary-part scope. Reject contradictory source scopes at validation. | 2 invalid relationships accepted before correction; 36 passed; all 19 unchanged real Gold records accepted. |
| `320f9f4` | Public Fidelity Gold loading accepted duplicate JSON keys, including escaped/nested keys, silently taking the final value. Reject decoded duplicate keys before strict JSON-mode model parsing. | 3 ambiguous inputs accepted before correction; 74 passed / 1 symlink skip. No annotation bytes changed. |
| `c05ea8b` | XLSX shared strings were read from a hardcoded filename, accepting orphan/stale values even when the actual relationship pointed elsewhere. Resolve the unique internal workbook relationship and validate its root. | 2 source-selection failures reproduced, including a wrong stored value; 40 passed with five shared-string success/failure controls. |

DESIGN: correction of existing parsing, source identity, trust classification and
validation boundaries. Unsupported sheet extraction stays failed; unsupported DOCX
content stays review-held. No partial workbook publication, invented table/grid,
calculated formula, guessed ancillary body index or automatic evidence promotion.
Microsoft's [sheet reference](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-sheets)
identifies worksheet, chart sheet and dialog sheet as distinct sheet kinds; these
are not interchangeable worksheet roots.

## Four remaining Office failures: resolved diagnosis

All original bytes, size and SHA matched the existing 60-source manifest.

| Opaque source | Current outcome | Evidence / disposition |
| --- | --- | --- |
| `e2-office-081ca479f8d7eebf` | failed / unsupported_format | Three worksheet relationships plus one dialogsheet. Unsupported content is explicit; no partial extraction published. |
| `e2-office-545836d5b9807326` | failed / unsupported_format | Same supported/unsupported part composition; corruption classification corrected. |
| `e2-office-51bd4fd25d37dd92` | failed / limit_exceeded | Character counter reaches 5,000,008 against unchanged 5,000,000 limit; 236,261 stored cells encountered in the sheet inventory. |
| `e2-office-969193c6e25c5c79` | failed / limit_exceeded | Character counter reaches 5,000,025 against unchanged 5,000,000 limit; 208,461 stored cells encountered in the sheet inventory. |

The two limits are protective rejections, not demonstrated defects. They count
extracted value/formula/format metadata under the existing policy. Neither limit
was raised or bypassed. All four remain in attempted/failed denominators.

## Final fidelity, source and downstream checks

Implementation snapshot for final executions:
`c05ea8b875ac5bbb36da940e0e16db6b29e12b0e`; subsequent report commit changes no runtime code.
Fresh local evidence is under ignored
`evaluation-output/stabilization-complete-20261021/`.

| Corpus/format | Attempted | Success | Needs review | Failed |
| --- | ---: | ---: | ---: | ---: |
| Legacy PDF | 30 | 27 | 3 | 0 |
| Legacy DOCX | 30 | 10 | 20 | 0 |
| Legacy XLSX | 30 | 15 | 15 | 0 |
| Additional Office, both formats | 60 | 17 | 39 | 4 |

Legacy `c1-0017` changes from success to needs_review because previously unflagged
header content is now correctly held. Ten other DOCX records gain warning detail
without changing their review status. **Every block, sheet, cell, note reference,
literal and source locator in all 84 previously nonfailed legacy captures is
identical to the prior captured output.** Six previously failed XLSX sources
recover as documented in the [numFmt report](xlsx_numfmt_stabilization_20261021.md).
No review-held legacy document becomes success. Office status totals are unchanged
from the post-numFmt run; changes are ancillary warnings and the two unsupported
sheet error categories. No new Office source fails.

Both complete pipeline replays agree on **365 byte-identical non-runtime files**
per run, including actual extraction captures, source units, both chunk sets,
per-label retention, gate output and completion hashes. Their diagnostic fingerprint:
`def26f496063e3b62727952190c345df06987ad462244219639c0dd3240f0ee4`.
Office's own two isolated passes also agree on every non-runtime field, with
fingerprint `1eca7a3a3855a5ada3b1d41b723079f6ec00d9810508c9aba5e14c96da90e40f`.
Both full populations remain 90/60. Current RAW identity, manifest, Gold, rights
and unchanged-code pins were reconciled with retained evidence. The unrelated
audit's SHA also remains unchanged.

Gold remains 19 existing real reviewed attestations, not new independent review.
The expanded Gold byte SHA is unchanged:
`f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf`.
All current reviewed metrics equal the unchanged post-numFmt baseline:

| Metric | Passed / expected |
| --- | ---: |
| Required anchors | 115/126 |
| Partial reading order | 43/58 |
| Table cells/spans | 28/52 |
| Same-row/column relationships | 13/33 |
| Provenance | 103/139 |
| Exact stored values / formulas / caches, each | 13/13 |

The independent local OOXML oracle again reconciles all 13 recovered sources:
19,376 meaningful cells, 71 sheets, 5,655 formula elements/caches, 1,149 local
formula definitions and 595 merged ranges. Original numeric strings, raw values,
formula attributes, formats and cell identities are checked separately. These
checks establish structural preservation, not recalculation/display correctness.

Cleaning accounts for **104,485 nonempty extracted-field observations with zero
unrendered fields or non-whitespace losses**. The 107,132 literal-field checks
preserve every non-whitespace sequence; prose whitespace normalization remains
explicit. The exact-value XLSX oracle and regression tests separately cover literal
whitespace and precision. All 1,432 nonempty TextBlock units map 471,700 normalized
code points to actual original text; original 472,642 characters reconcile with
787 trimmed outer-whitespace characters and 155 whitespace-only characters.
Tables/XLSX/generated reference units continue to state that no original TextBlock
map is available; no RAW-byte, glyph or XML-character offsets are invented.

Both fixed-size and structure-aware chunking have zero document-local failures,
zero oversized emitted chunks and complete provenance on emitted chunks. They
retain all **1,887,173/1,887,173 eligible source characters**, producing 1,802 and
2,064 chunks respectively. Each chunks 52 documents and skips all 38 review-held
documents. All **56/56 eligible located reviewed anchors** survive wholly in a
chunk. This conditional coverage does not claim that all corpus evidence is eligible
or that all semantic relationships fit in one chunk.

The existing data-quality gate returns **PASS for its frozen integrity/readiness
checks**. This does not close QG-00/01/02/03 semantic/release qualification.

## Exact verification commands and results

The full suite supersedes the overlapping focused checks in the fix table:

```powershell
$env:PYTHONPATH=(Get-Location).Path
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.venv/Scripts/python.exe -B -m pytest -q --tb=short --strict-config --strict-markers -o faulthandler_timeout=60 -p no:cacheprovider --basetemp=evaluation-output/stabilization-complete-20261021/full-tests --junitxml=evaluation-output/stabilization-complete-20261021/full-tests.xml
```

**Exit 0: 1,867 passed, 158 skipped, 331.12 s.** Local permissions were used to
avoid the known Windows asyncio socketpair sandbox stall. Skips: 141 unconfigured
PostgreSQL, three unconfigured Qdrant, one unconfigured S3, eight explicit opt-in
private/GPU-capture/replay checks, four missing browser-runtime checks and one
Windows symlink-privilege check. These are not reported as passing integrations.
No persistence, tenant/ACL, delete, retry or publication logic changed. Relevant
in-memory ingestion and canonical-provenance regressions ran within the full suite.

Additional PDF source-alignment/cell-recovery regression execution:

```powershell
.venv/Scripts/python.exe -B -m pytest tests/unit/test_pdf_cell_recovery.py tests/unit/test_extraction_v2.py tests/unit/test_ml28_evidence.py tests/unit/test_ml28_review.py -q --tb=short -p no:cacheprovider --basetemp=evaluation-output/stabilization-complete-20261021/pdf-evidence-tests
```

**Exit 0: 116 passed, 12.09 s**, including wrong numeric/sign assignments,
duplicate glyph ownership, crossed/unmapped glyphs, source mismatch and ambiguous
evidence holds. No new table-recognition method or private candidate was run.

Final local fidelity/pipeline commands, all exit 0:

```powershell
.venv/Scripts/python.exe -B -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output-dir evaluation-output/stabilization-complete-20261021/legacy-final-2
.venv/Scripts/python.exe -B evaluation-output/stabilization-complete-20261021/pipeline_run.py --output evaluation-output/stabilization-complete-20261021/pipeline-1
.venv/Scripts/python.exe -B evaluation-output/stabilization-complete-20261021/pipeline_run.py --output evaluation-output/stabilization-complete-20261021/pipeline-2
.venv/Scripts/python.exe -B -m tools.extraction_quality.extraction_v2 baseline --manifest docs/eda/extraction_corpus_v2_manifest.json --root evaluation-output/extraction-v2-20261021/office-discovery --output evaluation-output/stabilization-complete-20261021/office-final
.venv/Scripts/python.exe -B evaluation-output/stabilization-complete-20261021/verify_final.py
.venv/Scripts/ruff.exe check src tests tools alembic
.venv/Scripts/ruff.exe format --check tests/unit/test_xlsx_number_formats.py tests/unit/test_xlsx_sheet_classification.py tests/unit/test_docx_ancillary_limits.py tests/unit/test_docx_note_context.py tests/unit/test_docx_ancillary_warnings.py tests/unit/test_pdf_source_unit_bounds.py tests/unit/test_fidelity_relationship_scope.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_xlsx_shared_string_source.py
git diff --check
git diff --cached --check
git status --short
```

`pipeline_run.py` is a new local copy of the existing diagnostic, pinned to the
final implementation commit and new output directory. It reuses the same counters,
retention definitions, Gold, 1,200/120 chunk settings, logical limits and 1,200-second
wall budget. Protocol metadata explicitly records stabilization verification.
Historical instrumentation, outputs and protocols were not rewritten. A preliminary
`legacy-final-1` run before the final validator/shared-string fixes is retained;
it is not used as an identical-code repetition. Final repetitions are pipeline-1/2.

Ruff passes; all nine new test files pass formatting. One initial recheck attempted
pytest before creating its new basetemp parent, causing 16 setup errors; after the
parent was created, all 16 passed. A new note-context test initially used the wrong
test-side attribute name; it was corrected to the existing `Chunk.provenance`, and
the 165-case/full suites passed. Expected pre-fix failures and these setup/harness
failures are not hidden or counted as PASS.

Runtime is retained separately: complete pipeline runs took 82.711/82.767 seconds.
Office passes report P50/P95 2.219/5.578 and 2.031/4.781 seconds, sampled peak tree
RSS 312,164,352/306,577,408 bytes. Tests/diagnostics overlapped on the local host;
these are not causal speed comparisons, throughput claims or production SLOs.
Office preserves its 60-second/1-GiB worker controls. Legacy hard RSS isolation
remains unqualified. Environment: Windows, Python 3.12.3, pypdf 6.20.0,
python-docx 1.2.0, openpyxl 3.1.5, Pydantic 2.14.0. Pipeline audit hooks deny network;
no model, GPU, upload, indexing or generation work occurred.

## Remaining boundaries and completion decision

REMAINING REPRODUCIBLE, SAFELY FIXABLE BUGS: **None identified by this pass's source
inspection, targeted reproductions, complete test run and frozen diagnostics.**
This is a scoped engineering conclusion, not proof of absence of every possible bug.

Known evidence failures remain explicit:

- Native PDF still misses 11 required anchors, fails 24 PDF cell/span assertions
  and lacks verified table relationships. These baseline capabilities cannot be
  established by reassigning text, inventing cells or weakening validation.
- [c1-0040](pdf_c1_0040_table_locator_alignment_v1.md) retains unresolved source/Gold
  table-grouping conventions and native cell fragmentation. The existing
  [five-PDF packet](pdf_table_gold_review_packet_v1.md), including c1-0033, needs
  independent original-document adjudication. No reviewed grid was fabricated.
- One present DOCX ancillary anchor has no agreed mapping between frozen
  `part_index` and actual part URI/XML path. Its frozen scorer remains unsupported;
  footnote/header/footer source identities remain explicit and review-held.
- Independent comprehensive Gold, rendered XLSX display, semantic header/unit/period
  bundles, multilingual/family coverage and approved release thresholds remain
  **BLOCKED or NOT_EVALUATED**, as applicable. Existing Gold review metadata is an
  attestation, not newly performed independent review.
- Dialog/chart extraction and the two Office character-limit sources remain
  intentionally unsupported/rejected. Existing error/warning populations stay visible.
- Real-service integration, browser review flows and production recovery/load/E2E
  qualification remain unexecuted where their prerequisites are unavailable.

The requested safely fixable implementation work is complete within this verified
scope. Known native fidelity limitations still prevent a whole-stage semantic or
production readiness declaration. No future roadmap work or follow-up experiment began.

COMMIT: Nine focused Conventional Commits listed above; this consolidated report is
recorded separately. No push was requested or performed.

GIT STATUS: no staged/task changes; only the preserved unrelated audit remains:

```text
?? docs/eda/independent_engineering_audit_20261020.md
```
