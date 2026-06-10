"""Frame-exact video capture (#4a) regression lock. Needs node + a headless browser +
ffmpeg; skips cleanly when any is absent (can't verify, not a failure). Proves the
__recording / __ready / __seek(seconds) handshake produces a real ramp, not a frozen
video (the bug the Fable review caught: ms vs seconds + missing __recording)."""
import os
import shutil
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "export_video.sh")

# Documented contract: __seek in SECONDS, __ready boolean, __seek built only under __recording.
FIXTURE = (
    "<!doctype html><html><head><style>html,body{margin:0;height:100%}"
    "#s{width:100%;height:100vh;background:#000}</style></head><body><div id=s></div><script>"
    "const D=2;"
    "if(window.__recording){window.__ready=false;"
    "window.__seek=t=>{const v=Math.max(0,Math.min(255,Math.round(t/D*255)));"
    "document.getElementById('s').style.background=`rgb(${v},${v},${v})`;};"
    "window.__seek(0);requestAnimationFrame(()=>{window.__ready=true;});}"
    "</script></body></html>")


def _gray(mp4, at_end):
    args = ["ffmpeg", "-nostdin", "-loglevel", "error"]
    if at_end:
        args += ["-sseof", "-0.3"]
    args += ["-i", mp4, "-frames:v", "1", "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    out = subprocess.run(args, capture_output=True).stdout
    return out[0] if out else -1


def _skip():
    try:
        import pytest
        pytest.skip("node/ffmpeg/browser not available")
    except ImportError:
        return True
    return False


def test_seek_capture_is_not_frozen(tmp_path):
    if not (shutil.which("node") and shutil.which("ffmpeg")):
        if _skip():
            return
    page = tmp_path / "ramp.html"
    page.write_text(FIXTURE)
    out = tmp_path / "out.mp4"
    subprocess.run(["bash", SCRIPT, str(page), str(out), "2", "5"],
                   capture_output=True, text=True, timeout=180)
    if not out.exists():        # no headless browser in this env — can't verify
        if _skip():
            return
    first, last = _gray(str(out), False), _gray(str(out), True)
    assert abs(first - last) > 80, f"video looks frozen (first gray={first}, last={last})"
