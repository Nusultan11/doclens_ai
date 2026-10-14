# Production tenant-safe dense retrieval v1

## Scope and frozen conditions

Baseline: `9c5eb88afbabacec14da278532ee47e2d677b3a7`. This step adds authenticated dense Search API
and a private evaluator, not generation/RAG, conversations, deletion, training or reranking.
PostgreSQL is authoritative for ACL, canonical text and ACTIVE revisions; Qdrant is derived.
The repository rag-evaluation skill guided source-alignment gates and separate security/quality
measurement. The quality hypothesis is that the unchanged pinned E5 embedding contract can be
served through bounded production retrieval while preserving evidence matching and tenant safety;
this is not a claim of improvement over BM25. Expected failure modes are stale revisions, forged
metadata, revoked memberships, numeric/table ambiguity, truncation and negative-query candidates.

Actual evaluation used all 90 approved Corpus v1 files, independently SHA-256/size verified against
the unchanged manifest. Existing production UploadService, extraction worker and index worker
processed every source in a new disposable PostgreSQL 16 database with real MinIO and Qdrant 1.15.4.
There were 56 ACTIVE documents and 1,092 canonical chunks; 34 sources failed the existing
`extraction_needs_review` gate and had no active index. Incomplete CANDIDATE revisions: 0.
Indexing/ingestion behavior and migrations were not changed.

Gold is the existing 48 human-reviewed English questions: 45 positive, 3 negative, 80 evidence
anchors; dev 36 questions and test 12. Frozen Gold fingerprint:
`d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94`.
Every evidence anchor was independently alignable to canonical source spans. The evaluator
re-extracted verified files with the frozen structure-aware chunker and actual version UUIDs,
then compared canonical identity, ordinal, content SHA, configuration and complete provenance.
It did not use labels to manufacture anchors, restrict indexing to Gold documents or build filters.

Model: `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`; verified pinned local bytes, CPU float32, batch 2,
four intra-op threads/one inter-op thread, 384 dimensions, maximum 512 tokens, right truncation,
attention-mask mean pooling, query/passage prefixes and L2 normalization. Libraries: Torch 2.8.0+cpu,
Transformers 4.57.6, huggingface-hub 0.36.0, tokenizers 0.22.2, safetensors 0.8.0, NumPy 2.5.4.
Full configuration fingerprint:
`4aace3473f62dd7648fdb228b682a266ec85f92ff8c71180bbfd93567e3cd524`.
Only exactly compatible ACTIVE configurations are searched; incompatible scopes return 503.

Retrieval is exact cosine dense-only, candidate limit 20, evaluation result limit 20, no calibrated
score threshold. The API defaults to final limit 10. It never fetches all corpus scores. Gold query
IDs/text alone reach the service alongside a trusted evaluation user/workspace. Cutoffs/scoring
reuse `evaluation/gold.py` and `evaluation/metrics.py` without modification. MRR here is bounded
by the 20 candidates, not an unbounded all-corpus rank. nDCG uses existing binary-new-evidence gain
and the existing one-result-per-anchor ideal; multiple anchors inside one chunk can affect this
metric. No evaluation tuning, BM25 superiority or generation-quality claim is made.

## Measured quality and security

| Measure | Exact numerator / denominator | Value |
| --- | --- | --- |
| Hit@5 | 44 / 45 positive queries | 0.977777777778 |
| Hit@10 | 44 / 45 positive queries | 0.977777777778 |
| Recall@5 | 77 / 80 anchors | 0.962500000000 |
| Recall@10 | 77 / 80 anchors | 0.962500000000 |
| MRR, candidate bound 20 | 39.166666666667 / 45 | 0.870370370370 |
| nDCG@10 | 33.432545790725 / 45 | 0.742945462016 |
| Nonempty query coverage | 48 / 48 queries | 1.000000000000 |
| Negative-query candidate presence | 3 / 3 negative queries | 1.000000000000 |
| Unauthorized returned results | 0 / 960 returned results | hard gate PASS |

All three negative questions returned nearest neighbors. Candidate presence does not mean the
question is answerable or the neighbors relevant. An empty result likewise does not prove
unanswerability. There is no LLM answer, abstention classifier or calibrated relevance threshold.

| Category | Hit@5 and @10 | Recall@5 and @10 | MRR | nDCG@10 |
| --- | --- | --- | --- | --- |
| fact, 12 positive queries | 12/12 | 12/12 anchors | 10.333333333333/12 = 0.861111111111 | 10.761859507143/12 = 0.896821625595 |
| number, 13 | 13/13 | 25/25 | 12.5/13 = 0.961538461538 | 10.220128784852/13 = 0.786163752681 |
| identifier, 10 | 10/10 | 21/21 | 8.833333333333/10 = 0.883333333333 | 7.003628956292/10 = 0.700362895629 |
| table, 8 | 7/8 | 17/20 | 5.5/8 = 0.687500000000 | 3.446928542438/8 = 0.430866067805 |
| version, 2 | 2/2 | 2/2 | 2/2 = 1.000000000000 | 2/2 = 1.000000000000 |

