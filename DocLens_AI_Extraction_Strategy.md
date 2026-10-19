# DocLens AI — стратегия извлечения v4

19.10.2026. Владелец format-specific representation, методов, локаторов и parser
experiments. Приёмка: [QG-01](DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES).
Lifecycle/trust: [архитектура](Doclens_AI-architecture.md).

<a id="EX-ARCH"></a>
## Native-first и представление

Production baseline: `pypdf`, `python-docx`, `openpyxl`; ranges в `pyproject.toml`,
actual versions фиксируются в run. `extraction/parsers.py` и `extraction/models.py`
определяют runtime, не весь TARGET ниже.

Сохранять original text/typed values, source/version/SHA, parser/config identity,
настоящий locator, order, warnings и verified table/header/value relationships.
Не выдумывать missing fields/coordinates. `success/needs_review/failed` — status,
не fidelity. Сохранять signs/numbers/precision/dates/IDs/leading zeros/formulas/units.
Candidate observations отделены до independent verification; VLM не может скрыто
«исправлять» текст, числа или структуру. Library не доказывает hard timeout/sandbox;
это проверяемые architecture TARGET.

<a id="EX-PDF"></a>
## PDF

Сначала native page text с genuine 1-based pages и source spans. Proximity не
доказывает table/grid/order. Проверять columns/rotation/fonts/encoding/images,
пропуски и header/value/unit links по оригиналу. При наблюдаемом дефекте выбирать
минимальный page/region OCR или table/layout candidate; low-text flag не доказывает scan.
Pin engine/model/languages/DPI/selector/routing/fallback/limits; full OCR по умолчанию нет.

Native/OCR merge требует verified mapping/dedupe/order policy; conflicts и degraded
fallback явно needs_review. Locator — страница и реальный region, если доступен;
не синтезировать cell provenance из plain text.

<a id="EX-DOCX"></a>
## DOCX

Baseline: ordered body paragraphs/tables; complete headings/sections/ancillary parts —
TARGET. OOXML extension сохраняет package part, relationship/element identity,
genuine section membership, nested/merged tables, notes/references. Body order и
ancillary parts не превращать в выдуманный global page order. Word page numbers
без verified layout engine запрещены.

Проверять target part/type/bounds/version linkage, repeated note refs/shared headers
с явной dedupe semantics. Missing/ambiguous ref — warning/review.
[Footnote candidate](docs/eda/docx_footnote_candidate_v1.md) не означает production
support всех parts; address validator не заменяет reviewed locator Gold.

<a id="EX-XLSX"></a>
## XLSX

Сохранять workbook/version, sheet identity, cell/range, typed stored value/precision,
formula expression отдельно от cached value; missing cache явно маркировать.
Не выполнять formulas/macros/external links. Display format/date interpretation,
merges/headers/units/table membership — отдельные измерения; stored number не равен
display string. Не угадывать formatted value и не дублировать merged values.
Сохранять row/header/value/unit/period links и sparse anchors.
Cross-sheet joins/charts/recalculation baseline не обещает; sheet names чувствительны.

<a id="EX-EXPERIMENT"></a>
## Сравнения и решения

[ML protocol](DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) и
[extraction skill](.agents/skills/doclens-extraction-benchmark/SKILL.md): paired frozen
bytes, reviewed Extraction Gold, independent controls. Метрики: anchors/order,
cells/spans/relations/locators, formula/cache, eligibility/failures, evidence-in-chunk,
cold/warm time/peak RAM. OCR: reviewed page-level CER/WER по языкам.
Новые comparisons — два paired run в свежих ignored dirs; сверить все non-runtime
fields/fingerprints и сохранить actual timings. Диагноз отделяет omission/traversal/
fragmentation/order/locator mismatch от unknown cause. Extra characters не доказывают fidelity.
Critical baseline loss не компенсируется table gains. Unreviewed dimensions NOT_EVALUATED.

| Frozen конфигурация | Историческое решение, без нового run |
| --- | --- |
| Docling expanded | REJECTED: [report](docs/eda/docling_pdf_expanded_benchmark_v1.md) |
| Vector-grid | REJECTED: [report](docs/eda/pdf_table_candidate_v1.md) |
| pdfplumber table | REJECTED: [report](docs/eda/pdfplumber_table_candidate_v1.md) |
| Expanded selective OCR | INCONCLUSIVE: [report](docs/eda/pdf_selective_ocr_expanded_eval_v1.md) |
| MinerU 4.0 `basic` | Future offline CANDIDATE, NOT_EVALUATED на DocLens; version/API/license проверить до run |

Идеи для изучения: RAGFlow stage/evidence separation, Docling typed provenance,
Marker layout conversion, MinerU selective pipeline. Это не импорт платформ и не
результаты DocLens. [Official sources/caveats](DocLens_AI_Engineering_Sources.md#EXTERNAL-EXTRACTION).
Никакой production replacement без reviewed Gold, paired evidence и отдельного допуска.
