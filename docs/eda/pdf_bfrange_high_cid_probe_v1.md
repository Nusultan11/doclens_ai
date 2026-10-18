# ML-16: synthetic high-CID scalar bfrange probe v1

STATUS: PASS (bounded experiment execution).
H2: NOT_REPRODUCED for the tested synthetic configuration.
Frozen Docling candidate quality remains REJECT; production pypdf is unchanged.

Both repetitions decode all four validated fixtures exactly at pypdf and pinned
backend word/textline boundaries. High CID plus scalar bfrange is therefore not
sufficient to reproduce the ML-15 signature with this font/map configuration.
This neither explains c1-0043 nor establishes general parser correctness.

## Scope and pre-registration

Executed on 2026-10-18 at clean branch `main`, HEAD / ML-15 commit
`2252a5496baab72c0e1a30fa6fb0fb221b285efd` (`docs: audit PDF CID Unicode mapping`).
The four requested reports/protocol, relevant candidate/backend functions and
focused tests were inspected under root AGENTS.md and extraction/experiment/PDF
skills. No nested AGENTS.md applied to this report. External GOAL, QG-01,
EVALUATION and ENGINEERING policy definitions are UNAVAILABLE; no unavailable
policy gate is claimed passed.

The ML-15 report supplies historical observations only: 44 altered high-CID
scalar-bfrange positions, 134 unaffected bfchar positions and two unaffected
low-CID bfrange positions. Its H1 was NOT_REPRODUCED; the native mechanism and
checksum relevance remained UNKNOWN. No private original, Gold, embedded private
font or private capture was opened in ML-16. This is independent synthetic data,
not a fresh sealed test or human-reviewed Gold.

Before any fixture construction, `protocol.json` registered H2 at
`2026-10-18T04:54:15.906269+00:00`:

> The pinned backend may return raw CID values instead of Unicode for scalar
> bfrange mappings with nonzero CID high bytes.

Preregistered decisions, unchanged after observation:

- REPRODUCED: independently valid fixtures and exact pypdf in both repetitions;
  all three matched backend controls exact; high-CID bfrange has a mismatching
  Unicode value equal to raw CID in both word and textline representations,
  identically reproduced. Applies only to the tested configuration.
- NOT_REPRODUCED: all four valid fixtures exact in pypdf and both backend
  representations in both repetitions.
- INCONCLUSIVE: other patterns, unequal repetitions, control failures or
  failed/unknown stages. Retain their planned denominators.
- BLOCKED: essential runtime, font/license, independent validation or monitoring
  unavailable. Malformed fixtures never count as decoder failures.

Four variants, two serial repetitions, one fresh spawned worker per variant.
Order 1: bfchar-low, bfchar-high, bfrange-low, bfrange-high; order 2 reverses it.
Per worker: 600 seconds, 3,221,225,472 bytes, approximately 50-ms sampling,
memory-first guard and existing terminate/join/kill cleanup. These are sampled
guards, not an OS memory sandbox. Fixture/decoded-stream budget 1 MiB, one page;
OMP/MKL thread environment limits both 2. No random input or inference seed.

All scripts, fixtures, public font/license, images, captures, failed preparation
scripts and resource journals remain ignored in
`evaluation-output/pdf-bfrange-high-cid-v1-20261018/` (`$scratch` below).
Only this sanitized report is an intended Git change. No production, test,
configuration, prior report, frozen artifact or model changes; no full Docling
conversion, OCR, GPU workload, download, decoder patch or substitution.

## Controlled construction and independent validation

Use the unchanged, audited ML-13 public Bitstream Vera font (65,932 bytes), with
the complete permissive copyright/license notice copied alongside it. The notice
permits redistribution with conditions including retained notices, protected
names for modified fonts and no standalone font sale. No font modification or
private-font reproduction. Generator uses existing ReportLab 4.4.9 for glyph
metrics and pypdf 6.10.0 low-level PDF objects, not simple-font text encoding.