The single missed positive query at @10 and three missed anchors are in the table category.
This small fixed sample does not establish general table performance. No RU/KK queries were
evaluated, despite the multilingual model. Dev: Hit@10 33/33 and Recall@10 57/57; test: Hit@10
11/12 and Recall@10 20/23. Splits/categories were used for scoring only, never ranking/filtering.

A read-only repeat on identical database/index/Gold produced the identical normalized result
fingerprint `aa7395921f2fcb5ef8e3922702a4810a60f9045a017bc38804ca9abcfc7f37e4` and identical quality
metrics. UUIDs differ from the older offline corpus-index experiment; bounded candidate selection,
tie ordering and rank horizon differ too. Do not infer a valid production-versus-BM25 comparison
from these numbers alone.

A third read-only run on the final authorized-document-intersection implementation also passed
all alignment/security gates and reproduced the same normalized rankings and quality metrics.

## Measured latency

48 sequential queries per run; no warm-up queries were discarded. Model startup and corpus
preparation are excluded from query latency. Query embedding includes semaphore queue wait;
Qdrant includes version/collection validation and bounded query request; end-to-end also includes
scope resolution and two PostgreSQL candidate/final checks. Percentiles use linear interpolation
at `(n-1)*p`. Docker CPU/memory are shared with concurrent checks/builds; these are observations,
not throughput/SLA benchmarks.

| Stage | First-run P50 / P95 ms | Read-only repeat P50 / P95 ms |
| --- | --- | --- |
| Query embedding | 41.877 / 57.933 | 31.187 / 49.091 |
| Qdrant | 49.869 / 73.593 | 31.189 / 49.756 |
| End-to-end retrieval | 164.723 / 271.093 | 104.778 / 243.415 |

Final-source run, also 48 queries: embedding P50/P95 37.114/51.781 ms; Qdrant 34.503/40.775 ms;
end-to-end 119.397/246.808 ms. Variation across runs is recorded, not called an improvement.

First complete container execution, including model load, 90-source upload/extraction/indexing,
alignment and queries, took 333.166 seconds (Docker StartedAt/FinishedAt). The evaluation container
was capped at four CPUs/4 GiB, Qdrant at two CPUs/1 GiB. No model weights were downloaded.

## Authorization, protocol and residual race boundary

OIDC verifies signature, issuer/audience/expiry/scope; PostgreSQL resolves the known identity and
current owner/editor/viewer membership. Request workspace/document IDs are selectors, never proof
of access. Backend-derived Qdrant filters contain authorized workspace, selected ACTIVE revision
IDs and optional authorized document intersection. Foreign/missing document selectors cannot
expand the scope or disclose existence. Scope cardinality is bounded (128 ACTIVE revisions by
default, maximum 512); an incompatible/too-large selected scope fails closed rather than silently
searching a subset or mixing models.

