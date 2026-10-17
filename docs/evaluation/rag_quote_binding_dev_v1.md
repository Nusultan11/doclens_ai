# ML-8 offline deterministic quote-offset binding

## Decision and hypothesis

The hypothesis was limited to structural binding: some schema-valid frozen
Qwen3-4B DEV outputs might pass unchanged citation validation after recomputing
only their four offsets from exact, unambiguous packed text. This experiment
does not establish semantic truth, authorize production release or change the
production decision. The previous Qwen3-4B production decision remains REJECT.

Observed structural binding increased from 0/15 originally strictly valid outputs
to **3/15 structurally bound answers**, or **3/6 schema-eligible outputs**.
**12/15 remain rejected.** Every returned result has
`production_authorized=False` and `semantic_support=NOT_EVALUATED`. The production
pipeline is unchanged and releases zero additional answers.

## Candidate contract

`src/doclens_ai/services/rag_quote_binding.py` provides
`bind_quote_offsets(ModelAnswer, EvidenceContext) -> StructuralBindingResult`.
It accepts an already schema-valid ModelAnswer and an original authorized
EvidenceContext. Even unchecked Pydantic instances are revalidated first;
missing fields, invalid ranges and contradictory refusals are never repaired.
Input dictionaries are not treated as already validated model outputs.

For every proposed citation, the binder:

1. Checks unique context identities, alignment of evidence/text/message records,
   authoritative metadata and the packed-text prefix of the original chunk.
2. Verifies the proposed chunk and document-version identities without replacing
   a mismatched identity or borrowing another chunk's text.
3. Requires the unchanged nonblank quote to occur exactly once in its selected
   packed chunk, counting overlapping occurrences.
4. Requires the entire unchanged answer to occur exactly once inside that quote.
   Paraphrases, partial answers and overlapping/repeated occurrences are rejected.
5. Recomputes `quote_start`/`quote_end` from packed text and
   `answer_start=0`/`answer_end=len(answer)` from the complete exact answer.
   Indices are Unicode code points with exclusive ends, not UTF-8 bytes.
6. Revalidates the ModelAnswer and calls unchanged `validate_citations`. Returned
   Citation metadata comes from the authoritative context, including source
   locators. All proposed citations are retained or the entire binding fails.

Multiple chunks are allowed only when **each** proposed quote contains the full
answer. Complementary fragments are not stitched together. Duplicate chunk
references remain prohibited by the existing validator. Matching uses only the
visible packed prefix; it never falls back to a hidden original suffix. No case,
whitespace, Unicode normalization, quote replacement, citation dropping, schema
coercion or answer rewriting occurs. Strict valid refusals are copied unchanged;
invalid refusals are rejected before any binding.

This is a standalone offline module. RagService.answer, public APIs, LocalGenerator,
RagSettings and production validators are unchanged. There is no production feature flag,
model loading, inference, retrieval, upload or dependency addition. The component
does not establish fresh authorization; its caller must supply the original
authorized context. Its result is neither RagOutcome nor AnswerResponse and
contains no production-release grant.

## Frozen DEV replay

Only the existing private ML-7 packet was read:
`evaluation-output/rag-model-compare-dev-v1/human-output-review.json`.
Its SHA-256 is
`2392acbf710bb336670aff2f83131424451536009c61e394ae7ef8078f13da93`.
Exactly 15 unique DEV cases were replayed: 12 positive and three negative.
No TEST questions, retrieval reruns, new generation or tuning were used.

The packet embeds the original HTTP envelopes, requests, packed evidence and Gold
references. MockTransport replays them through the frozen runner's unchanged
LocalGenerator/strict_json/ModelAnswer/validate_citations path. Packet, raw-content,
output and configuration bindings are checked. Only the six already schema-valid
outputs reach the candidate; all nine schema-invalid outputs are skipped without
repair. Existing files and the packet bytes remain unchanged.