Each PDF has one Type0/Identity-H font, one CIDFontType2 descendant, the same
complete embedded font, explicit sparse CIDToGIDMap, identical glyphs and widths.
Two text-show operations draw public synthetic lines `ab` and `01`, 20 pt,
x=54, baselines y=700/660, on a 612x792-pt page. Expected ordered codepoints are
U+0061, U+0062, U+0030, U+0031; GIDs are 68, 69, 19, 20.

| Variant | CIDs | ToUnicode entries | Expected characters |
|---|---|---|---:|
| bfchar / low | 1, 2, 3, 4 | Four bfchar pairs | 4 |
| bfchar / high | 257, 258, 259, 260 | Four bfchar pairs | 4 |
| scalar bfrange / low | 1, 2, 3, 4 | 1..2 -> U+0061; 3..4 -> U+0030 | 4 |
| scalar bfrange / high | 257, 258, 259, 260 | 257..258 -> U+0061; 259..260 -> U+0030 | 4 |

Each expected Unicode differs from its raw CID. High variants offset source
codes by 256 in content and CMap keys; their sparse CIDToGID streams have 261
entries/522 bytes versus 5/10 in low variants, and W-array starting CID differs.
bfchar uses four pairs versus two inclusive two-code scalar ranges. These change
PDF lengths/xref offsets; font, selected glyphs, widths, layout, codespace and
metadata remain controlled. No cross-byte-boundary range or multi-codepoint
destination is tested.

Separate `validate.py` does not import the generator or its expected output.
Independent Unicode literals, byte-level cmap/SFNT decoding and strict PDF object
inspection establish these checks for all four fixtures before backend execution:

- One unencrypted page; correct Type0/Identity-H/CIDFontType2 objects, font identity,
  content operands, text positions and permitted text-show operators.
- Actual ToUnicode expansion yields all four expected codepoints; actual content
  codes agree with the appropriate low/high mapping.
- Explicit CIDToGID entries select the embedded Unicode cmap's GIDs; unused map
  entries are zero. GID bounds, monotone loca, nonempty glyf records and hmtx-derived
  widths agree. All 17 SFNT table checksums and whole-font 0xB1B0AFBA sum pass.
- Independent PDFium 126.0.6462.0 returns exactly `ab\r\n01` for every fixture:
  16/16 expected characters total. Rendering at scale 1.5 gives four identical
  RGB images (918x1188). One full-page image was visually inspected; identical
  pixels extend that inspection to all variants. All four glyphs are legible,
  without clipping, overlap or missing-glyph boxes. This is AI-assisted inspection,
  not human Gold review or formal universal PDF/font conformance certification.

Shared raster pixel SHA-256:
`8eadb85e72365aeddcfd25dbeea1d5aa9cf9a0749e53610295b479c046a69e1e`.
Shared PNG SHA-256:
`f9e87a8afb8767a9e22c54a19bbefe918509b6e6105cc1382f3714436822ebf4`.
No malformed fixture was admitted to backend scoring.

## Measured results and full denominators

The unchanged production `extract_file` supplies the pypdf comparator. Direct
`DoclingParseV4DocumentBackend` supplies `get_segmented_page()` word/textline
cells; no DocumentConverter/layout pipeline is instantiated. Existing defaults
create words/textlines, keep_chars=False, keep_lines=False, keep_images=True,
enforce_same_font=True. Zero retained character cells is configuration, not
evidence of absent characters. Each worker uses the existing offline guard.

| Variant | pypdf R1 / R2 exact | Backend words R1 / R2 exact | Backend textlines R1 / R2 exact | Mismatches / raw-CID substitutions, all arms/repeats |
|---|---|---|---|---|
| bfchar / low | 4/4 / 4/4 | 4/4 / 4/4 | 4/4 / 4/4 | 0 / 0 |
| bfchar / high | 4/4 / 4/4 | 4/4 / 4/4 | 4/4 / 4/4 | 0 / 0 |
| scalar bfrange / low | 4/4 / 4/4 | 4/4 / 4/4 | 4/4 / 4/4 | 0 / 0 |
| scalar bfrange / high | 4/4 / 4/4 | 4/4 / 4/4 | 4/4 / 4/4 | 0 / 0 |

