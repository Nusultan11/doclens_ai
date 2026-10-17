# ML-9 DEV schema-constrained decoding experiment

EXPERIMENT_EXECUTION: PASS
CANDIDATE_QUALITY: REJECT
PRODUCTION_AUTHORIZATION: false

## Pre-registered scope

Baseline commit: 81957668deafb216833075d29e9a0acf158df3a1.
Production generation remains REJECT. No production integration or schema repair.

Compare the frozen Qwen3-4B Q8_0 b11617 baseline with identical model, runtime,
prompt, messages, context, seed, output limit and runtime settings. Only
response_format differs: A json_object; B json_schema with json_schema.schema.
Run two unchanged repetitions, each with 15 frozen DEV cases (12 positive,
3 negative) plus four independently operator-confirmed synthetic refusal probes.
Even case indices run AB; odd indices BA, identically in both repetitions.
Gold/labels never enter model messages. No TEST queries or model selection.

The probes cover negation, unresolved conflicting assertions, wrong entity and
prompt injection. The operator independently confirmed all four as requiring
insufficient-evidence refusal before inference. Any accepted code answer on those
probes is unsafe. Original negative DEV questions explicitly name their source
document; their document-scoped Gold must not be interpreted as workspace truth.

## Schema compatibility

The schema snapshots the unchanged ModelAnswer JSON Schema, including required
fields, additionalProperties=false, UUID patterns, lengths, integer bounds and
citation-array limits. References are inlined, without dropping constraints.
The pinned parser ignores sibling bounds on anyOf. The current production export
already places the nullable answer's maxLength=8000 inside its string branch;
that bound is retained unchanged. The helper also losslessly distributes such a
bound if presented as a nullable-union sibling, and a dedicated regression test
verifies the same resulting schema. The frozen inference schema needed no such
rewrite.
No unsupported feature is silently removed. A compatibility guard rejects unknown
keywords, unanchored patterns, mixed object unions, noninteger bounds and
pattern-plus-length combinations (the pinned converter prioritizes patterns).

Custom Python validators (nonblank strings, answer/refusal consistency, relative
span bounds), citation identities and exact slices remain unchanged
post-generation checks; JSON Schema does not replace those checks. Semantic
support is not established by these validators and remains NOT_EVALUATED.
No claim that constrained decoding enforces the complete Python contract is made.

