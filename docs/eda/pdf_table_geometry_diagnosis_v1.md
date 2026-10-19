# ML-25 PDF table geometry diagnosis v1

2026-10-19. **Execution PASS**, diagnostic scope only. No new candidate-quality
benchmark, scorer invocation on real sources, production/parser/Gold/settings change
or promotion. ML-23/ML-24 remain REJECT for their frozen configurations;
QG-01 is not closed and production authorization remains false.

## Scope, protocol and source boundaries

Starting main HEAD `fe934277a9e0ad97bd7b483871a6ccf4f43de4cd`, clean; no staging.
Only three new files: diagnostic tool, synthetic tests and this report. Followed
AGENTS.md, extraction-benchmark/ML-experiment skills and EX-PDF/EX-EXPERIMENT.
Existing ML-23/24 code and reports were read for their actual geometry gates.
No nested instructions were found under affected directories. Sources: the local
extraction strategy; pinned pdfplumber 0.11.9 table.py (TableFinder, rect-edge
decomposition and cells_to_tables); [official pdfplumber documentation](https://github.com/jsvine/pdfplumber)
and [pypdf extraction limits](https://pypdf.readthedocs.io/en/6.20.0/user/extract-text.html).
Installed implementation, not current web documentation, determines measured behavior.

Frozen cohort: c1-0033, c1-0040, c1-0045, c1-0048, c1-0049, five sources/34 pages.
Reused ML-24's ignored isolated Python 3.12.3 runtime: pdfplumber 0.11.9,
pdfminer.six 20251230, pypdf 6.20.0, psutil 7.1.0, PDFium binding 5.14.0. No installs.
All 90 originals and the 19-record reviewed Gold are revalidated for identity only;
Gold labels/text never enter diagnostic classification, settings or fixture creation.

Before additional inspection, froze source-only hypothesis and budgets in ignored
protocol.json: rectangle outlines, exact topology and minimum-grid policy can
account for observed failure classes. Thin means minimum rectangle dimension <=2
points with long dimension >=3; near means an endpoint/intersection distance <=3
points. These are descriptive bins, not new extraction tolerances or proposed fixes.
The ML-24 lines/lines settings, zero snap/join/intersection tolerances, and existing
ML-23/24 code/configuration hashes are unchanged. No adjusted detection was run.

Existing captures lacked original paint/edge/connectivity detail. Bounded local
source inspection therefore adds topology counts, original character-box containment,
paint flags and independent pypdf operator counts. Top-level pypdf operators are
not a complete Form XObject interpreter or independent visual ground truth.
No original private PDF was rendered or displayed. Only public fixtures were rendered.

## Confirmed source observations

Rectangles below are pdfminer-derived objects; cells are native geometry proposals,
not reviewed correct cells. Singleton counts are cells excluded by pdfplumber's
explicit corner-connectivity grouping and len(group)>1 filter.

| Source | Rectangles | Filled thin rectangles | Native cells | Filtered singletons | Detected tables |
| --- | --- | --- | --- | --- | --- |
| c1-0033 | 185 | 112 | 12 | 12 | 0 |
| c1-0040 | 150 | 133 | 2,448 | 0 | 4 |
| c1-0045 | 7 | 0 | 7 | 7 | 0 |
| c1-0048 | 154 | 126 | 44 | 8 | 2 |
| c1-0049 | 439 | 248 | 14 | 14 | 0 |

All rectangles have positive area and painting flags; no unpainted rectangle object
was observed. Nominally black filled thin counts are respectively 112/133/0/4/237.
Color/paint flags do not establish final visibility: compositing and occlusion are
not independently audited. Do not describe all filled regions as black visible rules.

**c1-0040: outline decomposition is a demonstrated contributor.** Of 2,448 native
cells, 2,042 have a dimension <=2 points; centers of 2,044 fall strictly inside a
filled thin rectangle. All 133 thin filled rectangles are nominally black. This
direct source-geometry correspondence explains much of the apparent cell explosion;
it is not evidence for thousands of logical data cells. Four detected groups have
856/526/460/606 boxes versus 1672/722/646/798 Cartesian lattice positions. ML-24's
complete-grid gate rejects them before text association/normalization. The exact
logical row/column/spanning layout of the private original remains UNKNOWN.
Simply accepting every native box would admit painted-strip regions as evidence.

**c1-0048: two distinct gates.** On actual page 13, t0 has 33 boxes versus 150 lattice
positions, 18 micro-cells, 11 centers inside filled thin rectangles. t1 is a complete
one-column/three-row shape: 3/3 lattice positions, with one micro-cell. It is rejected
by the explicit minimum-two-columns policy, not a missing boundary. Semantic status
of this private shape (table/panel/another structure) requires original-document review.

**c1-0033/c1-0049: cells exist, table groups do not.** All 12/14 closed native regions
are filtered singletons. None is a <=2-point micro-cell or has its center inside a
filled thin rectangle. This is a connected-group/detection boundary, not text absence,
Gold-locator remapping or proof that no table exists visually. Whether separate boxes
should be grouped is UNKNOWN without original review; proximity alone is insufficient.

**c1-0045: no connected multi-cell vector grid in observed geometry.** One singleton
region per page is filtered (7/7). The flattened pdfminer geometry has no lines and
seven rectangles. Top-level pypdf streams contain 14 Do operations; nested Form paint
operations are not independently traversed. Thus top-level absence of stroke/fill
operators must not be interpreted as absence of visible structure. Unruled tables,
Form interpretation and semantic layout remain UNKNOWN and require original review.

**Boundary continuity is not the demonstrated rejection of the six native groups.**
All four boundaries of all 2,484 grouped boxes are supported by continuous original
page edges at exact coordinates: 9,936 successful boundary checks, zero missing.
This proves linkage to detected source edges, not semantic correctness of those boxes.
Crossing/partial character boxes cannot be silently assigned: c1-0040 t0 has 11/355
intersecting character boxes outside every complete cell; c1-0048 t0 has 211/325.
No multiple-cell containment was observed. These are geometry counts, not lost-anchor
or text-fidelity measurements. Actual private character text is never serialized.

| Source | Exact duplicate edges | Positive collinear overlap pairs | Positive collinear gaps | Gaps <=3 pt | Near missing crossing pairs |
| --- | --- | --- | --- | --- | --- |
| c1-0033 | 96 | 326 | 228 | 112 | 1,738 |
| c1-0040 | 0 | 107 | 321 | 11 | 843 |
| c1-0045 | 0 | 0 | 0 | 0 | 0 |
| c1-0048 | 54 | 163 | 126 | 50 | 773 |
| c1-0049 | 307 | 621 | 588 | 338 | 4,295 |

These span all page geometry, including non-table shapes. Near crossing counts are
edge-pair counts, not unique missing table joints; duplicates can multiply them.
They cannot justify a 3-point gap bridge, altered tolerances or invented intersections.
Controls below show that duplicates/exactly joined fragments can already yield a
correct native grid. Their presence alone is not a demonstrated failure cause.

## Independent public reproductions

Twelve fresh PDFs are constructed directly from explicit literal paths, known geometry
and public ASCII labels in the new tests. No private font, document structure, Gold
text or coordinates were copied. Standard Courier reference; no font file/model.
Expected source layout is authored in the generator, not inferred from parser output;
these fixtures are synthetic, not human-reviewed private evaluation observations.

| Fixture | Native cells / table groups | Demonstrated distinction |
| --- | --- | --- |
| stroked 2x2 control | 4 / 1 | Complete grid with source-supported boundaries |
| six filled thin ruling bars | 25 / 1 | 21 micro-regions and 21 centers inside painted bars |
| four stroked cell rectangles | 4 / 1 | Rectangle use/duplicate shared edges alone is not failure |
| exactly contiguous split rule | 4 / 1 | Zero-tolerance joining handles true continuity |
| rule with a two-point gap | 2 / 1 | Two near missing crossing pairs; geometry really discontinuous |
| genuine merged top cell | 3 / 1 | Valid merged topology, 3 boxes versus 4 Cartesian positions |
| single column, three rows | 3 / 1 | Complete 3-position lattice excluded by minimum-grid policy |
| borderless text layout | 0 / 0 | Text proximity does not create vector cell evidence |
| repeated stroked edges | 4 / 1 | Duplicate/overlap counts alone do not imply corruption |
| text crossing a boundary | 4 / 1 | A cell lattice does not justify forced text assignment |
| four unpainted rectangle paths | 0 / 0 | Raw re/n operators are not painted edges |
| two disconnected closed boxes | 2 / 0 | Singleton group filtering reproduced independently |

PDFium independently renders all fixtures; the filled-rule control has four known
white data interiors and black ruling samples. Pixel assertions and local inspection
confirm that appearance while pdfplumber produces 25 regions under the frozen
zero-tolerance configuration. This reproduces the
representation mechanism without using a private original or changing parser settings.
Pypdf independently confirms six re/f operations for the filled bars; it confirms four
re/n operations but no painting for the unpainted control. No invisible-path bug is
claimed: pdfminer correctly discards those unpainted paths in this control.

## What is addressable, unsupported or unresolved

- Demonstrably non-inferential policy limitation: the known complete synthetic 1x3
  grid can retain its three already detected cells without inventing any coordinate.
  Minimum-two-columns is stricter than geometric completeness. This is an intentional
  ML-24 subset limit, not evidence of an implementation bug or a valid private table.
- Reproduced representation problem: filled-bar outlines create data-like micro-regions.
  A stroked representation of the independently known four-cell layout gives four
  cells. This establishes an addressable mechanism; safe generic normalization and
  private-source improvement are NOT_EVALUATED, not a demonstrated parser repair.
- Genuine unsupported structures: actual merged cells cannot be faithfully represented
  by the frozen full-Cartesian/1x1 rule; real gaps provide no exact missing joint;
  borderless layout and crossing text need additional evidence. Rejecting ambiguity
  is appropriate. Relaxing the validation gate alone is not a safe correction.
- Requires human original review: logical boundaries and spans of c1-0040/c1-0048,
  whether c1-0048 t1 is a table, whether disconnected c1-0033/c1-0049 regions should
  group, and c1-0045's unruled/Form layout. Gold is not used to answer these questions.
- UNKNOWN: which near joints belong together, post-normalization logical cell counts,
  semantic headers, private text/value fidelity, nested Form geometry completeness,
  compositing and independent family/language generalization.

**Exactly one next experiment:** a separately preregistered **public-synthetic filled
ruling representation normalization experiment**, retaining pdfplumber as the fixed
detector. Vary only source-bound representation of filled thin bars versus their
outline edges; no private cohort scoring or new extractor. Success requires the known
four-cell case to return four data cells rather than 25 regions, explicit original-bar
provenance, literal numeric preservation, and no fabricated joins/merges. Controls
must preserve genuine stroked/cell-rectangle grids and keep merged, gapped, unpainted,
borderless and crossing-text ambiguity visible. A geometry-equivalence result would
not establish a private-source fix, QG-01 PASS or production authorization. Do not
change ML-23/24 settings or silently relax their acceptance gates.

## Verification, reproducibility and resources

Final synthetic plus existing extraction regressions: **326 passed in 14.54s**,
30 new diagnostic tests plus 296 existing tests; zero skipped/failed. Includes public
rendering, topology, malformed input, resource configuration, timeout/memory/worker
failures, bounded capture serialization and rejection of incomplete/terminated output.
Ruff and formatting checks pass for the two new Python files. The unit-only
confcutdir avoids unrelated DB fixtures; no extraction tests are deselected.

Final source workers: 1.438/2.094/6.390/2.719/3.016 seconds in cohort order;
sampled peak tree RSS 75,567,104 / 75,800,576 / 79,749,120 / 79,572,992 / 77,238,272
bytes. Cleanup 5/5, zero resource failures. Public 12-fixture worker: 1.578 seconds,
83,296,256 bytes sampled peak RSS, cleanup 1/1. Guards remain 20 seconds, 512 MiB,
64 MiB output, 0.02-second sampling; logical source budgets: 15 seconds, 50 MiB input,
100 pages, 500k characters/document, 5k edges/page, 10k native cells/page, 50k PDF
operations/page and 8 MiB decoded stream/page. Loading/materialization precedes some
checks; sampled RSS is not a continuous peak or hostile-input OS sandbox guarantee.
These are diagnostic costs, not candidate-quality benchmark latency or new fidelity.

Earlier attempts remain disclosed and ignored: initial 24 synthetic tests passed.
An expanded test incorrectly expected unpainted paths to create rectangles and
expected an unwrapped PDFSyntaxError; actual results contradicted those assumptions
(23 passed, 2 failed). Corrected tests to zero painted geometry and the actual
PdfminerException wrapper; the 322-test suite passed. Added four publication/size/
failure regressions after the monitor issue below; final 326 pass. Initial Ruff
findings (explicit zip behavior, exception specificity/import cleanup) were corrected.
No production/candidate parser was changed to make these diagnostics pass.

**Out-of-scope finding:** the inherited monitor has a directory-stat TOCTOU at
tools/docx_footnote_candidate/benchmark.py:212. The first public-capture harness raised
FileNotFoundError for an atomically renamed borderless.partial. Preserve that failed
directory/journal; it is not counted as a successful reproduction. The old monitor
and ML-23/24 remain untouched. New diagnostic workers write bounded result.capture
under a stable name, and the parent validates/publishes it only after completed
monitoring and exit zero. Failed/incomplete output is removed after termination.
The corrected public harness also uses stable filenames while monitored. No guard
limit/classification was weakened. The shared monitor race remains an out-of-scope
issue for other callers; this report does not identify old UNKNOWN failures as that
race without their original exception evidence.

Initial and extended source audits were preserved. The final publication-safe
audit-complete payloads are byte-identical to audit-final/audit-verified (same
extended geometry algorithm); metadata fingerprints differ when tool/test pins
change. No new score fields were generated. Five unique sources/34 pages remain
the population, not twenty sources because of verification repetitions.

| Identity | SHA-256 / canonical fingerprint |
| --- | --- |
| Manifest | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Reviewed Gold | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Frozen ML-24 package/file/license manifest | `74f4a08ed7d153fd2a0bcbd01d016bff528625f99c7d73aa3d7bc068fdd56352` |
| Diagnostic protocol | `ebc2fea9761b7437eec1430dc866b473b90cc38c03b845f14e7452ddda4d2bb2` |
| Final diagnostic fingerprint | `0ad68d2b68539e4fa6ac786ca925e21b853d8190401200823b5cf21def7bed85` |
| Diagnostic tool | `e8ab743b29c3feaaa38e1dbbc90b4597934351e41aa9f4bfcdfc94a09410b751` |
| Diagnostic tests | `a172350dc41771de67b816ebce7d4442016238a3e928ede68066ed3edf86ff12` |
| Final audit manifest, 11 entries | `ac1f63f8437e4f0402c5827e704789b38d590504a1ed94f76b53686156aabc9b` |

All 90 original SHA/size/format identities, 19 reviewed Gold records, 39 ML-23 and
84 ML-24 frozen artifacts and all runtime/package bytes reconcile before/after.
Prior scores are historical only and are not recomputed here. Public reproduction
records verify 12 PDF/JSON/PNG triplets (36 hashes). All artifacts, failed attempts,
verifiers and journals stay under the ignored ML-25 directory; no private text,
Gold answer, real filename, private absolute path, secret, binary or PDF enters Git.

Actual PowerShell commands from repository root:

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B tools/pdf_table_geometry/diagnose.py --output evaluation-output/pdf-table-geometry-v1-20261019/audit-complete
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdf-table-geometry-v1-20261019/reproduce-v2.py
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B -m pytest -q --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/pdf-table-geometry-v1-20261019/test-tmp-4 tests/unit/test_pdf_table_geometry.py tests/unit/test_pdfplumber_table_candidate.py tests/unit/test_pdf_table_candidate.py tests/unit/test_extraction.py tests/unit/test_extraction_fidelity.py tests/unit/test_docling_candidate.py tests/unit/test_pdf_ocr_candidate.py
.venv/Scripts/ruff.exe check tools/pdf_table_geometry/diagnose.py tests/unit/test_pdf_table_geometry.py
.venv/Scripts/ruff.exe format --check tools/pdf_table_geometry/diagnose.py tests/unit/test_pdf_table_geometry.py
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdf-table-geometry-v1-20261019/verify.py
```

Actual final verifier output (exit 0):

```text
PASS originals=90 Gold=19 frozen_artifacts=39,84 runtime_unchanged=1 sources=5 pages=34
PASS diagnostic_geometry=byte_identical native_tables=6 native_grouped_cells=2484 all_source_cell_boundaries_present
PASS synthetic_variants=12 PDF_JSON_PNG_hashes=36 PDFium_render_pixel_controls_passed
PASS source_workers=5/5 public_worker=1/1 resource_journals cleanup no_final_partial_output no_new_quality_scores
FINGERPRINT 0ad68d2b68539e4fa6ac786ca925e21b853d8190401200823b5cf21def7bed85
```

CLI printed status PASS, documents 5, quality NOT_EVALUATED and that fingerprint.
Ruff printed All checks passed; format printed 2 files already formatted. Gold is
used only for immutable identity/schema and privacy verification, never a root-cause
oracle. No decoder fix, source-specific rule, production setting or scoring change
is implemented. Stop after the authorized diagnostic commit; do not launch the
recommended experiment automatically.

Final privacy/scope commands executed the ignored privacy.py verifier,
git diff --check and git status --short --untracked-files=all. Actual verifier:
`PASS privacy files=3 private_Gold_text_matches=0 private_filenames=0 secrets=0
absolute_private_paths=0 public_identifier_overlaps=1`, followed by UTF-8/LF,
source-specific-branch, production-edit and exact three-file scope PASS. The single
overlap is a public CLI identifier already present in tracked baseline code, not
exported private evidence. No unrelated file was changed or staged.

The ignored terminal manifest pins 116 diagnostic/protocol/public-reproduction/
verifier artifacts, including earlier attempts and the disclosed failed public
capture attempt, excluding pytest temporary fixtures. SHA-256:
`0ad315eb1580761074f8f8261d2b3b8d8a8616109c014b7df7ef712faa541cb7`.
Immediate reconciliation returned True for all entries and the final read-only
verifier passed again. This includes no new private source or Gold copies.

Git completion review staged only these three files and inspected the complete
staged diff. git diff --cached --check and git diff --check both exit 0; exact
staged scope and privacy checks pass. Files and staged blobs match UTF-8/LF.
Existing autocrlf warns about future CRLF checkout; no repository setting changed.
No push, history rewrite or unrelated change is part of the authorized commit.
