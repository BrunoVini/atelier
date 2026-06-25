"""Render-grounded color measurement (A1). Needs a headless browser; when none is
present scan_rendered exits 3 and the test accepts that (can't verify, not a failure)
— the same `unknown`-not-fail discipline qa.py uses."""
import json
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "scan_rendered.mjs")
PAGE = ('<!doctype html><html><head><style>'
        'html,body{margin:0;min-height:100vh;background:#0f1115} h1{color:#e8e6e1}'
        '</style></head><body><h1>Title</h1></body></html>')


OKLCH_PAGE = ('<!doctype html><html><head><style>'
              'html,body{margin:0;min-height:100vh;background:oklch(0.22 0.03 250)}'
              'h1{color:oklch(0.95 0.02 250)}'
              '.glass{position:fixed;inset:0;background:rgba(255,255,255,0.06)}'
              '</style></head><body><div class="glass"></div><h1>Hi</h1></body></html>')


def _run(args):
    return subprocess.run(["node", SCRIPT, *args], capture_output=True, text=True, timeout=120)


def _skip_or_return_if_no_browser(r):
    """exit 3 = no headless browser; skip under pytest, return cleanly under the stdlib runner."""
    if r.returncode == 3:
        try:
            import pytest
            pytest.skip("no headless browser")
        except ImportError:
            return True
    return False


def test_scan_rendered_ranks_painted_background(tmp_path):
    page = tmp_path / "p.html"
    page.write_text(PAGE)
    r = _run([str(page), "--json"])
    if _skip_or_return_if_no_browser(r):
        return
    assert r.returncode == 0, r.stderr
    rendered = json.loads(r.stdout)["rendered"]
    assert rendered, "should detect at least one painted color"
    assert rendered[0]["hex"].lower() == "#0f1115"     # the body bg paints the most area
    assert rendered[0]["role"] == "surface"
    assert any(c["hex"].lower() == "#e8e6e1" for c in rendered)   # text color seen too


def test_scan_rendered_handles_oklch_and_alpha(tmp_path):
    # P0 regression: modern color formats must be read (canvas-normalized), and a
    # translucent overlay must NOT count as a solid surface.
    page = tmp_path / "o.html"
    page.write_text(OKLCH_PAGE)
    r = _run([str(page), "--json"])
    if _skip_or_return_if_no_browser(r):
        return
    assert r.returncode == 0, r.stderr
    top = json.loads(r.stdout)["rendered"][0]
    assert top["hex"].lower() != "#ffffff", "the 6%-alpha white overlay must not dominate"
    rr, gg, bb = int(top["hex"][1:3], 16), int(top["hex"][3:5], 16), int(top["hex"][5:7], 16)
    assert rr + gg + bb < 300, f"dominant should be the dark oklch background, got {top['hex']}"
    assert top["share"] >= 0.5


def test_scan_rendered_reconciles_against_static(tmp_path):
    page = tmp_path / "p.html"
    page.write_text(PAGE)
    static = tmp_path / "scan.json"
    static.write_text(json.dumps({"colors": [{"hex": "#0f1115", "count": 3},
                                              {"hex": "#ff00ff", "count": 1}]}))
    r = _run([str(page), "--json", "--static", str(static)])
    if _skip_or_return_if_no_browser(r):
        return
    assert r.returncode == 0, r.stderr
    rec = json.loads(r.stdout)["reconciliation"]
    assert "#ff00ff" in rec["declared_not_painted"]                # declared but never painted
    assert any(c["hex"].lower() == "#e8e6e1" for c in rec["painted_not_declared"])  # painted but not declared


# A declared color that is never mounted in the DOM (a dead class / never-activated
# theme) paints ZERO pixels; a real but small element (a 1px border, one link) paints a
# faint sliver. A static read cannot tell these apart — rendering can. The reconciliation
# must split declared-not-painted into `dead` (0 paint) vs `faint` (a real sliver).
DEAD_VS_FAINT_PAGE = (
    '<!doctype html><html><head><style>'
    'html,body{margin:0;min-height:100vh;background:#101418;color:#e8e6e1}'
    '.box{border:1px solid #445566;padding:40px}'           # #445566 paints only a 1px border -> faint
    '.dead{background:#ff00aa;color:#00ffcc}'               # class never used -> zero paint
    '</style></head><body><div class="box">Live text</div></body></html>')


def test_reconcile_splits_dead_from_faint(tmp_path):
    page = tmp_path / "p.html"
    page.write_text(DEAD_VS_FAINT_PAGE)
    static = tmp_path / "scan.json"
    static.write_text(json.dumps({"colors": [
        {"hex": "#101418", "count": 3},   # dominant bg -> painted
        {"hex": "#445566", "count": 1},   # only a 1px border -> faint
        {"hex": "#ff00aa", "count": 1},   # dead class bg -> zero paint
        {"hex": "#00ffcc", "count": 1},   # dead class text -> zero paint
    ]}))
    r = _run([str(page), "--json", "--static", str(static)])
    if _skip_or_return_if_no_browser(r):
        return
    assert r.returncode == 0, r.stderr
    rec = json.loads(r.stdout)["reconciliation"]
    # The never-mounted class colors paint zero pixels -> dead, not merely "faint".
    assert "#ff00aa" in rec["dead"], rec
    assert "#00ffcc" in rec["dead"], rec
    # The 1px border is a real, painted sliver -> faint, NOT dead.
    assert "#445566" in rec["faint"], rec
    assert "#445566" not in rec["dead"], rec
    # The dominant bg is painted plenty -> in neither bucket.
    assert "#101418" not in rec["declared_not_painted"], rec
    assert "#101418" not in rec["faint"], rec
    # declared_not_painted is the headline dead set (no visible paint).
    assert set(rec["declared_not_painted"]) == set(rec["dead"]), rec
    # dead and faint are disjoint.
    assert not (set(rec["dead"]) & set(rec["faint"])), rec


# A color applied by JS / inline at runtime (never a hex in the CSS source) is exactly
# what a static scan misses. Even when it paints only a small but VISIBLE sliver, the
# render must surface it as painted-but-not-declared (flagged as an `accent`).
JS_COLOR_PAGE = (
    '<!doctype html><html><head><style>'
    'html,body{margin:0;min-height:100vh;background:#101418;color:#e8e6e1}'
    '.banner{padding:24px;font-size:20px}'
    '</style></head><body><div class="banner" id="t">System alert: degraded</div></body>'
    '<script>document.getElementById("t").style.background="#ff6d00";</script>'
    '</html>')


def test_painted_not_declared_catches_visible_js_color(tmp_path):
    page = tmp_path / "p.html"
    page.write_text(JS_COLOR_PAGE)
    static = tmp_path / "scan.json"
    # The static CSS scan only sees the two stylesheet colors; #ff6d00 is JS-applied.
    static.write_text(json.dumps({"colors": [
        {"hex": "#101418", "count": 2}, {"hex": "#e8e6e1", "count": 1}]}))
    r = _run([str(page), "--json", "--static", str(static)])
    if _skip_or_return_if_no_browser(r):
        return
    assert r.returncode == 0, r.stderr
    rec = json.loads(r.stdout)["reconciliation"]
    hit = [c for c in rec["painted_not_declared"] if c["hex"].lower() == "#ff6d00"]
    assert hit, f"JS-applied #ff6d00 must be caught as painted-but-not-declared: {rec}"
    assert hit[0]["painted"] in ("accent", "major")
