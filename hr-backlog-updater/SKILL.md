---
name: hr-backlog-updater
description: Обновляет Excel-файл «Бэклог 1С ЗУП на N год» данными из Jira (проект CAB, беклог HR — настраивается под вашу организацию). Используй этот скилл всегда, когда пользователь просит «обновить бэклог», «прогнать бэклог 1С ЗУП по джире», прислал файл с именем Бэклог_1С_ЗУП_*.xlsx, или упоминает регулярное обновление списка задач 1С ЗУП / HR-беклога. Также используй, если пользователь явно ссылается на «JQL по HR-беклогу» или просит свести данные из Jira в файл. Если пользователь НЕ приложил файл — скилл качает свежий бэклог с Confluence через MCP; если MCP-download недоступен, просит пользователя положить файл руками. По окончании публикует обновлённый файл новой дочерней страницей Confluence с сегодняшней датой. НЕ используй для других беклогов кроме HR.
---

# HR Backlog Updater

Берёт текущий xlsx с бэклогом 1С ЗУП, обновляет его данными из Jira (CAB) — статусы, оценки, комментарии, даты завершения, плюс дату выхода в тест из связанных FI-задач. Колонки `ФН`, `Страна`, `Система` ведутся вручную, не перезаписываются.

## Когда применять

Триггеры:
- Пользователь приложил файл `Бэклог_1С_ЗУП_*.xlsx` и просит «обновить» / «прогнать»
- «Обнови бэклог», «обнови по JQL», «новый прогон», «пересоберём из Jira»
- Упоминание HR-беклога, CAB-проекта или JQL `беклог = HR`

Не применять для других беклогов (ФД, КБ, Ритейл) — это отдельные workflow.

## Окружение (Claude Code на macOS)

- **Рабочая директория**: `<work_dir>` (например `~/hr-backlog/` или `~/Assistant/hr-backlog/`). Содержит `.venv` (с openpyxl) и кэш JSON-ов. На первом запуске создаётся.
- **Скрипты**: `scripts/merge_backlog.py`, `scripts/distill_cab.py`, `scripts/distill_fi.py`, `scripts/render_page_storage.py` — лежат в директории скилла. Запускай их через `python` из `.venv`.
- **Cloud ID Atlassian** (для вашей организации): `<cloudId>` — UUID, получить через `getAccessibleAtlassianResources`.
- **Confluence parent-page** (родитель HR-бэклогов): `<hr_backlog_parent_id>` — числовой ID страницы в Confluence-пространстве, где живут датированные бэклоги.

### Два Atlassian MCP — у каждого свои сильные стороны

Подключены оба, надо знать, что от какого требовать:

| Операция | Какой MCP | Заметка |
|---|---|---|
| Список дочерних страниц Confluence | `mcp-atlassian.confluence_get_page_children` | работает |
| Тело страницы Confluence | `mcp-atlassian.confluence_get_page` | работает, поддерживает HTML/markdown/ADF |
| Список аттачей | `mcp-atlassian.confluence_get_attachments` | возвращает `fileSize`, `id` с префиксом `att...` |
| Download аттача | ❌ `mcp-atlassian.confluence_download_attachment` ВСЕГДА ПАДАЕТ (как минимум на май 2026). Если упало — проси пользователя положить файл руками. НЕ ищи в локальных директориях |
| Создание страницы | `mcp-atlassian.confluence_create_page` | поддерживает `content_format = storage` для макросов |
| Upload аттача | `mcp-atlassian.confluence_upload_attachment` | работает (не путать с download) |
| JQL Jira + пагинация | `<atlassian-mcp-uuid>.searchJiraIssuesUsingJql` (официальный Atlassian MCP) | КОРРЕКТНАЯ пагинация через `nextPageToken` |
| ❌ Не используй для пагинации | `mcp-atlassian.jira_search` | игнорирует `start_at`, возвращает одну и ту же страницу |

В дальнейшем тексте префиксы MCP опущены — выбирай по таблице.

## Высокоуровневый workflow

