# ML-30C — missing PDF cell-text diagnosis

Execution diagnosis only, from HEAD `fe3aa2f1410eff11718b8469d647cb938fb34b72`.
No safe recovery was established. The ML-30B text checks remain conservative:

| c1-0033 | Baseline | Final |
| --- | ---: | ---: |
| Cell boxes / stable row-column assignments | 44 | 44 |
| Non-null `literal_text` proposals | 20 | 20 |
| Null literals | 24 | 24 |

The complete recalculated proposal equals the frozen ML-30B implementation's result,
including its existing literals, statuses, geometry and method/provenance fields.
This is unchanged behavior, not an extraction-quality improvement or an approved
Gold result. QG-00–03 remain NOT_EVALUATED, experiment INCONCLUSIVE and production
enrichment disabled.

## Concrete findings

Primary reasons are mutually exclusive, in the diagnostic code's declared order.
Coordinates below identify zero-based `(row, column)` slots, not private values.

| Primary reason | Null cells | Slots |
| --- | ---: | --- |
| `CHARACTER_BBOX_CROSSES_CELLS` | 22 | (1,0), (2,0), (3,1), (4,1), (5,1), (6,1), (7,1), (8,0), (8,1), (9,0), (9,1), (10,0), (10,1), (11,0), (11,1), (12,0), (13,0), (14,0), (16,0), (17,0), (18,0), (19,0) |
| `CHARACTER_BBOX_OUTSIDE_CELL` | 1 | (21,0) |
| `GENERATED_WHITESPACE_GAP` | 1 | (20,0) |

PDFium tight character boxes cross horizontal cell boundaries in the first group.
Some examined crossings are sub-point slivers, but these still fail strict containment
and affect both intersected cells. One last-row character box extends below the selected
table's bottom edge. Ignoring an overlap, clipping a glyph box, moving a grid boundary,
choosing its center/majority overlap, or discarding the offending glyph would weaken
ownership or lose text. None is justified by these observations.

The spacing failure has a PDFium-generated space with a zero-area loose box, followed
by a 3.5-point geometric gap. The same cell therefore has supporting
`AMBIGUOUS_WHITESPACE_GAP` and `DEGENERATE_WHITESPACE_BOX` codes. This does not establish
an exact source-space identity/count. No whitespace is inserted, removed, normalized
or guessed to fill the value.

For the glyphs associated with these cells, no Unicode mapping failure, unavailable
mapping, invalid character identity, generated non-space character, unsupported
character rotation or absent intersecting text layer was observed. No ordering rejection
occurred among the 21 cells reaching that check. Ordering/spacing checks are downstream
of ownership: they are not evaluated for the 23 ownership-failed cells, so their zero
counts do not prove the absence of additional latent problems there.

These are native-box/text-layer findings, not independent visual or semantic judgments.
The 20 existing proposals are not newly qualified as correct, and 24 nulls do not mean
the original table is blank. Manual inspection or separately justified source evidence
is still required.

## Implementation and sanitized reports

`pdf_grid_proposals.add_text(..., diagnostics=report)` optionally fills a **separate**
metadata dictionary. It does not add diagnostic fields to cell proposals or change
their literal, status, geometry or fingerprint. Default workbench behavior and existing
proposal/correction records remain compatible. There is no new fallback or tolerance.

`ml30c-pdfium-text-diagnostics-v1` reports each row/column, literal-presence boolean,
existing text status, ordered reason codes and condition-occurrence counts. Aggregate
`primary_null_reason_counts` sum to the number of nulls. `reason_cell_counts` can overlap
because one condition has several supporting mechanisms. The report distinguishes
mapping errors from unavailable flags, generated non-space identity, ordering,
source/generated whitespace gaps, degenerate whitespace boxes, native rotation,
empty cell-layer observations and inspection limits. If no grid cells are analyzed,
the source character count is `null`, not an invented empty text layer.

Reports contain no literal strings, Unicode codepoints, glyph coordinates, private
source filenames or paths. They include the pinned source SHA, engine version, page
and geometry fingerprint. `NO_TEXT_LAYER_GLYPHS_IN_CELL` means no intersecting glyphs
were observed under these checks; it does not claim visual blankness or require OCR.

