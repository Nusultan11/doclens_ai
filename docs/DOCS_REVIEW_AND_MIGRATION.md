# DocLens AI — review и миграция документации v4

19.10.2026. Scope: документация и stale skill routing. Runtime, migrations,
Gold, configs, исторические evaluations и DOCX сохранены.
Исходный branch `main`, HEAD `c63d72d9bb854dd4ed16a29fcbe1bfb1ff873eb9`, worktree clean.
Предыдущий relevant [table geometry diagnosis](eda/pdf_table_geometry_diagnosis_v1.md)
исторический, не текущий runtime PASS.

## Владельцы и изменения

| Topic | Владелец после миграции | Решение |
| --- | --- | --- |
| Modules/contracts/lifecycle/security/roadmap | [Architecture v4](../Doclens_AI-architecture.md) | Новый Markdown owner; DOCX только история |
| Goals/coverage/QG/release | [Quality Policy](../DocLens_AI_Project_Goals_and_Quality_Policy-1.md) | Единственные gate definitions; thresholds TBD |
| Format methods/locators/parser experiments | [Extraction](../DocLens_AI_Extraction_Strategy.md) | Native-first, scoped rejected configs, future MinerU |
| EDA/Gold/cleaning/chunks/models/RAG/protocol | [ML Strategy](../DocLens_AI_ML_Quality_Strategy.md) | Frozen comparisons и independent scoring |
| Authorized Kaggle execution | [GPU Playbook](../DocLens_AI_Kaggle_GPU_Playbook.md) | Execution не promotion/transfer permission |
| Stable IDs/URLs/usage | [Engineering Sources](../DocLens_AI_Engineering_Sources.md) | Все 39 прежних IDs сохранены; PAR-06..08 добавлены |
| Codex procedure | [AGENTS](../AGENTS.md) | Ссылки на owners вместо второй копии contracts |
| Navigation | [Source map](../README_SOURCE_MAP.md), [README entry](../README.md) | Остальные README sections сохранены |
| Task procedures | Восемь `.agents/skills/*/SKILL.md` | Только stale routing/missing-playbook wording; строгие checks сохранены |

## Reconciliation и сохранённые contracts

Источники: user v4 brief; текст DOCX v3 через OOXML; прежние root Markdown и все
восемь skills; `pyproject.toml`; models/processing/index_revision и migration 0007,
services upload/retrieval/rag, extraction parsers/chunk config; selected reports.
Единственный AGENTS — root. Это не полный implementation/security audit:
часть code evidence просмотрена по определениям/выборочным участкам. Runtime tests
и ML/GPU experiments не запускались, прежние результаты не пересчитаны.

| Конфликт/риск | Решение |
| --- | --- |
| DOCX был sole architecture | P-ARCH теперь Markdown v4; старые section numbers historical |
| Target state machine похожа на runtime enums | ARCH-JOBS фиксирует enums отдельно от READY target |
| Upload identity сокращалась до SHA | Filename/type/size/SHA, operation scope/replay/409 сохранены |
| Разные transaction domains | DB/S3 references/readback/orphan checks; DB rollback не отменяет external writes |
| Stale workers/partial index | DB clock/lease/heartbeat/retry/cancellation/fencing, atomic chunks, exact candidate verification и single ACTIVE partial unique |
| Payload/locator примеры принимались за schema | Wire contract у code/README; genuine locators у Extraction; missing fields не фабрикуются |
| Revocation обещалась без race | Проверки до context/после inference всего packed evidence; delivery race явно сохранён |
| OCR/ML-11 не запускались в старом snapshot | Later reports отдельно; snapshot не current experiment ledger |
| DOCX heading/section support overstated | Body/table baseline; ancillary/section TARGET |
| Gate ownership дублировалось | Quality Policy определяет gates, методы/процедуры ссылаются на неё |
| Исторический OPEN выглядел fresh check | Старые link statuses не выдаются за текущую проверку |

