# DocLens extraction strategy

AVAILABLE LOCAL EDITORIAL SPECIFICATION, reconstructed 19 October 2026 from
architecture v3 §§7–8, 13, the reconstruction brief and extraction skill.
Not a recovered original or a parser promotion. Owns extraction representation,
format limitations and fidelity methods. Acceptance belongs to
[QG-01/QG-02](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES);
worker/storage lifecycle remains owned by architecture §§5–6, 9.

<a id="EX-ARCH"></a>
## [EX-ARCH] Unified extraction contract

Keep production baselines pypdf, python-docx and openpyxl; dependency ranges are
in `pyproject.toml`, not fixed installed-version attestations. The production PDF
baseline remains pypdf; the frozen expanded Docling configuration is REJECTED.
Other Docling/OCR/ancillary adapters remain candidates until separately evaluated.

Target representation: source/document/version identity, RAW SHA-256, parser and
configuration revision, original text or typed value, genuine locator, reading
order, table/header/value relationships, warnings and immutable provenance.
Distinguish target fields from the current ExtractionResult/canonical span schema;
do not claim every format currently supplies every field. Mark unavailable
dimensions explicitly rather than inventing structure or coordinates.

Keep success / needs_review / failed separate from measured fidelity. Ambiguous
structure or lost critical evidence requires review/failure under the applicable
policy; success is never proof of completeness. Preserve signs, numbers, precision,
dates, identifiers/leading zeros, units, negations, formulas and relationships.
Safe Unicode/whitespace cleaning must retain original facts and a verified offset
mapping when positions change; do not silently repair semantic values.

Never execute Office macros, formulas, external references or document instructions.
Apply input/MIME/signature/size/archive limits and isolate parser failures. Resource
caps, hard timeouts and OS/egress isolation are requirements to verify, not guarantees
established by parser-library use or this document.

<a id="EX-PDF"></a>
## [EX-PDF] PDF and selective OCR

Preserve genuine page numbers and ordered source spans. Layout/table/column
relationships require verified parser evidence; plain text proximity does not
establish a table. Preserve numbers/signs and header/value links, including units.
Native extraction can miss text encoded as shapes/images, unusual fonts or broken
text layers, and can misorder rotated/multi-column/complex layouts.

Selective OCR is an evaluated candidate for explicitly selected pages after triage
and original-page review. Scans need OCR; a heuristic low-text flag is not proof of
a scan. Pin engine/model/languages/DPI, routing, resource limits and fallback.
Do not silently OCR all pages or merge conflicting native/OCR outputs. Define
deduplication, order and locator mapping before mixed-document routing. Fallback
must expose degradation/needs_review rather than imply equal quality.

The DOCX's 17 October statement that OCR is unevaluated is historical. Later offline
work does not itself authorize production OCR. Consult selected current reports
without treating an old snapshot as a current experiment status ledger.

<a id="EX-DOCX"></a>
## [EX-DOCX] DOCX and OOXML references

Current production scope is ordered body paragraphs/tables; complete section and
ancillary coverage is not promised. Required extended representation preserves
package part, relationship and element identity, section membership where genuine,
ordered paragraphs, merges, nested tables, notes and headers/footers. Distinguish
body reading order from ancillary parts rather than inventing a global page order.

Resolve internal references against actual package parts and element addresses;
verify target existence, type, bounds and linkage to the immutable source version.
Shared headers/footers or repeated note references need explicit deduplication and
reference semantics. Missing/ambiguous references are warnings/review, not invented
text locations. Never fabricate Word page numbers without a verified layout engine.
An address validation is not independent reviewed locator correctness.

[ML-21](docs/eda/docx_footnote_candidate_v1.md) is an offline footnote candidate,
not production support for all ancillary OOXML. Validate notes, nested tables and
other parts independently, with unchanged body/table regression controls.

<a id="EX-XLSX"></a>
## [EX-XLSX] XLSX values and tables

Preserve workbook/version, sheet identity (name/index), cell/range coordinates,
typed stored values and numeric precision. Retain formula text separately from
cached results and record missing caches explicitly. Never claim an absent cache
was calculated; never execute formulas/macros/external workbook links.

Display number formats, date interpretation, merged ranges, headers, units and
table membership are distinct dimensions. Stored numeric values are not necessarily
rendered display strings. An unavailable display value is NOT_EVALUATED, not a
guessed formatted number. Sparse/merged cells need explicit anchors; don't duplicate
values or invent row/header relationships. Cross-sheet joins, charts and formula
recalculation are not promised by the baseline. Sheet names can be sensitive.

<a id="EX-EXPERIMENT"></a>
## [EX-EXPERIMENT] Fidelity comparisons and diagnosis

Use [shared experiment controls](DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT)
and the extraction-benchmark skill. Pair baseline/candidate on identical frozen
bytes, reviewed anchors and independent regression controls; record every attempt.
Measure exact text/anchor recall, reading order, table-cell/span/relationship and
locator fidelity, formula/cache preservation and evidence-in-chunk downstream.
OCR adds reviewed page-level CER/WER by language. Report eligibility/status changes,
failures, cold/warm latency and peak RAM with measurement scope.

Run new paired comparisons twice in fresh ignored output directories; compare
deterministic fingerprints and every non-runtime field. Preserve actual timings.
Separate observed native-parser omissions, adapter traversal, order, fragmentation
and locator mismatch from unknown root causes. Critical baseline evidence loss or
fabricated provenance forces REJECT; table gains cannot compensate. No reviewed
Gold means the corresponding fidelity dimension is NOT_EVALUATED. No parser/OCR
promotion follows from successful execution or additional characters alone.
