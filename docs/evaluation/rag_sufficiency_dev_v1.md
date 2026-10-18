# ML-14 paired DEV evidence-sufficiency experiment

EXPERIMENT_EXECUTION: PASS
MODEL_CONTRACT_QUALITY: REJECT
SEMANTIC_CORRECTNESS: NOT_EVALUATED
PREREGISTERED_DECISION: INCONCLUSIVE
PRODUCTION_AUTHORIZATION: false

The original private Kaggle versions 1 and 2 both completed and their original
captures passed mandatory genuine replay. Version 2 was recovered on 18 October
2026; no cancellation, replacement, third CLI version, model request retry or
output repair was needed. This is experiment execution PASS only. Reliable
insufficient-evidence refusal was not demonstrated; production is not authorized.

## Registered question and frozen protocol

Base HEAD: `20d0ca09416925cb82c2ca0aced145164b7b52c6`.
Registered before inference at `2026-10-17T18:24:55.250552+00:00`.
Measure whether deleting one necessary evidence span changes Qwen3-4B from a
strict accepted answer to a valid insufficient-evidence refusal. Twelve NEW
synthetic DEV pairs, 24 requests per repetition, two unchanged serial repetitions.
Two pairs per numbers/units, table relations, negation, versions/conflicts, wrong
entities and prompt injection; four pairs each EN/RU/KK.

Each pair retains the same question and synthetic evidence identities/locator
metadata. A is sufficient; B removes exactly one registered contiguous necessary
span. For negation, the whole decision is removed, rather than creating a positive
assertion by deleting only a negative particle. Conflict cases remove the rule
selecting the governing source. Distractor entities/instructions remain in B.
Synthetic locator metadata describes the original authored source block; citation
offsets are checked against the context view actually supplied. These are
mechanics fixtures, not real-document provenance or live authorization tests.

Seed 42 shuffles pairs; six are AB and six BA. Both runs use the same order.
Labels are synthetic fixture/zero reviewers, outside inference messages. No Gold,
TEST, private corpus, expected answer or reference JSON was used to construct
model requests. No human review is claimed. This paired-ablation fixture is not
a reviewed rag-gold-1.0 answer dataset; semantic scoring remains NOT_EVALUATED.

Production SYSTEM_PROMPT and post-validation are unchanged. Replay uses
LocalGenerator -> strict_json -> ModelAnswer -> validate_citations. Invalid
JSON/schema/citations and request failures remain failures, never valid refusals.
The preregistered decision rule remains: any unsafe accepted negative forces
REJECT; otherwise INCONCLUSIVE without independent semantic review. This saved
candidate_quality field is separate from the measured contract verdict below.
No post-hoc threshold or label change.

## Frozen identities

| Item | Pin / SHA-256 |
|---|---|
| Runner, both remote sources | fe12d6881f3c6d668e265006dc5438ea93d957ecf693877648811d0ebcbe9027 |
| Immutable preregistration JSON | da98de15692738791232c57ed5cabebcca624ac6c2a4856e63c9da5d0005baf5 |
| Cases | 7808455f8a04d9eba371665ff09e5ea942b818574fcf30e96c017696f7553f1a |
| Labels | acd1fc33532015e3b949e76c6806e9541e5411d3d2245fcfb3bbf6b299c2c995 |
| Configuration | 90de06de95ef3f7bf040a18024141aae669975519a72abaaa718a287dbfff0b3 |
| SYSTEM_PROMPT | 33622b5889415d5ec23df5995dfa647d4d8b0b3369838f03934b355be052ec89 |
| Model repository/revision | Qwen/Qwen3-4B-GGUF / bc640142c66e1fdd12af0bd68f40445458f3869b |
| Qwen3-4B-Q8_0.gguf, 4280404704 bytes | 8c2f07f26af9747e41988551106f149b03eb9b5cb6df636027b6bf6278473300 |
| llama.cpp | b11617 / 14310190cd0a0c831fe949ac8cbedd8abdc90695 |
| Runtime archive, 171623026 bytes | 1c5024dfa587a3f23ef8fc066cb2578fb43d661910d4111a8941184773c237d1 |
| llama-server binary | 88f69b22b3b109328e12109ee05ed4e32bf870c92c56c34479be7e1e9e0bce62 |
| Version-1 submitted metadata | 0aafd29b4313f5cdb27e2cfb6b16a7d88e0f711837475575a0c4104b105504c7 |
| Version-2/current metadata | b02e48f7d6c658c75aec19c61aac2b8cbad9f12a963fb33e1b664a09879a63c0 |

