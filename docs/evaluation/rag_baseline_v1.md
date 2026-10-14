# Stateless grounded RAG baseline v1

Starting commit: `d11de6e7d808bc90c61de54bcc14ed51d1359ace`.
This is a model-independent security/mechanics baseline, NOT a validated real-model quality release.
The repository rag-evaluation skill requires separate structural, authorization and human quality
gates. Hypothesis: bounded evidence and deterministic reference checks can fail closed on malformed,
forged or stale generated output without weakening existing retrieval. No retrieval/semantic
superiority is claimed. Failure modes include irrelevant nearest neighbors, injection, fabricated
citations, stale ACL/revisions, truncation, incomplete answers and valid quotes supporting false claims.

## Pipeline and limits

Authenticated `/api/v1/answers` -> existing authorized retrieval -> deterministic bounded evidence ->
operator-managed local HTTP generator -> strict JSON/schema/reference checks -> fresh PostgreSQL
authorization -> answer or refusal. No conversation persistence, migration, ingestion/indexing changes,
raw-token streaming, tools, reranking, agents, downloads or dependency additions.

Retrieval candidates 20; context maximum six chunks. Sort by descending verified score then chunk
UUID; dedupe IDs and exact-text SHA. Deduplication chooses one provenance for identical text rather
than merging documents; it can omit alternate-source evidence. Qdrant boundary ties retain the
existing bounded-candidate limitation. Limits: serialized question/evidence JSON 16,000 Unicode
characters, each source prefix 4,000. Binary-search prefix packing accounts for JSON escaping and
locator overhead. Oversized metadata/blank text can be excluded; no packed evidence refuses without
generation. A local generator tokenizer is not available, so no exact token or model-window claim
is made. System prompt/output reserve must fit the operator's actual tokenizer/window. Server context
overflow fails closed rather than silently changing the prompt. Tables can be truncated mid-row.

Instructions are a fixed system message; question and evidence are a single escaped user JSON data
object. Evidence carries authorized chunk/document/version/index revision and PG source locator.
Injection strings cannot become a system message, but prompt separation is not proof a real model
will ignore them. Model output is never trusted solely because it followed the JSON mode request.

Prompt version `grounded-qa-v1`; deterministic SHA is reported by `rag_eval`. Generation defaults:
temperature 0, maximum output 1,024 tokens, total HTTP deadline 60 s, queue 1 s, concurrency 1,
raw HTTP response cap 65,536 bytes. Prefix budget/configuration and prompt hash enter the experiment
fingerprint. Temperature zero does not guarantee deterministic inference on arbitrary servers.

## Output gate and authoritative citations

JSON keys exactly answerable/answer/citations/reason. True requires nonblank answer, nonempty citations,
null reason. False requires null answer, empty citations, insufficient_evidence. Backend additionally
uses no_relevant_context or source_unavailable. No confidence field. Backend-generated UUID request
ID does not establish persistence/idempotency. Input selectors never grant authorization.

Citation fields: chunk/version ID, exact quote plus zero-based exclusive quote offsets into the
PACKED prefix, and answer span offsets. Each chunk may be cited once; every nonwhitespace answer
character must be covered. Unknown metadata, invented/duplicate IDs, wrong versions, wrong quote
positions, hidden-suffix quotes, uncovered answer text and contradictory types are rejected.
Backend constructs document IDs/locators from authoritative evidence, never model metadata.
Offsets in public source locators remain extraction-unit offsets, distinct from quote/answer offsets.
Exact quote matching and covered spans are necessary reference checks, not semantic support proof;
a model can still make a false statement while quoting unrelated real text. There is no automatic
faithfulness guarantee, calibrated similarity threshold or uncalibrated confidence score.

Malformed model content/refusal/citations is suppressed and becomes insufficient_evidence, with
only a boolean rejected-output metric. HTTP timeout/connection/protocol/size/identity failure is a
sanitized 503. No JSON repair, fabricated citation or partially supported answer is released.
Missing context bypasses the generator; irrelevant nonempty context permits explicit model refusal.

ALL packed sources are freshly revalidated after inference, including on refusal/invalid output:
membership, chunk/run/document/version/workspace linkage, completed indexing run, exact ACTIVE
index/configuration, original canonical text hash/locator and source SHA. Revalidation queries PG
only in new sessions, never Qdrant or unauthorized source lookups. Revoked membership denies 403;
missing/deleted/superseded sources refuse source_unavailable. No locks/transactions span inference.
Revocation/cutover after the final PG check and before/during delivery remains a residual race.

