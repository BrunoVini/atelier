"""Live-site motion capture (#10). Needs a headless browser; skips on exit 3."""
import json
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "scan_motion.mjs")
PAGE = (
    "<!doctype html><html><head><style>"
    "@keyframes floaty{from{transform:translateY(0)}to{transform:translateY(-10px)}}"
    ".hero{animation:floaty 1.2s ease-in-out infinite}"
    ".sticky-nav{position:sticky;top:0}"
    ".card{transition:transform 200ms ease}"
    "</style></head><body>"
    "<nav class=sticky-nav>n</nav><div class=hero>h</div><div class=card>c</div>"
    "<div data-aos='fade-up'>x</div>"
    "<script>window.gsap={};window.ScrollTrigger={};</script>"
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
    assert "floaty" in spec["keyframes"]
    hero = next((a for a in spec["animated"] if a["name"] == "floaty"), None)
    assert hero and hero["duration"] == "1.2s" and hero["iteration"] == "infinite"
    assert "gsap" in spec["libraries"] and "gsap/ScrollTrigger" in spec["libraries"]
    assert spec["scroll"]["sticky"] >= 1
    assert spec["scroll"]["aos"] >= 1
