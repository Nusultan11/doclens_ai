# ML-6 real-model offline RAG diagnostic v1

## Decision

**Finalization PASS; production decision REJECT.** The failed ML-6 diagnostic
baseline is frozen. On 2026-10-16 the operator explicitly confirmed all 20
AI-assisted raw-output case assessments, bound privately to the frozen captures.
Kernel `nurs2005/doclens-rag-real-baseline/2` completed successfully with explicit
GPU layer-offload provenance. The baseline remains a **model-contract failure**:
all 20 outputs in both runs fail the unchanged ModelAnswer schema. This is not
proof that their factual content is incorrect. No output was repaired, no invalid
output was credited as a refusal, and no prompt or model setting was tuned.
The production safety decision is exactly **REJECT**, with no promotion.
Operator-confirmed raw factual assessments are reported separately below.
Independent human-reviewed production answer quality, production faithfulness
and unsupported-claim rates remain **NOT_EVALUATED**: there are no accepted
production answers, and the supplied review is AI-assisted rather than
independently reproduced manual annotation.

This is a staged offline benchmark: real authorized production retrieval was
frozen earlier, then model HTTP responses were captured privately on Kaggle and
replayed locally. It is not live PostgreSQL revalidation or a complete API E2E
benchmark. Finalization records the operator-confirmed diagnostic review without
turning rejected raw outputs into delivered answers. There is no production
promotion, fine-tuning, reranking or retrieval change. No fine-tuning decision was
made and no training was started; this step does not authorize further tuning.

## Runtime root cause and correction

Version 1 returned HTTP 200 with finish reason `stop` for all 20 requests but
ended in ERROR. Its server argument `--verbosity 1` produced an empty log, so the
explicit phrase-based GPU-offload evidence gate could not pass. CUDA0 enumeration
and GPU memory use were recorded but were not accepted as substitutes for layer
provenance. That first-run failure remains recorded and all its artifacts are
unchanged.

The corrected runner differs from the exact submitted v1 source only in
`--verbosity 1` becoming `--verbosity 5`, restoring the previously verified smoke
runner's logging. Byte-for-byte source comparison after that one replacement,
configuration comparison and all 20 request comparisons passed. Model/runtime
hashes, GGUF chat template, production prompt, packed contexts, temperature 0,
seed 42, 16,384-token context window, 1,024-token output budget, 120-second deadline,
65,536-byte response cap, concurrency 1, reasoning off, CUDA0 and context shifting
disabled are unchanged. No dataset was uploaded again and no individual output
was retried. Exactly one repeat of the same 20 requests was submitted.

Version 2 reached COMPLETE. Its original private llama.cpp log records:

```text
load_tensors: offloaded 29/29 layers to GPU
load_tensors: offloaded 29/29 layers to GPU
```

Both recorded load events report all 29 layers offloaded. CUDA0 selection,
expected public GGUF filename, model-loading records and runtime build commit
are present in the same log; health readiness and 20 successful requests further
confirm loading succeeded. Captured artifact hashing verifies model/archive/
executable bytes independently of text in the log. Runtime is `0.6.0-dev`, build
11617, commit `14310190c`, GNU 13.3.0, Linux x86_64. Python/library/runtime-version/
GPU-driver identities match the first run.

An initial local provenance verifier incorrectly required exactly one offload
line. It was corrected to require at least one event, every event positive and
fully offloaded, and all events agreeing on the same counts. This accepts the
two actual matching events while rejecting absent, zero, partial or conflicting
counts. This correction affected only provenance verification; no additional
remote run occurred and no generation or production validator changed.

## Output forensics and root cause

Both runs pass LocalGenerator transport/envelope validation and strict_json for
20/20 responses. Exact capture/request binding, original packed messages and
frozen generation configuration all match. The raw model contents themselves
fail ModelAnswer. The stored first-run review contents exactly match the original
raw responses. No answer repair, coercion, citation binding or validator weakening
was introduced. This establishes incompatibility with the frozen output contract
under this model/configuration. Independent manual semantic re-annotation was
not performed; the separate operator-confirmed AI-assisted findings are below.

Primary reasons use the first error returned by unchanged ModelAnswer validation,
with exactly one primary reason per rejected response:

| Exclusive primary reason | Run 1 / 20 | Run 2 / 20 |
| --- | ---: | ---: |
| Missing top-level required fields | 0 | 0 |
| Unexpected fields | 0 | 0 |
| Wrong types | 0 | 0 |
| Inconsistent answerable/answer/reason, including invalid reason literal | 15 | 15 |
| Missing or malformed citation list | 0 | 0 |
| Invalid nested citation structures | 5 | 5 |
| Other validation failures | 0 | 0 |
| Total | 20 | 20 |

Additional findings overlap and must not be added to the primary totals. In each
run, all 20 outputs have an answer/reason-contract failure; 4 outputs lack 12
required nested citation fields (six quote_start and six quote_end fields); one
additional output fails the nested citation-range contract. There are 19 reason
literal errors and one top-level consistency error per run. No response reaches
validate_citations: zero citation-stage rejections does not mean the citations
are valid. Transport, JSON and citation-stage failures are each 0/20; schema-stage
failures are 20/20. The report does not infer factual incorrectness from rejection.

## Exact verdicts and automatic metrics

| Measure | First run, version 1 | Repeat, version 2 |
| --- | ---: | ---: |
| Remote completion | ERROR | COMPLETE |
| HTTP 200 / stop responses | 20/20 | 20/20 |
| Strict JSON parse | 20/20 | 20/20 |
| Accepted positive answers | 0/17 | 0/17 |
| Valid correct refusals | 0/3 | 0/3 |
| Accepted answers / all requests | 0/20 | 0/20 |
| Valid refusals / all requests | 0/20 | 0/20 |
| Schema-invalid outputs | 20/20 | 20/20 |
| Request-level HTTP/runtime failures | 0/20 | 0/20 |
| Required Gold evidence coverage | 0/28 | 0/28 |
| Positive lexical exact match credited to accepted outputs | 0/17 | 0/17 |
| Citation structural validity | 0/0, undefined | 0/0, undefined |
| Answerability precision / recall | 0/0; 0/0, undefined | 0/0; 0/0, undefined |
| Refusal precision / recall | 0/0; 0/0, undefined | 0/0; 0/0, undefined |
| Runtime provenance gate | failed | passed, 29/29 layers |

Invalid outputs are absent outcomes in the existing evaluator, not synthetic safe
refusals or true negatives. Its broad undelivered-outcome rate therefore includes
schema rejections; the separate request-failure rate is zero. Lexical exact match
is not semantic correctness. Coverage counts delivered validated citations only.
The generated content strings match for all 20/20 cases across these two observed
runs. This was measured, not inferred from temperature 0, and is not a claim of
general determinism or future output equality. Raw envelopes/fingerprints can differ.

## Operator-confirmed AI-assisted raw-output review

The operator explicitly confirmed all 20 supplied AI-assisted case assessments
on **2026-10-16**. The original assessment identifies itself as AI analysis, not
formal human review. Its original file and draft-status fields were preserved;
a separate private audit records the subsequent operator confirmation and its
provenance. No independent reviewer identity was supplied or invented. This is
not independently reproduced manual annotation by another reviewer.

All 20 question IDs, Gold answerability and split, Gold and experiment
fingerprints, exact raw capture/output fingerprints, and unmodified generated
contents were verified against the frozen repeat packet. Original and repeated
raw contents match for 20/20 cases; their raw-capture fingerprints remain distinct
where HTTP envelope/timing metadata differ. The supplied review-packet SHA-256
and all 20 reported output fingerprints match the preserved repeat packet.
Proposed-citation observations were independently recomputed mechanically from
those same frozen messages without changing the supplied factual verdicts.
No conflict with the frozen bindings was found. The factual judgments themselves
were not independently re-annotated in this finalization.

| Diagnostic raw-output observation | Numerator / denominator |
| --- | ---: |
| Positive factual correctness, AI-assisted and operator-confirmed | 13/17 |
| Positive factual errors, AI-assisted and operator-confirmed | 4/17 |
| Valid negative refusals | 0/3 |
| Contradictory abstention on a negative case | 1/3 |
| Inappropriate nonempty negative answers | 2/3 |
| Proposed citations | 23 across 20 outputs |
| Proposed chunk IDs found in frozen packed context | 23/23 |
| Proposed quotes that are literal substrings | 14/23 |
| Proposed quotes with valid exact quote offsets | 0/23 |

