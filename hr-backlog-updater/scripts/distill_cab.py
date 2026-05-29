"""Distill CAB issues from raw Jira responses into compact JSON.

Reads one or more raw Jira-search JSON responses from disk (the kind that
the official `searchJiraIssuesUsingJql` MCP saves to tool-results files when
the response is too big to inline) and produces two outputs in WORKDIR:

  - cab_issues.json — {CAB-XXXX: {summary, status_name, status_category,
      priority, issuetype, plan_zup, plan_e, plan_due, comment, customer,
      fi_keys, resolutiondate}}
  - fi_keys.json    — sorted list of unique FI-XXXX keys referenced via
      issuelinks on the CAB issues

WORKDIR is taken from the HR_BACKLOG_WORKDIR env var; defaults to the
current working directory.

Usage:
    python distill_cab.py <raw1.json> [<raw2.json> ...]
"""
import json
import os
import sys

WORKDIR = os.environ.get("HR_BACKLOG_WORKDIR", os.getcwd())
OUT = os.path.join(WORKDIR, "cab_issues.json")
OUT_FI = os.path.join(WORKDIR, "fi_keys.json")


def adf_to_text(node):
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(x) for x in node)
    if isinstance(node, dict):
        t = node.get("type", "")
        out = []
        if "text" in node:
            out.append(node["text"])
        if "content" in node:
            out.append(adf_to_text(node["content"]))
        if t in ("paragraph", "heading", "listItem", "blockquote", "codeBlock"):
            out.append("\n")
        elif t == "hardBreak":
            out.append("\n")
        return "".join(out)
    return ""


def extract_customer(field):
    if not field:
        return None
    if isinstance(field, dict):
        child = field.get("child")
        if isinstance(child, dict) and child.get("value"):
            return child["value"]
        if field.get("value"):
            return field["value"]
    elif isinstance(field, str):
        return field
    return None


def distill_one(it):
    f = it.get("fields") or it
    fi_keys = []
    for ln in f.get("issuelinks") or []:
        for side in ("inwardIssue", "outwardIssue", "inward_issue", "outward_issue"):
            ii = ln.get(side)
            if ii and ii.get("key", "").startswith("FI-"):
                fi_keys.append(ii["key"])
    status = f.get("status") or {}
    # official MCP uses statusCategory; mcp-atlassian uses category
    cat = status.get("statusCategory") or status.get("category")
    if isinstance(cat, dict):
        cat = (cat.get("key") or cat.get("name") or "").lower()
    elif isinstance(cat, str):
        cat = cat.lower()
    issuetype = f.get("issuetype") or f.get("issue_type") or {}

    return {
        "summary": f.get("summary", ""),
        "status_name": status.get("name", ""),
        "status_category": cat or "",
        "priority": (f.get("priority") or {}).get("name", ""),
        "issuetype": issuetype.get("name", ""),
        "plan_zup": f.get("customfield_10293"),
        "plan_e": f.get("customfield_10561"),
        "plan_due": f.get("customfield_10311"),
        "comment": adf_to_text(f.get("customfield_10335")).strip(),
        "customer": extract_customer(f.get("customfield_10363")),
        "fi_keys": sorted(set(fi_keys)),
        "resolutiondate": f.get("resolutiondate"),
    }


def main():
    out = {}
    for fp in sys.argv[1:]:
        with open(fp) as f:
            raw = f.read()
        try:
            outer = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(outer, dict) and set(outer.keys()) == {"result"}:
            inner = json.loads(outer["result"])
        else:
            inner = outer
        issues_raw = inner.get("issues", [])
        # official MCP (3c1b8184): {"issues": {"nodes": [...], "totalCount": N, ...}}
        # mcp-atlassian / legacy: {"issues": [...]}
        if isinstance(issues_raw, dict):
            issues = issues_raw.get("nodes") or issues_raw.get("issues") or []
        else:
            issues = issues_raw
        for it in issues:
            key = it.get("key")
            if key:
                out[key] = distill_one(it)
    with open(OUT, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    # also dump unique FI keys
    fi_keys = sorted({k for v in out.values() for k in v.get("fi_keys", [])})
    with open(OUT_FI, "w") as f:
        json.dump(fi_keys, f, ensure_ascii=False, indent=2)
    print(f"Distilled {len(out)} CAB issues -> {OUT}")
    print(f"Distilled {len(fi_keys)} unique FI keys -> {OUT_FI}")
    return out


if __name__ == "__main__":
    main()
