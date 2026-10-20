# ML-30B — assisted PDF table cell proposals

This adds an optional assisted workflow to the [visual workbench](ml30a_visual_pdf_annotation.md).
It uses the existing local CPU pypdfium2 renderer (tested 5.14.0), Python's standard
library, and the authorized original PDF. No dependencies or models were downloaded;
no GPU, Docker, external rendering service or production path is involved.

## Use with existing drafts

Start with the existing ML-30A command and **`--resume`** for
`evaluation-output/ml29-human-review`. Keep one writer and never reset that directory.
The workspace/worksheet version is unchanged; existing drafts and manual cells survive.

1. Inspect the original page. Create/select a table and assign its bbox with ML-30A.
   Set its `row_count` and `column_count` in the worksheet JSON, then save. Choose that
   saved table (or one of its cells) in **Assign to**. Counts are reviewer declarations.
2. Click **Propose saved table grid** and confirm the assistance disclosure. This
   analyzes original ruling strokes and text; it does not read legacy assertions or
   legacy parser predictions. It does not change the worksheet.
3. Inspect the purple grid overlay and zero-based row/column labels on the original
   raster. Diagnostics show the method, source/page/render binding, detected divider
   counts, proposed coordinates and proposal fingerprint. Zoom/scroll work as before.
4. Inspect every proposed literal against the original. Missing/unreliable text stays
   `null`; no OCR or guessing occurs. Edit bboxes, literals or row/column assignments
   in **Editable proposed cells**, then **Save corrections and redraw overlay**.
   Corrections must cover the declared slots with contained, non-overlapping 1×1 cells.
   Original machine candidates are retained separately from edited cells.
5. Reload/restart with `--resume`, select the same saved table, then **Resume saved
   proposal**. Regenerating the same table preserves saved corrections. A changed
   saved table gets a separate proposal file; existing versions are retained.
6. **Explicitly accept missing cells into draft** requires confirmation. Acceptance
   appends only unoccupied slots. Every existing cell is preserved exactly, including
   manually entered text, bbox, uncertainty, evidence and notes. Existing ambiguous
   positions, duplicate slots, ID conflicts or geometry overlap block the whole save;
   resolve these deliberately rather than overwriting a manual cell. Raster rounding
   can reveal small boundary conflicts that require a proposed-bbox correction.

Accepted cells carry stable proposal-derived IDs and `proposal_origin` metadata;
the table retains `assisted_grid_proposals`. Their row/column, unit spans, bboxes and
available source text are proposals explicitly accepted into a draft. Header roles,
uncertainty, evidence references, relationships, structural completeness and reviewer
attestations remain unset. Existing template/reviewer/completion fields are unchanged.
No verified Gold is generated or exported.

## Assistance and independent review

Requesting machine grid/text proposals ends blind independent review for that document
in this workspace, even if the proposals are subsequently rejected. The saved sidecar
records assistance without filling in the reviewer's attestations. The workbench blocks
the existing independent Gold freeze for documents with proposal sidecars or accepted
assistance metadata. A separate, genuinely independent review is still needed for Gold;
this step does not create that review or relax ML-28 validation. The standalone ML-28
validator also rejects retained assistance markers in either validation mode, so direct
validation/export cannot promote these assisted worksheets. Do not remove provenance
or falsely attest that parser predictions were unseen.

Legacy assertions stay locked behind the existing whole-cohort freeze/adjudication
workflow. The assisted workspace cannot supply that independent evidence. Independently
reviewed worksheets without assistance continue through the existing workflow unchanged.
QG-00–03 remain **NOT_EVALUATED**, experiment **INCONCLUSIVE**, production enrichment disabled.

## Algorithm and limitations

`ml30b-ruled-raster-v1` analyzes the controlled original-page RGB raster. It groups thin,
dark gray/black ruling bands, requires visible outer borders near the selected bbox,
and requires the declared number of internal boundaries. It detects nonuniform row
heights/column widths; it never substitutes equal spacing when detection fails. Each
divider is also checked over every local row/column segment to reject partial/merged
boundaries. Solid fills are not treated as grid lines.

Fixed engineering heuristics: RGB channels below 200; axis coverage at least 80%;
local segment coverage at least 90%; outer-border proximity 2 PDF points; ruling-band
width at most 3 points (minimum raster allowance 2 pixels). These are conservative
detection rules, not approved quality-gate thresholds. Declared limits are 256 rows,
64 columns and 2048 cells, with at least four raster pixels per declared row/column.
The renderer's existing 3000-pixel edge cap and verified unrotated mapping still apply.

Borderless, colored/light/dashed/heavy or low-resolution rulings, merged cells,
unsupported page transforms and mismatched counts remain **UNRESOLVED**. Multi-page
table targets are rejected before proposing a single-page grid. No cells
are automatically guessed for those layouts; use manual annotation or a separate
review process. This stage supports only regular 1×1 cell topology, including
nonuniform physical sizes. Human corrections cannot turn an unresolved machine grid
into an accepted regular grid through this proposal endpoint.

