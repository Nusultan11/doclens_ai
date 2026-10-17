# c1-0045 memory diagnosis v1 (ML-11.1)

## Preregistration before new measurements

Registered at HEAD `e43258f90f0a996f5c7fbb76e6e0d6dc7d4ced42` on
2026-10-17. This is a bounded diagnosis, not a new model experiment, promotion
or full-corpus benchmark. Only this report may be added to Git. The four
unrelated untracked `rag_sufficiency_dev` paths are preserved and excluded.

Question: does the memory guard fire in converter/model initialization, native
PDF conversion, or DocLens normalization? Picture traversal is not assumed causal.
Compare exact frozen pre-ML-11 code from `e43258f^` with exact current code in
fresh serial spawned workers. AST comparison confirms their sole executable
difference is traverse_pictures=False versus True. Do not rewrite either
implementation or change any inference/resource setting to obtain a result.

Use only c1-0045, identical immutable source bytes, strict existing reviewed Gold,
the same local five-file models, Python/dependency environment, CPU/two threads,
FAST tables with cell matching, and existing offline/network/output restrictions.
No OCR, plugins, enrichment, external services, model downloads or GPU activity.
The same pypdf baseline runs first in each child to preserve paired-worker setup;
it is not the old-versus-current adapter comparison arm.

Unchanged per-worker limits: 600 seconds and 3221225472 bytes (3072 MiB),
52428800 source bytes, 200 pages, 100000 blocks/cells, 5000000 characters.
The primary guard uses actual spawned-child lifetime peak_wset, RSS fallback,
at approximately 50 ms intervals, as in the frozen runner. On a memory/time
violation terminate the owned child, join up to five seconds, then kill if
necessary; inspect and clean up only its recorded descendants. Retain the
unsuccessful attempt; never increase limits or infer completed fidelity.

First pair: old, then current, fresh processes with no concurrent inference/tests.
At most one additional pair, reversed current/old, is preregistered **only if**
the first pair has different outcome/attributed failure phase, both complete
without reproducing a resource event, or attribution is ambiguous. If both
implementations hit the guard in the same identifiable pre-normalization phase,
stop after that pair. Never loop until success. An instrumentation/infrastructure
failure is reported separately and cannot silently consume unlimited retries.

Temporary instrumentation lives solely under verified ignored
`evaluation-output/docling-c1-0045-memory-v1-20261017/`. Freeze exact old/current
module copies and instrumentation hashes there; retain sanitized raw measurements
ignored. No private text, filenames, Gold annotations or source paths are emitted.
Original files and tracked implementations remain read-only.

Trace coarse phase boundaries: worker startup, pypdf baseline, converter
construction/imports, lazy pipeline/model initialization, native PDF conversion
(with build/assembly/enrichment/unload subphases), native document available,
DocLens normalization, result completion and cleanup. Pinned vendor code shows
that DocumentConverter construction is not all model initialization: _get_pipeline
constructs/caches StandardPdfPipeline during convert. Instrument both boundaries.
Wrapper hooks call original methods with original arguments and return values;
no tracing of document payload or per-line Python execution.

A child/parent pipe handshake pauses briefly at boundaries so the parent can
sample the real worker before the next phase proceeds, without importing psutil
into the worker merely for tracing. Record PID, parent PID, creation time,
interpreter identity, monotonic phase timestamps/durations, current RSS and
kernel peak_wset. Distinguish supervisor/launcher memory and any descendants;
refresh descendant identities at one-second intervals and sample known processes.
Child peak is the unchanged primary guard; observed tree RSS is a secondary,
non-atomic measurement, not a new aggregate guard or sum-of-peaks claim.

Highest reliable memory evidence is the actual child OS high-water mark plus
its contemporaneous sampled RSS. Native allocations are included but allocator,
tensor/model/backend ownership is not established by process RSS alone. Boundary
tracing and host/page-cache variability may perturb timing/memory. Compare old
and current under the same instrumentation; do not treat them as exact replays
of historical uninstrumented runs. Historical failure phase cannot be recovered
retroactively from metadata that never captured it.

Evidence rules: an over-budget native conversion with no normalization entry
proves that this measured event precedes adapter traversal. Common old/current
failure supports a shared native resource problem, not a traversal regression.
An event during normalization requires boundary peaks and the corresponding
trace before attributing it. Mixed outcomes/material resource variability must
remain explicit. Missing measurements are UNKNOWN/BLOCKED, never fabricated.
Recommendations follow measurements and are not implemented in this substep.

## Frozen inputs verified before inference

