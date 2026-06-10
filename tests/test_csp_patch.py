"""CSP classification for the live preview (#8, scoped). The themed preview injects a
client script; a project CSP blocks it. Classify the patch mechanism per framework so the
preview (dev-only) can relax it. Pure function — testable without a running server."""
from csp_patch import classify_csp


def test_next(tmp_path):
    (tmp_path / "next.config.js").write_text("module.exports = {}")
    assert classify_csp(str(tmp_path))["mechanism"] == "next"


def test_sveltekit(tmp_path):
    (tmp_path / "svelte.config.js").write_text("export default {}")
    assert classify_csp(str(tmp_path))["mechanism"] == "sveltekit"


def test_nuxt(tmp_path):
    (tmp_path / "nuxt.config.ts").write_text("export default defineNuxtConfig({})")
    assert classify_csp(str(tmp_path))["mechanism"] == "nuxt"


def test_meta_tag(tmp_path):
    (tmp_path / "index.html").write_text(
        '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'">')
    assert classify_csp(str(tmp_path))["mechanism"] == "meta-tag"


def test_none_when_no_csp(tmp_path):
    (tmp_path / "index.html").write_text("<h1>hi</h1>")
    assert classify_csp(str(tmp_path))["mechanism"] == "none"
