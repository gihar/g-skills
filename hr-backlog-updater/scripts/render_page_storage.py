"""Render Confluence page body (storage format) for a fresh HR-backlog run.

Reads merge_stats.json + a few cmdline args and prints storage XHTML to stdout.
The output is meant to be passed verbatim as `content` to
`confluence_create_page` (with content_format="storage").

The previous-page link uses CONFLUENCE_BASE_URL and CONFLUENCE_SPACE_KEY
environment variables (defaults: example.atlassian.net + SPACE). Set them
to your own Confluence site/space before running.

Usage:
  python render_page_storage.py \
    --stats merge_stats.json \
    --output-filename "Бэклог_1С_ЗУП_на_2026-05-27.xlsx" \
    --prev-page-id 6496485503 \
    --prev-date 2026-05-15 \
    > page.xhtml
"""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path


ROW = "<tr><td>{name}</td><td>{value}</td></tr>"

CONFLUENCE_BASE_URL = os.environ.get(
    "CONFLUENCE_BASE_URL", "https://example.atlassian.net",
).rstrip("/")
CONFLUENCE_SPACE_KEY = os.environ.get("CONFLUENCE_SPACE_KEY", "SPACE")


def render(
    stats: dict, output_filename: str, prev_page_id: str, prev_date: str,
) -> str:
    today = stats["today"]
    cutoff = stats["cutoff_date"]
    updated = stats["updated"]
    added = stats["added"]
    labeled = stats["labeled"]
    skipped = stats.get("skipped", 0)
    skipped_breakdown = stats.get("skipped_status_breakdown") or {}
    bd = stats["label_breakdown"]
    not_in_jql = stats.get("file_keys_not_in_jql") or []

    cab_total = stats.get("cab_total", "")
    fi_total = stats.get("fi_total", "")

    rows = [
        ROW.format(name="Дата прогона", value=today),
        ROW.format(name="Cutoff-дата", value=cutoff),
        ROW.format(name="Обновлено CAB-задач из JQL", value=updated),
        ROW.format(name="Добавлено новых строк", value=added),
        ROW.format(
            name="Пропущено (статусы Выполнено / Отмена / План)",
            value=skipped,
        ),
    ]
    for status_name, cnt in sorted(skipped_breakdown.items()):
        rows.append(ROW.format(
            name=f"&nbsp;&nbsp;— статус «{status_name}»",
            value=cnt,
        ))
    rows.extend([
        ROW.format(name="Помечено меткой (всего)", value=labeled),
        ROW.format(name="&nbsp;&nbsp;— плейсхолдеры («нет», «-», …)",
                   value=bd.get("placeholders", 0)),
        ROW.format(name="&nbsp;&nbsp;— выполнены до cutoff",
                   value=bd.get("done_before", 0)),
        ROW.format(name="&nbsp;&nbsp;— отменены до cutoff",
                   value=bd.get("cancelled_before", 0)),
        ROW.format(name="&nbsp;&nbsp;— не Change Request (Project/др.)",
                   value=bd.get("non_cr", 0)),
        ROW.format(name="&nbsp;&nbsp;— некорректный ключ (кириллица)",
                   value=bd.get("invalid_cyrillic", 0)),
        ROW.format(name="&nbsp;&nbsp;— некорректная запись",
                   value=bd.get("invalid_other", 0)),
        ROW.format(name="&nbsp;&nbsp;— не в JQL (требуют lookup)",
                   value=bd.get("not_in_jql", 0)),
        ROW.format(name="Всего CAB-задач в выгрузке", value=cab_total),
        ROW.format(name="Всего FI-задач обработано", value=fi_total),
    ])

    not_in_jql_block = ""
    if not_in_jql:
        keys = ", ".join(not_in_jql)
        not_in_jql_block = (
            f"<p><strong>Внимание:</strong> "
            f"требуют lookup’а: {keys}</p>"
        )

    prev_link = (
        f'<a href="{CONFLUENCE_BASE_URL}/wiki/spaces/'
        f'{CONFLUENCE_SPACE_KEY}/pages/{prev_page_id}">'
        f'страница {prev_date}</a>'
    )

    body = (
        f'<p class="media-group">'
        f'<ac:structured-macro ac:name="view-file" ac:schema-version="1">'
        f'<ac:parameter ac:name="name">'
        f'<ri:attachment ri:filename="{output_filename}" />'
        f'</ac:parameter>'
        f'</ac:structured-macro>'
        f'</p>'
        f'<p>Обновлённый бэклог 1С ЗУП на {today}. '
        f'Cutoff-дата: <strong>{cutoff}</strong>. '
        f'Источник предыдущей версии: {prev_link}.</p>'
        f'<p>В этом прогоне задачи в статусах <em>«Выполнено»</em>, '
        f'<em>«Отмена»</em> и <em>«План»</em> не обновлялись — '
        f'их данные в файле зафиксированы. '
        f'Новые колонки <em>«Плановая/Фактическая дата выхода в тест»</em> и '
        f'<em>«Плановая/Фактическая дата завершения»</em> '
        f'считаются из связанных FI-задач (поля <em>customfield_11944</em> и '
        f'<em>customfield_10311</em> + история переходов в статусы '
        f'«Запланирована» и «Выполнено»).</p>'
        f'<h2>Сводка прогона</h2>'
        f'<table><tbody>'
        f'<tr><th>Метрика</th><th>Значение</th></tr>'
        + "".join(rows)
        + f'</tbody></table>'
        + not_in_jql_block
    )
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", required=True, help="merge_stats.json path")
    ap.add_argument("--output-filename", required=True,
                    help="xlsx filename to embed via view-file macro")
    ap.add_argument("--prev-page-id", required=True,
                    help="ID of the previous backlog Confluence page")
    ap.add_argument("--prev-date", required=True,
                    help="ISO date of the previous backlog page (for link text)")
    args = ap.parse_args()

    stats = json.loads(Path(args.stats).read_text())
    print(render(stats, args.output_filename, args.prev_page_id, args.prev_date))


if __name__ == "__main__":
    main()
