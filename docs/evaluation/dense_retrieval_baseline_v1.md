# Offline dense retrieval + Qdrant v1

## Scope and frozen experiment

This is a local CPU retrieval experiment, not production ingestion, a business-data store,
authorization, or generation. PostgreSQL remains the future canonical source of truth;
Qdrant holds disposable derived vectors only. Existing extraction, structure-aware chunking,
Gold, evaluator, BM25, API, coordinators, and migrations are unchanged. ML dependencies are an
optional `dense` extra; the production API image still installs only backend dependencies.

The first completed frozen run is v1. No model, chunking, search parameters, or labels were tuned
against held-out feedback. One index contains all eligible sources and serves both dev and test.
Gold is used only to validate frozen identities and score completed rankings, never for vector
generation, source filters, or ranking hints. The repository ingestion-change and rag-evaluation
skills guided explicit handoffs, stable identities, full-index failure safety, and separate
quality/security/latency reporting.

Pre-evaluation hypothesis: test whether this local dense model improves first-relevant ranking
while maintaining evidence coverage relative to BM25. Expected failure modes include exact numeric
identifier confusion, structurally dense XLSX cells, token truncation losing evidence, and lexical
or semantic candidates for negative queries. This is a comparison hypothesis, not an improvement
claim or a reason to tune against the test split.

## Model and resource policy

Model: `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`. The publicly licensed MIT model executes locally;
no questions or document content are sent to external inference APIs. Only public model assets
are downloaded. All five model/config/tokenizer files are SHA-256 checked against pinned bytes.

Configuration frozen before evaluation: CPU float32, batch 2, four intra-op threads and one
interop thread, seed 0, eval/inference mode, deterministic algorithms, eager attention.
Use documented `query: ` / `passage: ` prefixes, attention-mask mean pooling, and L2 normalization.
The tokenizer is XLMRobertaTokenizerFast from the same revision; maximum 512 tokens including
prefix/special tokens, right truncation, longest-in-batch padding. Original token lengths are
measured before truncation. No silent dropping, alternate models, quantization, or GPU fallback.

Installed inference versions: PyTorch 2.8.0+cpu, Transformers 4.57.6, huggingface-hub 0.36.0,
tokenizers 0.22.2, safetensors 0.8.0, NumPy 2.5.4. Versions are recorded in experiment metadata.
The inference path uses local files only and disables remote code; evaluation runs also set
`HF_HUB_OFFLINE=1`, disable Hugging Face telemetry, and disable tokenizer parallelism.

Preflight hardware: Windows 11 build 26200; Ryzen 7 5800HS, eight cores/16 logical processors;
15.41 GiB visible physical RAM, approximately 2.02 GiB free at preflight; approximately 466 GiB
free disk. Docker Desktop server 29.5.2 reports 16 CPUs and 7.46 GiB VM memory. Available RAM is
shared with existing applications; no unrelated process was stopped. A local model smoke test
returned one finite normalized 384-dimensional vector and peaked at 1,050,456,064 working-set bytes.
This established feasibility, not retrieval quality.

## Corpus identity and index safety

Starting HEAD: `a190c9aed6ab269ff478131b16562a863a09d5d2`, initially clean.
All 90 Corpus v1 source hashes and sizes were verified against the unchanged committed manifest.
The same gate produces 56 eligible documents and 1,092 chunks, excluding 34 needs-review sources.
Actual full chunk metadata and the text-sensitive BM25 index fingerprint must match the frozen
BM25 reference, or the dense experiment stops. No Gold-document-only subset is allowed.

| Frozen identity | Fingerprint |
| --- | --- |
| Corpus | `77854e7979caaeeaaa526c6dba57123a1661523a61e87ac45cfaa94a12267b99` |
| Chunking | `a7c53272ac7baa3f916e43dc4b96a455fa0daa1437cafe04fd7c90b2840edc4c` |
| Complete chunk metadata | `fb790b4d4777a679beeb287d2602e080a7beb0c65f20fcdde1cfb57d5a55e4f2` |
| Text-sensitive BM25 index | `986694d3cc7f41301e5d6331eb4f470fd69953d8a4f8852322ac5b26b7f8c096` |
| Gold | `d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94` |
| BM25 ranked results | `064bbdd32793c73bc352a34ad2dab69dc16f79faf623cbd3552d89df98917429` |
| BM25 evaluation report | `fea872420356de8ac4c0137f339b676e72737350499728c7a4aeca46d81587f0` |

