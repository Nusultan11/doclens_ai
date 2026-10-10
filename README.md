# DocLens AI

DocLens AI currently provides the Backend Core and PostgreSQL document-domain foundation for a production-oriented document intelligence system. This stage includes a FastAPI service, typed configuration, async PostgreSQL connectivity, health endpoints, and persistence models for workspaces, logical documents, and immutable document versions.

Document ingestion, authentication, object storage, background jobs, Qdrant, retrieval, RAG, embeddings, and LLM features are not implemented yet.

## Prerequisites

- Docker with Docker Compose, or Python 3.12+ and PostgreSQL 16 for local development

## Run with Docker

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`. Compose uses development-only PostgreSQL credentials and persists data in a named volume.

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

The PostgreSQL integration tests run only when `TEST_DATABASE_URL` is set to a disposable PostgreSQL database whose user can create temporary test databases. For example:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://doclens:doclens-local@localhost:5432/doclens pytest -m integration
```

Apply or revert the document-domain migration:

```bash
alembic upgrade head
alembic downgrade base
```

The current schema stores workspace ownership, stable document identity, and immutable version/file metadata. PostgreSQL rejects updates to persisted document-version rows; future upload flows must validate and confirm the complete file metadata before inserting a version, then create a new version rather than mutate it. It does not store file contents, extracted text, processing state, embeddings, or authorization data. Future schema changes must be created as new Alembic revisions rather than by editing migration history.
