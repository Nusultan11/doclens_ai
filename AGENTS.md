# DocLens AI Project Instructions

## Project

DocLens AI is a production document intelligence system for PDF, DOCX, and XLSX ingestion, search, source-grounded Q&A, structured extraction, version comparison, and contradiction analysis.

Correctness, reproducibility, isolation, explainability, and measurable quality are more important than feature count.

## Source and context policy

- Read only task-relevant files. Do not scan the repository or require the architecture document for every change.
- Use applicable `AGENTS.md` files, repository skills, and task instructions for architectural constraints. Do not treat a separate architecture document as required context or a blocker.
- For version-dependent behavior, determine the repository's version first, then query the configured documentation MCP server narrowly.
- Prefer evidence in this order: repository code, tests, migrations, and configuration; explicit DocLens architecture constraints; version-matched official/vendor documentation from MCP; primary papers or curated engineering references.
- Generic external guidance must not override repository architecture. Name material external sources in the completion report.
- Never put MCP credentials, tokens, or other secrets in Git.

## Architecture invariants

Preserve these unless the task explicitly changes the architecture:

- PostgreSQL is the source of truth for business state, document metadata, processing state, ownership, jobs, conversations, usage, and audit data.
- Qdrant is a rebuildable retrieval index, not a primary business database. Original documents and artifacts belong in object storage when that layer is introduced.
- Ingestion is explicit and reproducible: upload -> extraction/parsing -> cleaning/validation -> chunking -> embeddings -> indexing.
- Ingestion is idempotent. Retries must not create duplicate rows, chunks, vectors, or inconsistent states.
- A document failure must not corrupt or stop unrelated processing. Embedding, LLM, storage, and Qdrant failures must not corrupt PostgreSQL business state.
- Chunking configuration, embedding model/revision, retrieval parameters, prompts, and important metadata must be configurable and reproducible.
- Enforce tenant, workspace, and document isolation server-side. Trusted backend code constructs authorization filters; never accept Qdrant scope filters blindly from clients.
- A document-grounded answer may use only context selected by the retrieval pipeline. Treat LLM output as untrusted input and validate structured output or state changes.
- Abstain when evidence is insufficient. Preserve traceability to source chunks, pages, and documents where applicable.

## Engineering boundaries

- Prefer simple, explicit Python/FastAPI services and established repository patterns.
- Do not add a framework, infrastructure component, abstraction, queue, cache, service, or dependency without a concrete current requirement.
- Do not add LangChain, LangGraph, Kafka, RabbitMQ, Kubernetes, Terraform, microservices, or agent frameworks for appearance. Preserve existing workers; add a worker system only when durable background processing is required and the simpler design is insufficient.
- Do not implement future architecture stages early.
- Make the smallest correct change. Do not modify or refactor unrelated code; preserve existing behavior.
- Follow existing naming, typing, error-handling, logging, configuration, and module conventions unless strongly justified.
- Report out-of-scope issues instead of fixing them silently.

## Bug fixes

Use: reproduce -> identify root cause -> smallest correct fix -> regression test -> verification.

Do not patch only the visible symptom. Avoid broad refactoring for a local bug unless the architecture requires it.

## Testing

- Match verification to risk. Run targeted tests first; use broader suites for cross-cutting or release-critical work, or when targeted coverage is insufficient.
- Diagnose failures caused by the change, fix them, and rerun affected checks. Report commands and results; never claim checks "should pass."
- Distinguish pre-existing failures from failures caused by the task.
- When relevant, cover repeated ingestion, empty/corrupted documents, unsupported types, parser/embedding/LLM failures, unavailable Qdrant, insufficient context, metadata/workspace filtering, deletion/reindex, and migrations.

## ML and RAG discipline

- Use this progression: EDA/data quality -> simple baseline -> fixed offline evaluation dataset -> ingestion -> embeddings/indexing -> retrieval -> reranking only when measurements justify it -> generation -> end-to-end evaluation -> fine-tuning only after documented error analysis.
- Do not prepare training data or train before appropriate EDA. Fine-tuning is not the default and cannot replace document retrieval.
- Do not claim a RAG improvement from subjective examples. Compare on fixed data and identical conditions where practical.
- For changes to chunking, embeddings, retrieval, fusion, reranking, context selection, prompting, or generation, track applicable measures: retrieval recall/hit rate, top-k relevance, abstention/insufficient-context behavior, faithfulness or unsupported claims, citation quality, latency, and ingestion failures.
- Reserve fine-tuning for behavior such as output format, extraction, citation/refusal, or task following. Consider LoRA/QLoRA only after baseline and RAG evaluation plus documented error analysis show a need.

## Database and migrations

- Use the repository migration mechanism for PostgreSQL schema changes, normally Alembic when present.
- Never silently rewrite an applied migration for a new schema change. An exception requires an explicitly disposable pre-release migration state and a task that directs the rewrite.
- Verify migration execution and add appropriate regression or integration coverage.
- Keep PostgreSQL consistent when Qdrant, embeddings, storage, or other dependent systems fail.

## Security

- Never commit `.env`, API keys, passwords, access tokens, private credentials, provider/model secrets, or generated sensitive data.
- Apply project file-upload policy for extension, MIME type, magic bytes, and size where relevant.
- Never trust client-provided ownership or authorization filters.
- Avoid logging document content, credentials, tokens, or sensitive user data.
- Do not send sensitive documents to an external LLM unless project policy explicitly permits it.

## Git

- Keep each implementation step logically isolated. Use Conventional Commits: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`, or `ci:`.
- Before committing, inspect `git diff` and `git status`; confirm verification passed and no secrets, artifacts, or unrelated changes are staged.
- For an implementation task explicitly scoped as a completed project step, create one logical commit after successful verification. Never include unrelated pre-existing changes.

## Completion

Implementation alone is not completion. Continue through implementation -> relevant verification -> fixes -> final verification -> diff/status review -> requested commit.

Re-check these instructions before reporting. Use exactly this completion-report structure:

```text
STATUS: DONE | BLOCKED

CHANGED
- What changed and the files changed.

DESIGN
- Important decisions and any material external documentation source.

VERIFIED
- Exact commands executed and actual results.

REMAINING
- Genuine out-of-scope issues, skipped checks, blockers, or environment limitations; "None" if empty.

COMMIT
- Commit hash and subject when committed; otherwise "Not created" with the reason.

GIT STATUS
- Final `git status --short` output, or the exact reason it could not be obtained.
```

Use `STATUS: DONE` only when required verification passed and all requested in-scope work is complete. Clearly distinguish implementation from verification.
