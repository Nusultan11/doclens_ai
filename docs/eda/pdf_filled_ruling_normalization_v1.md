# ML-26 — source-bound filled-ruling normalization v1

## Preregistration — before synthetic scoring

2026-10-19. Starting HEAD `5e99449efa076bbf2a2f964e1941d120e818717e`, clean.
Sources: [ML-25](pdf_table_geometry_diagnosis_v1.md), its diagnostic/public fixture
code, [Extraction](../../DocLens_AI_Extraction_Strategy.md#EX-EXPERIMENT),
[ML protocol](../../DocLens_AI_ML_Quality_Strategy.md#ML-EXPERIMENT) and
[QG-01](../../DocLens_AI_Project_Goals_and_Quality_Policy-1.md#QUALITY-GATES).
Only three requested new files; no private inputs/scoring, models/GPU/dependencies,
production routing or changes to ML-23/24 code/settings/Gold.

**H1:** for independently authored complete rectangular grids made exclusively of
explicitly filled, black, thin axis-aligned rectangular rulings, replacing their
outline representation with source-contained centre-lines lets the unchanged
pdfplumber detector recover logical cells without changing literal text.

Frozen rules (not detector tolerance tuning): thickness >0 and <=2 pt, long side
>=3 pt and aspect ratio >=10; pure fill, no stroke, direct rectangle paths only.
No clipping, transforms, Forms/images, transparency or unknown paint operators;
the restricted direct-stream interpreter must reconcile each original rectangle
to pdfplumber coordinates. Derived lines carry source SHA/page/rectangle ordinal,
operator/paint identities, original bbox and separately labelled derived coordinates.
Centres and intersections must stay inside the originating bars; no extension,
snapping, gap bridge, merge repair or inferred borders. Non-bar painted objects
or mixed fill/stroke geometry force needs_review. Stroked controls are unchanged.

Require one complete >=2x2 Cartesian table with exact boundary support and every
source character contained in exactly one cell and no character intersecting a bar.
Reject merged/gapped/single-column/disconnected/borderless/crossing-text/ambiguous
shapes; do not emit accepted cells on rejection. Original objects/chars remain in
the diagnostic result. Centre-lines/cells are derived representation, never original
PDF paths or reviewed semantic table roles.

Fixtures: all 12 public ML-25 variants reused unchanged, plus independently authored
filled-rule signed/decimal/leading-zero/unit literals, filled merged/gapped and
crossing variants, thick/square/overlapping bars, fill+stroke and unsupported paint.
Expected boxes/literals come from fixture construction, never candidate outputs.

Success: filled ML-25 case native 25 → exactly 4 expected derived cells, one-to-one
bar provenance and exact character/literal preservation; stroked/cell-rectangle/
continuous/duplicate controls unchanged; every negative needs_review with zero
accepted cells. No critical loss/unsafe acceptance. Two fresh process executions
must match input/config/runtime/code hashes and all non-resource outputs.
PROMOTE only within this synthetic representation hypothesis if all pass;
REJECT on measured critical violation; INCONCLUSIVE if evidence incomplete.
Private fidelity/QG-01 and production authorization remain NOT_EVALUATED/false.

Bounds: serial CPU; existing isolated ML-24 Python/pdfplumber runtime only.
Per document <=1 MiB, one page, <=256 painted objects, <=256 edges, <=4096 chars,
<=1024 detector cells, <=5000 operations and <=1 MiB decoded content; 5 seconds
cooperative processing. Parent hard wall 20 seconds, sampled tree RSS <=512 MiB,
output <=8 MiB, sample 0.02 seconds. No automatic rerun/tuning on failed fixtures.
Stable capture name while monitored; publish only valid complete output after zero
exit/cleanup. Failed/timed-out/oversized/malformed output never becomes result.json.
Parsed object allocation precedes some logical checks; no hostile-input OS sandbox
or continuously measured memory peak is claimed.

## Результат и граница вывода

**Execution PASS; synthetic quality PASS; experiment PROMOTE только для H1 на
этих public fixtures.** Private-source quality/QG-01 NOT_EVALUATED;
production_authorized=false. Production pypdf и frozen ML-23/24 не изменены.

Два независимых worker process дали одинаковые 21 результата: 6 положительных/
контрольных accepted_synthetic и 15 needs_review. Это 21 уникальный fixture,
не 42 независимых документа. Все character indices положительных fixtures
сохранены ровно один раз; signed numbers, decimals, leading zeros и units
совпали буквально с oracle генератора. Numeric fixture дополнительно прочитан
независимым PDFium: все четыре исходных литерала найдены. Не выполнялось private
corpus scoring, чтение Gold для оценки или перенос private geometry/text в fixtures.

| Public fixture | Native regions → accepted cells | Итог/причина |
| --- | --- | --- |
| stroke / cell_rectangles / continuous_split / duplicate_edges | 4 → 4 каждый | Контроль без изменения original edges |
| filled_rules / numeric_filled | 25 → 4 каждый | Шесть исходных bars → шесть derived lines; все четыре data cells/литерала точны |
| gap | 2 → 0 | insufficient_grid |
| merged | 3 → 0 | merged_or_incomplete_grid |
| single_column | 3 → 0 | insufficient_grid, прежняя subset policy не ослаблена |
| borderless / unpainted_rectangles | 0 → 0 каждый | not_one_complete_table |
| separate_boxes | 2 → 0 | not_one_complete_table |
| text_crossing | 4 → 0 | ambiguous_text_association |
| filled_merged | 19 → 0 | unsupported_joint |
| filled_gap | 21 → 0 | incomplete_ruling_grid |
| filled_crossing | 25 → 0 | text_crosses_painted_bar |
| thick_shape / square_shape | 26 / 25 → 0 | ambiguous_painted_shape |
| parallel_overlap | 35 → 0 | overlapping_parallel_bars |
| fill_stroke / unsupported_state | 25 → 0 каждый | unsupported_operator |

ML-25 fixture generator переиспользован без изменений для 12 fixtures; tests
подтверждают byte identity с независимым вызовом прежнего генератора. Девять
дополнительных случаев определены literal PDF operators в новом test module.
Ожидаемые boxes/text заданы в fixture oracle до чтения candidate results.
Объекты исходного PDF не переписываются; SHA проверяется до/после.

## Representation и provenance

`original` хранит rect ordinals/bounds/paint flags, edges, character indices/text/
boxes и native detector regions. `origins` связывает каждый rect с PDF `re` и
paint operation ordinal в ограниченном direct content stream. Идентичность —
source SHA + page + object ordinal, не выдуманный PDF indirect-object ID.
`representation_edges` отдельно маркирует derived centre-line/source_object_id;
stroked controls сохраняют source_edge_index и derived=false.

Для известной filled fixture derived x = 50.5/200.5/350.5,
top = 99.5/149.5/199.5 pt. Четыре логические boxes — декартовы интервалы между
ними. Это **derived coordinates внутри исходной краски**, не существовавшие
в PDF strokes, не white-interior bboxes и не human-reviewed source locators.
Ни один segment не продлён за исходный bar. Проверены source-supported exact
intersections и четыре boundary edge ссылки на каждую ячейку.

Детектор — тот же `TableFinder` с копией ML-24 SETTINGS; меняется только входной
edge view. Для validation используется неизменённая frozen ML-24 `_grid`:
complete >=2x2/no spans, exact boundaries, conservative character association.
Дополнительно все исходные characters должны попасть в ровно одну ячейку;
пересечение с painted bar запрещено. Ошибка не выпускает accepted cells, исходные
наблюдения сохраняются. Source text не исправляется и не нормализуется по смыслу.

Ограниченный interpreter принимает только прямые `re/m/l/S/f/n` и необходимые
text operators с default graphics state. Unknown ops, transforms, clipping,
fill+stroke, Forms/images/curves и unreconciled objects отклоняются. Это намеренно
узкая область, не полный PDF renderer. Black paint здесь default black;
общая visibility/compositing/semantic table correctness не доказана.

## Reproducibility, ресурсы и frozen scope

Исходная preregistration сохранена в ignored `preregistered.md` до первого score;
код/fixture inputs/config/resolved TableSettings/runtime зафиксированы перед двумя
измеренными executions в `execution-pins.json`. Test-driven исправления не меняли
H1, normalization rules, expected cells или detector settings.

Runtime: Python 3.12.3, Windows 11, serial CPU; pdfplumber 0.11.9,
pdfminer.six 20251230, pypdf 6.20.0, psutil 7.1.0, PDFium binding 5.14.0.
Сверены existing package/file и wheel manifests, Python executable hash.
Никаких installs/new dependency или GPU. Два запуска — отдельные процессы,
использующие одинаковые 21 pinned input PDF; fingerprints совпали по всем
non-resource fields, включая полный provenance/original text/cells/rejections.

| Измерение | Run 1 | Run 2 |
| --- | --- | --- |
| Parent elapsed, seconds | 5.344 | 4.969 |
| Sampled peak tree RSS, bytes | 92,213,248 | 92,917,760 |
| RSS samples | 245 | 229 |
| Per-fixture normalize range, seconds | 0.005659–0.009027 | 0.005058–0.008191 |
| Sum normalize calls, seconds | 0.155224 | 0.135751 |
| Resource failures / cleanup | 0 / true | 0 / true |

Parent elapsed включает process startup, imports, runtime/hash verification,
fixture oracles и capture; normalize timings исключают большую часть import/startup.
Peak — sampled RSS process tree с интервалом 0.02s, не непрерывный OS peak.
Все исходные attempts сохранены; monitored executions не повторялись выборочно.

| Identity | SHA-256 / fingerprint |
| --- | --- |
| Preregistered protocol | `50c78cba47fe181dcd9cecd4543b10eb8d413651c4dea7c8a9173552f3c5e322` |
| Input/config/code/runtime identity | `d89eb5fa2ec516705ca8eeccabcee693961ebefa008210bc2b65da0641613141` |
| Both deterministic results | `9debb54e1ed2238de4baf46982a8e52c499af74224526fb6c61631ad483cdd4c` |
| New tool | `997472bbd86914d444c32fc89983817c85df40670dfa9e2306438f9486611e64` |
| New tests | `b7064d2892f434447d59fcab78783fffb3d93f12dab3ce4660d36c7361d42d62` |

Перед/после проверены 39 ML-23 и 84 ML-24 frozen artifact hashes и pinned code/
runtime. Дополнительная public regression сравнила полные ML-23/24 outputs до и
после transform на всех 21 fixtures: без различий. Это неизменность поведения,
не повторный private benchmark. Frozen ML-24 на filled fixture даёт 25 geometric
cells; он не обязан reject этот synthetic input. Historical private REJECT остаётся.

## Выполненная verification

Итог: **373 passed in 19.61s**, без failed/skipped: 47 новых и 326 прежних tests.
Включены malformed input, все logical limits, timeout, memory/output guard и
worker failure cleanup, invalid/mismatched capture, CLI success/failure/existing
output, literal/origin/oracle checks и unchanged detector behavior.
Ruff: All checks passed; format --check: 2 files already formatted.

Первый тестовый запуск: 45 passed / 1 failed. Все fixture oracles прошли;
неверная regression assumption ожидала, что ML-24 rejects filled fixture.
Исправлено только expectation на прежние 25 cells; поведение candidate не менялось.
Первоначальный Ruff нашёл пять длинных строк; format исправил их. Failures не скрыты.
Прежний monitor TOCTOU из ML-25 не исправлялся: workers используют stable capture
names, publication/cleanup только после завершения monitor. В этих executions
ошибка не наблюдалась; общий race у других callers остаётся out of scope.

Actual PowerShell commands from repository root:

```powershell
$env:PYTHONPATH = ((Join-Path (Get-Location) 'src') + ';' + (Get-Location).Path)
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B -m pytest -q --confcutdir=tests/unit -p no:cacheprovider --basetemp=evaluation-output/pdf-filled-ruling-v1-20261019/tests-2 tests/unit/test_pdf_filled_ruling_normalization.py tests/unit/test_pdf_table_geometry.py tests/unit/test_pdfplumber_table_candidate.py tests/unit/test_pdf_table_candidate.py tests/unit/test_extraction.py tests/unit/test_extraction_fidelity.py tests/unit/test_docling_candidate.py tests/unit/test_pdf_ocr_candidate.py
.venv/Scripts/ruff.exe check tools/pdf_table_geometry/filled_ruling_normalization.py tests/unit/test_pdf_filled_ruling_normalization.py
.venv/Scripts/ruff.exe format --check tools/pdf_table_geometry/filled_ruling_normalization.py tests/unit/test_pdf_filled_ruling_normalization.py
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdf-filled-ruling-v1-20261019/execute.py
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdf-filled-ruling-v1-20261019/execute.py --run run-1
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdf-filled-ruling-v1-20261019/execute.py --run run-2
evaluation-output/pdfplumber-table-v1-20261019/runtime/Scripts/python.exe -B evaluation-output/pdf-filled-ruling-v1-20261019/execute.py --verify
git diff --check
git status --short --untracked-files=all
```

`execute.py` preparation runs once with fresh inputs; existing output dirs are not
overwritten. Ignored public artifacts, resource journals, protocol, code/runtime/
input pins и before/after regression captures остаются в experiment directory.
Публичные PDF/JSON не добавляются в Git. Runtime/service E2E не требуется и не запускался.

## Limitations и остановка

Synthetic-only representation equivalence доказана для заявленного subset, а не
общее восстановление таблиц. Нет данных о private c1 sources, merged tables,
compositing/occlusion, nested Forms, OCR, RU/KK, independent private Gold fidelity
или downstream chunk/retrieval/answer improvement. Полные logical tables нельзя
считать найденными лишь по painted bars. Любая новая область требует отдельного
protocol/review; production routing и QG-01 не продвигаются.

Новые файлы: standalone tool, его public tests и этот report. Остальные tracked
файлы, frozen settings и Gold не менялись. Commit не создан: review required.


## Final scope/security review

`git diff --check` passed. Для трёх untracked файлов дополнительно выполнен
`git -c core.autocrlf=false diff --no-index --check -- NUL <file>`: нет whitespace
errors (exit 1 здесь означает наличие добавленного diff). Command-local autocrlf
использован после стандартного LF/CRLF warning; repository settings не менялись.
No-index diff/stat просмотрен: только три новые requested files. Проверены UTF-8/LF,
локальные report links/anchors и secret/private-path patterns; совпадений нет.
Staged diff пуст; существующие tracked files неизменны. Оригинальный protocol hash
проверяется по immutable ignored snapshot; после него добавлены только результаты.
Ignored terminal artifact manifest фиксирует public inputs, оба result/resource
capture, runner/config/protocol/runtime pins и frozen regression fingerprints;
все SHA сверены, pytest temporary fixtures исключены.

Exact final `git status --short --untracked-files=all`:

```text
?? docs/eda/pdf_filled_ruling_normalization_v1.md
?? tests/unit/test_pdf_filled_ruling_normalization.py
?? tools/pdf_table_geometry/filled_ruling_normalization.py
```
