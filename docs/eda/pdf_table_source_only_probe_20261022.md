# Source-only PDF table probe — 22 October 2026

**Engineering execution PASS. Candidate verdict:
PROMOTE_FOR_FURTHER_OFFLINE_EVALUATION. QG-00/QG-01 NOT_EVALUATED.**

One bounded source-only method adds limited, inspectable structural evidence on
c1-0040: **112 unique source-glyph ownership correspondences with exact literal
agreement**, inside four-source-bar face proposals. Native PDF emits no cells.
There is no gain on c1-0033. These are development-reference correspondences, not
independently verified cells, complete table recovery or production authorization.

## Mechanism and prior evidence

Starting HEAD `c796922c3b062cead03770339cf13b492f666b4f`, branch `main`; only the
unrelated engineering audit was initially untracked.

[ML-23](pdf_table_candidate_v1.md) stopped at unsupported PDF operators on these
sources. [ML-24](pdfplumber_table_candidate_v1.md) detected no table on c1-0033;
its global complete-grid validation rejected c1-0040's oversegmented lattice.
Those frozen configurations remain rejected. [ML-26](pdf_filled_ruling_normalization_v1.md)
supports thin filled-bar representation on synthetic fixtures only, without a
private-source quality result. [ML-30B](ml30b_assisted_pdf_cells.md) requires a
reviewer-selected bbox and declared dimensions, so it cannot be this inference arm.
The [accepted native diagnostic](pdf_native_dev_diagnostic_20261022.md) establishes
the unchanged page-text baseline and its missing native topology.

The new mechanism, `source-only-local-filled-bar-faces-v1`, discovers **local
rectangular spaces enclosed by four qualifying filled bars**, then groups faces
sharing a source bar and overlapping side projections. It does not construct or
repair a complete Cartesian lattice. Existing PDFium `_rulings` supplies qualified
direct, opaque black, thin filled-path rectangles; pdfplumber supplies original
character indices, text and bounds. No new dependency, model or OCR is introduced.

Face coordinates are the four actual **inner ink-edge positions** of their support
bars, separately labelled derived face bounds. They are not claimed original PDF
cell objects, human-verified exact borders or reference bboxes. No edge extension,
snapping, missing divider, equal-spacing fallback, row count, span or semantic link
is invented. Every emitted face retains its source page and four bar-object indices.
Characters require unique full containment; crossing/unsupported text stays null.
Absent text-layer glyphs also stay null, rather than asserting a physically empty cell.

Generic frozen config: minimum face side 3 pt; qualifying bars inherit the existing
maximum thickness 2 pt; minimum connected component four faces spanning at least
two distinct left/top positions; input 50 MiB, 100 pages, 512 qualified bars/page,
200,000 characters/page, 2,048 faces/page, 20,000,000 counted face-rule checks/page.
Parent guards: 20 seconds, 512 MiB sampled process-tree RSS, 64 MiB capture,
20 ms sampling. These are engineering bounds, not approved quality thresholds or
an OS hostile-input sandbox. Unsupported rotation, crop/origin or UserUnit transforms
are excluded. Arbitrary paint visibility/compositing is not independently verified.

## Inference separation and frozen criteria

The inference API accepts only PDF bytes and its frozen generic Config. Workers
receive only a PDF path and output directory and start as fresh processes.
Opaque IDs occur in those paths, but are not supplied to inference. No reference
paths, dimensions, proposals, labels or decisions are inference inputs.
An active inference file-access audit rejects reads outside installed Python/runtime
packages. All four actual workers recorded **zero forbidden/non-runtime file reads**;
tests also deny a deliberate annotation-file read. Library imports are allowed.

The parent checks rights/source/reference integrity separately. Candidate inference
does not call the review/grid/geometry-plan workflow. Registration (method, code,
config, sources, metrics, guards and decision rules) precedes all measured extraction.
All four paired outputs are hashed into `inference-seal.json` before reference-field
scoring. Both repetitions are then scored with the same frozen scorer; the second
post-seal scoring execution exactly reproduces the first evaluation object.

The development advancement rule requires at least one unique reference-cell
**non-whitespace source-glyph-index set** correspondence, four-source-bar geometry,
no duplicate glyph/reference assignment, no mapped non-whitespace text mismatch,
unchanged native captures/statuses, repeat equality and no resource/access failure.
Native output is retained separately and never replaced by proposed cell text.
Critical guardrail failures reject; missing/inconsistent captures are inconclusive;
complete measurements without structural correspondence reject. This rule does
not require or establish independent Gold, semantic relationships or QG PASS.

