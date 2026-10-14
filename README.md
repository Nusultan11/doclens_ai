# DocLens AI

DocLens AI currently provides the Backend Core, PostgreSQL document domain, authenticated document intake, durable processing workers, canonical PostgreSQL chunks, and opt-in versioned CPU embeddings with persistent Qdrant indexing. This stage includes OIDC JWT verification, PostgreSQL workspace authorization, health endpoints, immutable document versions, private S3-compatible storage, upload coordination, and lease-fenced extraction/indexing. Search API, RAG, LLM generation, and a document READY workflow are not implemented.

A dedicated ingestion worker consumes EXTRACTION jobs, persists canonical chunks, and hands runs
off to EMBEDDING. The opt-in index worker embeds and verifies versioned Qdrant points before
atomic activation/completion. Retrieval, RAG, and READY transitions
are not implemented. Standalone offline extraction and chunking remain engineering evaluation
tools. The worker image installs existing `[eda]` dependencies; the API image does not.

## Prerequisites

- Docker with Docker Compose, or Python 3.12+ and PostgreSQL 16 for local development

## Run with Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. MinIO's development console is available at `http://localhost:9001`. Compose uses development-only PostgreSQL and MinIO credentials and persists both services in named volumes. Because current MinIO Community Edition is source-only, the Docker build compiles the pinned upstream `RELEASE.2025-09-07T16-13-09Z` source instead of relying on a mutable third-party binary mirror. The one-shot `minio-init` service creates the private `doclens-documents` bucket idempotently; rerunning it is safe.

The health endpoints start when OIDC settings are absent, but every protected endpoint fails closed with `503` until all three trusted values (`OIDC_ISSUER`, `OIDC_AUDIENCE`, and `OIDC_JWKS_URL`) are configured. Compose passes these settings from the host environment and does not provide an authentication bypass.

Apply migrations before enabling the worker on a new or upgraded database:

```bash
docker compose up -d postgres minio minio-init
docker compose run --rm api python -m alembic upgrade head
docker compose up --build -d
docker compose logs -f worker
```

Compose startup does not apply migrations automatically. An unavailable database or missing schema
causes sanitized polling failures and retries, never a false successful processing state.

Health endpoints:

- Liveness: `GET /api/v1/health/live`
- Readiness: `GET /api/v1/health/ready`

## Local development

Copy `.env.example` to `.env`, then create a virtual environment and install the development dependencies:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
```

Run the API:

```bash
uvicorn doclens_ai.main:app --reload
```

Run verification:

```bash
ruff check src tests alembic
pytest
```

## Offline document EDA

An optional, local-only profiler establishes a reproducible extraction baseline for PDF,
DOCX, and XLSX files without using the API, PostgreSQL, object storage, or an LLM. Install
the EDA dependencies and point it at an explicit corpus directory:

```bash
python -m pip install -e ".[dev,eda]"
python -m doclens_ai.eda --input-dir ./local-corpus --output-dir ./eda-output
python -m doclens_ai.extraction --input-dir ./local-corpus --output-dir ./extraction-output
python -m doclens_ai.chunking --input-dir ./local-corpus --output-dir ./chunking-output
python -m doclens_ai.evaluation validate --gold docs/evaluation/synthetic_retrieval_gold_fixture.jsonl
```

The EDA profiler measures corpus characteristics. The extraction command evaluates ordered PDF
page text, ordered DOCX body paragraphs and tables, and sparse XLSX cells and table metadata. The
chunking command compares fixed-size and structure-aware character baselines in memory. These
commands persist privacy-safe aggregate metrics and opaque document identifiers; they do not
persist filenames, paths, extracted/chunk text, table contents, worksheet names, or cell values.
See `docs/eda/README.md` for methodology, limits, deterministic-run options, and interpretation
guidance. Generated reports and local corpora must not be committed.

The offline retrieval-evaluation foundation validates versioned Gold JSONL, stable source anchors,
document-family split isolation, ranked-result inputs, workspace scope, and deterministic Hit@5/10,
Recall@5/10, MRR, and nDCG@10 reports. It does not implement retrieval or establish measured quality.
The committed multilingual fixture is synthetic test data only. Real reviewed annotations and result
files belong under ignored `local-evaluation/`; see
`docs/evaluation/retrieval_gold_v1_protocol.md`.

The frozen offline BM25 baseline searches all extraction-eligible Corpus v1 chunks with the
existing structure-aware chunker and evaluates the human-reviewed Gold snapshot. It is independent
of production services and does not implement embeddings, authorization, or answer generation:

```bash
python -m doclens_ai.retrieval_baseline --output-dir evaluation-output/bm25-v1-run-1
python -m doclens_ai.evaluation evaluate \
  --gold local-evaluation/retrieval_gold_v1.jsonl \
  --corpus-manifest docs/eda/corpus_v1_manifest.csv \
  --results evaluation-output/bm25-v1-run-1/ranked_results.jsonl
