# ML-15: c1-0043 glyph/Unicode mapping audit v1

EXECUTION: PASS
PREREGISTERED H1: NOT_REPRODUCED
FROZEN DOCLING QUALITY: REJECT; production pypdf unchanged.

The tested font-cmap precedence explanation is contradicted at all 44 changed
anchor positions. PDF ToUnicode, the independently decoded embedded Unicode cmap
and the independently inspected glyphs support the baseline characters, while the
captured backend emits different characters. A narrower exploratory signature is
confirmed: all 44 substitutions involve high-byte-nonzero CIDs in scalar
`bfrange` entries, and each emitted Unicode scalar equals the raw CID. This
localizes a mapping boundary; it does not identify the compiled decoder branch
or justify a production fix.

## Scope, freeze and preregistered hypothesis

Read-only audit at HEAD `3561c726b2a793e24dc11263a4882f5b5188dc06`, branch main,
initial worktree clean. Read the four requested reports/protocol, applicable
AGENTS.md and extraction/experiment skills; inspected only relevant extraction
functions and installed backend wrappers. The PDF skill guided independent glyph
inspection. External GOAL, QG-01, EVALUATION and ENGINEERING policy definitions
are UNAVAILABLE; no absent gate is invented or claimed passed.

Preflight verified all 90 frozen originals, strict 19-record reviewed Gold,
source size/SHA, both expanded-v1 and picture-text-v1 report identities, and the
existing ML-12 private capture. Ninety-five prior input/code/test/capture files
were hashed before inspection and rechecked afterward. No private input, prior
capture, Gold, source, test, model or configuration changed. No Docling call,
OCR, model initialization/download or benchmark rerun occurred.

Registered at `2026-10-18T04:11:03.384292+00:00`, before additional mappings:

> H1: Where PDF ToUnicode and the unique inverse Unicode cmap of the
> CIDToGID-selected embedded glyph disagree, the captured backend follows the
> embedded-font cmap rather than PDF ToUnicode in both known font groups.

REPRODUCED required discriminating conflicts in both groups, complete unique
correspondence for all 44 altered positions, predicted backend values and
independent glyph support. Complete contradictory mappings imply NOT_REPRODUCED;
missing/ambiguous mappings or glyph correspondence imply INCONCLUSIVE. Decode
actual content bytes and both font routes first, persist them, then locate the
six existing opaque anchors. Gold supplies locations only; no Gold-derived
decoding or substitution rule is used. The protocol and acceptance are unchanged.

All new scripts, raw mappings, embedded fonts, per-character records and images
remain ignored under `evaluation-output/pdf-c1-0043-glyph-unicode-audit-v1-20261018/`
(called `$scratch` below). Only this sanitized report is an intended Git change.

## Independent structural and font audit

Strict PDF object inspection found four pages. Both relevant fonts are embedded
Type0/Identity-H with CIDFontType2 descendants and explicit CIDToGIDMap=Identity:
actual two-byte text-show code = CID = GID. All used codes have ToUnicode entries
and in-bounds nonzero GIDs. Parsed 2,590 relevant text-show strings / 5,328 CID
occurrences, with 36 and 71 distinct used codes. Other font groups are outside
this audit's font denominator; these are not complete-document fidelity counts.

| Observation | Group g1 | Group g2 |
|---|---:|---:|
| Embedded font bytes | 24032 | 29528 |
| ToUnicode expanded entries / used codes | 36 / 36 | 71 / 71 |
| bfchar entries / bfrange entries | 29 / 3 | 47 / 8 |
| Used CID occurrences | 236 | 5092 |
| Unicode cmap entries per subtable | 52 | 99 |
| SFNT tables / declared glyph slots | 13 / 1287 | 13 / 1287 |
| Nonempty glyph records | 76 | 172 |
| Table checksums passing | 12/13 | 12/13 |
| Whole-font checksum | mismatch | mismatch |
| Distinct altered glyphs inspected | 5 | 11 |

