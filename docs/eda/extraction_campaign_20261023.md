# Five-system extraction research campaign — execution record

Campaign requested 23 October 2026 (Asia/Qyzylorda). Starting branch
`codex/extraction-engine-integration`, HEAD
`2bbcbdc696ebe3a0cb514d9a4e3732317299278f`; research branch
`codex/extraction-research-20261023`. The preexisting untracked
`docs/eda/independent_engineering_audit_20261020.md` is user-owned and excluded.
This record closes the feasible technical R0 work. The consolidated verdict below
keeps the original-cohort R1/R2/R3 permission blocker explicit.

## Scope and authority

READ: root AGENTS/source map, maintained Architecture/Extraction/ML/Quality
owners, applicable extraction-benchmark/ML-experiment/data-quality skills,
previous Docling/readiness reports, relevant offline runners and strict Gold
interfaces. CREATE/MODIFY only `tools/extraction_campaign/`, its unit tests and
safe summaries in `docs/eda/`. Environments, source paths, native outputs, full
logs, model weights and private Gold remain under ignored local directories.
Production code, parser defaults, dependencies, migrations and service contracts
must remain unchanged. No retrieval, RAG, embeddings or indexing experiment.

Sources: [Extraction](../../DocLens_AI_Extraction_Strategy.md),
[ML](../../DocLens_AI_ML_Quality_Strategy.md),
[Quality](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md),
[readiness inventory](dataset_readiness_inventory_20261021.md).
The user's express authorization to execute all five candidates supersedes the
skills' ordinary stop-after-one-experiment procedure. It does not authorize
private data transfer, fabricated review, model promotion, push or PR merge.

