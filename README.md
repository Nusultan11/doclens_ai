# DocLens AI

DocLens AI currently provides the Backend Core foundation for a production-oriented document intelligence system. This stage includes a FastAPI service, typed configuration, async PostgreSQL connectivity, SQLAlchemy/Alembic foundations, and health endpoints.

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

The PostgreSQL integration test runs only when `TEST_DATABASE_URL` is set to an async PostgreSQL URL. For example:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://doclens:doclens-local@localhost:5432/doclens pytest -m integration
```

Validate the current Alembic environment against the configured database:

```bash
alembic current
```

No business schema exists yet. Future schema changes must be created as Alembic revisions rather than by editing database state manually.