## Local provider and artifact provenance

One existing-httpx adapter uses non-streaming `/v1/chat/completions`, JSON-object mode, one choice,
system/user messages and exact configured model identity. It rejects redirects, compressed bodies,
non-JSON, duplicate keys/nonfinite JSON, wrong model, tool/reasoning/extra message fields, non-stop
finish reason and excessive bytes. No tools are sent/executed; proxy inheritance disabled; TLS
verification retained. Endpoint is operator-only, literal private/loopback IP, no DNS/rebinding,
public APIs, URL secrets/query/fragment or arbitrary client endpoints. Operator must ensure that
private address actually hosts local inference rather than forwarding sensitive data externally.
Cancellation closes local HTTP streams/releases capacity; remote compute may continue, so independent
inference-server concurrency/cancellation and ingress limits are required. No unsafe process kill.

Model ID echo is protocol compatibility, NOT artifact attestation. Optional declared 40-hex revision
and 64-hex artifact SHA are metadata only, always marked unverified by adapter. A real pinned smoke
requires: approved local source/revision/license; hashes of actual loaded weights, tokenizer, chat
template/config and any quantized derivation; conversion recipe/revision/parameters and original
hashes; runtime build/container digest; server model config and inspected mounts; no network model
download; proof the queried process uses those inspected bytes. Record all of this independently
before describing it as verified pinning. Never accept `/models` name alone as proof.