Preflight exit 0: all 90 original SHA/size/format identities verified; strict
19-record reviewed Gold and both historical expanded / both ML-11 reports
verified. Only one source will be converted in this diagnosis.

| Identity | SHA-256 / fingerprint |
| --- | --- |
| Old exact adapter | `68c15cabb65f48c26fc531d0efb91900bf6ad5e9beaa9228fcf4005709b81b23` |
| Current exact adapter | `b0b872bb131b393b9338f135e353994c5213550c57e62ef92b49aee903d968fe` |
| c1-0045 source, 107597 bytes | `04358ce617249f170d38ea302cbc96a35701987507e61fb87ea2be30da2cfddc` |
| Manifest | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| 90-source identity map | `d32e9f9b2186d6973b59a1069df83d5d229a205ecac8d555091f6734053d47f8` |
| Gold bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Gold normalized | `50b37582e35382055515a16a2163f83a31ae8dcdd74e80729c499c04e65b815e` |
| Five-file model inventory | `3d5869718615820bc954966e26e85fce336cab115803452ac34d69b346c70e71` |

Layout revision `8f39ad3c0b4c58e9c2d2c84a38465abf757272d8`; table revision
`fc0f2d45e2218ea24bce5045f58a389aed16dc23`. Python 3.12.3; Docling 2.55.1,
docling-core 2.48.2, docling-ibm-models 3.15.0, torch 2.8.0, pypdf 6.20.0,
psutil 7.1.0. No dependency changes.

## Captured evidence motivating the diagnosis

| Historical c1-0045 attempt | Outcome | Candidate ms | Paired wall ms | Paired peak bytes |
| --- | --- | ---: | ---: | ---: |
| Expanded run 1 | success | 541845.103 | 545727.645 | 2872725504 |
| Expanded run 2 | success | 506161.104 | 510095.207 | 3063615488 |
| ML-11 run 1 | memory_limit | UNKNOWN | 383591.671 | 3226775552 |
| ML-11 run 2 | memory_limit | UNKNOWN | 372953.559 | 3221475328 |

All four attempted the same c1-0045. Their phase at the historical high-water
mark is UNKNOWN. ML-11 terminated before returning any candidate score/status;
its six anchors, two order pairs, four table cells, two relationships and six
provenance checks remain unknown, with denominators preserved. A runner exit 0
means evaluated attempt, not completed candidate extraction or evidence fidelity.

Relevant engineering sources: repository [ML-11 report](docling_picture_text_candidate_v1.md),
[ML-10 diagnosis](pdf_regression_root_cause_v1.md),
[frozen expanded protocol](docling_pdf_expanded_benchmark_v1.md), and pinned
Docling 2.55.1 installed document_converter.py / pipeline/base_pipeline.py /
pipeline/standard_pdf_pipeline.py for actual initialization/execution boundaries.
No private data is sent to external documentation services.

## Measured results

**Diagnosis complete: both exact adapters exceeded the unchanged process-memory
guard in Docling native building, before native document return and before
DocLens normalization.** This establishes the measured failure phase and
immediate cause (working-set high-water mark above budget). The picture traversal
change was never executed in either attempt and is not necessary to reproduce
this failure. The particular native allocation/component responsible is UNKNOWN.
This does not retroactively identify the exact phase of uninstrumented ML-11
events or establish an allocator leak. Their missing telemetry remains missing.

Exactly one old/current pair was measured, two attempts total. Both terminated
with memory_limit in native_build; no native_assembly, native document availability,
normalization or result-completion boundary was reached. The preregistered
same-phase stopping condition was met: **no second pair**. Both baseline pypdf
metadata objects exactly match the frozen c1-0045 baseline after removing latency.
Candidate fidelity/status remain UNKNOWN, including all six anchors, two order
pairs, four cells, two relationships and six provenance checks in each attempt.

### Phase timing and memory

All times are observed wall seconds, including small boundary handshakes.
Native conversion is inclusive of its nested initialization/build phases; do
not add the nested rows to that inclusive duration. Peaks are actual child
kernel peak_wset observations, not supervisor or launcher memory.