Gold is 48 human-reviewed English questions: dev 36 (33 positive/three negative), test 12 positive;
80 positive evidence anchors, 15 selected documents. Retrieval indexes all 56 eligible documents,
not just those 15. BM25 reference rankings are revalidated and rescored with the unchanged evaluator.

Qdrant v1.15.4 image digest:
`sha256:6ac4807063bbecddca0250bfbcff52acf18c22263b904d12919349e6d0a408f1`.
The actual server version is checked before creation. Docker is disposable, has no persistent
volume, uses a separate task network and a dynamic port published only on 127.0.0.1, and is
limited to two CPUs/512 MiB RAM. Telemetry is disabled. Compose and production services are unchanged.

One cosine vector per chunk, dimension validated from actual model output. Point UUIDv5 derives
from source SHA plus stable chunk ID, not query IDs or runtime randomness. Payload includes only
chunk ID, source SHA, format, ordinal, and chunker fingerprint; no chunk text. Provenance is rebuilt
from the complete local source-to-chunk mapping, using existing normalized source-unit offsets.

Every upsert waits for completion. Before querying (and again afterward), verify exact point count,
all identities, exact payloads, finite normalized vector dimensions, and stored vectors against
original embeddings. Model/inference errors, partial upserts, unknown identities, malformed metadata,
unavailable Qdrant, changed inputs, and incomplete indices fail the experiment; no partial successful
quality report is produced. Only a newly created `dense_v1_*` collection is owned and removed;
existing collections are refused and never overwritten or deleted.

Search is exact, no HNSW construction (`m=0`, indexing threshold 0), no quantization or filtering.
For reproducible ties at the rank-10 boundary, Qdrant returns the small complete 1,092-score pool;
the client sorts unrounded server scores descending, then stable chunk ID, and emits top 10.
This adds response/metadata-validation overhead and is not a scalable approximate-search design.
Any future ANN evaluation must separately measure recall, resources, latency, and tie policy.

## First frozen real-run measurements

Completed dense run 1 used all 1,092 points, dimension 384. Failed chunks: 0/1,092; queries: 0/48;
truncated chunks: 0/1,092; truncated queries: 0/48. The full stored point set and payloads were
verified before and after retrieval. These are actual full-corpus measurements, not synthetic
embedding-test results. Quality and timing files are separate.

| Dense identity | Fingerprint |
| --- | --- |
| Passage vector values, unrounded | `54f49100367c5b30220b19e3dbd90d7b2bb5e64527333fb4d0ca2f9d46f32f1f` |
| Sorted point identities | `a98c3bfe2da37892e3b41a200dc1218019e141a8cf2829eaaaab92c90c9c684a` |
| Evaluator normalized ranked results | `f236d4f85dca59c2d3ab76febb8a0316f31c921dff7ad6229b809bd833a1718c` |
| Evaluator report | `cd8add46905aa71584e9d8207de21c4e793ca99cbf3bf64387e9bea693c0f5ab` |
| Ranked JSONL bytes | `63f28f06f4db3bad523ba24bb27a390981ef87ff3a3c3c9c4e52e160e6301f76` |
| Quality-report bytes | `a57f8ae9abe20aa612b1cdd9f6885439b553ee7efbbf4b57152a84a5260912d7` |
| Experiment bytes | `1a6bfba500b451d6cd4a0bc57266e01559d65ba2830499826b8543eab2d77e6f` |

### Dev and held-out comparison

Fraction numerators/denominators are those serialized by the unchanged evaluator; decimal values
below retain its precision. Hit@1 is a separate diagnostic using the same evidence matcher,
not an evaluator contract change. Hit/MRR/nDCG exclude negatives; recall is micro-averaged
over evidence anchors. nDCG retains binary new-evidence gain and the one-result-per-anchor ideal,
so grouping several anchors into one chunk can limit nDCG even at a correct rank 1.