Only commit-pinned llama.cpp documentation/source is authoritative:
[grammar documentation](https://github.com/ggml-org/llama.cpp/blob/14310190cd0a0c831fe949ac8cbedd8abdc90695/grammars/README.md),
[server parsing](https://github.com/ggml-org/llama.cpp/blob/14310190cd0a0c831fe949ac8cbedd8abdc90695/tools/server/server-common.cpp),
[converter](https://github.com/ggml-org/llama.cpp/blob/14310190cd0a0c831fe949ac8cbedd8abdc90695/common/json-schema-to-grammar.cpp).
Documentation MCP returned unpinned master material, which was not used as evidence.
The documentation's legacy Python-converter path is absent in this revision;
compatibility is checked against the pinned C++ implementation and actual HTTP runs.

## Metrics and decision rules

Separate HTTP/runtime failures, strict JSON validity, schema validity, strict
citation validity, accepted responses, valid verified-scope negative refusals,
invalid refusal attempts, negative answers, unsafe accepted synthetic answers,
P50/P95 generation-request latency and available output token counts.
Keep both arms and repetitions separate; report paired regressions.
Genuine envelopes are replayed through unchanged LocalGenerator, strict_json,
ModelAnswer and validate_citations. For B, only the mock transport's expected
outgoing response_format is normalized to the adapter's fixed A format; captured
B requests and exact response bytes remain separately provenance-verified.
No quote binder is applied in this experiment.

Unsafe acceptance against a verified negative/probe label forces REJECT.
Schema improvement alone cannot support a positive quality decision. Generated
positive factual correctness/faithfulness remain NOT_EVALUATED without independent
output review. In its absence, quality is at best INCONCLUSIVE. No result authorizes
production. Structural acceptance is not semantic grounding or a delivered release.

## Execution and verification

Two unchanged GPU runs completed and genuine local capture replay passed.
Private preregistration, exact captures, labels, logs and manifests stay under the
ignored tools/kaggle_gpu/outputs/rag-schema-dev-v1 directory. Only this sanitized
report and the allowlisted runner, metadata and tests are eligible for Git.
Existing ML-6/7/8 artifacts are preserved.


## Frozen experiment identities

- Model revision: bc640142c66e1fdd12af0bd68f40445458f3869b.
- Model SHA-256: 8c2f07f26af9747e41988551106f149b03eb9b5cb6df636027b6bf6278473300.
- Runtime commit: 14310190cd0a0c831fe949ac8cbedd8abdc90695 (b11617).
- Runtime archive SHA-256: 1c5024dfa587a3f23ef8fc066cb2578fb43d661910d4111a8941184773c237d1.
- Server SHA-256: 88f69b22b3b109328e12109ee05ed4e32bf870c92c56c34479be7e1e9e0bce62.
- Frozen DEV input SHA-256: c546f6fba758dc4df103878f2e61dc396d48a326420636fd414fe2f6346e9bf9.
- Source SHA-256: c5da562385c67ba5912a733ad1a476cdc9129e2f912b6d95205b62fb045fe550.
- Schema fingerprint: 9f726c8371855ca0f28cd1e35316311913033f1cdfd10d77abc3da41934fda8f.
- Case fingerprint: b787c5be5930f73dce0bc7064babb83d781a15b78d613b1b2825bed81454ef97.
- Configuration fingerprint: a72cd4402a5b1032f58cb8f007d4675d589616e5690503ddacd9b19db47d13ee.

Existing dataset revisions: runtime /1, model /2, DEV input /2.
The exact revision references are preserved in submission metadata; runtime/model
bytes and DEV-input bytes are independently hash-checked inside each job.
No new dataset was created or uploaded.

The isolated upload contains exactly benchmark.py and kernel-metadata.json.
The first authenticated remote source matches the source SHA above. CLI pull
rewrites line endings on Windows, so exact source verification uses the API's
source string encoded as UTF-8. A version-suffixed CLI pull returned 403; the
authenticated latest-version response exposes the version number and exact source.

Preparation verification: 43 focused unit cases passed; production RAG/binder
regressions 103 passed. Final full-unit verification: 719 passed, one existing Windows
symlink-privilege skip.
Default integration invocation skips without the explicit replay environment
variable, confirming normal pytest does not launch inference. Ruff lint and format
checks passed. A read-only audit verified all 43,561 existing artifact files
unchanged (size, modification time, and hashes for files below 20 MB); larger
artifacts retain exact size/time and the pinned model/runtime are hash-checked
inside the GPU job. No private case, answer, Gold or document text, or recognizable
credential pattern was found in the five public files.


## Completed GPU runs and provenance

Private Kaggle kernel versions **1 and 2** both reached **COMPLETE**.
Each captured all 38 requests with HTTP 200 and no transport/runtime failures.
Each log contains two consistent full-offload events of **37/37 GPU layers** on
CUDA0, Tesla T4. Model, archive and executable hashes, b11617 version, input bytes,
source, schema, case and configuration fingerprints matched in both runs.
The exact Docker image and recorded HTTP/client libraries also matched.

Capture SHA-256:

- Version 1: 20cc82d4e2e911f357975a965eca0a82a14646f12ecfbda7beee735879fd942b.
- Version 2: a760580aea2bc0fda58b3bdece10af630265a05e2bf35a650ca5710d5bf6ce9a.

These are different genuine HTTP captures, not copied outputs. The 38 extracted
model-content hashes were identical across repetitions; envelope IDs/timestamps
and observed timings differ. This small observation does not guarantee future
determinism. Both server logs lack schema-conversion-incomplete warnings.
Preregistration timestamps precede inference in both runs. No schema, prompt,
settings or payload edits occurred between versions, and no rejected answer was
retried. No additional inference was performed.

## A/B results

Every rate below is per run, without pooling the repetitions. A uses json_object;
B uses schema-constrained decoding. Each arm contains 15 DEV cases and four probes.

| Run / arm | Strict JSON | ModelAnswer valid | Strict accepted | Request P50 / P95 ms | Output tokens |
|---|---:|---:|---:|---:|---:|
| 1 / A | 19/19 | 9/19 | 1/19 | 6509.762 / 15575.026 | 4226 |
| 1 / B | 19/19 | 8/19 | 1/19 | 5649.385 / 11108.234 | 4173 |
| 2 / A | 19/19 | 9/19 | 1/19 | 6362.639 / 15604.032 | 4226 |
| 2 / B | 19/19 | 8/19 | 1/19 | 5821.929 / 11127.486 | 4173 |

Output-token usage was available for all 19 responses in every arm.
Request latency includes prefill, decode, schema and local HTTP overhead.
Server-reported decode-only P50/P95 milliseconds, also available for all 19:

| Run | A | B |
|---|---:|---:|
| 1 | 4762.305 / 10832.417 | 4904.382 / 10322.889 |
| 2 | 4856.662 / 11104.249 | 4959.694 / 10703.874 |

Two short, cache-sensitive runs cannot establish a general speed advantage.

The following outcomes were identical in both repetitions:

| Measure | A | B |
|---|---:|---:|
| HTTP/runtime failures | 0/19 | 0/19 |
| Strict JSON failures | 0/19 | 0/19 |
| ModelAnswer failures | 10/19 | 11/19 |
| Citation failures after schema validation | 8/19 | 7/19 |
| Strict citation-valid responses | 1/19 | 1/19 |
| Strict accepted real DEV | 0/15 | 0/15 |
| Real DEV schema / citation failures | 9 / 6 | 9 / 6 |
| Synthetic schema / citation failures | 1 / 2 | 2 / 1 |
| Verified negative correct strict refusals (3 DEV + 4 probes) | 0/7 | 0/7 |
| Explicit invalid refusal attempts (answerable=false, invalid contract) | 0/19 | 0/19 |
| Accepted real negative answers | 0/3 | 0/3 |
| Raw answerable=true claims on real negatives | 3/3 | 3/3 |
| Schema-valid negative answer claims (DEV + probes) | 3/7 | 2/7 |
| Unsafe accepted probes under verified refusal labels | 1/4 | 1/4 |
| Production releases | 0/19 | 0/19 |

All four probes also received raw answerable=true claims. Such a flag is an
answerability-contract observation, not an independently established factual-error
count. Contract-invalid semantic abstention and general raw negative factual
correctness remain NOT_EVALUATED without independent output review. Invalid
outputs were never credited as valid refusals.

The sole accepted synthetic outcome in each arm/repetition was the negation
probe. Its output supplied a partial exclusion rather than identifying the
unknown requested value or strictly refusing. This violates the independently
operator-confirmed negative/refusal label and forces REJECT under the registered
rule. It is **not** evidence that the model falsely asserted a particular code:
the accepted partial exclusion itself repeats supplied evidence. Structural
citation acceptance therefore does not establish question answering or appropriate
abstention. No raw output text is reproduced here.

A had nine reason-enum errors and one invalid-span error per run. B instead had
ten answer/refusal-consistency errors and one invalid-span error. Constraining
the field types and reason enum did not enforce custom cross-field consistency,
citation slicing or semantic answerability. No validator was weakened to turn
these failures into successes.

Within each run, B changed one synthetic classification from citation failure to
schema failure. There were **zero A-accepted/B-rejected** and **zero
A-rejected/B-accepted** transitions. Between repetitions there were **zero
classification changes** for either arm. Overall schema validity fell by 1/19;
strict accepted outcomes did not improve. The real DEV outcomes remained at the
frozen baseline's 0/15 strict acceptance.

## Final decision and limitations

**EXPERIMENT_EXECUTION: PASS. CANDIDATE_QUALITY: REJECT.
PRODUCTION_AUTHORIZATION: false.** The experiment completed technically; the
candidate did not improve the complete contract and accepted a verified refusal
probe. No model, binder or generated response is promoted.

General positive factual correctness and faithfulness remain NOT_EVALUATED.
The semantic finding above is limited to the independently verified refusal
label; no broad hallucination rate is inferred. Citation identity/slice checks
are structural, not entailment. Canonical source-anchor coverage remains
unavailable without the export's omitted source-SHA mapping. Production delivered
DEV evidence coverage stays 0/19 because there are no production releases.
The sample is small, English-only and fixed DEV; no TEST selection occurred.

No future production integration is authorized. It would require a separately
evaluated full answer/refusal contract, independently reviewed semantic evidence,
verified source identities and authorization, and safety regressions. That work
is outside this step and has not been started.

## Final verification commands

Executed with the existing virtual environment, without adding dependencies:

- `.venv\Scripts\python -m pytest -q tests/unit/test_kaggle_rag_schema_dev.py`:
  **43 passed**.
- `.venv\Scripts\python -m pytest -q tests/unit/test_rag.py tests/unit/test_rag_quote_binding.py`:
  **103 passed**.
- `.venv\Scripts\python -m pytest -q tests/unit`:
  **719 passed, 1 skipped** (existing Windows symlink privilege limitation).
- `$env:DOCLENS_RAG_SCHEMA_REPLAY='1'; .venv\Scripts\python -m pytest -q -s tests/integration/test_kaggle_rag_schema_dev.py`:
  **1 passed**, both genuine completed captures; no inference from pytest.
- Without that opt-in, the integration test **skipped** as designed.
- `.venv\Scripts\python -m ruff check .`: passed.
- `.venv\Scripts\python -m ruff format --check tools/kaggle_gpu/rag_schema_dev tests/unit/test_kaggle_rag_schema_dev.py tests/integration/test_kaggle_rag_schema_dev.py`:
  passed, three files already formatted.
- `.venv\Scripts\python tools/kaggle_gpu/outputs/rag-schema-dev-v1/audit.py`:
  read-only privacy, frozen-artifact, private-capture and allowlisted-source checks.
- `git diff --check`, full staged diff and staged file-name/whitespace checks:
  reviewed before the single experiment commit.

A standalone sandboxed asyncio replay stalled on Windows and was terminated;
the same replay and the final genuine integration replay succeeded with the
required Windows execution permissions. Initial ad-hoc capture reading used the
wrong Windows default encoding; it was rerun explicitly as UTF-8, without changing
capture bytes. These were local execution issues, not model/runtime experiment
failures. No frozen ML-6, ML-7 or ML-8 artifact was overwritten.
