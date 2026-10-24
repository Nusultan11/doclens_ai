# DocLens AI

DocLens AI is a Python/FastAPI modular monolith for PDF, DOCX and XLSX intelligence.
It provides authenticated uploads, durable extraction workers, canonical PostgreSQL
chunks, opt-in E5/Qdrant indexing and dense search, and a stateless local-generator
RAG baseline. PostgreSQL owns authorization, source text and ACTIVE revisions;
S3/MinIO stores original files. Conversations, deletion and document READY workflows
are not implemented. Recorded real-generator configurations were rejected;
independent production semantic quality remains NOT_EVALUATED.

Start with [AGENTS.md](AGENTS.md) for engineering procedure and
[README_SOURCE_MAP.md](README_SOURCE_MAP.md) for the current normative owners.
[Architecture v4](Doclens_AI-architecture.md) distinguishes implemented boundaries
from targets. The [v3 DOCX](Doclens_AI-architecture.docx) and reports under
`docs/eda/` and `docs/evaluation/` retain historical evidence, not current-HEAD PASS.

## Run with Docker

Requires Docker Compose. Configure trusted OIDC settings from [.env.example](.env.example),
then initialize storage, apply migrations and start the services:

```bash
docker compose up -d postgres minio minio-init
docker compose run --rm api python -m alembic upgrade head
docker compose up --build -d
docker compose logs -f worker
```

The API is at `http://localhost:8000`, OpenAPI at `/docs`, and the MinIO console at
`http://localhost:9001`. Compose uses development credentials and persistent named
volumes. MinIO is built from the source release pinned in [Dockerfile](Dockerfile);
`minio-init` creates the private bucket idempotently. Migrations are explicit, never
automatic. If port 5432 is occupied, use a disposable PostgreSQL 16 instance and its
actual port. Production networking, TLS and secrets require separate qualification.

`GET /api/v1/health/live` is liveness; `/api/v1/health/ready` probes PostgreSQL.
Without `OIDC_ISSUER`, `OIDC_AUDIENCE` and `OIDC_JWKS_URL`, health still starts but
protected endpoints fail closed with 503.

## Local development and verification

Requires Python 3.12+ and PostgreSQL 16. Copy `.env.example` to `.env`, then:

```bash
python -m venv .venv
# Activate .venv before the following commands.
python -m pip install -e ".[dev,eda]"
python -m alembic upgrade head
uvicorn doclens_ai.main:app --reload
```

Lint with `python -m ruff check src tests tools alembic`. The complete local suite
also exercises offline PDF tools. Install their existing frozen test dependencies;
these are separate from backend/image dependencies:

```bash
python -m pip install psutil==7.1.0 pdfplumber==0.11.9 pypdfium2==5.14.0
```

Run from the repository root with `PYTHONPATH` including that root, because tool
subprocesses import the `tools` namespace. Review-packet tests enforce ignored local
output, so use a fresh scratch directory under `evaluation-output/`. In PowerShell:

```powershell
$env:PYTHONPATH = (Get-Location).Path
$testScratch = "evaluation-output/pytest-$([guid]::NewGuid().ToString('N'))"
python -m pytest --basetemp $testScratch
```

Do not point `--basetemp` at existing evidence: pytest clears that directory.

PostgreSQL integration tests require `TEST_DATABASE_URL` naming a disposable database
whose user can create temporary databases. Storage tests additionally require an
initialized private bucket and `TEST_S3_*` settings. For local Compose services:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://doclens:doclens-local@localhost:5432/doclens pytest -m integration
TEST_S3_ENDPOINT_URL=http://localhost:9000 \
TEST_S3_ACCESS_KEY=doclens-local \
TEST_S3_SECRET_KEY=doclens-local-secret \
TEST_S3_BUCKET_NAME=doclens-documents \
TEST_S3_SECURE=false pytest -m storage
```

PowerShell: assign `$env:NAME = 'value'` before pytest. Unconfigured service tests,
private-capture replays and optional renderer/browser checks report their own skip
reasons. Browser tests also need their documented local runtime. No GPU or model
inference is required for the local regression suite.

Apply/revert migrations with `python -m alembic upgrade head` /
`python -m alembic downgrade base`. Add new revisions; never edit applied history.

## Authentication and API

OIDC uses RS256 with validated issuer, audience, subject, expiry and configured scope
(`OIDC_REQUIRED_SCOPE=doclens:documents`). JWKS settings are in `.env.example`.
Trusted administrators provision users and workspace memberships in PostgreSQL;
a valid new subject does not create membership. `owner`/`editor` can write,
`viewer` can read. Client workspace/role claims never grant authorization.

All protected routes require `Authorization: Bearer <access-token>`:

| Route under `/api/v1` | Purpose |
| --- | --- |
| `POST /workspaces/{workspace_id}/documents` | Create document identity |
| `POST /workspaces/{workspace_id}/documents/{document_id}/versions` | Multipart `file`; required `Idempotency-Key` |
| `GET /workspaces/{workspace_id}/documents/{document_id}` | Metadata and derived version `is_searchable` |
| `GET /jobs/{job_id}` | Sanitized processing status |
| `POST /search` | Authorized dense search |
| `POST /answers` | Citation-validated answer or explicit refusal |

Upload example:

```bash
curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Idempotency-Key: client-generated-stable-key" \
  -F "file=@example.pdf;type=application/pdf" \
  http://localhost:8000/api/v1/workspaces/WORKSPACE_ID/documents/DOCUMENT_ID/versions
