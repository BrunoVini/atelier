"""Tests for live_config drift-heal."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_config as lc


def test_no_orphans_when_all_covered(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 0
    assert result["orphans"] == []


def test_finds_orphan_html(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "about.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 1
    assert any("about.html" in o for o in result["orphans"])


def test_excludes_node_modules(tmp_path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "index.html").write_text("<html></html>")
    (tmp_path / "index.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 0


def test_excludes_git_dir(tmp_path):
    git = tmp_path / ".git"
    git.mkdir()
    (git / "COMMIT_EDITMSG").write_text("msg")
    (tmp_path / "index.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 0


def test_empty_project_no_crash(tmp_path):
    result = lc.find_orphan_html(str(tmp_path), [])
    assert isinstance(result["orphans"], list)


def test_hint_mentions_count(tmp_path):
    (tmp_path / "a.html").write_text("<html></html>")
    (tmp_path / "b.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [])
    assert "2" in result["hint"]
