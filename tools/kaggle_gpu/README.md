# Kaggle GPU smoke

Uses the existing authenticated Kaggle CLI 2.2.4 account. This is batch remote
execution, not SSH: edit Python locally, submit a private kernel version, then
inspect logs and download outputs. No training, project documents, datasets,
model weights or credentials are uploaded by the CUDA smoke. The separate LLM
experiment below stages verified public weights only. Kaggle's preinstalled PyTorch is used;
internet is disabled. Metadata selects T4 x2 through `machine_shape`, and the
launcher also passes `--accelerator NvidiaTeslaT4`.

From the project root:

```powershell
.\tools\kaggle_gpu\run.ps1
kaggle kernels status nurs2005/doclens-gpu-smoke
kaggle kernels logs nurs2005/doclens-gpu-smoke
kaggle kernels logs nurs2005/doclens-gpu-smoke --follow
kaggle kernels output nurs2005/doclens-gpu-smoke -p tools/kaggle_gpu/outputs
```

The launcher uses `$PSScriptRoot`, so it also works from any directory when invoked
by its full path. Each submission after editing `gpu_smoke.py` creates a new remote
kernel version. Submission success does not prove execution success: wait for
`complete`, inspect logs, and verify `outputs/gpu_smoke.json` has `status: passed`,
`cuda_available: true`, `computation.device: cuda:0` and `computation.valid: true`.
Compare `source_sha256` and the UTC execution timestamps to the submitted run to
reject stale results.
Source hashes refer to uploaded UTF-8 code with LF newlines: CLI text reads
normalize Windows CRLF before sending it. Use that normalization when comparing.
Avoid overlapping submissions: CLI 2.2.4's one-shot logs
fetch the latest session even if a version suffix is supplied. Use the owner/slug
commands above for this workflow, and retain the version number printed by push.
Use owner/slug without a version suffix for live `--follow` too: the version-suffixed
stream URL returned HTTP 404 with this CLI, while the commands above worked.

The script lists all visible GPU names and VRAM, but computes only on `cuda:0`.
It checks every value of a synthetic 1024 x 1024 float32 matrix product against
1024. Timing is one warm sample with CUDA synchronization, excluding allocation,
warmup and result validation; it is not a representative performance benchmark.
CUDA absence or computation failure produces a nonzero exit. Downloaded outputs
are ignored by the local `.gitignore`; never put credentials in this folder.

## Offline Qwen3 generation experiment

The separate private kernel is `nurs2005/doclens-llm-smoke`; it must never replace
`doclens-gpu-smoke`. This is synthetic generation/contract compatibility, not
production end-to-end RAG, authorized retrieval, or human-reviewed answer quality.
Human-reviewed RAG quality, retrieval recall and semantic faithfulness are
`NOT_EVALUATED`. The RAG evaluation Skill requires fixed cases and explicit limits;
no quality improvement is inferred from this smoke.

Pinned public artifacts (original license texts retained):