Both fonts have matching platform-0/encoding-3 and platform-3/encoding-1 format-4
Unicode cmap subtables. An independent byte-level reader checked table bounds,
segment address/delta calculations, GID bounds, monotone loca offsets and glyph
record bounds. Existing ReportLab 4.4.9 independently agrees on all 52/99 cmap
entries. Its checksum enforcement was disabled; it is a mapping cross-check,
not a second checksum pass.

The checksum mismatches are real audit findings: head fails the checksum computed
with checkSumAdjustment zeroed; the other 12 table checksums pass. Whole-font sums
also mismatch. This is not a formal font/PDF-conformance PASS. Their causal role
is UNKNOWN; both independent font readers and PDFium load these unchanged bytes.
No checksum was corrected or condition silently waived. Both post tables are
format 3 with no glyph-name array, so no embedded post-name correspondence was
available to test.

Two independently written CMap readers agree on all 36/71 mappings, including
bfchar, scalar bfrange expansion and multi-codepoint UTF-16BE destinations. PDF
hex-string whitespace is parsed as syntax, not Unicode normalization. Outside
the 44 altered positions, g1/g2 have one/two unique inverse-cmap differences
involving compatibility ligatures, plus one used code per group without an
inverse Unicode cmap entry. These limits are retained; no full-font equivalence
or universal decoding claim follows.

## Comparison with the original captured boundaries

At every altered anchor position the inverse embedded cmap is unique, agrees
with PDF ToUnicode and disagrees with the captured backend. Thus H1 fails its
registered observable prediction in both groups; this is NOT_REPRODUCED rather
than an assertion that font precedence can never cause another PDF defect.

| Anchor | Page | Group | Normalized characters | Changed | Both independent maps support source | Backend equals raw CID scalar |
|---|---:|---|---:|---:|---:|---:|
| a1 | 1 | g1 | 55 | 5 | 5/5 | 5/5 |
| a2 | 1 | g2 | 11 | 6 | 6/6 | 6/6 |
| a3 | 1 | g1 | 10 | 1 | 1/1 | 1/1 |
| a4 | 2 | g1 | 20 | 1 | 1/1 | 1/1 |
| a5 | 2 | g2 | 56 | 19 | 19/19 | 19/19 |
| a6 | 3 | g1 | 54 | 12 | 12/12 | 12/12 |
| Total | | | 206 | 44 | 44/44 | 44/44 |

The 180 non-whitespace anchor positions have this exploratory, post-H1 pattern:

| ToUnicode entry form / CID class | Unchanged | Changed |
|---|---:|---:|
| bfchar / high byte zero | 50 | 0 |
| bfchar / high byte nonzero | 84 | 0 |
| bfrange / high byte zero | 2 | 0 |
| bfrange / high byte nonzero | 0 | 44 |

All 44 changed positions are scalar bfrange mappings; none follows the unique
embedded cmap value, and all instead equal the raw CID scalar. This is an exact
numeric association with the captured text, not a guessed character replacement.
The broad exploratory predictor "all bfrange becomes raw CID" matches only
178/180 positions: the two low-CID bfrange positions are decoded correctly.
An early scratch interpretation attributing those exceptions to multi-codepoint
ranges was checked and rejected; all inspected range destinations are scalar.
No post-hoc rule was installed and no corrected extraction was produced.

Independent PDFium 126.0.6462.0 text agrees on all 44 disputed positions after
diagnostic monotone alignment. It exposes the exact same embedded font-program
hashes as the PDF objects. PDFium-rendered isolated glyphs and separate FreeType
rendering through each embedded cmap were visually inspected for all 16 distinct
affected glyphs (5/11), supporting the source shapes. This is AI-assisted local
inspection, not new human Gold review or whole-document visual certification.
Missing-glyph boxes in the atlas's backend-value column are subset-font coverage
placeholders, not glyphs drawn in the source PDF.

