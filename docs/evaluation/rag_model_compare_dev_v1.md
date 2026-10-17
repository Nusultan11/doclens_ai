# ML-7 DEV-only Qwen3 model comparison

## Hypothesis and scope

Increasing Qwen3 Q8_0 weights from 1.7B to 4B may improve compliance with the
unchanged production answer/citation contract on the frozen English DEV sample.
This is model selection only. There is no production promotion, prompt tuning,
retrieval rerun, output repair, fine-tuning, or use of held-out TEST outputs in
the comparison. Human semantic correctness remains **NOT_EVALUATED**.

**Production decision: REJECT.** The completed candidate run delivers no valid answer or refusal:
strict acceptance remains 0/15, matching ML-6 DEV. Six outputs now pass the schema
but all six fail unchanged citation validation. The other nine fail the schema.
This is a completed model comparison with an unsuccessful candidate, not a
runtime/provenance failure. The original strict-comparison decision **FIX** remains
preserved in the private comparison; this finalization records the production
decision separately. New independent AI-assisted diagnostics assess all 12 raw
positive facts as correct, but identify two incorrect/unsupported negative
responses and one semantically appropriate, contract-invalid abstention. These
assessments are **not operator-confirmed or independently human-reviewed**.
There are no unsafe *accepted* answers because there are no accepted outputs;
this does not establish raw-output safety. Finalization performs no inference,
uploads, tuning, production changes or validator changes.

## Frozen identities

