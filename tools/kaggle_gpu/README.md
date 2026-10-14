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