```

Run from the repository root with the EDA dependencies installed and the approved local corpus
and Gold available. Use a new output subdirectory each time; existing experiments are never
overwritten. Ranked anchors may contain worksheet names and must remain local. Quality and
experiment metadata are deterministic; latency is recorded separately. Measured v1 results and
limitations are in `docs/evaluation/bm25_baseline_v1.md`.

The optional dense v1 experiment uses a pinned local multilingual E5 model and a disposable
Qdrant, never the production API or database. Install CPU PyTorch explicitly before the dense
extra (the backend image installs base dependencies only):

```bash
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e ".[dev,eda,dense]"
python -m doclens_ai.dense_baseline \
  --qdrant-url http://127.0.0.1:YOUR_DISPOSABLE_PORT \
  --output-dir evaluation-output/dense-v1-run-1
```

Download the pinned model/tokenizer locally first, start only an isolated Qdrant at the documented
image digest, and retain the frozen BM25 reference outputs. Complete setup, comparison results,
resource limits, and cleanup commands are in `docs/evaluation/dense_retrieval_baseline_v1.md`.
Use a fresh `evaluation-output/dense-v1-*` directory per run. Local model files, vectors, Gold,
and ranked anchors must not be committed. This experiment does not evaluate workspace security.

The PostgreSQL integration tests run only when `TEST_DATABASE_URL` is set to a disposable PostgreSQL database whose user can create temporary test databases. The real object-storage tests additionally require an initialized private test bucket and `TEST_S3_*` settings. For the local Compose services:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://doclens:doclens-local@localhost:5432/doclens pytest -m integration
TEST_S3_ENDPOINT_URL=http://localhost:9000 \
TEST_S3_ACCESS_KEY=doclens-local \
TEST_S3_SECRET_KEY=doclens-local-secret \
TEST_S3_BUCKET_NAME=doclens-documents \
TEST_S3_SECURE=false \
pytest -m storage
```

If port 5432 is already owned by a Windows PostgreSQL service, run a disposable PostgreSQL 16
container with a dynamically assigned loopback port and point `TEST_DATABASE_URL` at that port.
Do not assume the example port is available.

PowerShell users can set the same variables with `$env:NAME = "value"` before running pytest. The S3 settings are loaded only when storage is used, so a temporary MinIO outage does not prevent the existing API liveness and database-readiness checks from starting.

Apply or revert all migrations:

```bash
alembic upgrade head
alembic downgrade base
```

## Authentication and workspace authorization

Configure one trusted OIDC issuer and its static JWKS endpoint:

```dotenv
OIDC_ISSUER=https://identity.example.test/
OIDC_AUDIENCE=doclens-api
OIDC_JWKS_URL=https://identity.example.test/.well-known/jwks.json
OIDC_REQUIRED_SCOPE=doclens:documents
OIDC_JWKS_TIMEOUT_SECONDS=3
OIDC_JWKS_CACHE_TTL_SECONDS=300
```

Access tokens must use `RS256`, contain valid `iss`, `aud`, `sub`, and `exp` claims, and include the configured scope in `scope` (space-delimited) or `scp` (array). Signing keys are fetched asynchronously with a bounded timeout and cached. Invalid credentials return `401`; temporary JWKS failures return `503`. Tokens, object keys, and credentials are not returned by the API.

Users and workspace memberships are provisioned only by a trusted database administrator or a future administrative workflow. Merely presenting a valid new OIDC subject never creates a membership. The following illustrates the required transaction; replace every placeholder with administrator-controlled values:

```sql
BEGIN;
INSERT INTO users (id, issuer, subject)
VALUES ('00000000-0000-0000-0000-000000000001',
        'https://identity.example.test/', 'provider-subject');
INSERT INTO workspace_memberships (id, user_id, workspace_id, role)
VALUES ('00000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000003', 'editor');
COMMIT;
```

