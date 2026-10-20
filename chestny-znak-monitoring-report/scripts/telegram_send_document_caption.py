#!/usr/bin/env python3
"""Send a Telegram document with the post text as the document caption.

Designed for Hermes cron jobs that must publish one Telegram message containing
both a PDF and its text. Loads token from environment or ~/.hermes/.env without
printing secrets.
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
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

try:
    import requests
except Exception as exc:  # pragma: no cover
    print(json.dumps({"ok": False, "error": f"requests import failed: {exc}"}, ensure_ascii=False))
    sys.exit(2)

TOKEN_KEYS = [
    "MARKIROVKA_PRO_BOT_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "HERMES_TELEGRAM_BOT_TOKEN",
    "BOT_TOKEN",
]
CAPTION_TARGET = 950  # Reserve space under Telegram's 1024-character limit.
ALLOWED_HTML_TAGS = {"b", "strong", "i", "em", "u", "s", "del", "code", "pre", "a"}
PUBLIC_LAYOUT = re.compile(
    r"\A<b>Маркировка · \d{2}\.\d{2}\.\d{4}</b>\n\n"
    r"<b>Что нового:</b> (?P<news>(?:(?!\n\n<b>).)+)\n\n"
    r"<b>Что сделать:</b> (?P<action>(?:(?!\n\n<b>).)+)"
    r"(?:\n\n<b>Ближайшие сроки:</b>\n(?P<deadlines>.+))?\Z",
    re.DOTALL,
)


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


def validate_caption(caption: str, parse_mode: str = "HTML") -> int:
    """Return visible UTF-16 units; reject malformed, unsafe or long captions.

    Never truncate HTML: it can split a tag or remove a legal caveat. XML
    parsing intentionally requires escaped ampersands in hrefs and body text.
    """
    caption = caption.strip()
    if not caption:
        raise ValueError("empty caption")
    if parse_mode == "HTML":
        if "<!" in caption or "<?" in caption:
            raise ValueError("HTML declarations/comments are not allowed")
        try:
            root = ET.fromstring(f"<caption>{caption}</caption>")
        except ET.ParseError as exc:
            raise ValueError(f"invalid HTML caption: {exc}") from exc
        for node in root.iter():
            if node is root:
                continue
            if node.tag not in ALLOWED_HTML_TAGS:
                raise ValueError(f"unsupported HTML tag: {node.tag}")
            if node.tag == "a":
                if set(node.attrib) != {"href"} or not "".join(node.itertext()).strip():
                    raise ValueError("link must have href and visible title")
                url = urlsplit(node.attrib["href"])
                if url.scheme not in ("http", "https") or not url.hostname or any(
                    c.isspace() for c in node.attrib["href"]
                ):
                    raise ValueError("link href must be an http(s) URL")
            elif node.attrib:
                raise ValueError(f"unexpected attributes on {node.tag}")
        visible = "".join(root.itertext())
    else:
        visible = caption
    length = len(visible.encode("utf-16-le")) // 2
    if length > CAPTION_TARGET:
        raise ValueError(f"caption too long: {length} visible characters (target {CAPTION_TARGET})")
    return length


def validate_public_layout(caption: str) -> None:
    match = PUBLIC_LAYOUT.fullmatch(caption.strip())
    if not match or any(not match.group(name).strip() for name in ("news", "action")):
        raise ValueError("public caption must use the dated headline and spaced Что нового/Что сделать[/Ближайшие сроки] blocks")
    deadlines = match.group("deadlines")
    if deadlines is not None and any(
        not line.startswith("• ") or not line[2:].strip()
        for line in deadlines.split("\n")
    ):
        raise ValueError("Ближайшие сроки must be a bullet list, one item per line")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat-id", required=True, help="Telegram chat/channel id, e.g. @markirovka_pro or -100...")
    ap.add_argument("--file", required=True, help="Path to PDF/document")
    ap.add_argument("--caption-file", required=True, help="UTF-8 file with post text/caption")
    ap.add_argument("--parse-mode", default="HTML", choices=["HTML", "MarkdownV2", "none"])
    ap.add_argument("--dry-run", action="store_true", help="Validate inputs only; do not send")
    ap.add_argument("--require-public-layout", action="store_true", help="Require the public monitoring post structure")
    args = ap.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    caption_path = Path(args.caption_file).expanduser().resolve()
    if not file_path.exists() or file_path.stat().st_size <= 0:
        raise RuntimeError(f"Document missing or empty: {file_path}")
    if not caption_path.exists() or caption_path.stat().st_size <= 0:
        raise RuntimeError(f"Caption file missing or empty: {caption_path}")

    caption_raw = caption_path.read_text(encoding="utf-8").strip()
    visible_len = validate_caption(caption_raw, args.parse_mode)
    if args.require_public_layout:
        if args.parse_mode != "HTML":
            raise ValueError("public layout requires HTML parse mode")
        validate_public_layout(caption_raw)

    result = {
        "ok": True,
        "dry_run": bool(args.dry_run),
        "chat_id": args.chat_id,
        "file": str(file_path),
        "file_size": file_path.stat().st_size,
        "caption_len_markup": len(caption_raw),
        "caption_len_visible": visible_len,
    }
    if args.dry_run:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    token_key, token = resolve_token()
    result["token_source"] = token_key

    url = f"https://api.telegram.org/bot{token}/sendDocument"
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    data = {
        "chat_id": args.chat_id,
        "caption": caption_raw,
    }
    if args.parse_mode != "none":
        data["parse_mode"] = args.parse_mode
    with file_path.open("rb") as fh:
        files = {"document": (file_path.name, fh, mime)}
        resp = requests.post(url, data=data, files=files, timeout=60)
    try:
        payload = resp.json()
    except Exception:
        payload = {"ok": False, "description": resp.text[:500]}
    if not resp.ok or not payload.get("ok"):
        print(json.dumps({**result, "ok": False, "http_status": resp.status_code, "telegram": payload}, ensure_ascii=False, indent=2))
        return 1
    message = payload.get("result", {})
    print(json.dumps({**result, "telegram_ok": True, "message_id": message.get("message_id")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
