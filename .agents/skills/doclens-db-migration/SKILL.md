---
name: doclens-db-migration
description: Add, change, review, or debug a DocLens database schema migration. Do not use for ordinary database queries or model logic that does not alter or troubleshoot schema migration behavior.
---

# DocLens database migrations

Before changing a migration, inspect the current models/schema, repository migration mechanism, latest migrations, and application code that reads or writes the affected fields.

- Prefer additive, backward-compatible changes when practical. Plan multi-step rollout/backfill when old and new application versions may overlap.
- Review indexes, uniqueness and foreign-key constraints, nullability, server versus application defaults, data volume, lock duration, and downgrade expectations deliberately.
- Keep application and migration ordering compatible; do not expose code that requires a schema state the deployment cannot guarantee.
- Do not rewrite historical applied migrations. Only do so when the repository is explicitly in a disposable pre-release migration state and the task specifically authorizes it.
- Verify the migration executes through the repository's normal tooling. When supported, test upgrade and downgrade or document why downgrade is intentionally unsupported.
- Add a focused regression or integration test when schema behavior, data preservation, constraints, or compatibility could regress.

Inspect the final migration diff for destructive or environment-specific behavior and report commands, results, skipped checks, and rollout risks.