Roles are server-side PostgreSQL data: `owner` and `editor` may create documents and versions; `viewer` is read-only. All three roles may read metadata. Nonmembers are denied, and a document ID outside the authorized workspace is returned as not found. Client-supplied role or workspace claims are never accepted as authorization.

## Document intake API

All document routes are under `/api/v1` and require `Authorization: Bearer <access-token>`:

- `POST /workspaces/{workspace_id}/documents` creates a stable document identity.
- `POST /workspaces/{workspace_id}/documents/{document_id}/versions` accepts a multipart `file` and requires `Idempotency-Key`.
- `GET /workspaces/{workspace_id}/documents/{document_id}` returns document/version metadata without object-storage keys or credentials.
- `GET /jobs/{job_id}` returns sanitized processing status for users who belong to the owning workspace.

Example upload:

```bash
curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Idempotency-Key: client-generated-stable-key" \
  -F "file=@example.pdf;type=application/pdf" \
  http://localhost:8000/api/v1/workspaces/WORKSPACE_ID/documents/DOCUMENT_ID/versions
```

The application measures the bytes actually read and rejects uploads larger than `S3_MAX_UPLOAD_SIZE_BYTES`, even when `Content-Length` is absent or misleading. `UploadFile` uses a spooled file and the upload service streams into a bounded spool rather than loading the entire document into memory. Production ingress/proxy configuration must also impose an HTTP request-body limit slightly above `S3_MAX_UPLOAD_SIZE_BYTES` to account for multipart framing; that outer limit protects multipart parsing before the route is invoked.

Expected error classes are `401` invalid credentials, `403` insufficient workspace role, `404` document outside the authorized scope, `409` idempotency conflict, `413` actual file too large, `415` unsupported/invalid file type, and `503` unavailable identity, storage, or database dependency. Responses are sanitized.

## Upload lifecycle

`UploadService` remains an internal trusted boundary behind the authenticated API. It accepts a server-scoped workspace/document pair, streams a PDF, DOCX, or XLSX into a bounded spool, validates the declared type and basic file structure, calculates the actual byte count and SHA-256, and binds an idempotency key to that exact content. Object keys are generated server-side.

Upload sessions move through `pending`, `uploaded`, `completed`, or `failed`. The object is uploaded and read back for independent size and SHA-256 verification before PostgreSQL creates an immutable `DocumentVersion`. Finalization locks the logical document, allocates the next version number, and atomically records the version, initial processing run, queued processing job, and completed session. Repeating a completed request returns its existing version and job; a failed or interrupted request can safely retry with the same key and content.

Object storage and PostgreSQL are intentionally not treated as a distributed transaction. An object whose final database transaction fails remains associated with its non-completed upload-session key for retry or operator cleanup. Cleanup must first confirm that no completed upload session or document version references the object; never delete an object solely because a client reports a failed request. Failure codes are operational labels and do not contain document content or credentials.

The current schema stores workspace authorization, stable document identity, upload coordination,
immutable version/file metadata, versioned processing configuration identity, durable
queue/lease/retry state, and immutable canonical chunks. The internal ingestion service resolves
trusted object metadata through a `ProcessingRun`, performs a bounded verified download, runs the
frozen extraction and structure-aware character chunking contracts off the async event loop, and
atomically publishes the complete chunk set. Canonical chunk UUIDs, content hashes, configuration
fingerprints, ordinals, and JSONB provenance support deterministic replay, citations, and future
rebuilding of a vector index. Token counts remain `NULL` until a tokenizer is explicitly selected.

Internal ingestion requires trusted ownership explicitly:
`await ingestion.ingest(processing_run_id, worker_id=worker_id, lease_token=lease_token)`.
The coordinator must first claim the job; ingestion accepts only its active lease and a
`processing` run at the `extraction` stage. Preflight rejects missing, inactive, mismatched,
or expired leases before storage access. Download and extraction hold no database row locks.
Publication (including an identical already-persisted result) locks `ProcessingJob` then
`ProcessingRun`, matching the coordinator, and rechecks ownership, run state, and configuration.
Lease expiration uses PostgreSQL `clock_timestamp()` after lock waits and again just before
commit, so a worker whose lease expired or was reclaimed during extraction cannot publish.
`lease_ownership_lost` is a sanitized, non-retryable failure for that invocation; a stale caller
must not fail or complete a job now owned by another worker. An unchanged active lease may
repeat ingestion idempotently. Ingestion itself does not advance stages or mark jobs complete.
The ingestion worker uses this contract and hands off to the separate opt-in indexing worker.
This boundary alone does not imply a complete index or end-to-end production readiness.

