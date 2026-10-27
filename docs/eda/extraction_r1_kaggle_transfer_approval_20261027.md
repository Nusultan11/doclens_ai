# EX-02/R1 — пакет согласования передачи в Kaggle

27 октября 2026. **STATUS: PASS — пакет параметров подготовлен к рассмотрению.**
**Передача данных и запуск: BLOCKED. Пакет не утверждён.**

Пользователь разрешил подготовить конкретный пакет без загрузок. Поля
`approved_by` и `approved_at` оставлены пустыми, `transfer_authorized=false`.
Никаких человеческих подтверждений, разрешений правообладателей или новых
прав облачной обработки не сформировано автоматически.

## Что предлагается согласовать

Назначение — возможная передача ровно 11 замороженных DEV PDF для существующего
R1 Docling/native сравнения. План измерений остаётся прежним: две полные
последовательные итерации, по 11 документов, с учётом всех ошибок и пропусков.
Native captures, исторические метки и оценивание остаются локальными.
Семантическое качество, независимый Gold и QG-01 — NOT_EVALUATED.

Основания: [матрица облачного допуска](extraction_r1_kaggle_cloud_admission_20261027.json),
[аудит прав](extraction_r1_kaggle_cloud_admission_20261027.md),
[существующий локальный R1](extraction_r1_local_20261027.md),
[GPU Playbook](../../DocLens_AI_Kaggle_GPU_Playbook.md#GPU-MODE).
Новые конфигурации моделей, пороги допуска и эксперименты этим пакетом не вводятся.

Машиночитаемый документ:
[transfer approval JSON](extraction_r1_kaggle_transfer_approval_20261027.json).
Его fingerprint:
`3b15d4450156554bde35a1f57fdb9fe799a0d4c8f12ccd7317474ec6c4ece9db`.

## Проект назначения и доступа

| Параметр | Предлагаемое значение |
| --- | --- |
| Платформа | Kaggle |
| Владелец | `nurs2005`, по существующей документации проекта |
| Отдельный dataset | `nurs2005/doclens-extraction-r1-dev-pdf-11` |
| Отдельный notebook | `nurs2005/doclens-extraction-r1-docling-dev` |
| Видимость | Только private |
| Collaborators | Пустой список |
| Другие notebook/competition attachments | Не допускаются этим пакетом |
| Внешний inference/API, передача третьим сервисам | Не допускаются |
| Получатели | Предлагаемая учётная запись владельца и сервис Kaggle с его инфраструктурой |

Это **проект назначения**, а не подтверждение существования или доступности этих
ресурсов. Новые dataset/notebook не создавались. Текущая авторизованная учётная
запись, отсутствие коллизий имён, privacy и collaborators удалённо не проверялись.
Private не означает отсутствие обработки на стороне поставщика платформы.
Регион, subprocessors и резервное хранение поставщика не установлены.

Существующие R0, GPU smoke, LLM и RAG notebook не входят в разрешённое назначение;
они не должны быть перезаписаны или получить эти originals как новые inputs.

## Точный проект allowlist

**14 файлов, 1 391 386 байт:** 11 оригиналов — 1 368 922 байта; три файла
атрибуции/происхождения — 22 464 байта. Таблица показывает будущие aliases,
а не существующий upload/staging. Полные SHA-256 находятся в JSON.

| Предлагаемый alias | Байт | SHA-256, первые 12 символов |
| --- | ---: | --- |
| originals/c1-0031.pdf | 1732 | 1179d9f2925a |
| originals/c1-0032.pdf | 20617 | 5f9082eabbb5 |
| originals/c1-0033.pdf | 29702 | 081c9cfcc8e8 |
| originals/c1-0035.pdf | 38361 | 94a5b7cdc01f |
| originals/c1-0040.pdf | 64968 | 18a25155acbe |
| originals/c1-0041.pdf | 77333 | daef7ef6b8dd |
| originals/c1-0043.pdf | 91484 | b70a5d33160e |
| originals/c1-0044.pdf | 100551 | 43a961d9f868 |
| originals/c1-0048.pdf | 228777 | 5928ffa7f5f8 |
| originals/c1-0049.pdf | 254032 | fa821b92dde1 |
| originals/c1-0050.pdf | 461365 | f1ac87dc692b |
| ATTRIBUTION.md | 4121 | 1e8b5a5b4ba9 |
| OPEN-GOVERNMENT-LICENCE-v3.0.html | 10450 | f5b2b9f2af63 |
| PROVENANCE.json | 7893 | 55eba29f3068 |

Сопроводительные файлы содержат атрибуцию, публичные ссылки происхождения,
SHA/размеры и неизменённую ранее захваченную OGL v3. Они **не являются разрешением**
на облачную обработку. Статус прав в provenance явно относится к моменту подготовки
этого проекта. Превью находится только в ignored local storage; оригиналы PDF
не копировались, архив с ними не создавался, upload directory не готовился.

Не входят в allowlist: Gold, исторические метки, reviewer sessions и attestations,
EX-01 captures, TEST/QA/sealed sources, изображения страниц и аннотации,
предыдущие результаты, репозиторий/.git, credentials, переменные окружения,
веса моделей, код runner и посторонние evaluation reports.
Административные CLI metadata и исполняемый runner не подготовлены этим пакетом;
это не готовый каталог для команды Kaggle upload/push.

## Предлагаемые результаты и хранение

Возможный R1 должен сохранить полные Docling exports, backend pages и conversion
metadata, статусы/ошибки/предупреждения, оба повторения, SHA/fingerprints и измерения
времени/RSS. Такие файлы и полные логи могут содержать исходный материал, поэтому
они должны оставаться private. Только обезличенные технические агрегаты могут
попасть в Git; локальное сравнение с метками не требует передачи Gold.

Предлагаемый срок удалённого хранения:

- Не более **7 календарных суток от первой фактической загрузки**.
- После проверенной локальной выгрузки всех результатов — удалить созданные для
  этого запуска dataset versions, notebook outputs/logs и собственные временные
  ресурсы **в течение 24 часов**. Применяется более ранний срок.
- Продление, публикация, добавление collaborators или использование в иных
  notebook требуют нового согласования.
- Локальные доказательства сохраняются в ignored private storage. Ранее созданные,
  чужие или общие ресурсы не входят в план удаления.

Это предлагаемые параметры для пользовательского рассмотрения, а не уже принятое
разрешение на удаление. Гарантия удаления всех резервных копий у поставщика
не установлена. Если требования хранения нельзя выполнить, передача должна
оставаться заблокированной.

## Условия, которые согласование параметров не заменяет

1. **Права всех 11 originals:** действующая матрица по-прежнему содержит
   11 UNRESOLVED и 0 CLOUD_ADMITTED. Нужна отдельная доказательная квалификация
   применимости лицензии к cloud use и исключениям; разрешение пользователя
   не выдаёт недостающих прав правообладателя и не подтверждает иной законный basis.
   Локальные clearances c1-0033/c1-0040 не были расширены.
2. **Явное разрешение передачи:** текущий запрос разрешает только подготовку.
   Согласование этого документа как проекта параметров не должно быть записано
   как команда на upload или job submission. Для исполнения требуется отдельное
   явное указание, привязанное к окончательному manifest/fingerprint и назначению,
   после закрытия остальных условий.
3. **Фактическая проверка назначения и правил платформы:** владелец, private,
   recipients/collaborators, допустимое хранение и условия использования должны
   быть проверены до передачи. Публичные страницы
   [Kaggle Terms](https://www.kaggle.com/terms),
   [Privacy](https://www.kaggle.com/privacy) и документация открывались, но web tool
   не получил читаемого тела этих страниц. Их актуальные положения этим пакетом
   не считаются проверенными; никакие свойства удаления/конфиденциальности
   поставщика не выдуманы.
4. **Проверенный R1 runner и исполнение ограничений:** существующий
   [Kaggle staging guide](../../tools/kaggle_gpu/extraction_campaign.md) описывает R0
   и требует отдельно рассмотренный standalone source. Удалённый владельцем
   `extraction_remote.py` не восстановлен и не заменён. Перенос Windows Job limits
   и текущего worker на Linux, runtime parity и сетевые ограничения не проверены.
   Код/модели не входят в этот data-transfer allowlist.

Конфигурация остаётся Docling 2.55.1 / docling-core 2.48.2, CPU, FAST,
cell matching, 2 threads, seed 0, без OCR/enrichment/external inference.
Замороженный local configuration fingerprint:
`8f38b59b116df87a37f60aef1e26b0291cdb213a743ec8824d50cd43ad28676d`.
Полный model inventory fingerprint:
`3afbf148d4732567f47cd3320698a07327faecd2306956ab6c155c032da49994`.

Минимум RAM **2 684 354 560 байт** и действующие лимиты не ослаблены:
600 секунд wall/document, 1200 CPU seconds, 1.5 GiB sampled tree RSS,
4 GiB OS commit, 128 MiB native JSON, 256 MiB scratch, один worker.
Это ссылка на существующую политику, а не утверждение её исполнения в Kaggle.
Windows paths модели также не объявлены готовой конфигурацией mounted Kaggle input.
Исторические лимиты и runtime R0 не подставляются вместо R1.

Любой недопущенный источник, несовпавшие bytes/SHA/size, лишний файл,
непроверенная privacy, неподтверждённый runner либо изменение модели/лимитов —
**STOP**. Не допускаются частичный cohort, скрытая замена исходников или retries
с новой конфигурацией под видом того же R1.

## Что можно подтвердить при рассмотрении

Пользователь может согласовать именно **предлагаемые параметры**: назначение,
14-file allowlist, отсутствие collaborators, границы результатов и сроки хранения.
Возможная формулировка ответа для такого согласования:

> Согласовываю параметры проекта с fingerprint
> 3b15d4450156554bde35a1f57fdb9fe799a0d4c8f12ccd7317474ec6c4ece9db.
> Это не подтверждение недостающих прав источников и не команда начинать загрузку.

Этот текст — предложение для рассмотрения, не уже полученное согласие. Ни одно
поле reviewer/approver или human/legal attestation не заполнено агентом.

## Проверки и приватные материалы

Ветка `main`, HEAD `e27239e4f0d8b8e953dc7223aa3f07ed1f6db1d3`.
Сверены fingerprints ранее завершённого rights audit и матрицы, текущие code pins,
точный R1 source/config binding, SHA/size всех 11 originals, 14 уникальных aliases
и сумма байтов. **26 ранее существовавших файлов** сохранены побайтно, включая
uncommitted harness, локальный R1, предыдущие audit reports и четыре evaluation
reports. Предсуществующее удаление Kaggle runner сохранено.

Выполненные команды:

```text
.venv/Scripts/ruff.exe check evaluation-output/extraction-r1-kaggle-transfer-approval-20261027/prepare_packet.py
All checks passed!
.venv/Scripts/ruff.exe format --check evaluation-output/extraction-r1-kaggle-transfer-approval-20261027/prepare_packet.py
1 file already formatted
.venv/Scripts/python.exe -B -X utf8 evaluation-output/extraction-r1-kaggle-transfer-approval-20261027/prepare_packet.py
exit 0; READY_FOR_PARAMETER_REVIEW; transfer BLOCKED
14 files proposed; 11 originals; 1391386 bytes; 26 files preserved
uploads=0; jobs=0; original_copies_staged=0
```

Ignored private packet:
`evaluation-output/extraction-r1-kaggle-transfer-approval-20261027/review-1/`.
`review-materials/` содержит три файла превью; `preparation-receipt.json` — локальные
source bindings, SHA/fingerprints и доказательства сохранности. Fingerprint receipt:
`bdb85d585e572e823529f284ab3741b36bed4ee373af0b57dff436c53c99231c`.
Одноразовый private preparation script сохранён со своим SHA в receipt.

Pytest и extraction/model experiments не запускались: существующий Python-код
проекта не менялся, подготовлены документы и metadata. CLI/API Kaggle,
credentials, remote creation/upload/submission/cleanup не вызывались.
Ничего не staged, не committed и не pushed. Gold и исходные документы неизменны.

Финальная read-only проверка завершилась с exit 0: fingerprints обоих новых JSON,
14 aliases и их общий размер, SHA/size 11 originals, три файла превью, 26 прежних
файлов, ссылки и whitespace отчёта — PASS. В приватном пакете сохранён
`final-verification.json`. Проверено отсутствие PDF-копий в пакете.

```text
git diff --check
git diff --cached --check
Обе команды: exit 0, whitespace errors отсутствуют.
git diff --cached --name-only
Пусто.
git check-ignore evaluation-output/extraction-r1-kaggle-transfer-approval-20261027
evaluation-output/extraction-r1-kaggle-transfer-approval-20261027
git ls-files evaluation-output/extraction-r1-kaggle-transfer-approval-20261027
Пусто; приватные материалы ignored и untracked.
```
