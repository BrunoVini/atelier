"""Live-site motion capture (#10). Needs a headless browser; skips on exit 3."""
import json
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "scan_motion.mjs")
PAGE = (
    "<!doctype html><html><head><style>"
    # @keyframes nested in @media (atelier's own reduced-motion pattern) must still be seen
    "@media (min-width:0px){@keyframes floaty{from{transform:translateY(0)}to{transform:translateY(-10px)}}}"
    ".hero{animation:floaty 1.2s ease-in-out infinite}"
    ".sticky-nav{position:sticky;top:0}"
    ".card{transition:transform 200ms ease}"
    "</style></head><body>"
    "<nav class=sticky-nav>n</nav><div class=hero>h</div><div class=card>c</div>"
    "<div data-aos='fade-up'>x</div>"
    # shape-checked globals: a bare {} must NOT count as a library; real shapes must
    "<script>window.gsap={to:function(){}};window.ScrollTrigger={create:function(){}};</script>"
    "</body></html>")


def _skip_or_return(r):
    if r.returncode == 3:
        try:
            import pytest
            pytest.skip("no headless browser")
        except ImportError:
            return True
    return False


def test_captures_keyframes_libraries_and_scroll(tmp_path):
    page = tmp_path / "m.html"
    page.write_text(PAGE)
    r = subprocess.run(["node", SCRIPT, str(page), "--json"], capture_output=True, text=True, timeout=120)
    if _skip_or_return(r):
        return
    assert r.returncode == 0, r.stderr
    spec = json.loads(r.stdout)
    assert "floaty" in spec["keyframes"]                       # @media-nested keyframe seen
    assert "translateY" in spec["keyframes"]["floaty"]         # body captured, not just the name
    hero = next((a for a in spec["animated"] if a["name"] == "floaty"), None)
    assert hero and hero["duration"] == "1.2s" and hero["iteration"] == "infinite"
    assert any(t["property"].startswith("transform") for t in spec["transitions"])   # transition captured
    assert "gsap" in spec["libraries"] and "gsap/ScrollTrigger" in spec["libraries"]
    assert spec["scroll"]["sticky"] == 1                        # exactly one, not double-counted
    assert spec["scroll"]["aos"] >= 1


def test_bare_globals_are_not_false_positive_libraries(tmp_path):
    page = tmp_path / "b.html"
    page.write_text("<!doctype html><html><body><script>window.Motion={x:1};window.AOS={};</script></body></html>")
    r = subprocess.run(["node", SCRIPT, str(page), "--json"], capture_output=True, text=True, timeout=120)
    if _skip_or_return(r):
        return
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["libraries"] == []   # a bare {} global is not proof of a lib