| Metric | Dense dev | BM25 dev | Dense held-out test | BM25 held-out test |
| --- | --- | --- | --- | --- |
| Hit@1 | 28/33 = 0.8484848484848485 | 30/33 = 0.9090909090909091 | 7/12 = 0.5833333333333334 | 7/12 = 0.5833333333333334 |
| Hit@5 | 33/33 = 1 | 32/33 = 0.969696969697 | 11/12 = 0.916666666667 | 12/12 = 1 |
| Hit@10 | 33/33 = 1 | 33/33 = 1 | 11/12 = 0.916666666667 | 12/12 = 1 |
| Recall@5 | 57/57 = 1 | 56/57 = 0.982456140351 | 20/23 = 0.869565217391 | 23/23 = 1 |
| Recall@10 | 57/57 = 1 | 57/57 = 1 | 20/23 = 0.869565217391 | 23/23 = 1 |
| MRR | 30.333333333333/33 = 0.919191919192 | 31.166666666667/33 = 0.944444444444 | 8.833333333333/12 = 0.736111111111 | 9.5/12 = 0.791666666667 |
| nDCG@10 | 25.936730326947/33 = 0.785961525059 | 26.245526285116/33 = 0.795318978337 | 7.495815463779/12 = 0.624651288648 | 7.813890584684/12 = 0.651157548724 |
| Missing-result rate | 0/36 = 0 | 0/36 = 0 | 0/12 = 0 | 0/12 = 0 |
| Query coverage | 36/36 = 1 | 36/36 = 1 | 12/12 = 1 | 12/12 = 1 |
| Negative result presence | 3/3 = 1 | 3/3 = 1 | 0/0 = null | 0/0 = null |

Dense overall: Hit@1 35/45 = 0.7777777777777778; Hit@5/10 both 44/45 = 0.977777777778;
Recall@5/10 both 77/80 = 0.9625; MRR 39.166666666667/45 = 0.87037037037;
nDCG@10 33.432545790725/45 = 0.742945462016; missing 0/48 = 0, coverage 48/48 = 1,
negative presence 3/3 = 1. BM25 overall Hit@10 is 45/45 and Recall@10 is 80/80.
Query coverage measures nonempty results; every query also has an explicit JSONL record.
Dense has no relevance threshold, so even negative questions return ten candidates. Neither
result-presence rate nor these retrieval metrics establish abstention or generated-answer quality.

### Dense per-category quality

| Category | Hit@5/10 | Recall@5/10 | MRR | nDCG@10 |
| --- | --- | --- | --- | --- |
| fact | 12/12 = 1 | 12/12 = 1 | 10.333333333333/12 = 0.861111111111 | 10.761859507143/12 = 0.896821625595 |
| identifier | 10/10 = 1 | 21/21 = 1 | 8.833333333333/10 = 0.883333333333 | 7.003628956292/10 = 0.700362895629 |
| number | 13/13 = 1 | 25/25 = 1 | 12.5/13 = 0.961538461538 | 10.220128784852/13 = 0.786163752681 |
| table | 7/8 = 0.875 | 17/20 = 0.85 | 5.5/8 = 0.6875 | 3.446928542438/8 = 0.430866067805 |
| version | 2/2 = 1 | 2/2 = 1 | 2/2 = 1 | 2/2 = 1 |
| unanswerable | 0/0 = null | 0/0 = null | 0/0 = null | 0/0 = null |

Coverage is n/n = 1 and missing-result rate 0/n = 0 for each category (n respectively
12, 10, 13, 8, 2, 3). Negative presence is 3/3 = 1 for unanswerable; otherwise 0/0 = null.

### Per-query first-relevant-rank differences

Ranks are top-10 first relevant evidence, not complete answer-quality judgments. `>10` means no
matched Gold evidence in returned top 10; `N/A` means the question has no positive evidence.
Five positives improve, eight worsen, 32 are unchanged; all three negatives return candidates.