| Artifact | Pin | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Qwen3-1.7B Q8_0 GGUF | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` | 1834426016 | `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a` |
| llama.cpp Ubuntu CUDA 12.8 archive | `b11617`, commit `14310190cd0a0c831fe949ac8cbedd8abdc90695` | 171623026 | `1c5024dfa587a3f23ef8fc066cb2578fb43d661910d4111a8941184773c237d1` |

The model is [Apache-2.0](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/blob/90862c4b9d2787eaed51d12237eafdfe7c5f6077/LICENSE);
the runtime is [MIT](https://github.com/ggml-org/llama.cpp/blob/b11617/LICENSE).
Runtime settings follow the [pinned server documentation](https://github.com/ggml-org/llama.cpp/blob/b11617/tools/server/README.md).
`--reasoning off` disables thinking without editing the production prompt.
No CUDA libraries are redistributed: the runtime uses Kaggle's installed libraries.
Primary public downloads total 2006049042 bytes (1.868 GiB), below the 3 GiB budget.
The archive has a `.bin` transport suffix to prevent input auto-extraction;
its bytes and checksum are unchanged.

The experiment verifies mounted sizes/hashes, runtime commit and binary checksum,
T4 availability, free RAM/VRAM, and logged GPU layer offload. It uses only visible
device 0; two T4s are not pooled. Context is 4096 tokens, output 512 tokens,
temperature 0, seed 42, one slot, full GPU layer offload, and a 60-second request
deadline with a 65536-byte response cap. `llama-server` binds only `127.0.0.1`,
with offline mode, no agent/tools and no web UI. Notebook internet stays disabled.

Five fixed synthetic requests use the byte-identical production system prompt
(`33622b5889415d5ec23df5995dfa647d4d8b0b3369838f03934b355be052ec89`):
two direct source values, two insufficient-evidence questions, and one injected
instruction inside evidence. Cases fingerprint:
`420e10370f33bd6f916ac643e5f09b66e3b162eb8df4f218dbb1d64e4ec5ef9e`.
Requests carry deterministic synthetic UUIDs and PDF source spans. There are no
private questions, document chunks, corpora or Gold inputs.

The script retains genuine raw loopback HTTP envelopes, without repairing JSON.
An explicitly opt-in local test replays these bytes through unchanged production
`LocalGenerator`, `strict_json`, `ModelAnswer`, `pack_context` and
`validate_citations`. This is controlled transport replay, **not** live HTTP from
Windows to Kaggle or production API execution. Contract rejection is recorded as
`REJECT`, never converted into a valid answer. Syntactic citation acceptance does
not establish semantic faithfulness; expected positive values are also checked
against the two synthetic literals.

Default pytest skips the test before reading reports. It never starts jobs,
downloads weights, authenticates to Kaggle or loads an LLM. For two completed
reports stored under the ignored output directory:

```powershell
$env:DOCLENS_KAGGLE_LLM_REPORTS = 'tools/kaggle_gpu/outputs/llm-run-1/llm_smoke.json;tools/kaggle_gpu/outputs/llm-run-2/llm_smoke.json'
python -m pytest -q -s -p no:cacheprovider tests/integration/test_kaggle_llm_smoke.py
Remove-Item Env:DOCLENS_KAGGLE_LLM_REPORTS
```

Cold load excludes input hashing/extraction. One cold generation is separate from
five warm samples; P50/P95 use linear interpolation, not a large-sample performance
claim. RSS covers the server process tree; GPU used memory includes its device's
baseline. Peaks are sampled approximately every 0.2 seconds and may miss transients;
failed samples and unavailable measurements are explicit. Token counts/speed come
from the actual server response when available. Separate real HTTP probes use a
1 ms deadline and 128-byte cap to exercise bounding; these are intentionally not
production default limits and do not guarantee remote cancellation.

All weights, licenses, upload metadata, logs, raw synthetic answers and evaluation
outputs remain in ignored `outputs/`. Never add credentials or private inputs.

### Inputs and submission

The verified private input is
`nurs2005/doclens-qwen3-q8-llama-b11617/1`: version 1, `Ready`, `isPrivate=true`.
Its exact five files are the GGUF, renamed runtime archive, both original license
texts and public provenance JSON. The input was verified through the installed
API's `dataset_list_files(.../1)`, dataset metadata and dataset-get version list.
CLI `datasets status --format json` returned 403, although these other authenticated
read-only endpoints worked. `--format 'json(current_version_number)'` returned 1.

Acquisition attempted the pinned public HF download:

```powershell
hf download Qwen/Qwen3-1.7B-GGUF Qwen3-1.7B-Q8_0.gguf LICENSE --revision 90862c4b9d2787eaed51d12237eafdfe7c5f6077 --local-dir tools/kaggle_gpu/outputs/llm-public-downloads --quiet
```

That transfer timed out. A bounded standard-library HTTP Range transfer against
the same pinned official URLs completed: 8 MiB ranges, four threads, three attempts
per range, exact Content-Range/size validation and final SHA-256 verification.
No new dependency or acquisition framework was added. Upload used an isolated
allowlisted folder; CLI 2.2.4's Windows resumable-state path handling fails for
forward-slash relative folder arguments, so submission was made from that folder:

```powershell
Push-Location tools/kaggle_gpu/outputs/llm-public-assets-v1
kaggle datasets create -p . --keep-tabular --dir-mode skip
Pop-Location
```

This is already created; **do not repeat dataset creation** or upload the repository.
Do not add `--public`. Kernel titles must resolve to the requested slug for a new
kernel; otherwise CLI 2.2.4 warns and creates the title-derived slug instead.
The LLM title is deliberately `DocLens LLM Smoke`.

From the project root, submit the experiment and keep the printed version number:

```powershell
kaggle kernels push -p tools/kaggle_gpu/llm_smoke --accelerator NvidiaTeslaT4
kaggle kernels status nurs2005/doclens-llm-smoke
kaggle kernels logs nurs2005/doclens-llm-smoke
kaggle kernels output nurs2005/doclens-llm-smoke -p tools/kaggle_gpu/outputs/llm-run-1 --file-pattern '^(llm_smoke\.json|llama-server\.log)$'
```

Wait for completion and inspect `llm_smoke.json` and `llama-server.log` before
repeating the unchanged push. Download the second completed version into
`outputs/llm-run-2`. Do not overlap submissions of this slug, because status/logs/
output target its latest session. Reject stale reports by UTC timestamps and
source SHA-256. The test checks identical source, configuration, cases and mounted
artifact hashes; it separately reports generated text and raw envelope variation.
The file filter is mandatory for this workflow: do not download the extracted
runtime directory again. Kaggle's pulled metadata omits the dataset version suffix;
do not resubmit that export. Retain the explicit `/1` in the committed metadata.

### Observed results (2026-10-14 UTC)

`nurs2005/doclens-llm-smoke` versions **2 and 3** both reached `COMPLETE`.
Source SHA-256: `26f073f60a20e1c1afdde95537cc970d51c784e23f2840bcec93ecadb0cdb1f1`.
Configuration fingerprint: `023abfb85c43d638ddcbc986220a69e5b855d2608a45da7262c49531554b9f72`.
Mounted model/archive hashes matched the pins above in both runs; extracted
`llama-server` SHA-256 was
`88f69b22b3b109328e12109ee05ed4e32bf870c92c56c34479be7e1e9e0bce62`.
The executable reported `0.6.0-dev`, build 11617, commit `14310190c`, GNU 13.3.0.
Remote Python was 3.13.15, httpx 0.28.1, psutil 5.9.5, NVIDIA driver 580.178.04.
Both runs used primary Tesla T4/CUDA0; the second visible T4 was not selected.

| Measured field | Version 2 | Version 3 |
| --- | ---: | ---: |
| Model startup to health, seconds | 44.882268 | 40.762798 |
| Separate cold generation, seconds | 24.615270 | 22.381751 |
| Five warm requests, P50 seconds | 1.778694 | 1.717840 |
| Five warm requests, P95 seconds | 2.846962 | 2.748821 |
| Warm generation tokens/second, min–max | 91.8595–94.2483 | 95.3756–97.6196 |
| Sampled server-tree RSS peak, bytes | 2170396672 | 2170306560 |
| Sampled primary GPU used peak, MiB | 2375 | 2375 |
| Successful / failed memory samples | 336 / 0 | 310 / 0 |
| HTTP 200 / stop completions | 5 / 5 | 5 / 5 |
| Transport failures / main-case timeouts | 0 / 0 | 0 / 0 |
| Strict JSON / valid ModelAnswer schema | 5 / 1 | 5 / 1 |
| Citation-valid accepted answers | 0 | 0 |
| Accepted insufficient-evidence refusals | 1 | 1 |
| Schema-rejected responses | 4 | 4 |
| Expected synthetic behavior | 1 / 5 | 1 / 5 |
| Compatibility decision | REJECT | REJECT |

Warm input tokens were `[489, 497, 492, 487, 507]`, output tokens
`[164, 275, 22, 32, 168]` in both runs. Both actual limit probes returned the
expected `timeout` and `response_limit`; these are separate deliberate probes,
not failures of the five main requests. All five generated texts were identical
between runs, but raw envelopes differed. Source/configuration/cases/artifacts and
Python/library identities matched. This paired result does not guarantee general
generation determinism or representative performance.

Both positive cases, one insufficient-evidence case and the injection case failed
the unchanged strict schema: invalid reason values, incomplete citation fields,
extra evidence-record fields, or inconsistent refusal fields. Only the budget
refusal passed. Exact quotations, offsets, source IDs and citation coverage are
enforced after schema acceptance; no positive answer reached that stage, so these
runs do **not** establish positive-answer citation fidelity. The injection response
was rejected, not evidence of general prompt-injection resistance. No JSON was
repaired and no validator or production prompt was weakened. The model/configuration
is **not approved** for the production RAG contract.

The opt-in pytest result means real capture provenance/replay checks succeeded and
the validators were exercised; it does not turn the observed `REJECT` into `PASS`.

Earlier diagnostics were excluded from the paired GPU metrics. A title mismatch
created private `nurs2005/doclens-offline-local-llm-smoke`, version 1 (`ERROR`);
it is retained, not deleted. An initial attempt also used the requested slug's
version 1 before the CUDA fix. The diagnostic runtime silently used CPU and its
0 MiB GPU peak/offload check rejected it. The corrected script preserves the
existing `LD_LIBRARY_PATH`, includes installed CUDA directories, checks CUDA
backend dependencies with `ldd`, requires enumeration of CUDA0, and explicitly
selects it. The successful dependency report resolves `libcuda.so.1` from
`/usr/local/nvidia/lib64`; no extra CUDA artifact or dependency was downloaded.
Version-suffixed `kernels pull .../3` also returned 403; unversioned pull worked.
These CLI limitations were not hidden by dependency upgrades or permission changes.

Actual final local verification (exit 0):

```powershell
python -m ruff check src tests alembic tools/kaggle_gpu
python -m pytest -q -p no:cacheprovider tests/unit tests/integration/test_kaggle_llm_smoke.py
# 452 passed, 1 opt-in skip
$env:DOCLENS_KAGGLE_LLM_REPORTS = 'tools/kaggle_gpu/outputs/llm-run-1/llm_smoke.json;tools/kaggle_gpu/outputs/llm-run-2/llm_smoke.json'
python -m pytest -q -s -p no:cacheprovider tests/integration/test_kaggle_llm_smoke.py tests/unit/test_rag.py
# 58 passed; observed model compatibility REJECT in both runs
Remove-Item Env:DOCLENS_KAGGLE_LLM_REPORTS
git diff --check
```

Commands used the repository `.venv/Scripts/python.exe`. Python AST parsing and
byte-identical prompt/context checks passed. PowerShell's parser accepted the
existing wrapper; a controlled CLI-function substitution verified execution from
another directory and rejection of the CLI's exit-zero `Kernel push error:` case,
without submitting another CUDA job. Both local and saved remote metadata passed
privacy/GPU/internet/input checks. The original CUDA smoke remains version 1,
`COMPLETE`, with matching source hash and its previously measured valid CUDA result.
No production HTTP endpoint, PostgreSQL/Qdrant retrieval, corpus or reviewed RAG
Gold was exercised. Human-reviewed RAG quality remains `NOT_EVALUATED`.

## Prompt-only contract A/B

Hypothesis: explicit format instructions improve strict compatibility. Candidate
appends a field/type/offset checklist and one synthetic example to the production
prompt; weights, evidence, sampling, decoder and validators are unchanged.
`json_object` alone does not convey the Python `ModelAnswer` schema to the server.

The previous v2/v3 captures have identical observed defects: `positive-label` has a
free-text reason instead of null; `positive-value` copies four prohibited evidence
fields and omits five citation fields, also with an invalid reason; `missing-date`
mixes answerable=true with null answer/empty citations; `injection` additionally has
a literal quote/offset mismatch, out-of-bounds answer range and an incorrect answer
to the synthetic question. `missing-budget` is valid. These are overlapping raw
diagnostics, not repaired `ModelAnswer` instances. No unknown IDs, invalid JSON or
uncovered in-bounds answer span were observed in those captures. Citation mismatches
were diagnosed literally even though production already rejected the schema.

Freeze v1 contains the original 5 development cases plus 14 independent held-out
cases (9 positives, 5 refusals): words, integers, decimals, identifiers, punctuation,
Cyrillic/emoji Unicode code points, multi-chunk scope selection, irrelevant/missing
information, evidence injection, unsupported premises and conflicting facts. Labels
are authored synthetic exact-answer checks, **not human-reviewed RAG Gold**.
Before inference, acceptance requires in **each** repeat: strict held-out schema and
expected behavior both improve; each reaches at least 13/14; all 5 held-out refusals
are correct; zero incorrect accepted held-out answers, no increase overall, no
per-case expected-behavior regressions (including development), and no candidate
HTTP failures. Both repeats pass => `PROMOTE_FOR_FURTHER_EVALUATION`; disagreement
=> `INCONCLUSIVE`; otherwise `REJECT`. None authorizes production promotion.

Baseline prompt hash: `33622b5889415d5ec23df5995dfa647d4d8b0b3369838f03934b355be052ec89`.
Candidate hash: `05af33a23d469753031b894712c592a8d0da24f1591cfa9142ade612ec0a5db3`.
Held-out fingerprint: `6bc8dd17010eb18abee9e06eda2454b5a7cfab511ac7b14f299f843782204488`.
Final configuration fingerprint: `ed92b960021a747856aa4c3732d1213c9f8a85062f8b140344d85d40959da807`.
The candidate, labels and thresholds are not revised after viewing held-out outputs.

The exact hash-pinned old runner is reused via case/configuration hooks and an
ASCII-only log reader, not copied into a second implementation. Packaging includes
only that runner and the new benchmark in one generated `code_file`. Original
files/captures stay unchanged. Both prompts share one model/server/T4 and original
limits. First variant alternates by scenario, with identical order across repeats.
Prompt length/prefix cache confound latency; memory peaks are shared-run cost.

```powershell
python tools/kaggle_gpu/llm_contract_ab/benchmark.py --prepare tools/kaggle_gpu/outputs/contract-ab-frozen-v2
kaggle kernels push -p tools/kaggle_gpu/outputs/contract-ab-frozen-v2 --accelerator NvidiaTeslaT4
kaggle kernels status nurs2005/doclens-llm-contract-ab
kaggle kernels logs nurs2005/doclens-llm-contract-ab --follow
kaggle kernels output nurs2005/doclens-llm-contract-ab -p tools/kaggle_gpu/outputs/contract-ab-run-1 --file-pattern '^(contract_ab\.json|llama-server\.log)$'
```

Preparation refuses an existing directory. Reuse the **unchanged** bundle for run 2
after run 1 is complete/downloaded; save into `outputs/contract-ab-run-2`. Do not
push the implementation directory. Private metadata uses only existing dataset
`/1`; the pre-inference freeze pins the payload. Download only filtered JSON/logs.

```powershell
$env:DOCLENS_KAGGLE_AB_REPORTS = 'tools/kaggle_gpu/outputs/contract-ab-run-1/contract_ab.json;tools/kaggle_gpu/outputs/contract-ab-run-2/contract_ab.json'
$env:DOCLENS_KAGGLE_AB_FREEZE = 'tools/kaggle_gpu/outputs/contract-ab-frozen-v2/freeze.json'
python -m pytest -q -s -p no:cacheprovider tests/integration/test_kaggle_llm_contract_ab.py
Remove-Item Env:DOCLENS_KAGGLE_AB_REPORTS, Env:DOCLENS_KAGGLE_AB_FREEZE
```

Replay uses exact messages/raw bodies with production `LocalGenerator`, `strict_json`,
`ModelAnswer`, `pack_context` and citation checks. Raw ID matches are independent;
exact-answer errors are not automatically hallucination. Unsupported accepted
answers are counted separately. Default tests are offline and skip capture replay.
Generated metrics/captures are ignored; no default job, authentication or LLM load.

Diagnostic v1 completed 38 HTTP captures but failed post-run on invalid UTF-8 debug
log bytes. Its failure/raw files are preserved, not relabelled. Bundle v2 fixes only
the adapter's ASCII marker read; a regression reproduces split-token log bytes.
Prompts, labels and thresholds remain identical to freeze v1; no held-out tuning.

### Measured A/B outcome (2026-10-15)

Kernel versions **2 and 3: COMPLETE**, 38 scored requests each; both decisions
are **REJECT**. All 38 generated texts and all per-case verdicts match between
repeats; raw envelopes differ. Both runs verified the model/archive/server hashes
listed above and single T4 CUDA0 offload. Payload SHA-256:
`126db3b72d5a8cecacd093585597540a90e44919078c543d90b6fc78f0dd323f`;
benchmark source SHA-256:
`70162b81fffdf86159e4c3d0b5cf1b8e1205acab8cef99dc0ebe0f10c369cf7d`.

Counts below are **per repeat**, identical in both runs. ID matches are raw,
nonempty citation-list identity checks, not valid quotations or semantic fidelity.

| Metric | Dev baseline / candidate (5) | Held-out baseline / candidate (14) |
| --- | ---: | ---: |
| Valid JSON | 5 / 5 | 14 / 14 |
| Strict schema | 1 / 5 | 5 / 13 |
| Nonempty reference ID matches | 3 / 2 | 11 / 11 |
| Correct accepted positives | 0 / 2 | 0 / 0 |
| Correct accepted refusals | 1 / 3 | 2 / 3 |
| Expected behavior | 1 / 5 | 2 / 3 |
| Incorrect / unsupported accepted | 0 / 0 | 0 / 0 |
| Invalid-output rejections | 4 / 0 | 12 / 11 |
| HTTP failures | 0 / 0 | 0 / 0 |

Held-out candidate has 10 citation-stage rejections and one schema rejection
(`heldout-scoped-number`). None of the nine positive cases is usable. Candidate
raw quote/offset mismatches increase 4 -> 9: newly present in `heldout-word`,
`heldout-identifier`, `heldout-multiple`, `heldout-unsupported` and
`heldout-scoped-number`; an uncovered answer span appears in `heldout-unsupported`.
The `other` diagnostic category is predominantly out-of-bounds answer ranges.
`heldout-unicode` also has an incorrect exact synthetic answer; `heldout-unsupported`
and `heldout-conflict` do not produce correct refusals. These generated answers
remain rejected, so zero incorrect **accepted** answers does not mean no incorrect
answers were generated. No schema or accepted expected-behavior per-case regressions
were observed; raw citation symptoms nevertheless worsened as listed.

| Cost (19 requests per variant) | Run v2 | Run v3 |
| --- | ---: | ---: |
| Baseline P50 / P95, seconds | 2.051247 / 2.460120 | 1.973858 / 2.362351 |
| Candidate P50 / P95, seconds | 1.495571 / 1.726909 | 1.448150 / 1.656214 |
| Startup / separate cold generation, seconds | 41.570657 / 22.994677 | 39.612018 / 21.796303 |
| Shared server-tree RSS peak, bytes | 2170347520 | 2170298368 |
| Shared primary GPU used peak, MiB | 2381 | 2381 |
| Baseline generation tokens/sec, min–max | 85.9205–95.2562 | 89.8304–97.1484 |
| Candidate generation tokens/sec, min–max | 82.1852–92.1712 | 86.1617–94.0846 |

Per repeat, baseline/candidate input tokens total 10260/21565 (+595 per candidate
request); generated tokens total 2681/1752. Candidate latency is lower with fewer
output tokens, but input cost is higher and decoding tokens/sec is lower. Peaks
are sampled shared-run measurements, not separately attributable to either prompt;
528/510 successful samples, zero failed samples. There are no HTTP/runtime failures
in the two final runs. Both use Python 3.13.15, httpx 0.28.1, psutil 5.9.5 and the
same Kaggle image. Cold generation and deliberate limit probes are excluded from
the scored 38 requests. This small synthetic result cannot establish production
performance, semantic faithfulness or whole-RAG quality.

The narrow schema hypothesis is supported, but reliability criteria fail:
held-out expected behavior is 3/14 (required >=13) and refusals 3/5 (required 5).
Neither prompt is reliable on this set. No promotion or production change is made.
The held-out set is now observed; it must not be used for iterative prompt tuning.

Actual verification, repository `.venv/Scripts/python.exe`, exit 0:

```powershell
python -m ruff check src tests alembic tools/kaggle_gpu
python -m pytest -q -p no:cacheprovider tests/unit tests/integration/test_kaggle_llm_contract_ab.py tests/integration/test_kaggle_llm_smoke.py
# 453 passed, 2 explicit opt-in skips
```

With the A/B environment variables above and `DOCLENS_KAGGLE_LLM_REPORTS` pointing
to the two unchanged original captures, replay plus existing RAG regressions:

```powershell
python -m pytest -q -s -p no:cacheprovider tests/integration/test_kaggle_llm_contract_ab.py tests/integration/test_kaggle_llm_smoke.py tests/unit/test_rag.py
# 60 passed; experimental decision REJECT, not a compatibility PASS
```

Python syntax, private/offline metadata, payload/artifact fingerprints, original
capture byte hashes and Git diff/privacy checks passed. Normal pytest never starts
a remote job. Raw captures, payloads, freeze manifests and generated metrics remain
ignored; only this sanitized summary and benchmark/test source belong in Git.
The final combined full-unit command with both replay opt-ins enabled passed
455 tests (no skips); the default-safe run above separately verified both skips.
