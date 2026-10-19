# DocLens AI project contract

DocLens is a Python/FastAPI modular monolith for PDF/DOCX/XLSX intelligence.
Correctness, tenant isolation, reproducibility and measurable evidence come first.

## Instruction hierarchy and navigation

Follow platform instructions, current user scope, then applicable AGENTS.md files.
Read root and affected nested instructions before implementation. Use
[README_SOURCE_MAP.md](README_SOURCE_MAP.md) to select owners and only relevant sources.
Do not modify instructions unless the task authorizes it. Report essential missing
sources and substantive conflicts before changing critical contracts; never invent them.

## One scoped step

- Establish branch, HEAD, status, previous verdict and relevant existing changes.
- State Goal, READ/MODIFY/CREATE paths, tasks, constraints, acceptance, verification
  and Git action; cite 2–4 relevant sources before editing.
- Read only affected code/tests/config/reports. Load relevant project skills when
  needed; their procedures apply owner documents, not independent requirements.
- Bugs: reproduce → cause → smallest fix → regression → verify. Preserve working
  behavior, unrelated/staged edits, architecture and security invariants.
- No unrelated refactoring/dependencies/future stages. Report out-of-scope issues.
  Stop after the requested step/review gate; do not start another experiment.

## Sources and claims

[P-ARCH](Doclens_AI-architecture.md) is the maintained v4 architecture.
[DOCX v3](Doclens_AI-architecture.docx) is historical (15–17 October 2026, snapshot
`9b39846`), not current authority or current-HEAD verification. P-REPO means current
code/config/migrations/tests plus scoped executed evidence. P-ML/P-GPU route through
the source map. The v4 Markdown documents are authored requirements adopted by this
task, not recovered originals. Do not claim unavailable attachments were read.

IMPLEMENTED requires code and stated verification scope; code inspection must be
labelled and does not imply behavioral PASS. OFFLINE BASELINE = measured comparator;
TARGET = undelivered; CANDIDATE = experimental; REJECTED = failed frozen configuration;
NOT_EVALUATED = no defensible measurement. Historical tests/results remain historical.
Separate execution PASS/FIX/BLOCKED, quality PASS/FAIL/NOT_EVALUATED, experiment
PROMOTE/REJECT/INCONCLUSIVE and production authorization. Schema validity, extraction
success, indexing eligibility or CUDA execution never establishes factual/release PASS.

Use pinned/version-matched official references and configured MCP when needed;
[Engineering Sources](DocLens_AI_Engineering_Sources.md) owns stable technical IDs.
Do not export private text/Gold. Do not fabricate APIs, results, credentials or review.

## Contract routing

The following links are mandatory routing, not a second copy of requirements:

- [Architecture](Doclens_AI-architecture.md): PostgreSQL/S3/Qdrant ownership,
  immutable identity/idempotency, leases/fencing, verified ACTIVE publication,
  source/ACL checks, trust/security, lifecycle and dependency roadmap.
- [Quality Policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md): QG-00..QG-09,
  critical safety/evidence failures, approved thresholds and release acceptance.
- [Extraction](DocLens_AI_Extraction_Strategy.md): native baselines, real locators,
  format limits and parser comparisons. Frozen rejected configurations stay scoped.
- [ML Strategy](DocLens_AI_ML_Quality_Strategy.md): provenance/Gold/family splits,
  safe cleaning/chunks, frozen comparisons and independent semantic evidence.
- [GPU Playbook](DocLens_AI_Kaggle_GPU_Playbook.md): explicitly authorized cloud work;
  local tasks do not authorize upload or sensitive inference.

Never silently weaken owner contracts. New numerical thresholds remain TBD without
approved evidence. No model/training/framework complexity without demonstrated need.

## Quality and skill routing

Load only applicable `.agents/skills/<name>/SKILL.md` via source map:
`doclens-db-migration`, `doclens-ingestion-change`, `doclens-extraction-benchmark`,
`doclens-rag-evaluation`, `doclens-data-quality`, `doclens-ml-experiment`,
`doclens-kaggle-gpu`, `doclens-production-readiness`.
Preserve stricter compatible procedural checks; report stale/conflicting references.
ML comparisons require reproducible baselines; production qualification is separate.

## Verification, Git and completion

Run targeted tests then broader scope/risk-required checks, including applicable
positive/negative/failure, ACL, retry, delete/reindex and migration scenarios.
Fix task-caused regressions and rerun affected checks. Distinguish executed/passed/
failed/skipped/blocked and prior failures. Never claim tests should pass.

Inspect final diff, staged diff and exact status; confirm scope, secrets/artifacts
and actual required results. Never overwrite user edits, reset/clean, delete shared
resources, rewrite history/applied migrations or commit sensitive/unintended files.
Commit one logical Conventional Commit only when authorized; no success commit with
critical failures/missing required evidence. If review is required, leave uncommitted.

Report:
STATUS: PASS | FIX | BLOCKED
CHANGED: files and purpose.
DESIGN: decisions/sources and target versus implemented boundaries.
VERIFIED: exact commands/results; failures/skips/blockers separately.
REMAINING: limitations/out-of-scope issues or None; stop at this step.
COMMIT: SHA/subject or Not created with reason.
GIT STATUS: exact final git status --short output or why unavailable.

PASS requires all scoped work/checks; FIX means demonstrated in-scope defects remain;
BLOCKED means essential input/environment prevents completion. No unverified
production readiness claims.
