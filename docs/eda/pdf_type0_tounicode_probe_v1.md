# Synthetic Type0/ToUnicode probe v1

**Experiment verification: PASS. Decision: NOT_REPRODUCED.** The one validated
synthetic PDF preserves every expected codepoint at pypdf and the pinned backend
word/textline boundaries in both repetitions. This does not establish decoding
correctness for c1-0043. Docling remains REJECT for production.

## Pre-registration

ML-13, registered on 2026-10-17 at HEAD
`8b18f4a7b685a74885050e2f77ff1e0f29144557`, before fixture creation or extraction.
Hypothesis: the pinned backend may mishandle certain Type0/ToUnicode character
mappings, potentially affecting digit and letter fidelity. This is unproven;
neither the prior private case nor vendor documentation establishes this cause.

One independently constructed primary PDF, no diagnostic control unless needed
for toolchain validation. Use unmodified, locally bundled Bitstream Vera Sans
with its permissive redistribution license retained in ignored scratch. Encode
three lines: uppercase ASCII alphabet, lowercase ASCII alphabet, decimal digits
in ascending order. A Type0/Identity-H font has one embedded CIDFontType2,
explicit CIDToGIDMap and ToUnicode bfchar mappings. Assign consecutive two-byte
CIDs 1–62 to the 62 expected characters; these CIDs differ from Unicode values.
Derive actual glyph IDs/widths from the public font, never private documents.

Independently validate structure, embedded font identity/checksums, CID/glyph
references, ToUnicode codepoints and content operands, then inspect a rendered
page and independent Poppler font/text outputs. Stop if fixture validity cannot
be established; malformed input cannot demonstrate a backend defect. Freeze
fixture bytes, construction settings and expected codepoints before extraction.

Run pypdf and the pinned DoclingParseV4 word/textline backend on identical bytes,
twice in isolated serial workers/new ignored output directories. Compare exact
ordered codepoints, case/digits, substitutions, missing/extra characters and
combining marks. Count all 62 expected characters in each arm, retaining failed
stages as unavailable. Boundary whitespace/line grouping is reported separately;
no Unicode normalization, case folding or guessed correction. Native layout and
adapter conversion are conditional, only if direct backend evidence cannot answer
the question. Use existing offline guard and 600-second/3072-MiB parent monitoring;
no weights, OCR, GPU, model variants, dependencies or large sweep.

Decision: REPRODUCED for incorrect decoding of a validated fixture;
NOT_REPRODUCED for correct decoding at tested boundaries; INCONCLUSIVE for
insufficient mechanism discrimination; BLOCKED for essential tooling/validation
absence. One fixture cannot establish correctness of the private case or the
whole backend. Keep pypdf production and Docling REJECT unchanged. Only this
report may enter Git; all generators, fixture/font/license copies, renderings and
raw outputs stay in verified ignored
`evaluation-output/pdf-type0-tounicode-v1-20261017/`.

Toolchain clarification before backend evaluation: bundled Poppler contains
pdfinfo/pdftoppm, but not pdffonts/pdftotext; no install was attempted. Independent
text validation therefore uses existing PDFium, alongside strict pypdf structural
validation, explicit map/content checks and Poppler rendering. No outcome or
acceptance criterion changes. Generator: bundled Python 3.12.14, pypdf 6.10.0,
ReportLab 4.4.9. Evaluation: isolated Python 3.12.3, pypdf 6.20.0, Docling 2.55.1,
core 2.48.2, docling-parse 4.7.3, PDFium wrapper 4.30.0, psutil 7.1.0.

Fixture frozen before benchmark extraction: 69865 bytes, SHA-256
`2028fe685116119285f44d9fcc20c45ae1c2db37ec015f371d8379679a33a99a`.
Validation passed: Type0/Identity-H, one embedded CIDFontType2, 62 explicit
ToUnicode pairs, 63 CIDToGID entries including CID 0, no undefined used CIDs,
all 17 embedded SFNT table checksums and whole-font checksum, expected content
operands and independent PDFium text 62/62. Poppler parsed one unencrypted PDF 1.7
page, 612x792 points. Its rendered PNG was visually inspected: all three lines
legible, correct case/digits, no clipping, overlap, substitution boxes or missing
glyphs. This establishes this fixture's tested structural/rendering validity,
not formal PDF/A or complete ISO conformance. No control PDF is needed.