| Opaque question ID | Split | BM25 rank | Dense rank |
| --- | --- | ---: | ---: |
| rgv1-q-001 | dev | 1 | 1 |
| rgv1-q-002 | dev | 1 | 1 |
| rgv1-q-003 | dev | 1 | 1 |
| rgv1-q-004 | dev | 1 | 1 |
| rgv1-q-005 | dev | 2 | 1 |
| rgv1-q-006 | dev | 2 | 1 |
| rgv1-q-007 | dev | 1 | 3 |
| rgv1-q-008 | dev | 1 | 2 |
| rgv1-q-009 | dev | 1 | 1 |
| rgv1-q-010 | test | 2 | 2 |
| rgv1-q-011 | test | 2 | 2 |
| rgv1-q-012 | test | 1 | 2 |
| rgv1-q-013 | dev | 1 | 2 |
| rgv1-q-014 | dev | 1 | 1 |
| rgv1-q-015 | dev | 1 | 1 |
| rgv1-q-016 | dev | 1 | 1 |
| rgv1-q-017 | dev | 1 | 1 |
| rgv1-q-018 | dev | 1 | 1 |
| rgv1-q-019 | dev | 1 | 1 |
| rgv1-q-020 | dev | 1 | 1 |
| rgv1-q-021 | dev | 1 | 1 |
| rgv1-q-022 | test | 2 | 1 |
| rgv1-q-023 | test | 1 | 1 |
| rgv1-q-024 | test | 1 | 1 |
| rgv1-q-025 | dev | 1 | 1 |
| rgv1-q-026 | dev | 6 | 1 |
| rgv1-q-027 | dev | 1 | 2 |
| rgv1-q-028 | dev | 1 | 1 |
| rgv1-q-029 | dev | 1 | 1 |
| rgv1-q-030 | dev | 1 | 1 |
| rgv1-q-031 | test | 2 | 1 |
| rgv1-q-032 | test | 1 | 1 |
| rgv1-q-033 | test | 1 | 1 |
| rgv1-q-034 | dev | 1 | 1 |
| rgv1-q-035 | dev | 1 | 1 |
| rgv1-q-036 | dev | 1 | 1 |
| rgv1-q-037 | dev | 1 | 1 |
| rgv1-q-038 | dev | 1 | 1 |
| rgv1-q-039 | dev | 1 | 1 |
| rgv1-q-040 | dev | 1 | 1 |
| rgv1-q-041 | dev | 1 | 2 |
| rgv1-q-042 | dev | 1 | 1 |
| rgv1-q-043 | test | 1 | 3 |
| rgv1-q-044 | test | 2 | >10 |
| rgv1-q-045 | test | 1 | 1 |
| rgv1-q-046 | dev | N/A | N/A |
| rgv1-q-047 | dev | N/A | N/A |
| rgv1-q-048 | dev | N/A | N/A |

`rgv1-q-044` is the only dense top-10 miss, a test/table case with three anchors. Frozen chunks
contain those anchors (BM25 retrieves them); no inputs were truncated and the complete point set
was verified. Thus this is a measured dense-ranking miss, not a smaller corpus or partial upsert.
No specific semantic cause is established by that observation alone.

### Observed resource and latency costs

Run 1, 48 warm query samples after one synthetic warm-up (not included in Gold metrics).
Process-cold model loading is measured separately; filesystem caches were not forcibly flushed.

| Stage | Run 1 |
| --- | ---: |
| Verified corpus extraction/chunking/reference preparation | 12,516.792500 ms |
| Model load, file hashing, imports | 7,020.416100 ms |
| Corpus embedding generation | 179,591.545400 ms |
| Collection creation/version handshake | 122.563900 ms |
| Complete point upsert | 746.313000 ms |
| Initial full-index verification | 470.821300 ms |
| Warm-up query embedding + search | 84.916900 ms |
| Query embedding p50/p95 | 21.891650 / 29.016260 ms |
| Qdrant search client p50/p95 | 58.546150 / 63.868830 ms |
| Offline end-to-end query p50/p95 | 82.210800 / 91.040050 ms |

Peak working set: 1,288,204,288 bytes (about 1.20 GiB), measured by Windows process peak counters.
One observed idle Qdrant snapshot was 18.71 MiB within its 512 MiB cap; that snapshot is not a
measured Qdrant peak-memory claim. CPU threads were bounded, not an exclusive hardware reservation.
Download time and initial dependency installation are outside inference/search timing.

Embedding latency includes query tokenization, pooling, normalization, and vector validation.
Qdrant client latency includes loopback HTTP, exact search, full candidate transfer, JSON parsing,
identity validation, and stable top-10 selection, not just server computation. End-to-end offline
retrieval additionally includes provenance projection and result construction. Serialization and
Gold scoring are outside per-query timings. Percentiles interpolate at `(n-1)*p`.
Frozen BM25 search p50/p95 was 1.483100/2.091125 ms, including lexical tokenization/scoring/sorting
but excluding evidence projection. Do not equate Qdrant-only cost with full dense query cost or
claim a controlled production latency comparison. These are single-machine offline measurements.

Independent run 2 observed preparation 12,658.094900 ms; model load 7,309.243800 ms;
corpus embeddings 179,527.686900 ms; collection creation 114.755100 ms; upsert 730.619400 ms;
initial verification 452.493600 ms; warm-up 79.024100 ms; peak working set 1,283,125,248 bytes.
Across 48 warm queries, embedding p50/p95 was 20.704000/25.277095 ms, Qdrant client search
58.348450/60.818055 ms, and offline end-to-end retrieval 80.875750/87.894960 ms.
These timings differ normally; no timing values contribute to deterministic fingerprints.

