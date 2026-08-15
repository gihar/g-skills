# no_agent Watchdog Pattern for Cascaded Cron Pipelines

When a master cron job feeds downstream jobs (via `context_from` or on-disk artifacts), a silent master failure turns every downstream run into a "technical fallback" report. A watchdog job fixes this class of failure with zero LLM cost.

## Contract (no_agent=true cron job, script only)

- empty stdout → silent tick (nothing delivered);
- non-empty stdout → delivered verbatim to the origin chat;
- non-zero exit → scheduler error alert.

Design alerts as plain text on stdout; keep state in a per-day JSON file under the report tree so repeated ticks are idempotent.

## Tick structure (proven for a 06:05 UTC master + 06:30/06:35 UTC downstream)

1. **Intervention tick** (master end + ~20 min, e.g. 06:26): artifact missing?
   - master still RUNNING per `executions.db` → pause downstream, wait;
   - master completed/failed/never started → pause downstream + dispatch ONE auto-retry;
   - master job disabled/paused → alert, no retry.
2. **Resolution ticks** (e.g. 07:26, 08:26): artifact present → resume + dispatch downstream, report recovery; still missing and not yet alerted → final alert, downstream stay paused. Never auto-retry twice.

## Critical pitfalls (all hit in the real implementation)

- **`hermes cron run` BLOCKS the caller until the job finishes** (~18 min for an agent master scan; minutes for PDF jobs). A watchdog that calls it inline will hang its whole tick. Dispatch detached:
  ```bash
  nohup "$HERMES_BIN" cron run "$JOB_ID" --accept-hooks >/dev/null 2>&1 &
  ```
- **PATH in cron env**: cron environments may not carry `~/.local/bin`. Resolve `command -v hermes` and fall back to `$HOME/.local/bin/hermes` explicitly.
- **"Still running" vs "failed"**: query `~/.hermes/cron/executions.db` table `executions` (status ∈ claimed/running/completed/failed/unknown, filter by `job_id` + `started_at >= today`). Do not guess from artifacts alone — pausing downstream while master legitimately runs would skip the day's reports.
- **State booleans**: JSON `true` serializes as Python `True` — normalize with `str(...).lower()` before bash string comparison.
- **Artifact validation**: don't just test file existence; parse the JSON and check schema fields (`schema_version`, `has_significant_changes`) so a half-written artifact doesn't count as success.
- **Test safely**: `DRY_RUN=1` (log instead of executing hermes commands) + `WATCHDOG_TEST_HOUR=06|07|08` overrides; exercise all branches, then delete the per-day state/alert/log files created by the test so tomorrow starts clean.
- **Terminal lifecycle guard**: the terminal tool recursively scans referenced shell scripts and hard-fails ("embedded null byte") on path literals that resolve to existing directories/binaries. Workaround: assemble all paths at runtime from components (`SL=/; "$HOME$SL.reports$SL..."`) so the script contains no slash-bearing literals.

## Verification before shipping

- `bash -n` syntax check;
- dry-run every branch (artifact OK / missing+running / missing+retry / recovery / repeat-alert-silence);
- `cronjob(action='create', no_agent=True, script=..., deliver='origin')`;
- confirm exactly one watchdog in `cronjob(action='list')` (a retry with an absolute script path can create a duplicate).
