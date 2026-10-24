# Semantic acceptance defect closure — 2026-10-24

STATUS: **PASS — the three engineering counterexamples are resolved within the
verified bounded support contract.** QG-08/09 qualification verdicts remain FAIL;
no production release or universal semantic correctness is claimed.

## Scope and sources

Goal: fix the three confirmed semantic acceptance defects from the final QG
qualification, on current main, preserving numeric fidelity, source provenance
and final ACL/ACTIVE revalidation. Baseline:
`fd8f927e19f4c12b051896eea9fe5c947aa806e1`. No branch, merge, push, deployment,
model benchmark, GPU workload, EDA or repeated QG audit is part of this task.

Authority: [Quality Policy](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md)
`TRUTHFUL-LLM`/`PRODUCTION-DOD`, [ML generation](../../DocLens_AI_ML_Quality_Strategy.md#ML-GENERATION),
[architecture security/API](../../Doclens_AI-architecture.md#ARCH-SECURITY), and
[final qualification](../evaluation/final_qg_qualification_20261024.md) with its
JSON evidence. Root AGENTS/source map and applicable RAG-evaluation and
production-readiness skills were read. There are no applicable nested instructions.
No project instruction or qualification verdict was edited.

READ/MODIFY: answer support and its RagService call, affected tests and README.
CREATE: focused semantic unit/API regressions, this engineering report and its
sanitized [evidence receipt](semantic_acceptance_closure_20261024_evidence.json).
Acceptance: actual original red→green, source-qualified positive/negative controls,
full units, real-service API/RAG/ACL coverage, lint/changed-file format, self-review,
then two focused Conventional Commits on main. Existing deletion and all four
untracked qualification reports must retain their original state/bytes.

## Root causes and implemented change

1. Nonnumeric support was an arbitrary substring test. `allowed` passed a real
   quote of `Export is not allowed.`; polarity, conditions and subject could be
   dropped. Support now requires a complete source-qualified fact, a complete
   predicate bound to the question's subject, or an explicit complete quotation.
   Every citation must quote its whole canonical chunk and cover the whole answer;
   multiple individually quoted fragments cannot manufacture a reversed claim.
2. Literal document instructions supplied matching text without factual support.
   No instruction phrase blacklist was added. A bounded positive grammar admits
   explicit fields/declarative relations and source-bound questions. An imperative
   fragment or an instruction containing a nested factual-looking clause cannot
   supply an unrelated password/access-code fact. An explicit quotation request
   can still return the complete instruction as untrusted document data. Neither
   model output nor document content controls the backend's question or provenance.
3. Even complete numeric source matches ignored the requested entity/period.
   RagService now passes the original validated request question directly into
   the existing support validator. Matching binds the complete subject and scope,
   including literal year/quarter/month qualifiers. Explicit past/present copulas
   must agree; a proposed paraphrase cannot change the source tense. Digit-bearing
   and explicitly labelled identifiers retain case. Undated fields/headlines do
   not establish an unspecified past state. Unknown support is refused.

The implementation is in `services/answer_support.py`, with one caller change in
`services/rag.py`. It uses a private typed fact representation and deterministic
rules; no dependencies, model calls, uncalibrated entailment score or new
configuration/service was introduced. Narrow EN/RU/KK permission equivalences
preserve the complete qualifier (for example, `not allowed` ↔ `prohibited`);
source and requested subject/scope still bind. Recognized conflicting relevant
facts, or an unresolved permission counterpart for the same subject, are refused.

The prior numeric guard remains an additional requirement: exact source values,
signs, precision, units, formulas and periods; only the existing recognized bare
numeric labels may be elided. A permission paraphrase cannot bypass numeric
fidelity. Existing citation identity/version/offset validation runs first.
ALL packed sources are still revalidated after inference, including semantic
rejection/refusal; authorization failure and source invalidation retain precedence.
Public schema/refusal reason remains unchanged (`insufficient_evidence`).

## Coverage, compatibility and conservative limits

New unit coverage: 71 source/question/claim vectors, three relevant-counterpart
cases and one cropped-quote case = **75 cases**. These include alternate entities,
conditions, instruction forms, year/quarter/month changes, tense, case-sensitive
identifiers, EN/RU/KK permission positives/negatives, legitimate controlled
paraphrases, explicit full quotations and exact numeric controls.

New authenticated API coverage: 29 claim cases plus two final-authorization cases
(revoked membership and deletion of an UNcited packed canonical chunk). Sources
go through actual DOCX intake/native extraction, canonical storage, PostgreSQL
membership/ACTIVE authority, MinIO and Qdrant. Embeddings and adversarial generation
are controlled test doubles; these are engineering oracles, not Human Gold or
real-model error-rate measurements. Response/citation locators and sanitized logs
are asserted. Existing API/RAG/retrieval/search/upload tests remain enabled.

Legacy successful integration fixtures used meaningless `Controlled question?` /
`Fixture question?` prompts while copying a source verbatim. Their positive prompts
now explicitly ask what the evidence says; numeric fixtures ask for their actual
mass/period. All response, invalid-output, concurrency, membership/cutover and
source-isolation assertions are retained. No test was removed or deselected.

This is a bounded support contract, not universal natural-language entailment.
It deliberately refuses unrecognized questions, implicit coreference, arbitrary
paraphrases, multi-sentence/multiline fact reasoning, partial source quotes and
ambiguous multi-source composition. Full quotations remain available on explicit
quotation requests; literal scalar/whole-fact answers and controlled permission
paraphrases remain supported. Grammar fixtures do not establish RU/KK population
quality, authoritative review of source assertions, exhaustive contradiction
detection or arbitrary entity disambiguation. Such coverage needs separate
independent qualification; there is no automatic fallback to trusting the LLM.

## Reproduction, verification and self-review

Commands run from `C:/Users/nurs/doclens_ai` using
`C:/Users/nurs/doclens_ai/.venv/Scripts/python.exe` (PY below), PYTHONPATH repository
root + src, PYTHONDONTWRITEBYTECODE=1. Full units also set HF_HUB_OFFLINE=1 and
TRANSFORMERS_OFFLINE=1. Ignored logs/JUnit/scripts:
`evaluation-output/semantic-closure-20261024/`. Exact commands, exit codes,
per-file results, source/artifact hashes and skips are in the evidence JSON.

The original diagnostic script was copied byte-for-byte before implementation.
Before changes, its unchanged authenticated probes returned **3 failed / 3 passed,
exit 1, 34.82 s**. All three unsafe claims were accepted with real citations;
the two legitimate controls and invented-number refusal already passed.
After the initial implementation, unchanged probes returned **6 passed, exit 0,
26.96 s**. The final integration run includes these same six probes again.

| Check | Result | Exit |
| --- | --- | --- |
| Initial focused unit run | 2 false-refusal failures / 134 passed; corrected controlled predicate parsing | 1 |
| Second focused unit run | 139 passed | 0 |
| Initial affected real-service run | 68 passed / 0 skipped, 337.31 s | 0 |
| Self-review regression run | 5 failed / 57 passed: tense erasure and identifier case conflation reproduced | 1 |
| Focused units before final untimed-field guard | 259 passed / 0 skipped, 2.81 s | 0 |
| Full units before final untimed-field guard | 2300 passed / 6 skipped, 281.60 s | 0 |
| Broad affected services before final untimed-field guard | 81 passed / 0 skipped, 442.86 s | 0 |
| Untimed-field/headline review regression | 3 failed / 68 passed; missing past support reproduced | 1 |
| Focused units after untimed-field guard | 265 passed / 0 skipped, 3.28 s | 0 |
| Full units after untimed-field guard | 2306 passed / 6 skipped, 280.55 s | 0 |
| Period-type review regression | 2 failed / 73 passed; non-temporal qualifier used as past support | 1 |
| Final focused semantic/RAG/retrieval/binder units | 269 passed / 0 skipped, 3.29 s | 0 |
| Final full unit suite | 2310 passed / 6 skipped, 277.66 s | 0 |
| Final semantic/API/RAG services, including original probes | 61 passed / 0 skipped, 323.12 s | 0 |
| Repository Ruff | All checks passed | 0 |
| Changed Python files format | 6 files already formatted | 0 |
| Working/staged diff, scope, source/report preservation | Exact seven-file scope, code pins and all five pre-existing paths verified | 0 |
| Task fixture stop / cleanup inventory | Six owned containers removed; zero task containers/networks/volumes; 11 unrelated containers present | 0 / 0 |

Counts overlap and are not summed. Unit growth is exactly 2235 + 75 = 2310 passed.
Six existing skips remain: Windows symlink privilege in test_data_quality_gate and
test_readiness_release, plus optional Node/Playwright/Edge paths in
test_pdf_assisted_review, test_pdf_grid_proposals, test_pdf_proposal_review and
test_pdf_review_visual. No assertion, budget or configured CI check was weakened.
The unrelated pre-existing whole-repository format debt is not changed; all six
affected Python files pass the formatter. Remote CI was not triggered without a push.

Self-review independently traced the staged control flow and all affected
provenance/authorization paths. Two initial supported permission paraphrases were
falsely refused because the predicate parser treated `not` as a subject; checking
the complete controlled predicate before a full-clause paraphrase corrected them.
Further review reproduced past→present substitution and case conflation in an
explicit identifier before correcting them and adding positive/negative tests.
An additional red run exposed past-state claims drawn from untimed fields/headlines;
the final guard refuses them without discarding their supported present-state
answers. Explicit matching period-qualified requests remain supported.
Two additional negatives separated temporal periods from entity/condition
qualifiers such as `for adults`. Past field queries now require a matching literal
year, quarter, English month/year or ISO-like period form; arbitrary qualifiers
and relative dates cannot supply a missing temporal assertion. This finite
recognizer does not establish arbitrary calendar semantics or multilingual quality.
Production and unit-test code stayed unchanged throughout the final full-unit
run. The final service run uses the final API-test snapshot as well.

A one-off diagnostic was blocked while initializing Windows asyncio inside the
sandbox. Only its two exact PID/unique-command-line-verified processes were stopped;
the bounded probe was rerun successfully with loopback access. This is an
environment limitation, not an auto-review rejection. Test suites used authorized
Windows loopback/Docker access. All service fixtures are disposable, task-labelled,
loopback-only with read-only source mounts; no shared database/object/collection
is reset and no image/model/dependency download occurred.

## QG-09 assessed separately

The final qualification's QG-09 FAIL had unsafe authenticated delivery plus separate
unqualified operational requirements. Its source evidence records successful
collection, migrations/startup and bounded integration checks; manual pg_dump /
restore and a RAW checksum roundtrip explicitly do not establish coordinated
application restart, Qdrant rebuild, consistent fault recovery, RPO/RTO or rollback.
No independent executed recovery failure is invented from missing evidence.

This fix addresses the demonstrated unsafe delivery paths only. Complete
delete/tombstone/reindex/rebuild/reconciler lifecycle, all-enabled dependency
readiness (currently DB-only), real-generator E2E/independent semantics, approved
SLO/load/resources, deployment/observability and recovery/rollback qualification
remain separate requirements. Their implementation or qualification is outside
this task. QG-08/09 verdicts in the preserved qualification remain **FAIL**;
independent Gold/TEST, thresholds and production authorization are not supplied
by passing engineering tests. No completed audit/EDA/model campaign was repeated.

## Git and completion

CHANGED: seven implementation/test/README paths and two new engineering report/
evidence files; no instruction, migration or prior qualification report changed.
DESIGN: conservative source-qualified support using the existing provenance and
final authorization boundaries, without model/dependency changes. VERIFIED: the
commands/results above and adjacent JSON. REMAINING: bounded grammar/false-refusal
limits and the independent QG/operational requirements described above.

COMMIT: `3ea1ca0359e929b924496838b318313c963c629d`
`fix(rag): bind supported facts to question scope`. The separate documentation
commit's SHA is recorded in the final chat/Git log rather than embedded into its
own content. No merge, push or deploy.
Original deletion and all four qualification reports retain their initial hashes.
GIT STATUS: final unchanged pre-existing status, verified after both focused
commits in the local final receipt:

```text
 D tools/kaggle_gpu/extraction_remote.py
?? docs/evaluation/final_qg_qualification_20261024.md
?? docs/evaluation/final_qg_qualification_20261024_evidence.json
?? docs/evaluation/qg_qualification_20261024.md
?? docs/evaluation/qg_qualification_20261024_evidence.json
```