These are **diagnostic raw-output observations**, not accepted backend metrics,
production faithfulness, or validated-citation quality. A correct raw fact can
still have incorrect evidence or offsets and fail the entire output contract.
Literal substring membership does not establish support for the claimed fact.
The strict backend metrics above remain 0/20 accepted responses, 0/17 accepted
positive answers, 0/3 valid negative refusals, 20/20 schema-invalid outputs and
0/28 delivered required-evidence coverage.

The principal reviewed error classes are wrong document/entity variant, wrong
table value or column, numeric reasoning failure, failure to refuse when the
requested information is absent, incorrect quote or answer offsets, and an
inconsistent answer/reason contract. Case-level verdicts, questions, answers and
evidence stay private. Held-out results were used only for reporting, never tuning.

Original corpus documents were **not independently reopened** during the
AI-assisted review. Judgments use frozen reviewed Gold and the captured retrieval
context. The operator confirmation is not a formal OutputReview label: such
labels require an actual delivered RagOutcome, which none of these rejected
outputs produced. No formal OutputReview records or fabricated accepted outcomes
were created. The retained replay packets are unchanged; their original
NOT_EVALUATED fields are not silently relabeled. The separate audit is the source
of the confirmed diagnostic raw-output findings.

The private sign-off is stored under the ignored repeat directory in
`review-signoff-audit-c91af4cbecd84f799b87297af330eebc/operator-review-signoff.json`.
It binds each case to both captures, raw-content hashes, approved Gold and
experiment identity, original assessment hash, and explicit operator-confirmation
provenance. It contains no invented reviewer identity.

## Category and dev/test aggregates

Every group has zero accepted answers and zero valid refusals in both runs. The
following table reports actual repeat latency; invalid-count denominators are the
number of cases in each group. Groups were used only for scoring, never tuning.

| Group | Cases | Run 1 schema-invalid | Run 2 schema-invalid | Repeat P50 / P95 ms |
| --- | ---: | ---: | ---: | ---: |
| dev | 15 | 15/15 | 15/15 | 4124.390 / 13275.728 |
| test | 5 | 5/5 | 5/5 | 4058.037 / 9435.144 |
| fact | 2 | 2/2 | 2/2 | 3526.637 / 3688.498 |
| identifier | 3 | 3/3 | 3/3 | 5506.278 / 22491.565 |
| number | 6 | 6/6 | 6/6 | 3814.348 / 9050.261 |
| table | 4 | 4/4 | 4/4 | 5491.985 / 8135.053 |
| unanswerable | 3 | 3/3 | 3/3 | 4037.672 / 6616.344 |
| version | 2 | 2/2 | 2/2 | 4542.851 / 4919.465 |

Generation P50/P95 was **4,278.103 / 11,935.580 ms** in run 1 and
**4,091.214 / 11,232.168 ms** in run 2. Both use all 20 sequential requests,
including the first request; startup is excluded and no warm-up is discarded.
Percentiles use linear interpolation at (n-1)*p. The latency difference is an
observation, not a demonstrated performance improvement. Frozen retrieval latency
was measured separately at P50/P95 133.062 / 191.123 ms.

| Sampled resource | First run | Repeat |
| --- | ---: | ---: |
| Server-tree RSS peak, bytes | 9,682,350,080 | 9,679,642,624 |
| Primary GPU-used peak, MiB | 3,731 | 3,731 |
| Successful / failed resource samples | 682 / 0 | 670 / 0 |

Sampling was approximately every 0.2 seconds and may miss peaks. Both runs used
CUDA0/Tesla T4; the second visible T4 was unused. Resource observations are not SLA
or throughput guarantees.

## Frozen identities and privacy

- Private kernel: `nurs2005/doclens-rag-real-baseline`, versions 1 and 2.
- Private input: `nurs2005/doclens-rag-real-8229d0d088/2`, dataset ID 12637152.
- Model/runtime input: `nurs2005/doclens-qwen3-q8-llama-b11617/1`.
- Input SHA-256:
  `ccee3559dab595a68f836625b3669fa5c9e2c5b0b884f08f97227a03e6fa6260`.
- Retrieval-context fingerprint:
  `d60f17ce234ea44ec839638ce8f93bc3bc26073a7bb11d90877481b175d0c62d`.
- Production prompt grounded-qa-v1 SHA-256:
  `33622b5889415d5ec23df5995dfa647d4d8b0b3369838f03934b355be052ec89`.
- Model Qwen/Qwen3-1.7B-GGUF, Q8_0, revision
  `90862c4b9d2787eaed51d12237eafdfe7c5f6077`, SHA-256
  `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`.
