---
name: cron-job-operations
description: Use when Hermes cron jobs fail or miss runs.
version: 1.0.0
metadata:
  hermes:
    tags: [cron, scheduled-jobs, triage, recovery, operations]
    related_skills: [hermes-agent, jira-release-digest-cron]
---

# Cron Job Operations: Triage, Rerun, Recovery

Use when the user says things like «запусти задачи, которые не выполнились», asks why scheduled jobs failed, or a cron job needs provider/model pinning after errors. Covers: finding what actually failed, verifying real results, rerunning, and durable fixes.

For creating/scheduling new jobs and delivery targets, see the bundled `hermes-agent` skill and `jira-release-digest-cron` (Jira-digest specifics). This skill is about operating jobs that misbehave.

## 1. Find out what actually failed

1. `cronjob(action='list')` — check `last_status`, `last_run_at`, `execution_success`, `execution_error` per job. Example terminal failure: `RuntimeError: HTTP 429: The usage limit has been reached`.
2. Metadata is not proof. Read the actual output: `~/.hermes/cron/output/<job_id>/<timestamp>.md` (newest file = latest run); the `## Response` section shows what the agent actually produced.
3. Check the expected artifact exists and is fresh: report file, master JSON, Telegram `message_id` in the response text, `[SILENT]` when nothing to report. `last_status: ok` does NOT guarantee success — an agent can burn its tool budget in a loop and finish "ok" with no artifact (real incident: 50 empty web_search calls hit the loop guardrail, run "succeeded", zero output).

## 2. Rerun

- `cronjob(action='run', job_id=...)` dispatches an immediate run. Independent jobs may be rerun in parallel; rerun master/collector jobs before downstream consumers.
- The `run` acknowledgment only means the run was dispatched. After completion, re-check the output file/artifact before telling the user it worked.

## 3. Pin provider/model when a provider hits usage limits (429)

jobs.json layout gotchas (`~/.hermes/cron/jobs.json`):
- Top level is a **dict**: `{"jobs": [...], "updated_at": ...}` — not a list.
- Each job's identifier field is `id`, NOT `job_id`.

Preferred path: `cronjob(action='update', job_id=..., model=..., provider=...)`. Observed quirk: an update carrying only model/provider can return `{"error": "No updates provided.", "success": false}`; including `name` in the same call made it apply.

Reliable fallback — edit jobs.json directly (always copy a backup first, e.g. `jobs.json.bak-<reason>`):

```python
import json
p = '/home/user/.hermes/cron/jobs.json'
data = json.load(open(p))
for j in data['jobs']:
    if j.get('id') == '<job_id>':
        j['provider'] = '<fallback_provider>'
        j['model'] = '<fallback_model>'
        j['provider_snapshot'] = '<fallback_provider>'
        j['model_snapshot'] = '<fallback_model>'
json.dump(data, open(p, 'w'), ensure_ascii=False, indent=2)
```

Set `provider_snapshot`/`model_snapshot` to the same values so the job record stays consistent. Re-verify the fallback provider is currently available instead of assuming yesterday's working pair is still valid.

### Switch a job back to the configured default model

When a job has a model/provider pin that is exhausted or unsuitable and the user asks for the **default model**, clear the complete pin rather than guessing a replacement:

1. Inspect `hermes config` to identify the configured global model/provider.
2. Back up `~/.hermes/cron/jobs.json`.
3. For the target record, set all of `model`, `provider`, `base_url`, `model_snapshot`, `provider_snapshot`, and `base_url_snapshot` to `null`.
4. Re-read via `cronjob(action='list')`; it must show `model: null`, `provider: null`, and `base_url: null`. That means the next run inherits the global configuration.
5. If downstream jobs were paused because their master failed: fix and verify the master artifact first, clear stale downstream pins too, `resume` the downstream jobs, then dispatch their immediate runs in parallel.

Do not claim recovery from the dispatch acknowledgement alone: wait for the completion event and verify both the job output and the expected artifact/delivery.

## 4. Reliability rules for cron prompts

- Deterministic primary source first: if a job needs external data, have the agent run a script/HTTP fetch via terminal before any search, so a search outage can't zero out the run.
- Anti-loop: instruct the agent to stop retrying `web_search` after 2 consecutive empty/failed calls and switch strategy (fallback search endpoint, direct source fetch, or record the limitation in the report). Otherwise it can hit the loop guardrail and produce nothing.
- Search-budget trap: `loop_web_search_cap` counts **all** `web_search` calls in the cron turn, including distinct successful queries. A planned batch of 50 useful searches can therefore halt the turn before artifact creation while the run is still recorded as `completed/ok`. Keep cron prompts below 30 searches, cap batches at 8, aggregate repetitive queries, reserve follow-up budget, and write a preliminary valid artifact before starting web search.
- If web_search is empty/quota/402, a known fallback in this deployment is a SearXNG instance queried with `format=json`, then `web_extract` on the found URLs (verify current availability before relying on it).

## Pitfalls

- Treating shell `exit_code=0` from `hermes cron run ...` as job success. It only means the CLI returned normally; always parse the final `Ran now: completed|failed` line and verify `hermes cron runs <id>` plus the artifact.
- Trusting `last_status: ok` or the `run` dispatch response as proof of success.
- Parsing jobs.json as a list or using `job_id` as the key field.
- Editing jobs.json without a backup.
- Declaring "all tasks recovered" without checking each job's actual output/artifact.

## Verification

- For every rerun job: newest file in `~/.hermes/cron/output/<job_id>/` contains a real `## Response` (not a guardrail/loop message) and the expected side effect (file, post, sync summary) is present.
- `cronjob(action='list')` shows `execution_success: true` and the pinned `provider`/`model`.
