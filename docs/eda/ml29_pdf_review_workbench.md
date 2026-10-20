# ML-29 — local human PDF table review

For optional mouse-based geometry capture and safe resume of existing drafts, see
[ML-30A visual annotation](ml30a_visual_pdf_annotation.md). The workflow below and its
historical verification remain the ML-29 contract; visual capture adds a local renderer.

The workbench adds no dependencies: its server and UI use Python's standard library
and plain HTML/CSS/JavaScript, alongside the repository's existing pypdf/pydantic
validation dependencies. Use Chrome or Edge with the built-in PDF viewer enabled.
If embedded PDF display is unavailable, use **Open original in a separate viewer tab**.
No model, parser prediction, remote asset, database or production path is used.

From the repository root, start a **fresh** ignored workspace:

```powershell
$env:PYTHONPATH="src;."
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_review_workbench --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --packet evaluation-output/pdf-table-gold-review-v1-20261019/packet-1 --output evaluation-output/ml29-human-review
```

Open the printed `http://127.0.0.1:<port>/<session-token>/` URL locally. The listener
binds only IPv4 loopback and checks Host/Origin and a per-session request token.
Do not share the URL or follow embedded PDF actions/external links. The tool itself
does not make external requests; the browser/PDF viewer is not a network sandbox.
Stop with Ctrl+C. To resume, repeat the command with `--resume`. Run one writer
process per workspace; stale browser tabs are rejected rather than overwriting saves.

1. Select each original and page. Match the native viewer's page number to the UI.
   Mark **I inspected this original page** only after actually inspecting it.
2. Enter page table presence, regions, notes, tables/cells and text anchors in the
   labelled JSON fields. **Add blank table/anchor** supplies empty fields only.
   Cell/relationship templates are expandable; they supply no annotation decisions.
   Enter literal text, zero-based rows/columns, positive spans, header roles,
   uncertainty, evidence references and explicit relationships yourself.
3. Enter bboxes as `[left, bottom, right, top]` in **unrotated PDF user-space points**.
   The workbench checks observed page identities and CropBox bounds. It does not
   measure viewer pixels or infer coordinates. Use an original-page inspection
   method that provides real PDF coordinates, especially for rotated/cropped pages.
   Relationships point from a value to a header/unit/period. For unit/period links,
   also record matching `[target_cell_id, "unit"|"period"]` pairs in the value cell's
   `value_unit_period_links`. Preserve ambiguity instead of guessing.
4. Supply your reviewer ID/date, `kind: "independent_human"`, viewer/version/settings,
   annotation permission reference and all independence/completion attestations.
   Set booleans explicitly; none are pre-approved. Enter family/language/split and
   document reading-order pairs. Save freely while incomplete.
5. Save, then **Freeze completed independent draft**. The existing ML-28 validator
   checks the independent portion before fingerprinting it; incomplete, uncertain,
   conflicting, machine-attributed or unauthorized drafts are blocked. Frozen
   drafts are immutable in the UI. No Gold is returned by independent-only validation.
6. Only after **every selected original** is frozen can you explicitly reveal legacy
   assertions. This prevents one document's labels being disclosed while others
   are still undergoing independent review. Parser predictions are never served.
7. Complete the adjudication JSON yourself, including all assertion/region mappings,
   dates, evidence, corrections and disagreements. No decision is auto-confirmed.
   Save, then **Validate saved population with ML-28**. Its original full validator
   remains authoritative and all undecided/disputed assertions remain blockers.

Existing [ML-28 worksheet fields and mappings](ml28_pdf_evidence_v2.md) still apply.
Independent snapshots and resumable state stay in the ignored output directory.
Each validation writes a fresh `checks/<check_id>/review/` snapshot plus its result.
No Gold is automatically exported. After actual human adjudication, the separate
ML-28 export command can consume that review directory and the corresponding
explicit offline scopes, with all its normal frozen-input checks. Proposed later
corrections belong in adjudication; they do not rewrite the frozen blind snapshot.

Blinding is enforced by server routes, not just hidden HTML. It does not prevent a
local filesystem owner from opening the original packet directly. Reviewer identity
and inspection remain human attestations, not authenticated signatures. Do not
describe a machine-supplied identity or synthetic test as independent human Gold.
No quality gate, experiment promotion or production authorization changes here.

## Executed verification (20 October 2026)

Starting HEAD `61255a588f50e6561c229a2992cf0a2545207cde`, branch `main`; the pre-existing
untracked engineering audit is preserved. No commit is created for ML-29.

```powershell
$env:PYTHONPATH="src;."
.venv/Scripts/python.exe -B -m pytest -q --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/ml29-20261020/tests-final tests/unit/test_pdf_review_workbench.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_ml28_review.py tests/unit/test_ml28_evidence.py --tb=short
# 115 passed in 33.62s; 34 workbench cases plus 81 existing cases; no skips/failures.
.venv/Scripts/python.exe -B evaluation-output/ml29-20261020/intake_audit.py
# 90 RAW sources; 5 PDFs/34 pages; 118 frozen input/audit files unchanged.
.venv/Scripts/ruff.exe check tools/extraction_quality/pdf_review_workbench.py tools/extraction_quality/pdf_review_validation.py tests/unit/test_pdf_review_workbench.py
.venv/Scripts/ruff.exe format --check tools/extraction_quality/pdf_review_workbench.py tools/extraction_quality/pdf_review_validation.py tests/unit/test_pdf_review_workbench.py
git diff --check
git diff --cached --check
git diff --stat
git status --short
```

Loopback HTTP tests used approved local socket access. Synthetic browser verification
saved/reloaded a note and confirmed blank attestations and locked legacy controls;
original PDF bytes and headers were checked over HTTP. Browser PDF rendering across
platforms is not qualified. JavaScript syntax was checked with bundled Node's
`--check tools/extraction_quality/pdf_review_ui/workbench.js`. The first preview
launcher used a relative fixture root rejected by the inherited output guard;
restarting with an absolute fixture root succeeded. No implementation test failed.

Actual independent human reviews remain 0/5. QG-00–03 stay NOT_EVALUATED,
experiment INCONCLUSIVE, production enrichment disabled. A completed tool and
passing synthetic contracts do not establish the truth of human annotations.
