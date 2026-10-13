# Offline BM25 retrieval baseline v1

## Goal and experiment discipline

First real lexical baseline, evaluated against frozen human-reviewed Retrieval Gold v1.
This is an offline experiment, not a production retriever, authorization mechanism, or RAG system.
It adds no dependencies, embeddings, Qdrant, network services, database writes, or generation.
The existing extraction, chunking, Gold validation, ranked-results parser, and evaluator are
unchanged. Repository contracts and the ingestion/RAG-evaluation skills guided the handoffs,
failure isolation, evaluation separation, and reproducibility; no external documentation was needed.

The settings below were frozen before the first real run. Run 1 is the reported v1 baseline;
run 2 independently verified determinism, not a parameter search. No development or held-out
labels were used to tune settings. Both splits query one identical full index, without filtering
by Gold source, evidence, family, answerability, category, or split. The ranking boundary accepts
question IDs/text only; IDs label output and never contribute to scores.

## Frozen inputs and fingerprints

Pre-implementation HEAD: `05d85a785c55b9303edbde5d1a81e4f436be8594`, initially clean.
Corpus v1: 90 unique verified sources, 30 each PDF/DOCX/XLSX; every file's SHA-256 and byte size
matched the committed manifest. Actual byte identity maps to opaque manifest IDs, independent
of filename ordering. Missing, additional, duplicate, or changed sources fail preflight.

Gold: `corpus-v1-retrieval-gold-v1`, 48 human-reviewed English questions, 45 answerable with
80 evidence anchors, three unanswerable. There are 36 dev questions (33 positive, three negative)
and 12 held-out test questions (all positive). Selected Gold sources are only 15 documents;
retrieval uses all 56 eligible sources, not that subset. Families remain in their frozen splits.

| Identity | SHA-256 / deterministic fingerprint |
| --- | --- |
| Manifest file bytes | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Corpus sorted ID/hash/size/format records | `77854e7979caaeeaaa526c6dba57123a1661523a61e87ac45cfaa94a12267b99` |
| Gold normalized snapshot | `d6167fcf93d5cbce122e4bc444b478b23a0f02f3556364f1e3be58ad02f1bc94` |
| Chunker configuration | `a7c53272ac7baa3f916e43dc4b96a455fa0daa1437cafe04fd7c90b2840edc4c` |
| Full chunk metadata, excluding text | `fb790b4d4777a679beeb287d2602e080a7beb0c65f20fcdde1cfb57d5a55e4f2` |
| BM25 index identities/text hashes/settings | `986694d3cc7f41301e5d6331eb4f470fd69953d8a4f8852322ac5b26b7f8c096` |
| Ranked-results JSONL bytes | `1d855baa7e4c17ddc47dcd6eb3a965d1f4b33166ff9e8c76b78a44fa8af811c1` |
| Evaluator normalized ranked results | `064bbdd32793c73bc352a34ad2dab69dc16f79faf623cbd3552d89df98917429` |
| Evaluator report fingerprint | `fea872420356de8ac4c0137f339b676e72737350499728c7a4aeca46d81587f0` |
| Quality-report file bytes | `f1e319aef338c1b07032ff8c6a1da343279d3cbeb6e832275d8f3cdab320e3dc` |
| Experiment file bytes | `04db465988e2df60ff210fe9e92772763a50f20f6ae06070fc4ae1e641b5bb4b` |

File-byte hashes and evaluator-normalized fingerprints have different definitions and are not
interchangeable. Latency and environment are outside deterministic fingerprints.

## Corpus construction and exclusions

| Format | Verified sources | Extraction success / indexed documents | Indexed chunks | Excluded |
| --- | ---: | ---: | ---: | ---: |
| DOCX | 30 | 14 | 49 | 16 |
| PDF | 30 | 27 | 325 | 3 |
| XLSX | 30 | 15 | 718 | 15 |
| Total | 90 | 56 | 1,092 | 34 |

All 34 exclusions have reason `extraction_needs_review`; there were zero extraction failures
or additional chunking exclusions in this measured corpus. These are observed counts, not assumed
successes. Ordinary extraction/chunking failures are isolated per source; altered source bytes
invalidate the experiment instead of silently accepting a changed corpus.

Review warning document counts (non-exclusive; do not sum them as exclusions):

