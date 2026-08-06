#!/usr/bin/env python3
"""Send a Telegram document with post text as the document caption.

Use for public Telegram cron flows where text + PDF must be one Telegram
message. The script loads a bot token from env or ~/.hermes/.env and never
prints token values.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
import re
import sys
from typing import Dict, Tuple

import requests

TOKEN_KEYS = [
    "MARKIROVKA_PRO_BOT_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "HERMES_TELEGRAM_BOT_TOKEN",
    "BOT_TOKEN",
]
CAPTION_LIMIT = 1024


def load_env_file() -> Dict[str, str]:
    values: Dict[str, str] = {}
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            values[key] = value
    return values


def resolve_token() -> Tuple[str, str]:
    file_env = load_env_file()
    for key in TOKEN_KEYS:
        value = os.getenv(key) or file_env.get(key)
        if value:
            return key, value
    raise RuntimeError(f"No Telegram bot token found in any of: {', '.join(TOKEN_KEYS)}")


def truncate_caption(caption: str, limit: int = CAPTION_LIMIT) -> str:
    caption = caption.strip()
    if len(caption) <= limit:
        return caption
    suffix = "\n\nПодробнее — в PDF."
    keep = max(0, limit - len(suffix) - 1)
    return caption[:keep].rstrip() + suffix


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True, help="Telegram chat/channel id, e.g. @markirovka_pro or -100...")
    ap.add_argument("--file", required=True, help="Path to PDF/document")
    ap.add_argument("--caption-file", required=True, help="UTF-8 file with post text/caption")
    ap.add_argument("--parse-mode", default="HTML", choices=["HTML", "MarkdownV2", "none"])
    ap.add_argument("--dry-run", action="store_true", help="Validate inputs only; do not send")
    args = ap.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    caption_path = Path(args.caption_file).expanduser().resolve()
    if not file_path.exists() or file_path.stat().st_size <= 0:
        raise RuntimeError(f"Document missing or empty: {file_path}")
    if not caption_path.exists() or caption_path.stat().st_size <= 0:
        raise RuntimeError(f"Caption file missing or empty: {caption_path}")

    caption_raw = caption_path.read_text(encoding="utf-8").strip()
    caption = truncate_caption(caption_raw)
    token_key, token = resolve_token()

    result = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "chat_id": args.chat_id,
        "file": str(file_path),
        "file_size": file_path.stat().st_size,
        "caption_len_original": len(caption_raw),
        "caption_len_sent": len(caption),
        "caption_truncated": len(caption_raw) > len(caption),
        "token_source": token_key,
    }
    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    data = {"chat_id": args.chat_id, "caption": caption}
    if args.parse_mode != "none":
        data["parse_mode"] = args.parse_mode
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    with file_path.open("rb") as fh:
        resp = requests.post(url, data=data, files={"document": (file_path.name, fh, mime)}, timeout=60)
    try:
        payload = resp.json()
    except Exception:
        payload = {"ok": False, "description": resp.text[:500]}
    if not resp.ok or not payload.get("ok"):
        print(json.dumps({**result, "ok": False, "http_status": resp.status_code, "telegram": payload}, ensure_ascii=False, indent=2))
        return 1
    msg = payload.get("result", {})
    print(json.dumps({**result, "telegram_ok": True, "message_id": msg.get("message_id")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
