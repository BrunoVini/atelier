"""Record steer instructions from the browser into the session journal.

Usage (shelled by the proxy):
    python3 live_steer.py --journal-dir <dir> --session <id> \
        --message "make it bolder" [--page-url http://...]
"""
import argparse, json, os, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import live_journal as lj


def record_steer(journal_dir, session_id, message, page_url):
    if not message or not message.strip():
        return {"ok": False, "reason": "message must not be empty"}
    steer_id = str(uuid.uuid4())[:8]
    entry = lj.write_entry(journal_dir, session_id, "steer", {
        "id": steer_id,
        "message": message.strip(),
        "page_url": page_url or None,
    })
    return {"ok": True, "id": steer_id, "entry": entry}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Record live mode steer instruction")
    ap.add_argument("--journal-dir", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--page-url", default=None)
    ns = ap.parse_args()
    print(json.dumps(record_steer(ns.journal_dir, ns.session, ns.message, ns.page_url)))