```

Uploads enforce actual byte size and verify stored size/SHA-256 before finalization.
Ingress must also bound multipart request bodies. Error classes include 401 invalid
authentication, 403 insufficient role, 404 out-of-scope document, 409 idempotency
conflict, 413 oversize, 415 invalid format, 422 invalid input and 503 dependency failure.
`is_searchable` requires that version's verified ACTIVE revision and completed
indexing; it does not probe Qdrant availability. See OpenAPI for request/response
schemas and [architecture](Doclens_AI-architecture.md#ARCH-UPLOAD) for lifecycle invariants.

## Ingestion worker

The `worker` image installs `[eda]`; the default API image installs backend dependencies.
For direct execution, configure `DATABASE_URL` and `S3_*`, initialize the bucket,
apply migrations, then run:

```bash
python -m doclens_ai.worker
```

The worker claims EXTRACTION jobs, verifies downloads, extracts and chunks off the
async event loop, atomically publishes canonical chunks and queues EMBEDDING.
Leases fence stale workers; retries are bounded. Shutdown drains the current parser
thread. Parser execution has no hard process timeout. Worker settings and bounds
are defined by [WorkerSettings](src/doclens_ai/services/worker.py).

Extraction/chunking contract 1.1 preserves DOCX part/XML addresses, note references,
declared table headers, XLSX raw values, number formats, date system and formula/cache
metadata. Source-span offsets address rendered source units, not RAW bytes. New processing
identities include implementation hashes and the pinned native parser stack; workers reject
version/configuration drift. Existing runs and chunks are not rewritten. Queued runs
with older configurations fail with `configuration_mismatch`; processing them with
the new contract requires a new run with the current configuration.

Parser `success` is separate from evidence eligibility. Native PDF text remains available
offline, but production ingestion currently holds every PDF for review because verified
table topology/reading order is unavailable. DOCX notes and headers/footers are preserved
with real part identity and remain under review. Missing formula definitions/caches,
ambiguous spreadsheet structure/formats, corrupted Unicode, inconsistent locators, and
oversized table evidence splits cannot silently publish trusted canonical chunks.

## Embeddings and versioned indexing

Prepare private local assets for `intfloat/multilingual-e5-small` revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`. The five required files and SHA-256
allowlist are in [embeddings.py](src/doclens_ai/dense_baseline/embeddings.py).
Startup rejects missing, changed or symlinked assets; loading is local-only with
remote code disabled. Keep weights out of Git. CPU Torch and the dense runtime
are installed only in the opt-in ML images.

After migrations and asset preparation:

```powershell
$env:DOCLENS_E5_MODEL_DIR = 'C:/private/doclens-models/multilingual-e5-small'
docker compose --profile ml build index-worker
docker compose --profile ml run --rm --no-deps index-worker python -m doclens_ai.index_worker --preflight
docker compose --profile ml up -d qdrant index-worker
```

Preflight verifies assets and runs controlled local inference. Compose mounts the
model read-only without creating missing directories. Qdrant is pinned by digest,
persists its index and has no published host port. Indexing verifies complete
revision points before atomic ACTIVE cutover; failed replacements preserve the old
active revision. Orphan revisions are retained pending reference-safe cleanup.

