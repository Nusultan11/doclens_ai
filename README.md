# DocLens AI

DocLens AI currently provides the Backend Core, PostgreSQL document domain, and an authenticated document-intake API for a production-oriented document intelligence system. This stage includes a FastAPI service, OIDC JWT verification, PostgreSQL workspace authorization, async PostgreSQL connectivity, health endpoints, immutable document versions, private S3-compatible storage, and mutable upload-session coordination.

Parsing/extraction, background jobs, Qdrant, retrieval, RAG, embeddings, and LLM features are not implemented yet.

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

Upload sessions move through `pending`, `uploaded`, `completed`, or `failed`. The object is uploaded and read back for independent size and SHA-256 verification before PostgreSQL creates an immutable `DocumentVersion`. Finalization locks the logical document, allocates the next version number, and records the version and completed session in one database transaction. Repeating a completed request returns its existing version; a failed or interrupted request can safely retry with the same key and content.

Object storage and PostgreSQL are intentionally not treated as a distributed transaction. An object whose final database transaction fails remains associated with its non-completed upload-session key for retry or operator cleanup. Cleanup must first confirm that no completed upload session or document version references the object; never delete an object solely because a client reports a failed request. Failure codes are operational labels and do not contain document content or credentials.

The current schema stores workspace authorization, stable document identity, upload coordination, and immutable version/file metadata. PostgreSQL rejects updates to persisted document-version rows. File bytes live only in the private object bucket; the database does not store extracted text, processing state, or embeddings. Future schema changes must be created as new Alembic revisions rather than by editing migration history.
