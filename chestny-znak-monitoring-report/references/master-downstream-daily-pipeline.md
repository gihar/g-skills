# Master/downstream daily monitoring pipeline

Use this pattern when the same daily Chestny ZNAK monitoring facts need multiple outputs, e.g. a public Telegram post and an internal PDF.

## Pattern

1. Create one **master** cron job that does all web/legal/source collection and normalization.
2. Deliver the master job to `local` only.
3. Make downstream jobs depend on the master via `context_from: [<master_job_id>]`.
4. Downstream jobs must not repeat `web_search`/`web_extract`; they should transform the injected `MASTER_MONITORING_RESULT` into audience-specific output.
5. Stagger schedules so the master finishes before downstream jobs run.

## Example schedule

- `09:05 MSK` — master scan, `deliver=local`, toolsets `web,terminal,file`.
- `09:30 MSK` — public Telegram post, `context_from=<master>`, toolsets `terminal,file`.
- `09:35 MSK` — internal PDF, `context_from=<master>`, toolsets `terminal,file`.

Cron expressions are UTC in Hermes output, so MSK = UTC+3:

- `5 6 * * *` → 09:05 MSK.
- `30 6 * * *` → 09:30 MSK.
- `35 6 * * *` → 09:35 MSK.

## Master output contract

The master final response should be stable and machine-readable enough for downstream jobs:

```text
MASTER_MONITORING_RESULT YYYY-MM-DD

period: ...
has_significant_changes: true/false
critical:
important:
medium:
expected_events_6m:
checked_sources:
limitations:
artifacts:
```

Also save artifacts under a deterministic directory, e.g.:

```text
/home/user/reports/chestny-znak/master/chestny-znak-master-YYYY-MM-DD.json
/home/user/reports/chestny-znak/master/chestny-znak-master-YYYY-MM-DD.md
```

## Downstream prompts

Downstream prompts should explicitly say:

- Use the injected `MASTER_MONITORING_RESULT` as the single source of facts.
- Do not recollect normative data if the master result is fresh.
- If the master result is missing/stale, report the monitoring error rather than inventing facts.
- Keep public output free of internal logs, tool details, and personal address lines.

## File naming

Use distinct filenames per audience to avoid collisions:

- Public channel PDF: `markirovka-pro-daily-YYYY-MM-DD.pdf`.
- Internal PDF: `chestny-znak-internal-daily-YYYY-MM-DD.pdf`.
- Master artifacts: `chestny-znak-master-YYYY-MM-DD.{json,md}`.

## Verification

After updating cron jobs:

1. Re-list jobs and verify schedules, delivery targets, and `context_from`.
2. Inspect `~/.hermes/cron/jobs.json` if the listing omits `context_from`.
3. Run only the master first to avoid duplicate public posts.
4. Verify master output exists and contains `MASTER_MONITORING_RESULT`.
5. Let downstream jobs run on schedule unless the user explicitly asks for a live publication test.
