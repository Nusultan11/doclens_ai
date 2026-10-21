# QG-00 assisted review generator reproducibility — 21 October 2026

**Engineering PASS for the scoped generator/handoff only.** Starting HEAD
`f2281b1789227f1a55ddb7ffa70adc37afa8750a`, branch `main`.
Independent Gold and QG-00/QG-01 quality remain **NOT_EVALUATED**.

## Implementation and input boundary

Moved the reusable private draft pipeline into
`tools/extraction_quality/pdf_assisted_review.py` and local static UI assets.
It reuses existing eligibility/preflight, original-page inventory, glyph diagnostics,
physical-ruling checks, Cell/Table models and proposal_review validation. It does not
open or mutate a blind ML29 workspace, import legacy assertions as annotations,
export Gold, install dependencies or change production routing.

Document-specific source IDs, boxes, counting conventions, header-row/language
proposals and requested partitions are **private data inputs**, not embedded in
tracked code/tests. The strict geometry plan contains only whitelisted geometry and
configuration; cell literals and reviewer/approval fields are rejected. Actual text,
numbers, glyph geometry and ruling observations are re-read from the originals.
The CLI requires the exact plan SHA and existing eligibility record. The complete
admitted population must match the plan; blocked candidates cannot be substituted.
Full frozen 90-source / 19-record / five-PDF integrity checks remain in preflight.

The accepted correction is preserved: `c1-0040` has a three-cell year band, with the
middle segment ending at **x=1065.054993** and an empty third segment above the
activity-grid total header. The partition is unruled: source paint/column alignment
is retained as evidence, without inventing a printed vertical divider. Empty-segment
meaning remains unknown. Generic tracked logic applies a declared single-row split;
the actual coordinates, source paint object and expected seed box live in the plan.

The independent-human review and no-fabrication boundaries follow
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA),
[extraction](../../DocLens_AI_Extraction_Strategy.md#EX-PDF),
[QG-00](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES) and the
[eligibility handoff](qg00_review_handoff_20261021.md). Semantic roles, period/header
links, language and family grouping remain hypotheses. User CSV decisions are carried
separately, without filling machine proposal attestations or independent Gold fields.

## Reproduced evidence

Private accepted reference: `evaluation-output/qg00-annotation-rights-20261021/assisted-review/`.
Fresh tracked-code outputs and audit: `evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/`.

- **536 cells; 1,154 items; 13 spanning cells; 60 uncertain cells**. Also 476 supported
  cells, 291 empty cells, zero unknown literal fields; six physical regions/two pages.
- **Both full document records and all 1,154 item records match the accepted package
  exactly**, including every observation, literal, bbox, diagnostic and semantic
  hypothesis. Source PDFs, all eight UI/image assets and the decisions CSV are
  byte-identical to the accepted reference. Neither document regressed.
- Two fresh builds have **18 byte-identical core files each**. Core fingerprint:
  `ed735b8ddaa717c97a1acfb63f511f4ebf37845a84c3853a877b84a85ba05338`.
  This is not byte equality with the old whole package: code/input provenance,
  the generic report banner/summary and historical verification supplements differ.
- **5,817 protected files unchanged**, including accepted outputs, original PDFs,
  frozen Gold, old scripts/packets, eligibility evidence, ML29 workspaces and the
  pre-existing independent engineering audit. New outputs are separate and ignored.
- No private PDF, image, glyph ledger, annotation, plan or decision CSV is staged.
  Tracked tests use independent public synthetic drawings and rights fixtures only.

The private `geometry-plan.json` is a geometry-only revision derived from the prior
535-cell seed plus the accepted split instruction. Its SHA-256 is
`e08d4adc481674320cb70c30a87eb93bd49c31ee6179854acf318f1cd308bcb2`.
It must be restored together with the authorized source/rights/decision inputs on
another checkout. Missing inputs fail closed; Git intentionally does not contain them.
The tracked CLI never executes or imports an ignored Python script. Old ad-hoc
scripts remain unchanged historical evidence; fresh reproduction uses tracked code.

## Exact reproduction and verification commands

From the repository root, using the existing local venv:

```powershell
$env:PYTHONPATH=(Get-Location).Path
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_assisted_review --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --eligibility evaluation-output/qg00-annotation-rights-20261021/eligibility-v2.json --plan evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/geometry-plan.json --plan-sha256 e08d4adc481674320cb70c30a87eb93bd49c31ee6179854acf318f1cd308bcb2 --decisions-from evaluation-output/qg00-annotation-rights-20261021/assisted-review/review_decisions.csv --output evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/run-1
.venv/Scripts/python.exe -B -m tools.extraction_quality.pdf_assisted_review --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --eligibility evaluation-output/qg00-annotation-rights-20261021/eligibility-v2.json --plan evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/geometry-plan.json --plan-sha256 e08d4adc481674320cb70c30a87eb93bd49c31ee6179854acf318f1cd308bcb2 --decisions-from evaluation-output/qg00-annotation-rights-20261021/assisted-review/review_decisions.csv --output evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/run-2
.venv/Scripts/python.exe -B -m pytest tests/unit/test_pdf_assisted_review.py tests/unit/test_pdf_review_eligibility.py tests/unit/test_pdf_table_review_packet.py tests/unit/test_pdf_review_workbench.py tests/unit/test_pdf_review_visual.py tests/unit/test_pdf_grid_proposals.py tests/unit/test_pdf_proposal_review.py tests/unit/test_ml28_review.py tests/unit/test_ml28_evidence.py tests/unit/test_corpus_v2.py tests/unit/test_pdf_cell_recovery.py tests/unit/test_pdf_filled_ruling_normalization.py -q --tb=short --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/tests-final --junitxml=evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/tests-final.xml
.venv/Scripts/python.exe -B evaluation-output/qg00-annotation-rights-20261021/tracked-assisted-reproduction-20261021/verify.py
.venv/Scripts/python.exe -m ruff check src tests tools alembic
git diff --check
git diff --cached --check
git diff --cached --stat
git status --short
```

Existing ML30 browser tests require `ML30_NODE` and `ML30_NODE_MODULES` supplied from
the installed local Node/Playwright runtime. They were explicitly set for execution,
without installing anything. The public synthetic browser test blocks network and
checks file-mode overlays, filtering, CSV export and blank decisions after reload.
Build outputs must be fresh ignored directories; existing destinations are rejected.
The helper audit is private; it compares outputs, accepted payloads and protected
hashes, and is not a runtime dependency of the tracked generator.

Executed test result: **359 passed, zero failures/errors/skips, 245.68s**.
The 17 new synthetic tests cover regular/partitioned generation, exact source/page/plan
SHA binding, invalid/missing/duplicate geometry, rejected body/review fields,
unsupported split/paint/population, plan drift, correction preservation, HTML escaping
and offline browser export. Existing review/geometry/rights regressions also passed.

Initial template-migration syntax and a synthetic fixture page-lifetime error were
corrected before final verification. No failing check is accepted as PASS.

Resolved packages: pypdf 6.20.0, pypdfium2 5.14.0, pdfplumber 0.11.9,
Pillow 13.0.0, pydantic 2.14.0. Versions/code/plan/decision SHA are pinned in outputs.
The supported scope is one-page, rotation-zero, UserUnit-one PDFs with bounded
original raster/glyph/grid sizes. Unsupported inputs fail closed; this step does
not implement broader parser or ingestion functionality.

One focused Conventional Commit contains only the reusable generator, static assets,
public synthetic tests and this sanitized report. Original accepted outputs and
all private data remain ignored/local. No push. Commit SHA and exact final status
are returned in the completion message; the existing audit remains untracked.