| Phase | Old seconds | Current seconds | Old peak bytes | Current peak bytes |
| --- | ---: | ---: | ---: | ---: |
| Worker startup after first boundary | 0.016490 | 0.015379 | 33665024 | 33705984 |
| pypdf baseline and its metadata | 2.160365 | 2.143217 | 76267520 | 75702272 |
| Converter construction/imports | 6.965295 | 6.504153 | 409776128 | 408743936 |
| Native conversion, inclusive until guard | 362.640660 | 382.530692 | 3224690688 | 3222560768 |
| Within conversion: pipeline/model construction | 0.807908 | 0.781261 | 728469504 | 727306240 |
| Within conversion: native_build | 361.786167 | 381.709692 | 3224690688 | 3222560768 |
| Native assembly/enrichment/unload | NOT_REACHED | NOT_REACHED | UNKNOWN | UNKNOWN |
| Returned native document available | NOT_REACHED | NOT_REACHED | UNKNOWN | UNKNOWN |
| DocLens normalization/result completion | NOT_REACHED | NOT_REACHED | UNKNOWN | UNKNOWN |
| Parent termination/cleanup | 0.198474 | 0.214803 | NOT_SAMPLED | NOT_SAMPLED |

The first phase boundary occurred 0.309891 / 0.308639 seconds after the parent
start clock (spawn/unpickling overhead). Native build began at elapsed
10.306533 / 9.792388 seconds. Guard observations were at 372.092700 /
391.502080 seconds; total elapsed through cleanup was 372.291174 / 391.716883
seconds. Neither reached the 600-second timeout. _get_pipeline observed zero
cached pipelines before initialization in each fresh worker. Constructor return
does not imply that all later first-use model/workspace allocations have already
occurred; such allocations during inference belong to native_build here.

| Resource/accounting fact | Old | Current |
| --- | ---: | ---: |
| Primary child PID | 3428 | 17452 |
| Supervisor PID (= child parent PID) | 28324 | 740 |
| Runtime launcher PID | 14852 | 9712 |
| Child created, Unix seconds | 1792246013.4254284 | 1792246476.2571385 |
| Highest reliable child peak_wset | 3224690688 | 3222560768 |
| Highest sampled child RSS | 3224690688 | 3221905408 |
| Maximum observed tree RSS | 3224690688 | 3221905408 |
| Peak over 3221225472-byte guard | 3465216 | 1335296 |
| Highest sampled supervisor RSS | 73863168 | 74522624 |
| Launcher kernel peak_wset at setup | 5062656 | 4993024 |
| Recorded memory samples | 5948 | 6219 |
| Median / maximum sample gap, ms | 63.647300 / 77.942500 | 63.751950 / 78.781600 |
| Available system RAM at worker start | 8000753664 | 8205660160 |
| Worker exit code | -15 | -15 |
| Explicit terminate / additional kill | yes / no | yes / no |
| Child alive after cleanup | false | false |
| Observed descendants / survivors | 0 / 0 | 0 / 0 |

The actual worker executable SHA-256 is identical in both attempts:
`15b41a488c356c0e331facdea6c836a6cec021f12d5fde9844e7ca4a1aa0361a`.
Both started with 31420416 sampled RSS bytes at their first boundary. The
supervisors/launchers were excluded from the primary guard. The highest current
kernel peak exceeds its highest sampled RSS: Windows retained a transient
high-water mark between polls. This is not a fabricated RSS observation.

For each attempt the **first recorded over-limit sample is the final sample**;
all preceding recorded peaks are within budget. The parent then terminates and
joins the actual worker, with no additional kill required. No candidate result
or complete flag was returned. This is an unsuccessful resource-limited attempt,
not ExtractionStatus.success or an invented ExtractionStatus.failed payload.

Hardware: Windows 11 10.0.26200, AMD64, 8 physical / 16 logical CPUs,
16541597696 RAM bytes. Two inference threads remain configured in the original
converter; total OS thread count was not measured. Serial fresh workers prevent
model reuse between arms. CPU/background-load/page-cache state was not frozen.
System RAM availability differed by about 205 MB; no causal attribution to that
difference is established. Historical old peaks 2872725504 / 3063615488 bytes
and the new old-adapter limit event demonstrate variability across captures,
under nominally identical budgets. The comparison does not support attributing
that variability to the traversal flag.

### Measurement limits and interpretation

Native build is the pinned PaginatedPipeline._build_document called by
StandardPdfPipeline: page initialization and the configured page-processing
pipeline execute there. Pipeline assembly and DocLens normalization occur later.
The trace does not distinguish individual layout/table/backend calls or attribute
native allocations to tensors, page buffers, caches or allocator retention.
Those mechanisms, the particular page responsible and a memory-reduction patch
remain UNKNOWN/NOT_EVALUATED. No source page/cell coordinates are invented.