## Fixture identity and validation

The construction uses ReportLab's existing TrueType reader for public-font
metrics/glyph IDs and pypdf's low-level PDF object writer; it does not use
ReportLab's default simple-font PDF encoding. One page, one full unmodified
embedded font, three text-show operations at x=54 and y=700/660/620 points,
20-point text, 612x792-point page, PDF 1.7. Each expected character gets one
two-byte CID, an explicit glyph index and width, and one UTF-16BE ToUnicode entry.
No random input, private source, private font or reviewed Gold is used.

An independently written validator imports no generator/constructed expectation
JSON. It derives the alphabet/digit ranges separately; parses the PDF strictly
with pinned pypdf 6.20.0; checks the font dictionaries, Identity-H/CIDSystemInfo,
descriptor, embedded-font hash/length, all SFNT checksums, glyph-index bounds,
width count, codespace, 62 unique bfchar pairs and all three content operands.
Manual CMap application to those actual CID operands yields the expected 62
codepoints. Independent PDFium text and Poppler-render inspection agree with
the expected glyphs. These checks precede Docling evaluation. PDFium's initial
default get_text_range call emitted its implicit-redirection UserWarning; the
validator was changed to explicit get_text_bounded and rerun successfully before
backend runs. Fixture bytes and acceptance criteria never changed.

The locally bundled font is Bitstream Vera Sans Roman, unmodified, SHA-256
`c4c45690b345435b2cba52ecabe275f05e49b389b39fe68ad03afbb551288d3d`.
The accompanying license permits use, embedding/copying and redistribution under
its notice/name conditions. Its full notice is retained beside the ignored font
copy; license SHA-256
`3361d054759a2fc686a2c058be82deaf9c2e6fe549be9004d7935a6c1736315d`.
No font modification, download, dependency addition or font distribution in Git.

## Exact character results

Both repetitions have identical complete result objects and deterministic
fingerprint
`09c089a4a46930cccb82ed35ff614831ec1d6a83e9e605a7b271820e94fd7b1b`.
Every codepoint in the following ordered lists has observed=expected at its
individual position in all three tested representations, in both runs:

```text
Uppercase: U+0041 U+0042 U+0043 U+0044 U+0045 U+0046 U+0047 U+0048 U+0049
           U+004A U+004B U+004C U+004D U+004E U+004F U+0050 U+0051 U+0052
           U+0053 U+0054 U+0055 U+0056 U+0057 U+0058 U+0059 U+005A
Lowercase: U+0061 U+0062 U+0063 U+0064 U+0065 U+0066 U+0067 U+0068 U+0069
           U+006A U+006B U+006C U+006D U+006E U+006F U+0070 U+0071 U+0072
           U+0073 U+0074 U+0075 U+0076 U+0077 U+0078 U+0079 U+007A
Digits:    U+0030 U+0031 U+0032 U+0033 U+0034 U+0035 U+0036 U+0037 U+0038 U+0039
```

| Expected public synthetic line | CIDs | pypdf | Backend words | Backend textlines |
| --- | --- | --- | --- | --- |
| ABCDEFGHIJKLMNOPQRSTUVWXYZ | 1–26 | 26/26 exact | 26/26 exact | 26/26 exact |
| abcdefghijklmnopqrstuvwxyz | 27–52 | 26/26 exact | 26/26 exact | 26/26 exact |
| 0123456789 | 53–62 | 10/10 exact | 10/10 exact | 10/10 exact |
| All 62 positions, each run | 1–62 | 62/62 | 62/62 | 62/62 |

