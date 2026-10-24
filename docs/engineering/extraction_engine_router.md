# Extraction engine routing contract

The router foundation and extraction integration now use one exact-pin registry.
This is an engineering contract, not model onboarding, extraction-quality approval,
an OS security sandbox or production release authorization.

## Single API

- `EngineDescriptor` declares name, revision, implementation SHA-256, supported
  formats and `EngineCapability` values: native text, structured tables, spatial
  locators and OCR. Claims describe selection requirements; they prove no fidelity.
- `ExtractionEngine.extract(Path, options_json=...) -> DocumentIR` retains candidate
  observations. `NativeEngine` lazily invokes the unchanged native parser and
  retains its complete `ExtractionResult` as `DocumentIR.native`.
- `EngineRegistry.register` is an application-owned allowlist. Duplicate exact pins
  are rejected; explicitly pinned revisions may coexist. `descriptors` lists the
  registered descriptors without loading optional engines or models.
- `resolve(pin, format, require=...)` checks exact identity, format and capability
  requirements. `select_format` accepts supported extensions case-insensitively;
  the parser still validates the actual input bytes.
- `EngineRegistry.extract(path, route=...)` checks every selected pin before any
  extraction. It is the low-level trusted adapter boundary, not an execution sandbox.
  Ingestion invokes it only through `BoundedEngineExecutor` with pinned budgets.
  There is no additional name-only dispatcher, implicit fallback or preprocessing.

Only native is registered by default. No OCR/layout model or dependency is added.
All native options are explicit in the pin. Unknown identities, changed identities,
unsupported formats and missing capabilities fail closed.

## Requirements, fingerprints and historical artifacts

Current `EngineRoute.version` is **1.2**. `required_capabilities` is an immutable,
unique, lexically sorted tuple, applied to **every** selected engine. It participates
in the route and processing fingerprints, durable artifact bytes and DB-immutable
route snapshot. Missing capability is rejected during ingestion configuration
validation before RAW processing/engine invocation, and checked again in the child.

Artifact readers preserve the exact v1.0 and v1.1 route shapes/fingerprints; they do
not inject capabilities or execution controls into historical evidence. These old
routes cannot silently execute as v1.2. Re-chunking requires the same extraction
pins and capability requirements as the stored snapshot, in addition to independent
source/review checks; no engine registration is needed to read retained evidence.

## Candidate selection and evidence trust

Registration/capability claims never establish production approval. An engine's
`reviewed_for_production` flag and the prototype `production=False` switch are not
accepted authority. Offline callers can inspect explicit candidate IR through the
same registry. Production verified-IR admission requires trusted application-owned
engine/reviewer allowlists and a source/tenant/version-bound independent review.
No upload request grants PDF trust, and native/default PDF admission stays closed.

Verified-IR chunking reports `complete`, `partial_review_required`, or `blocked`.
Only `complete` may persist canonical chunks. Rejected/unreviewed elements,
held oversized units, or a partial document keep diagnostic artifacts but cannot
silently publish the remaining prefix. Failed reprocessing preserves existing
ACTIVE data. Current validator/chunker pins are 2.1/2.2; historical pins remain
readable and require explicit compatible reprocessing rather than silent execution.
Index preparation and transactional ACTIVE cutover also reject obsolete verified-IR
routes/chunks, including candidates verified before rollout. Existing records are
retained; this guard does not rewrite or retrospectively certify earlier ACTIVE data.
Containment and semantic relations remain atomic; reading-order links connect
independent units. Canonical text provenance labels rendered offsets separately
from an optional native TextBlock offset map; no native offsets are inferred for IR.

The prototype `extract_routed -> ExtractionResult` API is deliberately superseded
by the single versioned IR API. Native callers needing the original result use
`.native`; candidate observations remain distinct from approved searchable chunks.
No lossy wrapper or parallel unbounded dispatch mechanism is introduced.

## Extension, rollout and rollback

New adapters must pin models/artifacts, effective options and their implementation,
preserve real source locators and exact facts, retain failures/unknown observations,
and pass independent evidence review and applicable quality gates. Capability names
are not substitutes for those checks. GPU execution remains unsupported by the
bounded executor. Resource limits are not a network/egress security sandbox.

Apply migrations `0008_extraction_route` then `0009_extraction_artifacts` before new
application code. Drain/stop old workers before producing new route snapshots.
Changed runtime/code/route fingerprints require explicit compatible reprocessing;
never rewrite queued snapshots or fabricate pins for historical NULL routes.
A downgrade removes artifact DB identities (0009) and route snapshots (0008).
It does not roll back external S3/Qdrant writes and is not an in-place preservation
strategy for new runs. Back up DB and immutable objects before an authorized rollback.
Downgrade/re-upgrade checks use only task-owned disposable databases.

Sources: `Doclens_AI-architecture.md`, `DocLens_AI_Extraction_Strategy.md`,
`DocLens_AI_ML_Quality_Strategy.md`, `DocLens_AI_Project_Goals_and_Quality_Policy-1.md`.
Current verification and prototype behavior mapping:
`audit_closure_20261024.md`. Historical integration execution:
`extraction_integration_20261022.md`.