No candidate setting or inference/scoring implementation changed after measured
captures or scores. A read-only graph inspection reused captured source rules with
the same configuration solely to explain rejected components; it accepted no new output.

## Measured results — two sources, not four independent documents

The frozen reference fingerprint remains
`64fa75b779854918fc50df38bc3e3cb3bf0069c8cb6c76e775bf6c35f8e1c9dc`.
Existing validator, source-specific local dev eligibility and held-out-family checks
passed before and after the paired executions. Both pinned SHA/size identities match
the authoritative originals and exact frozen source copies. All 536 reference cells
and six logical grids remain in denominators; 291 empty cells are not text-scored.
The reference's 62 text anchors and 115 printed-symbol observations remain available
through the byte-identical native page text; they are not promoted to new cell/unit links.

Original source identities (SHA-256; bytes):

- c1-0033: `081c9cfcc8e885544698f617dfdb9bf351fcf60b512cc449a3620deb538695fd`; 29,702.
- c1-0040: `18a25155acbe6dfb0a97309097234dc3040a67d2f54250af82288e56dc8c4344`; 64,968.

| Observation | c1-0033 | c1-0040 | Total |
| --- | ---: | ---: | ---: |
| Reference cells / nonempty cells | 44 / 44 | 492 / 201 | 536 / 245 |
| Reference logical grids | 1 | 5 | 6 |
| Native tables / cells | 0 / 0 | 0 / 0 | 0 / 0 |
| Qualifying source bars | 112 | 133 | 245 |
| Locally closed faces before component filtering | 12 | 365 | 377 |
| Retained region / face proposals | 0 / 0 | 5 / 365 | 5 / 365 |
| Face proposals with source text / unresolved text | 0 / 0 | 112 / 253 | 112 / 253 |
| Unique reference glyph-set correspondences | 0 | 112 | 112 |
| Exact literals among those correspondences | 0 | 112 | 112 |
| Nonempty reference cells without a correspondence | 44 | 89 | 133 |
| Empty reference cells not verified | 0 | 291 | 291 |
| Distinct reference grids with partial region-membership evidence | 0 | 4 | 4 |
| Duplicate nonspace glyph ownership / reference assignments | 0 / 0 | 0 / 0 | 0 / 0 |
| Unsupported-coordinate / mapped nonspace-text violations | 0 / 0 | 0 / 0 | 0 / 0 |

Glyph identity, not duplicated literal matching, establishes these correspondences.
All 112 are exact strings, with no whitespace-only or non-whitespace mismatch.
The other 424 reference cells remain unresolved: 133 nonempty and 291 empty cells.
The 253 null-text face proposals are not asserted to equal 253 reference empty cells.
All opaque candidate/reference item correspondences remain in ignored evaluation files;
no source excerpts, annotation literals or bbox values are published here.

**Five components do not mean five recovered reference tables.** Two components
map to portions of the same reference grid (5 and 42 matched items); the remaining
components map 15, 18 and 32 items to three other grids. The unruled year-band
partition is not supplied or manufactured. Complete logical-grid occupancy,
row/column ranks and spans remain NOT_EVALUATED for all six reference grids.

**Limiting mechanism:** strict whole-side bar support and shared-object connectivity
fragment or exclude the table layout. On c1-0033 the 12 closed faces form four
singletons and one eight-face single-column component; none passes the frozen
two-dimensional component rule. On c1-0040 one reference grid splits across two
components, and most reference cells lack verified correspondence. No post-result
tolerance, gap completion or grouping repair was attempted.

The candidate preserves all 945/851 source-character observations as a separate
inventory. Unassigned nonspace glyph counts are 813/564 respectively, including
text outside retained faces. This is incomplete cell assignment, not deletion from
the document: baseline text, warnings, duplicates and page/block locators are
unchanged before/after every probe and equal the accepted native fingerprints.
Baseline outcomes remain success/success; probe outcomes are needs_review/needs_review.
Combining unreviewed proposals would require review; no production eligibility or
success-status equivalence is claimed. Existing informational table-structure
warnings are retained; there are no native extraction failures or resource failures.

## Reproducibility, timing and verification

Two serial paired repetitions completed: four source executions, each native before,
source-only probe, native after. Both per-source result captures and both inference
file-audit records are byte-identical across repetitions. Timing/resource journals
are separate. Both post-seal evaluations match, including opaque findings and verdict.