Each actual field list is exactly the three strings above: no internal
whitespace was removed to obtain the result. The baseline's raw one-page text
contains two U+000A separators between lines; splitlines exposes the three
fields. These layout separators are reported separately from the 62 mapped
characters. No case folding, NFC/NFKC, accent stripping, rounding, remapping or
guessed character correction. Per-character expected/observed codepoint records
are retained in each ignored result JSON.

All three representations classify as **correctly_decoded**. Each has three
fields, zero substituted/missing/extra mapped characters, zero combining marks,
and exact digit/case sequences. No unexpected fragmentation is observed. pypdf's
ExtractionResult is success with the existing informational table warning; the
backend's successful parse alone is not the fidelity evidence—the explicit
62-position comparisons are. Neither arm failed; all expected characters stay
in denominators. Repeating the same fixture is reproducibility evidence, not
124 independent character cases or two independent documents.

**Earliest observed divergence: none at the tested boundaries.** Direct backend
calls use InputDocument(PDF, DoclingParseV4DocumentBackend), load_page(0) and
get_segmented_page(). Defaults remain create_words=True, create_textlines=True,
keep_chars=False, keep_lines=False, keep_images=True, enforce_same_font=True.
No backend option or source was changed. Native Docling document construction
and the offline adapter are NOT_EVALUATED/not run because direct testing answers
this fixture's question. Retained char_cells=0 follows the default keep setting,
not a claim about absent source characters.

## Resources, reproducibility and limits

Serial fresh spawned workers use the previously verified scratch monitor,
unchanged SHA-256
`104f7329f34b4cc4e68d2fc0bd1d7e4402bb3aede85ae03c742db502b1b0aa67`.
The parent journals samples and handles poll/recv closure; both worker PIDs match
the actual base Python executable, SHA-256
`15b41a488c356c0e331facdea6c836a6cec021f12d5fde9844e7ca4a1aa0361a`.
The memory guard is 3221225472 process bytes and timeout 600 seconds, memory-first.
No guard fired, IPC failure, monitor error or worker failure. Both exited 0 and
were joined normally; neither required terminate/kill. No descendants were
observed or left alive. Checkpoints actually received were input_validation,
baseline_extraction, conversion (direct backend), source_integrity, then complete.

| Repetition | Parent / worker PID | Peak bytes (MiB) | Wall seconds | Samples / max gap seconds |
| --- | --- | --- | ---: | --- |
| 1 | 23504 / 16992 | 296505344 (282.76953125) | 6.707823899996583 | 117 / 0.06513190000259783 |
| 2 | 14864 / 7308 | 297115648 (283.3515625) | 4.88783200000762 | 85 / 0.06515840000065509 |

These are paired-worker measurements including imports/baseline/backend/cleanup,
using psutil peak_wset with RSS fallback, not separate stage peaks or summed-tree
measurements. A sampled guard is not a hard OS cap. Independent native allocation
owner and per-stage peaks are UNKNOWN. Host: Windows 11, AMD64, 16 logical CPUs;
serial comparison with OMP_NUM_THREADS=2 and MKL_NUM_THREADS=2. Those environment
settings do not establish measured backend thread concurrency. The full CPU/two-
thread FAST layout pipeline was not loaded. Model weights/revisions are not
applicable to these direct calls; no model was initialized or downloaded, and no
OCR, remote service, GPU or full conversion ran. Existing private-offline guard
blocked Python socket connections and third-party logs; it is not an OS firewall.

The font's Unicode cmap and PDF ToUnicode are consistent here. This passing
fixture therefore does not distinguish their precedence or prove which map the
backend used internally. It covers one full font, one Identity-H/CIDFontType2
configuration, explicit BMP bfchar entries and simple ASCII. Subset/conflicting
maps, bfrange variants, sparse/complex encodings, non-BMP characters, ligatures,
private fonts and semantic extraction are NOT_EVALUATED. The private c1-0043
source/Gold/fonts/glyphs/mappings/captures were not opened or copied in ML-13.
Only its sanitized report was consulted. Its demonstrated substitutions remain
unresolved; this fixture neither reproduces nor disproves that failure.