Official compatibility references (configured documentation MCP unavailable; narrow official web
fallback): [Chat Completions envelope](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
and [JSON mode limitations](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat).
No OpenAI hosted inference is used; local vendor behavior must still pass the strict adapter contract.

## Real-model and real-quality status

NOT EVALUATED: no operator-configured local generator endpoint or Qwen3-8B artifacts were supplied.
`RAG_*`/`LLM_*` environment inventory was empty, no llama-server/ollama executable was found, and
Docker inventory contained no generator runtime. NVIDIA preflight: RTX 3050 Laptop, 4,096 MiB total,
3,794 MiB free at sampling; host RAM 16,541,597,696 bytes. This does not prove CPU/offload/quantized
Qwen3-8B impossible; capacity/context/latency need an actual approved artifact/runtime test. No model
was silently substituted, installed/downloaded, or represented by the deterministic fake generator.

Private evaluation inventory contained Retrieval Gold/review/candidates only, not reviewed RAG
answer annotations or reviewed generated outputs. Real answer correctness, human citation support,
unsupported-claim rate and RU/KK quality are NOT EVALUATED. Release requires the independent protocol
in `rag_gold_v1_protocol.md`, actual local-model smoke and reviewed generated-output error analysis.

## Executed synthetic evaluation

Four explicit in-memory mechanics fixtures, English only, one positive and three negative. They do
not use the real corpus or a real model. Exact answer match 4/4; answerability precision/recall 1/1;
refusal precision/recall 3/3; delivered valid citation references/quotes 1/1; required anchor coverage
1/1; dependency/model/retrieval failures 0/4; actual retrieval-empty 1; insufficient_evidence 2,
no_relevant_context 1; rejected malformed output 1. Human quality metrics all null/NOT EVALUATED.
These values test code paths, not real groundedness. Generated metrics are ignored and metadata-only.

Final synthetic runs:

```text
.venv/Scripts/python.exe -m doclens_ai.rag_eval --synthetic --output-dir evaluation-output/rag-v1-synthetic-final-1
.venv/Scripts/python.exe -m doclens_ai.rag_eval --synthetic --output-dir evaluation-output/rag-v1-synthetic-final-2
```

Both exit 0. Every metric/configuration/fingerprint except latency is identical. Gold fingerprint
`8c8411522bb5c984078ed071a0fdc58a9a08ef6e2139a756758248ae6a6a7c7b`; prompt SHA
`33622b5889415d5ec23df5995dfa647d4d8b0b3369838f03934b355be052ec89`; normalized results SHA
`d2c7437bd65a8286335b1e01f0f45010ec01955beb3663722641accb964c9cd8`.
Observed synthetic latency P50/P95: 0.176/0.537 ms and 0.207/0.540 ms. These are four in-memory
fake-provider cases, NOT inference/production/RAG quality latency benchmarks. Source inspection
and automated tests confirmed no question/answer/quote/worksheet/path/token/credential fields in
reports; output directories were confirmed Git-ignored.

## Actual verification

Host Windows `.venv`, Docker Linux Python 3.12, disposable private-network PostgreSQL 16, MinIO and
Qdrant 1.15.4, read-only current-source bind. No existing unrelated container/process was stopped.
All requested integration cases ran, not skips. Existing dependencies were used; pytest/ruff were
installed only in disposable verification containers, not added to repository requirements.

```text
.venv/Scripts/python.exe -m ruff check src tests alembic
  All checks passed.
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit
  344 passed in 10.63 s (final host run)
docker exec doclens-rag-1791973874788-tests python -m pytest -q tests/integration/test_retrieval.py tests/integration/test_search_api.py tests/integration/test_rag.py tests/integration/test_answers_api.py
  40 passed in 128.45 s; one harmless read-only pytest-cache warning; zero skips
  Final-source repeat: 40 passed in 125.13 s; same one warning; zero skips
docker exec doclens-rag-1791973874788-tests python -m pytest -q -p no:cacheprovider
  480 passed in 408.80 s; zero skips
python -m alembic upgrade head
  All seven existing migrations applied to disposable smoke databases.
python -m alembic check
  No new upgrade operations detected.
docker compose -f compose.yaml -f compose.search.yaml -f compose.rag.yaml config --quiet
  exit 0
git diff --check
  exit 0
```

The initial targeted run failed 16 existing retrieval tests because the disposable MinIO bucket was
not initialized (HeadBucket 404), while 24 passed. Standard `python -m doclens_ai.storage.s3` created
the private bucket; the complete target suite was rerun successfully. No tests or production storage
behavior were weakened. Early Ruff formatting findings were fixed and checks rerun.

Security regression coverage includes cross-workspace/document selectors, revocation during answers
and refusals, actual new-version index cutover, deletion of UNcited packed evidence, PG-only exact
revalidation, forged/wrong-version/duplicate/unrelated quote citations, hallucinated metadata,
malformed/inconsistent output, empty/irrelevant context, injection separation, timeout/connection/
size/redirect/tool/identity failures, queue bounds/cancellation/concurrency, JWT, sanitized errors,
PDF/DOCX/XLSX source locations, valid answer and refusal. Sanitized answers-route 422 responses never
echo private question input. Default API behavior/search remains unchanged except new opt-in route.

## Actual Docker HTTP smoke

Reused existing local default/ML images with current source bound read-only; no image build/model
download was claimed. Default API had no Torch/Transformers/DOCX dependencies, live/ready 200 and
unauthenticated answers 401. ML smoke was capped at four CPUs/4 GiB, with existing pinned E5 assets
read-only. Its explicit `run_network_smoke` helper in `tests/integration/test_answers_api.py` started
real Uvicorn TCP API and local HTTP fake-generator servers; OIDC signed JWT verification retained
the existing controlled in-memory JWKS fixture, no authentication bypass. Synthetic uploaded DOCX
included an injection string; ingestion/indexing used existing real services and verified E5 bytes.

Actual helper command inside the disposable container:

```text
python -c "import asyncio,os; from doclens_ai.storage.config import get_storage_settings; from tests.integration.test_answers_api import run_network_smoke; asyncio.run(run_network_smoke(os.environ['DATABASE_URL'], get_storage_settings(), '/models/e5'))"
```

Final exit 0: readiness 200; authenticated unconfigured generator 503; Search 200; supported answer
200 with authoritative DOCX locator; explicit refusal insufficient_evidence; actual new-version
cutover during HTTP generation source_unavailable with null answer; membership revocation 403 with
no source text. The fake generator is deliberately NOT Qwen or a real generation-quality result.
First helper attempts exposed only helper bugs (str instead of Path for E5; locally scoped FastAPI
Request annotation under deferred annotations). Both were fixed in the allowed new test file and
the full TCP smoke repeated successfully. Production model loading/algorithm/security did not change.

## Remaining operational limits

Real generator smoke is blocked by absent approved local Qwen3-8B artifacts/runtime/endpoint, not
reported as passed. Reviewed answer Gold and bound human generated-output judgments are absent.
Character budgets, prefix/dedupe information loss, quote-vs-meaning distinction, and final-check race
remain explicit. No RU/KK quality or release-quality groundedness claim. Operators must supply and
verify generator provenance, server limits/tokenizer budget and human evaluation before release.

Out-of-scope finding: the existing `.dockerignore` does not exclude ignored local corpus/evaluation
directories. Dockerfile copies only explicit source/config paths, but a future image build can still
send private assets in the build context. It was not changed (not permitted by this task); smoke used
existing images/read-only source mounts, not a build containing those assets.