Kaggle image:
`gcr.io/kaggle-private-byod/python@sha256:2757e0c7d1e0a9cb43da657b97e223c321a98f5014bdf64f44f2f6b083ad2b2f`.
Both metadata/provenance records verify private=true, internet=false and T4.
Generation is json_object, temperature 0, seed 42, max output 1024, context 16384,
one slot, four CPU threads, reasoning off, no context shift; CUDA0 only, full
offload, no CPU fallback. Requests have a 120s deadline/65536-byte cap; kernel
limit 3600s; startup/readiness limit 180s. Response retries/output repairs: zero.

All preregistered post-validator file hashes still match; replay uses pydantic
2.14.0 and httpx 0.28.1. No runtime, prompt, label, extraction, retrieval or model
configuration was retuned after observing responses.

## Authenticated recovery and input access

Actual kernel: `nurs2005/doclens-ml14-paired-sufficiency-dev`, numeric ID
139278943. Genuine versions are **1 and 2**, both COMPLETE. The initial status
query in this completion step already returned COMPLETE for version 2; all 24
capture events were present in its logs. Cancellation/quota investigation and
replacement branches were therefore unnecessary and were not invoked.

Installed Kaggle CLI 2.2.4 authentication succeeded. Supported SDK
get_dataset and dataset_list_files calls verified both existing private inputs:

| Requested dataset | Version status | Expected artifact verified by versioned file list |
|---|---|---|
| nurs2005/doclens-qwen3-q8-llama-b11617/1 | version 1 Ready, private | llama-b11617-bin-ubuntu-cuda-12.8-x64.tar.gz.bin, 171623026 bytes |
| nurs2005/doclens-qwen3-4b-q8-ml7/2 | version 2 Ready, private | Qwen3-4B-Q8_0.gguf, 4280404704 bytes |

The runtime dataset has five files, including its existing unused 1.7B GGUF,
license texts and provenance; the model dataset has three files. The runner
loaded the pinned **4B** artifact: both GPU reports independently verify its SHA
and size, archive SHA/size and executable SHA. Dataset access did not download or
reupload weights, replace revisions or expose credentials. The kernel read API
returns dataset slugs without version suffixes; exact requested versions are
preserved in submitted metadata and checked through versioned dataset file APIs.

Version-2 COMPLETE proof was observed at
`2026-10-18T03:28:46.051791+00:00` (18 October 08:28:46 +05:00).
Its remote source matches the frozen local source byte-for-byte. Downloaded
outputs are original HTTP envelopes and logs, not reconstructed model outputs.
No Jupyter benchmark or replacement was executed. Earlier Jupyter CUDA preflight
and missing-mount diagnostics are historical diagnostics only, not repetitions.

## Original capture and output fingerprints

All captures and operational records remain under ignored
`tools/kaggle_gpu/outputs/ml14-paired-sufficiency-v1/`.