The requested polling delay was 50 ms; actual median gaps are about 64 ms because
sampling, process discovery and scheduling add overhead. Kernel high-water marks
help preserve transient child peaks but do not measure peak private commit or
attribute shared pages. Descendants were discovered every second: zero were
observed, but very short-lived processes could escape discovery. Tree RSS is
non-atomic secondary evidence, not an enforced tree-wide sandbox. Cleanup memory
after the final guard observation was not sampled. Tracing/handshakes perturb
execution slightly, so these are controlled diagnostic measurements, not exact
uninstrumented replays, latency benchmarks or production-quality acceptance.
Both peaks are censored by termination: similar stopping values reflect the
shared threshold and do not establish equal uncapped or full-conversion memory
demand. No complete candidate latency or full-conversion peak was measured.

## Reproducibility, interruption and exact verification

The first command measured and preserved the old guard event, then exited 1 in
postflight verification because the saved source tuple reloads from JSON as a
list. This was a **scratch bookkeeping defect**, not a corpus/model mismatch,
second conversion or discarded measurement. A separate resume wrapper canonicalized
only that comparison in the supervisor and restored the standard JSON loader
before spawning. The original tracing script, phase/monitor/worker functions,
adapter copies and preflight bytes were unchanged. The unstarted current arm
then ran once; no old-arm retry occurred. Different supervisor PIDs and the pause
between arms are recorded above. The wrapper's setup/import overhead is another
measurement limitation; worker first-boundary RSS was identical.

The preregistration snapshot SHA-256 before inference was
`52090e9a31994ee38a2d7eb0169265c0e7fc573b302b5fe09dd1574303a44351`.
Scratch-only evidence identities:

| Ignored artifact | SHA-256 |
| --- | --- |
| Frozen diagnose.py | `05ac381cc94a09d498f947d17417ce65274fd1baca330c2d87323af2b3d90a60` |
| resume_pair1.py | `218ffdbc57867d7e45547f4762b69328bf7146f96fb7f25d988209dad12006b3` |
| verify_diagnosis.py | `2dc49a29ef49d30591446225ac5c24103c3a01f88c3ea5e339e4b575bd6bc3f5` |
| Immutable preflight.json | `e8d88c5d9ea82d6a6a43fb3e4e9b665627c9cee92193641832102197c06e800b` |
| Original limits/model-inventory configuration fingerprint | `562fc3ca48fa26d464d5c17151f2f61a88a78e376663708127eaf7cce32531b7` |
| Old samples.jsonl | `12d663f0e56d829cce7d61161f37cd3c735ba89f2d858b6621732a04db914721` |
| Old summary.json | `4c08d21a28a2bd1672d6f6bdfcc7d88dac9937ff556e226637a82a34472bf663` |
| Current samples.jsonl | `3c3fb716c6ce0b06f7cad5dd316620cca54320c8e4228a19ec9343b674904d71` |
| Current summary.json | `90d959f61b2a8d3825cd905fc4ec7299d489cdb847d0fa9fa6c4284747a76b2f` |

All four historical reports were reverified byte-for-byte before and after
measurements. Expanded run 1/2 bytes:
`dc96f3aa74da084c0135f7611e5d94edcfdadac7cc4fc56721d7e6552cb12c48` /
`3a4eb7cce304ee1d2fa41f631337ce481ada4a46704bee7a40274891a06d906a`;
both deterministic fingerprints:
`d9978aa0322d7f2ea3933f72c3b2a8e19e72a41d8073ab7b442ea049e0d3de24`.
ML-11 run 1/2 bytes:
`f78aaf265e0fa065f81a7d9b6472ad42f02ce9e956ff703083203b48428c8aeb` /
`2ece0ad6c59dab7770a97891ed4569f33a745ed5e615c1e29a0a49b319f4f13c`;
both deterministic fingerprints:
`faaef99c1e9bf5be6aa76c92159aee6fa5dd1dfa13bd24a10dab088a6523597d`.
Strict Gold, manifest, all 90 original identities, five model files, full installed
package-version maps, converter configuration and parser/models/scorer/Gold-loader
code hashes matched before and after. Neither adapter source was modified.

Actual commands from repository root (the scratch directory is verified ignored):

```powershell
git rev-parse HEAD
git merge-base --is-ancestor e43258f90f0a996f5c7fbb76e6e0d6dc7d4ced42 HEAD
git check-ignore evaluation-output/docling-c1-0045-memory-v1-20261017/diagnose.py evaluation-output/docling-c1-0045-memory-v1-20261017/old_adapter.py evaluation-output/docling-c1-0045-memory-v1-20261017/current_adapter.py
$env:PYTHONPATH='src'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_HUB_DISABLE_TELEMETRY='1'
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0045-memory-v1-20261017/diagnose.py --self-test
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0045-memory-v1-20261017/diagnose.py --pair 1
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0045-memory-v1-20261017/resume_pair1.py
evaluation-output/docling-v1-runtime/Scripts/python.exe -B evaluation-output/docling-c1-0045-memory-v1-20261017/verify_diagnosis.py
git diff --check
git status --short
git diff --name-only
```