- llama.cpp b11617 commit `14310190cd0a0c831fe949ac8cbedd8abdc90695`, archive
  SHA-256 `1c5024dfa587a3f23ef8fc066cb2578fb43d661910d4111a8941184773c237d1`;
  executable SHA-256
  `88f69b22b3b109328e12109ee05ed4e32bf870c92c56c34479be7e1e9e0bce62`.
- First submitted source SHA-256:
  `e7dcf1dc2996b6ed228b614fb5a443f86d669f33a5fca7080dc1dce3e64ff4ff`.
- Repeat source SHA-256:
  `510f3ddf3b5558754a0a2ce31c6da7951e88d49907dcca78c6394b509fca0841`.
- Approved Gold fingerprint:
  `66e84c335da8c6fd51468bed623e24ed7dc276e8dfc051f2a0261274105f00ee`.
- Unchanged configuration fingerprint:
  `6f3b7c0bef6bce4841f27b21af28cdde8c101329f2cc6802b3820e9f86802fb7`.
- First capture SHA-256:
  `7ca8b8509bb865fe59d34f36cfb97f6343b355e8d774ae1730a6a3b3213d6b96`.
- Repeat capture SHA-256:
  `90a01c4166f2e079877d1afafe4ba0a3bff2f527506fcf67ec56b921e6d4b2df`.
- Repeat original server-log SHA-256:
  `59795419fb64eb1e6a7428af8b3f6e2e200317a2e568bc84d0fb05da064ffa93`.

There are 20 original questions, 20 nonempty contexts and 110 packed chunks.
Authenticated metadata verified the existing datasets private and owner-only,
with zero collaborators and exact version identities. The input file allowlist
contains only the candidate. The repeat made no dataset uploads. Kernel private
visibility, internet disabled, T4, exact two-source allowlist and source SHA were
verified remotely during the pre-inference hold. Dataset version suffixes are
retained in submitted metadata; pulled Kaggle metadata omits these suffixes, so
actual input/model hashes also bind the mounted bytes. No credentials, Gold
reference answers, evidence labels, full corpus or replay manifest reached Kaggle.
The source contains no private questions/evidence. Sensitive runtime logs and all
raw captures remain local and Git-ignored after download.

## Private review and reproduction

The immutable first-run artifacts remain under
`evaluation-output/rag-real-kaggle-8f93bb53b0fb415aa6ba751f3b54dbea/`.
New artifacts are under
`evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/`:
`first-run/taxonomy.json`, `taxonomy.json`, per-case forensics, `gpu-provenance.json`,
`comparison.json`, `metrics.json`, `human-output-review.json`, captured responses,
original runtime log, frozen identities and preservation hashes.
Both original and repeat review packets retain original questions, unrepaired
outputs, cited/packed evidence, local Gold references and Gold/experiment/output
fingerprints. Rejected-output fingerprints bind raw captures, not invented answers.
No formal OutputReview approvals were generated. The operator-confirmed
AI-assisted raw-output review is recorded in the separate sign-off audit above;
it is not an independent manual production-quality review.

The installed Kaggle CLI/SDK is 2.2.4. Repository code, pinned runtime flags, the
installed API and actual runtime logs supplied the evidence; no new external API
or library behavior was assumed. The DocLens RAG evaluation skill guided strict
stage separation, fixed conditions and limits on quality claims.

Executed commands from the repository root:

```powershell
.venv/Scripts/python.exe evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/forensics.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_kaggle_rag_baseline.py::test_offload_gate_keeps_verified_server_logging
kaggle kernels pull nurs2005/doclens-rag-real-baseline -p evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/remote-before --metadata
kaggle kernels push -p tools/kaggle_gpu/rag_baseline --accelerator NvidiaTeslaT4
kaggle kernels pull nurs2005/doclens-rag-real-baseline -p evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/remote-kernel --metadata
kaggle kernels status nurs2005/doclens-rag-real-baseline
kaggle kernels output nurs2005/doclens-rag-real-baseline -p evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/capture --file-pattern '^(rag_capture\.json|llama-server\.log)$' --quiet
.venv/Scripts/python.exe evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/verify_repeat.py
.venv/Scripts/python.exe evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/forensics.py --repeat
.venv/Scripts/python.exe evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/compare.py
$env:DOCLENS_RAG_REAL_RUN = 'C:\Users\nurs\doclens_ai\evaluation-output\rag-real-repeat-c0b5539a72f54e66b479c65dffed4545'
$env:DOCLENS_RAG_REAL_EXPECT_STATUS = 'complete'
.venv/Scripts/python.exe -m pytest -q -s -p no:cacheprovider tests/integration/test_kaggle_rag_baseline.py tests/unit/test_kaggle_rag_baseline.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
.venv/Scripts/python.exe -m ruff check src tests alembic tools/kaggle_gpu
git diff --check
git status --short
```