| Measure | Original strict replay | Offline structural candidate |
|---|---:|---:|
| Schema-eligible outputs | 6/15 | 6/15 |
| Strictly valid original outputs / structurally bound answers | 0/15 | 3/15 |
| Still rejected | 15/15 | 12/15 |
| Valid negative refusals | 0/3 | 0/3 |
| Structural validity of returned citations | 0 citations | 3/3 citations |
| Correct bound positive raw facts, according to prior AI diagnostics | No valid outputs | 3/3 bound answers |
| Incorrect/unsafe bound answers, according to the same prior diagnostics | No valid outputs | 0/3 bound answers |
| Production release authorization | 0/15 | 0/15 |
| Delivered production required-evidence coverage | 0/19 | 0/19 |

Remaining rejection categories are **9 schema failures**, **2 missing complete
exact answers inside the proposed quote**, and **1 missing exact quote in the
selected packed chunk**. The three bound answers preserve all original answer,
quote, ID and reason fields; only citation offsets change. No negative case is
repaired into a refusal or answer. All returned citations pass the original
validator, but these are structural diagnostics, not delivered production answers.

The prior independent AI-assisted ML-7 assessment classified 12/12 raw positive
facts as correct and two negative responses as incorrect/unsupported, with one
contract-invalid semantic abstention. That assessment was supplied in the
preceding finalization request and recorded in the ML-7 freeze at commit
`7ea1fc178c1ff4053085d598cf7eed5c45c35263`; it was not independently re-annotated
here. Its source-review SHA-256, previously verified, is
`9053d7c8c7d5c755c18816e548c466baf39ee5270b322e668f212b1af35bba56`.
An explicit private evaluation-only copy of those prior verdicts is bound to the
same packet. Gold is used only for DEV diagnostics and denominators, never
evidence selection, offset binding or answer construction. The binder has no Gold
argument. Human-reviewed correctness remains **NOT_EVALUATED**, and these
AI-assisted assessments are **not operator-confirmed**.

Canonical required-anchor coverage for the structurally bound citations is
**NOT_EVALUATED_SOURCE_IDENTITY_UNAVAILABLE**: this packed export omits the
authoritative document-source SHA mapping used by the canonical evaluator.
Workspace/source-SHA placeholders in the replay adapter are explicitly unused by
citation validation; they do not manufacture source identity or authorization.
We do not infer those identities from Gold, quote matching or locators. The
reported 0/19 delivered coverage is exact because no result is production-released;
it must not be mistaken for measured candidate anchor coverage.

The first observed six eligible local binding/evaluation attempts had P50
0.383 ms and P95 2.504 ms (linear interpolation). This includes replay-harness
post-binding validation/assertions, excludes schema skips, and is not an isolated
function benchmark or generation latency. First-observation timings are kept
privately and never overwritten on repeat replay. Six observations are insufficient
for performance guarantees. No new model latency, VRAM or RAM benchmark was run.

## Semantic safety boundary

The earlier simplified extractive binder accepted 11 unsafe synthetic answers.
This candidate does **not** solve semantic support with lexical matching. The
safety boundary is explicit: it returns only a structural diagnostic result and
never authorizes release, even after production citation validation passes.

Current synthetic tests deliberately bind unsafe examples involving conflicting
source assertions, negation, wrong entity and prompt injection. Their quotes and
answer substrings are exact and unambiguous; their answers still do not follow
from the question/evidence. All four examples are structurally bindable, all have
semantic support NOT_EVALUATED, and none is production-authorized. This demonstrates
the limitation rather than treating those examples as successful safe answers.
No prompt-injection text is executed or used as an instruction.

The DEV observation of 0/3 previously assessed unsafe bound answers is a tiny,
English-only diagnostic subset, not a demonstrated zero unsafe-answer rate.
The six eligible cases exclude nine schema failures, including all negatives;
this cannot establish refusal safety or generalization. Literal substring
membership, valid quote offsets and complete lexical answer coverage do not
establish entailment, correct entity, current version, lack of contradiction or
semantic faithfulness. A general semantic safety decision cannot be established
by this deterministic binder.