| Identity | ML-6 baseline | ML-7 candidate |
|---|---|---|
| Official repository | Qwen/Qwen3-1.7B-GGUF | Qwen/Qwen3-4B-GGUF |
| Revision | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` | `bc640142c66e1fdd12af0bd68f40445458f3869b` |
| File | Qwen3-1.7B-Q8_0.gguf | Qwen3-4B-Q8_0.gguf |
| Bytes | 1,834,426,016 | 4,280,404,704 |
| License | Apache-2.0 | Apache-2.0 |

GGUF SHA-256:

- Baseline: `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`.
- Candidate: `8c2f07f26af9747e41988551106f149b03eb9b5cb6df636027b6bf6278473300`.

Both use llama.cpp b11617, commit
`14310190cd0a0c831fe949ac8cbedd8abdc90695`. Runtime archive SHA-256:
`1c5024dfa587a3f23ef8fc066cb2578fb43d661910d4111a8941184773c237d1`;
llama-server SHA-256:
`88f69b22b3b109328e12109ee05ed4e32bf870c92c56c34479be7e1e9e0bce62`.
Candidate compatibility was verified by the actual completed CUDA run, matching
model/archive/executable hashes and two consistent full-offload events of 37/37
layers. Only CUDA0 was selected, with no CPU fallback. The T4 host exposes two
devices; the second was not used for this experiment.

Embedded tokenizer metadata matches between models: GPT2/qwen2, vocabulary
151,936, canonical tokenizer fingerprint
`cedb9b127c808acac86ff28de8f3637a02412c93921238514666fad30466357c`.
Both embedded chat templates have SHA-256
`57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`.
Unavoidable model differences include 28 versus 36 blocks, embedding width
2,048 versus 2,560, feed-forward width 6,144 versus 9,728, and 16 versus 32
attention heads. KV heads remain eight. The configured context stays 16,384.

Sources: official pinned [candidate model](https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/bc640142c66e1fdd12af0bd68f40445458f3869b)
and [license](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/bc640142c66e1fdd12af0bd68f40445458f3869b/LICENSE),
authenticated Kaggle metadata, local GGUF metadata and artifact hashes.
Hub metadata was queried with installed huggingface_hub 0.36.0;
configured documentation MCP supplied the official model-info API reference.
The downloaded license SHA-256 is
`5de36594c10839788a8c589443a8ef9d8b8d17c65a1b5807206ae037fc36c6bd`.

## Input and controlled protocol

The existing strict Gold loader validates the approved dataset. Split selection
retains exactly 15 unique DEV IDs, 12 positive and three negative questions,
and 84 originally packed chunks. Only original question/context messages enter
the private export. Gold selects the split, never evidence or generated answers.

- Approved Gold SHA-256: `a818104a22833e174ceef572df8c699b81e93a5fd61d90092f33705ad61d7fa0`.
- Gold fingerprint: `66e84c335da8c6fd51468bed623e24ed7dc276e8dfc051f2a0261274105f00ee`.
- Original input SHA-256: `ccee3559dab595a68f836625b3669fa5c9e2c5b0b884f08f97227a03e6fa6260`.
- DEV input SHA-256: `c546f6fba758dc4df103878f2e61dc396d48a326420636fd414fe2f6346e9bf9`.
- DEV context fingerprint: `49ecf99088a021def3cff8073fd3cb0f13946600ea5816712df177b4fea9b967`.
- Production prompt SHA-256: `33622b5889415d5ec23df5995dfa647d4d8b0b3369838f03934b355be052ec89`.
- Frozen ML-6 capture SHA-256: `90a01c4166f2e079877d1afafe4ba0a3bff2f527506fcf67ec56b921e6d4b2df`.

DEV serialization explicitly preserves the staged Windows CRLF bytes on all
platforms. Message string contents are unchanged. Temperature 0, server seed 42,
JSON-object mode, 1,024 output tokens, 120-second deadline, 65,536-byte response
cap, concurrency one, reasoning off, CUDA0, full requested GPU offload and no
context shifting are fixed. No rejected answer is retried. LocalGenerator,
strict_json, ModelAnswer and validate_citations execute unchanged during replay.
The standalone candidate runner preserves the frozen runtime/capture/replay code;
synthetic tests compare the relevant function ASTs and provenance constants.

Private sources are the existing runtime/model dataset version 1, separate 4B
asset dataset version 2, and DEV input dataset version 2. The unused 1.7B weights
remain in the existing runtime dataset. The new script only selects the exact
4B filename; it cannot silently fall back to the old weights. The input dataset
was created with a harmless placeholder, then authenticated owner-only privacy
and absence of collaborators were checked before private content upload. Exact
remote input bytes and file allowlist were verified. Model assets contain only
public model/license/provenance files. Internet is disabled in the T4 kernel.

## DEV measurements

| Measure | Frozen ML-6 DEV | Candidate |
|---|---:|---:|
| Strict acceptance | 0/15 | 0/15 |
| Correct accepted positives | 0/12 delivered | 0/12 delivered |
| Correct negative refusals | 0/3 | 0/3 |
| Incorrect accepted positives | 0/12 delivered | 0/12 delivered |
| Unsupported accepted answers | 0/15 delivered | 0/15 delivered |
| Accepted negative answers | 0/3 | 0/3 |
| JSON failures | 0/15 | 0/15 |
| Schema failures | 15/15 | 9/15 |
| Citation failures | 0/15 | 6/15 |
| Runtime/protocol failures | 0/15 | 0/15 |
| Required-anchor coverage | 0/19 | 0/19 |
| Generation latency P50/P95, ms | 4,124.390 / 13,275.728 | 8,186.758 / 18,047.616 |
| Peak primary GPU memory, MiB | 3,731 | 6,605 |
| Peak server-tree RSS, bytes | 9,679,642,624 | 9,712,451,584 |

Exactly 15 unique DEV chat requests completed with HTTP 200 and finish reason
`stop`. There were no duplicate/TEST requests or rejected-output retries. All 15
passed transport/envelope and strict JSON parsing, but none passed the complete
production acceptance gate. Eight schema failures have an invalid `reason`
literal and one has an invalid citation range. Among the six citation failures,
all six have quote-slice mismatch, out-of-bounds answer ends and uncovered answer
characters; two also have out-of-bounds quote ends. These flags overlap. No
response was repaired. No raw factual correctness is inferred from these checks.

Candidate P50 is approximately 1.98 times baseline DEV P50, and P95 approximately
1.36 times baseline DEV P95. Sampled primary VRAM increased by 2,874 MiB.
Candidate sampling recorded 811 successful samples and zero failures at a nominal
0.2-second interval. Cold model startup after verification was 43.082 seconds,
separate from generation latency and Kaggle queue/container initialization.

Zero delivered-answer counts do not establish that raw factual answers were
correct or safe. Invalid output is a failure, never a successful refusal.
Baseline resource peaks cover its original complete 20-request process; latency
and answer metrics above select only the same 15 DEV cases. Peaks include model
startup and are not isolated DEV resource measurements. Latency uses linear
interpolation, includes failures, excludes startup and has no warm-up exclusion.

## Review, limitations and verification

The private review packet binds exact unrepaired responses, packed evidence,
DEV Gold references and output/configuration fingerprints. It is not an assertion
of independent human review. Accepted answers require semantic review; matching
JSON or quote offsets alone cannot establish source support. Any observed unsafe
acceptance requires REJECT. Improvements without observed unsafe acceptance may
only yield CANDIDATE_FOR_FURTHER_EVALUATION, never production PASS.

This small, English-only sample cannot establish generalization to Russian,
Kazakh, other domains or production workloads. This is staged offline replay,
not fresh PostgreSQL authorization or an API end-to-end benchmark. The packed
input does not contain authoritative source SHA mappings; source-anchor coverage
for nonempty delivered citations requires that separate mapping. With no delivered
citations the exact coverage numerator is zero without inferring identities.

Candidate execution, final safety comparison, review-packet location and final
verification are recorded below. The comparison and private review packet are:

- `evaluation-output/rag-model-compare-dev-v1/comparison.json`.
- `evaluation-output/rag-model-compare-dev-v1/human-output-review.json` (15 outputs).
- `evaluation-output/rag-model-compare-dev-v1/contract-forensics.json`.
- `evaluation-output/rag-model-compare-dev-v1/remote-completion-provenance.json`.

The operator has now explicitly authorized one commit freezing these five ML-7
files after verification. This authorization is not confirmation of the new
AI-assisted factual verdicts and does not promote the model.

## Independent AI-assisted diagnostic raw-output review

The supplied independent AI-assisted assessment is recorded without independently
re-annotating its factual judgments. It is not an operator-confirmed assessment,
independent human review, or formal OutputReview. Human-reviewed correctness,
faithfulness and unsupported-claim rates remain **NOT_EVALUATED**. Original
capture/review/metric files, their original FIX and NOT_EVALUATED fields, and all
rejected outputs remain unchanged. No rejected output is made into a delivered
RagOutcome or formal review label.

| Diagnostic observation, rejected raw outputs only | Numerator / denominator |
|---|---:|
| Qwen3-4B positive factual correctness, independent AI-assisted | 12/12 |
| Qwen3-1.7B DEV raw positive correctness, previous operator-confirmed ML-6 assessment | 10/12 |
| Qwen3-4B incorrect/unsupported negative responses | 2/3 |
| Qwen3-4B semantically appropriate but structurally invalid negative abstention | 1/3 |
| Qwen3-4B strict production acceptance | 0/15 |
| Qwen3-4B valid production negative refusals | 0/3 |
| Qwen3-4B delivered required-evidence coverage | 0/19 |

The two negative diagnostic failures are an unsupported assertion and an
incorrect answer to the question. The third negative conveys an appropriate
abstention but fails the production response contract. The 12/12 versus 10/12
comparison uses different review provenance: new independent AI-assisted findings
for 4B and the previously operator-confirmed AI-assisted ML-6 DEV assessment.
It is not a new controlled human correctness study or evidence of improved
production quality. The larger model costs more latency/VRAM while delivering
the same zero strictly valid results.

Citation checks were recomputed mechanically from all unmodified proposed
citations and their exact frozen packed contexts, including schema-invalid
outputs. They match the supplied observations with **no discrepancies**:

| Diagnostic proposed-citation check | Numerator / denominator |
|---|---:|
| Total proposed citations | 17 |
| Chunk identity found in the corresponding frozen context | 17/17 |
| Document-version identity matches that chunk | 17/17 |
| Nonblank quote is a literal substring of that chunk | 11/17 |
| Nonempty in-bounds quote offsets reproduce the exact quote | 1/17 |
| Nonempty answer span is within the raw answer bounds | 4/17 |

These are independent checks, not a conjunction establishing valid citations.
Identity binding, literal substring matching and bounded offsets do not establish
semantic support or faithfulness. The one exact quote-offset match does not
rescue its complete response; strict acceptance remains zero. Invalid outputs
are never credited as successful refusals or delivered evidence coverage.

Each private verdict is bound to question ID, DEV Gold example/full-dataset
identity, experiment/input identity, capture/packet hashes, exact raw model-content
SHA-256 and raw-capture fingerprint. The original supplied review bytes and all
15 original output bindings were verified. The private audit is under
`evaluation-output/rag-model-compare-dev-v1/diagnostic-review-audit-133e3b85491e4be7b1a822f75b4c215f/`:

- `supplied-review-original.json`: unchanged supplied AI assessment.
- `bound-diagnostic-verdicts.json`: all 15 privately bound verdicts and recomputed checks.
- `verification-summary.json`: sanitized aggregates and empty discrepancy list.
- `preservation-before.json`: hashes of 88 existing ML-7 artifacts before finalization.

The source review SHA-256 is
`9053d7c8c7d5c755c18816e548c466baf39ee5270b322e668f212b1af35bba56`;
the exact original review packet SHA-256 is
`2392acbf710bb336670aff2f83131424451536009c61e394ae7ef8078f13da93`.
No reviewer identity or operator confirmation was invented. Case texts, Gold
answers, rationales and raw model responses remain private.

The previous simplified extractive binder was also rejected because it accepted
unsafe answers. That historical rejection remains in force; literal evidence
binding cannot substitute for semantic support. No binder is introduced or
re-evaluated here, and no prompt, retrieval, model or decoding change is made.

## Completed remote provenance

Private kernel `nurs2005/doclens-rag-model-compare-gpu-dev-v1/1` reached COMPLETE.
Only one inference run was created. Two preceding SaveKernel attempts returned
409 before a run existed: the initial kernel title was already occupied by the
input dataset. Authenticated search and the API error body established that
cause; only kernel title/slug changed before the successful submission. There
were no changes to the model script, contexts or generation configuration.

Actual API source bytes exactly match source SHA-256
`6e7c10c5a620e4c6ea135c1be6d35a96cc4f6a34edbe02d02e930f3813403aba`.
The Windows CLI's pulled copy converts LF to CRLF; verification used the API
source itself, then the Linux capture's independently computed source hash.
The API private/T4/internet/source-allowlist verification completed at
2026-10-17 02:54:29 UTC, before inference began at 03:04:06 UTC. Inference finished
by 03:06:34 UTC. Dataset processing had also completed before submission; the
first post-upload metadata response still pointed to placeholder version 1 and
was preserved rather than treated as ready or causing another upload.

- Configuration fingerprint: `51c9b0c1f9b13ecd7aec0ee098eb0bf52eaa1ca098e2ca5366ce279c88532d5e`.
- Request/case fingerprint: `f10442fbb6251076ac46f8180b1ed14b539cc0b74ef8af29241cd92ca13b3437`.
- Candidate capture SHA-256: `7de912a2d79ba4cf2ded0bafa1acdb323aab042e7747f6192423a45d492cd121`.
- Candidate server-log SHA-256: `39bdd952d0193f2a7d1ca50a8a24d9fe9ba5e3dde8d832317c59269430dc9dc2`.

Both runs used the same Kaggle container image
`gcr.io/kaggle-private-byod/python@sha256:2757e0c7d1e0a9cb43da657b97e223c321a98f5014bdf64f44f2f6b083ad2b2f`,
Python 3.13.15, httpx 0.28.1, psutil 5.9.5, GPU driver 580.178.04 and the same
pinned llama.cpp executable. CUDA0 was Tesla T4, 15,360 MiB total memory.

Preparation verification on 2026-10-17:

- `.venv\Scripts\python -m pytest -q tests/unit`: **630 passed, 1 skipped**
  (Windows symlink privilege unavailable).
- `.venv\Scripts\python -m pytest -q tests/unit/test_kaggle_rag_model_compare.py tests/integration/test_kaggle_rag_model_compare.py`:
  preparation: **42 passed, 1 skipped**, before capture existed; final invocation
  with `DOCLENS_RAG_MODEL_COMPARE_RUN` set: **43 passed, no skips**.
- `$env:DOCLENS_RAG_MODEL_COMPARE_RUN='C:\Users\nurs\doclens_ai\evaluation-output\rag-model-compare-dev-v1'; .venv\Scripts\python -m pytest -q -s tests/integration/test_kaggle_rag_model_compare.py`:
  **1 passed**, actual candidate/baseline DEV strict replay and GPU provenance.
- `.venv\Scripts\ruff check .`: passed.
- `.venv\Scripts\ruff format --check tools/kaggle_gpu/rag_model_compare tests/unit/test_kaggle_rag_model_compare.py tests/integration/test_kaggle_rag_model_compare.py`:
  passed.
- `git diff --check`: passed.
- `.venv\Scripts\python evaluation-output/rag-model-compare-dev-v1/preflight.py`:
  frozen baseline DEV replay/configuration comparison passed.
- `.venv\Scripts\python evaluation-output/rag-model-compare-dev-v1/audit.py`:
  original 40 file hashes unchanged, exact remote DEV bytes, DEV selection and
  public-file privacy audit passed.
- `python evaluation-output/rag-model-compare-dev-v1/final_provenance.py`:
  COMPLETE, exact mounted hashes, source/configuration/request binding, 15 HTTP
  200/stop responses and pre-inference verification passed.
- `kaggle kernels status nurs2005/doclens-rag-model-compare-gpu-dev-v1`:
  `KernelWorkerStatus.COMPLETE`.
- Authenticated post-run metadata again confirmed all three datasets owner-only
  private with no collaborators and expected versions 2/1/2.

Direct `pytest -q tests/unit` initially failed collection because the console
entry point omitted the repository root needed for the existing `tools` import.
The complete suite passed using `python -m pytest`; no existing code was changed
to accommodate that invocation issue. An earlier permission-review service limit
interrupted execution before a command ran; verification resumed after the user
requested continuation. HF CLI transfer stalled, then a bounded range download
was interrupted by DNS failure; resumed bytes were not trusted until the complete
official SHA-256 matched. These were operational interruptions, not model results.

## Finalization verification

The independent AI-assisted review was finalized offline on 2026-10-17. No new
model inference, Kaggle API operation, upload, prompt tuning or production change
was performed. No implementation regression was found, so runner, metadata and
both test files were kept byte-for-byte unchanged during finalization. Only this
sanitized report changed; the commit freezes the five previously prepared ML-7
files and excludes all private audit/capture/model files.

Executed commands and actual results:

- `.venv\Scripts\python -m pytest -q tests/unit/test_kaggle_rag_model_compare.py`:
  **42 passed**.
- `$env:DOCLENS_RAG_MODEL_COMPARE_RUN='C:\Users\nurs\doclens_ai\evaluation-output\rag-model-compare-dev-v1'; .venv\Scripts\python -m pytest -q tests/integration/test_kaggle_rag_model_compare.py`:
  **1 passed**, replaying existing captures with unchanged strict validators.
- `.venv\Scripts\python -m pytest -q tests/unit`: **630 passed, 1 skipped**;
  the skipped test requires Windows symlink privilege unavailable here.
- `.venv\Scripts\ruff check .`: passed.
- `.venv\Scripts\ruff format --check tools/kaggle_gpu/rag_model_compare/benchmark.py tests/unit/test_kaggle_rag_model_compare.py tests/integration/test_kaggle_rag_model_compare.py`:
  passed; all three Python files already formatted.
- `.venv\Scripts\python evaluation-output/rag-model-compare-dev-v1/audit.py`:
  frozen DEV export/privacy checks and original 40 pre-ML-7 preservation checks
  passed.
- `.venv\Scripts\python evaluation-output/rag-model-compare-dev-v1/diagnostic-review-audit-133e3b85491e4be7b1a822f75b4c215f/verify_review.py`:
  all 15 source/output/Gold bindings, requested verdicts, structural citation
  counts, COMPLETE/37-layer provenance and all **88 existing ML-7 artifact
  hashes** passed; discrepancy list empty.
- `.venv\Scripts\python evaluation-output/rag-model-compare-dev-v1/diagnostic-review-audit-133e3b85491e4be7b1a822f75b4c215f/check_scope_privacy.py`:
  five-file scope, unchanged implementation and absence of private case/Gold/
  document content, model artifacts and recognizable secret formats verified.
  Diagnostic audit files are Git-ignored.
- `git diff --check` and `git status --short`: checked before staging;
  only the five authorized ML-7 files were present. Staged diff and status are
  checked again before the single requested commit.

Finalization is complete after successful verification and the authorized freeze
commit. The **production decision remains REJECT**; human-reviewed quality
remains **NOT_EVALUATED**. No next major step is started.