| Format | Review warnings and affected source counts |
| --- | --- |
| DOCX | headers 9; footers 8; footnotes 3; drawings 6; nested tables 4; text boxes 2; unsupported body content 5 |
| PDF | insufficient text 3 |
| XLSX | unavailable formula definition 7; missing formula cache 3; drawings 11; comments 1 |

`pdf_table_structure_not_preserved` is informational on all 30 PDFs, including 27 eligible ones;
it does not imply table fidelity is established. The local experiment records warning codes and
opaque IDs for every excluded source, without their filenames, titles, content, or paths.

Chunks use the unchanged structure-aware v1 configuration: 1,200-character limit, 120-character
overlap, `allow_needs_review=false`, maximum 5,000,000 source characters and 100,000 chunks per
document, formula policy `formula_and_cached_value`. Formula definitions/stored cached values
are text features only, never executed or recalculated. Review-gated missing caches remain excluded.

In-memory chunks retain source SHA, format, manifest identity, deterministic chunk ID, ordinal,
configuration version/fingerprint, and full source-unit provenance. Evidence copies actual
normalized source-unit character intervals (half-open Python character offsets), not chunk-relative
positions or Gold spans. This includes the chunker's rendered cell/coordinate prefixes. Returned
anchors preserve PDF page/block, DOCX body/table/row/cell, and XLSX sheet/cell locations.

## BM25 settings

For each query's distinct term `t`, score each chunk `d`:

```text
idf(t) = log(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
score(d,q) = sum(idf(t) * tf(t,d) * (k1+1)
                 / (tf(t,d) + k1 * (1-b + b*len(d)/avg_len)))
```

`k1=1.5`, `b=0.75`, `top_k=10`, version `1.0`. `N` is indexed chunk count, not source count.
Tokenization: Unicode casefold then Unicode alphanumeric runs (`[^\W_]+`); punctuation and
underscores split tokens. No stemming, stopword removal, normalization beyond casefold,
query expansion, reranking, or model. Numerical/alphanumeric tokens and leading zeroes survive;
decimal punctuation separates numeric tokens, and combining marks can split tokens. These rules
are intentionally simple and frozen, not a multilingual morphological solution.

Repeated query terms count once. Query terms are summed in sorted order, postings use sorted stable
chunk IDs, and exact score ties sort by stable ID. Empty/unknown queries yield zero results rather
than zero-score filler. Duplicate IDs with identical text are idempotent; conflicting text for
one ID is rejected. Equal text at distinct source locations remains separate evidence.

Measured vocabulary: 26,651 terms; mean chunk length 177.16483516483515 tokens.
Character chunk sizing is not token sizing; token lengths and semantic scope vary across formats.

## Measured real quality

All metrics are from the unchanged evaluator, with explicit numerators/denominators below.
Values are the serialized 12-decimal evaluator values, not synthetic unit-test quality.
Hit/MRR/nDCG exclude unanswerable queries. Recall is micro-averaged over Gold anchors, not
over documents. nDCG uses binary new-evidence gain and an ideal one-result-per-Gold-anchor
ranking; multiple anchors in one structural chunk therefore can lower nDCG even at rank 1.
MRR is over returned top-10 ranks, so a missing relevant top-10 result contributes zero.

| Metric | Overall | Development | Held-out test |
| --- | --- | --- | --- |
| Hit@5 | 44/45 = 0.977777777778 | 32/33 = 0.969696969697 | 12/12 = 1 |
| Hit@10 | 45/45 = 1 | 33/33 = 1 | 12/12 = 1 |
| Recall@5 | 79/80 = 0.9875 | 56/57 = 0.982456140351 | 23/23 = 1 |
| Recall@10 | 80/80 = 1 | 57/57 = 1 | 23/23 = 1 |
| MRR | 40.666666666667/45 = 0.903703703704 | 31.166666666667/33 = 0.944444444444 | 9.5/12 = 0.791666666667 |
| nDCG@10 | 34.0594168698/45 = 0.75687593044 | 26.245526285116/33 = 0.795318978337 | 7.813890584684/12 = 0.651157548724 |
| Missing-result rate | 0/48 = 0 | 0/36 = 0 | 0/12 = 0 |
| Query coverage | 48/48 = 1 | 36/36 = 1 | 12/12 = 1 |
| Unanswerable result presence | 3/3 = 1 | 3/3 = 1 | 0/0 = null (no negative cases) |