1. Подготовить рабочую директорию (venv, .venv/bin/pip install openpyxl)
2. Найти свежую страницу Confluence (`source_page_id`)
3. Получить исходный xlsx через Confluence MCP download; если упало — попросить пользователя положить файл
4. JQL CAB-задач (через official MCP, пагинация nextPageToken)
5. JQL связанных FI-задач батчами по 50
6. **NEW (2026-05-27): `jira_batch_get_changelogs` для всех FI** — нужно для двух новых колонок: «Плановая дата выхода в тест» (первая установка test_date при статусе FI «Запланирована») и «Фактическая дата завершения» (последний переход в статус «Выполнено»). Батчи по 30-35 ключей, ответы сохраняются в tool-results.
7. Lookup для непришедших ключей (`non_jql_lookup.json`)
8. Запустить `scripts/merge_backlog.py` — он создаст xlsx + `merge_stats.json`
9. Сгенерировать тело страницы через `scripts/render_page_storage.py` (читает `merge_stats.json` и вшивает таблицу-сводку) и создать страницу Confluence
10. Upload xlsx
11. Сообщить URL пользователю

## Шаг 1: подготовка

```bash
mkdir -p <work_dir>
cd <work_dir>
[ -d .venv ] || (python3 -m venv .venv && .venv/bin/pip install -q openpyxl)
```

Cutoff-дата по умолчанию — `2026-01-01` (или начало года, для которого собирается бэклог). Если у пользователя другое — спросить через AskUserQuestion заранее.

## Шаг 2: свежая страница Confluence

```
confluence_get_page_children
parent_id = <hr_backlog_parent_id>
limit = 50
```

Из заголовков формата `Беклог 1С ЗУП YYYY-MM-DD` (или `Беклог 1С ЗУП на YYYY-MM-DD`) выбери самую свежую дату. Сохрани `source_page_id` — пригодится для текста новой страницы.

Если страниц больше 50 — листай через `start`.

## Шаг 3: получить xlsx

### 3a. Метаданные аттача

```
confluence_get_attachments
content_id = <source_page_id>
```

Из списка возьми xlsx (по имени `*.xlsx` или mediaType `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`). Запомни:
- `title` — точное имя файла (например `Бэклог_1С_ЗУП_на_2026-05-08.xlsx`)
- `extensions.fileSize` — точный размер в байтах
- `id` — например `att6480003438`

### 3b. MCP download

```
confluence_download_attachment
attachment_id = <id с префиксом att>
```

Если получилось — сохрани полученный бинарь в `<work_dir>/backlog_source.xlsx` и переходи к шагу 4.

### 3c. Если упало — fallback на workspace, потом на пользователя

Если `confluence_download_attachment` вернул ошибку (на момент написания, май 2026, метод регулярно падает с «Failed to download attachment»):

**Шаг 3c.i — workspace fallback.** Проверь `<work_dir>` на наличие файла с именем и размером, точно совпадающими с метаданными аттача (`title` и `extensions.fileSize` из шага 3a). Это будет наш собственный output прошлого прогона — Confluence-аттач и локальный файл идентичны, потому что один создан из другого. Если совпало:
```bash
cp "<work_dir>/<title>" "<work_dir>/backlog_source.xlsx"
```
Сообщи пользователю, что использовал локальную копию прошлого прогона. Переходи к шагу 4.

**Шаг 3c.ii — запрос пользователю (если workspace не помог).** Сообщи: «Не удалось скачать `<filename>` через MCP, локальной копии нет. Открой страницу `https://<your-site>.atlassian.net/wiki/spaces/<space_key>/pages/<source_page_id>` и положи файл в `<work_dir>/backlog_source.xlsx`. Параллельно собираю данные из Jira — это не зависит от файла».

**Не лезь в `~/Downloads`, `~/Desktop` или другие пользовательские директории** — даже если файл там есть. Только Confluence, workspace `<work_dir>`, или прямое указание пользователя на путь.

Параллельно запускай шаги 4-6 (Jira не зависит от xlsx). Шаг 7 (merge) подождёт пока файл появится.