PDFium is not substituted as ground truth wholesale: only a1/a2/a4 match as
complete raw anchors. Its text path omits one component of a multi-codepoint
ToUnicode glyph in each of a3/a5/a6. Those three omissions are outside the 44
Docling-altered positions. They remain a separate independent-engine limitation.
NFKC was checked diagnostically and did not recover those raw anchors; it also
classifies the non-disputed compatibility ligatures above. It is not used in the
44-position comparison or to change outputs/scores. No OCR or output repair.
All 44 comparisons have mapped positions with zero missing/ambiguous inverse maps.

Earliest directly observed divergence remains the captured backend word/textline
boundary, before layout, native-document assembly and the project adapter.
Installed _to_cells copies native row text into text/orig; keep_chars=False and
the word/line-cell branches do not expose a captured character-level trace.
This narrows the investigation toward native CMap expansion/lookup or fallback,
but the exact compiled branch, fallback condition and responsibility of font
checksum anomalies remain UNKNOWN. No internal native_build phase is claimed.

Frozen outcomes remain pypdf needs_review, 6/6 anchors and provenance, 4/4 order;
Docling success, 0/6 anchors/provenance and 0/4 order. All six anchors and four
order checks remain in denominators. Table/cell/value dimensions have no labels
here and are NOT_EVALUATED. The 12-PDF benchmark population and metrics are not
rescored. Status success does not establish evidence fidelity.

## Smallest justified next action, not implemented

A narrowly scoped synthetic backend regression fixture is justified; a parser
patch is not yet justified. Use one redistributable public font, independently
validated glyphs and explicit CIDToGIDMap. Hold glyphs/Unicode fixed while varying
bfchar versus scalar bfrange and zero versus nonzero CID high byte. Include a
digit and a letter, correct font checksums and explicit word/textline assertions.
ML-13 tested only bfchar with low CIDs, so its 62/62 result does not exercise this
observed boundary. Reproduce on that small fixture before identifying an upstream
lookup/expansion fix. Do not copy private fonts/mappings or infer Gold replacement
rules. No fixture, parser repair or next experiment was implemented here.

## Fingerprints and runtime

| Identity | SHA-256 / fingerprint |
|---|---|
| Manifest bytes | c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0 |
| Source, 91484 bytes | b70a5d33160ee12eba6b5f66e305df69b6d504389c11c142657c41d2be45c3ce |
| Gold bytes | f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf |
| Normalized reviewed Gold | 50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e |
| Expanded run 1 / run 2 bytes | dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48 / 3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a |
| Both expanded deterministic reports | d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24 |
| Picture-text run 1 / run 2 bytes | f78aaf265e0fa065f81a7d9b6472ad42f02ce9e956ff703083203b48428c8aeb / 2ece0ad6c59dab7770a97891ed4569f33a745ed5e615c1e29a0a49b319f4f13c |
| Both picture-text deterministic reports | faaef99c1e9bf5be6aa76c92159aee6fa5dd1dfa13bd24a10dab088a6523597d |
| Original ML-12 private capture | 7a3ba4fe49d5afa6a990be07da5c8ba16e5ad7e9db93107fd8eba5ebaea22510 |
| g1 ToUnicode / embedded font | 7ed70602034727694d2d61d17266101ecfe65bcf5d0351d481183e5e5280f473 / ddfc937612068e7808dbe061910e7dc0a133416f5b00e1caa20743492111466f |
| g2 ToUnicode / embedded font | 7ea2b058a9847321c4391ec1885b0a3ea23397a18350baaea588a4581bf12601 / c479917b9c0e727f7947bf93dbc97483a2d305389e5ac7eb5b8b6cdcf04219bc |
| Preregistered protocol | 9e30de923cf5d7403b648f319a81e244664edc0baefc5f9a1705e9d0678a4386 |
| Audit script/map/image freeze manifest | 7ba0d2d7996527154580cf2ec3210f4554576be0b5069431d9255d32c2bb2a43 |
| Independent mapping summary | 75bbbb3a229dd310cf44e196d3b1bb5451cb1f779d819467594477d1a600f4d3 |
| Anchor comparison | 44f4f500970453ddc275414c90ea735812fb6948b2c01ac01d1210c68a9f770b |
| Entry-form comparison | fc97770b2ad02f9f30a9e7be4c81a4f536153a9d8c317ced752e1ee8734aa8ae |
| Independent glyph/text summary | 497b075bc32b403bd5bba4a29e78dcb1dff30a1d7040ec2a5a7c89f7bb78de4a |
| Native parser binary | 1dc5839ceabd8576b51ebdd035382c5515e79b8dcdde7169bb83a7da2fe768e1 |

