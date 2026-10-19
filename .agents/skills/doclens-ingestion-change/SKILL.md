---
name: doclens-ingestion-change
description: Change DocLens upload, parsing, cleaning, chunking, embeddings, indexing, jobs, retries or delete/reindex behavior. Not for offline parser or RAG quality evaluation without ingestion changes.
---

# DocLens ingestion changes

## Apply and inspect

Use for lifecycle implementation. Read AGENTS.md and only affected functions in
services/upload.py, processing.py, ingestion.py or indexing.py under src/doclens_ai,
their models/configuration, persistence boundaries and focused tests. Consult
[architecture upload/jobs/index contracts](../../../Doclens_AI-architecture.md#ARCH-UPLOAD) for changed boundaries, not as a full-repository prerequisite.
Use extraction-benchmark or rag-evaluation separately when making quality claims.

## Invariants and workflow

1. Map upload -> extraction -> validation/safe cleaning -> canonical chunks ->
   embeddings -> verified index. Distinguish actual enums/checkpoints from target stages.
2. Preserve immutable RAW bytes in S3/MinIO; verify size/SHA and DB references.
   Keep workspace/document Idempotency-Key identity, replay and conflict semantics.
3. Define ProcessingRun/Job transitions, lease/token/DB-clock fencing, heartbeat,
   cancellation, bounded retry and terminal failure. A stale owner cannot publish
   or change another worker's job. Keep external work outside long DB locks.
4. Preserve deterministic chunk identities, complete atomic chunk publication,
   lineage and source/parser/chunker/model/configuration fingerprints. Safe cleaning
   must retain facts and genuine provenance; never fabricate structure/coordinates.
5. Verify Qdrant points and canonical linkage before transactional ACTIVE cutover.
   Keep partial/stale candidate revisions unsearchable and the previous verified
   revision intact on failure. PostgreSQL is authoritative; Qdrant is rebuildable.
6. Define delete/reindex and recovery before changing behavior: authorized scope,
   obsolete revision fencing, retry, reference-checked orphan cleanup and rebuild.
   Existing upload/index code does not establish a delivered deletion lifecycle.

## Failure modes

Exercise duplicate/interrupted ingestion, hash mismatch, corrupt/unsupported input,
parser/embedding/storage/Qdrant failure, cancellation, reclaimed leases, partial
upserts and concurrent versions. One source must not corrupt unrelated processing.
Keep failed/needs_review explicit and prevent cross-workspace leakage.

## Verify and report

Run targeted deterministic/state/retry tests first; use real persistence/storage/
Qdrant integration where the changed boundary requires it. Evaluate fidelity or
retrieval on fixed Gold if affected; implementation tests are not ML quality evidence.
Report actual transitions, unchanged invariants, commands/results, fingerprint
changes, rollback/cleanup implications and missing checks under AGENTS.md.

Accept only when the changed lifecycle, applicable fidelity and tenant-isolation
checks pass; unresolved critical publication/recovery failures block completion.