Qdrant's bounded response must have finite cosine scores/valid identities and exact metadata keys;
invalid/foreign payloads are dropped. Duplicate point IDs keep the best score. Equal scores sort
by point UUID within the returned candidate set; boundary ties are not a global ordering guarantee.
No text is requested from Qdrant. Behavior follows the version-matched official
[Qdrant 1.15 query-points API](https://api.qdrant.tech/v-1-15-x/api-reference/search/query-points).

PostgreSQL validates every candidate's chunk, run, source version/document/workspace, still-ACTIVE
revision, configuration, requested scope, current membership, deterministic point identity and
canonical content hash. Returned text/locators come from canonical PostgreSQL rows only. A new
session/transaction then repeats ACL/ACTIVE/linkage checks before returning. No business locks span
inference or Qdrant. Revocation/cutover after that final check but before/during network delivery
remains an unavoidable residual boundary; no network-level atomicity is claimed. No deletion or
tombstone workflow is introduced.

Source locations preserve PDF pages, DOCX blocks/tables, and XLSX sheets/cells/ranges and normalized
span offsets. DOCX headings/section titles are absent from the extraction contract and are not
invented. Source text and worksheet names are authorized response content, not public telemetry.
No storage keys, credentials, private model paths or unverified payloads are released.

Inference loads once per application process and uses a semaphore, default 1 (maximum 2).
Queue wait is bounded; cancelled inference drains its CPU thread before releasing its permit.
There is no unsafe thread-kill deadline. Deployments still need ingress-level request/body limits.
Runtime startup failures keep search unavailable with fixed diagnostic codes and sanitized 503.
The default API imports neither ML frameworks nor EDA parsers and remains operational without assets.

## Reproduction and private artifacts

From the repository root, on a previously prepared authorized corpus workspace:

```powershell
python -m doclens_ai.retrieval_eval --model-dir PRIVATE_PINNED_MODEL_DIR `
  --user-id TRUSTED_USER_UUID --workspace-id AUTHORIZED_WORKSPACE_UUID `
  --output-dir evaluation-output/production-retrieval-new-run
```

For explicit preparation use `--prepare-corpus` instead of identity/workspace flags. It requires
an empty disposable database named `doclens_eval_<32 hex>`, current migrations, a private initialized
MinIO bucket, and the entire unchanged approved `local-corpus`/manifest. Set `DATABASE_URL`, existing
`S3_*`, `SEARCH_QDRANT_URL` and optionally a private evaluation collection prefix. Do not point it
at an existing production domain. Cleanup remains an operator action on owned disposable resources.

Actual runs executed in a CPU Docker runtime with read-only source/corpus/model mounts and a writable
private `evaluation-output` mount, using `--model-dir /models/e5`. The first used `--prepare-corpus`;
the second supplied the same trusted generated user/workspace and did not re-index. Only `metrics.json`
was persisted: sanitized aggregate metrics, fingerprints/configuration and counts. No queries,
ranked text, source paths or worksheet names were written. Raw corpus, model weights, local Gold
and generated reports are not committed.

## Verification and known limits

Unit checks cover query/filter bounds, query-prefix routing, invalid vectors, payload validation,
finite scores, deterministic tie ordering/deduplication, private locator projection and cancellation
capacity. Real PostgreSQL/MinIO/Qdrant tests cover tenant/document filtering, foreign high-score
points, forged/malformed metadata, missing/deleted canonical chunks, membership revocation and
real active-revision cutover during Qdrant and before the final authorization check, configuration
mismatch, absent indexes, concurrent requests, JWT authentication and sanitized dependency failures.
Mocks are used for protocol fault injection, not as evidence of real model inference or quality.

Executed verification (Windows unit runtime; Linux Docker integration runtime with real disposable
PostgreSQL/MinIO/Qdrant):

```text
.venv/Scripts/python.exe -m ruff check src tests alembic
  PASS
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
  269 passed in 17.76 s
python -m pytest -q tests/integration/test_retrieval.py tests/integration/test_search_api.py tests/integration/test_production_indexing.py
  47 passed in 174.05 s (via docker exec)
python -m pytest -q -p no:cacheprovider
  386 passed in 407.87 s (via docker exec), zero skips
python -m alembic check
  No new upgrade operations detected (smoke database)
git diff --check / git diff --cached --check
  PASS
```

Targeted pytest emitted one nonblocking cache-write warning because the source bind was read-only;
no integration test was counted as passing via a skip. Initial new API fixtures had mismatched
coordinator/worker TTLs; they were corrected. A real asyncpg connection-refusal regression exposed
unwrapped OSError, now mapped to sanitized 503 at search/auth boundaries. Repeated cancellation
initially released an inference permit prematurely; the regression reproduced it, the CPU-drain
loop was fixed, and both cancellation cases plus the full suite were rerun successfully.

Actual Docker HTTP/JWT smoke used a temporary in-memory RSA/JWKS fixture on the private test network,
not an authentication bypass or a new production service. Default API started without Torch, EDA
parsers or model assets: readiness 200, three authenticated PDF/DOCX/XLSX uploads succeeded, extraction
queued EMBEDDING and authenticated Search returned sanitized 503. The ML overlay then indexed those
same documents and returned four verified chunks from three ACTIVE revisions, preserving page,
DOCX table and XLSX sheet/cell locators. Wrong workspace returned 403 and no unauthorized text.
Stopping only the owned smoke Qdrant produced sanitized 503; restart preserved the points and search
returned 200 again. Missing pinned model files in a disposable ML runtime produced Search 503 while
readiness remained 200. The rebuilt final image contained the cancellation fix and passed HTTP smoke.
Read-only model mount and four-CPU/4-GiB API limits were inspected. One post-query memory sample was
626.4 MiB for API, 640.9 MiB for index worker, 18.24 MiB for Qdrant; these are samples, not peaks/SLA.

Evaluation and security are independent gates. E5 remains an unchanged baseline. The present corpus
is small, English-only and subject to extraction review exclusion and token truncation. Search
does not certify answerability, faithfulness, citations in generated answers or continuous Qdrant
availability. No LLM, hybrid search, reranker, fine-tuning, deletion or new infrastructure service
was added. Ingestion/indexing contracts and historical migrations remain unchanged.
