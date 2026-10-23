# Extraction-only Kaggle R0

This is the continuation of the frozen 2026-10-23 extraction campaign. It runs
three authored synthetic, born-digital, single-page PDFs. It does not upload the
original corpus, private Gold, repository, credentials, or production dependencies.
These controls are technical compatibility checks, not approved extraction Gold.

`extraction_registry.json` freezes the selected package/model revisions and weight
hashes. Each kernel installs into `/tmp/extraction-env`, stages public models in
`/tmp/extraction-models`, and processes cases sequentially. The uploaded directory
contains exactly `runner.py` and private `kernel-metadata.json`; its hash manifest
is retained outside that directory. Candidate internet access is needed for public
acquisition. Python socket connections during inference are restricted to loopback;
this is not an OS egress sandbox. No external inference service is configured.

From the repository root, create a **new** directory and unique run ID:

```powershell
.venv/Scripts/python.exe -m tools.kaggle_gpu.extraction_stage docling evaluation-output/extraction-campaign-20261023/kaggle/NEW-STAGE --run-id UNIQUE-RUN-ID
kaggle kernels push -p evaluation-output/extraction-campaign-20261023/kaggle/NEW-STAGE --accelerator NvidiaTeslaT4 --timeout 3900
kaggle kernels status nurs2005/doclens-extraction-docling-r0
kaggle kernels logs nurs2005/doclens-extraction-docling-r0
kaggle kernels output nurs2005/doclens-extraction-docling-r0 -p evaluation-output/extraction-campaign-20261023/kaggle/NEW-OUTPUT
kaggle kernels pull nurs2005/doclens-extraction-docling-r0 -p evaluation-output/extraction-campaign-20261023/kaggle/NEW-METADATA --metadata
```

Supported candidates are `docling`, `marker`, `ppstructure`, `paddlevl`, `mineru`.
Change the slug accordingly. Never overlap submissions. Retain the push version,
terminal status, logs, source/metadata, and all failed attempts. CLI 2.2.4 output
and logs address the latest session, so download before the next push of that slug.
No input datasets or collaborators are added. Check pulled metadata remains private.

Each worker has a 600-second document deadline and sampled 24 GiB tree-RSS cap.
Setup and public model acquisition have separate 1200/900-second bounds. The kernel
has a 3900-second outer deadline, which can interrupt an overlong aggregate run;
missing final reports/provenance must remain UNKNOWN. Later runner revisions also
bound exported artifacts to 256 MiB. Sampled RSS can miss short peaks. Device-0
GPU-used memory includes the baseline; it is not per-model allocated memory.
Docling and Paddle CPU runs declare CPU explicitly; no GPU-model claim follows
from using an accelerated notebook. MinerU requires observed CUDA forward results.

Before accepting a download, call `extraction_stage.verify` on its `extraction/`
directory using the submitted LF-normalized `runner.py` SHA-256 and unique run ID.
It verifies every declared output checksum and rejects stale identities and unsafe
paths. Separately inspect native outputs, model/environment identities, privacy,
status and errors. A completed Kaggle kernel can contain a blocked/failed experiment.
Raw outputs and full logs remain ignored under `evaluation-output/`.

R1 on the existing 11-source cohort requires explicit authorization to transfer
those documents. Its private Gold remains local. No quality thresholds, annotations,
sealed splits, production code/defaults or release status are changed by R0.
