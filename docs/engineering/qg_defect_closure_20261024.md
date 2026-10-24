# QG counterexample fixes — 24 October 2026

STATUS: **PASS for the three scoped engineering fixes**. All original
counterexamples are resolved by executed regressions. Whole-repository formatting
is not green: the 27 verified pre-existing differences below remain unchanged.

Scope: fix only F-01/F-02/F-03 from [qualification](../evaluation/qg_qualification_20261024.md).
Baseline branch `codex/audit-closure-20261024`, HEAD
`cb95127b57df54cf31aa8d19a93c89591c2381c7`. The pre-existing deletion
`tools/kaggle_gpu/extraction_remote.py` and both untracked qualification documents
are preserved byte-for-byte/absent as applicable and excluded from these commits.
No migration, model, dependency, dataset, Gold, threshold or sealed TEST changes.

Owners: [Quality Policy](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md)
QG-07/08/09 and truthful/refusal contract;
[ML Strategy](../../DocLens_AI_ML_Quality_Strategy.md) context/generation;
[Architecture](../../Doclens_AI-architecture.md) authorization/current-source checks.
The repository RAG skill guided the scoped procedure. This is engineering defect
closure, not a repeat qualification, model comparison or release authorization.

## Reproduction before implementation

- `pytest tests/unit/test_extraction_kaggle.py --collect-only -q -p no:cacheprovider`:
  exit **2**, `ModuleNotFoundError` importing the user-deleted module.
- New `test_rag_safety.py` before implementation: exit **1**, **10 failed/3 passed**.
  The original complete atomic 4405-character IR group lost the numeric/unit/
  formula/period suffix under default 4000-character packing. Unsupported numeric
  claims, altered signs/units/periods/precision and cropped facts were accepted.
- New authenticated API regression before implementation: exit **1**, **1 failed**.
  With real disposable PostgreSQL/S3/Qdrant and a test-double generator, `999 kg`
  reached HTTP 200/answerable with an exact authentic citation despite absence of
  that value in source evidence. The expected refusal assertion failed.

Raw red/green JUnit, logs, baseline/preservation receipts and disposable-service
orchestration are ignored under `evaluation-output/qg-fixes-20261024/`.
No old qualification artifact was rewritten to reproduce these defects.

## Implementation and review decisions

**F-01, context.** `services/rag.py::pack_context` now includes a whole canonical
chunk or excludes it, retaining an internal chunk ID/reason. Chunk, serialized
context, count and measured-token limits cannot cut a prefix. Later smaller
chunks can still fit. Empty packing due to budgets propagates existing
`insufficient_evidence`, without generator inference, and retains the ACL recheck.
Truly empty retrieval keeps `no_relevant_context`.

Optional `RAG_CONTEXT_WINDOW_TOKENS` requires a trusted counter through
`build_rag_runtime`/`RagService`; it must count complete serialized model chat
messages, template and special tokens. The full output-token reserve is included.
Missing/invalid/failing counters fail closed. Default character limits remain
character limits: no tokenizer, bytes/token estimate or remote API is invented.
The HTTP adapter does not automatically discover a tokenizer. Actual tokenizer/
model-window qualification is separate; no real-model experiment was rerun.

Regressions cover a fitting complete atomic group, oversized exclusion, small
serialized budgets, skip-then-fit, deterministic dedupe/injection separation,
exact token-budget boundary/output reserve, missing/invalid counter, builder
forwarding, no inference on exclusion and reauthorization. The offline binder's
hidden-suffix negative remains explicit using a frozen-style prefix context;
the current packer is no longer expected to create that unsafe prefix.

**F-02, claims.** New `services/answer_support.py` is called after unchanged strict
schema/citation validation and before the existing final PostgreSQL revalidation.
Answer spans must be literal quoted text, preventing an unsupported quantity
from bypassing the guard merely by using words. Number-bearing source/answer
claims require a complete literal fact from the whole authorized packed chunk,
not a model-selected cropped quote. Signs, precision, decimal separators,
Unicode numerals, units, formulas and periods are not normalized or recomputed.
Only an explicit small vocabulary of bare value labels can be omitted; unknown
labels, units in labels and ambiguous partial/multi-source numeric composition
require the complete source fact or produce `insufficient_evidence`.