Eight attempted workers, eight complete, zero failed/unknown; 24/24 representation
observations. Per arm: 32/32 exact characters across repetitions, zero substitutions,
raw-CID matches, missing or extra characters. Across three arms: 96/96 expected
character observations exact. Backend word/textline fields are exactly `[ab, 01]`.
pypdf raw page text is exactly `ab\n01`; PDFium's CRLF is recorded separately.
Only line separators are separated for scoring; no case folding, Unicode
normalization, whitespace deletion within fields or output repair.

Every pypdf document status remains **needs_review**, with warning counts
`insufficient_text=1`, `pdf_table_structure_not_preserved=1`; all eight remain in
the denominator. Worker `complete` is diagnostic execution status, not a candidate
quality status or a full conversion result. No table, provenance/locator fidelity,
whole-document order, reviewed-anchor recovery or production quality gate is scored.

For each variant the entire result JSON, including baseline extraction fingerprint,
backend settings, exact fields and per-character observations, is byte-identical
across repetitions (4/4). Timings/PIDs/resources are separate and actually differ.
No excluded failed/needs_review cases or retries. Independent replay recomputed
codepoint counts from stored fields, not from reported success labels.

## Resources and reproducibility

Host: Windows 11 AMD64, AMD64 Family 25 Model 80 Stepping 0, 8 physical/16 logical
CPUs, 16,541,597,696 bytes RAM. Evaluation Python 3.12.3; pypdf 6.20.0,
Docling 2.55.1, core 2.48.2, docling-parse 4.7.3, pypdfium2 4.30.0,
psutil 7.1.0. Construction uses bundled Python with pypdf 6.10.0/ReportLab 4.4.9.
No dependency installation. Baseline version differences between construction
and evaluation are intentional and recorded, not silently substituted.

| Variant | R1 wall seconds | R1 peak bytes | R2 wall seconds | R2 peak bytes |
|---|---:|---:|---:|---:|
| bfchar / low | 9.166189 | 298168320 | 9.227769 | 298242048 |
| bfchar / high | 7.230568 | 298500096 | 8.459427 | 298401792 |
| scalar bfrange / low | 7.221101 | 297725952 | 7.487091 | 298557440 |
| scalar bfrange / high | 7.185264 | 298278912 | 6.914599 | 297517056 |

Total worker-monitor wall time 62.892007 s; maximum peak 298,557,440 bytes
(284.726563 MiB). 1,227 samples; maximum intersample gap 0.055567 s. Wall includes
spawn, imports, baseline/backend work and cleanup; per-stage CPU/latency and
construction/validation peak resources were NOT_MEASURED. Memory is sampled
Windows kernel peak_wset with RSS fallback for the actual spawned worker,
not the venv launcher, parent or summed process tree. Child executable identity
and parent linkage were verified in all eight journals. Two descendants were
observed in R1's first two workers; existing cleanup handles owned descendants.
All workers exited 0 without worker terminate/kill; no observed descendant
survived and no monitor/cleanup errors occurred. No hard cap or unobserved
descendant-peak guarantee. Thread limits are environment settings, not a measured
thread count; GPU utilization/VRAM were NOT_MEASURED, with no GPU/model calls.

Protocol, generator, validator, runner, font/license, construction/validation and
visual record plus four PDFs/PNGs were frozen before backend work (17 file pins).
All 17 and 15 prior report/source/test/runtime/public-font pins remain unchanged.
The final ignored artifact manifest records all 46 existing scratch files,
including all eight results/resources/sample journals and the verifier.