## Executed verification and reproducibility

Two independent real processes recreated full collections, re-embedded all frozen passages/queries,
and produced byte-identical `ranked_results.jsonl`, `quality_report.json`, `experiment.json`, and
`rank_diagnostics.json`. The exact unrounded passage-vector fingerprint and sorted point identities
also matched. No result/metric rounding was introduced to hide differences. This demonstrates
reproducibility on this fixed software/hardware environment, not bitwise equivalence across all
platforms or future library versions. The existing evaluator CLI produced a semantically identical
quality report; its pretty-printed JSON has a different file-byte hash than the compact runner file.

Actual real-run commands used this step's dynamically assigned Qdrant port:

```powershell
.venv/Scripts/python.exe -m doclens_ai.dense_baseline --qdrant-url http://127.0.0.1:50825 --output-dir evaluation-output/dense-v1-run-1
.venv/Scripts/python.exe -m doclens_ai.dense_baseline --qdrant-url http://127.0.0.1:50825 --output-dir evaluation-output/dense-v1-run-2
```

Both exited successfully, each with 1,092 indexed points, 384 dimensions, and the same recorded
ranked-results/report fingerprints. The server has since been removed; reproduction chooses a
new unused loopback port rather than assuming 50825 remains available.

Actual targeted command (Windows; approved unrestricted execution for localhost/Docker access):

```powershell
$env:TEST_QDRANT_URL='http://127.0.0.1:50825'
.venv/Scripts/python.exe -m pytest -q tests/unit/test_dense_baseline.py tests/integration/test_dense_qdrant.py tests/unit/test_bm25_baseline.py tests/unit/test_bm25_runner.py tests/unit/test_retrieval_eval.py
```

Result: 101 passed in 6.62s, including 34 dense unit cases, three real Qdrant integration cases,
and 64 unchanged BM25/evaluation tests. Initial 99-test verification also passed before adding
top-10-boundary and malformed-protocol regression cases. Ruff initially identified formatting and
one unused import in new files; formatting/import fixes were followed by a successful complete
`ruff check src tests alembic`. Tests were not weakened.

The localhost port above belonged only to this step's disposable Qdrant. PostgreSQL verification
uses Docker-network `postgres:5432`, never Windows localhost:5432. Fixture embeddings test algorithm
contracts only; the two real model/corpus runs establish the measured dense metrics in this report.

Comparison actually executed:

```powershell
foreach ($name in @('ranked_results.jsonl','quality_report.json','experiment.json','rank_diagnostics.json')) {
  $first = (Get-FileHash "evaluation-output/dense-v1-run-1/$name" -Algorithm SHA256).Hash
  $second = (Get-FileHash "evaluation-output/dense-v1-run-2/$name" -Algorithm SHA256).Hash
  if ($first -ne $second) { throw "Non-deterministic output: $name" }
}
```

Result: all four files identical. `git diff --check` passed; final complete diff/status and staged
privacy/scope checks are required before the task commit. Private Gold/corpus, model weights,
embeddings, and local outputs remain excluded from Git.

Full regression actually executed in a disposable `doclens_ai-api` container:

```text
python -m doclens_ai.storage.s3
python -m pytest -q -p no:cacheprovider
```

Result: **226 passed in 92.20s**, no skips, including PostgreSQL/migration, real MinIO, and real
Qdrant tests. The repository was mounted read-only at `/workspace` with `PYTHONPATH=/workspace/src`;
`DATABASE_URL`/`TEST_DATABASE_URL` targeted `postgres:5432`, `S3_*`/`TEST_S3_*` targeted `minio:9000`
and a step-owned private test bucket, and `TEST_QDRANT_URL=http://qdrant:6333`. These services shared
only the isolated task network. No PostgreSQL/MinIO host ports were published. Transient container
test dependencies were pytest 9.1.1 and the declared EDA libraries (openpyxl 3.1.5, pypdf 6.20.0,
python-docx 1.2.0); ML libraries were not installed into the API image. Fake-embedding unit tests
need no ML framework; the separate real local evaluations exercised the pinned model twice.
The Docker network and all three step-owned service containers were removed after verification;
local model assets and metadata reports were retained for reproduction.

## Recommendation and limits

Retain BM25 as the reference baseline. Dense v1 does not justify replacing it: held-out Hit@10,
Recall@10, MRR and nDCG are all lower, and query costs are higher in this offline setup. The five
improved versus eight worsened positive queries suggest potential complementary signals, not a
proven hybrid gain. Hybrid may be investigated later in a separate frozen dev-led experiment;
no fusion, reranking, or parameter optimization is implemented here.