PostgreSQL rejects updates to persisted document-version rows, processing-run identity/configuration,
and canonical chunks. Atomic job claims use row locking with skip-locked semantics; lease tokens
fence stale workers, and retry backoff and attempts are bounded. The ingestion worker consumes only
EXTRACTION jobs; it never marks a document ready or complete. The indexing worker persists vectors
in Qdrant and atomically publishes verified revision/completion metadata in PostgreSQL. File bytes
remain in the private object bucket. Character limits are not token limits, and
documents requiring extraction review are rejected rather than silently published. Future schema
changes must be new Alembic revisions rather than edits to migration history.

## Ingestion worker

For local execution, configure the existing `DATABASE_URL` and `S3_*` settings, initialize the
private bucket, apply migrations, and install parsing dependencies:

```bash
python -m pip install -e '.[eda]'
python -m alembic upgrade head
python -m doclens_ai.worker
```

Each process generates an opaque UUID-based worker identity and processes one document at a time.
Multiple processes compete through PostgreSQL skip-locked claims. The stage filter applies before
claiming, so queued EMBEDDING work remains untouched. Original documents and canonical chunks stay
in their existing storage layers; no model download, vector indexing, or new queue is introduced.

Configuration is loaded from the environment or `.env`:

| Variable | Default | Bounds |
| --- | --- | --- |
| `WORKER_POLL_INTERVAL_SECONDS` | 1 | > 0, <= 60 |
| `WORKER_HEARTBEAT_INTERVAL_SECONDS` | 10 | > 0, <= 60 |
| `WORKER_LEASE_SECONDS` | 120 | > 0, <= 3600 |
| `WORKER_DB_TIMEOUT_SECONDS` | 5 | > 0, <= 60 |

All values must be finite. Heartbeat interval plus DB timeout must be strictly below half the lease
TTL, and the worker and coordinator use the same TTL. Local timers schedule polling/heartbeats;
PostgreSQL `clock_timestamp()` determines whether ownership is valid. A heartbeat runs throughout
download, extraction, and chunking without keeping a database transaction open. Heartbeat or DB
failure prevents handoff/failure routing through uncertain ownership; fenced persistence remains
the final authority. Logs contain only fixed operational codes, not exception details or content.

Retryable ingestion failures use existing bounded per-stage attempts and exponential backoff.
Permanent errors fail immediately through the fenced coordinator. Unexpected ingestion exceptions
use `worker_unexpected_failure` with safe retry. Ownership loss never changes the current owner's
job. A failed document does not stop unrelated jobs. A crash consumes an attempt; after lease expiry
a replacement can replay ingestion idempotently (subject to the existing attempt limit), including
the crash window after canonical persistence but before handoff.

Successful handoff locks Job then Run, validates active ownership and EXTRACTION state, and checks
for canonical chunks. CLEANING/CHUNKING have already succeeded inside ingestion; the transaction
records their completed boundary by advancing directly to EMBEDDING without exposing intermediate
committed states. Run/job become `queued`, the lease is cleared, and `attempt_count` resets to zero
for the next stage while `max_attempts` remains unchanged. Sequential `advance_stage()` still
requires one-step transitions for other callers. No COMPLETED or READY state is set.

SIGINT/SIGTERM stops new polling and drains the current document with heartbeat cleanup. An
already-started claim may finish. Task cancellation also drains the parser thread before cleanup
and skips handoff. Compose allows five minutes to drain; a forced kill beyond that grace period
uses lease-expiry recovery. This worker does not impose a hard CPU parser timeout or run an
embedding/indexing executor; EMBEDDING jobs remain queued unless the ML worker is enabled.

## Production embeddings and versioned Qdrant indexing

The independent index worker consumes only EMBEDDING/INDEXING jobs. PostgreSQL remains the source
of truth; Qdrant is a rebuildable index. API and extraction-worker images contain no Torch or
Transformers dependencies. The `index-worker` target adds the existing optional `dense` dependencies,
including CPU Torch 2.8.0, Transformers 4.57.6 and huggingface-hub 0.36.0. Parsing dependencies remain
in that image because the reused offline provider imports its existing extraction contracts.

