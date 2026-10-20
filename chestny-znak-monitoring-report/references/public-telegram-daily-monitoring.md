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
  --parse-mode HTML --require-public-layout
```

5. The helper **rejects**, never truncates, malformed HTML and captions exceeding 950 visible UTF-16 characters after HTML entity parsing (Telegram limit: 1024). With `--require-public-layout`, it also checks the dated bold headline and spaced **Что нового / Что сделать / [Ближайшие сроки]** blocks. If the deadline block is present, its header must be on a separate line, followed by one `• ` bullet per deadline; no single inline paragraph or semicolon-joined list. It requires named, nonempty HTTP(S) links and escaped `&amp;` in link URLs/text; `--dry-run` validates without token access or publishing. If validation fails, shorten/edit the caption semantically and retry; do not discard legal caveats.
6. Use a self-contained cron prompt for `@markirovka_pro`: one PDF + HTML caption, no personal header. Mobile-friendly structure with blank lines: `<b>Маркировка · DD.MM.YYYY</b>`, `<b>Что нового:</b>` (main confirmed signal first, including effective dates of new norms; or one concise no-change line), `<b>Что сделать:</b>` (specific action), and optional `<b>Ближайшие сроки:</b>` on its own line, followed by one `• DD.MM — group · action · <a href="https://...">act</a>` line per distinct deadline (even if several groups share the date; literal bullet characters, not HTML `<ul>`). No fixed one-deadline limit: show all new critical dates of the day if they fit the caption; usually 1–2 routine dates suffice. If critical dates cannot fit despite semantic compression, name the most urgent and explicitly point to the remaining urgent dates in the attached PDF. Never recycle a long list of old deadlines every day. Mark statuses next to each claim: `Принято`, `Проект — не действует`, `Сбой — статус уточняется`; no global confidence statement. Place a named clickable `<a href="https://...">акт/публикация</a>` beside each significant claim, not in a trailing links section. Never present a `requires_recheck=true` date as current without independent legal re-verification. When no confirmed changes are found but official news coverage is partial for both Честный ЗНАК and Минпромторг, write in the public «Что нового» block: «Среди проверенных публикаций новых подтверждённых изменений за сутки не выявлено. Публикации „Честного ЗНАКа“ и Минпромторга могли быть охвачены не полностью». Name only the affected outlet if just one was incomplete. Never assert unconditionally that there were no changes. This caveat concerns discovery of additional news, not the reliability of separately verified acts or deadlines. The sender validates layout and length, not factual coverage. Keep the normative-control process in the master task; downstream does not search again.
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
  --parse-mode HTML --require-public-layout \
  --dry-run
```

- If a PDF is included, it exists under `~/.hermes/cache/documents/` and `file` reports a non-empty PDF.
- If the task is tracked in GitHub, update the issue only after delivery is verified.

## Telegram channel access caveat

For public channels, `getChat(@username)` can resolve the channel while `getChatMember` may return `Bad Request: member list is inaccessible`. Treat that as inconclusive for admin rights. A successful `sendMessage`/cron delivery to the numeric channel id is the practical proof of publish access.
