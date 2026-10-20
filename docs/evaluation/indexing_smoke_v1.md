# Recorded indexing smoke v1

The historical indexing smoke recorded a controlled two-chunk DOCX traversing real MinIO,
PostgreSQL 16, CPU E5 and Qdrant 1.15.4: one active
revision, two fully verified 384-dimensional points and one COMPLETED job; embedding failures 0,
incomplete candidate revisions 0. Worker indexing duration was 1010.662 ms, including 679.023 ms of
embedding, excluding model startup. Separate preflight model load was 12062.060 ms. The exact smoke
configuration fingerprint was
`4aace3473f62dd7648fdb228b682a266ec85f92ff8c71180bbfd93567e3cd524`.
One post-indexing Docker stats sample measured 589.6 MiB worker memory and 17.8 MiB Qdrant memory;
these are point-in-time samples, not peak memory or representative corpus benchmarks.
These recorded observations were not rerun during the documentation audit.

Fault/concurrency integration tests use an explicitly fake deterministic embedding provider with
real PostgreSQL, MinIO and Qdrant; they test persistence/protocol/fencing, not real-model quality.
The separate indexing Docker smoke uses actual pinned weights. Existing
[dense retrieval baseline](dense_retrieval_baseline_v1.md) remains the retrieval-quality evidence: E5 is a
baseline candidate, not a demonstrated BM25 improvement. The indexing smoke does not validate
the separate Search or Answers API paths.

This section was moved from README during repository hygiene cleanup. These are
historical observations, not a new execution or current-HEAD qualification.
