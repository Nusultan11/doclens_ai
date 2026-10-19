# DocLens Kaggle GPU playbook

AVAILABLE LOCAL EDITORIAL SPECIFICATION, reconstructed 19 October 2026 from the
reconstruction brief, architecture §11, project GPU skill and existing
[runner guide](tools/kaggle_gpu/README.md). Not a recovered original, cloud-run
authorization or production qualification. Owns temporary GPU operations;
[ML strategy](DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) owns experiments
and [quality policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES)
owns acceptance. Follow the GPU skill for task-specific execution checks.

<a id="GPU-MODE"></a>
## [GPU-MODE] Boundaries and preflight

Backend/API, database, migrations and Docker development remain local. Kaggle is
temporary explicitly authorized experiment compute, never production hosting.
Establish workload, device/concurrency, duration/storage/resource limits, authorized
inputs, expected artifacts and stopping rules before submission. Check actual
account availability, quotas and CLI/runtime versions; no account-specific IDs,
credentials, hardware allocation or remote connection is assumed here.

Stage only an explicit allowlist of necessary source and permitted public assets
with hashes. Keep credentials outside Git/staging/logs. Private RAW, proprietary
documents, protected Gold, sensitive prompts and document-derived embeddings need
explicit scoped transfer authorization, privacy/retention controls and recipient
review; private visibility alone is not authorization. Inspect exact staged files
and remote collaborators/visibility before transfer. Never upload the repository
by glob or mount production data for convenience.

<a id="GPU-A"></a>
## [GPU-A] Interactive Jupyter execution

Use the official notebook interface, or a supported verified editor connection
when available. Do not assume remote VS Code access exists or expose an unauthenticated
server/tunnel. Capture final notebook/source, cell execution order, Git/config/model/
input revisions, dependencies, seeds and device placement. Restart/run the frozen
workflow cleanly; out-of-order notebook state is not reproducible evidence.
Export sanitized logs and JSON/CSV metrics with run identity, failures and timings.
Keep private intermediate outputs in approved protected storage.

<a id="GPU-B"></a>
## [GPU-B] Versioned CLI benchmarks

Use the existing runner guide rather than inventing a second command sequence.
Check installed `kaggle --version` and relevant subcommand help before using
version-sensitive metadata/flags; resolve only explicitly authorized notebook IDs.
Freeze staged source hashes, metadata, model bytes and inputs before submission.
Record submission/version identity, poll status to terminal completion and retrieve
that exact version's logs and declared artifacts. Reject stale or mismatched outputs.

Preserve failed submissions, queue/startup/inference timing and terminal errors.
Bound retries under the registered protocol; no overlapping runs or selective
retries of rejected answers unless preregistered. Submission/download/HTTP 200 is
not successful inference. Cleanup only explicitly owned temporary resources after
retaining required evidence; never delete shared datasets or local source originals.

<a id="GPU-GATE"></a>
## [GPU-GATE] CUDA and artifact verification

Record actual GPU model/count, selected device(s), driver/CUDA/framework versions,
loaded artifact SHA-256/revisions, runtime identity and execution configuration.
Prove real CUDA computation or model-layer offload using the selected runtime's
outputs; device enumeration or allocated memory alone is insufficient. Record
offload/placement consistency and reject silent CPU/model fallback. Two T4 devices
do not form one combined 32 GB address space; report each device and actual placement.

Measure cold load/startup separately from steady inference and total elapsed time;
record P50/P95 where sample size permits, peak device VRAM and host RAM, units,
sampling/process scope, concurrency, timeouts and failed attempts. Mark unavailable
measurements UNKNOWN/NOT_EVALUATED rather than infer peaks from one sample.

Execution PASS requires completed workload plus matching source/input/model/runtime
and CUDA provenance, valid expected artifacts and inspected logs. Missing essential
runtime/provenance means BLOCKED or failed execution, never a silent success.
JSON/CSV results must separate operational execution from stage quality decisions.
GPU execution PASS grants no model-quality PASS or production authorization.
