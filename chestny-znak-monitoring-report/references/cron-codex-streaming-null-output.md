# Cron/Codex streaming `response.output=None` diagnostic note

Use this reference when a `chestny-znak-monitoring-report` cron job fails almost immediately with:

```text
TypeError: 'NoneType' object is not iterable
RuntimeError: 'NoneType' object is not iterable
```

## Symptom pattern

- `cron.scheduler` starts the job and creates an OpenAI/Codex client.
- The failure occurs on the first model/API call, before meaningful report-generation tools run.
- Logs show provider/model similar to `openai-codex / gpt-5.5` and `agent.conversation_loop: API call failed ... TypeError ... NoneType ... not iterable`.
- Cron output contains only the expanded prompt/skill plus the error; no final PDF summary.

This points to the Codex/Responses streaming path receiving or constructing `response.output=None`, which the SDK may try to iterate.

## Investigation steps

1. List the job and note `job_id`, `last_run_at`, `last_status`, `enabled_toolsets`, and delivery target.
2. Search logs by `job_id` or cron session id, e.g. `cron_<job_id>_YYYYMMDD_...`.
3. Confirm whether the error happened before tool calls. If yes, do not spend time editing the report prompt or PDF conversion logic.
4. Ignore unrelated MCP warnings unless the job explicitly depends on that MCP. For this report job, `web`, `terminal`, and `file` are enough.

## Fix/recovery pattern

1. Ensure Hermes has the Codex streaming fallback that handles terminal `response.output=None` by recovering from streamed events or using the create-stream fallback.
2. If the gateway/cron process was running old code, restart/update Hermes so cron uses the fixed code path.
3. Trigger the job manually:

```bash
hermes cron run <job_id>
```

or via the cron tool:

```python
cronjob(action="run", job_id="<job_id>")
```

4. Wait for completion, then verify:
   - `last_status` changed to `ok`;
   - a fresh file exists under `~/.hermes/cron/output/<job_id>/`;
   - the final response contains the expected summary and `MEDIA:/home/user/.hermes/cache/documents/<report>.pdf`;
   - `file <pdf>` reports a PDF and `stat` shows non-zero size.

## Example verified recovery

A failed daily run at `2026-05-27 06:30 UTC` for `chestny-znak-daily-critical-watch` showed the `NoneType` Codex streaming error before any report work. After running on the updated Hermes process and triggering the job manually, the job completed successfully, delivered to Telegram, and created a valid non-empty PDF in `~/.hermes/cache/documents/`.
