# DocLens AI — карта документации v4

19.10.2026. Только навигация и распределение ответственности; требования находятся
у владельцев ниже. Начало работы: [AGENTS.md](AGENTS.md).

## Owners and section routing

| Тема | Единственный нормативный владелец | Разделы |
| --- | --- | --- |
| Модули, данные, lifecycle, security, roadmap | [Architecture / P-ARCH](Doclens_AI-architecture.md) | [Modules](Doclens_AI-architecture.md#ARCH-MODULES), [data](Doclens_AI-architecture.md#ARCH-DATA), [upload](Doclens_AI-architecture.md#ARCH-UPLOAD), [jobs](Doclens_AI-architecture.md#ARCH-JOBS), [index](Doclens_AI-architecture.md#ARCH-INDEX), [security](Doclens_AI-architecture.md#ARCH-SECURITY), [API](Doclens_AI-architecture.md#ARCH-API), [roadmap](Doclens_AI-architecture.md#ARCH-ROADMAP) |
| Цели, coverage, QG-00..QG-09, release acceptance | [Quality Policy](DocLens_AI_Project_Goals_and_Quality_Policy-1.md) | [GOAL](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#GOAL), [COVERAGE](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#COVERAGE), [QUALITY-GATES](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES), [TRUTHFUL-LLM](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#TRUTHFUL-LLM), [EVALUATION](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#EVALUATION), [PRODUCTION-DOD](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#PRODUCTION-DOD) |
| Format methods, locators, parser experiments | [Extraction Strategy](DocLens_AI_Extraction_Strategy.md) | [EX-ARCH](DocLens_AI_Extraction_Strategy.md#EX-ARCH), [EX-PDF](DocLens_AI_Extraction_Strategy.md#EX-PDF), [EX-DOCX](DocLens_AI_Extraction_Strategy.md#EX-DOCX), [EX-XLSX](DocLens_AI_Extraction_Strategy.md#EX-XLSX), [EX-EXPERIMENT](DocLens_AI_Extraction_Strategy.md#EX-EXPERIMENT) |
| EDA/Gold, cleaning/chunks, models, retrieval, context, generation, experiments | [ML Strategy / P-ML](DocLens_AI_ML_Quality_Strategy.md) | [ML-DATA](DocLens_AI_ML_Quality_Strategy.md#ML-DATA), [ML-CHUNK](DocLens_AI_ML_Quality_Strategy.md#ML-CHUNK), [ML-RETRIEVAL](DocLens_AI_ML_Quality_Strategy.md#ML-RETRIEVAL), [ML-EVIDENCE](DocLens_AI_ML_Quality_Strategy.md#ML-EVIDENCE), [ML-GENERATION](DocLens_AI_ML_Quality_Strategy.md#ML-GENERATION), [ML-FINETUNE](DocLens_AI_ML_Quality_Strategy.md#ML-FINETUNE), [ML-EXPERIMENT](DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) |
| Temporary authorized Kaggle execution | [GPU Playbook / P-GPU](DocLens_AI_Kaggle_GPU_Playbook.md) | [GPU-MODE](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-MODE), [GPU-A](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-A), [GPU-B](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-B), [GPU-GATE](DocLens_AI_Kaggle_GPU_Playbook.md#GPU-GATE) |
| Stable technical IDs, official links, intended use | [Engineering Sources](DocLens_AI_Engineering_Sources.md#CATALOG) | Catalog, legacy IDs, external extraction |
| Codex procedure | [AGENTS.md](AGENTS.md) | Scope, verification, Git, report |
| Actual setup/commands/features | [README](README.md) | API, worker, local/evaluation commands |

## Priority, conflicts and historical evidence

Иерархия, P-REPO и правила статусов: [AGENTS](AGENTS.md#sources-and-claims).
[DOCX v3](Doclens_AI-architecture.docx) — historical reference, не второй owner.
[Review and migration](docs/DOCS_REVIEW_AND_MIGRATION.md) сохраняет решения v4,
проверки того snapshot и limitations; исторические отчёты не пересчитаны.

## Skill selection

Skills — процедуры применения owner documents, не параллельные спецификации.

| Работа | Процедура |
| --- | --- |
| Schema/migrations | [doclens-db-migration](.agents/skills/doclens-db-migration/SKILL.md) |
| Upload/jobs/index/delete/reindex | [doclens-ingestion-change](.agents/skills/doclens-ingestion-change/SKILL.md) |
| Parser fidelity/diagnosis | [doclens-extraction-benchmark](.agents/skills/doclens-extraction-benchmark/SKILL.md) |
| Retrieval/context/answers/refusal | [doclens-rag-evaluation](.agents/skills/doclens-rag-evaluation/SKILL.md) |
| Provenance/review/coverage/leakage | [doclens-data-quality](.agents/skills/doclens-data-quality/SKILL.md) |
| Experiment protocol | [doclens-ml-experiment](.agents/skills/doclens-ml-experiment/SKILL.md) |
| Authorized GPU execution | [doclens-kaggle-gpu](.agents/skills/doclens-kaggle-gpu/SKILL.md) |
| Operational/release qualification | [doclens-production-readiness](.agents/skills/doclens-production-readiness/SKILL.md) |