### Pinned local model and startup

Reuse `intfloat/multilingual-e5-small` at revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`. Obtain approved artifacts ahead of time from that exact
revision into a private local directory, using the existing offline baseline preparation workflow.
Required files are `config.json`, `tokenizer_config.json`, `special_tokens_map.json`,
`model.safetensors` and `tokenizer.json`; the SHA-256 allowlist is defined in
`src/doclens_ai/dense_baseline/embeddings.py`. Startup validates every file and rejects symlinks,
missing files and hash mismatches before loading. Neither builds nor startup download weights;
loading uses local files only and never enables remote model code. Keep artifacts out of Git.

Default inference is CPU float32, batch 2, maximum 512 tokens, four intra-op threads and one inter-op
thread, seed 0, deterministic eager attention, attention-mask mean pooling, `passage: ` prefix and
L2 normalization. Vectors must have exactly 384 finite normalized values, one per canonical chunk.
Oversized character-based chunks can be truncated by the existing tokenizer contract; indexing
does not resolve that quality limitation. A small replaceable `Embedder` protocol is reused rather
than introducing a provider framework. Exact configuration, tokenizer/file identities and all six
runtime library versions are fingerprinted and stored in PostgreSQL.

For PowerShell, after preparing verified assets:

```powershell
# Default services work without this variable or model files.
docker compose up --build -d
docker compose exec api python -m alembic upgrade head