Forensic replay, source/input/configuration verification, submission, download and
final explicit-offload verification returned exit 0. Final remote status is
COMPLETE for version 2, ERROR for preserved version 1. The initial one-offload-line
local assertion failed and was corrected as documented above; it did not trigger
another inference submission. Detailed verification records remain private.
The inference/repeat stages prohibited commits. The subsequent finalization task
explicitly authorizes one commit containing only the five ML-6 implementation,
test and report files. Private captures, Gold, input, logs and sign-off audit are
excluded.


Repeat-stage verification results (before finalization):

- Original 20-output forensic replay: exit 0, 20 schema rejections, exclusive
  primary taxonomy 15 answer/reason failures and 5 nested citation failures.
- GPU logging regression: 1 passed in 0.62 s before submission.
- Complete repeat replay and focused GPU provenance regressions: **29 passed in
  1.28 s**, exit 0; no opt-in skips in this run.
- Full unit suite: **585 passed, 1 skipped in 28.79 s**, exit 0. The skip is the
  pre-existing Windows symlink-privilege test.
- Ruff over `src tests alembic tools/kaggle_gpu`: all checks passed, exit 0.
- Privacy/public-report audit and unchanged-original hash verification: passed;
  30 preserved original files and all new private outputs checked.
- `git diff --check`: passed. `git status --short` still contains only the permitted
  untracked report, two tests and rag_baseline directory from this uncommitted step.
  Nothing was staged or committed.


## Finalization boundary and verification

The failed baseline is retained for reproducible diagnosis; production remains
REJECT. Architectural limitations remain: the benchmark is staged offline replay
rather than live API E2E execution, authorization is a frozen retrieval snapshot
rather than continuous PostgreSQL revalidation, structural references are not
semantic support, and the sample is a small English-only reviewed set. Existing
extraction eligibility excludes part of Corpus v1; this evaluation does not
change those gates or generalize to other languages or document populations.
No production component, prompt, retrieval setting, Gold record or validator was
modified. No inference or Kaggle upload occurred during finalization.

A focused replay regression now verifies existing metric/review files instead of
overwriting them. Identical existing JSON is read-only; a mismatch fails without
writing, while a genuinely new packet can still be created. This preserves the
private read-only sources during the required opt-in replay.

Finalization commands and outcomes are recorded privately in the sign-off audit.
The audit validator binds the operator-confirmed findings without constructing
OutputReview or RagOutcome objects from rejected raw outputs.


Finalization verification executed successfully:

```powershell
.venv/Scripts/python.exe evaluation-output/rag-real-repeat-c0b5539a72f54e66b479c65dffed4545/review-signoff-audit-c91af4cbecd84f799b87297af330eebc/validate_signoff.py
$env:DOCLENS_RAG_REAL_RUN = 'C:\Users\nurs\doclens_ai\evaluation-output\rag-real-repeat-c0b5539a72f54e66b479c65dffed4545'
$env:DOCLENS_RAG_REAL_EXPECT_STATUS = 'complete'
.venv/Scripts/python.exe -m pytest -q -s -p no:cacheprovider tests/unit/test_kaggle_rag_baseline.py tests/integration/test_kaggle_rag_baseline.py
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
.venv/Scripts/python.exe -m ruff check src tests alembic tools/kaggle_gpu
git diff --check
git diff --cached --check
```

The audit verifies all 20 sign-off bindings and 58 preserved source/artifact
hashes. Focused tests plus actual opt-in replay: **32 passed in 2.86 s**.
Full unit suite: **588 passed, 1 skipped in 16.50 s**; the skip is the existing
Windows symlink-privilege test. Ruff and whitespace checks passed. Private
inputs/captures, Gold, logs, model artifacts and sign-off audit remain excluded
from the explicitly allowlisted five-file commit. The final commit subject is
`test: freeze ML-6 real RAG contract failure baseline`.