Сохранены immutable source/config/model lineage, deterministic IDs, bounded resources,
private/least-privilege boundaries, Office non-execution, untrusted inputs/model output,
semantic checks/refusal отдельно от schema, no sealed tuning, family-safe splits,
failure-inclusive denominators и independent quality/release authorization.
Delete/reindex/READY/recovery/backups+restore/rollback — обязательные TARGET,
не выдуманные implemented features. Dependencies/infrastructure не добавлены.

## Историческое evidence и gaps

[Docling expanded](eda/docling_pdf_expanded_benchmark_v1.md),
[vector-grid](eda/pdf_table_candidate_v1.md),
[pdfplumber](eda/pdfplumber_table_candidate_v1.md): frozen configurations REJECTED.
[Expanded selective OCR](eda/pdf_selective_ocr_expanded_eval_v1.md): INCONCLUSIVE.
[DOCX footnote](eda/docx_footnote_candidate_v1.md): offline candidate, не production coverage.
[Generation baseline](evaluation/rag_real_baseline_v1.md),
[comparison](evaluation/rag_model_compare_dev_v1.md),
[schema](evaluation/rag_schema_dev_v1.md) сохраняют scoped отрицательные результаты;
[quote binder](evaluation/rag_quote_binding_dev_v1.md) не semantic approval.

DOCX фиксировал 48 reviewed EN Retrieval queries (45 positive/3 negative), 20 EN
Answer records (17 positive/3 negative), negatives только DEV и одного attested reviewer.
Это исторические срезы, не новый independent review. RU/KK, held-out negatives,
family/language coverage и semantic production quality требуют отдельного evidence.
Утверждённых исторических QG thresholds не восстановлено. MinerU 4.0 `basic` — future
proposal из brief, NOT_EVALUATED; exact tag/API/runtime/license не квалифицированы.
Существенных неразрешённых конфликтов между v4 owners не выявлено; эти quality/
implementation gaps не закрываются документацией.