## Шаг 4: JQL CAB-задач

JQL (год в cutoff подставь актуальный):
```
project = CAB AND "беклог[select list (multiple choices)]" = HR AND type = "Change Request" AND (statusCategory != Done OR resolutiondate >= "2026-01-01") ORDER BY Rank ASC
```

Поля:
```python
["summary", "status", "priority",
 "customfield_10293",  # 1С (план в ч/д, ZUP)
 "customfield_10561",  # 1С_E (план в ч/д, E)
 "customfield_10311",  # Плановая дата завершения
 "customfield_10335",  # Статус-отчет (комментарий, ADF)
 "customfield_10363",  # Заказчик (cascading: parent.value + child.value)
 "issuelinks",          # для FI ссылок
 "resolutiondate",
 "issuetype"]
```

Вызов:
```
<atlassian-mcp-uuid>.searchJiraIssuesUsingJql
cloudId = <cloudId>
jql = <выше>
fields = [...]
maxResults = 100
nextPageToken = <из предыдущего ответа; на первом вызове опусти>
```

Ответы большие (~200-800KB), автосохраняются в `~/.claude/projects/.../tool-results/`. Это норма, не пытайся их читать целиком — передавай файлы в `distill_cab.py` (он сам распарсит).

Когда `isLast: true` → стоп. Запусти:
```bash
.venv/bin/python "<skill_dir>/scripts/distill_cab.py" <file1> <file2> ...
```

Скрипт пишет `cab_issues.json` (компактный) и `fi_keys.json` (список уникальных FI).

### Подсказка: JQL `статус != Done OR resolutiondate >= cutoff`

Эта формулировка — намеренная. `resolution = Unresolved` пропускает закрытые задачи без `resolutiondate` (их в Jira много). Не меняй её.

## Шаг 5: JQL связанных FI

```python
keys = json.load(open('fi_keys.json'))
batches = [keys[i:i+50] for i in range(0, len(keys), 50)]
```

Для каждого батча:
```
<atlassian-mcp-uuid>.searchJiraIssuesUsingJql
cloudId = <cloudId>
jql = key in (FI-1, FI-2, ...)
fields = ["customfield_11944", "customfield_10311", "customfield_10365", "status", "resolutiondate"]
maxResults = 100
```

(11944 = «Дата выхода на тест»; 10311 = «Плановая дата завершения»; 10365 = «Номер CAB»)

**Важно**: `customfield_10311` обязателен — теперь это источник для колонки N «Плановая дата завершения» (раньше брался из CAB).

Третий маленький батч (≤10 задач) может прийти инлайн целиком — сохрани его в `fi_batch_last.json` руками и передай скрипту. **При ручном сохранении ОБЯЗАТЕЛЬНО включай поле `id`** (не только `key`) — оно используется для маппинга changelog'ов.

## Шаг 6: changelog для FI (NEW 2026-05-27)

Для новых колонок «Плановая дата выхода в тест» (L) и «Фактическая дата завершения» (M) нужна история переходов FI.

```
mcp-atlassian.jira_batch_get_changelogs
issue_ids_or_keys = "FI-1,FI-2,..."  # 30-35 ключей за раз
fields = "status,customfield_11944"   # фильтр для меньшего размера ответа
```

Батчи по 30-35 FI — ответы 130-180KB, автосохраняются в tool-results. Если диск переполнен — батчи по 5-10 FI (≤25KB, влезает inline).

После сбора всех батчей:
```bash
.venv/bin/python "<skill_dir>/scripts/distill_fi.py" \
  --issues <fi_batch1.txt> <fi_batch2.txt> ... \
  --changelogs <fi_cl_batch1.txt> <fi_cl_batch2.txt> ... \
  --output fi_issues.json
```

Скрипт мапит changelog'и на FI-ключи через `issue_id` (Jira internal id) → `key`, потом:
- **plan_test_date** = первый changelog item `field=Дата выхода на тест`, когда текущий статус FI был `Запланирована`/`Запланировано`.
- **fact_done_date** = последний changelog item `field=status, to_string=Выполнено`.

