# `context_from`: master result hidden by cron-output preamble

## Symptom

A downstream daily report says that `MASTER_MONITORING_RESULT` was not supplied even though the master job has `last_status=ok` and wrote valid JSON/Markdown artifacts.

## Cause

Hermes cron output files can contain the entire assembled skill/prompt before the final agent answer. The scheduler limits `context_from` to 8,000 characters from the **start** of the latest output. With a large loaded skill, the final `## Response` block containing `MASTER_MONITORING_RESULT` may therefore be omitted.

## Diagnose

1. Confirm master and downstream `last_status`, schedules, and `context_from` IDs.
2. Inspect the master output file and find `## Response` / `MASTER_MONITORING_RESULT` position relative to the 8K limit.
3. Validate the deterministic master artifact:
   - `/home/user/reports/chestny-znak/master/chestny-znak-master-YYYY-MM-DD.json`
   - require valid JSON plus `prepared_at` and monitoring period for the run date.
4. Distinguish a missing context injection from a missing master run; do not call the fallback a failed master when the artifact proves the master completed.

## Durable mitigation

Downstream prompts must retain `context_from` but include this recovery path:

- if the injected context lacks a complete, current-date `MASTER_MONITORING_RESULT`, read and validate the current-date master JSON artifact;
- use that fresh artifact as the sole factual source;
- perform no repeat web/legal collection;
- only issue a technical fallback when both injected result and validated artifact are unavailable.

## Scheduler-level fix

When maintaining Hermes source, extract the final content after the last `\n## Response\n` marker before applying the `context_from` size cap. Add a regression test with a >8K preamble and a compact final `MASTER_MONITORING_RESULT`.

After a source change, test `tests/cron/test_cron_context_from.py`. The running gateway must be restarted from an external shell for the changed scheduler module to be loaded; the downstream JSON fallback protects scheduled runs before that restart.