Before any future integration, independent output review and a separate evaluated
semantic/support decision would be required, including negative, wrong-entity,
negation, conflict, version and injection regressions. Source-identity mappings
would be needed for canonical anchor coverage. The unchanged fail-closed response
validators, server-side isolation and live authorization revalidation must remain
in force. A binding result alone must never become a release gate. No such
integration, semantic guard, prompt change or next major step is implemented here.

## Artifacts and verification

Private ignored outputs are restricted to
`evaluation-output/rag-quote-binding-dev-v1/`:

- `metrics.json`: aggregate structural/strict results and explicit limitations.
- `binding-review.json`: original-output fingerprints, bound outputs and failures.
- `prior-diagnostic-assessment.json`: prior AI judgments and provenance, evaluation only.
- `timing.json`: first local timing observations.
- `preserved-input.json`: original packet identity.

No private case questions, answers, evidence, document text or Gold labels belong
in tracked files. This step creates only the standalone module, its unit and
integration tests, and this report. Finalization authorizes one commit containing
only those four files; production integration remains unauthorized.

Implementation verification (repeated during finalization below):

- `.venv\Scripts\python -m pytest -q tests/unit/test_rag_quote_binding.py`:
  **46 passed**. Cases cover exact strings/metadata, Unicode, repeated and
  overlapping matches, wrong identities, missing/invalid schema fields,
  contradictory/empty refusals, truncation, multi-chunk coverage and the four
  deliberately unsafe structural counterexamples.
- `$env:DOCLENS_RAG_QUOTE_BINDING_REPLAY='1'; .venv\Scripts\python -m pytest -q -s tests/integration/test_rag_quote_binding.py`:
  **1 passed**, actual packet replay. Repeat runs reproduce the exact preserved
  metrics and bound-output audit without overwriting the first timing observation.
- `.venv\Scripts\python -m pytest -q tests/unit`: **676 passed, 1 skipped**.
  The existing Windows symlink-privilege test cannot run in this environment.
- `.venv\Scripts\ruff check .`: passed.
- `.venv\Scripts\ruff format --check src/doclens_ai/services/rag_quote_binding.py tests/unit/test_rag_quote_binding.py tests/integration/test_rag_quote_binding.py`:
  passed; all three files already formatted.
- `.venv\Scripts\python evaluation-output/rag-quote-binding-dev-v1/audit.py`:
  original packet SHA unchanged, exactly four allowed new files, no changes to
  existing tracked code, private case/Gold/document/output text absent from public
  files, recognizable credential formats absent and private output Git-ignored.
- `git diff --check` and `git status --short`: checked. New-file whitespace is
  also explicitly checked by the audit because the four files remain untracked.
  At implementation completion, nothing was staged or committed.

Two new unchecked-extra-field regression cases initially failed: Pydantic
`model_dump()` hid extra attributes inserted by unchecked `model_copy()`. The
candidate now revalidates original raw fields, including nested citation objects,
so forbidden fields are rejected rather than silently discarded. The targeted
tests, actual replay and full suite passed after that correction. This fix is
confined to the new candidate; production ModelAnswer and validators are unchanged.

**PASS for the offline structural experiment only.** No semantic-safety or
production acceptance PASS is claimed. Remaining schema/literal failures,
unavailable candidate anchor coverage, small English-only sample and semantic
counterexamples remain explicit limitations. Finalization freezes the four files
in one commit; no next major step is run.

## Finalization verification

The focused tests (46 passed), frozen actual-capture replay (1 passed), full unit
suite (676 passed, 1 skipped), Ruff lint and three-file format checks were repeated
successfully using the commands above. No implementation regression was found;
the module and tests were preserved unchanged.

A read-only privacy audit checked the four public files against private question,
Gold, evidence and raw-output text and recognizable credential patterns. Private
ML-8 files and the original ML-7 packet retained their SHA-256 hashes and modification
times; the earlier audit script was not rerun because it writes its audit record.
Only the four intended files were staged, and the full staged diff, staged names,
whitespace checks and Git status were reviewed before the single freeze commit.
No private artifacts, captures, model files or documents are included.
