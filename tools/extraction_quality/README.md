# Local independent PDF table review

Use the existing frozen review packet and the
[workbench launcher](../../docs/eda/ml29_pdf_review_workbench.md). Keep original
PDFs, Gold, packets and experimental captures unchanged. All workbench output must
remain in a fresh ignored directory under `evaluation-output/` or `local-evaluation/`.
Use `--resume` to reopen an existing workspace; do not reset it.

## Separate proposal review

1. The independent reviewer starts a **separate original-only workspace** using the
   same packet. Inspect every PDF page, identify tables and their counting convention,
   and record cells, literal text, zero-based rows/columns, spans, roles and real
   unrotated PDF rectangles. The existing rendered original and rectangle tools
   support this step. Complete your own permission, identity and inspection fields.
2. Freeze every independent worksheet before revealing legacy assertions or machine
   proposals. An assisted workspace remains ineligible for this blind freeze, even
   if its proposals were not accepted. Do not strip assistance provenance or claim
   unseen predictions after exposure.
3. Reveal the comparison phase. In **Review proposed cells**, import a saved
   `grid-proposals/*.json` sidecar from the assisted workspace. Import checks the
   packet, source hash, document and page identity. It retains both the machine
   candidate and the corrected proposal; every review decision starts unreviewed.
4. Inspect each proposed cell beside the original. Purple outlines the proposed
   rectangle; green outlines the selected frozen independent cell on the current
   page. Table ID/index, row, column, spans, text, page and bounding box are shown.
   Navigate to the indicated page when the two locations differ.
5. **Confirm** requires exact agreement with independent table identity, grid and
   source locator. **Correct mapping** selects a cell already recorded in the blind
   worksheet; it never edits that frozen evidence. Old sidecars without a table ID
   need an explicit corrected mapping. **Reject** requires no independent target.
   Supply your own reviewer ID/date, original-page evidence (`page_number` and
   `bbox`), rationale/counting convention and ambiguity decision, then save.
6. Resolve the existing legacy adjudication as before, then validate. Missing,
   conflicting, ambiguous or incomplete proposal decisions block export. Imported
   proposals cannot be silently removed or relabelled through worksheet saves.
7. Enter a new independent Gold revision name. **Export validated independent Gold** writes a fresh
   `checks/check-*/reviewed-gold-v2.json`. Only independently authored frozen cells
   enter Gold. Rejections and corrections remain in the accompanying adjudication
   audit, whose fingerprint is bound into each exported document. Existing Gold is
   never overwritten. The standalone validator enforces the same proposal checks.

If the required independent cell is absent, obtain a separate blind annotation
revision rather than inventing a correction. In
[c1-0040](../../docs/eda/pdf_c1_0040_table_locator_alignment_v1.md), matching repeated
text did not establish the correct table, row, column or first source occurrence;
those conventions and any split-cell interpretation still require human review.

These checks validate supplied attestations and mappings. They do not authenticate
reviewer identity, perform human review or establish extraction/production quality.

## Offline physical-cell text recovery

`pdf_cell_recovery` repairs text ownership using original PDF glyphs and an explicitly
supplied physical-cell proposal. It ignores reference literals and relationships,
verifies source SHA/page identity, grid coverage, opaque thin filled ruling rectangles
and absence of internal dividers, then reuses the existing conservative glyph checks.
It preserves cell IDs, rows/columns, spans and measured rectangles. Each recovered
literal includes its original character range, glyph coordinates and mapping flags.
No predicted neighboring fields are concatenated or reassigned by repeated text.

```powershell
$env:PYTHONPATH='src;.'
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_cell_recovery --source <original.pdf> --source-sha256 <original-sha256> --proposal <bound-proposal.json> --output evaluation-output/pdf-cell-recovery-example
```

Output must be a fresh ignored `pdf-cell-recovery-*` directory. `cell-evidence.json`
contains separate machine evidence, not a replacement for the native capture or Gold.
Unverified/clipped/occluded boundaries and genuine cross-cell glyphs fail closed.
Empty text-layer cells stay unfilled; position-inferred separators remain explicitly
uncertain. Unsupported strokes, page transforms and semantic relationships require
separate evidence. Production routing and independent-review requirements are unchanged.
