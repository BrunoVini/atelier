"""Tests for live_insert — anchor resolution for net-new content."""
import sys, os, tempfile, pathlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_insert as li


def test_find_by_id(tmp_path):
    f = tmp_path / "index.html"
    f.write_text('<div id="hero">\n  <h1>Title</h1>\n</div>\n<footer>foot</footer>\n')
    result = li.find_insert_anchor(str(f), {"id": "hero"})
    assert result["ok"]
    assert result["line"] > 0    # 1-based line number of the anchor element
    assert "hero" in result.get("context", "")


def test_find_by_tag_text(tmp_path):
    f = tmp_path / "page.html"
    f.write_text('<section>\n  <h2>Features</h2>\n  <p>stuff</p>\n</section>\n')
    result = li.find_insert_anchor(str(f), {"tag": "section"})
    assert result["ok"]


def test_anchor_not_found(tmp_path):
    f = tmp_path / "empty.html"
    f.write_text('<html><body></body></html>')
    result = li.find_insert_anchor(str(f), {"id": "nonexistent-xyz"})
    assert not result["ok"]
    assert "reason" in result


def test_file_not_found():
    result = li.find_insert_anchor("/tmp/does-not-exist-atelier.html", {"id": "x"})
    assert not result["ok"]