Missing-result rate means no nonempty results, not absent JSONL records. All 48 questions have
records and lexical matches. No relevance threshold or abstention mechanism was introduced.
Result presence on negative questions is not a generated-answer or true abstention measurement.

### Per-category quality

| Category | Hit@5 | Hit@10 | Recall@5 | Recall@10 | MRR | nDCG@10 |
| --- | --- | --- | --- | --- | --- | --- |
| fact | 11/12 = 0.916666666667 | 12/12 = 1 | 11/12 = 0.916666666667 | 12/12 = 1 | 10.166666666667/12 = 0.847222222222 | 10.618066694251/12 = 0.884838891188 |
| number | 13/13 = 1 | 13/13 = 1 | 25/25 = 1 | 25/25 = 1 | 12/13 = 0.923076923077 | 9.851058538423/13 = 0.757773733725 |
| table | 8/8 = 1 | 8/8 = 1 | 20/20 = 1 | 20/20 = 1 | 7/8 = 0.875 | 4.338375085363/8 = 0.54229688567 |
| identifier | 10/10 = 1 | 10/10 = 1 | 21/21 = 1 | 21/21 = 1 | 9.5/10 = 0.95 | 7.251916551763/10 = 0.725191655176 |
| version | 2/2 = 1 | 2/2 = 1 | 2/2 = 1 | 2/2 = 1 | 2/2 = 1 | 2/2 = 1 |
| unanswerable | 0/0 = null | 0/0 = null | 0/0 = null | 0/0 = null | 0/0 = null | 0/0 = null |

For fact/number/table/identifier/version/unanswerable respectively, category query coverage is
12/12, 13/13, 8/8, 10/10, 2/2, 3/3 (all 1); missing-result rate is 0 divided by the same
denominators (all 0). Negative result presence is 3/3 = 1 for unanswerable and 0/0 = null
for each other category. The very small version category is not strong generalization evidence.

### Failure analysis (opaque IDs only)

One positive query misses Hit@5: `rgv1-q-026` (dev/fact), first relevant evidence at rank 6.
Seven other positive queries first match at rank 2: `rgv1-q-005`, `rgv1-q-006`, `rgv1-q-010`,
`rgv1-q-011`, `rgv1-q-022`, `rgv1-q-031`, `rgv1-q-044`. The remaining 37/45 positives first
match at rank 1. All 80 anchors are found within top 10; there is no measured top-10 evidence
coverage failure. This identifies ranking positions, not an unmeasured semantic cause.
All three negatives (`rgv1-q-046`–`rgv1-q-048`) return lexical candidates.
The table-category nDCG limitation reflects the evaluator's chunk-versus-anchor gain definition;
it must not be read as a direct table extraction-fidelity score.

## Latency and environment

Run 1: Windows 11 build 26200, AMD64 Family 25 Model 80 Stepping 0 (AuthenticAMD),
Python 3.12.3 MSC v.1938 64-bit; pypdf 6.20.0, python-docx 1.2.0, openpyxl 3.1.5.
Single process, standard-library inverted index, 48 question samples in stable ID order;
no dedicated load test or controlled idle-machine condition. No hardware acceleration.

| Measurement | First frozen run | Independent repeat |
| --- | ---: | ---: |
| Extraction/chunking/metadata preparation | 13,076.841700 ms | 13,500.385900 ms |
| BM25 index construction | 125.546300 ms | 125.579400 ms |
| Query p50 (48 samples) | 1.483100 ms | 1.469100 ms |
| Query p95 (48 samples) | 2.091125 ms | 1.977415 ms |

Query latency includes casefold/tokenization, scoring, sorting, and top-k selection. It excludes
evidence projection, JSON serialization, Gold scoring, API overhead, and corpus preparation.
Percentiles use linear interpolation at `(n-1)*p`. This is observed offline search cost,
not end-to-end production latency or a confidence interval.

## Reproduction and local privacy

From repository root, with approved private inputs and existing dev/EDA extras installed:

```powershell
.venv/Scripts/python.exe -m doclens_ai.retrieval_baseline --output-dir evaluation-output/bm25-v1-run-1
.venv/Scripts/python.exe -m doclens_ai.retrieval_baseline --output-dir evaluation-output/bm25-v1-run-2
.venv/Scripts/python.exe -m doclens_ai.evaluation evaluate --gold local-evaluation/retrieval_gold_v1.jsonl --corpus-manifest docs/eda/corpus_v1_manifest.csv --results evaluation-output/bm25-v1-run-1/ranked_results.jsonl --json-output evaluation-output/bm25-v1-run-1/cli_quality_report.json
```