[RAGFlow](https://github.com/infiniflow/ragflow),
[Docling](https://github.com/docling-project/docling),
[Marker](https://github.com/datalab-to/marker),
[MinerU](https://github.com/opendatalab/MinerU) открыты 19.10.2026.
Это reachability, не adoption/version/license/benchmark qualification.

## Проверки и воспроизведение

Runtime/real-service/ML/GPU проверки пропущены: изменения документационные;
production release не квалифицируется. Commit запрещён до review.
Documentation acceptance проверяется скриптом ниже; он также проверяет ссылки
в остальных tracked Markdown, stable IDs/explicit anchors и неизменность DOCX.

```python
from pathlib import Path
from urllib.parse import unquote
import re
import subprocess
import hashlib

def git(*args):
    return subprocess.check_output(['git', *args])
def anchors(text):
    result = set(re.findall(r'<a\s+id="([^"]+)"', text))
    counts = {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', text, re.M):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        result.add(slug if n == 0 else f'{slug}-{n}')
    return result
files = [Path(p) for p in git('ls-files', '*.md').decode().splitlines()]
files += [Path('Doclens_AI-architecture.md'), Path('docs/DOCS_REVIEW_AND_MIGRATION.md')]
errors, checked = [], 0
for p in dict.fromkeys(files):
    text = p.read_text(encoding='utf-8')
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'`[^`]+`', '', text)
    for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        link = link.strip().strip('<>')
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', link):
            continue
        target, _, fragment = unquote(link).partition('#')
        dest = (p.parent / target) if target else p
        checked += 1
        if not dest.exists():
            errors.append(f'{p}: missing {link}')
        elif fragment and dest.suffix == '.md':
            if fragment not in anchors(dest.read_text(encoding='utf-8')):
                errors.append(f'{p}: missing anchor {link}')
old_catalog = git('show', 'HEAD:DocLens_AI_Engineering_Sources.md').decode()
new_catalog = Path('DocLens_AI_Engineering_Sources.md').read_text(encoding='utf-8')
ids = set(re.findall(r'^\| ([A-Z]+-\d+|[RD]\d+) \|', old_catalog, re.M))
assert ids <= set(re.findall(r'^\| ([A-Z]+-\d+|[RD]\d+) \|', new_catalog, re.M))
for p in Path('.').glob('DocLens_AI_*.md'):
    old = git('show', f'HEAD:{p.as_posix()}').decode()
    assert set(re.findall(r'<a id="([^"]+)"', old)) <= anchors(p.read_text(encoding='utf-8'))
changed = git('diff', '--name-only', 'HEAD').decode().splitlines()
assert all(p.endswith('.md') for p in changed), changed
assert not any(p.startswith(('src/', 'tests/', 'alembic/', 'tools/')) for p in changed)
untracked = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
assert set(untracked) == {'Doclens_AI-architecture.md', 'docs/DOCS_REVIEW_AND_MIGRATION.md'}
quality = Path('DocLens_AI_Project_Goals_and_Quality_Policy-1.md').read_text(encoding='utf-8')
assert all(f'| QG-{n:02d} ' in quality for n in range(10))
docx = 'Doclens_AI-architecture.docx'
assert hashlib.sha256(Path(docx).read_bytes()).digest() == hashlib.sha256(git('show', f'HEAD:{docx}')).digest()
assert not errors, '\n'.join(errors)
print(f'PASS: {checked} local links/anchors; {len(ids)} stable IDs; legacy explicit anchors; documentation scope; unchanged DOCX')
```

Из root запустить Python-блок выше через `.venv\Scripts\python.exe -`, затем
`git diff --check`, `git diff --stat`, `git status --short`.
Scope review включает новые untracked документы, которые `git diff --stat`
до staging не учитывает. Результаты фиксируются после выполнения ниже.


### Выполненные результаты

- `.venv\Scripts\python.exe -` (Python-блок выше, извлечённый до closing fence):
  PASS — 138 local links/anchors, 39 stable IDs, прежние explicit anchors,
  только documentation scope и byte-identical DOCX. Проверены также десять gate
  rows и точный allowlist двух untracked files.
- `git diff --check`: PASS, exit 0, без вывода.
- `git diff --stat` / `git diff --numstat`: reviewed; 16 tracked Markdown files,
  489 insertions / 710 deletions до добавления двух новых документов в index.
- `git diff --cached --stat`: пусто; staged изменений нет.
- `git diff -- README.md` и `git diff -- .agents/skills`: только documentation entry
  и устаревшая маршрутизация; procedural safety/evaluation checks сохранены.
- Manual owner/contract review: один owner на тему; critical contracts сопоставлены
  в reconciliation table. Нет нового benchmark/Gold review/gate/release PASS.
- Initial shell quoting/command-length/encoding issues исправлены; первая попытка
  извлечения verification block завершилась SyntaxError из-за fence delimiter;
  исправленный запуск прошёл. Это tooling failures, не скрытые runtime results.

Точные final status paths (все unstaged):

```text
 M .agents/skills/doclens-data-quality/SKILL.md
 M .agents/skills/doclens-db-migration/SKILL.md
 M .agents/skills/doclens-extraction-benchmark/SKILL.md
 M .agents/skills/doclens-ingestion-change/SKILL.md
 M .agents/skills/doclens-kaggle-gpu/SKILL.md
 M .agents/skills/doclens-ml-experiment/SKILL.md
 M .agents/skills/doclens-production-readiness/SKILL.md
 M .agents/skills/doclens-rag-evaluation/SKILL.md
 M AGENTS.md
 M DocLens_AI_Engineering_Sources.md
 M DocLens_AI_Extraction_Strategy.md
 M DocLens_AI_Kaggle_GPU_Playbook.md
 M DocLens_AI_ML_Quality_Strategy.md
 M DocLens_AI_Project_Goals_and_Quality_Policy-1.md
 M README.md
 M README_SOURCE_MAP.md
?? Doclens_AI-architecture.md
?? docs/DOCS_REVIEW_AND_MIGRATION.md
```
