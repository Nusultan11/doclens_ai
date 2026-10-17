---
name: doclens-db-migration
description: Add, review or debug DocLens PostgreSQL schema migrations and their compatibility, constraints or concurrent data transitions. Not for ordinary queries or model logic without a schema change.
---

# DocLens database migrations

## Apply and inspect

Use for Alembic/schema work. Read AGENTS.md, the affected model, current migration
head and relevant revisions, callers of changed fields and focused DB tests.
Inspect only those paths; architecture section 4 is needed only for a changed invariant.

## Invariants and workflow

1. State the before/after schema, ownership and rollout/backfill/downgrade contract.
   PostgreSQL owns ACL, immutable versions/chunks, jobs and IndexRevision state.
2. Add a new Alembic revision; never rewrite applied history. Prefer additive
   compatibility; document application/migration ordering when versions overlap.
3. Review FK/unique/check/null constraints, defaults, indexes, existing data and
   backfill cost. Preserve the partial unique ACTIVE revision per document; no
   independent active pointer. Inspect affected lock order/isolation and races.
4. Specify failure/rollback effects, irreversible data loss and safe retry. Do not
   imply that a DB rollback undoes S3/Qdrant operations.
5. Use a disposable, explicitly scoped database for clean upgrade and supported
   downgrade/re-upgrade checks. Never reset an existing user database to test a migration.

## Failure modes

Check duplicate versions/chunks, orphan references, concurrent uploads/cutovers,
stale leases, constraint violations, long locks and partially applied backfills.
Data changes must preserve schema/data consistency and tenant scope.

## Verify and report

Execute repository Alembic commands against the disposable DB, plus focused
integration/regression tests for constraints, preservation and concurrency.
If downgrade is intentionally unsupported, document why and verify the recovery
path; do not claim it passed. Report exact revisions/commands/results, data/lock
risks, rollout order and skipped/environment-blocked checks using AGENTS.md.

Accept only after schema/data constraints and supported migration paths pass.
Missing required DB execution is BLOCKED, not a successful migration check.
