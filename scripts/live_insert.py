"""Insert mode anchor resolution for live mode.

Given a source file and an anchor description (id / classes / tag / text snippet),
find the line number of the anchor element so the agent knows WHERE to insert new
content before or after it. Returns a safe scaffold the agent uses to write net-new
variants ephemerally and persist the accepted one via edit_apply.

This intentionally does NO write — it only locates and describes the anchor. The
write happens at accept time through the existing live_accept / edit_apply flow.
"""
import json, os, re, sys

# Mirror edit_apply's generated-file guards so insert_at_position refuses the same
# files that accept refuses.
_GENERATED_DIRS = {"node_modules", "dist", "build", ".next", "out", ".git",
                    "vendor", "coverage", ".cache", ".turbo", ".svelte-kit"}
_GENERATED_MARK = ("@generated", "DO NOT EDIT", "sourceMappingURL", "// prettier-ignore-start")


def _is_generated(path, text=None):
    """True if `path` looks like a file you must NOT hand-edit (build output,
    minified, vendored, or machine-generated). Mirrors edit_apply.is_generated."""
    parts = set(os.path.normpath(path).split(os.sep))
    if parts & _GENERATED_DIRS:
        return True
    base = os.path.basename(path).lower()
    if ".min." in base or base.endswith((".map", ".lock")):
        return True
    if text is None:
        try:
            if os.path.getsize(path) > 2_000_000:
                return True
            text = open(path, encoding="utf-8").read()
        except Exception:
            return True
    if any(mark in text for mark in _GENERATED_MARK):
        return True
    if any(len(line) > 5000 for line in text.splitlines()):    # minified
        return True
    return False


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
        # Fix: use two precise conditions instead of the superset ("<" + tag) which
        # would match <divwrapper> when looking for <div>.
        if ("<" + tag + " ") in hay or ("<" + tag + ">") in hay:
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


def find_insert_anchor(file_path, anchor_desc, position="after"):
    """Locate the anchor element in `file_path` that matches `anchor_desc`.

    anchor_desc: dict with optional keys: id, tag, classes, text
    position: one of 'before', 'after', 'first_child', 'last_child'
    Returns {ok, file, line, position, context} on success or {ok, reason} on failure.

    For first_child/last_child the returned `line` is the insert point:
      - first_child: the line AFTER the matched opening tag (insert before that line)
      - last_child:  the line of the matching closing tag (insert before that line)
    """
    if not os.path.isfile(file_path):
        return {"ok": False, "reason": f"file not found: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        return {"ok": False, "reason": str(e)}

    matches = [i for i, line in enumerate(lines, 1) if _match_anchor(line, anchor_desc)]

    if len(matches) == 0:
        return {"ok": False, "reason": "anchor not found in file"}
    if len(matches) > 1:
        return {"ok": False, "reason": f"anchor matches {len(matches)} lines, must be unique"}

    i = matches[0]  # 1-based line number of the anchor element

    # Compute the effective insert line based on position.
    if position in ("first_child", "last_child"):
        if position == "first_child":
            # Insert after the opening tag line — insert_line is i + 1 (1-based).
            insert_line = i + 1
        else:  # last_child
            # Find the closing tag that corresponds to the matched opening tag.
            # Heuristic: extract the tag name from the matched line and look for its
            # closing tag on a subsequent line.
            matched_line = lines[i - 1]
            tag_match = re.search(r'<([a-zA-Z][a-zA-Z0-9]*)', matched_line)
            tag_name = tag_match.group(1).lower() if tag_match else None
            close_line = None
            if tag_name:
                depth = 0
                for j in range(i - 1, len(lines)):
                    ll = lines[j].lower()
                    # Count opens (tags, not self-closing)
                    opens = len(re.findall(r'<' + re.escape(tag_name) + r'[\s>]', ll))
                    closes = len(re.findall(r'</' + re.escape(tag_name) + r'[\s>]', ll))
                    depth += opens - closes
                    if j > i - 1 and depth <= 0:
                        close_line = j + 1  # 1-based
                        break
            # Fall back: use the last line of the file as the insert point.
            insert_line = close_line if close_line is not None else len(lines) + 1
    else:
        insert_line = i  # for 'before'/'after' the insert_line is the anchor line itself

    # Return the 5 lines of context around the original match for the agent.
    start = max(0, i - 3)
    end = min(len(lines), i + 2)
    context = "".join(lines[start:end])
    return {
        "ok": True,
        "file": file_path,
        "line": insert_line,
        "anchor_line": i,
        "position": position,
        "context": context,
    }


def insert_at_position(file_path, anchor_desc, position, content):
    """Insert `content` into `file_path` at the position described by `anchor_desc`.

    Refuses generated/minified/vendored files (mirrors edit_apply).
    Returns {ok, line} on success or {ok, reason} on failure.
    """
    # Generated-file safety check (same guard as edit_apply.apply_edit).
    if _is_generated(file_path):
        return {"ok": False, "reason": "refusing to edit a generated/minified/vendored file"}

    result = find_insert_anchor(file_path, anchor_desc, position)
    if not result.get("ok"):
        return result

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        return {"ok": False, "reason": str(e)}

    insert_line = result["line"]  # 1-based; insert BEFORE this line
    anchor_line = result["anchor_line"]

    # For 'after', insert after the anchor line.
    if position == "after":
        insert_idx = anchor_line  # 0-based index after anchor_line
    else:
        # 'before', 'first_child', 'last_child': insert before insert_line (1-based).
        insert_idx = insert_line - 1

    new_line = content if content.endswith("\n") else content + "\n"
    lines.insert(insert_idx, new_line)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except OSError as e:
        return {"ok": False, "reason": str(e)}

    return {"ok": True, "line": insert_idx + 1}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Find insert anchor in source file")
    ap.add_argument("file")
    ap.add_argument("--anchor", required=True, help="JSON anchor desc {id?, tag?, classes?, text?}")
    ap.add_argument("--position", choices=("before", "after", "first_child", "last_child"),
                    default="after")
    ns = ap.parse_args()
    result = find_insert_anchor(ns.file, json.loads(ns.anchor), ns.position)
    print(json.dumps(result))
