# DocLens AI

DocLens AI currently provides the Backend Core, PostgreSQL document domain, authenticated document intake, a durable PostgreSQL processing control plane, and an internal production extraction service with canonical PostgreSQL chunk persistence. This stage includes a FastAPI service, OIDC JWT verification, PostgreSQL workspace authorization, async PostgreSQL connectivity, health endpoints, immutable document versions, private S3-compatible storage, upload-session coordination, and lease-based processing jobs.

Actual background workers, embeddings, Qdrant, retrieval, RAG, and LLM features are not implemented
yet. New processing jobs remain queued until a real worker invokes the internal ingestion service.
The service does not consume jobs or mark runs/jobs complete. Standalone offline extraction and
chunking commands remain engineering evaluation tools and are not connected to the queue.
The future worker environment that invokes ingestion must install the existing `[eda]` optional
dependencies; they are intentionally not added to the API image in this step.

## Prerequisites

- Docker with Docker Compose, or Python 3.12+ and PostgreSQL 16 for local development

## Run with Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. MinIO's development console is available at `http://localhost:9001`. Compose uses development-only PostgreSQL and MinIO credentials and persists both services in named volumes. Because current MinIO Community Edition is source-only, the Docker build compiles the pinned upstream `RELEASE.2025-09-07T16-13-09Z` source instead of relying on a mutable third-party binary mirror. The one-shot `minio-init` service creates the private `doclens-documents` bucket idempotently; rerunning it is safe.

The health endpoints start when OIDC settings are absent, but every protected endpoint fails closed with `503` until all three trusted values (`OIDC_ISSUER`, `OIDC_AUDIENCE`, and `OIDC_JWKS_URL`) are configured. Compose passes these settings from the host environment and does not provide an authentication bypass.

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

PostgreSQL rejects updates to persisted document-version rows, processing-run identity/configuration,
and canonical chunks. Atomic job claims use row locking with skip-locked semantics; lease tokens
fence stale workers, and retry backoff and attempts are bounded. No daemon or dummy handler consumes
these jobs, and nothing marks a document ready or complete. File bytes remain in the private object
bucket; embeddings and vector state are not persisted. Character limits are not token limits, and
documents requiring extraction review are rejected rather than silently published. Future schema
changes must be new Alembic revisions rather than edits to migration history.