For direct execution, install `.[eda,dense]`, set `INDEX_MODEL_DIR`,
`INDEX_QDRANT_URL`, `DATABASE_URL` and `WORKER_*`, then run
`python -m doclens_ai.index_worker`. Install CPU Torch first as shown below.
Defaults/bounds: [IndexSettings](src/doclens_ai/index_worker.py).
Lifecycle/security contracts: [architecture index](Doclens_AI-architecture.md#ARCH-INDEX).
[Recorded indexing smoke](docs/evaluation/indexing_smoke_v1.md) is historical evidence.

## Dense search and local answers

Enable the same FastAPI application with the optional search overlay after indexing:

```powershell
docker compose -f compose.yaml -f compose.search.yaml up --build -d
```

`POST /api/v1/search` accepts `workspace_id`, `query`, optional `document_ids`,
`top_k` (1..20) and `limit` (1..top_k). Results contain canonical text, source
locators, IDs and cosine scores. PostgreSQL scope and ACTIVE configuration are
checked before search and immediately before delivery. Empty results do not prove
unanswerability. [SearchSettings](src/doclens_ai/core/search_config.py) owns defaults.

`POST /api/v1/answers` accepts `workspace_id`, `question` and optional `document_ids`.
It returns `answerable`, `answer`, `citations`, `reason` and `request_id`. The service
packs at most six chunks within character budgets, validates exact quote/answer
spans and reauthorizes all packed sources after inference. These structural checks
do not establish factual correctness. Revocation after the final DB check remains
a delivery race. Conversations, streaming and tool execution are absent.

To enable an operator-managed private generator:

```powershell
$env:RAG_ENDPOINT = 'http://192.168.1.10:8080/v1/chat/completions'
$env:RAG_MODEL_ID = 'EXACT_OPERATOR_CONFIGURED_MODEL_ID'
docker compose -f compose.yaml -f compose.search.yaml -f compose.rag.yaml up --build -d
```

Context packing includes complete canonical chunks or excludes them with an internal
budget reason; it never sends a truncated prefix. If all candidates exceed the
budget, the answer path returns `insufficient_evidence` without generation.
Character caps do not establish a tokenizer window. A configured
`RAG_CONTEXT_WINDOW_TOKENS` requires a trusted `token_counter` supplied through
`build_rag_runtime`/`RagService`; it must count the complete model chat template and
special tokens. The packer reserves `RAG_MAX_OUTPUT_TOKENS`. Missing/failing counters
fail closed; the default HTTP adapter does not invent a tokenizer or token ratio.

Accepted answer spans must be literal quoted text. Number-bearing answers use a
conservative complete-fact check against the whole authorized chunk, retaining
signs, precision, units, formulas and periods. Only explicitly recognized bare
value labels may be omitted. Cropped numerical facts, ambiguous composition and
unsupported paraphrases return the existing `insufficient_evidence` refusal.
This is a fidelity guard, not general semantic entailment or production qualification.

The endpoint/model are placeholders. Use an explicit reachable private/loopback IP;
DNS names, public endpoints, redirects and environment proxies are rejected.
Docker loopback addresses the API container. HTTPS must validate the IP certificate.
The operator must verify local inference and server concurrency/cancellation limits.
[RagSettings](src/doclens_ai/core/rag_config.py) defines budgets and optional secret
settings. Model revision/hash declarations are not proof of loaded weights.

## Offline evaluation

Use approved local corpus/Gold only; keep RAW, annotations, model assets and generated
outputs out of Git. Use fresh output directories. These commands do not establish
production quality or authorize cloud uploads.

| Workflow | Entry point and evidence |
| --- | --- |
| EDA, extraction, chunking | [Local methodology and commands](docs/eda/README.md) |
| Fidelity Gold/scoring | [Protocol](docs/eda/extraction_fidelity_protocol_v1.md), [historical benchmark](docs/eda/extraction_fidelity_benchmark_v1.md) |
| Retrieval Gold and BM25 | [Gold protocol](docs/evaluation/retrieval_gold_v1_protocol.md), [baseline](docs/evaluation/bm25_baseline_v1.md) |
| Offline E5/Qdrant comparison | [Frozen setup/results](docs/evaluation/dense_retrieval_baseline_v1.md) |
| Production retrieval evaluator | [Protocol/results](docs/evaluation/production_retrieval_v1.md) |
| RAG evaluation | [Answer Gold](docs/evaluation/rag_gold_v1_protocol.md), [baseline](docs/evaluation/rag_baseline_v1.md) |
| Explicitly authorized Kaggle work | [GPU Playbook](DocLens_AI_Kaggle_GPU_Playbook.md), [tool commands](tools/kaggle_gpu/README.md) |

Install CPU dense dependencies explicitly when needed:

```bash
python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e ".[dev,eda,dense]"
```

Common validation/evaluation commands:

```bash
python -m doclens_ai.evaluation validate --gold docs/evaluation/synthetic_retrieval_gold_fixture.jsonl
python -m doclens_ai.retrieval_baseline --output-dir evaluation-output/bm25-new-run
python -m doclens_ai.dense_baseline --qdrant-url http://127.0.0.1:YOUR_DISPOSABLE_PORT --output-dir evaluation-output/dense-new-run
python -m doclens_ai.extraction.fidelity_eval --corpus local-corpus --manifest docs/eda/corpus_v1_manifest.csv --gold local-evaluation/extraction_fidelity_v1.jsonl --output-dir evaluation-output/fidelity-new-run
python -m doclens_ai.retrieval_eval --model-dir /private/e5 --user-id TRUSTED_USER_UUID --workspace-id AUTHORIZED_WORKSPACE_UUID --output-dir evaluation-output/retrieval-new-run
python -m doclens_ai.rag_eval --synthetic --output-dir evaluation-output/rag-new-fixture-run
```

Real RAG evaluation additionally requires approved Answer Gold, `SEARCH_*`,
`DATABASE_URL` and `RAG_*`; see `python -m doclens_ai.rag_eval --help`.
Synthetic fixtures test mechanics only. Frozen candidate runners remain available
for reproduction; rejected configurations remain rejected in their measured scope.