# Explicit private location; mount is read-only and never auto-creates a missing directory.
$env:DOCLENS_E5_MODEL_DIR = 'C:/private/doclens-models/multilingual-e5-small'
docker compose --profile ml build index-worker
docker compose --profile ml run --rm --no-deps index-worker python -m doclens_ai.index_worker --preflight
docker compose --profile ml up -d qdrant index-worker
```

Preflight verifies artifacts and performs real local inference on a controlled passage; output is
configuration/hash metadata and counts only. Apply migrations before enabling the worker. Optional
profile `ml` gates both Qdrant and the index worker, so ordinary Compose startup does not need assets.
For direct execution install existing `.[eda,dense]` dependencies, configure `DATABASE_URL`,
`INDEX_MODEL_DIR`, `INDEX_QDRANT_URL` and the existing `WORKER_*` settings, then run
`python -m doclens_ai.index_worker`. An optional `INDEX_QDRANT_API_KEY` is a secret setting, never
logged or stored in revision metadata. Compose's unauthenticated HTTP endpoints/development
credentials are local-only; deploy on a trusted private network and configure authentication/TLS
for production. No Qdrant port is published by Compose.

| Setting | Default / bound |
| --- | --- |
| `INDEX_BATCH_SIZE` | 2 / 1..8 |
| `INDEX_CPU_THREADS` | 4 / 1..8 |
| `INDEX_UPSERT_BATCH_SIZE` | 64 / 1..256 |
| `INDEX_QDRANT_TIMEOUT_SECONDS` | 15 / >0..60, finite |
| `INDEX_COLLECTION_PREFIX` | `doclens_e5_v1` / validated lowercase identifier |
| Service source budget | at most 10,000 chunks and 20,000,000 characters per attempt |

Qdrant is pinned to 1.15.4 by image digest
`sha256:6ac4807063bbecddca0250bfbcff52acf18c22263b904d12919349e6d0a408f1`, with persistent
`doclens-qdrant-data` storage. Compose caps the index worker at four CPUs/4 GiB and Qdrant at two
CPUs/1 GiB. These are configured limits, not a general throughput/sizing guarantee.

### Revision, verification and cutover contract

Migration `0007_index_revisions` adds only the new table, indexes and lifecycle guard. Existing
DocumentVersion and canonical chunk data/triggers are unchanged. Downgrade removes revision metadata
but preserves canonical chunks and source versions; it does not delete external Qdrant data.

Each lease attempt owns a deterministic revision UUID and immutable run/version/document/workspace
scope, model revision/configuration, collection/dimension, canonical chunk-set fingerprint and
expected point count. Lifecycle is `candidate -> verified -> active -> superseded`, or
`verified -> superseded` when an older candidate loses cutover. Verification/activation timestamps
and counts are constrained; identity/configuration cannot be changed. A PostgreSQL partial unique
index permits at most one active revision per logical document.

Collection identity is the validated prefix plus the full embedding fingerprint. Existing collection
dimension/distance must match 384/Cosine; incompatible collections are never deleted/recreated.
Points use UUIDv5 derived from revision UUID plus canonical chunk UUID/identity. Payload has exactly
`workspace_id`, `document_id`, `document_version_id`, `processing_run_id`, `index_revision_id`,
`chunk_id`, `embedding_revision`, and `embedding_configuration_fingerprint`, all constructed from
trusted PostgreSQL/provider metadata. No chunk text, filename, storage key, path or cell values are
sent as payload. Embeddings themselves are document-derived sensitive data and require private
access controls even without text payloads.

Batched upserts require `wait=true` and completed acknowledgements. Before marking VERIFIED, the
adapter checks exact revision-filtered count, paginates the entire candidate, and compares every
expected ID, complete payload, vector dimension, finite normalization and vector values. HTTP 200
alone is insufficient. REST behavior follows the version-matched Qdrant
[upsert](https://api.qdrant.tech/v-1-15-x/api-reference/points/upsert-points),
[count](https://api.qdrant.tech/v-1-15-x/api-reference/points/count-points) and
[scroll](https://api.qdrant.tech/v-1-15-x/api-reference/points/scroll-points) contracts.

Inference and network calls hold no PostgreSQL row locks. Short candidate/checkpoint/activation
transactions lock Job then Run and recheck worker/token/expiry using PostgreSQL `clock_timestamp()`
after lock waits and after flush. Completion additionally locks the logical Document to serialize
cutover, requires this lease's VERIFIED revision and unchanged canonical set, then atomically
supersedes the previous index, activates the replacement and marks Run/Job COMPLETED. Calling
stage-only `complete()` is rejected. Historical pre-migration COMPLETED rows are not falsely
backfilled into verified indexes; operators must explicitly reprocess them if an index is required.

Newer document versions win. For the same version, newer run `created_at` wins, with run UUID as a
deterministic tie-breaker. A late older candidate becomes SUPERSEDED without activation and its job
fails with `obsolete_index_revision`; it never gets a false COMPLETED status. A failed replacement
does not delete old active points or replace its active revision.

Temporary embedding/DB/Qdrant errors use bounded attempts/backoff. Invalid configuration/data/vector
errors are terminal. A crash or expired lease can be reclaimed at either supported stage; retry
creates a fresh lease-scoped candidate and deterministically re-embeds/upserts. Repeating an
unchanged lease is idempotent. Stale external writes can only touch their old revision namespace,
not replacement points. Heartbeat uncertainty/cancellation suppresses activation and drains the
inference operation; lease expiry is the recovery mechanism, not a distributed transaction.

Orphan CANDIDATE/VERIFIED revisions and their vectors are retained intentionally. Cleanup is deferred
and must first establish no active/reference or in-flight owned attempt exists, then remove only
that revision's external points and safe metadata. Never delete a shared collection on worker exit.
An external administrator can still alter/delete Qdrant after verification; PostgreSQL completion
does not promise continuous external availability. Future retrieval must resolve the authoritative
active revision and tenant scope server-side, not accept arbitrary client filters.

### Measured smoke and evaluation limits

A controlled two-chunk DOCX traversed real MinIO, PostgreSQL 16, CPU E5 and Qdrant 1.15.4: one active
revision, two fully verified 384-dimensional points and one COMPLETED job; embedding failures 0,
incomplete candidate revisions 0. Worker indexing duration was 1010.662 ms, including 679.023 ms of
embedding, excluding model startup. Separate preflight model load was 12062.060 ms. The exact smoke
configuration fingerprint was
`4aace3473f62dd7648fdb228b682a266ec85f92ff8c71180bbfd93567e3cd524`.
One post-indexing Docker stats sample measured 589.6 MiB worker memory and 17.8 MiB Qdrant memory;
these are point-in-time samples, not peak memory or representative corpus benchmarks.

Fault/concurrency integration tests use an explicitly fake deterministic embedding provider with
real PostgreSQL, MinIO and Qdrant; they test persistence/protocol/fencing, not real-model quality.
The separate Docker smoke uses actual pinned weights. Existing
`docs/evaluation/dense_retrieval_baseline_v1.md` remains the retrieval-quality evidence: E5 is a
baseline candidate, not a demonstrated BM25 improvement. This step adds no Search API, retrieval
ranking, RAG, LLM generation, fine-tuning, reranker or hybrid retrieval.