Audit runtime: Windows 11 AMD64, Python 3.12.3, pypdf 6.20.0, Docling 2.55.1,
core 2.48.2, docling-parse 4.7.3, pypdfium2 4.30.0, psutil 7.1.0.
Independent ReportLab 4.4.9 uses the existing bundled runtime; no install.
Backend wrapper and Python parser hashes match ML-12. The complete per-script,
mapping/image and 95-file prior-artifact pins remain in ignored JSON manifests.

## Commands, checks and resource evidence

PowerShell from repository root. Preflight/protocol freezing used an inline read-only
Python script piped to the pinned audit runtime; its timestamp, complete protocol
and prior-file hashes are retained in the ignored protocol JSON. Later verification
rechecks the same inputs. `$scratch` abbreviates the ignored directory above;
`$runtime` is `evaluation-output/docling-v1-runtime/Scripts/python.exe` and
`$bundledPython` is the installed Codex dependency Python returned by the workspace
dependency tool. Aliases below abbreviate the actual literal command paths.

```powershell
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; $env:HF_HUB_DISABLE_TELEMETRY='1'
git rev-parse HEAD
git branch --show-current
git status --short --untracked-files=all
git check-ignore evaluation-output/pdf-c1-0043-glyph-unicode-audit-v1-20261018/audit_freeze.json
& $runtime -B "$scratch/run_readonly.py" inspect_maps 3
& $runtime -B "$scratch/run_readonly.py" compare_captures
& $runtime -B "$scratch/run_readonly.py" independent_glyphs 2
& $runtime -B "$scratch/run_readonly.py" mapping_entry_audit
& $bundledPython -B "$scratch/crosscheck_reportlab.py"
# Determinism checks after freezing current scripts and map/image outputs:
& $runtime -B "$scratch/run_readonly.py" inspect_maps 4
& $runtime -B "$scratch/run_readonly.py" compare_captures 2
& $runtime -B "$scratch/run_readonly.py" independent_glyphs 3
& $runtime -B "$scratch/run_readonly.py" mapping_entry_audit 2
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

All commands in that successful audit block exited 0. Mapping readers agree;
44/44 comparisons support the source route, 0/44 the H1 backend prediction;
ReportLab checks 52/52 and 99/99 entries. Repeated read-only audits preserve
identical map, comparison and image bytes. Focused regressions: **159 passed in
6.09s**, zero failed/skipped. No new application tests were authored. Broader
suites and tracked-Python Ruff/format checks were NOT_RUN: no tracked Python
changed; existing focused regressions cover the preserved extraction boundary.

The existing verified scratch monitor was reused with audit-only limits of
120 seconds / 536870912 process bytes, sampled approximately every 50 ms.
These are diagnostic ceilings, not changes to the frozen candidate's limits.
Each sampled PID matches the actual base Python executable, SHA
15b41a488c356c0e331facdea6c836a6cec021f12d5fde9844e7ca4a1aa0361a.

| Read-only stage | First successful peak bytes / wall s | Repeat peak bytes / wall s |
|---|---|---|
| Source/font mapping | 72232960 / 1.3980 | 72515584 / 1.3958 |
| Captured-anchor comparison | 69750784 / 1.7541 | 69857280 / 1.7039 |
| PDFium/font glyph inspection | 140910592 / 1.6483 | 140939264 / 1.7567 |
| Exploratory entry-form audit | 70193152 / 1.2954 | 70062080 / 1.4512 |

All eight successful workers completed, exited 0, retained journals and had no
guard breach, monitor error or survivors; no descendants were observed. Peaks
are process peak_wset with RSS fallback, not summed-tree or per-function peaks.
Sampling may miss transients; this is not a hard OS sandbox. Ad-hoc metadata,
ReportLab and documentation checks did not record separate peaks; their resource
peaks/CPU attribution remain UNKNOWN.

Three earlier scratch attempts failed and are preserved, not counted as passes:
two mapping attempts rejected valid whitespace inside multi-codepoint CMap hex
strings (1.2958/1.3438 s; peaks 66654208/66277376 bytes), then one glyph attempt
incorrectly required complete raw PDFium anchor equality (1.3938 s;
121638912 bytes). Only ignored inspection code was corrected. The latter was
replaced with explicit raw-match reporting and diagnostic coordinate alignment,
retaining the three real PDFium omissions; no parser output was changed. Their
worker_failure outcomes and parent journals remain available. The first compound
PowerShell invocation returned shell exit 0 despite its displayed worker_failure;
subsequent explicit failing runner invocations returned 1. No failed attempt
loaded a model or ran Docling. Earlier scratch-source revisions were not separately
frozen; the successful final sources and deterministic outputs are pinned above.

## Privacy, limitations and review gate

Report privacy/scope checks exclude original basenames/paths, all focus Gold
strings, other long Gold strings, raw source text, font names, code-to-character
tables, credentials and binary payloads. Manual review complements pattern
checks. Embedded fonts/images/mappings are local ignored diagnostics, never Git
assets. The initial privacy check found a generic terminology collision with an
unrelated Gold anchor; the overlap was removed and the complete check passed.
An ad-hoc font inventory also initially rejected a nonfocus font lacking
ToUnicode; the completed readers explicitly scope the two known groups. Neither
partial check is reported as a pass.

Final checks:

```powershell
& $runtime -B "$scratch/verify_audit.py"
git diff --check
git diff --cached --check
git diff --no-index --check -- /dev/null docs/eda/pdf_c1_0043_glyph_unicode_mapping_audit_v1.md
git status --short --untracked-files=all
```

The final verifier reports execution=PASS, hypothesis=NOT_REPRODUCED,
prior_files_unchanged=95, changed_positions_verified=44, h1_prediction_matches=0,
independent_glyphs_inspected=16, successfully_monitored_audits=8,
preserved_scratch_failures=3, resources_and_cleanup=PASS, privacy_and_scope=PASS
and staged_files=0. It independently checks UTF-8/newline/trailing whitespace.
Ordinary tracked/staged whitespace checks exit 0. The no-index check of this new
file exits 1 for the new-file difference, with no whitespace-error lines and only
Git's LF-to-CRLF checkout warning; this is not represented as a zero-exit check.
Full new-file diff is reviewed; exactly this report is untracked. No staging or
commit before review.

This is one previously exposed document, not a fresh sealed test. No population
quality improvement, semantic equivalence, visual-layout correctness or parser
promotion is claimed. Font checksum causality, exact native CMap branch and
general behavior outside the inspected mappings remain UNKNOWN. The independent
PDFium text limitation is reported, not silently fixed. Other c1-0040/c1-0049
defects remain outside scope. Stop after this diagnostic.

PAR-01 discusses extraction/ligature/position limits; the version-matched
[pypdf 6.20.0 documentation](https://pypdf.readthedocs.io/en/6.20.0/user/extract-text.html)
was consulted alongside its supplied stable URL. [PAR-05 Docling documentation](https://docling-project.github.io/docling/)
was consulted for context. Neither establishes a native mapping precedence rule;
all mechanism claims above rest on actual local bytes, installed code and captures.