Если в changelog'е никогда не было статуса «Запланирована» в момент установки test_date — `plan_test_date = None` (пусто в файле).

## Шаг 7: lookup непришедших ключей

Перед merge определи, какие CAB-ключи есть в файле, но НЕТ в JQL результате:

```bash
.venv/bin/python <<'PYEOF'
import json, re, openpyxl
wb = openpyxl.load_workbook('backlog_source.xlsx')
ws = wb.worksheets[0]
in_file = set()
for r in range(5, 6000):   # data row starts at 5 (row 4 пустая после header в row 3)
    v = ws.cell(r, 1).value
    if v: in_file.add(str(v).strip())
cab = set(json.load(open('cab_issues.json')))
missing = [k for k in in_file if re.match(r'^CAB-\d+$', k) and k not in cab]
print(','.join(missing))
PYEOF
```

Если ключи есть — запроси по ним:
```
<atlassian-mcp-uuid>.searchJiraIssuesUsingJql
jql = key in (<missing list>)
fields = ["summary","status","issuetype","resolutiondate"]
maxResults = 50
```

Из ответа собери `non_jql_lookup.json`:
```json
{
  "CAB-9710": {"issuetype":"Change Request","status_category":"done","status_name":"Выполнено","resolutiondate":null},
  "CAB-4512": {"issuetype":"Project","status_category":"indeterminate","status_name":"В работе","resolutiondate":null}
}
```

`status_category` — lowercase из `statusCategory.key`: `done`/`new`/`indeterminate`.

## Шаг 8: merge

```bash
.venv/bin/python "<skill_dir>/scripts/merge_backlog.py" \
  --input backlog_source.xlsx \
  --cab-json cab_issues.json \
  --fi-json fi_issues.json \
  --non-jql non_jql_lookup.json \
  --output "Бэклог_1С_ЗУП_на_$(date +%F).xlsx" \
  --cutoff-date 2026-01-01 \
  --today $(date +%F)
```

Скрипт сам:
- Найдёт лист `2026` (или первый — терпит кириллицу в заголовке `№CАВ`)
- Прочитает row 3 как заголовки, **data начинается с row 5** (row 4 — пустая строка-разделитель)
- Соберёт **все** строки с ключами (включая дубликаты типа 24× `нет`)
- Manual колонки B (ФН), C (Страна), H (Система) — НЕ ТРОНЕТ
- **SKIP-логика (NEW 2026-05-27)**: если текущий статус (колонка F) в файле = `«Выполнено»`, `«Отмена»` или `«План»` — строка вообще не трогается (никаких ячеек, никаких меток). Счётчик `skipped` в `merge_stats.json`.
- Обновит data из Jira для совпадений (только активные строки, не в SKIP-статусах)
- Добавит новые строки из JQL в конец
- Расставит метки в O (Дата обновления):
  - `нет` / `-` / `—` / `tbd` / `?` → «Плейсхолдер (нет CAB)»
  - Кириллица в префиксе ключа → «Некорректный ключ (кириллица)»
  - Не CAB-shaped → «Некорректная запись»
  - В non_jql, тип ≠ Change Request → «Не Change Request (тип X)»
  - В non_jql, done + «Отмен» в названии → «Отменена до YYYY»
  - В non_jql, done остальное → «Выполнена до YYYY»
  - Остальные → «Не в JQL»
- Пересчитает SUBTOTAL формулы в row 2 (диапазон `G5:G<last>`, `I5:I<last>`)
- Добавит шапки «Фактическая дата выхода в тест» (K), «Плановая дата выхода в тест» (L), «Фактическая дата завершения» (M), «Плановая дата завершения» (N), «Дата обновления» (O) если их ещё нет

Вывод скрипта:
```
updated=51 added=4 labeled=27 skipped=75
  skipped by status: {'Выполнено': 50, 'Отмена': 1, 'План': 24}
  placeholders=24 done_before=2 cancelled_before=0 non_cr=1 invalid_cyrillic=0 invalid_other=0 not_in_jql=0
file_keys_marked_'Не в JQL' (need lookup): []
stats  -> <work_dir>/merge_stats.json
output -> Бэклог_1С_ЗУП_на_2026-05-27.xlsx
```

