# DocLens engineering sources

AVAILABLE LOCAL EDITORIAL SPECIFICATION, reconstructed 19 October 2026 from the
reconstruction brief, repository configuration and architecture §22. Owns source
IDs and engineering purposes, not product requirements or a technology roadmap.
Select 2–4 relevant references per task; consult the [source map](README_SOURCE_MAP.md)
for the specification owner. Vendor documentation never proves private-corpus quality.

<a id="CATALOG"></a>
## Reference catalog

IDs are stable; retire rather than reassign them. Verify installed/pinned versions
before applying APIs: `pyproject.toml` has ranges for most libraries and exact dense
pins (Torch 2.8.0, Transformers 4.57.6, Hub 0.36.0). A `/stable/` or `/latest/` URL
is navigation, not a version pin. PostgreSQL 16 and Qdrant 1.15.x references match
the documented runtime family. Model revisions/hashes remain in code/configuration.

Link checks on 19 October 2026: OPEN means a readable page was returned by the web
tool, REDIRECT means the returned destination differs, LIMITED means no readable
body, UNVERIFIED means no successful check in this task. This verifies reachability
only, not installed compatibility, every API assertion or continued availability.

| ID | Official reference | Engineering use and constraint | Link check |
| --- | --- | --- | --- |
| CODE-01 | [Python 3.12](https://docs.python.org/3.12/) | Language/stdlib behavior; use the actual runtime version. | OPEN |
| CODE-07 | [Google code review](https://google.github.io/eng-practices/review/reviewer/) | Scope, correctness and maintainable review; project contracts remain binding. | OPEN |
| API-01 | [FastAPI](https://fastapi.tiangolo.com/) | Request validation, async boundaries and dependencies; verify installed release. | OPEN |
| DB-01 | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) | Transactions/async sessions/locking; don't share sessions across concurrent tasks. | OPEN |
| DB-02 | [Alembic](https://alembic.sqlalchemy.org/en/latest/) | Compatible new revisions and migration commands; never rewrite applied history. | OPEN |
| DB-03 | [PostgreSQL 16](https://www.postgresql.org/docs/16/) | Constraints, transactions, locks and DB clock; qualify concurrency on real PostgreSQL. | OPEN |
| OBJ-01 | [S3 object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html) | Checksum/upload verification; S3 and PostgreSQL are not one transaction. | OPEN |
| OBJ-02 | [MinIO documentation](https://docs.min.io/) | S3 deployment/security reference; redirects to AIStor, whose features must not be assumed in pinned Community builds. | REDIRECT |
| VEC-01 | [Qdrant 1.15 upsert](https://api.qdrant.tech/v-1-15-x/api-reference/points/upsert-points) | Revision-scoped writes; acknowledgement alone is not complete candidate verification. | OPEN |
| PAR-01 | [pypdf extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) | PDF text/layout limitations; no OCR or semantic fidelity inferred. | OPEN |
| PAR-02 | [python-docx](https://python-docx.readthedocs.io/en/latest/) | Word package/body/table behavior; verify unsupported ancillary/section cases separately. | OPEN |
| PAR-03 | [openpyxl](https://openpyxl.readthedocs.io/en/stable/) | Cell/formula/cache/display behavior; no formula execution or invented caches. | OPEN |
| PAR-05 | [Docling](https://docling-project.github.io/docling/) | Candidate adapter representation; current docs do not approve a rejected frozen configuration. | OPEN |
| EXP-01 | [PyTorch reproducibility](https://docs.pytorch.org/docs/2.8/notes/randomness.html) | Seeds and deterministic controls; repeatability must be measured on declared hardware/runtime. | OPEN |
| EXP-02 | [Hugging Face Transformers](https://huggingface.co/docs/transformers/index) | Loading/tokenization/offline behavior; generic page OPEN, exact v4.57.6 page fetch failed and remains unverified. | OPEN |
| RET-01 | [multilingual E5 small](https://huggingface.co/intfloat/multilingual-e5-small) | Baseline instructions/model identity; model card is not retrieval evidence for DocLens. | UNVERIFIED |
| RAG-01 | [Original RAG paper](https://arxiv.org/abs/2005.11401) | Retrieval/generation research context; not a DocLens implementation template or quality result. | OPEN |
| RAG-02 | [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | Untrusted document/context threat model; schema validation alone is insufficient. | OPEN |
| FT-01 | [Hugging Face PEFT](https://huggingface.co/docs/peft/index) | Optional LoRA implementation only after ML training gate; no dependency adoption implied. | OPEN |
| GPU-01 | [Kaggle notebooks](https://www.kaggle.com/docs/notebooks) | Notebook/runtime/CLI discovery; page returned no readable body, check actual CLI/help. | LIMITED |
| GPU-02 | [PyTorch 2.8](https://docs.pytorch.org/docs/2.8/) | CUDA placement, synchronization and memory APIs; enumeration alone is not inference proof. | OPEN |
| SEC-01 | [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | Deny-by-default and per-request access checks; preserve current PostgreSQL authority. | OPEN |
| TST-01 | [pytest](https://docs.pytest.org/en/stable/) | Fixtures/markers/assertion behavior; use installed version and real-boundary tests where needed. | OPEN |
| TST-02 | [pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html) | Positive/negative/failure matrices; test independent behavior rather than mirror implementation. | OPEN |
| OPS-01 | [Docker Compose](https://docs.docker.com/compose/) | Profiles, lifecycle and resource configuration; startup is not migrations or release qualification. | OPEN |
| OPS-02 | [Git reference](https://git-scm.com/docs) | Diff/status/staged review; no destructive history/worktree changes without authorization. | OPEN |
| PERF-01 | [Python performance clock](https://docs.python.org/3.12/library/time.html#time.perf_counter) | Elapsed timings; state cold/warm scope and synchronize asynchronous GPU work. | OPEN |

## Architecture legacy IDs

Architecture §22 retains the following IDs. They remain historical reference leads,
not chosen next experiments. All twelve URLs below returned readable pages (OPEN)
on 19 October 2026; revision, licenses, access and underlying-document rights still
require verification before use. No dataset
is approved automatically for Gold or training by inclusion here.

| ID | Original reference | Purpose and constraint |
| --- | --- | --- |
| R1 | [Qwen3 Embedding 0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Candidate embedding reference; paired evaluation required. |
| R2 | [Qwen3 8B](https://huggingface.co/Qwen/Qwen3-8B) | Historical generator candidate; no release approval. |
| R3 | [Qwen3.5 9B](https://huggingface.co/Qwen/Qwen3.5-9B) | Historical challenger reference; no next-model selection. |
| R4 | [Qwen3 Reranker 0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | Only for demonstrated ranking need. |
| R5 | [Docling repository](https://github.com/docling-project/docling) | Candidate source/runtime inspection; PAR-05 is its documentation. |
| D1 | [DocVQA](https://site.docvqa.org/datasets) | Visual QA; not a replacement for document-RAG Gold. |
| D2 | [DocLayNet](https://huggingface.co/datasets/docling-project/DocLayNet) | Layout evaluation; assess actual revision and rights. |
| D3 | [TAT-QA](https://github.com/NExTplusplus/tat-qa) | Table/text QA; verify underlying report permissions. |
| D4 | [SQuAD 2.0](https://huggingface.co/datasets/rajpurkar/squad_v2) | Answerability smoke; passage QA is not production RAG. |
| D5 | [KazQAD](https://huggingface.co/datasets/issai/kazqad) | Kazakh QA; access and annotation suitability need verification. |
| D6 | [MIRACL](https://huggingface.co/datasets/miracl/miracl) | Retrieval comparator; does not establish PDF/XLSX or Kazakh coverage. |
| D7 | [Zerde QA 50K](https://huggingface.co/datasets/kurumikz/Zerde-QA-50K) | Synthetic QA lead; not reviewed evidence Gold or auto-SFT. |
