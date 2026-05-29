"""Distill FI issues from raw Jira responses + changelogs into compact JSON.

Inputs:
  --issues PATH ...      raw JQL batch JSON files (from the official Jira
                         `searchJiraIssuesUsingJql` MCP)
  --changelogs PATH ...  raw `jira_batch_get_changelogs` JSON files
                         (from mcp-atlassian)
  --output PATH          default: fi_issues.json in the current directory.
                         Override with --output to put it elsewhere.

Output JSON shape (one entry per FI key):
  {
    "FI-XXXX": {
      "fact_test_date": ISO|None,    # current customfield_11944 (last value)
      "plan_test_date": ISO|None,    # first time test_date was set
                                     #   while status was Запланирована
      "fact_done_date": ISO|None,    # last transition to "Выполнено"
                                     #   from changelog
      "plan_due_date":  ISO|None,    # current customfield_10311
      "cab":            "CAB-..."|None,
      "status_name":    str,
      "status_category": "done"|"new"|"indeterminate"|"",
      "resolutiondate": ISO|None,
    }, ...
  }
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_OUT = "fi_issues.json"

PLANNED_STATUSES = {"Запланирована", "Запланировано", "Новый"}
DONE_STATUS = "Выполнено"
TEST_DATE_FIELD_NAME = "Дата выхода на тест"

# If True: any first set of test_date (regardless of status) counts as
# plan_test_date. Fallback for FI workflows where "Запланирована" never
# appears (most common: статус Новый).
PLAN_TEST_FALLBACK_TO_FIRST_SET = True


def _extract_issues(node):
    """Pull issues list from either {issues: [...]} or {issues: {nodes: [...]}}."""
    if not isinstance(node, dict):
        return []
    issues = node.get("issues")
    if isinstance(issues, list):
        return issues
    if isinstance(issues, dict):
        return issues.get("nodes") or issues.get("issues") or []
    return []


def _unwrap_result(data):
    """If data is {result: <json-string>}, parse the inner JSON."""
    if (
        isinstance(data, dict)
        and set(data.keys()) == {"result"}
        and isinstance(data["result"], str)
    ):
        try:
            return json.loads(data["result"])
        except json.JSONDecodeError:
            return data
    return data


def load_issues_from_file(fp):
    with open(fp) as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    data = _unwrap_result(data)
    if isinstance(data, dict) and "issues" in data:
        return _extract_issues(data)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    inner = json.loads(item["text"])
                    inner = _unwrap_result(inner)
                    if isinstance(inner, dict):
                        return _extract_issues(inner)
                except json.JSONDecodeError:
                    continue
    return []


def load_changelogs_from_file(fp):
    """Returns list of {issue_id: str, changelogs: list}."""
    with open(fp) as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    data = _unwrap_result(data)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def extract_value(v):
    """Pull string value from raw field — handles dict {value: '...'} or
    string-or-None."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        val = v.get("value")
        if isinstance(val, str):
            return val
    return None


def extract_date(v):
    s = extract_value(v)
    if not s:
        return None
    return s[:10] if len(s) >= 10 else s


def distill_issue(it):
    f = it.get("fields") or it
    status = f.get("status") or {}
    cat = status.get("statusCategory") or status.get("category")
    if isinstance(cat, dict):
        cat = (cat.get("key") or cat.get("name") or "").lower()
    elif isinstance(cat, str):
        cat = cat.lower()
    return {
        "_id": str(it.get("id") or ""),
        "fact_test_date": extract_date(f.get("customfield_11944")),
        "plan_due_date":  extract_date(f.get("customfield_10311")),
        "cab":            extract_value(f.get("customfield_10365")),
        "status_name":    status.get("name", ""),
        "status_category": cat or "",
        "resolutiondate": f.get("resolutiondate"),
        "plan_test_date": None,  # filled from changelog
        "fact_done_date": None,  # filled from changelog
    }


def process_changelog(changelogs):
    """Walk changelog chronologically. Return (plan_test_date, fact_done_date).

    plan_test_date:
      - PRIMARY: first set of test_date while status in PLANNED_STATUSES
        (Запланирована / Запланировано / Новый — common workflows).
      - FALLBACK: if PRIMARY misses, take the very first set of test_date
        regardless of status (controlled by
        PLAN_TEST_FALLBACK_TO_FIRST_SET).
    fact_done_date:
      - LAST transition to status="Выполнено".
    """
    items = []
    for cl in changelogs or []:
        created = cl.get("created")
        for it in cl.get("items") or []:
            items.append({"created": created, **it})
    items.sort(key=lambda x: x.get("created") or "")

    plan_test_date = None
    plan_test_fallback = None  # very first test_date set, any status
    fact_done_date = None

    # Seed initial status from first status item's from_string
    # (best guess of pre-history).
    current_status = None
    for it in items:
        if it.get("field") == "status" and it.get("from_string"):
            current_status = it["from_string"]
            break

    for it in items:
        field = it.get("field")
        created = it.get("created") or ""
        if field == "status":
            new_status = it.get("to_string") or ""
            current_status = new_status
            if new_status == DONE_STATUS:
                # last transition wins; overwrite as we walk forward
                fact_done_date = created[:10] if created else fact_done_date
        elif field == TEST_DATE_FIELD_NAME:
            to_id = it.get("to_id") or it.get("to_string")
            if to_id:
                date_norm = to_id[:10] if len(to_id) >= 10 else to_id
                if plan_test_fallback is None:
                    plan_test_fallback = date_norm
                if current_status in PLANNED_STATUSES and plan_test_date is None:
                    plan_test_date = date_norm

    if plan_test_date is None and PLAN_TEST_FALLBACK_TO_FIRST_SET:
        plan_test_date = plan_test_fallback
    return plan_test_date, fact_done_date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--issues", nargs="+", required=True,
        help="JQL FI batch JSON files",
    )
    ap.add_argument(
        "--changelogs", nargs="*", default=[],
        help="changelog batch JSON files",
    )
    ap.add_argument("--output", default=DEFAULT_OUT)
    args = ap.parse_args()

    out = {}
    id_to_key: dict[str, str] = {}

    for fp in args.issues:
        for it in load_issues_from_file(fp):
            key = it.get("key")
            if not key:
                continue
            entry = distill_issue(it)
            out[key] = entry
            if entry["_id"]:
                id_to_key[entry["_id"]] = key

    cl_matched = 0
    for fp in args.changelogs:
        for batch_entry in load_changelogs_from_file(fp):
            issue_id = str(batch_entry.get("issue_id") or "")
            key = id_to_key.get(issue_id)
            if not key or key not in out:
                continue
            plan_test, fact_done = process_changelog(
                batch_entry.get("changelogs"),
            )
            if plan_test:
                out[key]["plan_test_date"] = plan_test
            if fact_done:
                out[key]["fact_done_date"] = fact_done
            cl_matched += 1

    # Strip internal _id from output payload
    for v in out.values():
        v.pop("_id", None)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(
        f"Distilled {len(out)} FI issues -> {args.output}; "
        f"changelogs matched={cl_matched}"
    )


if __name__ == "__main__":
    main()
