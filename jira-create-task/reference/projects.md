# Project reference — detmir.atlassian.net

Snapshot of 2026-08-30, verified against `jira_get_project_issue_types`, `jira_get_create_fields`, `jira_get_field_options`, `jira_get_link_types`. Field IDs and option lists are cached here because they are stable and expensive to re-derive per run; when a creation error names a field missing here, trust the error and update this file.

## Summary naming

| Project | Pattern | Example |
|---|---|---|
| OPER | `OPER_<текст>` | `OPER_Новый алгоритм расчета парсинговой цены по собственным товарам` |
| EWM | `EWM_<текст>`; issues of type ОПЭ — `ОПЭ_<объект>` | `EWM_Запрет создания задач на комплектование товара с ссылками на ДКК`, `ОПЭ_РЦ Урал` |
| CAB | plain text, no prefix | `Новый алгоритм расчета парсинговой цены по собственным товарам` |

## OPER (Отдел операционных приложений) and EWM (Отдел складских приложений)

Identical create schemas.

Issue types: Business task `10472`, Internal task `10473`, Bug `10103`, ОПЭ `12022`, Проектное решение `10514`, Epic `10000`, Sub-task `10102`; testing types Тест, РТ, ИТ, ФТ.

Required at creation:
- **Беклог** — `customfield_10362`, multi-select → `[{"value": "…"}]`
- **Номер CAB** — `customfield_10365`, text → the linked CAB key

On the create screen and worth filling when the user mentions them: `priority`, `labels`, `components`, `parent`, Плановая дата завершения задачи `customfield_10311` (date), Объект блокировки `customfield_10587` (multi-select, 15+ values — long-list rule), Sprint `customfield_10115`. There is no `duedate` here — a deadline goes into `customfield_10311`.

Canonical split pair: ERP work → OPER, warehouse work → EWM, both blocking the same CAB issue with the same Беклог and Номер CAB.

## CAB

Issue types: Change Request `10471`, Defect `10529`, Project `10470`, Epic `10000`.

Required at creation — metadata reports only Беклог as required; the other two surface as «Заполните поле …» on create:
- **Беклог** — `customfield_10362`, multi-select
- **Подразделение заказчика** — `customfield_10324`, select → `{"value": "…"}`
- **Заказчик** — `customfield_10363`, cascading: parent = подразделение, child = ФИО → `{"value": "Коммерческая дирекция ТНП", "child": {"value": "Какуркина Эльвира Курбановна"}}`

Also on the create screen: `duedate`, `priority`, `labels`, Epic Link `customfield_10005`, Продуктовое направление `customfield_10673` (select), Контрагент `customfield_10301` (multi-select).

A CAB issue never blocks another CAB issue — the blocking task lives in OPER / EWM / another delivery project.

## Беклог — allowed values (shared by CAB, OPER, EWM)

14 values; the strings are exact, commas included:

`BackOffice` · `CHEAP` · `E-com, Цифровые сервисы` · `ГИС` · `ДИТ, 2,5` · `ДЛ + TMS+СИ + ДУТЗ` · `Маркетинг, МП, КД` · `ОД+Зоо` · `ФД, КБ` · `HR` · `Lassie` · `Маркетинг` · `Маркетплейс` · `Коммерция`

Refresh: `jira_get_field_options(field_id: "customfield_10362", values_only: true)`.

## Issue links

`jira_create_issue_link(link_type, inward_issue_key, outward_issue_key)`. Observed on OPER-18609 / OPER-18629 / EWM-6311: with `inward_issue_key` = the new task and `outward_issue_key` = the CAB issue, the new task lists the CAB key as `outward_issue` and displays «blocks CAB-…»; the CAB issue displays «is blocked by …». Keep that orientation for «задача блокирует CAB».

| link_type | outward description | inward description | user phrasing |
|---|---|---|---|
| `Blocks` | blocks | is blocked by | блокирует |
| `Relates` | relates to | relates to | связано с |
| `Duplicate` | duplicates | is duplicated by | дубликат |
| `Финансирование` | финансирует | финансируется из | финансируется из |
| `Problem/Incident` | causes | is caused by | вызвано |
| `Issue split` | split to | split from | выделено из |

## Users

`jira_search_assignable_users(query, project_key)` resolves Cyrillic names («Хабленко» → `dhablenko@detmir.ru`, `account_id`). `jira_assign_issue(issue_key, assignee: "<email>")` is the reliable assignment path — `jira_get_user_profile` and create-time `assignee` are the ones that used to fail on this instance.