## Actual commands and verification

Commands ran from the repository root. `$bundledPython` and `$bundledNode`
abbreviate the exact installed executables returned by load_workspace_dependencies;
the PDF marker path abbreviates the installed PDF skill's container_tools helper.
Scratch paths below were verified ignored before writing. PDF authoring marker
ran once, exit 0, immediately before the single generator execution:

```powershell
git merge-base --is-ancestor 8b18f4a7b685a74885050e2f77ff1e0f29144557 HEAD
git check-ignore evaluation-output/pdf-type0-tounicode-v1-20261017/generate.py
& $bundledNode <pdf-skill>/container_tools/mark_artifact_operation_started.mjs --operation-kind create --expected-output-count 1 --output-format pdf
& $bundledPython -B evaluation-output/pdf-type0-tounicode-v1-20261017/generate.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-type0-tounicode-v1-20261017/validate.py
pdfinfo evaluation-output/pdf-type0-tounicode-v1-20261017/primary.pdf
pdftoppm -r 100 -singlefile -png evaluation-output/pdf-type0-tounicode-v1-20261017/primary.pdf evaluation-output/pdf-type0-tounicode-v1-20261017/primary-render
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-type0-tounicode-v1-20261017/run_probe.py 1
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-type0-tounicode-v1-20261017/run_probe.py 2
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
```

All listed commands returned exit 0. The ignore check printed the specified
scratch path; ancestor check confirms required HEAD. Optional tool discovery
returned no pdffonts/pdftotext/fontTools, not an experiment failure. Required
tools were present; no dependency installation was needed. Validation returned
structure=PASS, independent_content_mapping=62/62, pdfium_exact_codepoints=62/62,
sfnt_checksums=PASS_all_tables_and_whole_font. pdfinfo returned Pages:1,
Encrypted:no, Suspects:no, File size:69865 bytes, PDF version:1.7; rendering
returned no error and its PNG was visually reviewed.

Both actual run outputs gave the same result for each of pypdf/backend_words/
backend_textlines:

```json
{"classification":"correctly_decoded","combining_marks":0,"digits_exact":true,"equal_positions":62,"field_count":3}
```

Each printed `PINS_UNCHANGED` with deterministic fingerprint
`09c089a4a46930cccb82ed35ff614831ec1d6a83e9e605a7b271820e94fd7b1b`.
All complete non-runtime results match. The focused tests actually reported
**159 passed in 6.41s**, zero failures/skips. Broader tests, Ruff and formatting
were not run for this report-only tracked change. No production code/test change.

| Fingerprint | SHA-256 |
| --- | --- |
| Fixture PDF | `2028fe685116119285f44d9fcc20c45ae1c2db37ec015f371d8379679a33a99a` |
| Generator | `e0f1090831baa04adaa0aa07b095463ce34e1b2c9f06b92b4bcee7b63b491a0f` |
| Independent validator | `35c15093af178c0b728f92945738537f444f2c067f007734939da7e2c54a3a81` |
| Validation record | `ac4292cd55a64621798fded6eb1e7b8211ef0b0e3ad3dbc6ab551f40dba6cb17` |
| Runner | `87559266e8e1bc4198249469241bf7b4237f938119937018cbbd260f7b831581` |
| Frozen registration | `10cadc77db71fd2c9530d381bb359906b8f8c50a11a762a279cf38a3b13969b4` |
| Rendered PNG | `b9748ea327b1408ba578b7927dc433c27992717d0c9af9d03d66d4263ef87d4c` |
| Both complete results JSON bytes | `8a7de7bb4c3bc1f208f53387279d96f38befc6621c60351f33731c7343224ed7` |
| Run 1 resource summary | `378598d789d42264544399888b03156792d0c835352ffc1766b1dd103494a4fb` |
| Run 2 resource summary | `b89c3a8ebff8442a9c8c6fbcb6d24ff5eb6f1b3b9de534476c71b02294242c53` |
| Production parser, unchanged | `151186e13dfd0407ade2276217d6a0d07db39e9634cbf676fc34d42cf88a44c8` |
| Candidate, unchanged | `8b9bbcdcc4a3951da27107fc4ef9cca4ef3a5bcee99e37ec9f8dc14018038973` |
| Scorer, unchanged | `59bc64a98c58c8e2561af5fc8d50955e1c99f2ea7fc32d549ce8e5ebf069b31c` |
| Gold validator, unchanged | `4065b83b27c76fc7d6b615b393ad767d30415b43fa5dca83c31c859b748b07af` |
| Pinned Docling backend | `c4205b69a5e334dace6a877db6606e09b7b998bfe2a664cd1b65cec556c61b7c` |
| Pinned docling-parse wrapper | `3851bb66444b72b6c5aca6ca27d61b2fdc5d4a9363ff4bad89f2f7a7109db52f` |
| Pinned native parser binary | `1dc5839ceabd8576b51ebdd035382c5515e79b8dcdde7169bb83a7da2fe768e1` |

