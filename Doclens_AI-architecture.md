# DocLens AI — архитектура v4

19.10.2026. Нормативный владелец модулей, системных контрактов, lifecycle,
безопасности и roadmap. [Карта владельцев](README_SOURCE_MAP.md).
[DOCX v3](Doclens_AI-architecture.docx) — только история 15–17.10.2026,
со снимком `9b39846`, без действующей нормативной силы.

<a id="ARCH-STATUS"></a>
## Состояние и доказательства

P-REPO: просмотр кода на `c63d72d9bb854dd4ed16a29fcbe1bfb1ff873eb9`.
Runtime-тесты и эксперименты при редактуре не запускались. IMPLEMENTED здесь —
наличие реализации и тестовых контрактов, без нового behavioral PASS.

| Статус | Область и основание |
| --- | --- |
| IMPLEMENTED, code inspection | Authenticated intake, durable workers, canonical chunks, verified cutover, dense search, stateless answers: `src/doclens_ai/services/`, `security/jwt.py`, `models/`; контракты `tests/integration/` |
| OFFLINE BASELINE | Измеренные comparators в исторических `docs/eda/` и `docs/evaluation/` |
| TARGET | READY, deletion/tombstones, полный reindex/rebuild/reconciler, conversations/SSE, comprehensive CI/E2E/restore и release qualification |
| CANDIDATE / REJECTED / NOT_EVALUATED | Экспериментальные статусы методов ведут Extraction/ML Strategy; они не меняют runtime |

Наличие кода не доказывает RU/KK/EN quality или production readiness.
Приёмка принадлежит [Quality Policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md).

<a id="ARCH-MODULES"></a>
## Модули и владельцы данных

Python 3.12+/FastAPI modular monolith: API, ingestion worker и index worker —
разные процессы одной кодовой базы. Тяжёлый parsing/OCR не выполняется в upload route.

| Граница | Ответственность |
| --- | --- |
| `api/`, `security/` | JWT/OIDC, validation и trusted request scope; клиентские claims не заменяют DB membership |
| PostgreSQL: `models/`, `db/`, `services/` | Identities, текущие workspace ACL, версии, metadata, runs/jobs, canonical chunks, IndexRevision и source verification |
| MinIO/S3: `storage/` | Immutable RAW и разрешённые derived artifacts; не источник ACL |
| `extraction/`, `chunking/` | Воспроизводимые внутренние преобразования с source lineage |
| `dense_baseline/`, `vector/` | Embeddings и derived/rebuildable Qdrant; не canonical text/state/ACL authority |
| `llm/`, `services/rag.py` | Model provider и проверка результата; не доменная логика или tools execution |

Новые dependencies/frameworks, brokers/Redis/Celery, microservices, agents,
LangChain/LangGraph, Kubernetes/Terraform, DVC/MLflow требуют измеренной необходимости.
Предпочитать существующие explicit service/error/config/log patterns.

<a id="ARCH-DATA"></a>
## Идентичность и lineage

User определяется trusted issuer+subject, Membership хранит текущие grants.
Document принадлежит workspace. DocumentVersion неизменяем после commit:
`version_number`, `object_storage_key`, `sha256_checksum`, `file_size`,
`content_type`, `original_filename`. UploadSession хранит operation scope/idempotency/state.
ProcessingRun — operation/configuration/stage/status; ProcessingJob — lease/retry.
CanonicalChunk — text/hash, ordinal, stable identity/provenance; workspace/version
выводятся через DB relations. `token_count` может быть NULL.

Цепочка RAW → version → parser/cleaner → block → chunk → embedding → revision →
evidence сохраняет immutable identities и config fingerprints. Reprocess создаёт
новый derived набор; опубликованные chunks не переписываются до cutover.
Config фиксирует source/model bytes/revisions, parser/cleaner/chunker, routing/OCR,
instructions/pooling/normalization, collection/dimension/distance, budgets,
prompt/schema и worker lease/retry. Название модели не заменяет artifact hashes.
Applied migrations не переписывать; schema changes — совместимые новые ревизии.

<a id="ARCH-UPLOAD"></a>
## Upload и immutable RAW

1. Проверить authentication и текущий DB workspace доступ.
2. Проверить filename/type, MIME/signature/Office archive structure, фактический
   размер/SHA-256; ограничить streaming bytes и multipart на ingress.
3. Scope Idempotency-Key: workspace + document + operation + client key.
   Те же validated filename/type/size/SHA возвращают ту же версию; отличие → 409.
   Одинаковый hash сам по себе недостаточен.
4. Server-generated object key; private RAW подтвердить readback/hash либо строгим
   эквивалентным checksum-контрактом. Перед finalization сверить DB/S3 references.
5. Одна DB-транзакция фиксирует DocumentVersion и ProcessingRun/Job.

DB/S3 не распределённая транзакция: DB rollback не удаляет объект.
Orphan cleanup требует проверки DB references и owned scope. SHA не определяет права.

<a id="ARCH-JOBS"></a>
## Jobs и отказы

Логическая цепочка: upload → parsing → validation/safe cleaning → chunks → embeddings
→ indexing → verification. Не подменять ею текущие enums:
ProcessingStage = extraction/cleaning/chunking/embedding/indexing;
run status = queued/processing/retry_wait/failed/completed;
job status = queued/leased/retry_wait/failed/completed.
Текущий worker передаёт extraction → embedding; READY — TARGET.