Supported scalar/extractive facts are preserved. This deliberately conservative
guard can refuse correct paraphrases/compositions that it cannot verify. It is
not a semantic entailment model, a relevance judge, conflict resolver or proof of
global unanswerability. Exact extraction still does not establish semantic truth;
independent Answer Gold/threshold/operational qualification remains necessary.
The offline quote binder is not connected or promoted. Default RAG enablement and
final revalidation of **all** packed evidence, including uncited evidence and
invalid/refusal outcomes, remain intact.

Unit cases cover the original `999 kg`, correct `7` and complete signed quantity,
sign loss/flip, unit/period change, leading zeros, decimal precision, Unicode
digits/minus, exponent sign, units in labels, missing period header, deliberately
cropped exact quote, unsupported number words and a supported nonnumeric answer.
Real API regressions cover the original unsafe claim, a correct signed quantity,
and incorrect sign/unit/period; existing tenant/revocation/cutover negatives remain.

**F-03, collection.** `test_extraction_kaggle.py` no longer imports a retired
runner. Meaningful coverage moves to maintained contracts: deterministic readable
native PDF fixtures, explicit staging/no adjacent secrets, checksum/run binding,
size and same-size hash mismatches before publishing weights, and mocked CUDA
preflight initialization-before-statistics/CPU rejection. There is no GPU run or
download in these tests. The staging CLI also no longer silently selects the
deleted file: it requires an explicit reviewed `--source`, covered by a CLI test
and documented in the existing campaign guide. The deleted file is not restored
or committed as a new deletion by this task.

Separate staged review inspected source, tests and docs against the initial HEAD:
complete-chunk boundaries, full-prompt token reservation, conservative claim
support, unchanged citation schema/ACL checks, refusal paths, maintained retired
runner coverage, secret/artifact scope and unrelated work preservation. No
independent human/model-quality review is claimed. Findings during development
were fixed: obsolete prefix-producing expectations, explicit historical binder
context, one missing test import, and platform-dependent telemetry in a synthetic
preflight test (now mocked). Final staged diff is whitespace-clean.

## Exact verification commands

Changed paths:

- Runtime: `src/doclens_ai/services/rag.py`, `services/answer_support.py`,
  `core/rag_config.py`, `rag_runtime.py` (the latter three relative to
  `src/doclens_ai/`); operator guidance in `README.md`.
- RAG regressions: `tests/unit/test_rag.py`, `test_rag_safety.py`,
  `test_rag_quote_binding.py` (same unit directory), and
  `tests/integration/test_answers_api.py`, `test_search_api.py` (same integration directory).
- Retired-runner contract: `tests/unit/test_extraction_kaggle.py`,
  `tools/kaggle_gpu/extraction_stage.py`, `tools/kaggle_gpu/extraction_campaign.md`.
- Verification record: `docs/engineering/qg_defect_closure_20261024.md`.

`PY` below abbreviates `.venv/Scripts/python.exe`, from repository root.
Environment: `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONPATH=C:\Users\nurs\doclens_ai;C:\Users\nurs\doclens_ai\src`.
Full unit runs also use `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`.
Windows asyncio loopback and Docker access required the authorized execution
environment; there were no approval rejections. No dependency/model/image download.

```powershell
PY -m pytest tests/unit/test_rag.py tests/unit/test_rag_safety.py tests/unit/test_extraction_kaggle.py tests/unit/test_extraction_campaign.py tests/unit/test_rag_quote_binding.py tests/unit/test_citation_binding_candidate.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg-fixes-20261024/targeted-verified --junitxml=evaluation-output/qg-fixes-20261024/targeted-verified.xml --tb=short
PY -m pytest tests/unit --collect-only -q --strict-config --strict-markers -p no:cacheprovider
PY -m pytest tests/unit -q --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg-fixes-20261024/unit-final --junitxml=evaluation-output/qg-fixes-20261024/unit-final.xml --tb=short
PY evaluation-output/qg-fixes-20261024/services.py tests/integration/test_answers_api.py tests/integration/test_rag.py tests/integration/test_retrieval.py tests/integration/test_search_api.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg-fixes-20261024/services-final --junitxml=evaluation-output/qg-fixes-20261024/services-final.xml --tb=short
PY evaluation-output/qg-fixes-20261024/services.py tests/integration/test_answers_api.py tests/integration/test_rag.py -q --strict-config --strict-markers -p no:cacheprovider --basetemp=evaluation-output/qg-fixes-20261024/rag-final --junitxml=evaluation-output/qg-fixes-20261024/rag-final.xml --tb=short
PY -m ruff check src tests tools alembic
PY -m ruff format --check src tests tools alembic
PY -m ruff format --check src/doclens_ai/services/rag.py src/doclens_ai/services/answer_support.py src/doclens_ai/core/rag_config.py src/doclens_ai/rag_runtime.py tests/unit/test_rag_safety.py tests/unit/test_rag.py tests/unit/test_rag_quote_binding.py tests/unit/test_extraction_kaggle.py tests/integration/test_answers_api.py tests/integration/test_search_api.py tools/kaggle_gpu/extraction_stage.py
git diff --check
git diff --cached --check
```