Draft [PR #1](https://github.com/Nusultan11/doclens_ai/pull/1), head
`9eebdca7b5910107c09994600b3d79124c849b34`, was rechecked via the GitHub connector.
It remains a registry foundation without model inference or quality evidence;
the current branch already contains stronger integrated contracts. No merge,
cherry-pick, production routing reuse or duplicate production engine was added.
Offline research reuses strict corpus/Gold loaders and the existing isolated
Docling converter/legacy projection. Current model-native JSON is captured
separately from that historical lossy projection and from Markdown.

## Phase 0: foundation and dataset boundaries

Measured host: Windows AMD64, Ryzen 7 5800HS, 8 physical/16 logical CPUs,
15.41 GiB RAM, approximately 4.52 GiB available at preflight; RTX 3050 Laptop GPU,
4096 MiB VRAM, driver 566.07, initially 3745 MiB free. C: had approximately
455 GB free. GPU enumeration is not CUDA inference. Existing Docling environment
has Torch 2.8.0 **CPU**, `torch.version.cuda=None`, `cuda.is_available=False`.
At the initial foundation stage no cloud workload/upload was authorized or started.
The later explicit Kaggle authorization and its narrower transfer boundary are
recorded below; the initial observations remain historical.

All 90 legacy source SHA/size/format identities were freshly matched against
local immutable originals using the existing verifier. Strict Gold loading
validated 19 historical source-bound records, of which 12 are PDFs. This is
historical partial single-reviewer attestation, not independent whole-document
Gold. Selected diagnostic DEV population: **11 PDFs, 77 pages, 84 anchors,
17 numeric-bearing anchors, 44 order pairs**, 11 declared families. Historical
language metadata: EN 10, CY 1; zero real RU/KK sources. Twenty legacy table-span
assertions exist, but prior unresolved table mappings do not provide independent
GriTS/TEDS or exhaustive table Gold. No reviewed full transcripts/layout boxes,
empty-cell/formula/image Gold or independently labelled sealed test is created.

`c1-0045` is explicitly excluded because its new-processing permission remains
unresolved in the authoritative readiness inventory. Other historical failures
are retained, not selected away based on candidate performance. Existing
cross-collection family exclusions were revalidated using only the QA split
metadata; no QA evaluation was executed. All selected sources are already exposed
DEV controls. Validation/sealed-test populations are empty, with independence
NOT_EVALUATED. No exposed source is renamed a blind test. Expansion to 36–48 is
not admitted without additional rights, reviewed Gold and resources.

The first immutable metadata audit is at ignored
`evaluation-output/extraction-campaign-20261023/foundation-v1/`; its selection
fingerprint is `3c84cedf78693151bad49b5080cc7788ae4898b592b1a9c1124001860b08d644`.
It predates final harness edits and is not used as a current-code run protocol;
an explicitly new revision is required before inference. Original and Gold
bytes are never changed when a code/protocol revision is frozen.

Metrics preregistered: exact whitespace-only anchors with explicit sign/zero/
numeric-token boundaries; exact numeric-bearing anchors in their original
context; one-based page presence; historical order pairs from native sequence.
All attempted failures retain label denominators and UNKNOWN observations.
CER/WER, GriTS-Top/Con/Loc, TEDS, layout AP, exhaustive numerical/formula accuracy
remain NOT_EVALUATED without valid corresponding reviewed Gold and verified
implementations. Table HTML/geometry/relations are preserved as observations,
never relabelled as reviewed truth. Any new measured critical baseline-present
anchor/numeric/page/order loss rejects that frozen configuration; pooled gains
cannot cancel it. Numerical release thresholds stay TBD.

Initial research budgets: one candidate/worker at a time; 600 s/document;
3 GiB sampled process-tree RSS, 4 GiB OS job committed-memory ceiling,
1200 CPU seconds/job, at most eight owned auxiliary processes; 128 MiB structured
output and 256 MiB scratch. These are explicit operational limits, not QG/SLO
thresholds. Check at least 4 GiB available host RAM before admitting a heavy job.
Two repetitions on identical inputs; baseline plus at most two justified changes;
at most one lower-resource attempt after OOM. No unconstrained GPU/VRAM claim.
Windows job limits are installed/read back before the actual worker PID enters
framework imports; venv launchers are distinguished. Owned descendants are
terminated on completion/failure. External connections are denied in the worker;
only explicit owned loopback auxiliaries are allowed. This is not an OS egress
sandbox. Candidate processes receive a minimal environment and isolated profile,
not inherited API credentials or the repository `.env`.

## Foundation verification and reproduced tooling errors

Adapter fixtures cover native Docling reference trees/picture descendants and
charspans, Paddle structured wrappers, Marker HTML/tree identity and MinerU
middle JSON; unknown fields/pages/coordinate bases remain unknown. Full model
outputs are stored before adaptation so adapter defects can be separated from
model observations. This fixture coverage does not establish real-model fidelity.

- Initial adapters: **2 failed, 14 passed**. Fixed loss of the explicit native
  tree-parent edge. Corrected a test that incorrectly prohibited negative native
  coordinates without a known coordinate basis; it now tests an inverted rectangle.
- HTML projection regression: **2 failed, 20 deselected**; raw Paddle table HTML
  could credit an anchor appearing only in an attribute. A separate visible-text
  projection now excludes markup attributes while retaining complete native HTML.
- Snapshot-reuse regression: **1 failed, 27 deselected**; same-size modified config
  could bypass its pinned Git blob identity. Reuse now verifies that identity too.
- Actual worker tests exercise hang/crash, MemoryError under an enforced job limit,
  output overflow and auxiliary-process cleanup. No resource assertion/budget was
  weakened to pass tests.
- Affected extraction/Gold/adapter suite before staging-tool tests:
  `.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_campaign.py tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_dataset_readiness.py tests/unit/test_document_ir.py -q -p no:cacheprovider --basetemp=.pytest_cache/research-foundation-final -x --tb=short`
  — **217 passed**, 13.49 seconds. Final expanded verification follows below.

Public package/model metadata and official vendor docs were captured locally.
Current candidates found: Marker 2.0.0 + Surya 0.22.1, PaddleOCR 3.7.0,
PaddlePaddle CPU 3.3.1, MinerU 4.0.12. Exact requested VLM model revisions:
PaddleOCR-VL-1.6 `c5630abae1d940eafe0697512a0325494b02ab42`;
MinerU2.5-Pro-2604-1.2B `d3f5e08d073c21466bbabe21c71bb1e9c2e595da`.
These are discovery pins, not proof that weights were loaded or inference ran.
Each candidate must independently register actual environment, full effective
configuration, loaded-artifact hashes, licenses and backend before inference.

Foundation final verification:
`.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_campaign.py tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_dataset_readiness.py tests/unit/test_document_ir.py -q -p no:cacheprovider --basetemp=.pytest_cache/research-foundation-complete -x --tb=short`
— **224 passed**, 14.53 s. Ruff check/format on the new tooling/tests — PASS;
`git diff --check` — PASS. No production/dependency/migration diff versus starting
HEAD. Final pre-inference input/code protocol is immutable `foundation-v3`,
fingerprint `7dc10d9f449675bbf2fbeb06f9f485a6c695920386a2eebb8af23c29d26df2c2`.
The v1/v2 files are preliminary metadata captures; no model inference used them.
The committed [safe protocol projection](extraction_campaign_20261023_protocol.json)
contains opaque source/page identities, hashes, family/exclusion and scoring rules;
private full records also retain environment/hardware. New worker captures include
complete native pages/predictions, conversion status/confidence/errors/timings and
model-native document JSON. Only explicit latency/timing fields are excluded from
repeat comparison; raw captures are never overwritten.

### Admission and bootstrap failures retained before model inference

The original native comparator registration (`native-r1`) recorded 22
`resource_blocked_before_start` outcomes: available RAM had fallen to
3,155,021,824 bytes, below its 4 GiB admission requirement. These are 22 scheduled
admissions on 11 distinct sources, **zero executed extractions**, not measured
accuracy or model reproducibility. No user process was stopped.

A pre-inference resource revision reduces the native comparator's RSS ceiling to
512 MiB, OS committed memory to 1 GiB and admission floor to 1.5 GiB. Docling's
RSS ceiling is reduced to 1.5 GiB, with a 2.5 GiB admission floor and unchanged
4 GiB OS committed-memory ceiling. This preserves approximately 1 GiB host
headroom at the observed RAM level, rather than admitting the original 3 GiB
RSS workload. Data/scoring/quality criteria remain identical. The exact two
configuration records are retained as `native-low-memory.json` and
`docling-low-memory.json`; this is not model-accuracy tuning or a raised limit.

The first reduced-resource native run retained **22 failed bootstrap attempts**,
each WinError 10106 while importing the Windows asyncio provider, before parsing.
Cause reproduced by a new actual subprocess test: the minimal-environment filter
used case-sensitive `SystemRoot`, while Windows `os.environ` supplies `SYSTEMROOT`.
This omitted the provider's required system path. The regression test first
**FAILED: 1 failed, 29 deselected**. Fixed only case-normalization of the OS
environment allowlist; credentials and repository `.env` remain excluded.

Affected suite rerun with `--basetemp=.pytest_cache/research-bootstrap-fixed`:
**225 passed**, 13.52 s. New immutable protocol `foundation-v4` fingerprint
`39e0b5f1b48f4349b5f1d6886b50896885929f599093a84ffe0b311b0251f1e5`
preserves the same 11 source/Gold identities and scoring rules, with corrected
bootstrap code pins. Native R0 on c1-0033 then **completed**, 2.05 s, under the
lower resource ceiling. No Docling/model inference ran during the failed native
bootstrap attempts. The failed outputs remain separate and unmodified.

## Authorized Kaggle continuation — 23 October 2026

The user explicitly authorized private Kaggle kernels for sequential extraction
research on public/synthetic inputs. Apply the maintained
[GPU Playbook](../../DocLens_AI_Kaggle_GPU_Playbook.md) and
[GPU skill](../../.agents/skills/doclens-kaggle-gpu/SKILL.md). Additional authorized
CREATE/MODIFY scope: `tools/kaggle_gpu/extraction_*`, its dedicated unit tests,
this report and ignored campaign artifacts. No production changes, local heavy
inference, push, merge, private corpus/Gold upload or new approved labels.

Starting state was audited rather than restarted: branch
`codex/extraction-research-20261023`, HEAD `3d9a787`; foundation `d7de077` and
bootstrap correction `3d9a787` already committed. The user's independent audit
remains untracked/excluded. Seven manifest/Gold/readiness hashes and all eleven
selected original-source hashes were rechecked unchanged after Kaggle staging.

The preserved `native-r1-bootstrap-fixed` comparator has **22/22 completed**
attempts (11 documents, two repeats), 16 `success` and 6 `needs_review`, with matching
non-runtime fingerprints. Per-repeat strict diagnostic counts: **72/84 anchors,
16/17 numeric anchors, 72/84 page anchors, 33/44 order pairs**. These are partial
DEV checks, not a quality gate PASS. Earlier 22 admission failures, 22 Windows
bootstrap failures, and three local Docling environment-pin failures are retained.
The latter occurred before model inference and are not Docling quality failures.

### Transfer and frozen controls

No permission was supplied to transfer the eleven original cohort documents.
Therefore remote **R1/R2/R3 on that cohort are BLOCKED**; private Gold stays local.
R0 uses exactly three deterministic, authored synthetic PDF controls, generated
inside the kernel from the reviewed script: prose, signed/leading-zero numbers,
and aligned rows. All are English, born-digital and one page. They are not reviewed
Gold, scanned-page coverage, RU/KK evidence, or a substitute quality cohort.
The eleven authored text-line presence checks are technical diagnostics only.
R0 success cannot justify an R2 quality modification or production promotion.

Only one explicit Python script and private metadata are uploaded per kernel.
Exact upload manifests are retained outside each stage. No repository glob,
private inputs, model upload, credential, competition/dataset/kernel source or
collaborator is added. Public weights are downloaded at immutable revisions
remotely; models/environments remain ephemeral and excluded from output exports.
All full native outputs, logs and failures are retained in ignored
`evaluation-output/extraction-campaign-20261023/kaggle/`.
Reproduction commands and bounds: [runner guide](../../tools/kaggle_gpu/extraction_campaign.md).
Current safe public pins: [registry](../../tools/kaggle_gpu/extraction_registry.json).
Historical submitted scripts/manifests remain immutable even when the runner is fixed.

### Authenticated runtime preflight

Installed CLI **2.2.4**, read-only `kaggle kernels list --mine --page-size 5 --csv`
succeeded. `kaggle quota` initially returned **12.90 h used / 17.10 h remaining /
30 h GPU**, reset `2026-10-24T00:00:00`; TPU 0/20 h. No credential values were read
or printed. CLI advertised 2.2.5; no upgrade was made. The exact global maximum
session duration is UNKNOWN: the official dynamic
[notebooks page](https://www.kaggle.com/docs/notebooks) did not expose its content
to the documentation reader. Submissions use an explicit **3900 s** bound (preflight
180 s), plus separate setup/acquisition/document/process-memory limits.

Private `nurs2005/doclens-extraction-preflight`, version **1**, reached COMPLETE.
Its source SHA-256 is `ce93c421cf766be383501ef5b6a6b6adc83526c490c5b2c6a6740817fcc17adc`.
Downloaded report and all declared checksums matched. Actual remote hardware:
4 logical CPU, **33,658,318,848 bytes RAM**, initially 32,264,392,704 available;
20,957,446,144-byte working disk; **two Tesla T4**, each **15,636,037,632-byte VRAM**.
Python 3.13.15; preinstalled Torch 2.11.0+cu128/CUDA 12.8. Validated every element
of real 512x512 matrix products on CPU and `cuda:0`; elapsed 0.1664/0.9702 s,
CUDA peak allocated 10,880,512 bytes. This proves runtime computation only, not
model inference or pooled VRAM. The second T4 is not selected for model work.

### Remote attempts retained

| Kernel / version | Technical outcome | Documents / resources / cause |
| --- | --- | --- |
| `doclens-extraction-docling-r0` / 1 | BLOCKED before setup | 0/3 started: Debian Python `ensurepip` unavailable; complete failure report/checksums retained |
| Same / 2 | R0 execution PASS | 3/3 native `success`; CPU; whole-worker 7.4245–8.0269 s; peak tree RSS 999,710,720–1,029,832,704 bytes |
| `doclens-extraction-marker-r0` / 1 | BLOCKED before inference | Packages and public HF snapshots downloaded; dated official OCR-error `manifest.json` returned HTTP 403; 0/3 started |
| `doclens-extraction-ppstructure-r0` / 1 | R0 execution FIX | 3/3 failed in actual layout inference: oneDNN `ConvertPirAttribute2RuntimeAttribute` unsupported `pir::ArrayAttribute<pir::DoubleAttribute>`; peak RSS 2,663,661,568–2,681,724,928 bytes |
| Same / 2 | R0 execution PASS; diagnostic limitation | 3/3 completed; same weights/pipeline, `enable_mkldnn=False`; worker 68.9431–70.9096 s; peak RSS 13,193,216,000–13,214,314,496 bytes |
| `doclens-extraction-paddlevl-r0` / 1 | R0 execution PASS | 3/3 completed, full official v1.6/0.9B CPU pipeline; worker 52.8943–86.5957 s; peak RSS 9,706,946,560–9,799,331,840 bytes |
| `doclens-extraction-mineru-r0` / 1 | R0 execution FIX before model load | 3/3 failed: Torch 2.8 CUDA statistics reset before lazy context initialization; no model-quality observation |
| Same / 2 | R0 execution PASS | 3/3 full PDF conversions with observed CUDA model forwards; worker 19.9683–21.9440 s; peak tree RSS 3,061,063,680–3,449,737,216 bytes |
| `doclens-extraction-marker-r0` / 2 | R0 execution FIX before model inference | Acquisition succeeded after requests-client repair; 3/3 then rejected unregistered render-font network download during converter construction |
| Same / 3 | CUDA provenance gate FIX | 3/3 native documents produced, but all attempts remain failed: default llama.cpp verbosity omitted explicit offload evidence; GPU allocation alone was not accepted |
| Same / 4 | R0 execution PASS; diagnostic limitation | 3/3 completed, 25/25 CUDA-layer offload observed; worker 120.9856–123.3956 s; peak RSS 2,793,435,136–2,825,887,744 bytes |

Docling v2 source SHA-256:
`c3da4c94dd13b7c1642b5915ce9a8efa2778b693e0bdc04ba72ebb289f88ffbf`.
It retains Docling 2.55.1/core 2.48.2/IBM models 3.15.0, isolated Torch 2.8.0 CPU,
Transformers 4.57.6; FAST/cell matching/no OCR/no enrichment/no external service,
two CPU threads, seed 0. Layout/table revisions remain the original frozen pins.
Every downloaded Docling model/config hash matched the existing local frozen
artifact inventory. Complete document, native backend pages, conversion metadata
and effective options were downloaded and checksum-verified. Existing native
adapter recovered all **11/11 authored synthetic text lines** (3/3, 4/4, 4/4).
Conversion including lazy model load: 2.1067–2.1575 s. Constructor alone is near-zero
because model initialization is lazy; whole-worker latency includes imports.
This is one technical R0, not a paired R1 or model-quality comparison. Pulled
Docling/Marker server metadata confirms private visibility and no input datasets.

Marker v1 source SHA-256:
`538ee672962bb5af6b1c65f7314f73fe9b936620423ebff11d163081d36b8a13`.
Marker 2.0.0/Surya 0.22.1, balanced full-PDF pipeline, JSON renderer, no external
LLM, pinned official Surya GGUF revision `6a3a4c30e5e74446d4f8b6afd05b2f2da970f470`.
No Markdown-only/fast/no-OCR substitute was used. Public model access failed at
`https://models.datalab.to/ocr_error_detection/2025_02_18/manifest.json` before the
CUDA server/model ran. Setup 96.3448 s; acquisition failed after 14.0507 s;
peak acquisition RSS 812,929,024 bytes. Model CUDA/quality remain NOT_EVALUATED.
Subsequent diagnosis reproduced **requests HTTP 200 versus urllib HTTP 403** on
the same public manifest, matching the vendor's requests downloader. The v1
outcome is retained as an acquisition defect, not a permanent model-access denial.
V2 source `0fc70cf975e432c4089e78ed7b0cd6a4b491ac2a4df691ec3dd3cbf685052c56`
successfully acquired the exact OCR-error assets, Surya GGUF, and checksum-pinned
llama.cpp CUDA runtime. It then exposed a separate preparation defect: Marker
BaseConverter always calls `download_font`, including PDF/JSON mode. All three
inference attempts were blocked by the external-network guard before model use.
V3 preregisters the public GoNoto font (14,700,060 bytes, SHA
`882afbab965608c2d2bc627fd8016b962aa5a6be2d358f9de24a7b5967c5632e`),
prefetches it during acquisition, pins the already acquired OCR-error byte hashes,
and keeps inference restricted to loopback. These are bounded setup repairs, not
quality tuning or an external inference API.
V3 source `ad513cf01afaf5d544511e508174f6f4411b88bfb1279d990bd761ac5eb45ba2`
did save three native documents and server generation timings, but default log
verbosity 3 omitted backend CUDA-layer evidence. The unchanged proof gate returned
`marker_cuda_offload_unverified` in all three cases. They are retained as failures,
not retroactively credited as GPU PASS. A single instrumentation repeat of the
same R0 model configuration enables `-lv 5`; no decoder, data, model, batch,
context, sampling or quality criterion changes. This is not a fourth R1 quality
configuration or an R2/R3 tuning experiment. The earlier complete captures include
disposable CUDA ComputeCache files; subsequent caches stay in ephemeral `/tmp`,
while native JSON and complete failure/server logs remain exported.

PP-StructureV3 v2 source SHA-256:
`2248e291ba9b9d196faec7898c6c8e03d734ca2805add9012b4ad5f5c4447246`.
PaddleOCR 3.7.0/PaddleX 3.7.2/PaddlePaddle CPU 3.3.1, twelve pinned official models
including layout/region/OCR/table/formula, batches 1, two threads, seed 0. Each
downloaded output checksum and all three synthetic input identities were verified;
pulled server metadata confirms private visibility/no input datasets. Initial
v1 source `aad155827e0f7505673fa534766091ad278ab3abfadc90e41932a25ea84a55fe`
is retained with all three oneDNN failures. V2 changes optional CPU acceleration,
not model bytes or evidence criteria. Constructor 11.4559–11.6272 s; conversion
48.7548–50.5813 s. This 12.3 GiB RSS workload was not attempted on the local host.

PP-Structure's paragraph output preserves **9/11 authored lines** (3/3, 4/4, 2/4).
The aligned-row controls expose a producer postprocessing defect: separate OCR
tokens for count/cost survive in `overall_ocr_res.rec_texts`, but native paragraph
content concatenates numeric columns. The adapter faithfully preserves that native
paragraph defect; raw OCR and geometry are retained without inventing table links
or silently repairing text. This is a concrete synthetic limitation, not a
Gold-based quality score or a justification to tune R2 without the frozen R1 cohort.

MinerU uses the inspected, pinned 2.7.6 full-PDF `do_parse` implementation and
mineru-vl-utils 0.1.19.1; 4.0.12's changed default checkpoints/backends are not used.
The exact requested Pro model remains `d3f5e08d073c21466bbabe21c71bb1e9c2e595da`,
weight SHA `f2650d91aaa619534980445034f62cde27fc3fa0430aaf5c3302b91179cad0c5`.
Before first inference, float16 is registered for T4 compatibility instead of
checkpoint BF16. Stock Transformers loading supplies the exact model/processor
through the version-verified official predictor injection point; the workflow
still renders PDFs, performs two-step extraction, and writes full middle/model
JSON/content outputs. No standalone image-demo result is counted as full parsing.

PaddleOCR-VL v1 source SHA-256:
`756a4095e05815be7b8d4421d834c3b54b6e2ad8a449c51a1ee461bf39faf80e`.
Full pipeline layout model is PP-DocLayoutV3, revision
`241f8bdfc77a7c7bee915a5057aaee58c235a8d3`; VLM revision is the frozen
`c5630abae1d940eafe0697512a0325494b02ab42`. All required selected weight SHA pins,
environment top-level package pins, three identical synthetic input hashes and
downloaded artifacts were verified. Native page JSON retains layout, recognized
blocks/HTML and native metadata. Authored line diagnostics: **11/11** (3/3, 4/4,
4/4). Constructor 21.6266–22.3212 s; conversion 21.8099–55.2855 s. No standalone
VLM invocation was substituted. CPU execution does not establish CUDA-model PASS.

MinerU v2 source SHA-256:
`02db63749a1c6d107a223581130614a9cf15201ac098816e6ca6baab39896f61`.
Actual runtime: Torch 2.8.0+cu128, CUDA 12.8, Tesla T4/CUDA0, NVIDIA driver
580.178.04. Each model parameter was on `cuda:0`, float16. Observed CUDA-output
forward counts: **88 / 116 / 82** for prose/numbers/rows, not just allocation or
device enumeration. Peak framework allocated CUDA memory **2,784,383,488 bytes**;
sampled device-0 used peak **3,618,635,776 bytes** (includes baseline). No second-GPU
pooling or CPU fallback. Full model JSON, middle JSON, content lists, image crop,
Markdown sidecar and native CUDA proofs were downloaded and checksum-verified.

The original MinerU adapter scored only 7/11 authored lines because it visited
top-level `para_blocks.lines` and skipped the actual nested table `blocks` holding
caption and HTML body. On identical preserved native captures, the pre-fix code
at `3d9a787` gives per-case **3/3, 4/4, 0/4**; the corrected adapter gives
**3/3, 4/4, 4/4**. The regression first failed (**1 failed, 1 passed, 29 deselected**),
then passed. The fix follows explicit native child edges and projects visible HTML
text, preserving actual parent/page references and leaving unverified cell links
and coordinate basis UNKNOWN. This is recovered native evidence, not a new model
result or fabricated table Gold. Existing v4 protocols/captures remain immutable;
future local runs must freeze new code pins for this adapter revision.

The missing-pinned-weight preflight regression was reproduced locally (**1 failed,
3 passed**) and fixed to reject absent required files rather than only comparing
hashes of existing files. Affected extraction/Kaggle/Gold regression suite then
passed **229 tests, 10.48 s**. Later CUDA/table-adapter checks and final verification
are recorded below.

### Final Marker evidence and consolidated R0 results

Marker version 4 source SHA-256:
`a262ea3248e815c48737d767da1ab28ccd3048152efb4e3ba62ee57c5c24608a`.
All three server logs explicitly report **25/25 layers offloaded to GPU**, identify
CUDA0, and record actual generation. Device-0 sampled used peak is
**1,972,371,456 bytes** (baseline included). The full balanced PDF pipeline produces
native structured JSON with no external LLM. Conversion including lazy startup:
98.1974–100.3055 s. All three native JSON values and adapted observations match
the prior v3 captures exactly; the earlier missing-proof failures remain failures.
This small diagnostic repeat is not an independently scored paired R1 comparison.

Marker preserves **9/11 authored lines**: 2/3 prose, 3/4 numeric, 4/4 aligned rows.
The first heading line is absent from native rendered JSON on the first two
controls; it is not discarded by the adapter. Upstream rendering supports header
suppression, but these captures do not prove the exact internal cause. No header
retention setting was tuned to repair the measured answer. This remains a known
synthetic evidence omission, not a quality PASS or an approved deployment candidate.

| Final frozen R0 system | Execution / cases | Whole-worker seconds, min–max | Tree RSS peak range, GiB | Device used peak, GiB | Authored line diagnostic |
| --- | --- | ---: | ---: | ---: | --- |
| Docling 2.55.1 FAST/no OCR | PASS, 3/3, CPU | 7.42–8.03 | 0.93–0.96 | N/A, CPU | 11/11 |
| Marker 2.0.0 balanced/Surya 0.22.1 | PASS, 3/3, CUDA0 + CPU auxiliary models | 120.99–123.40 | 2.60–2.63 | 1.84 | 9/11; two heading omissions |
| PP-StructureV3 / PaddleOCR 3.7.0 | PASS, 3/3, CPU, oneDNN disabled | 68.94–70.91 | 12.29–12.31 | N/A, CPU | 9/11; numeric-column concatenation |
| PaddleOCR-VL-1.6 full 0.9B pipeline | PASS, 3/3, CPU | 52.89–86.60 | 9.04–9.13 | N/A, CPU | 11/11 |
| MinerU2.5-Pro-2604-1.2B / full 2.7.6 workflow | PASS, 3/3, CUDA0 float16 | 19.97–21.94 | 2.85–3.21 | 3.37 | 11/11 after native-adapter repair |

GiB = 2^30 bytes. RSS is sampled process-tree RSS, not PSS or kernel-wide RAM;
device used includes baseline and is not framework allocated memory. RAM samples
are approximately 0.2 s, device samples approximately 1 s; short peaks may be missed.
Each document uses a new worker/model process with public weights already staged;
these are process-cold measurements, not steady-throughput benchmarks. Three tiny
purposive cases do not support meaningful P95, language, scan, layout, formula,
table-fidelity or generalization estimates. No such scores are invented.

Complete remote extraction population: **11 kernel versions, 33 scheduled document
attempts on only 3 distinct synthetic originals**: **15 completed, 12 failed,
6 not started**. The separate runtime matrix preflight is not a document run.
Every failure/not-started remains in the safe results with its denominator and
UNKNOWN line observations. The failed CUDA-proof run is not retroactively passed.
Private native-baseline admissions/bootstrap attempts remain a separate population.
Machine-readable [sanitized results](extraction_campaign_20261023_kaggle_results.json)
retain all attempts, source/environment/model fingerprints, exact case/resource
counts and the explicit native-adapter SHA. Complete native payloads, model
inventories, environment snapshots and logs remain local/ignored.

All final pulled metadata confirms private visibility and zero dataset,
competition, kernel or model inputs. LF-normalized pulled source hashes match
each staged script. Observed base image for all five latest kernels:
`gcr.io/kaggle-private-byod/python@sha256:9a6bcfda6d03b2cd9aa347ee8c1bae62043328ed0f4afe9bda014e4f8bbf9435`.
This is an observed image identity, not an assurance that a future default image
will remain unchanged. Final `kaggle quota --format json`: **14.36 h used /
15.64 h remaining / 30 h GPU**, same reset; TPU 0/20 h. Quota is shared with the
account, so the 1.46 h observed difference is not exclusively attributed to this
campaign. All campaign kernels reached terminal COMPLETE; experimental statuses
are separately recorded above. No shared kernels/datasets were deleted or stopped.
An initial PP-Structure staging/submission command was not executed when automatic
approval review reported a usage-limit failure. It created no kernel/version or
transfer. After the user's continue instruction, the authorized command executed;
this review-service incident is separate from the 33 remote document attempts.

### Final verification, Git and remaining boundary

Executed final command:

```powershell
.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_kaggle.py tests/unit/test_extraction_campaign.py tests/unit/test_docling_candidate.py tests/unit/test_extraction_fidelity.py tests/unit/test_fidelity_duplicate_keys.py tests/unit/test_dataset_readiness.py tests/unit/test_document_ir.py -q -p no:cacheprovider --basetemp=.pytest_cache/research-kaggle-closed -x --tb=short
```

**231 passed, 15.42 s**. The focused CUDA-init test also rejects CPU fallback.
Ruff check and format check on the affected campaign/Kaggle code and tests: PASS.
`git diff --check`: PASS. Final downloaded reports/artifacts were checked against
all declared SHA-256 values; accepted package pins, model revisions/required weight
hashes and all synthetic input identities match. The old/current MinerU adapter
comparison uses identical captures and independently retains the native SHA.

`git diff 3d9a787 -- src pyproject.toml uv.lock alembic` is empty. The production
venv distribution fingerprint still matches `native-low-memory.json`; seven
manifest/Gold/readiness pins and all eleven original-source pins remain unchanged.
The focused adapter fix is commit **17cd03a8098570e5c0ad417f90a55cd44130fcd3**,
`fix(research): retain MinerU nested native table evidence`. R0 infrastructure,
safe evidence and this report form a separate verified commit. Initial submissions
were staged at HEAD `3d9a7878bdc9fb3cb79049281d13684b78bfe6ce`; the final Marker
proof repeat was staged after the adapter commit, at HEAD `17cd03a8098570e5c0ad417f90a55cd44130fcd3`.
Each has explicit uncommitted runner SHA pins; the repository itself was not uploaded.
No push/merge.
The user-owned independent audit is preserved and excluded from both commits.

**Overall STATUS: BLOCKED for the complete original-cohort research campaign;
technical R0 execution PASS for all five systems.** R1/R2/R3 are not claimed as
executed. The authoritative readiness inventory's external-processing column is
NOT_EVALUATED for these originals; it states: “A dataset-card license, public URL,
corpus access or structural validator cannot fill missing source rights.” The
current authorization admits approved public/synthetic experiments, not a silent
upgrade of those source-specific qualifications. No confirmation/review was sought
and no unapproved transfer occurred. R2/R3 quality tuning is not defensible without
the frozen eligible R1 comparison. General quality/QG acceptance and experiment
promotion remain **NOT_EVALUATED / INCONCLUSIVE**, with the two demonstrated
synthetic omission mechanisms explicitly retained. No production approval follows.

SKIPPED/BLOCKED: original-cohort remote paired measurements/Gold scoring; reviewed
full transcripts/table-cell Gold, CER/WER/GriTS/TEDS/layout/formula metrics; real
RU/KK/scan coverage and sealed independent evaluation. Those inputs/qualifications
are absent. Service/DB/migration/release tests are outside this research-only change;
no production readiness is claimed. Stop at this step.
