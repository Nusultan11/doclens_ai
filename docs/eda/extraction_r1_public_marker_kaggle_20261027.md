# R1-public Р Р†Р вЂљРІР‚Сњ Marker 2.0 versus verified Native and Docling

27 October 2026. **Execution/evidence STATUS: PASS.** Private notebook
[`nurs2005/doclens-marker-r1-public-20261027`](https://www.kaggle.com/code/nurs2005/doclens-marker-r1-public-20261027),
**version 2, COMPLETE**, downloaded and verified. **Experiment verdict: INCONCLUSIVE** (independent semantic evidence unavailable).
**Independent semantic quality and QG-01: NOT_EVALUATED.** No production promotion.

Both passes retained 37,755/41,576 Native tokens (90.81%), 1,498/1,841 numeric
tokens (81.37%) and 2,415/3,300 same-page chunks (73.18%). All 65 original page
IDs are present in each pass, with no page ID outside source bounds.

## Frozen cohort and execution

Exactly the existing Docling R1-public cohort: **11 real JOSS PDFs, 65 pages**;
same opaque IDs, original SHA-256/size, DEV/family bindings and source-specific
CC-BY-4.0 permission records. No replacement, synthetic substitution, TEST/QA,
sealed source or unresolved original DEV document was admitted. Source pages,
attribution and licence evidence remain in the frozen private cohort. The original
11-source cloud-UNRESOLVED cohort remains excluded. The papers share a publisher
template; this is exposed DEV evidence, not independent generalization evidence.

Two complete sequential passes used fresh worker processes and separate profiles.
The **22 verified Native captures** from Docling version 2 were reused after
checking their complete checksum manifest, source bindings and deterministic captures;
Native was not rerun. Current candidate code imports only three explicitly embedded
committed helper/adapter modules; unrelated uncommitted campaign changes are excluded.

**Marker 2.0.0 / Surya 0.22.1**, the successful R0 v4 balanced full-PDF pipeline:
`mode=balanced`, `use_llm=false`, `disable_ocr=false`; seed 0, llama.cpp b11617,
pinned GGUF/layout/OCR-error/font/runtime bytes. The complete 87-file inventory was
checked before/after workers and at run completion. Package versions are pinned to
the actual successful R0 environment, including Torch 2.8.0+cpu and Transformers
5.12.1. CPU Torch auxiliaries do not imply CPU-only inference: the Surya
llama.cpp model actually executes on CUDA0. Balanced-mode VLM layout/recognition
and CPU auxiliaries must not be described as an entirely GPU pipeline.

Actual Python: **3.13.15**; host CPUs: **4**;
host RAM: **33,658,155,008 bytes**. GPU inventory: Tesla T4 x2;
only device 0 is selected, with no VRAM pooling. The actual GPU image matches R0 v4:
`9a6bcfda6d03b2cd9aa347ee8c1bae62043328ed0f4afe9bda014e4f8bbf9435`.
Run UTC: `2026-10-27T11:03:42.564717+00:00` to `2026-10-27T12:36:55.155266+00:00`.

**22/22 Marker attempts and outputs accounted for: 11/11 completed in each pass.**
Worker statuses: `{"completed": 22}`. Every successful
native JSON has a source-bound receipt, actual model-path log, 25/25 GPU layer
offload and positive generated-token evaluation records. CUDA enumeration alone
was not accepted. No CPU fallback, timeout or selectively retried document is hidden.
Running/unverified owned PIDs after cleanup: **0**;
non-running zombie entries: **0**.

## Retention against Native

The exact Docling metrics are reused: Unicode word/punctuation token multisets,
signed/leading-zero-preserving numeric token multisets, and whitespace-normalized
eight-word chunks checked anywhere and on the original page. Counts are technical
Native-relative matches. Unmatched text/numbers are not adjudicated source errors;
markup, formatting and extraction changes are not repaired or silently normalized.

| ID | Status R1/R2 | Tokens retained R1/R2 / Native | Numbers retained R1/R2 / Native | Same-page chunks R1/R2 / Native | Export repeat |
| --- | --- | ---: | ---: | ---: | --- |
| rp-0001 | completed/completed | 4013/4013 / 4599 | 174/174 / 220 | 200/200 / 327 | AGREE |
| rp-0002 | completed/completed | 2453/2453 / 2678 | 69/69 / 88 | 173/173 / 222 | AGREE |
| rp-0003 | completed/completed | 3209/3209 / 3512 | 126/126 / 157 | 197/197 / 280 | AGREE |
| rp-0004 | completed/completed | 2669/2669 / 2904 | 88/88 / 108 | 180/180 / 243 | AGREE |
| rp-0005 | completed/completed | 3983/3983 / 4336 | 163/163 / 199 | 259/259 / 352 | AGREE |
| rp-0006 | completed/completed | 3203/3203 / 3538 | 147/147 / 178 | 204/204 / 290 | AGREE |
| rp-0007 | completed/completed | 3216/3216 / 3546 | 142/142 / 176 | 204/204 / 278 | AGREE |
| rp-0008 | completed/completed | 5491/5491 / 5893 | 167/167 / 207 | 364/364 / 450 | AGREE |
| rp-0009 | completed/completed | 3841/3841 / 4142 | 163/163 / 193 | 247/247 / 326 | AGREE |
| rp-0010 | completed/completed | 2977/2977 / 3453 | 125/125 / 155 | 228/228 / 308 | AGREE |
| rp-0011 | completed/completed | 2700/2700 / 2975 | 134/134 / 160 | 159/159 / 224 | AGREE |

| Aggregate per pass | Marker R1 | Marker R2 |
| --- | ---: | ---: |
| tokens_retained | 37755 | 37755 |
| tokens_native | 41576 | 41576 |
| numeric_retained | 1498 | 1498 |
| numeric_native | 1841 | 1841 |
| chunks_retained | 2430 | 2430 |
| page_chunks_retained | 2415 | 2415 |
| chunks | 3300 | 3300 |
| tokens_lost | 3821 | 3821 |
| tokens_added | 674 | 674 |
| numeric_lost | 343 | 343 |
| numeric_added | 8 | 8 |
| unknown_documents | 0 | 0 |

Docling retains its two rp-0001 RSS failures in the 22-attempt denominator.
Its conditional measurements cover ten documents per pass; the following Marker
comparison uses those same ten documents, rather than mixing cohort denominators:

| Same ten documents, per pass | Marker R1 | Marker R2 | Docling R1/R2 |
| --- | ---: | ---: | ---: |
| tokens_retained | 33742 | 33742 | 36568 / 36568 |
| tokens_native | 36977 | 36977 | 36977 / 36977 |
| numeric_retained | 1324 | 1324 | 1609 / 1609 |
| numeric_native | 1621 | 1621 | 1621 / 1621 |
| page_chunks_retained | 2215 | 2215 | 2244 / 2244 |
| chunks | 2973 | 2973 | 2973 / 2973 |

On the same ten measurable documents, Marker retained fewer Native tokens and
numeric tokens than Docling, and 2,215 versus 2,244 same-page chunks. Marker also
completed rp-0001, which exceeded Docling's RSS cap. Different device/resource
limits prevent an equal-budget recovery or speed claim. These are technical
observations; no source error or semantic quality verdict is inferred.

## Structure, repetition and resource cost

**11/11 complete deterministic observations agree** between passes.
Mismatch identities: `[]`. Full native JSON, actual block/page IDs,
emitted order, HTML tables/cells/spans, geometry, equations and metadata are retained.
Only declared worker/conversion timing fields are excluded from context comparisons;
source/status/native structural captures and observation fingerprints are compared
separately from runtime metrics. The private ledger retains every native export
difference, not merely an aggregate agreement flag.

| Native Marker structure | Pass 1 | Pass 2 |
| --- | ---: | ---: |
| Page blocks | 65 | 65 |
| Text blocks | 371 | 371 |
| SectionHeader blocks | 145 | 145 |
| Table blocks | 5 | 5 |
| TableCell blocks | 0 | 0 |
| Equation blocks | 5 | 5 |
| Figure blocks | 10 | 10 |
| Diagram blocks | 4 | 4 |
| Emitted HTML table elements | 5 | 5 |
| Emitted HTML tr elements | 47 | 47 |
| Emitted HTML td elements | 123 | 123 |
| Emitted HTML th elements | 16 | 16 |

Native provides page text and no structured table blocks for these PDFs. Docling
emitted five tables / 136 cells per successful ten-document pass. Structural counts
are predictions, not reviewed correct-table/cell counts. Marker geometry and
relationships remain exactly as emitted; no coordinate basis or missing cell link
is invented by the adapter. Reading-order accuracy, table/cell correctness, numeric
truth, equation equivalence, locator accuracy, CER/WER and semantic completeness
are all **NOT_EVALUATED**.

| All 22 attempts | Wall P50 / P95, seconds | Tree RSS P50 / P95, GiB |
| --- | ---: | ---: |
| Native | 1.016 / 1.170 | 0.066 / 0.073 |
| Docling | 27.249 / 31.608 | 1.330 / 1.499 |
| Marker | 225.507 / 457.259 | 3.512 / 4.244 |

Marker sampled device-0 GPU-used peak: **2,169,503,744 bytes**,
including the device baseline, not Torch allocated memory. RSS is sampled worker-tree
sum every 50 ms; GPU device memory/utilization approximately every second. Shared
pages may be counted more than once; samples can miss short peaks. Wall time includes
fresh-worker imports, hashing, lazy model/server startup, complete conversion, export
and owned cleanup; it is not pure GPU forward time. No steady-state throughput is claimed.

Isolated package setup took **76.171 s**; pinned model/runtime acquisition took
**29.720 s**, separately from the 22 worker measurements.

Marker limits were frozen before inference: sequential worker, **600 s/document**,
**24 GiB tree RSS**, **26 GiB available-RAM admission**, 32 GiB per-process RLIMIT_DATA,
1200 CPU seconds/process, eight sampled processes, 256 MiB file/scratch caps and
2 GiB aggregate output cap; setup/model acquisition have separate 1200/900 s bounds.
Docling used CPU/FAST, 600 s and **1.5 GiB tree RSS**, with 4 GiB RLIMIT_DATA;
Native used a 120 s deadline. Marker used CUDA and a different GPU image. These
resource costs are observed configurations, not equal-budget model speed comparisons.

## Preserved operational failure and verification

Version 1 is preserved separately: **five emitted conversions, five cleanup-unverified
receipts and 17 resource-blocked-before-start observations**; neither repetition
was complete. All **247 checksummed artifacts** were downloaded and verified.
Each remaining owned PID matches its OCR-error server record. The Docling helper
killed the process group but lacked the R0 explicit escaped-descendant cleanup.
Final OS states were not recorded in v1, so running versus zombie is not invented.
The single preregistered operational retry restored PID-plus-creation-time-owned
cleanup, preserved the original worker outcome and reported zombies separately.
The cohort, model/configuration/package pins, metrics and all numerical limits
were unchanged. Version 2 ran two completely fresh passes; no v1 output was
substituted into either repetition. The retirement of extraction_remote.py is preserved.

Version 2: **866 checksummed artifacts plus checksums.json**,
**2,067,738,913 bytes**. This total includes isolated CUDA compiler caches,
not just extraction JSON. The slow per-file CLI download was retained partially;
a version-bound output ZIP was retrieved through the installed Kaggle SDK and
safely extracted to `archive-download-2/`. The archive is 494,368,945 bytes;
SHA-256 `c64f78a0218d74ddaa1fa90d1fe86343b91d6c5415a885dd9c4a995642858631`.
Only the matching redundant local CLI downloader was stopped after full archive
verification; no user application or Kaggle job was stopped. Every declared checksum and source/model/code/environment
postcheck passed. All observations, structures, metrics, percentiles and repetition
fingerprints were recomputed locally. Positive generated-token CUDA inference and
actual model paths were verified per conversion. Wrapper sitecustomize/missing-wrapt
and nbconvert syntax warnings are retained; they did not prevent either completed pass.

Actual command selection (project .venv Python; private directories are ignored).
The archive used the installed CLI's Python 3.12 interpreter and
`download_archive.py`; exact local invocation and cleanup identity are retained
privately in `archive-command-and-cleanup.json`. This was read-only retrieval,
not an additional notebook execution:

```powershell
kaggle --version  # 2.2.4; authenticated account nurs2005
kaggle kernels list --mine --page-size 4
.venv/Scripts/python.exe evaluation-output/kaggle-marker-r1-public-20261027/freeze_stage.py
kaggle kernels push -p evaluation-output/kaggle-marker-r1-public-20261027/stage-1 --accelerator NvidiaTeslaT4 --timeout 18000
kaggle kernels output nurs2005/doclens-marker-r1-public-20261027 -p evaluation-output/kaggle-marker-r1-public-20261027/download-1
.venv/Scripts/python.exe evaluation-output/kaggle-marker-r1-public-20261027/verify_download.py 1
.venv/Scripts/python.exe evaluation-output/kaggle-marker-r1-public-20261027/freeze_stage_v2.py
kaggle kernels push -p evaluation-output/kaggle-marker-r1-public-20261027/stage-2 --accelerator NvidiaTeslaT4 --timeout 18000
kaggle kernels status nurs2005/doclens-marker-r1-public-20261027
kaggle kernels output nurs2005/doclens-marker-r1-public-20261027 -p evaluation-output/kaggle-marker-r1-public-20261027/download-2
# Partial CLI transfer retained; complete SDK archive retrieval: download_archive.py
kaggle kernels pull nurs2005/doclens-marker-r1-public-20261027 -p evaluation-output/kaggle-marker-r1-public-20261027/metadata-2 --metadata
kaggle kernels logs nurs2005/doclens-marker-r1-public-20261027
.venv/Scripts/python.exe evaluation-output/kaggle-marker-r1-public-20261027/verify_download.py 2
.venv/Scripts/python.exe evaluation-output/kaggle-marker-r1-public-20261027/postprocess.py
.venv/Scripts/python.exe -m pytest tests/unit/test_marker_r1_public.py tests/unit/test_docling_r1_public.py tests/unit/test_extraction_kaggle.py -q --tb=short --basetemp evaluation-output/kaggle-marker-r1-public-20261027/tests-independent-control --junitxml evaluation-output/kaggle-marker-r1-public-20261027/tests-independent-control.xml
# 43 passed in 2.67s
.venv/Scripts/python.exe -m pytest tests/unit/test_extraction_campaign.py::test_marker_html_entities_and_source_page_do_not_invent_geometry -q --tb=short --basetemp evaluation-output/kaggle-marker-r1-public-20261027/tests-marker-adapter --junitxml evaluation-output/kaggle-marker-r1-public-20261027/tests-marker-adapter.xml
# 1 passed in 0.21s; selected test function unchanged from HEAD
.venv/Scripts/python.exe -m ruff check tools/kaggle_gpu/marker_r1_public.py tests/unit/test_marker_r1_public.py
.venv/Scripts/python.exe -m ruff format --check tools/kaggle_gpu/marker_r1_public.py tests/unit/test_marker_r1_public.py
git diff --check
git diff --cached --stat
git status --short
```

Ruff/format and `git diff --check` passed; staging is empty. New-file
`git diff --no-index --check -- NUL PATH` returns the expected difference status
1 with no whitespace diagnostics (only Windows LF/CRLF notices); an initial local
wrapper assertion was corrected to recognize this normal new-file result.
Negative checks cover denied/TEST/QA sources, helper hashes,
missing results, CUDA-only enumeration/offload, PID reuse, escaped cleanup, and
RAM/wall/process/artifact limits. An intermediate timing-fixture failure was fixed
with a deterministic test clock; the final suite above passed. The private verifier
initially compared Python tuples with JSON lists; canonical JSON fingerprints fixed
that representation-only check, without changing captured outputs.

## Fingerprints and private evidence

- Git HEAD: `30bd689e8b2bf8f3edcadf1ea9ec5d3627d97b17` (experimental runner uncommitted).
- Both deterministic pass fingerprints: `5d1601afc5f86eea07e50c3d89c1ba9157ca69fb35db587698de4b332e19ef30`.
- Cohort: `bd9739b0011e529a389e6be567e41a1444aa52db6b029a174c3fc08e194c3862`.
- Submitted v2 runner: `3dec368f3ff0ccea7dcaf67d0944db2a64bcfa7cdeaa4eff4a41fe594fd3da69`.
- Full frozen v2 configuration: `6638aae3ea256ad97f32ce381d7b38dc902f59e5fc6e76b629306d11f420a39d`.
- Model/runtime inventory: `b7fbe978dd5b533a617dff61640ae7fa1cf47b59900c4ea9c4b4da39d1a8ce38`.
- Environment: `99d0b5d4280bed7a32ac3add92236a88748806e47ef801bc6c789ef7f54e84e0`.
- Run report: `f966eec292ebe738d1fcaece1c6677e9e4a51d4f6f664ace905ca9882e9387f2`.
- Download checksums manifest: `ee96bc414cf50a42023216f62bec22621aadbe6d084b85624ef5dcb35224d975`.
- Verified final summary: `e67e8518df203849793579b6e68975a57b7aacfc9bcdfe99ae25802de8a2383b`.

Private root: `evaluation-output/kaggle-marker-r1-public-20261027/`.
Inspect `FINAL.json`, `complete-private-ledger.json`, `paired-evidence-2.json`,
`archive-download-2/marker-r1-public/report.json` and each repeat/opaque-ID directory.
Both configurations/stages, metadata, full logs, v1 diagnosis, tests and failed
attempts are retained. No source text, native capture, credential or Gold is published.
Source facts and licence evidence are distinct from machine predictions and independent Gold.
Historical R0 synthetic controls establish compatibility only; no semantic promotion follows.
No production parser, frozen historical experiment or independent Gold was modified.
No repository commit or push was performed.

References: [Docling R1-public baseline](extraction_r1_public_kaggle_20261027.md),
[Marker 2.0 model/shutdown implementation](https://github.com/datalab-to/marker/blob/v2.0.0/marker/models.py),
[Surya 0.22.1 OCR-error client](https://github.com/datalab-to/surya/blob/v0.22.1/surya/ocr_error/client.py).
