# DocLens AI — инженерные источники v4

19.10.2026. Владелец stable technical IDs, official URLs и intended usage;
требования/выбор технологий находятся у [topic owners](README_SOURCE_MAP.md).
IDs сохраняются навсегда: retire, не reassign. Выбирать 2–4 relevant sources на задачу.

<a id="CATALOG"></a>
## Каталог

`pyproject.toml`: Python >=3.12, большинство dependencies — ranges;
dense pins Torch 2.8.0, Transformers 4.57.6, Hub 0.36.0. PostgreSQL 16/Qdrant 1.15.x —
семейства documented profiles. `/stable/` и `/latest/` не version pins.
До API usage сверить installed/pinned versions и official version-specific docs.
Vendor/model/dataset page не доказывает качество private corpus или release PASS.

Links ниже сохранены из прежнего каталога; их прежние OPEN/REDIRECT/LIMITED пометки
не выдаются за новую проверку. В этой задаче повторно открыты только четыре external
repositories из следующего раздела; reachability не compatibility/license approval.

| ID | Official reference | Применение и ограничение |
| --- | --- | --- |
| CODE-01 | [Python 3.12](https://docs.python.org/3.12/) | Runtime/stdlib; сверить actual Python version. |
| CODE-07 | [Google code review](https://google.github.io/eng-practices/review/reviewer/) | Correctness/scope/maintainability при review. |
| API-01 | [FastAPI](https://fastapi.tiangolo.com/) | Validation/async/dependencies; сверить installed release. |
| DB-01 | [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) | Transactions/async/locking; session не разделять между concurrent tasks. |
| DB-02 | [Alembic](https://alembic.sqlalchemy.org/en/latest/) | Новые совместимые revisions; applied history не переписывать. |
| DB-03 | [PostgreSQL 16](https://www.postgresql.org/docs/16/) | Constraints/locks/DB clock; concurrency проверять на real PostgreSQL. |
| OBJ-01 | [S3 object integrity](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html) | Upload/readback checksum; DB/S3 не одна транзакция. |
| OBJ-02 | [MinIO documentation](https://docs.min.io/) | Deployment/security; redirect AIStor не доказывает Community feature parity. |
| VEC-01 | [Qdrant 1.15 upsert](https://api.qdrant.tech/v-1-15-x/api-reference/points/upsert-points) | Revision-scoped writes; ACK не заменяет candidate verification. |
| PAR-01 | [pypdf extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) | Native PDF limitations; extraction не доказывает fidelity/OCR. |
| PAR-02 | [python-docx](https://python-docx.readthedocs.io/en/latest/) | Body/tables/OOXML; ancillary support проверять отдельно. |
| PAR-03 | [openpyxl](https://openpyxl.readthedocs.io/en/stable/) | Cell/formula/cache/display; не вычислять формулы или absent caches. |
| PAR-05 | [Docling](https://docling-project.github.io/docling/) | Typed extraction candidate; docs не отменяют frozen REJECT. |
| EXP-01 | [PyTorch reproducibility](https://docs.pytorch.org/docs/2.8/notes/randomness.html) | Seeds/determinism; измерять repeatability на declared hardware. |
| EXP-02 | [Hugging Face Transformers](https://huggingface.co/docs/transformers/index) | Loading/tokenization/offline; exact v4.57.6 page ранее не проверена. |
| RET-01 | [multilingual E5 small](https://huggingface.co/intfloat/multilingual-e5-small) | E5 baseline identity/instructions; model card не DocLens quality evidence. |
| RAG-01 | [Original RAG paper](https://arxiv.org/abs/2005.11401) | Research context, не готовый implementation contract. |
| RAG-02 | [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | Untrusted document/context threat model; schema не достаточна. |
| FT-01 | [Hugging Face PEFT](https://huggingface.co/docs/peft/index) | Optional LoRA после justified ML experiment; dependency не принята. |
| GPU-01 | [Kaggle notebooks](https://www.kaggle.com/docs/notebooks) | Runtime/CLI discovery; проверить actual help/quotas. |
| GPU-02 | [PyTorch 2.8](https://docs.pytorch.org/docs/2.8/) | CUDA placement/sync/memory; enumeration не inference. |
| SEC-01 | [OWASP authorization](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | Deny-by-default/per-request authorization; DB authority сохраняется. |
| TST-01 | [pytest](https://docs.pytest.org/en/stable/) | Fixtures/markers; реальные boundaries требуют integration. |
| TST-02 | [pytest parametrization](https://docs.pytest.org/en/stable/how-to/parametrize.html) | Positive/negative/failure matrices. |
| OPS-01 | [Docker Compose](https://docs.docker.com/compose/) | Profiles/lifecycle; startup не migrations/release. |
| OPS-02 | [Git reference](https://git-scm.com/docs) | Diff/status/staged review; без destructive cleanup. |
| PERF-01 | [Python performance clock](https://docs.python.org/3.12/library/time.html#time.perf_counter) | Cold/warm elapsed timing; asynchronous CUDA требует sync. |
| R1 | [Qwen3 Embedding 0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Embedding CANDIDATE, paired evaluation до выбора. |
| R2 | [Qwen3 8B](https://huggingface.co/Qwen/Qwen3-8B) | Historical generator CANDIDATE, не release approval. |
| R3 | [Qwen3.5 9B](https://huggingface.co/Qwen/Qwen3.5-9B) | Historical challenger, не следующий выбранный experiment. |
| R4 | [Qwen3 Reranker 0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | Только при observed ranking need. |
| R5 | [Docling repository](https://github.com/docling-project/docling) | Source/runtime inspection; PAR-05 содержит documentation. |
| D1 | [DocVQA](https://site.docvqa.org/datasets) | Visual QA, не замена document-RAG Gold. |
| D2 | [DocLayNet](https://huggingface.co/datasets/docling-project/DocLayNet) | Layout evaluation; проверить revision/rights. |
| D3 | [TAT-QA](https://github.com/NExTplusplus/tat-qa) | Table/text QA; проверить underlying report rights. |
| D4 | [SQuAD 2.0](https://huggingface.co/datasets/rajpurkar/squad_v2) | Answerability smoke, не production RAG evidence. |
| D5 | [KazQAD](https://huggingface.co/datasets/issai/kazqad) | Kazakh QA; проверить access/annotation suitability. |
| D6 | [MIRACL](https://huggingface.co/datasets/miracl/miracl) | Retrieval comparator; не PDF/XLSX/KK coverage. |
| D7 | [Zerde QA 50K](https://huggingface.co/datasets/kurumikz/Zerde-QA-50K) | Synthetic QA lead, не reviewed Gold/auto-SFT. |

## Architecture legacy IDs

R1..R5 и D1..D7 сохранены в каталоге выше. Это historical reference leads,
не выбор следующего model/dataset. Inclusion не разрешает Gold/training/transfer.
Зафиксировать revision, license/attribution, access и права underlying documents.

<a id="EXTERNAL-EXTRACTION"></a>
## Внешние extraction references

| ID | Official source | Идея для изучения и caveat |
| --- | --- | --- |
| PAR-06 | [RAGFlow](https://github.com/infiniflow/ragflow) | Stage/evidence boundaries; не принимать platform/agent stack целиком |
| PAR-07 | [Marker](https://github.com/datalab-to/marker) | Layout conversion как offline candidate; code/model licenses проверять раздельно |
| PAR-08 | [MinerU](https://github.com/opendatalab/MinerU) | Future MinerU 4.0 `basic` из brief — NOT_EVALUATED на DocLens; точные tag/API/backend/dependencies до run ещё не квалифицированы |
| R5 / PAR-05 | [Docling](https://github.com/docling-project/docling) | Typed representation/provenance; frozen rejected config не реабилитируется новой upstream version |

Четыре repository pages открыты 19.10.2026; Marker old URL перенаправил на datalab-to.
Не зафиксирован конкретный upstream commit для внедрения. До experiment зафиксировать
code/model revisions, license texts, веса/renderer dependencies, compute/transfer
policy; лицензия repository не автоматически лицензия weights, inputs или outputs.
Никаких совместимости, производительности или DocLens benchmark gains здесь не заявлено.