Если в `file_keys_marked_'Не в JQL'` НЕ пусто — догони lookup (шаг 6), пересоздай non_jql_lookup.json, перезапусти merge.

Скрипт также сохраняет `merge_stats.json` рядом с output — он нужен на шаге 8a, чтобы автоматически собрать таблицу для Confluence-страницы.

## Шаг 9: публикация в Confluence

### 9a. Собрать тело страницы и создать её

ОБЯЗАТЕЛЬНО `content_format = "storage"`, иначе макрос view-file и таблица сводки не отрисуются.

Сначала сгенерируй тело страницы из `merge_stats.json` (там уже есть все цифры с разбивкой меток):

```bash
# (optional) override base URL + space key for the prev-page link
export CONFLUENCE_BASE_URL="https://<your-site>.atlassian.net"
export CONFLUENCE_SPACE_KEY="<space_key>"

.venv/bin/python "<skill_dir>/scripts/render_page_storage.py" \
  --stats merge_stats.json \
  --output-filename "Бэклог_1С_ЗУП_на_$(date +%F).xlsx" \
  --prev-page-id <source_page_id> \
  --prev-date <YYYY-MM-DD предыдущей страницы> \
  > page.xhtml
```

`page.xhtml` — это storage-XHTML: блок с view-file макросом, вступительный параграф, заголовок «Сводка прогона» и таблица с метриками (обновлено / добавлено / помечено меткой с разбивкой по подкатегориям + полные счётчики CAB и FI). Если есть не-в-JQL ключи — в конец добавляется блок «Внимание: требуют lookup'а: …».

Затем создай страницу:

```
confluence_create_page
space_key = <space_key>
parent_id = <hr_backlog_parent_id>
title = "Беклог 1С ЗУП <today_YYYY-MM-DD>"
content_format = storage
content = <содержимое page.xhtml>
```

Запомни `new_page_id` из ответа.

Если title уже занят (409 / duplicate) → добавь суффикс «(повторный прогон)» или «(v2)» и повтори.

Если страница уже создана, а таблицу нужно дописать (например, пользователь попросил пересчитать) — используй `confluence_update_page` с тем же `content_format = "storage"` и тем же body из `render_page_storage.py`.

### 9b. Upload xlsx

```
confluence_upload_attachment
content_id = <new_page_id>
file_path = <work_dir>/<output_filename>
comment = "Итог прогона <today>: <updated> обновлено + <added> добавлено, <labeled> помечено"
```

Эта операция **РАБОТАЕТ** (баг есть только на download). После успеха view-file макрос на странице автоматически отрисует превью xlsx.

### 9c. Финальное сообщение пользователю

```
Готово.
- Confluence: https://<your-site>.atlassian.net/wiki/spaces/<space_key>/pages/<new_page_id>
- Локально: <work_dir>/<output_filename>
- Stats: <таблица из merge>
```

## Структура целевого файла (обновлено 2026-05-27)

Лист `2026`:
- Row 1: пустая
- Row 2: `Итого задач` (F) + формула `=SUBTOTAL(3,G5:Glast)` (G); `Итого часов` (H) + формула `=SUBTOTAL(9,I5:Ilast)` (I)
- Row 3: заголовки
- Row 4: **пустая строка-разделитель**
- Row 5+: данные

Колонки:

