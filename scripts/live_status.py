"""Live mode session status — reads the journal and reports current state.

Usage:
    python3 live_status.py --journal-dir <dir> --session <id>
    # -> prints {session, accepts, reverts, steers, status, last_accept?} as JSON
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import live_journal as lj


def status(journal_dir, session_id):
    state = lj.session_state(journal_dir, session_id)
    if state["accepts"]:
        state["last_accept"] = state["accepts"][-1]
    return state


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Live mode session status")
    ap.add_argument("--journal-dir", required=True)
    ap.add_argument("--session", required=True)
    ns = ap.parse_args()
    print(json.dumps(status(ns.journal_dir, ns.session)))
