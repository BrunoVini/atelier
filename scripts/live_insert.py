"""Insert mode anchor resolution for live mode.

Given a source file and an anchor description (id / classes / tag / text snippet),
find the line number of the anchor element so the agent knows WHERE to insert new
content before or after it. Returns a safe scaffold the agent uses to write net-new
variants ephemerally and persist the accepted one via edit_apply.

This intentionally does NO write — it only locates and describes the anchor. The
write happens at accept time through the existing live_accept / edit_apply flow.
"""
import json, os, re, sys


def _match_anchor(line, anchor):
    """Return True if `line` (raw HTML text) plausibly contains the anchor element."""
    hay = line.lower()
    if anchor.get("id"):
        if ('id="' + anchor["id"].lower() + '"') in hay:
            return True
        if ("id='" + anchor["id"].lower() + "'") in hay:
            return True
    if anchor.get("tag"):
        tag = anchor["tag"].lower()
        if ("<" + tag) in hay or ("<" + tag + " ") in hay or ("<" + tag + ">") in hay:
            if anchor.get("classes"):
                cls = anchor["classes"].lower()
                if cls in hay:
                    return True
            elif anchor.get("text"):
                if anchor["text"].lower()[:40] in hay:
                    return True
            else:
                return True
    if anchor.get("classes"):
        for cls in re.split(r'[\s,]+', anchor["classes"]):
            if cls and ('class="' in hay or "class='" in hay) and cls.lower() in hay:
                return True
    return False


def find_insert_anchor(file_path, anchor_desc):
    """Locate the anchor element in `file_path` that matches `anchor_desc`.

    anchor_desc: dict with optional keys: id, tag, classes, text
    Returns {ok, file, line, context} on success or {ok, reason} on failure.
    """
    if not os.path.isfile(file_path):
        return {"ok": False, "reason": f"file not found: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        return {"ok": False, "reason": str(e)}

    for i, line in enumerate(lines, 1):
        if _match_anchor(line, anchor_desc):
            # Return the 5 lines of context around the match for the agent.
            start = max(0, i - 3)
            end = min(len(lines), i + 2)
            context = "".join(lines[start:end])
            return {
                "ok": True,
                "file": file_path,
                "line": i,
                "context": context,
            }
    return {"ok": False, "reason": "anchor not found in file"}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Find insert anchor in source file")
    ap.add_argument("file")
    ap.add_argument("--anchor", required=True, help="JSON anchor desc {id?, tag?, classes?, text?}")
    ap.add_argument("--position", choices=("before", "after"), default="after")
    ns = ap.parse_args()
    result = find_insert_anchor(ns.file, json.loads(ns.anchor))
    if result.get("ok"):
        result["position"] = ns.position
    print(json.dumps(result))