| # | Заголовок | Источник | Перезаписывать? |
|---|---|---|---|
| 1 (A) | №CAB (или с кириллицей №CАВ) | `key` | да |
| 2 (B) | ФН | ручной | **НЕТ** |
| 3 (C) | Страна | ручной | **НЕТ** |
| 4 (D) | Статус (priority) | `priority.name` | да |
| 5 (E) | Название | `summary` | да |
| 6 (F) | Статус (workflow) | `status.name` | да |
| 7 (G) | Инициатор | `customfield_10363.child.value`, fallback `value` | да |
| 8 (H) | Система | ручной | **НЕТ** |
| 9 (I) | План в ч/д | `customfield_10293 + customfield_10561`, оба null → пусто | да |
| 10 (J) | Комментарий | `customfield_10335` (ADF → plain text) | да |
| 11 (K) | Фактическая дата выхода в тест | `max(customfield_11944)` среди активных FI | да |
| 12 (L) | **Плановая дата выхода в тест (NEW)** | Из истории FI: первая установка `customfield_11944` при статусе FI = «Запланирована» | да |
| 13 (M) | **Фактическая дата завершения (NEW)** | Из истории FI: последний переход в статус «Выполнено» (`created`) | да |
| 14 (N) | Плановая дата завершения | `max(customfield_10311)` среди активных FI (раньше брался из CAB) | да |
| 15 (O) | Дата обновления | `today()` или метка | да |

«Активная FI» = `statusCategory != done` OR `resolutiondate >= cutoff`.

### SKIP-статусы (NEW 2026-05-27)

Если в файле текущий статус (колонка F) задачи равен одному из:
- **«Выполнено»**
- **«Отмена»**
- **«План»**

→ строка **полностью не трогается**: ни data, ни даты, ни метка в O. Это нужно, чтобы случайные изменения в Jira не затирали зафиксированные данные. Счётчик `skipped` отдельно от `updated`.

Все остальные задачи обновляются как обычно.

## Подводные камни

1. **CAB vs САВ**: кириллические С, А, В выглядят одинаково. Jira такие ключи не найдёт. Скрипт помечает.
2. **Дубликаты ключей** (`нет` 24×) — get_existing_key_rows возвращает list, не dict. Все строки помечаются.
3. **resolutiondate=None у Done-задач**: не используй `resolution = Unresolved`, используй `statusCategory != Done OR resolutiondate >= cutoff`.
4. **План = 0 vs план не указан**: оба null → пусто. Иначе сумма (0 валидно).
5. **Комментарий в ADF**: используй `adf_to_text` из distill_cab.py — рекурсивно с переносами строк.
6. **SUBTOTAL formula refs**: `=SUBTOTAL(3,G4:G<last>)`, `=SUBTOTAL(9,I4:I<last>)`. После добавления строк обновляй last.
7. **Confluence title duplicate**: добавь «(повторный прогон)» / «(v2)». Не перезаписывай чужую страницу.
8. **storage format**: для view-file макроса обязательно. Markdown не поддерживает `<ac:structured-macro>`.
9. **mcp-atlassian.jira_search ignores start_at**: всегда возвращает первую страницу. Используй официальный Atlassian MCP для пагинации.
10. **mcp-atlassian.confluence_download_attachment broken**: если падает — НЕ лезь в локальные директории, попроси пользователя положить файл руками.
11. **Customer cascading select**: `customfield_10363.child.value` (более конкретное имя), fallback на `.value` (отдел).
12. **Status category формат различается**: официальный MCP даёт `statusCategory: {key: 'done', name: 'Done'}`; mcp-atlassian — `category: 'Done'` или dict. Скрипт `distill_cab.py` нормализует.
13. **`issues` теперь dict, а не list** (наблюдено 2026-05-21): официальный MCP `searchJiraIssuesUsingJql` возвращает `{"issues": {"nodes": [...], "totalCount": N, "pageInfo": {...}, "webUrl": "..."}}`. Старый формат был `{"issues": [...]}` (list). Скрипты `distill_cab.py` и `distill_fi.py` поддерживают оба формата через `_extract_issues` — если упадут с `AttributeError: 'str' object has no attribute 'get'`, значит этот хелпер сломали, и нужно его восстановить.
14. **JQL пагинация — `hasNextPage`/`endCursor`**: ответ содержит `issues.pageInfo.hasNextPage` (bool) и `issues.pageInfo.endCursor` (token для следующего вызова через `nextPageToken`). `isLast: true` встречается в FI-батчах через mcp-atlassian, но у официального MCP это `hasNextPage: false`. Не путай.

