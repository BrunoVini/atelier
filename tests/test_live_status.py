"""Tests for live_status.py — reads the journal and reports session state."""
import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_journal as lj
import live_status as ls

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def test_status_empty_session(tmp_path):
    jdir = str(tmp_path / "journal")
    state = ls.status(jdir, "empty-sess")
    assert state["session"] == "empty-sess"
    assert state["accepts"] == []
    assert state["reverts"] == []
    assert state["steers"] == []
    assert state["status"] == "active"
    assert "last_accept" not in state


def test_status_last_accept_present(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s", "accept", {"file": "a.html", "ok": True})
    lj.write_entry(jdir, "s", "accept", {"file": "b.html", "ok": True})
    state = ls.status(jdir, "s")
    assert state["last_accept"]["file"] == "b.html"


def test_status_exited_session(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s", "accept", {"ok": True})
    lj.write_entry(jdir, "s", "exit", {})
    state = ls.status(jdir, "s")
    assert state["status"] == "exited"
    assert "last_accept" in state


def test_status_counts(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s", "accept", {"file": "x.html"})
    lj.write_entry(jdir, "s", "accept", {"file": "y.html"})
    lj.write_entry(jdir, "s", "revert", {"journal_id": "j1"})
    lj.write_entry(jdir, "s", "steer", {"message": "bolder"})
    lj.write_entry(jdir, "s", "steer", {"message": "quieter"})
    state = ls.status(jdir, "s")
    assert len(state["accepts"]) == 2
    assert len(state["reverts"]) == 1
    assert len(state["steers"]) == 2


def test_status_cli_outputs_json(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "cli-sess", "accept", {"file": "f.html", "ok": True})
    cmd = [sys.executable, os.path.join(SCRIPTS, "live_status.py"),
           "--journal-dir", jdir, "--session", "cli-sess"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["session"] == "cli-sess"
    assert len(out["accepts"]) == 1
    assert out["last_accept"]["file"] == "f.html"


def test_status_cli_empty_session(tmp_path):
    jdir = str(tmp_path / "journal")
    cmd = [sys.executable, os.path.join(SCRIPTS, "live_status.py"),
           "--journal-dir", jdir, "--session", "no-such"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["accepts"] == []
    assert out["status"] == "active"