| Artifact | Version 1 SHA-256 | Version 2 SHA-256 |
|---|---|---|
| capture/rag_capture.json | 05783f58337f89dcecce2655573743319c7a7402a0a55d7ba186034517abb8b6 | 77ab7aa9702be509a8cceae674f59095e4e04907f9cfddb2938cc49da540ff49 |
| capture/llama-server.log | 20d59c5f56a39c3889da8ddaee1eda9638beaac54ecbc5b340327b1aba4ac7de | f0e9f99b238fe400a7e83f8d743d3c59116e595a25d2e1701ed1626b7ec5fee4 |
| capture/doclens-ml14-paired-sufficiency-dev.log | 24aaf3496b2303d5a707f9b3d298afce54c00cfced6ba7e215d1582d3f61ae3e | 167909b2c0a7796fea8f5229d386655506854b8bf631691b91b9b498cf61ef6b |
| provenance.json | 9c805fa901591393c6477134dc927f72763e0de3bfcb5ea2f74132a6b3c801e1 | 154a8c543722b5623f92109a76b5aa623a8d28e1271a845baf5e77e7f6297200 |
| Response collection fingerprint | 44a73f1ebc03a11f3efe27814abbdb8cf63c71b8f7b371ed2313e86797762e9b | fded4ade2e366c6b7c515f3fec614ce69265fa67d064f789ace35229cfdf30f1 |
| Case-level rows.json | 69baa79426e8cf464455646a37eaa1f0a4e7de78c1c4d0304831991eec9b99f6 | 8c9cecc9e095ccc82cf0206a90857f73620998cf9df80aa035230cda32690941 |

Deterministic comparison.json:
`365799878a06d7d2bd4294522563d0ffbcae2cdb9d5e24b43163075a05a06b49`.
Dataset-access verification:
`a322443caf015e52ba132f45d82e8c3a859d257d7a04fd8c7176e2de0863b0ad`.
The original blocked report was preserved byte-for-byte as
report-before-completion.md, SHA
`f5bd9d1d90163520da7e9cb26a2f72c0ef02c1a8f1e4550abbe5e8e92422db6e`.
All 11 original run-1 files and all frozen source/test/metadata files are unchanged.

## Both-run metrics

Each repetition has 24 planned, attempted and captured requests: 12 sufficient
A and 12 insufficient B. All failures remain in denominators. There are 48 actual
attempts overall; repetitions are not pooled as 48 independent documents.

| Metric | Run 1 | Run 2 |
|---|---:|---:|
| Planned / attempted / captured | 24 / 24 / 24 | 24 / 24 / 24 |
| Strict accepted sufficient / 12 | 0 | 0 |
| Valid insufficient-evidence refusal / 12 | 0 | 0 |
| Unsafe strict accepted negative / 12 | 0 | 0 |
| False refusal on sufficient / 12 | 0 | 0 |
| Invalid JSON / 24 | 0 | 0 |
| Invalid schema / 24 | 4 | 4 |
| Invalid citation / 24 | 20 | 20 |
| Request failure / 24 | 0 | 0 |
| Raw affirmative negative / 12 | 12 | 12 |
| Strict successful pairs / 12 | 0 | 0 |

Raw affirmative is the diagnostic strict-parseable answerable=true flag, not
reviewed factual correctness. All 24 A/B responses in each run have that flag.
No invalid response is counted as a refusal or accepted answer.

Each category has four attempts (two A + two B); counts below apply independently
to **each** repetition. Other strict outcome counters are zero in every category.

| Category | Invalid schema / 4 | Invalid citation / 4 | Raw affirmative B / 2 |
|---|---:|---:|---:|
| numbers/units | 1 | 3 | 2 |
| table relations | 1 | 3 | 2 |
| negation | 0 | 4 | 2 |
| versions/conflicts | 2 | 2 | 2 |
| wrong entities | 0 | 4 | 2 |
| injection | 0 | 4 | 2 |

Each language has eight attempts (four A + four B) per repetition:
EN = two schema/six citation failures; RU = two/six; KK = zero/eight.
A contains one schema and 11 citation failures; B three schema and nine citation
failures, identically in both runs. All four schema failures concern the reason
literal; the other 20 responses first fail unsupported evidence reference.
Nonexclusive mechanical flags per run: 18 quote-slice mismatches, 18 answer bounds
violations, five quote bounds violations. No semantic cause is inferred from these.

## Repetition agreement, GPU and resources

Agreement: **24/24 outcome statuses** and **24/24 exact model-content strings**.
All 24 raw HTTP envelopes differ only at root keys id, created and timings.
Both original envelopes are preserved; variable metadata is not a semantic change.
Repeatability over these two fixed runs does not establish general reliability.