Engineering evidence: repository PDF extraction/offline-guard interfaces; exact
installed DoclingParseV4PageBackend._ensure_parsed and document load_page;
independent PDF object/font/Unicode checks and bundled font license. PAR-01 and
PAR-05 identify the official pypdf/Docling documentation, but no vendor statement
is used as evidence of a defect in the private case. No external documents,
source text or Gold were sent to a service.
The supplied [PAR-01](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
and [PAR-05](https://docling-project.github.io/docling/) URLs were opened directly.
The stable pypdf page identified itself as 6.21.1, newer than the pinned runtime;
version-specific execution therefore follows inspected local 6.20.0/Docling
source, not an assumed match to current documentation.

## Decision and recommendation

**NOT_REPRODUCED.** This independently validated mapping decodes correctly at
every tested position and boundary. No defective function or divergence is
identified; the earliest internal cause of the private failure stays UNKNOWN.
A decoder-specific patch is not justified by this fixture. Retain pypdf as the
dependable production text baseline and require a validated mechanism-specific
reproducer before proposing decoder changes. No correction is implemented.
c1-0040 table locators, c1-0049 furniture/order and c1-0045 native memory ownership
remain unresolved. Docling remains REJECT for production. Stop after ML-13.

## Final privacy, scope and Git review

```powershell
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/pdf-type0-tounicode-v1-20261017/verify.py
git add -- docs/eda/pdf_type0_tounicode_probe_v1.md
git diff --cached -- docs/eda/pdf_type0_tounicode_probe_v1.md
git diff --check
git diff --cached --check
git diff HEAD --name-only
git status --short
```

Final verifier exit 0: verification=PASS, decision=NOT_REPRODUCED,
all_per_character_comparisons_equal=true, complete_results_identical=true,
resource_journals=PASS, cleanup=PASS, source_code_and_prior_report_pins=UNCHANGED,
private_inputs_opened=false, privacy_provenance=PASS, ignored_artifacts=PASS,
tracked_allowlist=PASS, full_conversions=0 and model_loads=0. Every resource
journal was independently checked against its parent summary and identity.
The public synthetic character strings in this report are intended disclosure;
no private originals, Gold, font/mapping payloads, real document filenames,
absolute private paths, credentials or model weights are included. Provenance
audit checks the generator/validator/runner inputs without reopening private data.
Initial final-verifier runs exited 1 because drive-pattern checks confused HTTPS
scheme syntax, then its quoted example in this explanation, with a drive path.
The ignored verifier's drive-boundary rule and this explanation were corrected;
the final scan found zero drive paths and returned exit 0/PASS. No fixture,
result or criterion changed.

Both Git whitespace checks returned exit 0 with no output. Full staged diff was
reviewed. Only this new report is staged; fixture/font/license/scripts/images/raw
results remain ignored. The four initial rag_sufficiency_dev entries remain
untracked and unread. Root completion instructions were rechecked. Commit scope
is this report only, with subject `docs: probe PDF Type0 Unicode decoding`.
