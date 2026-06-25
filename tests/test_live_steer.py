"""Tests for live_steer — record steer instructions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_steer as ls
import live_journal as lj


def test_record_steer_writes_journal(tmp_path):
    jdir = str(tmp_path / "journal")
    result = ls.record_steer(jdir, "sess-s", "make the hero bolder", "http://localhost:5173/")
    assert result["ok"]
    assert result.get("id")
    entries = lj.read_entries(jdir, "sess-s")
    assert any(e.get("type") == "steer" for e in entries)
    steer = next(e for e in entries if e.get("type") == "steer")
    assert steer["message"] == "make the hero bolder"
    assert steer["page_url"] == "http://localhost:5173/"


def test_record_steer_no_page_url(tmp_path):
    jdir = str(tmp_path / "journal")
    result = ls.record_steer(jdir, "s2", "quieter please", None)
    assert result["ok"]
    entries = lj.read_entries(jdir, "s2")
    assert entries[0].get("page_url") is None


def test_record_steer_missing_message(tmp_path):
    result = ls.record_steer(str(tmp_path / "j"), "s", "", None)
    assert not result["ok"]
    assert "message" in result.get("reason", "")