| Measurement | Run 1 | Run 2 |
|---|---:|---:|
| Inference start, UTC 17 October | 18:32:32.923189 | 20:31:09.738317 |
| Finished, UTC 17 October | 18:34:22.010853 | 20:33:01.544362 |
| Server startup/readiness, seconds | 44.7204 | 43.2560 |
| Request P50, seconds | 3.3357 | 3.7237 |
| Request P95, seconds | 5.1152 | 5.1772 |
| Maximum/first request, seconds | 26.4815 | 25.2586 |
| Sum request latency, seconds | 108.7347 | 111.4423 |
| Sampled CUDA0 peak VRAM, MiB | 6603 | 6603 |
| Sampled server-tree peak RSS, bytes | 4616491008 | 4616462336 |
| Successful / failed resource samples | 653 / 0 | 661 / 0 |
| Nonzero CUDA0 model buffer, MiB | 4076.43 | 4076.43 |
| Every layer-offload log event | 37/37 | 37/37 |

Both runs: two Tesla T4 devices, 15360 MiB each, driver 580.178.04; only CUDA0 used,
no pooled VRAM claim. Both load events log 37/37: an initial zero-size dry load
and the real 4076.43 MiB CUDA0 model buffer. CUDA libraries resolve, CUDA0 is
enumerated, pinned model inference completes, and GPU allocation is measured.
This is actual CUDA offload/inference evidence, not only a GPU-name check.

Python 3.13.15, httpx 0.28.1, psutil 5.9.5, runtime commit, server flags, model,
prompt and request settings match exactly across captures. Resource samples wait
0.2s plus collection overhead; peaks may miss transients. RSS covers the server
process tree, excluding benchmark Python/input hashing; device used memory includes
baseline/context allocations. Startup excludes the initial 120s verification
hold and input verification/extraction. First slow requests remain in latency
statistics. Run 2 starts after run 1 finishes; no duplicate concurrent run.

## Quality verdict and uncertainty

MODEL CONTRACT QUALITY is **REJECT**: all 24 responses in each repetition fail
the strict contract, with 0/12 accepted sufficient answers, 0/12 valid
insufficient-evidence refusals and 0/12 successful pairs. This describes the
observed contract failure; it does not replace the preregistered decision rule.
The unchanged replay field candidate_quality remains **INCONCLUSIVE** under
that rule: no unsafe accepted negative and no independent semantic review.
SEMANTIC CORRECTNESS remains **NOT_EVALUATED**.
Zero unsafe *accepted* answers does not mean model safety: all raw negative
affirmatives were blocked by schema/citation gates. Structural rejection is not
evidence that the model recognized insufficiency.

Semantic correctness, citation entailment, unsupported-claim rate, real-corpus
performance, retrieval quality, live authorization and production readiness are
NOT_EVALUATED. Existing rejected candidates are not reinstated. No promotion.
For each run, 0/12 valid refusals or unsafe accepted negatives has descriptive
Wilson 95% interval approximately [0%,24.25%]; 12/12 raw affirmative negatives
has [75.75%,100%]. This small purposive DEV fixture is not a population sample
or sealed test; repetitions are not independent document families.

## Executed verification and recovery commands

PowerShell at repository root, installed Kaggle CLI 2.2.4. Network and local
asyncio tests used the authorized execution mode outside Windows socket
restrictions. No dependency was added and no sensitive input was uploaded.

