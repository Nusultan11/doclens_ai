# DocLens AI — цели и политика качества v4

19.10.2026. Единственный владелец целей, покрытия, QG-00..QG-09 и release acceptance.
Системные контракты: [архитектура](Doclens_AI-architecture.md). Это текущая редакция
по заданию, не восстановленный оригинал и не подтверждение исторических thresholds.

<a id="GOAL"></a>
## Цель

Multi-tenant PDF/DOCX/XLSX intelligence: надёжный ingestion, точное извлечение,
авторизованный поиск и ответы с проверяемыми настоящими источниками.
Приоритет — факты, tenant isolation и воспроизводимость, затем число возможностей.

<a id="COVERAGE"></a>
## Обязательное покрытие

| Срез | Проверяемые случаи |
| --- | --- |
| PDF | Native/scanned/mixed, rotation, columns, tables, сложные fonts/layout |
| DOCX | Body/sections, nested/merged tables, notes, headers/footers, OOXML references |
| XLSX | Typed values/precision, formula/cache/display, merges, sheet/cell/table relationships |
| Вопросы/языки | RU/KK/EN, mixed/cross-lingual, numbers/IDs, multi-hop, conflicting/no-evidence |
| Ошибки/атаки | Corrupt/empty/protected/oversized/unsupported, injection, cross-tenant, revoked/stale/deleted |

Показывать attempted/eligible/failed/needs_review по format/language/family/difficulty.
Отсутствующий срез — NOT_EVALUATED. Покрытие не означает поддержку parser.

<a id="QUALITY-GATES"></a>
## Gates и решения

Gate record: scope/revisions, независимость review, evidence, числители/знаменатели,
срезы, approved criteria, verdict. PASS — все применимые проверки и заранее
утверждённые критерии пройдены; FAIL — critical нарушение или провал approved criterion;
NOT_EVALUATED — существенные measurements/labels/thresholds отсутствуют.
Известный critical FAIL не превращается в NOT_EVALUATED.

Все numerical thresholds качества/покрытия/ресурсов — **TBD**, если нет подтверждённого
утверждения и независимого evidence. Утвердить до release evaluation, не подгонять
после результата. Critical failure не компенсируется средним score. Здесь gate PASS нет.

| Gate | Необходимое evidence и метрики | Critical failure |
| --- | --- | --- |
| QG-00 RAW provenance, EDA и Gold | Rights/sensitivity, immutable SHA/size/version manifest, EDA, reviewed labels/family-safe splits; integrity/review/coverage/missingness/overlap | Unauthorized data, unmatched bytes, fabricated review, leakage, hidden exclusions |
| QG-01 Extraction fidelity/locators | Paired originals/Extraction Gold/controls; anchors, order, cells/spans/relations, genuine locators, formula/cache, eligibility/failures/time/RAM | Critical baseline evidence loss, fabricated provenance, unsafe execution |
| QG-02 Safe cleaning | Versioned before/after fixtures и source-offset map; signs/numbers/dates/IDs/negation/units/formulas/links | Silent factual correction или unverifiable remapping |
| QG-03 Evidence-preserving chunks | Fixed extraction/Gold; complete evidence-in-chunk, broken rows/header-value links, duplicates/lengths/index size/latency | Critical evidence loss или fabricated relationships |
| QG-04 Reproducible embeddings | Loaded artifact hashes, config/instructions/tokenizer/dimension/pooling/normalization, repeated runs; counts/finiteness/truncation/time/RAM/VRAM | Model substitution, mixed spaces, invalid vectors/provenance |
| QG-05 Index integrity/activation | Exact candidate IDs/counts/payload/vectors/canonical linkage, real DB constraints/concurrency/fault/fencing; incomplete/stale counts | Partial activation, second ACTIVE authority, stale-owner publication |
| QG-06 Authorized current retrieval | Trusted filters, DB source/ACL/ACTIVE checks; tenant/revocation/version/delete tests, Hit/Recall@5/10, MRR, nDCG@10, latency | Cross-tenant/unauthorized/stale/deleted release |
| QG-07 Context survival | Actual serialized prompt и traced Gold; complete support survival, truncation/header/unit loss, tokens/chars/latency | Critical evidence loss или unauthorized transfer |
| QG-08 Grounded answers/refusal | Independently reviewed Answer Gold/semantic judgments; correctness/groundedness, citation precision/recall, unsupported claims, refusal precision/recall/F1, unsafe acceptance/failures/time | Unsafe accepted claims, invented refs, unauthorized delivery |
| QG-09 Independent E2E/security/operations | Frozen independent evaluation, real services/models, startup/migrations/CI/fault/load/recovery/rollback; factual/safety outcomes, failures, P50/P95/P99, peak resources | Data loss/leakage, unsafe output, failed required recovery, rejected configuration release |

<a id="TRUTHFUL-LLM"></a>
## Достоверный ответ и отказ

Ответ допустим только при поддержке авторизованным актуальным evidence.
При недостаточной, недоступной либо неразрешённо противоречивой поддержке — отказ.
JSON/schema validity, exact quotes и citation coverage не доказывают entailment.
Invalid output — ошибка контракта, не правильный отказ. Проверка IDs/версий/quotes
и independent semantic support необходимы раздельно.
Методы: [ML generation](DocLens_AI_ML_Quality_Strategy.md#ML-GENERATION);
trust/authorization: [архитектура](Doclens_AI-architecture.md#ARCH-SECURITY).

<a id="EVALUATION"></a>
## Evidence и решения

[ML protocol](DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) определяет сравнения.
Failed/needs_review остаются в attempted population, conditional eligible quality
показывается отдельно. Execution PASS/FIX/BLOCKED, quality PASS/FAIL/NOT_EVALUATED,
experiment PROMOTE/REJECT/INCONCLUSIVE и production authorization — разные решения.
Historical reports не квалифицируют current HEAD. Independent review не заменяется
AI-assisted diagnostics или synthetic smoke.

<a id="PRODUCTION-DOD"></a>
## Приёмка выпуска

Нужны все применимые gates с approved criteria и independent evidence:
реальные JWT/JWKS fail-closed/DB ACL, immutable intake, durable/fenced workers,
canonical/index publication, semantic citations/refusals и adversarial E2E.
Проверить delete/tombstone/reindex/rebuild, reference-checked orphan cleanup,
backup **и restore**, crash/cancellation/dependency outages, clean startup/migrations,
repeatable CI, load/resource limits, private storage/networks/secrets и sanitized
observability. Утвердить workload SLO и deploy/rollback/recovery commands.
Отсутствующий lifecycle оставляет gate незакрытым. Production release требует
отдельного решения; эта редакция его не предоставляет.