| Identity | SHA-256 |
|---|---|
| Protocol, actual on-disk bytes | b832f14a7bc17a3cc7518f66b4f73a85a592f68b80cc152cb2dbd6a7fbb2485b |
| Pre-execution freeze.json | ea08e17eaa4ce384fc7b43c2a1b661f1b9fc35136c508d657ef0e8b24929930f |
| Final artifact_manifest.json | b5ff264f0e969232cd89e21778bcad3b3df26ced3018ce87d0c5c7a71e89c263 |
| Public Vera.ttf | c4c45690b345435b2cba52ecabe275f05e49b389b39fe68ad03afbb551288d3d |
| Complete font-license.txt | 3361d054759a2fc686a2c058be82deaf9c2e6fe549be9004d7935a6c1736315d |
| generate.py | 880dd9f109a85cea02d0504a97dfbcdedd707057600becbd777d5fe591e4f8f1 |
| validate.py | 6e6dab88fb06ff613c09374599d521242ebbad8e499d6f5554046469a41cbafc |
| run.py | e70c24ba89f0fdfa62122b620baa6e5486d9d84ee020ac3ece750f5c9b77854e |
| verify.py | 6f16d88146f813d8079d83ee36155df29cd5c22fda60ad779a4357456c2209fa |
| validation.json | 5678180035e44a3afe517abf42dda8f1b55ec50308b47577d2fb88b074409d20 |
| verification.json | 7adeb495bc43f3d2a94d815b1275ce438b26ea31471a7ec2e55f717dabb18175 |
| Backend wrapper | c4205b69a5e334dace6a877db6606e09b7b998bfe2a664cd1b65cec556c61b7c |
| Native pdf_parsers.cp312-win_amd64.pyd | 1dc5839ceabd8576b51ebdd035382c5515e79b8dcdde7169bb83a7da2fe768e1 |
| Actual worker Python executable | 15b41a488c356c0e331facdea6c836a6cec021f12d5fde9844e7ca4a1aa0361a |

| Fixture | Bytes | PDF SHA-256 | Result JSON SHA-256, same in R1/R2 |
|---|---:|---|---|
| bfchar-low | 68031 | 174d75e4b9d6dee2dbc2db6771096345e359dd46d621588f669b1c8a6bf4a249 | ea2d69a33f97aaf1653a437e98fee64ca83dfdbcd594d7a638714e1dea4839bb |
| bfchar-high | 68546 | 5a65ac9d764e5e9bc8e8f9ff03c4f5df659fc723315fdd058a09b43276d77d50 | 7eab5749492147dc2c15ef9fd79fc50749792f87fa99fe8699f0d45658d649d2 |
| bfrange-low | 68019 | ef4c35e0a92b7810a23eadf38bf39804bfd348ff80c9b025925b7f50a3b10c67 | df6ed2c51344e79e5c50118a918f5ed042827b483af566f7fcc04c56cea451e8 |
| bfrange-high | 68534 | 34d2ff1ecc00bc069dfa7140d18a63edb4e824751d8f42832c1df443e2bb9cdf | d4e4f39893a89fcb5bc7e8b6450dcfe765fbe5b73a11bc2b14ad03783e20a659 |

## Actual commands, checks and preparation failures

PowerShell command paths below are repository-relative. Independent Python tooling
was the existing bundled runtime; no external service or private data was used.

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git merge-base --is-ancestor 2252a5496baab72c0e1a30fa6fb0fb221b285efd HEAD
git log -1 --format='%H %s'
git check-ignore evaluation-output/pdf-bfrange-high-cid-v1-20261018/protocol.json
```

Initial status: empty. Branch: main. HEAD/subject as above; ancestor check exit 0.
check-ignore prints the supplied ignored relative path. The final independent
verifier also checks every scratch file via `git check-ignore --stdin`.

```powershell
# $scratch abbreviates evaluation-output/pdf-bfrange-high-cid-v1-20261018
# $bundledPython denotes the existing bundled Python executable; its personal
# installation prefix is redacted here. Arguments below were actually executed.
& $bundledPython -B evaluation-output/pdf-bfrange-high-cid-v1-20261018/generate.py
$env:PYTHONDONTWRITEBYTECODE='1'
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-bfrange-high-cid-v1-20261018/validate.py
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; $env:HF_HUB_DISABLE_TELEMETRY='1'
$env:OMP_NUM_THREADS='2'; $env:MKL_NUM_THREADS='2'
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-bfrange-high-cid-v1-20261018/run.py 1
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-bfrange-high-cid-v1-20261018/run.py 2
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-bfrange-high-cid-v1-20261018/verify.py
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