## Reference

- `scripts/merge_backlog.py` — merge с поддержкой дубликатов, плейсхолдеров, кириллицы, **SKIP-статусов** и **4 новых колонок (K/L/M/N)**. Помимо xlsx пишет `merge_stats.json` рядом с output (для render_page_storage и анализа).
- `scripts/distill_cab.py` — компактизация ответов JQL CAB → cab_issues.json + fi_keys.json. WORKDIR настраивается env-var `HR_BACKLOG_WORKDIR` (по умолчанию `cwd`).
- `scripts/distill_fi.py` — **обновлён 2026-05-27**: CLI = `--issues PATH ... [--changelogs PATH ...] [--output PATH]`. Парсит JQL FI + jira_batch_get_changelogs, заполняет `plan_test_date` (первая установка test_date при статусе «Запланирована») и `fact_done_date` (последний переход в «Выполнено»). Также читает `customfield_10311` из FI для plan_due_date.
- `scripts/render_page_storage.py` — собирает body Confluence-страницы (storage XHTML) из `merge_stats.json`: view-file макрос + параграф контекста (с описанием новых правил) + таблица «Сводка прогона» с разбивкой меток + блок про skipped + warning-блок для not-in-JQL. Base URL + space key для prev-page-ссылки настраиваются env-vars `CONFLUENCE_BASE_URL` + `CONFLUENCE_SPACE_KEY`.
- `merge_stats.json` (создаётся merge_backlog.py): `{today, cutoff_date, input, output, updated, added, labeled, skipped, skipped_status_breakdown: {Выполнено: N, Отмена: N, План: N}, label_breakdown: {placeholders, invalid_cyrillic, invalid_other, non_cr, cancelled_before, done_before, not_in_jql}, file_keys_not_in_jql: [...], cab_total, fi_total}`. Даты — ISO `YYYY-MM-DD`.

## Адаптация под вашу организацию

Этот скилл изначально написан под одну конкретную команду 1С ЗУП. Чтобы адаптировать:

1. **Замени плейсхолдеры на свои значения** при использовании:
   - `<cloudId>` — uuid Atlassian site, см. `getAccessibleAtlassianResources`
   - `<hr_backlog_parent_id>` — id parent-страницы в Confluence, где живут датированные бэклоги
   - `<your-site>.atlassian.net` — домен вашей Jira/Confluence
   - `<space_key>` — ключ пространства Confluence (например `PO`, `ENG`)
   - `<work_dir>` — локальная папка для кэша/output xlsx
   - `<atlassian-mcp-uuid>` — uuid инстанса официального Atlassian MCP в вашем `~/.claude.json`
2. **Сверь customfield IDs**. Поля `customfield_10293/10561/10311/10335/10363/10365/11944` специфичны для конкретного Jira-сайта. Сделай `mcp__mcp-atlassian__jira_search_fields` и проставь свои.
3. **JQL и filter «беклог = HR»** — у тебя в Jira это поле может называться иначе. Замени в запросе.
4. **Заголовок страницы Confluence** (`Беклог 1С ЗУП YYYY-MM-DD`) — поменяй под свою convention.

## Что нового в 2026-05-27

1. **SKIP-статусы**: задачи в статусах «Выполнено», «Отмена», «План» вообще не обновляются (ни data, ни даты, ни label).
2. **Новая раскладка колонок**: K=Фактическая дата выхода в тест, L=Плановая дата выхода в тест, M=Фактическая дата завершения, N=Плановая дата завершения, O=Дата обновления.
3. **Новый источник для plan_due (N)**: `customfield_10311` берётся из FI (раньше из CAB).
4. **Новые поля из changelog FI** (L и M): требуют `jira_batch_get_changelogs` для всех FI. Без этого L и M будут пустыми (но скрипт не упадёт).
5. **Data row сместился на 5**: row 4 теперь пустая строка-разделитель. SUBTOTAL формулы переехали на `G5:G<last>` и `I5:I<last>`.
