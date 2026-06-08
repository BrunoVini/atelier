"""Integration tests for responsive_check.mjs — the rendered sweep.

These shell out to the real Node script + a headless browser (the only faithful
way to test the in-page probe), so they skip when node/playwright aren't present.

Focus: an OPAQUE decoration sitting on real text is a hard defect (exit != 0),
while a blurred / edge-transparent wash over text stays an advisory (exit 0) —
the discrimination that lets the gate enforce the most-missed collision without
false-flagging legitimate layered art.
"""
import os
import shutil
import subprocess

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
_RC = os.path.join(_SCRIPTS, "responsive_check.mjs")


def _browser_ok():
    if not shutil.which("node"):
        return False
    probe = subprocess.run(
        ["node", "-e", "import('playwright').then(()=>process.exit(0)).catch(()=>process.exit(3))"],
        cwd=_SCRIPTS, capture_output=True)
    return probe.returncode == 0


requires_browser = pytest.mark.skipif(not _browser_ok(), reason="node + headless browser unavailable")

_PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body{{margin:0;font-family:Georgia,serif}}
  .wrap{{max-width:760px;margin:0 auto;padding:64px 24px}}
  .stat{{position:relative;margin:40px 0}}
  .stat p{{margin:0;font:600 22px/1.45 Georgia,serif;width:300px}}
  .deco{{position:absolute;top:-10px;left:150px;width:130px;height:130px;border-radius:50%;{deco}}}
</style></head><body><div class="wrap"><div class="stat">
  <p>Trusted by 2,000+ design teams across 40 countries</p><span class="deco"></span>
</div></div></body></html>"""

OPAQUE = _PAGE.format(deco="background:#b8442c")
WASH = _PAGE.format(
    deco="background:radial-gradient(circle, rgba(184,68,44,.35), rgba(184,68,44,0) 70%);filter:blur(8px)")


def _run(page):
    return subprocess.run(["node", _RC, str(page), "--widths", "390,1440"],
                          capture_output=True, text=True)


@requires_browser
def test_opaque_decoration_over_text_is_a_hard_failure(tmp_path):
    page = tmp_path / "opaque.html"
    page.write_text(OPAQUE)
    r = _run(page)
    out = r.stderr + r.stdout
    assert r.returncode == 1, f"opaque deco over text must fail the sweep; got {r.returncode}\n{out}"
    assert "COLLISION" in out, f"opaque deco should surface as a COLLISION, not a soft note\n{out}"


@requires_browser
def test_transparent_wash_over_text_stays_advisory(tmp_path):
    page = tmp_path / "wash.html"
    page.write_text(WASH)
    r = _run(page)
    out = r.stderr + r.stdout
    assert r.returncode == 0, f"a blurred edge-transparent wash must stay advisory; got {r.returncode}\n{out}"
    assert "deco-over-text" in out, f"the wash should still be reported as an advisory to verify\n{out}"