There is no statistical superiority claim on this small family-correlated pilot. English-only
Gold does not establish RU/KK or multilingual performance; test has no negatives, and only two
version questions. The 34 extraction-gated sources and PDF/table/display-value limitations remain.
Character chunk sizing is not token sizing even though this corpus observed zero truncations.
Exact full-score-pool search does not establish approximate-index scalability.

Workspace-isolation security is **NOT EVALUATED**: zero evaluated queries, 48 unchecked,
`passed=null`, no invented scope IDs. No refusal mechanism, answer generation, faithfulness,
or citation correctness was evaluated. Production authorization boundaries are untouched.

## Reproduction

Run from repository root, using approved local corpus/Gold and retained BM25 reference artifacts.
Install optional dependencies without introducing ML into the production backend image:

```powershell
.venv/Scripts/python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python.exe -m pip install -e ".[dev,eda,dense]"
$env:HF_HUB_DISABLE_TELEMETRY='1'
$env:HF_HUB_DOWNLOAD_TIMEOUT='60'
.venv/Scripts/hf.exe download intfloat/multilingual-e5-small --revision 614241f622f53c4eeff9890bdc4f31cfecc418b3 --include config.json model.safetensors tokenizer.json tokenizer_config.json special_tokens_map.json --local-dir evaluation-output/dense-v1-model --max-workers 2
docker network create doclens-dense-eval
docker run --rm -d --name doclens-dense-qdrant --network doclens-dense-eval --network-alias qdrant --cpus 2 --memory 512m -p 127.0.0.1::6333 -e QDRANT__TELEMETRY_DISABLED=true qdrant/qdrant@sha256:6ac4807063bbecddca0250bfbcff52acf18c22263b904d12919349e6d0a408f1
docker port doclens-dense-qdrant 6333
# Substitute the actual loopback port printed above, not a fixed production endpoint.
$env:HF_HUB_OFFLINE='1'
$env:TOKENIZERS_PARALLELISM='false'
.venv/Scripts/python.exe -m doclens_ai.dense_baseline --qdrant-url http://127.0.0.1:PORT --output-dir evaluation-output/dense-v1-run-1
.venv/Scripts/python.exe -m doclens_ai.dense_baseline --qdrant-url http://127.0.0.1:PORT --output-dir evaluation-output/dense-v1-run-2
.venv/Scripts/python.exe -m doclens_ai.evaluation evaluate --gold local-evaluation/retrieval_gold_v1.jsonl --corpus-manifest docs/eda/corpus_v1_manifest.csv --results evaluation-output/dense-v1-run-1/ranked_results.jsonl --json-output evaluation-output/dense-v1-run-1/cli_quality_report.json
docker stop doclens-dense-qdrant
docker network rm doclens-dense-eval
```

Choose unused container/network names and fresh output directories; never reuse an unrelated
service or remove its collection. HF CLI was used according to the hf-cli skill. Network timeouts
were retried without changing model identity; public asset downloads completed and bytes were checked.
All weights, questions, vectors, and ranked anchors remain local and ignored. Ranked results contain
actual worksheet locators where required, so they must not be published. Committed documentation
contains only aggregate measurements, fingerprints, and opaque question IDs, never source excerpts.

## Sources

Configured Hugging Face MCP provided model metadata but its documentation search was unavailable;
the README option did not return model-card content. Primary-source fallback used the pinned
[model card](https://huggingface.co/intfloat/multilingual-e5-small/blob/614241f622f53c4eeff9890bdc4f31cfecc418b3/README.md),
[Transformers 4.57 documentation](https://huggingface.co/docs/transformers/v4.57.1/en/model_doc/auto),
the [official CPU PyTorch installation instructions](https://pytorch.org/get-started/previous-versions/),
and version-matched Qdrant v1.15 REST references for
[collection creation](https://api.qdrant.tech/v-1-15-x/api-reference/collections/create-collection),
[upsert](https://api.qdrant.tech/v-1-15-x/api-reference/points/upsert-points),
[scroll](https://api.qdrant.tech/v-1-15-x/api-reference/points/scroll-points),
[count](https://api.qdrant.tech/v-1-15-x/api-reference/points/count-points), and
[exact vector query](https://api.qdrant.tech/v-1-15-x/api-reference/search/query-points).
