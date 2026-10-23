# Five-system extraction research campaign — execution record

Campaign requested 23 October 2026 (Asia/Qyzylorda). Starting branch
`codex/extraction-engine-integration`, HEAD
`2bbcbdc696ebe3a0cb514d9a4e3732317299278f`; research branch
`codex/extraction-research-20261023`. The preexisting untracked
`docs/eda/independent_engineering_audit_20261020.md` is user-owned and excluded.
This record is in progress until its final consolidated verdict below.

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
No cloud workload or upload is authorized/started by this campaign.

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
