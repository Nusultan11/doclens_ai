---
name: doclens-production-readiness
description: Audit or qualify DocLens operational/release readiness through real service, security, recovery and E2E gates. Not for ordinary feature edits or claiming readiness from unit tests/offline model results.
---

# DocLens production readiness

## Apply and inspect

Use when release qualification, an operational audit or a production gate is requested.
Read AGENTS.md, relevant README operating sections, Compose/profile configuration,
current migrations and selected integration/E2E reports/tests. Inspect architecture
sections 16–20 for security, observability and Definition of Done. Do not infer
gates passed from code presence or historical tests alone.

## Invariants and workflow

1. Build a requirement/evidence matrix: IMPLEMENTED, TARGET, CANDIDATE, REJECTED,
   NOT_EVALUATED. Separate this run's checks from historical recorded evidence.
2. Use isolated disposable resources for real clean Compose startup and migrations;
   never delete shared volumes or reset user databases. Verify enabled profile
   health/readiness, required dependencies and fail-closed missing configuration.
3. Exercise JWT/OIDC and PostgreSQL workspace authorization across API, S3/MinIO,
   canonical chunks and Qdrant. Verify authorized source/ACTIVE linkage and final
   revalidation, cross-tenant attacks, stale revisions and revocation boundaries.
4. Test worker durability, leases/heartbeat, bounded retries, cancellation/fencing,
   duplicate upload/ingestion and atomic verified ACTIVE cutover.
5. Require index rebuild/recovery, delete/reindex safety, reference-checked orphan
   cleanup, backup AND restore evidence. If lifecycle code is absent, record TARGET/
   BLOCKED for that gate, not passed recovery.
6. Use scoped fault injection for DB/storage/parser/embedding/Qdrant/LLM failures
   and partial indexing. Verify source preservation and no unauthorized/stale release.
7. Require repeatable CI/E2E and deployment profile evidence, safe Git history,
   secret handling, realistic resource/load observations and rollback.
8. Apply independent real-model correctness/groundedness/refusal and semantic
   citation gates. Offline execution, valid JSON and structural binding cannot
   qualify rejected generators/parsers as production-ready.

## Failure modes and acceptance

No release PASS with failed critical isolation/integrity/recovery/quality gates.
Skipped or unsupported gates stay visible; missing environment is BLOCKED, not
success. Distinguish liveness, DB readiness and readiness of all enabled mandatory
services. No mock/synthetic-only evidence substitutes for real integration.

## Verify and report

Execute applicable existing migration, integration, security/fault and E2E commands
against the declared disposable environment. Run only authorized load/failure work.
Report exact commands/results, service versions/profile, cleanup/rollback, each
passed/failed/skipped gate and remaining targets. Production promotion requires an
explicit decision; this skill grants no deployment or external-write authorization.
