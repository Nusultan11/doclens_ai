# DocLens documentation source map

Single navigation and ownership index. Start with [AGENTS.md](AGENTS.md), then
select only the owner/sections and evidence needed for the task. Reconstruction
date: 19 October 2026; repository HEAD: `4005adee30375e2a326d5cf8e9cba57bcc894eea`.

## Owners and section routing

All five new Markdown specifications below are **AVAILABLE LOCAL EDITORIAL
SPECIFICATIONS** authored from the current reconstruction brief, architecture and
repository evidence. They are not recovered historical originals, verified old QG
definitions, measured improvements or production approvals. No ZIP was imported.

| Topic | Authoritative owner | Sections |
| --- | --- | --- |
| Repository workflow, scope, verification, Git and completion | [AGENTS.md](AGENTS.md) | One scoped step; Verification, Git and completion |
| Architecture, domain/state/API/ACL/storage/worker/index/recovery contracts and roadmap | [Architecture v3 DOCX](Doclens_AI-architecture.docx) (P-ARCH) | §§2–6, 9–10, 16–20, 23 |
| Product scope, coverage, acceptance and production DoD | [Quality Policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md) | [GOAL](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#GOAL), [COVERAGE](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#COVERAGE), [QUALITY-GATES](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES), [TRUTHFUL-LLM](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#TRUTHFUL-LLM), [EVALUATION](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#EVALUATION), [PRODUCTION-DOD](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#PRODUCTION-DOD) |
| Format representation, extraction limitations/locators and fidelity methods | [Extraction Strategy](DocLens_AI_Extraction_Strategy.md) | [EX-ARCH](DocLens_AI_Extraction_Strategy.md#EX-ARCH), [EX-PDF](DocLens_AI_Extraction_Strategy.md#EX-PDF), [EX-DOCX](DocLens_AI_Extraction_Strategy.md#EX-DOCX), [EX-XLSX](DocLens_AI_Extraction_Strategy.md#EX-XLSX), [EX-EXPERIMENT](DocLens_AI_Extraction_Strategy.md#EX-EXPERIMENT) |
| Data/Gold/splits, chunking, embedding/retrieval, context, generation and comparisons | [ML Strategy](DocLens_AI_ML_Quality_Strategy.md) (P-ML) | [ML-DATA](DocLens_AI_ML_Quality_Strategy.md#ML-DATA), [ML-CHUNK](DocLens_AI_ML_Quality_Strategy.md#ML-CHUNK), [ML-RETRIEVAL](DocLens_AI_ML_Quality_Strategy.md#ML-RETRIEVAL), [ML-EVIDENCE](DocLens_AI_ML_Quality_Strategy.md#ML-EVIDENCE), [ML-GENERATION](DocLens_AI_ML_Quality_Strategy.md#ML-GENERATION), [ML-FINETUNE](DocLens_AI_ML_Quality_Strategy.md#ML-FINETUNE), [ML-EXPERIMENT](DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) |
| Stable technical IDs, URLs, intended use and link status | [Engineering Sources](DocLens_AI_Engineering_Sources.md#CATALOG) | Catalog and architecture legacy IDs |
| Temporary GPU operations, staging, CUDA/resources/artifacts | [GPU Playbook](DocLens_AI_Kaggle_GPU_Playbook.md) (P-GPU) | [GPU-MODE](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-MODE), [GPU-A](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-A), [GPU-B](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-B), [GPU-GATE](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-GATE) |
| Implemented capabilities, setup, commands and operator workflows | [README](README.md) | Existing API, worker, model setup and evaluation headings |
| Task execution and focused verification | [Project skills](.agents/skills) | Select below; no policy ownership transfer |

## Priority, conflicts and historical evidence

Follow platform instructions, current user scope and applicable AGENTS.md files.
The owner table assigns requirements; code/configuration/tests (P-REPO) establish
actual implementation, with executed evidence required for behavioral claims.
If a target is not implemented, report the gap rather than describing it as delivered.
For conflicting requirements, identify statements and owner; preserve critical
contracts and report unresolved conflicts before changing them. No silent relaxation.

The unchanged DOCX is the sole architecture representation, originally dated
15 October with a 17 October 2026 snapshot at `9b39846`. Its detailed extraction,
ML, GPU and acceptance discussions remain historical context; the topic owners
above are the maintained editorial definitions. Architecture boundaries remain
binding. This routing resolves overlapping ownership without deleting DOCX text or
introducing a competing architecture. Original numbered sections remain available
to skills; no historical result or contractual edge case is waived by a reference.

QG-00…QG-09 now follow the explicit reconstruction brief. Their complete historical
originals and historical numerical thresholds remain UNAVAILABLE. New numerical
thresholds are TBD pending approval before release use. This limitation does not
block authoring/consolidation; no historical QG reconciliation, gate PASS or
production readiness is claimed. See the quality policy for current gate decisions.

Use AGENTS.md's IMPLEMENTED / OFFLINE BASELINE / TARGET / CANDIDATE / REJECTED /
NOT_EVALUATED vocabulary. Keep task PASS/FIX/BLOCKED, gate PASS/FAIL/NOT_EVALUATED,
experimental PROMOTE/REJECT/INCONCLUSIVE and production authorization separate.
Old tests and reports are evidence only for their recorded scope, not current-HEAD
verification. Select relevant primary reports rather than loading all experiment history.

## Skill selection

| Task | Focused procedure |
| --- | --- |
| Schema compatibility/migrations | [doclens-db-migration](.agents/skills/doclens-db-migration/SKILL.md) |
| Upload through indexing/jobs/delete/reindex | [doclens-ingestion-change](.agents/skills/doclens-ingestion-change/SKILL.md) |
| Frozen parser fidelity and regressions | [doclens-extraction-benchmark](.agents/skills/doclens-extraction-benchmark/SKILL.md) |
| Retrieval/context/grounded answers/refusal | [doclens-rag-evaluation](.agents/skills/doclens-rag-evaluation/SKILL.md) |
| Provenance/review/coverage/leakage | [doclens-data-quality](.agents/skills/doclens-data-quality/SKILL.md) |
| Shared comparison protocol and decisions | [doclens-ml-experiment](.agents/skills/doclens-ml-experiment/SKILL.md) |
| Authorized temporary Kaggle operations | [doclens-kaggle-gpu](.agents/skills/doclens-kaggle-gpu/SKILL.md) |
| Real-service operational/release qualification | [doclens-production-readiness](.agents/skills/doclens-production-readiness/SKILL.md) |

## Reconciliation notes and future review

- DOCX §7's heading support is qualified by §8: complete DOCX heading/section and
  ancillary representation is a target, as clarified by EX-DOCX. Its locator examples
  are not a guarantee of every populated runtime field.
- DOCX §9 uses illustrative payload names; exact wire fields remain in current
  indexing code/README. Its single ACTIVE authority and complete cutover contracts
  remain binding. §17's general request-ID statement is target beyond Answers;
  README records no general Search request-ID contract.
- DOCX statements that OCR is unevaluated and ML-11 has not run belong to its
  17 October snapshot. Later candidates are not automatically production changes;
  [ML-21](docs/eda/docx_footnote_candidate_v1.md) records offline execution PASS,
  advancement INCONCLUSIVE and no production authorization.
- Existing stage skills still point at DOCX evaluation sections; those remain
  readable context. Future authorized skill synchronization should route acceptance
  to Quality Policy and methods to Extraction/ML Strategy. The GPU skill's missing
  playbook wording is now stale; use the available P-GPU above. Skills were not edited.
- The existing Kaggle runner guide includes historical account/CLI commands; verify
  current identity, privacy, installed CLI and output-version linkage before reuse.
- README commands and historical evidence remain scoped. Engineering catalog links
  disclose failed/limited fetches and version drift; they are not compatibility tests.
