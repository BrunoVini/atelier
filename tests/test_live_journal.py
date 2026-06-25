"""Tests for live_journal and live_status."""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_journal as lj


def test_write_and_read_entry(tmp_path):
    jdir = str(tmp_path / "journal")
    entry = lj.write_entry(jdir, "sess-01", "accept", {"file": "x.html", "ok": True})
    assert entry["type"] == "accept"
    assert entry["session"] == "sess-01"
    entries = lj.read_entries(jdir, "sess-01")
    assert len(entries) == 1
    assert entries[0]["file"] == "x.html"


def test_read_missing_journal_returns_empty(tmp_path):
    entries = lj.read_entries(str(tmp_path / "journal"), "sess-missing")
    assert entries == []


def test_session_state_accumulates(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s", "accept", {"file": "a.html", "ok": True})
    lj.write_entry(jdir, "s", "revert", {"journal_id": "j1"})
    lj.write_entry(jdir, "s", "steer", {"message": "make it bolder"})
    state = lj.session_state(jdir, "s")
    assert len(state["accepts"]) == 1
    assert len(state["reverts"]) == 1
    assert len(state["steers"]) == 1
    assert state["status"] == "active"


def test_session_state_exit(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s", "accept", {"ok": True})
    lj.write_entry(jdir, "s", "exit", {})
    state = lj.session_state(jdir, "s")
    assert state["status"] == "exited"


def test_write_creates_journal_dir(tmp_path):
    jdir = str(tmp_path / "deep" / "journal")
    lj.write_entry(jdir, "s", "start", {})
    assert os.path.isdir(jdir)


def test_multiple_sessions_isolated(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s1", "accept", {"file": "a.html"})
    lj.write_entry(jdir, "s2", "accept", {"file": "b.html"})
    assert len(lj.read_entries(jdir, "s1")) == 1
    assert len(lj.read_entries(jdir, "s2")) == 1
    assert lj.read_entries(jdir, "s1")[0]["file"] == "a.html"
