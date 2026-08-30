---
name: jira-create-task
description: Use when the user asks to create a Jira issue, task, bug, or story. Triggers on "создай задачу", "create task", "заведи баг", "create issue in Jira", "согласуй описание перед созданием", or when user provides task information expecting a Jira issue to be created.
---

# Jira Task Creation

Turn free-form input into one or more well-formed Jira issues. Every call goes through `mcp-atlassian` (`jira_*` tools); the single exception is the rendered-HTML check in step 9, which only `claude_ai_Atlassian.getJiraIssue` provides.

Project conventions, field IDs, option lists and link semantics live in [reference/projects.md](reference/projects.md) — open it in steps 3, 5 and 8.

## Rules

- **Questions go through `AskUserQuestion`**, 1–3 questions per call. After each call check that every answer came back; re-ask any empty one on its own.
- **Parallelize** independent calls: bootstrap lookups, creation of several issues, post-creation assign / attach / link.
- **Defaults**: project `CAB` when none is given. Issue type and assignee are asked, never inferred. «без исполнителя / не назначать / оставить пустым / unassigned» = assignee None — record it and skip the question.
- **Description is Markdown.** The MCP converts it to Wiki (`##` → `h2.`, `**b**` → `*b*`, `` `x` `` → `{{x}}`). Headings, bullets, numbered lists and bold render fine. File paths, UNC paths, code and punctuation-heavy strings go in **fenced code blocks** — the only construct that reaches Jira byte-exact (inline `{{…}}` consumes `\!` and `\#`; seen on CAB-10892). Tables arrive as plain text — use bullets with bold labels. Hand-written Wiki (`h2.`, `{noformat}`, `{code}`) is mangled by the converter.
- **Attachments only from `~/Assistant`.** Any other path — Downloads, the scratchpad — is rejected with «Path traversal detected». Copy the file into `~/Assistant/jira-attachments/`, attach, then delete the copy.

## Steps

### 1. Parse the request

| Extract | Goes to |
|---|---|
| Project key or alias (`склад / WMS` → EWM, `ОД / операционные` → OPER; otherwise `jira_get_all_projects` + fuzzy match by name, shortlist when ambiguous) | `project_key` |
| Issue type, assignee | asked when absent |
| Priority, labels, components, due date, parent / epic | native fields — never description text |
| Issue links («блокирует CAB-…», «связано с …») | step 8 |
| Local files, attached images | read in step 2, attached in step 8 |
| Everything else | material for summary and description |

**Split check.** Work spanning 2+ systems (ERP+EWM, web+mobile, API+UI, several integrations) → ask «разбить на N задач?» before drafting anything; for the well-known pairs the split is the first, recommended option. When the user already listed the tasks, proceed with N.

**CAB never blocks CAB.** A task that blocks or is linked to a CAB issue lives in another project — ask which, with CAB left out of the options.

### 2. Bootstrap (parallel)

- `jira_get_project_issue_types(project_key)` → match the user's type by name, keep its `id`.
- `jira_search_assignable_users(query, project_key)` → `email` + `account_id`; handles Cyrillic names. Several matches → ask. Skipped when unassigned.
- `jira_get_issue(<linked CAB key>, fields: "summary,issuetype,status,customfield_10362")` → confirms the link target exists; its summary and Беклог seed the defaults in step 3.
- Read every attached file — field names, error texts and data samples from files belong in the description.

### 3. Required fields

`jira_get_create_fields(project_key, issue_type_id)` → every `required: true` field the user did not supply, **plus** the fields the reference marks as required-at-creation (metadata omits them). Prefill from context — Номер CAB = linked CAB key, Беклог = linked CAB's Беклог — and ask for the rest.

- **Long list (>4 options):** the full option list goes into the question text; `options` holds the 4 most likely, top one marked `(Recommended)`; built-in «Other» covers the rest.
- **Free-text answer:** match case-insensitively against the allowed values — unique prefix/substring → use it and echo the resolved value in step 6; several → ask; none → re-ask with the full list.
- **Split tasks:** shared fields (Беклог, Номер CAB, priority, link target …) are asked once — «…для всех задач?» — and copied to every task.

Field JSON: select `{"value": "X"}` · multi-select `[{"value": "X"}]` · cascading `{"value": "Parent", "child": {"value": "Child"}}` · user `{"accountId": "…"}` · date `"YYYY-MM-DD"` · priority `{"name": "High"}` · parent `"KEY-1"`.

### 4. Duplicate check

`jira_search(jql: 'project = <KEY> AND summary ~ "<2–3 key words>" AND created >= -90d', limit: 5)`. Similar issues are shown in the step-6 preview with links; the user decides.

### 5. Draft summary and description

- **Summary**: 5–15 words, outcome first, the user's language, project prefix per the reference (`OPER_…`, `EWM_…`, CAB without prefix).
- **Description**: the user's material under headings — context → what to do → scope → source data → open questions — with every technical detail preserved, formatted per the Markdown rule above.

### 6. Confirm

One consolidated preview per task: project, type, summary, assignee, custom fields, links, attachments, possible duplicates. Include the full description when the user asked to review it («согласуй», «покажи описание», «review before create»). A Markdown table when ≥2 tasks (tables are fine in chat). Then `AskUserQuestion`: `Создаём` / `Нужны правки`; edits → revise → confirm again.

Skipped only on an explicit opt-out («создавай без подтверждения»).

### 7. Create

```
jira_create_issue(project_key, summary, issue_type: "<name>", description: "<Markdown>",
  components: "A,B",
  additional_fields: '{"customfield_10362": [{"value": "…"}], "customfield_10365": "CAB-…",
                       "priority": {"name": "…"}, "labels": […], "parent": "KEY-1"}')
```

Assignee is set in step 8. Several tasks → parallel calls.

**«Заполните поле X, Y»** is the expected failure: `jira_search_fields("X")` → `jira_get_field_options(field_id)` → ask (long-list rule) → retry with everything. The error message is the ground truth for required fields; add the field to the reference afterwards.

### 8. Assign, attach, link (parallel, all tasks in one batch)

- `jira_assign_issue(issue_key, assignee: "<email>")` — the dedicated endpoint; skipped when unassigned.
- `jira_update_issue(issue_key, fields: "{}", attachments: "<paths under ~/Assistant/jira-attachments>")`, then delete the copies. One file for several tasks → attach to each.
- `jira_create_issue_link(link_type: "Blocks", inward_issue_key: "<new task>", outward_issue_key: "<CAB key>")` → the new task shows «blocks CAB-…». Confirm with `jira_get_issue(key, fields: "issuelinks")`: the CAB key must appear as `outward_issue`. Other link types in the reference.

### 9. Verify rendering

When the description carries paths, code or `!` / `#` / `\`: `claude_ai_Atlassian.getJiraIssue(cloudId, key, expand: "renderedFields")` (`cloudId` from `getAccessibleAtlassianResources()`). That HTML is what Jira displays; every `jira_get_issue` variant re-converts on read and cannot show this. Anything mangled → fix via `jira_update_issue`.

### 10. Report

Per task: key as link (`https://detmir.atlassian.net/browse/KEY`), summary, type, assignee, custom fields set, links, attachments, rendering-check result. Table when ≥2 tasks.

## Failure modes

- Assignee not found → ask for email or full name; «без исполнителя» is a valid answer.
- Attachment failed → the issue already exists; report the key and the files to attach by hand.
- Permission denied → report; suggest checking project access.
- `AskUserQuestion` returned fewer answers than questions → re-ask the missing ones one at a time.
