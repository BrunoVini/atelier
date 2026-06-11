"""Phase 7 live mode — the reverse proxy's HTML injection (live-proxy.cjs).

The injection logic is the load-bearing part of the proxy, so it is unit-tested in the
DEFAULT suite by requiring the .cjs module in a node subprocess and calling its exported
`inject(html)` — no second server, no browser. Skips cleanly if node is absent.

An opt-in end-to-end test that boots the proxy in front of a FakeDevServer lives in
tests/live_e2e/ (not wired into run.py).
"""
import json
import os
import shutil
import subprocess

import pytest

PROXY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "preview", "live-proxy.cjs"))


def _node():
    return shutil.which("node")


def _call_inject(html):
    """Require live-proxy.cjs in node and call inject(html); return the result string."""
    node = _node()
    if not node:
        pytest.skip("node not available")
    script = (
        "const p = require(%r);"
        "let html = '';"
        "process.stdin.on('data', d => html += d);"
        "process.stdin.on('end', () => process.stdout.write(p.inject(html)));"
    ) % PROXY
    r = subprocess.run([node, "-e", script], input=html, capture_output=True,
                       text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_inject_before_body():
    out = _call_inject("<html><body><h1>Hi</h1></body></html>")
    assert 'data-atelier-live="1"' in out
    # injected BEFORE the closing body tag
    assert out.index('data-atelier-live="1"') < out.index("</body>")


def test_inject_html_fallback_when_no_body():
    out = _call_inject("<html><h1>no body tag</h1></html>")
    assert 'data-atelier-live="1"' in out
    assert out.index('data-atelier-live="1"') < out.index("</html>")


def test_inject_append_when_no_closing_tags():
    out = _call_inject("<h1>fragment</h1>")
    assert "<h1>fragment</h1>" in out
    assert 'data-atelier-live="1"' in out


def test_inject_is_idempotent():
    once = _call_inject("<html><body>x</body></html>")
    twice = _call_inject(once)
    # already injected -> not injected again
    assert twice.count('data-atelier-live="1"') == 1


def test_parse_args_round_trip():
    node = _node()
    if not node:
        pytest.skip("node not available")
    script = (
        "const p = require(%r);"
        "process.stdout.write(JSON.stringify(p.parseArgs("
        "['--upstream','http://localhost:5173','--port','4100','--inject-only'])));"
    ) % PROXY
    r = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    opts = json.loads(r.stdout)
    assert opts["upstream"] == "http://localhost:5173"
    assert opts["port"] == 4100
    assert opts["injectOnly"] is True


def test_isHtml_only_matches_text_html():
    node = _node()
    if not node:
        pytest.skip("node not available")
    script = (
        "const p = require(%r);"
        "process.stdout.write(JSON.stringify(["
        "p.isHtml({'content-type':'text/html; charset=utf-8'}),"
        "p.isHtml({'content-type':'application/json'}),"
        "p.isHtml({})]));"
    ) % PROXY
    r = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [True, False, False]
