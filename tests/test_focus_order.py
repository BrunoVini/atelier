"""Keyboard focus-order rendered check (focus_order.mjs + lib/focusorder.mjs).

The pure helpers (cycle detection + the focusable-hidden predicate) are unit-tested via
`node -e` WITHOUT a browser, mirroring test_live_proxy.py's _node() pattern, so they run
in the default suite when node is present and SKIP cleanly when it isn't.

Browser-backed tests render fixtures (focusable-hidden, custom file-input, transform
drawer, clean modal page) and assert focus_order is ADVISORY-ONLY: it alway exits 0
when the browser ran, reporting findings in --json but NEVER gating. They SKIP on exit 3
(no browser) so the default suite is deterministic.

ADVISORY-ONLY DISCIPLINE: focus_order NEVER gates (the focus heuristics are too
FP-prone for a hook gate — the custom-form-control and closed-drawer idioms would be
wrongly flagged). It detects and REPORTS `focusable-hidden`, tab-vs-visual order,
positive tabindex, and possible-focus-trap as advisories. The qa --hook must never FAIL
on any of these.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "focus_order.mjs")
LIB = os.path.join(ROOT, "scripts", "lib", "focusorder.mjs")
_QA = os.path.join(ROOT, "scripts", "qa.py")


def _node():
    return shutil.which("node")


# ── pure helpers via node -e (no browser) ─────────────────────────────────────

def _eval(expr_js):
    """Import lib/focusorder.mjs and JSON.stringify the given JS expression `m.<...>`."""
    node = _node()
    if not node:
        pytest.skip("node not available")
    script = (
        "import(%r).then(m => process.stdout.write(JSON.stringify(%s)))"
        ".catch(e => { console.error(e); process.exit(1); });"
    ) % (LIB, expr_js)
    r = subprocess.run([node, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_detect_cycle_finds_ring_wrap():
    out = _eval("m.detectCycle(['a','b','c','a'])")
    assert out["cycled"] is True
    assert out["repeatedAt"] == 3
    assert out["stops"] == ["a", "b", "c"]


def test_detect_cycle_no_repeat_means_not_cycled():
    out = _eval("m.detectCycle(['a','b','c'])")
    assert out["cycled"] is False
    assert out["repeatedAt"] == -1
    assert out["stops"] == ["a", "b", "c"]


def test_focusable_hidden_predicate_gates_real_bugs():
    # zero-size box, visibility:hidden, and opacity:0 (not transitioning) all GATE.
    out = _eval(
        "["
        "m.isFocusableHidden({width:0,height:0,visibility:'visible',opacity:'1'}),"      # zero box
        "m.isFocusableHidden({width:10,height:10,visibility:'hidden',opacity:'1'}),"     # vis hidden
        "m.isFocusableHidden({width:10,height:10,visibility:'visible',opacity:'0'}),"    # opacity 0
        "m.isFocusableHidden({width:10,height:10,opacity:'0',transitioning:true}),"      # fade -> NO
        "m.isFocusableHidden({width:10,height:10,opacity:'1',rectLeft:-9999,rectTop:5,rectRight:-9989,rectBottom:15})"  # offscreen
        "]"
    )
    assert out == [True, True, True, False, True]


def test_focusable_hidden_does_not_gate_normal_or_skiplink():
    # a normal visible control and a legit screen-reader skip-link must NOT gate (FP guard).
    out = _eval(
        "["
        "m.isFocusableHidden({width:80,height:30,visibility:'visible',opacity:'1',"
        "  rectLeft:5,rectTop:5,rectRight:85,rectBottom:35,viewportWidth:1440,viewportHeight:900}),"
        "m.isFocusableHidden({width:1,height:1,clip:'rect(0px 0px 0px 0px)',clipPath:'inset(50%)',"
        "  className:'sr-only',tag:'a',href:'#main',text:'Skip to main content'}),"
        "m.isFocusableHidden({width:0,height:0,className:'skip-link',tag:'a',href:'#main',text:'Skip'})"
        "]"
    )
    # normal -> False; both skip-link shapes -> False (intent allowlist wins over zero-size)
    assert out == [False, False, False]


# ── browser-backed end-to-end (skips without a browser) ───────────────────────

# A clean, accessible page WITH a focus-trapping modal — a trap is legitimate and must
# NOT gate. Includes a real screen-reader skip-link (must also not gate).
CLEAN = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>clean</title><style>'
    '.sr-only{position:absolute;width:1px;height:1px;clip:rect(0 0 0 0);clip-path:inset(50%);overflow:hidden}'
    '.modal{position:fixed;inset:20% 30%;background:#fff;border:2px solid #333;padding:24px}'
    'a,button,input{font:16px system-ui;margin:6px}:focus-visible{outline:3px solid #06f}'
    '</style></head><body>'
    '<a class="sr-only skip-link" href="#main">Skip to main content</a>'
    '<nav><a href="/a">Home</a> <a href="/b">About</a> <a href="/c">Contact</a></nav>'
    '<main id="main"><h1>Hello</h1>'
    '<form><label for="q">Search</label><input id="q" type="text"><button>Go</button></form>'
    '<div class="modal" role="dialog" aria-modal="true"><h2>Subscribe</h2>'
    '<label for="e">Email</label><input id="e" type="email">'
    '<button id="ok">OK</button><button id="cancel">Cancel</button></div></main>'
    '<script>const modal=document.querySelector(".modal");'
    'const f=modal.querySelectorAll("input,button");const first=f[0],last=f[f.length-1];'
    'document.addEventListener("keydown",e=>{if(e.key!=="Tab")return;'
    'if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}'
    'else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}});'
    'first.focus();</script></body></html>'
)

# A page with a focusable-but-hidden control: tabindex=0 on a 0x0 element that still
# receives focus. Now ADVISORY (reported in JSON) and must NOT gate (exit 0).
HIDDEN = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>hidden</title><style>'
    'a,button,input{font:16px system-ui;margin:6px}:focus-visible{outline:3px solid #06f}'
    '.ghost{position:absolute;width:0;height:0;overflow:hidden;padding:0;border:0}'
    '</style></head><body><nav><a href="/a">Home</a> <a href="/b">About</a></nav>'
    '<main><h1>Page</h1><button>Visible button</button>'
    '<span class="ghost" tabindex="0">I take focus but you cannot see me</span>'
    '<input type="text" aria-label="name"></main></body></html>'
)

# FP guard: the ubiquitous custom file-input pattern — a native <input type=file> hidden
# with opacity:0;width:0;height:0 behind a styled <label>. Fully accessible. The advisory
# may flag it, but it must NEVER gate (exit 0).
CUSTOM_FILE_INPUT = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>upload</title><style>'
    'body{font:16px system-ui}.field input{opacity:0;width:0;height:0;position:absolute}'
    '.field label{display:inline-block;padding:10px 16px;border:2px solid #06f;border-radius:8px;cursor:pointer}'
    ':focus-visible{outline:3px solid #06f}</style></head><body>'
    '<main><h1>Upload</h1>'
    '<form><div class="field"><label for="file">Upload a file</label>'
    '<input id="file" type="file"></div>'
    '<button type="submit">Send</button></form></main></body></html>'
)

# FP guard: a closed mobile drawer hidden via transform:translateX(-100%) with its links
# left in the tab order — the common closed-nav idiom. Must NEVER gate (exit 0).
TRANSFORM_DRAWER = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>drawer</title><style>'
    'body{font:16px system-ui}.drawer{position:fixed;top:0;left:0;width:260px;height:100%;'
    'background:#fff;border-right:2px solid #333;transform:translateX(-100%)}'
    '.drawer a{display:block;padding:10px}:focus-visible{outline:3px solid #06f}'
    '</style></head><body>'
    '<header><button id="menu">Menu</button></header>'
    '<nav class="drawer"><a href="/a">Home</a><a href="/b">About</a><a href="/c">Contact</a></nav>'
    '<main><h1>Home</h1><button>Action</button>'
    '<form><label for="q">Search</label><input id="q" type="text"></form></main></body></html>'
)


def _run(page_path):
    return subprocess.run(["node", SCRIPT, str(page_path), "--json"],
                          capture_output=True, text=True, timeout=120)


def _skip_no_browser(r):
    if r.returncode == 3 or "no headless browser" in (r.stderr + r.stdout):
        pytest.skip("no headless browser")


def _adv_kinds(out):
    return {a.get("kind") for a in (out.get("advisories") or [])}


def test_hidden_focusable_is_advisory_not_a_gate(tmp_path):
    # A focusable-but-hidden 0x0 control is now ADVISORY: reported in JSON, exit 0.
    if not _node():
        pytest.skip("node not available")
    p = tmp_path / "hidden.html"
    p.write_text(HIDDEN)
    r = _run(p)
    _skip_no_browser(r)
    assert r.returncode == 0, f"focusable-hidden must NOT gate — advisory only (exit 0)\n{r.stderr}"
    out = json.loads(r.stdout)
    assert out["hidden"], out                          # still detected
    assert "focusable-hidden" in _adv_kinds(out), out  # surfaced as an advisory
    assert out["finding"] is None, out                 # never a gating finding


def test_custom_file_input_does_not_gate(tmp_path):
    # FP guard: native file input hidden behind a styled label -> exit 0 (advisory at most).
    if not _node():
        pytest.skip("node not available")
    p = tmp_path / "upload.html"
    p.write_text(CUSTOM_FILE_INPUT)
    r = _run(p)
    _skip_no_browser(r)
    assert r.returncode == 0, (
        f"custom file-input pattern must NOT gate; got {r.returncode}\n{r.stdout}\n{r.stderr}")
    assert json.loads(r.stdout)["finding"] is None


def test_transform_drawer_does_not_gate(tmp_path):
    # FP guard: closed mobile drawer (transform:translateX(-100%)) -> exit 0.
    if not _node():
        pytest.skip("node not available")
    p = tmp_path / "drawer.html"
    p.write_text(TRANSFORM_DRAWER)
    r = _run(p)
    _skip_no_browser(r)
    assert r.returncode == 0, (
        f"transform-hidden drawer must NOT gate; got {r.returncode}\n{r.stdout}\n{r.stderr}")
    assert json.loads(r.stdout)["finding"] is None


def test_clean_modal_page_does_not_gate(tmp_path):
    if not _node():
        pytest.skip("node not available")
    p = tmp_path / "clean.html"
    p.write_text(CLEAN)
    r = _run(p)
    _skip_no_browser(r)
    assert r.returncode == 0, (
        f"a clean page (incl. a focus-trapping modal + skip-link) must NOT gate; got "
        f"{r.returncode}\n{r.stdout}\n{r.stderr}")
    out = json.loads(r.stdout)
    assert out["hidden"] == [], out
    assert out["finding"] is None, out


# ── qa.py wiring ──────────────────────────────────────────────────────────────

def test_focus_order_is_in_the_page_plan_not_film():
    from qa import _rendered_plan
    assert "focus_order.mjs" in _rendered_plan("page")
    assert "focus_order.mjs" not in _rendered_plan("animation")


def _focus_result(page):
    """Run qa --hook --json on `page` and return (returncode, focus_order CheckResult dict)."""
    r = subprocess.run([sys.executable, _QA, str(page), "--hook", "--json"],
                       text=True, capture_output=True, timeout=180)
    results = json.loads(r.stdout)
    fo = next(x for x in results if x["name"] == "focus_order.mjs")
    return r, fo


def test_hook_does_not_fail_on_focusable_hidden_artifact(tmp_path):
    # focus_order is advisory: a focusable-hidden artifact must NOT block the hook, while
    # the advisory is still surfaced as a NON-GATING CheckResult.
    if not _node():
        pytest.skip("node not available")
    page = tmp_path / "bad.html"
    page.write_text(HIDDEN)
    probe = _run(page)
    _skip_no_browser(probe)
    r, fo = _focus_result(page)
    assert fo["gating"] is False, fo                       # never gates
    assert fo["status"] in ("advisory", "unknown"), fo     # never "fail"
    # the focus observation is surfaced (advisory count or detail mentions it)
    if fo["status"] == "advisory":
        assert fo["counts"].get("advisories", 0) >= 1, fo
    # focus_order alone must never make the hook exit 1 (1 only on a real gating FAIL)
    other_fail = any(x["gating"] and x["status"] == "fail"
                     for x in json.loads(r.stdout) if x["name"] != "focus_order.mjs")
    if not other_fail:
        assert r.returncode != 1, f"focus_order must not BLOCK the hook\n{r.stdout}"


def test_hook_does_not_gate_focus_order_on_fp_fixtures(tmp_path):
    # The custom file-input and transform-drawer FP cases must not fail the hook.
    if not _node():
        pytest.skip("node not available")
    for name, html in (("upload.html", CUSTOM_FILE_INPUT), ("drawer.html", TRANSFORM_DRAWER)):
        page = tmp_path / name
        page.write_text(html)
        probe = _run(page)
        _skip_no_browser(probe)
        r, fo = _focus_result(page)
        assert fo["gating"] is False, (name, fo)
        assert fo["status"] != "fail", (name, fo)
        other_fail = any(x["gating"] and x["status"] == "fail"
                         for x in json.loads(r.stdout) if x["name"] != "focus_order.mjs")
        if not other_fail:
            assert r.returncode != 1, f"{name}: focus_order must not BLOCK the hook\n{r.stdout}"


def test_hook_does_not_gate_focus_order_on_clean_modal_page(tmp_path):
    if not _node():
        pytest.skip("node not available")
    page = tmp_path / "good.html"
    page.write_text(CLEAN)
    probe = _run(page)
    _skip_no_browser(probe)
    r, fo = _focus_result(page)
    assert fo["status"] in ("advisory", "pass", "unknown"), fo
    assert fo["gating"] is False, fo
