# Symbol and period semantic defect closure — 2026-10-26

STATUS: **PASS for the scoped engineering defects and applicable final checks.**
Quality **QG-08/09 remain FAIL pending complete independent qualification**.
No universal entailment or production readiness is claimed.

## Scope, baseline and sources

Verified main baseline: `e9252f22e47b2560edc549ff7edd862a0efb6810`. Only answer support, its focused
unit/API regressions and README contract changed. The existing trusted-question
caller, citation validation and final ALL-packed-source authorization paths remain.
No model, dependency, schema, prompt, threshold, corpus, Gold or prior report change.
No branch, merge, push, deployment, EDA, GPU/model benchmark or repeated QG audit.

Read root AGENTS/source map (no nested instructions), the RAG-evaluation skill,
[Quality Policy](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#TRUTHFUL-LLM),
[ML generation](../../DocLens_AI_ML_Quality_Strategy.md#ML-GENERATION),
[architecture trust boundary](../../Doclens_AI-architecture.md#ARCH-SECURITY) and
the independently reproduced verification report/evidence under
`evaluation-output/semantic-verification-20261024/`.

## Root causes and changes

1. `_permission` normalized the entire predicate+qualifier using a general case
   key. `mW` and `MW` became equal, and digit-free permission answers bypassed the
   separate numerical literal guard. Predicate normalization now applies only to
   the closed EN/RU/KK permission vocabulary. Qualifiers retain exact spelling,
   whitespace, Unicode symbols, SI prefix case and identifier values. Questions
   are parsed without normalizing their evidence-bearing qualifiers.
   Subjects retain case equivalence only for known grammatical/field words;
   entity, identifier and unit-role tails remain exact. Capitalization shape is
   not proof of linguistic identity (`Nm`, `Nmm`, `Mmol` may be symbols).
   Unknown Unicode regex/casefold aliases fail closed instead of causing KeyError.
2. `_question_mode` accepted a requested period because the source value ended
   with that string. A full positive scalar/permission–scope relation now binds
   the complete value, property/entity key and one literal period. The period may
   occur in the scalar value or explicit field label; competing periods or
   unparseable values cannot use a matching year as proof. No English/Russian
   exclusion-phrase blacklist is used. Failed temporal parsing cannot fall back
   to a generic condition or a separate boolean-language path. Same-property /
   entity counterparts are compared across both field/value period placement;
   recognized conflicting or unresolved temporal evidence is refused, while a
   clearly bound different period or different entity does not block the answer.
   A complex, unparseable counterpart with the same explicit field/copular
   subject also causes refusal; it is not silently ignored or used as support.

Full canonical quotes, complete answer coverage, exact numeric/sign/precision/
unit/formula literals and the pre-existing numeric elision restrictions remain
additional requirements. No conversion, value recomputation or LLM judgment is
used. All packed sources are still ACL/ACTIVE-revalidated after generation even
on invalid/refusal output, as independently exercised by integration regressions.

CHANGED:
- `src/doclens_ai/services/answer_support.py`: separated grammar and literal keys,
  positive value/period binding, shared boolean checks and counterpart handling.
- `tests/unit/test_answer_support.py`: **60 added cases**, no removals/weakened
  assertions. Covers mW/MW, Mmol/mmol, µ/μ, token spacing, typed IDs, Nm/nm,
  EN/RU/KK controls, exclusions/neighboring periods/entity mismatch, field/value
  placement, ambiguity, conflicts and clear positive scopes.
- `tests/integration/test_answer_semantics.py`: **27 added API cases**, preserving
  real DOCX intake/extraction, PostgreSQL, MinIO, Qdrant and authenticated delivery.
- `README.md`: documented supported literal/period boundaries and refusal limits.
- This report and its sanitized evidence JSON. Prior qualification reports unchanged.

## Reproduction and final verification

Saved diagnostic scripts were copied byte-for-byte into a new ignored directory
before implementation; old evidence was preserved. Before: unit **3 failed / 10
passed**, API **3 failed / 2 passed**, exit 1. Actual API outputs had real full
citations and accepted `permitted for measurements in MW`, or answered a 2026
question from `not for 2026` / `for 2025, unavailable for 2026` source data.
After: all **13 saved unit probes** and all **5 saved API probes** pass within the
final suites, including the two supported API controls. The three unsafe responses
now return `answerable=false`, `insufficient_evidence`, null answer/no citations.
The original prior negation/instruction/wrong-year probes, their two positive
controls and invented-number negative are also all green (six cases).

Self-review independently of passing tests added red runs before correcting three
temporal fallback paths, two compound-symbol identity cases, a mixed EN/RU
past→present acceptance, an ignored complex counterpart and two Unicode aliases.
EN/RU boolean field-period positives, correct compound units and the supported
present-state control were retained. No failing assertion was reversed/removed.
Intermediate full-unit/integration runs were interrupted when the compound-symbol,
complex-counterpart and Unicode findings required source changes. One earlier
complete unit run passed 2366/6 before the last counterpart/Unicode changes; it is
retained separately and NOT counted as final verification.
Only exact task-command/ancestry-verified Python processes were stopped; the
final suites were restarted against the new pinned source snapshot.

Work began on 24 October and resumed on 26 October. The final unit suite completed
on the 24th; all source/test pins were independently confirmed unchanged on resume.
An integration run crossed the pause: 113 passed / 1 failed, exit 1, 160491.322 s.
Its sole failure was fixture setup (`worker.run_once`, `worker_heartbeat_lost`),
before the semantic validator was called. The unchanged failed case passed in a
fresh isolated run, then the entire integration suite was rerun on the 26th.
No lease duration, heartbeat, assertion or worker implementation was weakened.
The paused run is retained as `integration-paused.*`, not treated as release
latency evidence or a green full-service result.

| Executed check | Result | Exit |
| --- | --- | --- |
| Saved unit reproduction before changes | 10 passed / 3 failed / 0 errors / 0 skipped; 3.337 s | 1 |
| Saved API reproduction before changes | 2 passed / 3 failed / 0 errors / 0 skipped; 29.999 s | 1 |
| Temporal fallback self-review red | 121 passed / 3 failed / 0 errors / 0 skipped; 1.915 s | 1 |
| Compound symbol self-review red | 127 passed / 2 failed / 0 errors / 0 skipped; 2.388 s | 1 |
| Mixed-language tense self-review red | 130 passed / 1 failed / 0 errors / 0 skipped; 2.404 s | 1 |
| Complex-counterpart self-review red | 132 passed / 1 failed / 0 errors / 0 skipped; 2.881 s | 1 |
| Unicode alias self-review red | 133 passed / 2 failed / 0 errors / 0 skipped; 3.845 s | 1 |
| Integration spanning pause | 113 passed / 1 failed / 0 errors / 0 skipped; 160491.322 s | 1 |
| Fresh unchanged lease-case repeat | 1 passed / 0 failed / 0 errors / 0 skipped; 7.808 s | 0 |
| Final semantic/RAG/retrieval/binder + saved unit probes | 342 passed / 0 failed / 0 errors / 0 skipped; 3.841 s | 0 |
| Final complete unit suite | 2370 passed / 0 failed / 0 errors / 6 skipped; 345.855 s | 0 |
| Final affected real-service suite + all saved API/original probes | 114 passed / 0 failed / 0 errors / 0 skipped; 665.226 s | 0 |
| Repository Ruff / changed Python format | All checks passed / 3 files formatted | 0 / 0 |
| Working/staged diff, source pins and preservation | Verified scoped files only | 0 |
| Owned service cleanup | 0 task containers/networks/volumes remain | 0 |

Counts overlap and are not summed. Unit growth: 2310 + 60 = **2370 passed**, plus
six unchanged skips: two Windows symlink privileges and four optional local
Node/Playwright/Edge UI prerequisites. Exact test names/reasons and per-file counts
are in the JSON. No test deselection, threshold change or assertion weakening.
Remote CI was not triggered; no push was authorized.

Service environment: three newly owned, uniquely labelled cached-image containers
(PostgreSQL 16-alpine, local MinIO image, Qdrant v1.15.4), tmpfs, loopback-only
ports and fresh credentials. No shared databases/objects/collections were reset.
Embeddings/generation are controlled providers, not real-model quality evidence.
Source/test/README SHA pins were checked before and after final test execution.
The 435 unrelated tracked/report paths and 49 previous verification artifacts
retain their original bytes/absence. The intentionally deleted runner stays absent.

## Limits and quality gates

The verifier remains bounded. Unknown case aliases, entity disambiguation,
arbitrary paraphrases, units/compound quantities, formulas in temporal relations,
multi-sentence reasoning, relative dates and arbitrary calendar validity are not
certified. Complete literal formulas still have the previous exact-evidence guard;
this change does not add formula interpretation. Ambiguous/undated counterparts
can conservatively refuse an otherwise plausible answer. Existing explicit full
quotation requests remain document-data retrieval, not factual endorsement.
No population false-refusal rate or universal multilingual correctness is claimed.

QG-08/09 FAIL verdicts are **not promoted**. Engineering red→green does not supply
independent Answer Gold/semantic/refusal judgments, approved quality thresholds,
qualified generator/tokenizer/window or representative real-model E2E. QG-09 also
requires separate lifecycle/delete/reindex/rebuild/reconciler, all-enabled readiness,
fault-consistent restore/Qdrant rebuild/RPO-RTO/rollback, workload/SLO/resources and
deployment/security/observability qualification. These were not rerun or invented
as completed. No production authorization is created.

## Exact commands and Git

From `C:/Users/nurs/doclens_ai`, existing venv Python, PYTHONPATH root+src,
PYTHONDONTWRITEBYTECODE=1, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1. Detailed
commands/exit codes, source/artifact hashes and JUnit counts are in adjacent JSON.

- **api-red**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\services.py C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\test_independent_api.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\api-red-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\api-red.xml --tb=short` → exit **1**.
- **counterpart-review-red**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit/test_answer_support.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\counterpart-review-red-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\counterpart-review-red.xml --tb=short` → exit **1**.
- **format**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m ruff format --check src/doclens_ai/services/answer_support.py tests/unit/test_answer_support.py tests/integration/test_answer_semantics.py` → exit **0**.
- **full-units-before-counterpart**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\full-units-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\full-units.xml --tb=short` → exit **0**.
- **full-units**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\full-units-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\full-units.xml --tb=short` → exit **0**.
- **integration-paused**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\services.py tests/integration/test_answer_semantics.py tests/integration/test_answers_api.py tests/integration/test_rag.py tests/integration/test_retrieval.py tests/integration/test_search_api.py C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\semantic_probes.py C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\test_independent_api.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\integration-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\integration.xml --tb=short` → exit **1**.
- **integration**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\services.py tests/integration/test_answer_semantics.py tests/integration/test_answers_api.py tests/integration/test_rag.py tests/integration/test_retrieval.py tests/integration/test_search_api.py C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\semantic_probes.py C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\test_independent_api.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\integration-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\integration.xml --tb=short` → exit **0**.
- **lease-repeat**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\services.py tests/integration/test_rag.py::test_generation_time_pg_changes_invalidate_whole_answer[deleted] -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\lease-repeat-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\lease-repeat.xml --tb=short` → exit **0**.
- **lint**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m ruff check src tests tools alembic` → exit **0**.
- **review-red**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit/test_answer_support.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\review-red-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\review-red.xml --tb=short` → exit **1**.
- **start**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\services.py start` → exit **0**.
- **stop**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\services.py stop` → exit **0**.
- **symbol-review-red**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit/test_answer_support.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\symbol-review-red-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\symbol-review-red.xml --tb=short` → exit **1**.
- **targeted**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit/test_answer_support.py tests/unit/test_rag.py tests/unit/test_rag_safety.py tests/unit/test_rag_quote_binding.py tests/unit/test_citation_binding_candidate.py tests/unit/test_retrieval.py C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\test_independent_probes.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\targeted-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\targeted.xml --tb=short` → exit **0**.
- **tense-review-red**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit/test_answer_support.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\tense-review-red-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\tense-review-red.xml --tb=short` → exit **1**.
- **unicode-review-red**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest tests/unit/test_answer_support.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\unicode-review-red-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\unicode-review-red.xml --tb=short` → exit **1**.
- **unit-red**: `C:\Users\nurs\doclens_ai\.venv\Scripts\python.exe -B -m pytest C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\test_independent_probes.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\unit-red-tmp --junitxml=C:\Users\nurs\doclens_ai\evaluation-output\semantic-binding-fix-20261024\unit-red.xml --tb=short` → exit **1**.

Additional preservation, staged scope/diff/secrets review and cleanup inventory
commands are in the local receipts under
`evaluation-output/semantic-binding-fix-20261024/`. Only task-owned resources were
removed. No service credentials, private RAW/Gold or corpus-derived payloads are
committed. Only public synthetic probe receipts are included in the evidence.
`python -B evaluation-output/semantic-binding-fix-20261024/preservation.py`,
`git diff --check`, `git diff --cached --check` and the local staged-review helper
each completed with exit 0. The task container/volume/network label inventory
also completed with exit 0; exact commands are retained in the cleanup receipt.

Implementation COMMIT: `10b8294007e5e9d031fc2d455f6182510b87eeea` — `fix(rag): preserve symbols and bind temporal evidence`.
The documentation commit SHA is recorded in the final Git receipt/chat rather
than embedded into its own content. No push or deployment.
GIT STATUS after both focused commits must retain the five original entries:

```text
 D tools/kaggle_gpu/extraction_remote.py
?? docs/evaluation/final_qg_qualification_20261024.md
?? docs/evaluation/final_qg_qualification_20261024_evidence.json
?? docs/evaluation/qg_qualification_20261024.md
?? docs/evaluation/qg_qualification_20261024_evidence.json
```