The focused `pdf_text_diagnostics` helper accepts a pinned original SHA, page and
machine candidate (or an existing proposal sidecar's original `candidate`). It checks
source/page binding and geometry, copies input in memory and recalculates text checks
without reading edited-cell text as source evidence. It never saves proposals or
modifies a worksheet. Output must be a fresh, directly nested, ignored
`evaluation-output/ml30c-*` directory; existing outputs and review workspaces are rejected.

Using the same local pypdfium2 5.14.0 environment as ML-30B, the command template is:

```powershell
$env:PYTHONPATH='src;.'
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_text_diagnostics --source evaluation-output/pdf-table-gold-review-v1-20261019/packet-1/sources/c1-0033.pdf --source-sha256 <pinned-original-sha256> --page 1 --proposal evaluation-output/ml30b/c1-original-proposal.json --output evaluation-output/ml30c-example
```

Use the trusted original SHA from the frozen source record. If using the desktop's
bundled renderer, append its package directory after the virtual environment's packages
as in the executed verification command. Reports are `text-diagnostics.json`, with
sanitized aggregate counts also printed to the local console.

## Verification boundaries

Two separate fresh ignored real-PDF runs produced identical complete reports. A frozen
copy of the ML-30B module was compared against current output in memory; every proposal
field matched, and every remaining null had a deterministic reason. The diagnostic
runs used the same pinned original and unchanged captured 44-cell geometry. They did
not regenerate grids, accept cells, modify corrections or call a human-review action.

Hash checks covered **122 protected files**, including 90 RAW sources, frozen
manifest/Gold/packet, both `ml29-human-review` and `ml30b-assisted-review`, and the
unrelated engineering audit. The captured ML-30B candidate was also checked unchanged.
Private real-PDF analysis stayed local; only sanitized counts/opaque cell slots appear
here. No GPU, Docker, OCR/model downloads, unrelated benchmark or full E2E run occurred.

Synthetic regressions check unchanged proposal equality with diagnostics enabled,
adversarial cross-cell boxes, outer-bound violations, mapping errors/unavailable flags,
generated/invalid characters, nonfinite angles, native-order interleaving, ambiguous
source/generated spacing, empty layers versus limits, sanitized repeatable helper
output, source/page binding, correction preservation and forbidden output directories.
Native failure flags/order are fault-injected where needed; real-PDF findings above
come from unmodified PDFium extraction. Existing proposal acceptance/security and visual
workbench regressions are included in the scoped verification.

Executed commands/results (20 October 2026):

```powershell
$env:PYTHONPATH='src;.'
$env:ML30_NODE='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$env:ML30_NODE_MODULES='C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
.venv/Scripts/python.exe -B -c "import sys; sys.path.append(r'C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'); import pytest; raise SystemExit(pytest.main(sys.argv[1:]))" -q -s --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/ml30c-focused-final tests/unit/test_pdf_grid_proposals.py tests/unit/test_pdf_review_visual.py tests/unit/test_pdf_review_workbench.py --tb=short
# 99 passed in 92.93s; 17 new diagnostic cases, 82 existing cases; no skips.
.venv/Scripts/ruff.exe check tools/extraction_quality/pdf_grid_proposals.py tools/extraction_quality/pdf_text_diagnostics.py tests/unit/test_pdf_grid_proposals.py
.venv/Scripts/ruff.exe format --check tools/extraction_quality/pdf_grid_proposals.py tools/extraction_quality/pdf_text_diagnostics.py tests/unit/test_pdf_grid_proposals.py
# All checks passed; 3 files formatted.
.venv/Scripts/python.exe -B -c "import sys; sys.path.append(r'C:/Users/nurs/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'); exec(compile(open('evaluation-output/ml30c/verify_real.py',encoding='utf-8').read(),'verify_real.py','exec'))"
# Local integrity/paired-diagnosis helper: baseline and final 20 non-null / 24 null;
# complete proposals equal, reports identical, all 44 geometries and 122 protected hashes unchanged.
git diff --check
git diff --cached --check
```

Only the existing local renderer/browser dependencies were used. Loopback/browser
regressions required Windows sandbox escalation. There were no failing executed tests.
The repeated metadata-only helper timings are retained locally; they are warm diagnostic
execution observations, not latency, memory, quality or production qualification.
