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


# ── Fix 1: first_child / last_child positions ────────────────────────────────

def test_first_child_position(tmp_path):
    f = tmp_path / "index.html"
    f.write_text('<div id="hero">\n  <h1>Title</h1>\n</div>\n')
    result = li.find_insert_anchor(str(f), {"id": "hero"}, "first_child")
    assert result["ok"]
    # first_child insert line should be AFTER the opening tag (line 1), so line 2
    assert result["line"] == 2


def test_last_child_position(tmp_path):
    f = tmp_path / "index.html"
    f.write_text('<div id="hero">\n  <h1>Title</h1>\n</div>\n')
    result = li.find_insert_anchor(str(f), {"id": "hero"}, "last_child")
    assert result["ok"]
    # last_child insert line should be the closing </div> which is line 3
    assert result["line"] == 3


# ── Fix 2: anchor uniqueness enforcement ─────────────────────────────────────

def test_anchor_uniqueness_error(tmp_path):
    f = tmp_path / "index.html"
    # Two divs with the same class — anchor matches 2 lines
    f.write_text('<div class="card">\n</div>\n<div class="card">\n</div>\n')
    result = li.find_insert_anchor(str(f), {"classes": "card"})
    assert not result["ok"]
    assert "2" in result["reason"]
    assert "unique" in result["reason"]


# ── Fix 3: generated/minified/vendored safety check ──────────────────────────

def test_insert_refuses_generated_file(tmp_path):
    # A file inside node_modules should be refused.
    nm = tmp_path / "node_modules" / "lib"
    nm.mkdir(parents=True)
    f = nm / "bundle.js"
    f.write_text('export default function() {}\n')
    result = li.insert_at_position(str(f), {"tag": "div"}, "after", "<p>new</p>")
    assert not result["ok"]
    assert "generated" in result["reason"].lower() or "minif" in result["reason"].lower() or "vendor" in result["reason"].lower()


def test_insert_refuses_minified_file(tmp_path):
    f = tmp_path / "app.min.js"
    f.write_text('var x=1;\n')
    result = li.insert_at_position(str(f), {"tag": "div"}, "after", "<p>new</p>")
    assert not result["ok"]
    assert "generated" in result["reason"].lower() or "minif" in result["reason"].lower()


# ── Fix 5: tag matching must not match prefix-extended tags ──────────────────

def test_tag_match_does_not_match_prefixed_tag(tmp_path):
    # Looking for <div> must NOT match <divwrapper ...>
    f = tmp_path / "index.html"
    f.write_text('<divwrapper id="x">\n  <span>hi</span>\n</divwrapper>\n')
    result = li.find_insert_anchor(str(f), {"tag": "div"})
    assert not result["ok"], "tag=div must not match <divwrapper>"


def test_tag_match_matches_div_with_attrs(tmp_path):
    # <div id="x"> must still match tag=div
    f = tmp_path / "index.html"
    f.write_text('<div id="x">\n  <span>hi</span>\n</div>\n')
    result = li.find_insert_anchor(str(f), {"tag": "div"})
    assert result["ok"], "tag=div must match <div id=...>"


def test_tag_match_matches_self_closing_div(tmp_path):
    # <div> (no attrs) must still match tag=div
    f = tmp_path / "index.html"
    f.write_text('<div>\n  <span>hi</span>\n</div>\n')
    result = li.find_insert_anchor(str(f), {"tag": "div"})
    assert result["ok"], "tag=div must match <div>"