| Identity | Fingerprint |
| --- | --- |
| Registration | `473ceba7d928d9793967f5b2780df4290a60eff877fc96571da54cef8c805e24` |
| Both evaluated repetitions | `032b9e3c34160f54c07f6d7ec655805d0163f7d3418c8cb529497c8223471fcc` |
| Source-only detector code | `a40fb6ff734eea3dde69f3b44fa9b269f14d25fea715dc48860cf7b9141306d1` |
| Paired runner/scorer code | `27ca3e132711cbd892245be03c3746afcbff8969a4aa349b682c070644ab5177` |

| Source | Probe seconds run 1 / 2 | Paired worker seconds run 1 / 2 | Sampled peak tree RSS bytes run 1 / 2 |
| --- | ---: | ---: | ---: |
| c1-0033 | 0.175013 / 0.202676 | 1.657 / 1.750 | 86,597,632 / 87,805,952 |
| c1-0040 | 0.399849 / 0.440810 | 1.875 / 1.937 | 87,265,280 / 87,179,264 |

Probe-call time includes parsing and inference audit/lazy-import overhead. Paired
worker time includes cold process startup, native-before/probe/native-after and
capture persistence. All cleanup checks passed. Serial CPU, Windows 11 / AMD64,
16 logical CPUs, Python 3.12.3; OS cache not reset; no GPU/model. Versions are frozen:
pypdf 6.20.0, pdfplumber 0.11.9, pdfminer.six 20251230, pypdfium2 5.14.0, psutil 7.1.0.
Memory is sampled process-tree RSS, not an exact high-water mark. The two-source
paired-wall nearest-rank P50/P95 is 1.657/1.875 s and 1.750/1.937 s respectively;
this tiny exposed subset does not establish latency or quality generalization.

Actual paired command (repository root; all output directories were fresh/ignored):

```powershell
.venv/Scripts/python.exe -m tools.extraction_quality.pdf_table_source_only_probe --source c1-0033=local-evaluation/pdf-dev-reference-20261022-v1/sources/c1-0033.pdf --source c1-0040=local-evaluation/pdf-dev-reference-20261022-v1/sources/c1-0040.pdf --snapshot local-evaluation/pdf-dev-reference-20261022-v1 --validation-config evaluation-output/pdf-native-dev-diagnostic-20261022/validation-config.json --output evaluation-output/pdf-table-source-only-probe-20261022
```

Exit 0; engineering PASS and the verdict above. Existing outputs must not be
overwritten. The private integrity companion retains the independent second-score
object, before/after receipts and exact verification commands. No new inference was
run for post-seal scoring or captured-rule graph inspection.

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_pdf_source_only_faces.py tests/unit/test_pdf_table_source_only_probe.py -q --basetemp=evaluation-output/pdf-table-source-only-probe-20261022-focused-tests
.venv/Scripts/python.exe -m pytest tests/unit/test_pdf_source_only_faces.py tests/unit/test_pdf_table_source_only_probe.py tests/unit/test_pdf_cell_recovery.py tests/unit/test_pdf_native_dev_diagnostic.py tests/unit/test_pdf_dev_reference.py tests/unit/test_extraction.py -q --basetemp=evaluation-output/pdf-table-source-only-probe-20261022-regression-tests
.venv/Scripts/ruff.exe check src tests tools alembic
.venv/Scripts/ruff.exe format --check tools/extraction_quality/pdf_source_only_faces.py tools/extraction_quality/pdf_table_source_only_probe.py tests/unit/test_pdf_source_only_faces.py tests/unit/test_pdf_table_source_only_probe.py
.venv/Scripts/python.exe evaluation-output/pdf-table-source-only-probe-integrity-20261022/verify.py
git diff --check
```

Focused tests: **20 passed in 1.28 s**. Broader focused suite: **97 passed in 4.49 s**,
no skips/failures. Includes positive known source geometry/text, gapped/borderless/
insufficient components, crossing glyphs, duplicate rulings, resource bounds,
reference-interface/file-access rejection, duplicate assignments, coordinate/text
violations, native-loss rejection and incomplete/nondeterministic verdicts.
Initial Ruff findings were corrected before measured execution; no post-score tuning.

Integrity receipts confirm **13,271 protected files unchanged**, including both
originals, frozen reference, Gold, accepted review artifacts, previous reports,
production code and the unrelated audit. No private source data or annotations are
in the proposed code/tests/report. No production routing, existing-code refactor,
dependency change, Gold promotion, commit or push.

Semantic roles/relationships, reading order, exact borders, ambiguous/unruled
partitions, currency interpretation, language/family review and independence remain
NOT_EVALUATED. The verdict permits only further offline evaluation of this limited
source-supported proposal mechanism; it does not authorize the next experiment.