Claim/reclaim атомарен, с DB clock и locking/SKIP LOCKED либо эквивалентом.
Lease token/expiry и heartbeat ограждают publication/completion/failure writes:
stale worker не может изменить работу нового владельца. Сохранять cancellation,
bounded attempts/backoff, terminal failure и deterministic stage identities.
Внешняя работа не удерживает долгие DB locks. Canonical chunks публикуются целиком
с проверкой lease/config/source. Ошибка документа изолирована от batch.

Crash, corrupt input, parser/embedding/S3/Qdrant/LLM outage и partial writes
не теряют source и не создают ложный success. Fallback явно degraded/needs_review;
его quality не считается эквивалентным baseline без измерений. Hard parser timeout,
OS/egress isolation и полный recovery reconciler — отдельно проверяемые TARGET.

<a id="ARCH-INDEX"></a>
## IndexRevision и cutover

Единственный ACTIVE authority — PostgreSQL `IndexRevision.status=active` плюс
partial UNIQUE `document_id WHERE status='active'`; второй pointer запрещён.
Состояния: candidate → verified → active → superseded, также verified → superseded.
Candidate имеет отдельный revision/lease scope и point IDs.

До активации проверить точные IDs/counts, payload, dimension/finiteness/vector content,
canonical linkage, source freshness и model/config identity. ACK upsert/search sanity
недостаточны. Транзакционный cutover перепроверяет owner/source; при сбое прежний
ACTIVE сохраняется. Partial/stale points остаются unsearchable.

Полный delete/reindex/rebuild lifecycle — TARGET: authorized tombstone исключает
источник немедленно; fences не допускают republish; external cleanup после
reference/grace checks. Rebuild требует canonical chunks и доступных pinned model/
config artifacts. Cutover-код не доказывает восстановление после потери Qdrant.

<a id="ARCH-SECURITY"></a>
## Retrieval, ответы и trust boundaries

JWT/OIDC проверяет подпись/JWKS, issuer/audience/expiry; missing trusted config
закрывает protected routes. PostgreSQL membership авторизует scope.
Client selectors только сужают разрешённый набор. Backend строит Qdrant filters
по workspace/ACTIVE/model space; hit сверяется с DB canonical chunk/source/version/run.

До model context и после inference перед final delivery перепроверяется весь packed
evidence, включая нецитированные chunks. Unauthorized/stale/deleted evidence не
выпускается. Между последней DB-проверкой и network delivery остаётся race;
network-atomic revocation не обещается. Tombstone/delete race — целевой контракт,
а не утверждение о реализованном deletion lifecycle.

Documents/retrieval/model output — untrusted data; их инструкции не исполняются.
Никаких произвольных model tools/web или Office formulas/macros/external links.
Проверять schema, refs/versions/quotes/offsets и proposed state changes;
semantic support оценивается отдельно по Quality Policy. При недостатке evidence — отказ.
Secrets, PII/private text, corpus/Gold и weights не попадают в Git/logs.
Sensitive external inference/transfer требует explicit authorization.

<a id="ARCH-API"></a>
## API и эксплуатация

Точный wire contract: `api/routes/`, schemas и [README](README.md).
Есть health, create/get document, upload version, job status, search, stateless answers.
Readiness сейчас DB-only; готовность всех enabled dependencies — TARGET.
Conversations/SSE/DELETE — TARGET; будущий SSE выпускает system events и verified
final, не неподтверждённые answer tokens. General Search request_id — TARGET;
у Answers собственный контракт. Версионировать response/error taxonomy, sanitized
errors и request correlation; object keys/credentials не публиковать.

Private buckets, least privilege, retention/deletion policy, secure backups и
раздельные dev/staging/prod credentials обязательны. Quotas/rate limits, audit
delete/permission events и sanitize policy — TARGET отдельной qualification.
Ограничивать ingress/archive expansion, pages/pixels/time, CPU/RAM/VRAM,
inference/concurrency/storage; parser egress по умолчанию запрещён целевой policy.
Budgets/SLO требуют утверждения. Observability: queue/lease age, attempts/retries,
stage/total latency, source→eligible→indexed counts, resource peaks/config/run IDs,
без приватного текста. Backup RAW/DB, restore, rebuild, rollback и failure drills
обязательны по [приёмке](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#PRODUCTION-DOD),
но не объявлены выполненными.

<a id="ARCH-ROADMAP"></a>
## Roadmap по незакрытым зависимостям

| Шаг | Результат перед переходом |
| --- | --- |
| 1. Gold/families/languages | Provenance/EDA, independent review, family-safe RU/KK/EN coverage |
| 2. Extraction | Critical fidelity/locator failures измерены; baseline сохраняется до допуска кандидата |
| 3. Cleaning/chunking | Facts/offsets и полные header/row/value/unit/period relationships |
| 4. Embedding/index/retrieval | Frozen comparators, reproducibility, integrity/ACL/freshness |
| 5. Context/answers | Evidence survival и independent semantic/refusal evaluation |
| 6. Operational release | Lifecycle, fault/security/load/CI/E2E, restore/rebuild/rollback |

Существующий durable backend не закрывает upstream gaps. Следующий шаг не
автоматический; gate definitions у Quality Policy, методы у Extraction/ML Strategy.
Fine-tuning не обязательный ранний этап.
