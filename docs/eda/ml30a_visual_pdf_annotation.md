# ML-30A — visual geometry for the local PDF review workbench

The ML-29 worksheet, independent-review/freeze/adjudication contracts and workspace
version are unchanged. Geometry is a human selection, never reviewed Gold by itself.
QG-00–03 remain NOT_EVALUATED, experiment INCONCLUSIVE, production enrichment disabled.

## Local renderer and resume

Visual capture optionally uses **pypdfium2**, a free open-source CPU PDFium binding
(tested 5.14.0). It is needed because the native browser PDF viewer cannot expose a
reliable coordinate transform. No other image package is needed: the server encodes
RGB PNGs using Python's standard library. This step used the already available local
bundle; no packages, models or browser binaries were downloaded. For another machine,
make `pypdfium2==5.14.0` available in the chosen Python environment. Without it, the
original viewer and JSON workflow remain available with a clear capture diagnostic.

Use the [ML-29 command](ml29_pdf_review_workbench.md) with **`--resume`** for the existing
`evaluation-output/ml29-human-review` workspace. Never delete/reset that directory or
run the fresh-workspace command against it. Stop any existing server first; keep one
writer. The existing `c1-0033` draft needs no migration. For the bundled runtime on
this workstation, the same ML-29 command can use this local import path:

```powershell
$env:PYTHONPATH="src;.;C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages"
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_review_workbench --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --packet evaluation-output/pdf-table-gold-review-v1-20261019/packet-1 --output evaluation-output/ml29-human-review --resume
```

The server renders only selected authorized originals behind the existing loopback,
session token, same-origin and POST-token checks. Images stay in server/browser memory;
responses use `no-store`, blob URLs are revoked, and no raster files or persistent
public caches are created. Native viewer links retain the ML-29 inspection caveats.

## Draw, adjust and explicitly assign

1. Select the original and page using the existing controls. The visual surface shows
   that page's original raster. The native PDF viewer remains in an expandable panel
   and the separate viewer link remains available.
2. Choose **Draw rectangle** and drag on the visual surface. The displayed bbox is
   `[left, bottom, right, top]` in unrotated PDF user-space points. **Move rectangle**
   drags an existing selection; **Resize bottom-right corner** moves that corner.
   **Undo selection** restores the previous selection; **Cancel selection** clears it.
3. Create a blank original region, a blank table using the worksheet button, or a blank
   cell using the selected table. Supply IDs and every semantic field yourself in JSON.
   No text, row/column/span, relationship, table-presence or attestation is inferred.
4. **Refresh targets from JSON**, select the exact region/table/cell, then **Assign
   rectangle and save worksheet**. This saves all current worksheet edits through the
   existing validation and atomic draft save. **Adjust target rectangle** loads a saved
   bbox for further mouse adjustment; changing it still needs explicit assignment.
   **Undo last assignment** restores the worksheet saved before that assignment, with
   confirmation. It is available only until another save changes the worksheet revision.
5. Reload/restart with `--resume` to continue. Pending unassigned selections are temporary;
   only assigned/saved worksheet geometry persists. Complete human review, attestations,
   freeze, legacy reveal and adjudication exactly as before. Frozen drafts are read-only.

## Mapping and limitations

Only rotation **0**, `/UserUnit` **1**, positive finite CropBoxes contained in the
MediaBox are supported. Offset and fractional CropBoxes are supported. The server
compares the renderer's effective page box/dimensions and both bitmap corner mappings
against the original-page inventory within **0.001 point**; disagreement disables capture.
Rotations 90/180/270, non-default UserUnit and unsupported crop combinations fail closed
with an explanation. Inspect them in the original viewer; do not guess a transform.

For normalized displayed-canvas coordinates `(u,v)`, mapping is
`x = crop_left + u * crop_width`, `y = crop_top - v * crop_height`.
Pointer coordinates use the canvas's current viewport rectangle, so container/page
scrolling, fit-width layout, zoom and viewport resizing do not add offsets. The raster
uses at most 2 pixels/point and a 3000-pixel edge cap; mapping uses actual bitmap and
display dimensions, including fractional-size raster rounding. Display rounding is
three decimals only; saved values retain precision. Human pointer/pixel placement has
resolution limits: the synthetic 260×340-point page passes **0.6-point** end-to-end
tolerance; this is not a universal annotation-accuracy or factual-quality guarantee.
No coordinate is taken from the native iframe or a screenshot.

Page/source identity and render identity are rechecked on assignment. Invalid, reversed,
out-of-page, zero-area, nonfinite and mismatched-page rectangles are blocked. Targets
must already exist in the supplied worksheet; all other fields remain human controlled.
The local filesystem owner can still edit JSON directly, as in ML-29; fingerprints and
reviewer identities are not authenticated signatures.

Renderer API reference: [pypdfium2 rendering and position conversion](https://pypdfium2.readthedocs.io/en/stable/python_api.html).

## Verification

The focused test file `tests/unit/test_pdf_review_visual.py` checks real PNG pixels,
fractional CropBoxes, rejected transforms/identities/geometry, resume, frozen drafts,
and route security. `tests/unit/pdf_review_visual.browser.cjs` uses an installed Edge
and locally available Playwright for actual mouse input against a public synthetic
PDF. It locates the painted rectangle in the rendered canvas, then checks zoom,
scrolling, resizing, movement, selection undo/cancel and region/table/cell save/reload.
No real private page is sent to browser automation. Optional visual tests skip if the
renderer is absent; the browser case additionally requires `ML30_NODE` and
`ML30_NODE_MODULES`. Required verification for this step sets both and allows no skips.

Executed on 20 October 2026 from `be690cd15b1ce5d3fa03b7a7214628dfb61eba46`:

```powershell
$env:PYTHONPATH='src;.'
$env:ML30_NODE='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:ML30_NODE_MODULES='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
.venv/Scripts/python.exe -B -c "import sys; sys.path.append(r'C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))" -q -s --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/ml30a-tests-final tests/unit/test_pdf_review_visual.py tests/unit/test_pdf_review_workbench.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_ml28_review.py tests/unit/test_ml28_evidence.py --tb=short
# 138 passed in 48.97s; no skips. Headless Edge used --disable-gpu.
.venv/Scripts/ruff.exe check tools/extraction_quality/pdf_review_workbench.py tests/unit/test_pdf_review_workbench.py tests/unit/test_pdf_review_visual.py
.venv/Scripts/ruff.exe format --check tools/extraction_quality/pdf_review_workbench.py tests/unit/test_pdf_review_workbench.py tests/unit/test_pdf_review_visual.py
# All checks passed; 3 files already formatted.
& $env:ML30_NODE --check tools/extraction_quality/pdf_review_ui/annotation.js
& $env:ML30_NODE --check tools/extraction_quality/pdf_review_ui/workbench.js
& $env:ML30_NODE --check tests/unit/pdf_review_visual.browser.cjs
.venv/Scripts/python.exe -B evaluation-output/ml30a/compatibility_audit.py
# Local metadata-only helper: 90 RAW, 5 PDFs; 119 protected files unchanged.
# Existing workspace and c1-0033 resumed; legacy locked; zero private content matches.
git diff --check
git diff --cached --check
```

Initial checks exposed incorrect renderer handle cleanup, missing new-script routing
and an asynchronous assignment-status race; these were corrected before the final
passing run. Loopback/browser checks required local sandbox escalation on Windows.
Existing saved workspace compatibility and frozen-input hashes were checked without
saving or changing human review decisions. No quality gate or production qualification
follows from these synthetic checks.
