# Public Telegram daily monitoring setup notes

Use this when converting the `chestny-znak-monitoring-report` skill from a private PDF/report flow into an automated public Telegram-channel post.

## Pattern

1. Create a dedicated Hermes cron job rather than reusing a private report job.
2. If the result is text-only, deliver directly to the Telegram channel target, preferably numeric channel id (`telegram:-100...`) rather than a username.
3. If the result includes both post text and PDF, do **not** rely on cron `MEDIA:` delivery: the scheduler strips `MEDIA:` and sends cleaned text first, then sends the PDF as a separate attachment. For a single Telegram message, set cron `deliver=local` and have the job publish the PDF itself via Telegram Bot API `sendDocument` with the post text as `caption`.
4. Use the packaged helper `scripts/telegram_send_document_caption.py` for the one-message PDF+caption case. If running from the installed skill, copy or install it to `/home/user/.hermes/scripts/telegram_send_document_caption.py` and make it executable:

```bash
cp /home/user/.hermes/skills/research/chestny-znak-monitoring-report/scripts/telegram_send_document_caption.py /home/user/.hermes/scripts/telegram_send_document_caption.py
chmod +x /home/user/.hermes/scripts/telegram_send_document_caption.py
/home/user/.hermes/scripts/telegram_send_document_caption.py \
  --chat-id @markirovka_pro \
  --file /home/user/.hermes/cache/documents/markirovka-pro-daily-YYYY-MM-DD.pdf \
  --caption-file /home/user/reports/chestny-znak/downstream/markirovka-pro-daily-YYYY-MM-DD.caption.html \
  --parse-mode HTML
```

5. Keep the caption short enough for Telegram document captions (target ≤950 characters; Bot API limit is 1024). Put detail in the PDF.
6. Use a self-contained cron prompt that says:
   - daily public monitoring post for `@markirovka_pro` or the relevant channel;
   - no personal header or `Подготовлено для: Алексей`;
   - post text and PDF must be one Telegram message when PDF is present;
   - clickable source names, no separate `источники` label;
   - still publish a short “no significant changes” post if the channel needs daily proof-of-work;
   - include the anti-miss normative control and full watchlist requirements from the main skill.
7. Convert local time to UTC in the cron expression. Example: `09:30 MSK` → `30 6 * * *`.
8. Set `enabled_toolsets` narrowly. For master/downstream: master needs `web`, `terminal`, `file`; downstream publisher needs only `terminal`, `file`.

## Verification checklist

- `cronjob(action="list")` shows the job enabled, expected schedule, and delivery mode.
- For a direct cron-delivered text-only post: target channel is set and `~/.hermes/logs/agent.log` contains a delivery confirmation like `delivered to telegram:<channel_id>`.
- For one-message PDF+caption publishing: cron `deliver` is `local`, the prompt calls `telegram_send_document_caption.py`, and the helper output includes `telegram_ok: true` plus `message_id`.
- Dry-run the helper after changes without publishing:

```bash
/home/user/.hermes/scripts/telegram_send_document_caption.py \
  --chat-id @markirovka_pro \
  --file /path/to/existing.pdf \
  --caption-file /path/to/caption.html \
  --parse-mode HTML \
  --dry-run
```

- If a PDF is included, it exists under `~/.hermes/cache/documents/` and `file` reports a non-empty PDF.
- If the task is tracked in GitHub, update the issue only after delivery is verified.

## Telegram channel access caveat

For public channels, `getChat(@username)` can resolve the channel while `getChatMember` may return `Bad Request: member list is inaccessible`. Treat that as inconclusive for admin rights. A successful `sendMessage`/cron delivery to the numeric channel id is the practical proof of publish access.