Text comes from PDFium's original text layer, not Gold. Glyph boxes must map uniquely
inside a cell, have valid Unicode mappings and unrotated printable characters. Cross-cell
or interleaved glyphs, uncertain spacing and missing text remain unfilled. Character
ownership avoids leaking a neighbor cell or a generated trailing separator. Interior
PDFium separators remain provisional text-layer reconstruction; ambiguous repeated
spacing is left unfilled. This does not prove visible-text fidelity, OCR correctness
or semantic truth. Inspect every proposed value, especially numbers and font mappings.

Proposals/corrections stay under ignored `grid-proposals/` sidecars in the selected
workspace, bound to packet/source/page/table/render/method fingerprints. Original
candidates are fingerprinted; correction saves use a revision check. Acceptance uses
the existing atomic worksheet save and cannot be repeated against a changed table.
All new routes require the existing loopback session, same-origin and POST-token checks;
responses are `no-store`. No private page/text is sent to browser automation or an
external service. Local filesystem ownership remains the ML-29 trust boundary.

## Local c1-0033 check

The existing reviewer-selected bbox and declared 22×2 counts were used without
document-specific geometry/content in the implementation. The original supplied 21
internal horizontal dividers and one vertical divider, producing **44 cell boxes**
in one grid-generation operation, without 44 manual cell rectangles. **20 cells** had
conservative source-text proposals; **24** remained unfilled. These are machine
proposals, not human-verified values.

The actual workbench proposal endpoint was checked twice in an isolated ignored copy
of the saved workspace and returned identical proposals. The existing manual cell
and live saved draft were unchanged. No real-document proposal was accepted as human
review. RAW, frozen Gold/packet, the saved review workspace and unrelated audit were
checked by hash: **119 protected files unchanged** across **90 RAW sources / 5 PDFs**.
Private proposal contents remain in ignored local evidence only.

## Verification

Focused tests cover regular/nonuniform/merged/borderless/solid-fill tables, original
text assignment and ambiguous spacing, determinism, containment/ordering, manual-cell
preservation/conflicts, corrections, explicit acceptance, resume, forged/stale records,
frozen drafts, assistance disclosure and route security. A real headless Edge test
checks the painted overlay, zoom, corrections, reload, cancel/explicit acceptance and
unchanged attestations using public synthetic PDFs. Existing ML-30A/29/28 regressions
are included. Optional renderer/browser tests require local dependencies; the executed
verification sets them explicitly so required cases are not skipped.

Executed on 20 October 2026 from `3840a47df306ea9db20e70a74dd982f4ad55bb58`:

```powershell
$env:PYTHONPATH='src;.'
$env:ML30_NODE='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:ML30_NODE_MODULES='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
.venv/Scripts/python.exe -B -c "import sys; sys.path.append(r'C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))" -q -s --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/ml30b-tests-final3 tests/unit/test_pdf_grid_proposals.py tests/unit/test_pdf_review_visual.py tests/unit/test_pdf_review_workbench.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_ml28_review.py tests/unit/test_ml28_evidence.py --tb=short
# 162 passed in 89.89s, no skips, including both actual browser paths.
# Final single-page guard added afterward; all affected grid paths rerun:
.venv/Scripts/python.exe -B -c "import sys; sys.path.append(r'C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))" -q -s --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/ml30b-grid-final tests/unit/test_pdf_grid_proposals.py --tb=short
# 25 passed in 29.85s, no skips.
.venv/Scripts/ruff.exe check tools/extraction_quality/pdf_grid_proposals.py tools/extraction_quality/pdf_review_workbench.py tools/extraction_quality/pdf_review_validation.py tests/unit/test_pdf_grid_proposals.py tests/unit/test_pdf_review_visual.py
.venv/Scripts/ruff.exe format --check tools/extraction_quality/pdf_grid_proposals.py tools/extraction_quality/pdf_review_workbench.py tools/extraction_quality/pdf_review_validation.py tests/unit/test_pdf_grid_proposals.py tests/unit/test_pdf_review_visual.py
# All checks passed; 5 files already formatted.
& $env:ML30_NODE --check tools/extraction_quality/pdf_review_ui/grid.js
& $env:ML30_NODE --check tools/extraction_quality/pdf_review_ui/annotation.js
& $env:ML30_NODE --check tools/extraction_quality/pdf_review_ui/workbench.js
& $env:ML30_NODE --check tests/unit/pdf_grid_proposals.browser.cjs
.venv/Scripts/python.exe -B -c "import sys; sys.path.append(r'C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'); exec(compile(open('evaluation-output/ml30b/local_probe.py', encoding='utf-8').read(),'local_probe.py','exec'))"
# Local-only integrity/proposal helper: 44 deterministic c1-0033 boxes, 20 text proposals;
# saved draft/manual cell unchanged, 119 protected hashes unchanged; private-content scan clean.
git diff --check
git diff --cached --check
```

Initial focused checks exposed PDFium-generated trailing separators, collapsed repeated
spaces and a manual-cell boundary-overlap case. Text ambiguity now remains unfilled;
manual overlap blocks acceptance rather than changing a human cell. Both browser
workflows passed after these fixes. Windows loopback/browser checks used sandbox
escalation; no package/model/browser download or unrelated benchmark was run.
