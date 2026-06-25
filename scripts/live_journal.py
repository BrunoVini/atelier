"""Session-level append-only JSONL journal for live mode.

One .jsonl file per session under journal_dir. Each line is a JSON object
with at minimum: {type, ts, session}. The journal is the recovery source of
truth — if the proxy restarts, live_status.py reads it to reconstruct state.
"""
import json
import os
import time


def _path(journal_dir, session_id):
    safe_id = "".join(c if c.isalnum() or c in '-_.' else '_' for c in str(session_id))
    return os.path.join(journal_dir, "session-" + safe_id + ".jsonl")


def write_entry(journal_dir, session_id, entry_type, data):
    """Append one entry to the session journal. Creates journal_dir if needed."""
    os.makedirs(journal_dir, exist_ok=True)
    entry = {"type": str(entry_type), "ts": time.time(),
             "session": str(session_id)}
    entry.update(data)
    with open(_path(journal_dir, session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_entries(journal_dir, session_id):
    """Return all journal entries for session_id. Returns [] if not found."""
    p = _path(journal_dir, session_id)
    if not os.path.exists(p):
        return []
    entries = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def session_state(journal_dir, session_id):
    """Derive session state from journal. Returns a state dict."""
    entries = read_entries(journal_dir, session_id)
    state = {
        "session": session_id,
        "accepts": [],
        "reverts": [],
        "steers": [],
        "status": "active",
    }
    for e in entries:
        t = e.get("type")
        if t == "accept":
            state["accepts"].append(e)
        elif t == "revert":
            state["reverts"].append(e)
        elif t == "steer":
            state["steers"].append(e)
        elif t == "exit":
            state["status"] = "exited"
    return state
