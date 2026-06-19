"""Tests for knob_values round-trip through accept_variant."""
import sys, os, json, tempfile, pathlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Stub QA to always pass so accept succeeds
import live_accept as la
_orig_run_qa = la._run_qa


def _fake_qa_pass(target, **kw):
    return "PASS", [{"name": "slop", "status": "pass", "gating": True}]


def test_knob_values_recorded_in_journal(tmp_path):
    """accept_variant with knob_values stores them in journal entry."""
    la._run_qa = lambda *a, **kw: _fake_qa_pass(a[0])
    try:
        src = tmp_path / "index.html"
        src.write_text('<div class="hero">old content</div>', encoding='utf-8')

        journal_dir = str(tmp_path / "journal")
        result = la.accept_variant(
            str(src),
            old='<div class="hero">old content</div>',
            new='<div class="hero" style="--p-amount:0.7">new content</div>',
            qa_target=str(src),
            journal_dir=journal_dir,
            session="sess-knob-01",
            knob_values={"amount": {"kind": "range", "value": 0.7}},
        )
        assert result.get("ok"), result
        assert result.get("knob_values") == {"amount": {"kind": "range", "value": 0.7}}
    finally:
        la._run_qa = _orig_run_qa


def test_knob_values_none_still_accepts(tmp_path):
    """accept_variant works fine with no knob_values (backwards compat)."""
    la._run_qa = lambda *a, **kw: _fake_qa_pass(a[0])
    try:
        src = tmp_path / "page.html"
        src.write_text('<p id="x">old</p>', encoding='utf-8')

        result = la.accept_variant(
            str(src), old='<p id="x">old</p>', new='<p id="x">new</p>',
            qa_target=str(src), journal_dir=str(tmp_path / "j"), session="s2",
        )
        assert result.get("ok"), result
        assert "knob_values" not in result or result.get("knob_values") is None
    finally:
        la._run_qa = _orig_run_qa