Successful generator: four PDF hashes/sizes above, exit 0. Independent validator:
`validation=PASS`, four valid variants, PDFium 4/4 each, identical pixels, exit 0.
Both runner commands: four `outcome=complete` records each, every arm
`equal_positions=4, mismatch_positions=0, raw_cid_positions=0, missing=0, extra=0`,
exit 0. Verifier: `status=PASS, H2=NOT_REPRODUCED, prior_pins_unchanged=15,
frozen_pins_unchanged=17, attempted_workers=8, complete_workers=8,
failed_workers=0, unknown_workers=0, representation_observations=24,
planned_character_observations=96, repeat_deterministic_results_equal=4/4,
resource_samples=1227`, exit 0. Focused pytest: **159 passed in 10.16s**, exit 0;
none failed/skipped. These synthetic regressions do not load production models.
No full benchmark, service/E2E suite or production-readiness test was run.

Two generator preparation commands initially failed, both exit 1 and before any
PDF existed: (1) missing closing parenthesis / SyntaxError; (2) protocol-hash
assertion used a hash of LF serialization rather than Windows-written CRLF bytes.
Both initial script versions are retained ignored. Corrected only the generator
syntax and its expected byte hash before construction; protocol bytes/criteria
never changed. The early LF-derived hash was
`9c97027dc412b89e639edde728e9607eafc4038f03a64be483fad8e5a1f1c1e3`;
the actual immutable byte hash is in the table above. These were tooling failures,
not malformed fixtures, backend failures or repeated extraction attempts.

Final checks actually executed:

```powershell
git diff --check
git diff --cached --check
git diff --no-index -- /dev/null docs/eda/pdf_bfrange_high_cid_probe_v1.md
git diff --no-index --check -- /dev/null docs/eda/pdf_bfrange_high_cid_probe_v1.md
git diff --name-only
git diff --cached --name-only
git status --short
```

Both normal whitespace checks exit 0 with no output; tracked/index diffs are
empty. Full new-file diff was inspected. The two no-index commands exit 1 for
the new-file difference, without whitespace errors; Git warns that its configured
future checkout may convert LF to CRLF. Actual report bytes are UTF-8 without
BOM, LF-only, final newline, no trailing whitespace; no Git configuration changed.
An inline read-only Python integrity/privacy/scope check returned exit 0:

```text
PASS: 46 artifact SHA-256s unchanged; manifest pin exact; 8/8 captures verified; 96/96 exact observations
PASS: report UTF-8 without BOM, LF-only, no trailing whitespace; secret/absolute-path patterns absent
PASS: sole Git change is allowed report; index empty; no font/PDF/model/output artifacts in Git scope
```

The inline check hashes every manifest entry, checks captures against fixture
hashes, inspects UTF-8/line endings and token/private-key/absolute-drive-path
patterns, then asserts the exact porcelain status and empty index. Early attempts
exited 1 because a drive-path regex matched a URL scheme suffix, including that
suffix quoted in this check description. A drive-token boundary and clarified
description resolved these false positives; no fixture or output changed.
Manual full-report review found
only public synthetic text, public font identity, opaque historical source ID and
sanitized aggregates; no private source/Gold excerpt or personal absolute path.
This scan does not claim exhaustive secret detection or access private files.
Final status:

```text
?? docs/eda/pdf_bfrange_high_cid_probe_v1.md
```

The original experiment stopped without stage/commit/push for ChatGPT review.

## Finalization review, 2026-10-18

Subsequently authorized report-only finalization reviewed the complete report,
preregistered protocol, original generator/validator/runner/verifier and original
captures at the same pre-commit HEAD above. No new fixture, baseline/backend run,
full conversion, OCR, model initialization or GPU workload. No critical evidence
inconsistency or change to H2 criteria was found. H2 remains NOT_REPRODUCED only
for this tested configuration; c1-0043's mechanism remains UNKNOWN and Docling
quality remains REJECT.