Existing output directories are refused to preserve the initial experiment. Use fresh run names
for reproduction. Default inputs are `local-corpus/`, the committed Corpus v1 manifest, and
`local-evaluation/retrieval_gold_v1.jsonl`; the CLI enforces 90 sources and the frozen Gold hash.
API overrides of expected count/Gold hash exist only to exercise synthetic unit fixtures.

Local outputs: strict `ranked_results.jsonl`, unchanged evaluator `quality_report.json`, sanitized
`experiment.json`, and separate nondeterministic `latency.json`. No questions/chunk text, source
filenames, or paths are written. Ranked anchors retain actual worksheet names where required by
the provenance contract, so ranked results are not suitable for publication. All generated outputs
stay in ignored `evaluation-output/`; private Gold and corpus stay ignored and unchanged.

Two separate process runs produced byte-identical ranked JSONL, quality report, and experiment
metadata. The existing CLI report parsed identically to the runner report. Repeat comparison:

```powershell
foreach ($name in @('ranked_results.jsonl','quality_report.json','experiment.json')) {
  $first = (Get-FileHash "evaluation-output/bm25-v1-run-1/$name" -Algorithm SHA256).Hash
  $second = (Get-FileHash "evaluation-output/bm25-v1-run-2/$name" -Algorithm SHA256).Hash
  if ($first -ne $second) { throw "Non-deterministic output: $name" }
}
```

## Verification and limitations

Targeted checks: `ruff check src tests alembic` passed; the BM25 and runner tests plus unchanged
retrieval-evaluator tests passed, 64 total (33 new and 31 existing). An initial default system-Python
invocation lacked the editable package/dependencies; verification used the existing `.venv` instead.
Two sandboxed temporary-file rename tests received WinError 5; the unchanged tests passed in an
approved unrestricted run. No implementation or test weakening was needed for that limitation.

Commands actually executed:

```text
ruff check src tests alembic
  PASS
.venv/Scripts/python.exe -m pytest -q tests/unit/test_bm25_baseline.py tests/unit/test_bm25_runner.py tests/unit/test_retrieval_eval.py
  PASS: 64 tests in 3.83s (approved Windows run)
python -m pytest -q -p no:cacheprovider
  PASS: 189 tests in 91.04s, no skips (disposable Docker test container)
git diff --check
  PASS
```

The full suite used the existing `doclens_ai-api` image, repository mounted read-only at
`/workspace`, `PYTHONPATH=/workspace/src`, and an isolated disposable Docker network with
`postgres:16-alpine` at `postgres:5432` and `doclens_ai-minio` at `minio:9000`.
No host ports or Windows localhost:5432 were used. `TEST_DATABASE_URL` selected PostgreSQL;
the existing private test bucket was initialized with `python -m doclens_ai.storage.s3`, and
`S3_*`/`TEST_S3_*` selected the isolated local MinIO. Local HTTP was confined to the test network;
production security settings were unchanged. Disposable test credentials were not committed.
Transient container installs supplied pytest 9.1.1 and the already-declared EDA extras pinned
to the measured versions. No repository dependency changes or service rebuilds were required.
PostgreSQL, migration, and real object-storage regression tests ran, rather than being skipped.

Workspace-isolation security: **NOT EVALUATED**, zero evaluated queries, 48 unchecked,
`passed=null`. A lexical index without a trusted authorization context cannot validate that gate.
No fabricated workspace IDs were added. Production scope enforcement is unchanged.

This establishes one baseline, not improvement over another measured retriever. Gold is a small
English pilot, test has no negatives, version cases are few, and 34 sources are extraction-gated.
It does not demonstrate RU/KK quality, OCR, complete PDF tables, formula calculation, semantic
matching, adversarial robustness, grounding/faithfulness, citation correctness, or abstention.
Do not infer corpus-wide extraction recall from selected evidence recall.

Next evaluations should use frozen input identities and family splits, more reviewed negative and
multilingual cases, separately assessed extraction exclusions, and identical retrieval conditions
when comparing another method. Any future tuning uses development data with a new experiment
version; do not repeatedly tune against this disclosed held-out test. Authorization needs its own
trusted-scope security evaluation before production retrieval. Generation remains out of scope.
