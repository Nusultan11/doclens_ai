---
name: doclens-kaggle-gpu
description: Prepare, run or audit an explicitly authorized temporary DocLens Kaggle GPU workload, including staging and CUDA/model provenance. Not for local coding alone, quality promotion or production hosting.
---

# DocLens Kaggle GPU execution

## Apply and inspect

Read AGENTS.md, tools/kaggle_gpu/README.md and only the selected existing runner,
metadata, staging manifest and experiment protocol. Check actual CLI/runtime
versions before using version-sensitive official APIs. GPU-01 is
https://www.kaggle.com/docs/notebooks; P-GPU requirements come from the user's
brief unless an actual playbook is supplied. Do not claim to read missing attachments.

## Modes and invariants

Local development remains local; Kaggle is temporary compute, never production hosting.
- Mode A: interactive Jupyter/VS Code only through a supported, verified connection;
  capture the final code/configuration and execution provenance.
- Mode B: reproducible Kaggle CLI benchmark using a scoped staging directory,
  explicit metadata, versioned submission and retained JSON/CSV metrics/logs.

Two Tesla T4 devices do not automatically share one 32 GB VRAM address space.
Measure the selected device(s), actual placement and peak VRAM/RAM.

## Workflow and failure modes

1. Confirm workload authorization, experiment freeze, hardware/concurrency/time/
   storage limits and expected cost. A local task does not authorize a cloud run.
2. Stage only explicitly allowlisted source/public model assets and verify hashes.
   No private documents, Gold, sensitive contexts, secrets or credentials by default.
   A separately explicit private-data authorization must define scope/privacy before
   any upload; private visibility alone is not permission to transfer data.
3. Keep credentials outside Git/staging/logs. Check remote privacy/collaborators and
   exact uploaded file list before any authorized sensitive transfer. Never glob
   the repository or upload unrelated files. Pin source/model/runtime revisions.
4. Record submission/version identity; wait for completion and inspect status, logs
   and actual outputs. Submission, model download, HTTP 200 or CUDA enumeration
   alone is not successful GPU inference.
5. Verify actual CUDA computation/offload, selected devices, loaded artifact hashes,
   runtime/configuration/input identities and stale-output protection. Reject
   absent/partial/conflicting provenance; never silently fall back to CPU/model.
6. Preserve failures, timeouts, queue/startup versus inference timings and sampled
   resource scope. Bound retries by the task protocol; no overlapping submissions
   or tuning/retrying rejected model answers unless explicitly preregistered.

## Verify and report

Run local staging/runner tests first; verify exact remote source and loaded bytes,
completed kernel status, logs and JSON/CSV outputs after execution. Kaggle reports
may be unavailable/incomplete: mark the corresponding measurement UNKNOWN/BLOCKED.
Report commands, version IDs, hardware, CUDA proof, hashes, resources, failures and
privacy checks. Quality belongs to stage evaluation; no production promotion follows.
