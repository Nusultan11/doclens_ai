# ML-27 — independent PDF table Gold review packet v1

19.10.2026. **Execution PASS: локальный packet подготовлен.** Независимый human
review ещё не выполнен; evaluation readiness NOT_ESTABLISHED, QG-00/QG-01
NOT_EVALUATED, production_authorized=false. Это подготовка проверки, не parser
benchmark, новая Gold-разметка или продолжение ML-26 normalization experiment.

## Scope и источники

Исходный `main` HEAD `79dc712052eadd1baf959ad225bb156b312a46b3`, clean.
Только новый tool в `tools/extraction_quality/`, focused synthetic tests и этот
sanitized report. Production/candidate code, frozen settings, RAW/Gold и прежние
reports не менялись. Ни parser text extraction, table detection/scoring, model
inference, rendering private страниц, GPU, external transfer или services не запускались.
Pypdf использован только для page count/MediaBox/CropBox/rotation оригиналов.

Требования и основания: [QG-00/01](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES),
[ML-DATA](../../DocLens_AI_ML_Quality_Strategy.md#ML-DATA), existing strict
`fidelity_gold.py`, [coverage audit](extraction_scenario_coverage_v1.md),
[ML-25](pdf_table_geometry_diagnosis_v1.md) и
[ML-26](pdf_filled_ruling_normalization_v1.md). ML-25 выявил недостаток независимых
logical grid/locator evidence; synthetic ML-26 не закрывает этот пробел на private PDFs.

## Frozen intake и полная selected population

Проверены все **90 RAW SHA/size/format identities**, strict **19-record Gold**,
manifest rights declarations и byte hashes до/после подготовки. Corpus extras,
duplicates, changed/missing sources, links, wrong populations, missing rights или
Gold linkage приводят к отказу. CLI по умолчанию принимает только frozen hashes
и population 90/19/5. Synthetic opt-in существует только в тестовом library call.
License metadata подтверждает прежнюю provenance declaration, не новый legal review.

Выбраны **все пять** PDF records с `table_cells` или `table_relationships`;
нет отбора по результатам parser или успешности прежнего candidate.
Остальные 25 PDF не объявляются table-free. Каждая выбранная source copy побайтово
проверена и названа opaque ID; Gold файл и annotations не редактируются.

| Opaque ID | Все source pages | Anchors | Cell/span assertions | Same row | Same column | Order pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| c1-0033 | 1 | 9 | 8 | 4 | 4 | 3 |
| c1-0040 | 1 | 8 | 4 | 4 | 0 | 3 |
| c1-0045 | 7 | 6 | 4 | 1 | 1 | 2 |
| c1-0048 | 17 | 11 | 3 | 1 | 0 | 6 |
| c1-0049 | 8 | 12 | 5 | 3 | 2 | 6 |
| **Total: 5/5 prepared, 0 excluded** | **34** | **46** | **24** | **13** | **7** | **20** |

Legacy page/table grouping даёт **19 source scopes**: пять с asserted table index
и 14 context/page scopes. Это группировка существующих утверждений, не независимо
обнаруженные 19 visual regions. Отдельные cells/spans не считаются уникальными
physical cells без original review. Все 24 supplied spans равны 1x1; это не
доказательство отсутствия merged cells. Исторический reviewer_count=1 у всех пяти
records — прежняя attestation, без идентичности/independence нового reviewer.

## Содержимое packet и независимая adjudication

Готовый local-only packet находится под ignored experiment directory:
`evaluation-output/pdf-table-gold-review-v1-20261019/packet-1/`.
Вторая независимая генерация в `packet-2/` побайтово совпала со всеми 25 файлами.
Каждый packet содержит:

- Пять неизменённых source PDF copies в `sources/`, именованных opaque IDs.
- По документу `independent.json`: все страницы и пустые inventory/table/cell/
  relationship templates. Нет Gold text, asserted grid positions или parser outputs.
- Отдельный `legacy-assertions.json`: normalized faithful copy frozen record,
  исходные locators/text/occurrences/spans/order/relationships и license provenance;
  page/table scopes явно legacy, independent bbox отсутствует.
- `adjudication.json`: **110 unresolved assertion decisions** (46 anchors + 24
  cell/spans + 20 relationships + 20 order pairs) и **19 unresolved region mappings**.
- `inputs.json`, sanitized `summary.json`, local workflow `REVIEW.md`, 23-entry
  artifact hash manifest и final `COMPLETE.json` с fingerprint.

Workflow: осмотреть все original pages, заполнить independent draft до открытия
legacy assertions, зафиксировать draft fingerprint, затем сравнить и adjudicate.
Доступ к файлам не обеспечивает технического blinding: reviewer должен явно
заявить original-annotator independence, prior exposure и просмотр parser/Gold outputs.
Поле exposure никогда не предзаполнено как false.

Human fields: reviewer/adjudicator IDs/dates, viewer/version/render settings,
page/coordinate basis/visual bbox, literal cell text, row/column/span, header roles,
value/unit/period links, relationship visual basis, ambiguities/disagreements,
missing/extra assertions, rationale и proposed corrections. Decisions допускают
confirm/reject/revise/unresolved/not_applicable; изначально всё unresolved/null.
Legacy table_index не преобразуется в physical table identity. Предлагаемая
коррекция не изменяет frozen Gold; нужна отдельная reviewed revision.

## Readiness blockers

**Independent reviews completed: 0/5; independently verified assertions: 0/110.**
Полнота packet — не полнота Gold и не fidelity PASS.

| Blocker | Что отсутствует |
| --- | --- |
| Independent review | Идентифицированный независимый reviewer, attestation и signed draft |
| Visual mappings | Проверенные source region/table/cell bboxes и locator mapping по оригиналу |
| Cells/spans/relations | Подтверждение/исправление всех 24 spans и 20 relationships; ambiguous/merged cases |
| Semantic associations | Независимые header/value/unit/period роли, не выведенные из proximity |
| Family/language/split | Family/version/translation adjudication, RU/KK coverage и независимый test scope |
| Review provenance | Evidence revisions, dates, disagreements/adjudication и prior-exposure declarations |

Эти пробелы ожидаемы в unfilled review packet; они блокируют последующее quality
qualification, а не успешную подготовку packet. Нового quality/promotion решения нет.

## Verification и воспроизводимость

**82 passed in 9.77s**, без failures/skips: 20 новых packet tests + 62 existing
coverage/Gold tests. Проверены deterministic bundle bytes, manifest integrity,
literal legacy preservation, no automatic review, sanitized aggregate, missing/
changed/extra inputs, wrong population/page, rights, ignored/fresh output,
input drift, timeout/write failure без COMPLETE marker, linked-path guard,
synthetic opt-in и fixed content-free CLI failures. Extraction/scorer entrypoints
в отдельном тесте запрещены monkeypatch; generation всё равно проходит.

Ruff check: All checks passed. Format --check: 2 files already formatted.
Два actual packet runs прошли pre/post frozen integrity; каждый 25-file bundle
имеет 23 hash-listed artifacts плюс artifact manifest/COMPLETE marker.
Runtime: существующий Python 3.12, pydantic 2.14.0, pypdf 6.20.0; dependencies не добавлены.
Code/Gold-validator hashes, packages и starting HEAD сохранены в packet provenance.

| Frozen identity / result | SHA-256 / fingerprint |
| --- | --- |
| Corpus manifest | `c3a91af4bf789400f23821a30c6468040334bdd65135460b96dc21bb64d335c0` |
| Gold 19 bytes | `f372f54d65916b57994ee62ce1fc00fdc536bcdd459b384c6d6e11e9f114bfaf` |
| Selected input identity | `bc90863aca943c1dafb6bb181c550c80c61746fe136b70616aa533c36f50c562` |
| Both packet fingerprints | `bc5e1911a9902bbe1cfe51b5663744b61e9c1733cf3b046c55a35d1db979ce82` |
| Both sanitized summaries | `8fafab2d82586613f188caeb4678777d0ea8915b2f6eeb3b54b6334a44c4765a` |
| New tool | `ebcb40a62424c7488b58a5e3e5d81a31d027dc1ec09bd7233e448a24d4027c9f` |
| New tests | `99300b53602bdbcb49b59b46ea69111bdf75c6f25ebdc4c69a0cfb8e3930c1eb` |

Ранние attempts раскрыты: первый pytest launch дал 17 setup errors из-за
отсутствующего parent basetemp; создан только ignored parent, затем 17 tests прошли.
Ruff выявил три длинные строки workflow, они укорочены. Расширенная suite дала
81 passed/1 skipped: OS не разрешила synthetic symlink. Проверка linked-path guard
заменена детерминированным filesystem-flag mock; окончательная suite 82/82 PASS.
Это не утверждение о выполнении native symlink creation на данной ОС.

Actual PowerShell commands from repository root:

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
.venv/Scripts/python.exe -B -m pytest -q --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/pdf-table-gold-review-v1-20261019/test-4 tests/unit/test_pdf_table_review_packet.py tests/unit/test_extraction_coverage_audit.py tests/unit/test_extraction_fidelity.py
.venv/Scripts/ruff.exe check tools/extraction_quality/pdf_table_review_packet.py tests/unit/test_pdf_table_review_packet.py
.venv/Scripts/ruff.exe format --check tools/extraction_quality/pdf_table_review_packet.py tests/unit/test_pdf_table_review_packet.py
.venv/Scripts/python.exe -B tools/extraction_quality/pdf_table_review_packet.py --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output evaluation-output/pdf-table-gold-review-v1-20261019/packet-1
.venv/Scripts/python.exe -B tools/extraction_quality/pdf_table_review_packet.py --manifest docs/eda/corpus_v1_manifest.csv --corpus local-corpus --gold local-evaluation/extraction_fidelity_v1_expanded_approved.jsonl --output evaluation-output/pdf-table-gold-review-v1-20261019/packet-2
.venv/Scripts/python.exe -B evaluation-output/pdf-table-gold-review-v1-20261019/verify.py
.venv/Scripts/python.exe -B evaluation-output/pdf-table-gold-review-v1-20261019/privacy.py
git diff --check
git diff --cached --check
```

Existing packet directories intentionally cannot be overwritten. Missing required
inputs fail closed with sanitized CLI diagnostics; unsuccessful writes/builds lack
COMPLETE. Bounds: existing 50 MiB/source intake, <=90 sources, <=20 MiB Gold,
<=1 MiB manifest, <=100 pages/selected PDF, cooperative 60s preparation and bounded
JSON publication. Metadata parsing/allocations precede some checks; no hostile-PDF
OS sandbox or independent visual correctness guarantee is claimed.

## Privacy и Git scope

Source copies, assertion text, original filenames/provenance, review worksheets и
private packet JSON остаются только в Git-ignored local storage. stdout/summary
используют whitelist opaque IDs/counters/fixed states. Не передавать пакет наружу;
не добавлять заполненные worksheets или source PDFs в Git. Sanitized report
содержит только IDs, coverage counts, hashes, methods/commands и blockers.
Ни private values/quotes, source filenames, абсолютные private paths или secrets
в публикуемые файлы не включаются. Scoring/model/service E2E не требуются и не запускались.
Commit scope: только новый tool, synthetic tests и этот report; следующий шаг не начат.

Final local verifiers: PASS — два byte-identical 25-file bundles, все 90 originals/
19 Gold identities неизменны, 5/5 selected copies совпадают с RAW, 110 assertion
decisions и 19 mappings unresolved. Privacy scan по полным существующим Gold
anchor strings длиной >=8 и всем original source filenames: **0 matches** в трёх
публикуемых файлах. Secret/absolute-private-path patterns: 0 matches. Все packet
файлы проверены через `git check-ignore`; report links/anchors и UTF-8/LF валидны.
Это ограниченный pattern/content scan, не универсальный DLP detector.
Новые файлы не содержат real Gold labels; fixtures полностью synthetic.