The unchanged `verify.py` was executed again via `runpy.run_path(...,
run_name='__main__')` in the pinned runtime. Its final exclusive write to the
already-existing `verification.json` was redirected to an in-memory StringIO;
other writes were rejected. All assertions ran and every printed field exactly
matched the original verification record excluding its historical file-inventory
hash map (the manifest itself was created after that original inventory). This
preserves the original verifier, its strict original-HEAD check and all artifacts.
Do not mistake plain exclusive-output reruns for an overwrite-safe command.

The unchanged `validate.py` was also re-executed with JSON/PNG destinations
redirected to memory. PDF structure, ToUnicode, CIDToGIDMap, embedded cmap, GIDs,
widths, all 17 table checksums and whole-font checksum passed again. Every expected
Unicode differs from its raw CID. PDFium again gave 16/16 expected characters;
all four in-memory PNGs were byte-identical to the originals and the full
validation JSON matched. The existing high-CID bfrange PNG was visually reviewed.
These are rechecks of the original fixtures, not new experimental observations.

Both in-memory invocations used PowerShell here-string Python input piped to
`evaluation-output/docling-v1-runtime/Scripts/python.exe -B -`, with
`PYTHONDONTWRITEBYTECODE=1`, `unittest.mock.patch` limited to output I/O and
`contextlib.redirect_stdout` for exact JSON comparison. Both exited 0. No scoring,
decoder, condition, expected value or stored output was patched.

An additional independent read-only manifest/population check returned exit 0:
46/46 artifact SHA-256s plus the pinned manifest unchanged; 15/15 prior inputs
unchanged; 17 pre-execution pins covered; runtime versions unchanged; all 47
scratch files (46 manifest entries plus the manifest) remain ignored. Actual
run-directory populations and raw fields independently confirm four variants x
two repetitions x three representations x four codepoints = 96 exact, zero raw
CID matches. Resource/sample replay retains 1,227 samples, 62.892007 s total and
298,557,440 bytes maximum, with no recorded monitor/cleanup error or survivor.

Focused regression command was re-executed unchanged:

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

Actual finalization result: **159 passed in 8.13s**, exit 0, no failed/skipped tests.
Only this report is authorized for staging and the requested Conventional Commit;
scratch artifacts, production code, tests and prior reports remain unchanged.
No push or next experiment is authorized.

## Interpretation and limitations

Confirmed: all four configurations preserve the known Unicode at both observed
backend boundaries in both repetitions. H2's preregistered failure is absent;
there is no demonstrated divergence in these fixtures. The compiled CMap branch,
fallback conditions and private-case decoder responsibility remain UNKNOWN.

Differences from c1-0043, based only on the ML-15 report, remain uncontrolled:
this experiment uses a complete public font, valid checksums and an explicit
sparse CIDToGID stream; the private source used subset-like sparse glyph coverage,
CIDToGIDMap=Identity, different cmap contents, checksum anomalies and much longer
text/layout. This test uses only CIDs 257..260 and two short scalar ranges.
Any role of these differences is a hypothesis, not a cause established here.
No ligatures, multiple fonts, complex destinations or broad CID range coverage.
PDFium's previously reported private-case ligature limitation is not retested.
Four controlled fixtures and two repetitions are not a population estimate.

No production parser repair or expected-failure regression asserting this bug is
justified by this result. The public fixtures are passing controls. The smallest
future action would be separately reviewed, bounded native CMap-path inspection
or a single preregistered public-font mapping contrast for one remaining
difference, with independent validity checks. None is implemented or started.
c1-0043 evidence loss, other frozen candidate regressions and candidate REJECT
remain unresolved; no promotion, quality improvement or ML-17 is claimed.

Directly relevant official context only: PAR-01
[pypdf 6.20.0 text extraction](https://pypdf.readthedocs.io/en/6.20.0/user/extract-text.html),
PAR-05 [Docling documentation](https://docling-project.github.io/docling/), TST-02
[pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html).
The 2x2 control design and existing parametrized regressions are concrete local
evidence; vendor documentation does not establish the native mechanism.