```powershell
kaggle --version
kaggle kernels status nurs2005/doclens-ml14-paired-sufficiency-dev/2
kaggle kernels logs nurs2005/doclens-ml14-paired-sufficiency-dev/2
kaggle kernels output nurs2005/doclens-ml14-paired-sufficiency-dev/2 -p tools/kaggle_gpu/outputs/ml14-paired-sufficiency-v1/run-2/capture --file-pattern '(rag_capture\.json|llama-server\.log)$'
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'
$env:DOCLENS_RAG_SUFFICIENCY_REPLAY='1'
.venv/Scripts/python.exe -B -m pytest -q -s -p no:cacheprovider tests/integration/test_kaggle_rag_sufficiency_dev.py
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_kaggle_rag_sufficiency_dev.py tests/unit/test_rag.py tests/unit/test_rag_gold.py tests/unit/test_rag_quote_binding.py tests/unit/test_kaggle_rag_schema_dev.py
.venv/Scripts/python.exe -B tools/kaggle_gpu/outputs/ml14-paired-sufficiency-v1/evaluate_run.py 2
.venv/Scripts/python.exe -B tools/kaggle_gpu/outputs/ml14-paired-sufficiency-v1/diagnose_capture.py 2
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/integration/test_kaggle_rag_sufficiency_dev.py
.venv/Scripts/python.exe -m ruff check tools/kaggle_gpu/rag_sufficiency_dev/benchmark.py tests/unit/test_kaggle_rag_sufficiency_dev.py tests/integration/test_kaggle_rag_sufficiency_dev.py
.venv/Scripts/python.exe -m ruff format --check tools/kaggle_gpu/rag_sufficiency_dev/benchmark.py tests/unit/test_kaggle_rag_sufficiency_dev.py tests/integration/test_kaggle_rag_sufficiency_dev.py
git diff --check
git status --short --untracked-files=all
```

Actual outputs: version-2 status COMPLETE; logs contain 24 capture events;
download returns rag_capture.json, llama-server.log and the automatically
accompanying Kaggle kernel log. No extracted runtime directory was downloaded.
Mandatory genuine replay: **1 passed in 0.70s**. Unit/RAG regressions:
**203 passed in 1.74s**. No tests skipped or failed in these current invocations.
Replay repeated against the already-existing comparison record: **1 passed in
0.53s**, with the same comparison SHA and metrics; no inference was reissued.
Ruff: **All checks passed!** Format: **3 files already formatted**.
git diff --check exits 0, with no output; untracked report whitespace and full
report-only diff are also checked, since ordinary git diff excludes new files.

The existing remote_control.py was executed with arguments `2 proof` through
the installed Kaggle-CLI host Python to preserve exact API metadata/source and
COMPLETE status. Dataset checks used KaggleApi.authenticate(), ApiGetDatasetRequest,
get_dataset() and dataset_list_files(ref,page_size=100), with explicit versioned
refs, size/status/private assertions and no paging/error remainder. These are
read-only supported SDK operations; credentials and private local interpreter
locations are omitted from this sanitized report. GPU logs contain platform
nbconvert SyntaxWarnings after inference; they did not fail the benchmark/replay
and no unrelated platform package was changed.

## History, privacy and Git review

Before ML-14, the five untracked filenames contained an incompatible older ML-10
classifier protocol with 19 cases. Byte-for-byte originals and original_inventory
remain ignored and preserved. Initial source/style checks and a mistyped image
digest were corrected before preregistration/inference; the initial failing test
was rerun successfully. No candidate tuning followed model observations.
The first submission's title generated the actual slug; only metadata.id was
corrected before version 2. The two submitted metadata hashes differ accordingly;
all benchmark source/configuration/cases remained unchanged.

Earlier BLOCKED reports accurately described missing run-2 captures while queued.
The original job subsequently completed; its cause of queue delay remains UNKNOWN.
Earlier Jupyter preflight had CUDA but no inputs and never ran Qwen. It is not
used as benchmark evidence. These historical reports/diagnostics are retained
in ignored storage; they are superseded by the recovered original version 2.
No operator was asked to attach inputs or execute a cell in this completion step.

Only approved synthetic source/code was originally staged; the two-file stage
contains benchmark.py and kernel-metadata.json. No repository root, credentials,
Gold/TEST, private documents, raw outputs or weights enter Git. Captures, input
metadata, per-case hashes, original snapshots and resource/API proofs remain
ignored. Privacy pattern checks complement manual full-diff review; they are
not a general secret-detection guarantee. No production code, retrieval, parser,
Gold, split, model, config, validator or test file was changed in this recovery.

