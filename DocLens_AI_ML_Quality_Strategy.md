# DocLens AI — ML/RAG стратегия v4

19.10.2026. Владелец EDA/Gold, cleaning/chunking methods, моделей, retrieval,
context/generation evaluation и experiment methodology. Acceptance — только
[Quality Policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md);
lineage/security — [архитектура](Doclens_AI-architecture.md).

<a id="ML-DATA"></a>
## EDA и reviewed Gold

До оптимизации фиксировать rights/license/transfer/annotation scope, sensitivity,
immutable RAW SHA/size/source version. EDA: grain, format/language/size/structure,
missing/corrupt/unsupported, exact/near duplicates, translations, versions/families.
Не удалять meaningful versions и не выводить права из SHA. Private corpus/Gold
локальны без отдельно разрешённого transfer scope.

Extraction, Retrieval и Answer Gold раздельны; reviewer/revision/source anchors,
adjudication/unresolved labels явны. Machine draft не reviewed Gold.
Train/dev/sealed-test разделяются по family, включая translations/versions/near-duplicates;
фиксировать split revision/seed/review. Нет sealed-test tuning или переименования
exposed test в blind. RU/KK/EN и negative coverage — по Quality Policy;
multilingual model не доказывает покрытие данных.

<a id="ML-CHUNK"></a>
## Safe cleaning и chunks

Transforms версионированы, сохраняют оригинал и verified source-offset map.
Unicode/whitespace normalization допустима без изменения facts; нельзя молча менять
decimal separators/currencies/dates/leading zeros/negation/units/formulas либо удалять
«шумные» factual строки. Неоднозначность → review.

Comparator: structure-aware character baseline, `chunking/models.py`, size 1200,
overlap 120; это characters, не tokens и не optimum. Fixed/token/table/row-aware
варианты — CANDIDATE. PDF сохраняет verified page/block/table order; DOCX — body/table
order с честной границей headings/sections; XLSX — ranges/rows с headers.
Полная header/row/value/unit/period связь важнее длины. Нельзя скрыто обрывать факт;
повтор headers сохраняет provenance.

На fixed extraction/Gold измерять complete evidence-in-chunk, broken relations,
duplicates, length/token distribution, latency/index size. Отделять extraction loss
от chunk loss. Stable identities/config lineage — контракт архитектуры.

<a id="ML-RETRIEVAL"></a>
## Embeddings и ranking

Baseline: `intfloat/multilingual-e5-small`, revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384d, cosine/L2 normalization,
`query:`/`passage:` instructions. Loaded artifacts/config сверять с
`src/doclens_ai/dense_baseline/embeddings.py`; model name недостаточен.
Tokenizer/truncation/pooling/instructions совпадают с indexed space.
Cache key: content hash + exact model/config/instructions/normalization,
с безопасным scope/invalidation; spaces не смешиваются.

BM25 — OFFLINE BASELINE/comparator, не production hybrid. На совместимом scope
сравнивать frozen BM25/E5; historical EN results не обобщать на RU/KK.
Hit/Recall@5/10, MRR, nDCG@10 требуют ranking horizon/ties/attempted/eligible counts.
Gold выбирает scoring/splits, не filters/candidates/context. Bounded production
top-k не равен old full-pool protocol. Hybrid/fusion, reranker/alternative embeddings
требуют observed error/complementarity, paired gains и acceptable latency/resources.

<a id="ML-EVIDENCE"></a>
## Context packing

Трассировать discovery → facts внутри retrieved chunks → selection/dedupe/truncation
→ actual serialized prompt. Chunk ID hit не доказывает complete support.
Измерять evidence-in-context/retrieved-to-packed survival, anchors/headers/units,
token/character utilization и latency. Packing A/B держит candidate pool и generator
постоянными. Score-order/prefix runtime — baseline, не optimum. Character cap не
заменяет measured tokenizer window/output reserve. Gold не подмешивается в prompt.

<a id="ML-GENERATION"></a>
## Generation, citations и refusal

[Политика достоверности](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#TRUTHFUL-LLM)
задаёт допустимый ответ. Раздельно оценивать runtime/HTTP, JSON/schema, source identity,
quotes/offsets/coverage, factual correctness, groundedness, semantic citation
precision/recall, unsupported claims, refusal precision/recall/F1 и unsafe acceptance.
Нужен independent reviewed Answer Gold; AI-assisted diagnostics — другой evidence class.
Negative probes: wrong entity/negation/conflicts/no-evidence/injection/multilingual/numeric.
Document-scoped negative не доказывает workspace unanswerability.

Все packed sources повторно авторизуются после inference по архитектуре.
Исторические rejected generators остаются отклонёнными в измеренном scope:
[real baseline](docs/evaluation/rag_real_baseline_v1.md),
[model comparison](docs/evaluation/rag_model_compare_dev_v1.md),
[schema candidate](docs/evaluation/rag_schema_dev_v1.md).
[Quote binder](docs/evaluation/rag_quote_binding_dev_v1.md) — offline structural
CANDIDATE, semantic support NOT_EVALUATED; не подключать автоматически и не ослаблять
validator. Open-weight generators/serving alternatives не выбраны roadmap.

<a id="ML-FINETUNE"></a>
## Необязательное обучение

LoRA/QLoRA — отдельно разрешённый эксперимент после достаточного lawful reviewed
SFT Gold, family isolation и generation-specific failure при правильном retrieval/context.
Нужны frozen base/config, comparative untuned held-out quality/safety/resource evidence.
Не обучать запоминанию private documents. Public QA не становится автоматически
RAG Gold/SFT. Обязательного раннего training stage нет.

<a id="ML-EXPERIMENT"></a>
## Общий протокол

До run зарегистрировать hypothesis/changed variable, baseline/candidate, immutable
manifest/Gold/family split, metrics/approved thresholds/guardrails, stopping rules,
resource budgets. Зафиксировать Git SHA, data/code/model hashes/revisions,
parser/cleaner/chunker/retrieval/packing/prompt/schema configs, dependencies/seeds,
hardware/concurrency. Freeze другие stages либо раскрыть unavoidable differences.

Paired runs на тех же inputs; воспроизвести comparisons/deterministic fields.
Сохранять failures/needs_review/excluded с причинами в attempted denominator;
conditional eligible quality отдельно. Unknown не zero. Independent scoring по
document/split/language/format/difficulty, sample size/uncertainty обязательны;
small purposive samples/zero observed errors не доказывают safety.
Latency P50/P95 (P99 при необходимости), cold/steady scope, RAM/VRAM peak units,
sampling/process tree, timeouts/missing observations показывают стоимость.

Execution PASS/FIX/BLOCKED; quality PASS/FAIL/NOT_EVALUATED по policy.
Experiment PROMOTE — продвижение только внутри registered scope;
REJECT — failed guardrail/critical regression; INCONCLUSIVE — insufficient evidence.
Production authorization отдельно с release gates/rollback. Следующий experiment
автоматически не начинать. GPU mechanics — [playbook](DocLens_AI_Kaggle_GPU_Playbook.md).