Final results:

| Check | Actual result | Exit |
| --- | --- | --- |
| Final targeted regressions | **205 passed**, 0 skipped, 10.14 s | 0 |
| Complete final unit collection | **2241 collected**, no errors/deselection | 0 |
| Complete final unit execution | **2235 passed, 6 skipped**, 311.07 s | 0 |
| Broader real-service run before final review refinement | **45 passed**, 0 skipped, 345.19 s | 0 |
| Final affected API/RAG rerun after claim/builder refinement | **24 passed**, 0 skipped, 180.14 s | 0 |
| Repository Ruff lint | All checks passed | 0 |
| Formatting of all 11 affected Python files | Already formatted | 0 |
| Working/staged whitespace checks | No findings | 0 |

The service counts overlap and must not be added. A preceding full unit run had
2230 passed/6 skipped before five final safety cases and support/builder refinement;
it is superseded by the final 2241-outcome run. Both full runs are preserved.
The six final skips are two Windows symlink-privilege tests and four optional
Node/Playwright/Edge browser paths without their required local inputs. No tests
were silently deselected, removed to obtain green results, or credited as passed.
Remote CI was not triggered because no push was authorized/performed.

Repository-wide formatter: **exit 1**, **27 pre-existing files** would reformat.
Every reported path was independently checked from initial HEAD using
`git show HEAD:<path>` piped to `ruff format --check --stdin-filename <path> -`:
all 27 already fail and none is modified by this task. Receipt:
`evaluation-output/qg-fixes-20261024/format-baseline.json`.
All 11 affected Python files pass formatting; repository lint passes. Unrelated
formatting is deliberately left unchanged, not reported as a green whole-repo check.

Service checks use a separate labelled `doclens-qg-fixes-20261024` Compose project,
cached images/current RO source, loopback-only ports, throwaway credentials and
tmpfs state. Fixtures create/drop only their UUID databases, objects and Qdrant
collections. Embeddings/generation are synthetic test doubles; services are real.
No private corpus, human Gold or real-model inference is involved.
Cleanup: all **six exact-ID/label task containers** and their empty private network
were removed; task networks/volumes remaining **0/0**, independently inspected.
No shared or customer resources were used or removed.

## Completion

All three original counterexamples: **RESOLVED**. Oversized atomic context is
excluded explicitly or included whole when the budget allows; the authenticated
unsupported `999 kg` claim is refused while the correct signed quantity is
preserved; complete unit collection succeeds without restoring the deleted runner.
No QG-07/08/09 PASS promotion, independent Gold approval, threshold approval,
sealed TEST acceptance, merge, push or deployment is made. The earlier
qualification remains a frozen assessment of its previous dirty-tree state.

Implementation commits:

- `509ba2afc0abe77aaf7e1ea79bc31d976d1e81f5`
  `fix(rag): preserve atomic context and reject unsupported claims`.
- `e11441fafdb5b756e7f1bd7ea3a04f1537f68f0b`
  `fix(extraction): replace retired runner test dependencies`.

A separate Conventional Commit records this verification report; its SHA is
reported in the final response rather than embedded into its own content.

REMAINING: conservative extractive acceptance can refuse semantically correct
paraphrases; trusted model-specific tokenizer integration/measurement, independent
Gold/thresholds and broader operational qualification are separate. The 27 existing
format differences remain out of scope. No additional task begins automatically.

Final worktree after these commits retains only the pre-existing paths:

```text
 D tools/kaggle_gpu/extraction_remote.py
?? docs/evaluation/qg_qualification_20261024.md
?? docs/evaluation/qg_qualification_20261024_evidence.json
```