Snapshot creation used `git show e43258f^:src/doclens_ai/extraction/docling_candidate.py`
bytes through Python subprocess into the ignored old_adapter.py; current bytes
were copied read-only. Both hashes and the sole AST constant delta were verified.
Ancestor check returned exit 0; check-ignore returned the requested scratch paths,
exit 0. Self-test printed `PASS: unchanged guard boundaries/precedence and exact adapter snapshots; no inference`,
exit 0. Focused tests: **116 passed in 6.74s**, exit 0. No broader unit, service,
GPU/OCR or full-corpus benchmark was run; tracked runtime/test code is unchanged.
Real diagnostic workers ran outside the restricted shell sandbox with original
offline restrictions active, avoiding the previously observed sandbox stalls.

Initial diagnostic command actual terminal output:
`ATTEMPT {"attempt": "pair1_old", "child_alive_after_cleanup": false, "child_exitcode": -15, "outcome": "memory_limit", "peak_child_bytes": 3224690688, "sample_count": 5948, "terminal_phase": "native_build", "wall_seconds": 372.29117380001117}`,
then `BLOCKED: diagnostic setup/measurement failed: AssertionError`, exit 1.
The diagnostic assertion inspection identified only
`diagnose.py:177 assert json.loads(destination.read_text()) == state`;
serialized source type was list. Resume printed
`PASS: immutable preflight reverified after tuple/list-only bookkeeping correction; resuming unstarted current arm`,
then current memory_limit/native_build with 3222560768 peak bytes and 6219 samples;
pair summary `repeat_needed: false`; exit 0.

Final audit exited 0 and printed:
`CONFIRMED: both exact adapters exceed unchanged memory guard in native_build before native document availability and normalization; repeat not needed`
and `PASS: frozen identities, process accounting, raw trace consistency, guard termination, cleanup and baseline equivalence verified`.
It independently checked every sample count/high-water maximum, monotonic kernel
peaks, first-over-limit termination, PID/parent identities, matching executable,
no surviving owned workers/descendants, unchanged inputs and baseline equivalence.
`git diff --check` returned exit 0; `git diff --name-only` was empty before
staging because only this new report is eligible. No tracked code/configuration
or existing report changed.

Final report validation ran through `.venv/Scripts/python.exe -B -`, exit 0:
`PASS: report trace/artifact identities, two-attempt bound, cleanup, unchanged tracked files and bounded privacy checks`.
It checked both saved traces/artifact hashes against this report, exactly two
attempt directories/no repeat, terminated worker state, no tracked modifications,
and all original identities. The privacy scan compared real corpus filenames and
normalized Gold anchor strings of at least twelve characters against the report,
and rejected absolute paths/private-key headers. Manual staged-diff review
supplements this bounded scan; it is not a universal secrets detector. Only this
sanitized report is eligible for the requested documentation commit; temporary
instrumentation and captures remain ignored. The unrelated untracked work is
neither read nor staged by this substep's checks.

## Confirmed findings, unknowns and smallest corrective action

Confirmed: the measured limit is a shared native-build resource failure preceding
the changed adapter path. Pipeline construction peaks below the guard; both old
and current conversion workers later exceed it. Original runner metadata omits
the active phase when the parent kills a worker, which prevented attribution in
ML-11. No candidate fidelity observation can be recovered from that absence.

UNKNOWN: the allocation owner inside native_build, why earlier old captures fit
within budget, the exact historical failure phase, effect of caches/host load/
native allocators, and whether a specific native optimization would reduce peak
memory without affecting evidence fidelity. No evidence-backed memory-reduction
patch is established by this diagnosis.

Smallest justified future corrective action: add content-free phase checkpoints
to the **offline benchmark worker/parent metadata** so a controlled resource kill
retains its last reliable phase and real worker identity. Keep the same budgets
and unknown-score handling. This corrects the demonstrated diagnostic gap; it
does not claim to reduce RAM. A memory-reduction fix requires separately scoped
native-build allocation evidence. Neither action is implemented here.

ML-11 candidate acceptance and overall production quality remain REJECT. The
picture-text recovery remains a measured offline finding, with no promotion.
Production pypdf, both adapter implementations, Gold, models, configurations,
historical outputs and test splits are preserved. No ML-12 or other task starts.