Recovery checkpoint before final pre-commit review: branch `main`; HEAD
`20d0ca09416925cb82c2ca0aced145164b7b52c6`.
Only this report changed among the five pre-existing untracked project paths;
tracked/staged diffs are empty. Original run-1 files remain byte-identical.
No stage, commit or push had occurred at that recovery checkpoint. The final
pre-commit review is separately authorized to stage exactly these five files and
make one commit after all checks pass; no push is authorized.

```text
?? docs/evaluation/rag_sufficiency_dev_v1.md
?? tests/integration/test_kaggle_rag_sufficiency_dev.py
?? tests/unit/test_kaggle_rag_sufficiency_dev.py
?? tools/kaggle_gpu/rag_sufficiency_dev/benchmark.py
?? tools/kaggle_gpu/rag_sufficiency_dev/kernel-metadata.json
```

## Final pre-commit review, 18 October 2026

Reviewed all five ML-14 files against the frozen protocol and original captures.
No implementation defect requiring a code change was identified. Only report
terminology was corrected: execution PASS, measured contract REJECT, semantic
correctness NOT_EVALUATED. The preregistered decision rule, replay's
candidate_quality=INCONCLUSIVE, labels, configuration and raw outputs are unchanged.

Independent read-only re-evaluation matched both saved metrics.json files,
rows.json files, comparison.json and the report's metrics/latency tables. All 22
files under run-1/run-2 stayed byte-identical during review; all 11 original run-1
hashes and the three original run-2 capture hashes also match the earlier inventory.
Both runs retain 24/24 captures, 37/37 offload events, a nonzero 4076.43 MiB CUDA0
model buffer and 6603 MiB sampled peak VRAM. Content/status agreement is 24/24;
only root envelope id/created/timings differ. No inference or remote job was run.

The focused unit/RAG command above passed again: **203 passed in 2.03s**.
The genuine opt-in replay command above passed again: **1 passed in 0.64s**.
Ruff again reported **All checks passed!**; formatting **3 files already formatted**.
Default opt-out behavior was checked separately:

```powershell
Remove-Item Env:DOCLENS_RAG_SUFFICIENCY_REPLAY -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -B -m pytest -q -rs -p no:cacheprovider tests/integration/test_kaggle_rag_sufficiency_dev.py
git branch --show-current
git rev-parse HEAD
git rev-list --left-right --count 'HEAD...@{upstream}'
git ls-remote origin refs/heads/main
```

Default replay: **1 skipped in 0.05s**, explicit genuine-capture opt-in required.
No failing tests in this review. Pre-commit branch main/HEAD matches the base HEAD
above; upstream origin/main is 003df041411ff48c8a6ba562d563c5a88ab6a9ca, confirmed
by read-only ls-remote; pre-commit divergence is ahead 1 / behind 0. No history
reset, force-push or remote write. This authorization permits one five-file
Conventional Commit after full staged-diff, whitespace, privacy and scope checks.
Small synthetic DEV coverage and absent independent semantic review remain
limitations; no model or production promotion follows this commit.

Full staged-diff review covers exactly the five approved text files. The staged
bytes equal the reviewed working files; no unrelated changes, raw captures,
weights or private corpus enter the index. All 50 existing runtime artifacts
remain ignored. Secret-pattern/private-path checks found no matches;
git diff --cached --check exits 0. These checks complement manual review.
Git emitted LF-to-CRLF checkout warnings; current index/source bytes retain the
frozen LF hashes. Future replay must preserve the registered source bytes;
line-ending changes correctly fail the exact-byte provenance checks.

Sources: repository runner/tests, original frozen protocols and actual captures;
[GPU-01](https://www.kaggle.com/docs/notebooks),
[GPU-02](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md),
[RAG-04](https://docs.pydantic.dev/latest/concepts/json/).
Installed CLI/SDK 2.2.4 and executed pinned validators establish actual behavior;
external guidance does not override the frozen experiment. The external GOAL,
QUALITY-GATES QG-07/QG-08, TRUTHFUL-LLM and EVALUATION definitions remain UNAVAILABLE;
no absent policy definition is invented or described as passed.
