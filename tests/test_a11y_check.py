"""Static accessibility audit (a11y_check.py).

Severity discipline: `important` fires only on UNAMBIGUOUS violations; every
heuristic is `polish`. Each important rule has multiple FLAG cases and multiple
ways it must NOT fire (decorative alt, aria-hidden, wrapping label, aria-label,
visible text, svg title). Known-good fixtures must produce no `important`
findings, and malformed HTML must never crash.
"""
import glob
import os
import subprocess
import sys

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
KNOWN_GOOD = os.path.join(os.path.dirname(__file__), "known_good")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from a11y_check import check_a11y, scan_repo_a11y


def _kinds(html, sev=None):
    return {f["kind"] for f in check_a11y(html) if sev is None or f["severity"] == sev}


def _important(html):
    return [f for f in check_a11y(html) if f["severity"] == "important"]


# --- img-missing-alt (important) -----------------------------------------

def test_img_missing_alt_flags_no_alt():
    assert "img-missing-alt" in _kinds("<img src='a.png'>", "important")
    assert "img-missing-alt" in _kinds("<body><img src='a.png'></body>", "important")
    assert "img-missing-alt" in _kinds("<div><img src='x'><img src='y'></div>", "important")


def test_img_missing_alt_does_not_fire():
    # decorative empty alt is VALID
    assert "img-missing-alt" not in _kinds("<img src='a.png' alt=''>", "important")
    # real alt text
    assert "img-missing-alt" not in _kinds("<img src='a.png' alt='A cat'>", "important")
    # aria-hidden image is exempt
    assert "img-missing-alt" not in _kinds("<img src='a.png' aria-hidden='true'>", "important")
    # role=presentation / none exempt
    assert "img-missing-alt" not in _kinds("<img src='a.png' role='presentation'>", "important")
    assert "img-missing-alt" not in _kinds("<img src='a.png' role='none'>", "important")


# --- input-missing-label (important) -------------------------------------

def test_input_missing_label_flags():
    assert "input-missing-label" in _kinds("<form><input type='text' name='q'></form>", "important")
    assert "input-missing-label" in _kinds("<select><option>a</option></select>", "important")
    assert "input-missing-label" in _kinds("<textarea></textarea>", "important")


def test_input_missing_label_does_not_fire():
    # <label for=id> association (label can come before or after)
    assert "input-missing-label" not in _kinds(
        "<label for='n'>Name</label><input id='n' type='text'>", "important")
    assert "input-missing-label" not in _kinds(
        "<input id='n' type='text'><label for='n'>Name</label>", "important")
    # wrapping label
    assert "input-missing-label" not in _kinds(
        "<label>Name <input type='text'></label>", "important")
    # aria-label
    assert "input-missing-label" not in _kinds(
        "<input type='text' aria-label='Search'>", "important")
    # title / aria-labelledby
    assert "input-missing-label" not in _kinds(
        "<input type='text' title='Search'>", "important")
    assert "input-missing-label" not in _kinds(
        "<input type='text' aria-labelledby='lbl'>", "important")
    # exempt types
    assert "input-missing-label" not in _kinds("<input type='hidden' name='t'>", "important")
    assert "input-missing-label" not in _kinds("<input type='submit' value='Go'>", "important")
    assert "input-missing-label" not in _kinds("<input type='button' value='Go'>", "important")


# --- control-missing-name (important) ------------------------------------

def test_control_missing_name_flags():
    assert "control-missing-name" in _kinds("<button></button>", "important")
    assert "control-missing-name" in _kinds("<button><span class='icon'></span></button>", "important")
    assert "control-missing-name" in _kinds("<a href='/x'><i class='ico'></i></a>", "important")


def test_control_missing_name_does_not_fire():
    # visible text
    assert "control-missing-name" not in _kinds("<button>Save</button>", "important")
    # aria-label on the control
    assert "control-missing-name" not in _kinds("<button aria-label='Close'></button>", "important")
    assert "control-missing-name" not in _kinds("<a href='/x' aria-label='Home'></a>", "important")
    # img alt inside the control names it
    assert "control-missing-name" not in _kinds("<button><img src='i.png' alt='Menu'></button>", "important")
    # svg <title> inside the control names it
    assert "control-missing-name" not in _kinds("<button><svg><title>Close</title></svg></button>", "important")
    # an <a> with no href is not a link control — don't flag empty anchors
    assert "control-missing-name" not in _kinds("<a><i class='ico'></i></a>", "important")
    # link with text
    assert "control-missing-name" not in _kinds("<a href='/p'>Pricing</a>", "important")


# --- polish rules ---------------------------------------------------------

def test_missing_landmarks_polish():
    assert "missing-landmarks" in _kinds("<body><div>hi</div></body>")
    # a landmark tag satisfies it
    assert "missing-landmarks" not in _kinds("<body><main>hi</main></body>")
    assert "missing-landmarks" not in _kinds("<body><nav>hi</nav></body>")
    # role= satisfies it
    assert "missing-landmarks" not in _kinds("<body><div role='main'>hi</div></body>")
    # a fragment with no <body> must NOT fire document-level rules
    assert "missing-landmarks" not in _kinds("<div>fragment</div>")


def test_h1_rules_polish():
    assert "no-h1" in _kinds("<body><main><p>x</p></main></body>")
    assert "multiple-h1" in _kinds("<body><main><h1>a</h1><h1>b</h1></main></body>")
    assert "no-h1" not in _kinds("<body><main><h1>a</h1></main></body>")
    assert "multiple-h1" not in _kinds("<body><main><h1>a</h1></main></body>")
    # fragment without body: no h1 rules
    assert "no-h1" not in _kinds("<p>just a fragment</p>")


def test_positive_tabindex_polish():
    assert "positive-tabindex" in _kinds("<div tabindex='3'>x</div>")
    assert "positive-tabindex" in _kinds("<span tabindex='1'>x</span>")
    assert "positive-tabindex" not in _kinds("<div tabindex='0'>x</div>")
    assert "positive-tabindex" not in _kinds("<div tabindex='-1'>x</div>")
    assert "positive-tabindex" not in _kinds("<div>x</div>")


# --- robustness -----------------------------------------------------------

def test_clean_accessible_page_yields_zero_findings():
    html = (
        "<!doctype html><html lang='en'><head><title>OK</title></head>"
        "<body><header><nav><a href='/'>Home</a></nav></header>"
        "<main><h1>Title</h1>"
        "<img src='hero.png' alt='A hero'>"
        "<img src='deco.png' alt=''>"
        "<form><label for='q'>Search</label><input id='q' type='text'>"
        "<button>Submit</button></form>"
        "</main><footer>foot</footer></body></html>"
    )
    assert check_a11y(html) == []


# --- aria-labelledby-self-reference (important) --------------------------
# A custom control (e.g. <button role=switch>) whose aria-labelledby points only
# at its OWN id is a self-reference: it resolves to an empty/recursive accessible
# name. This is a real, unambiguous bug (caught on a settings toggle).

def test_aria_labelledby_self_reference_flags():
    # button role=switch labelledby its own id → no real name
    html = ('<button id="sw" role="switch" aria-checked="true" '
            'aria-labelledby="sw"></button>')
    assert "aria-labelledby-self-reference" in _kinds(html, "important")


def test_aria_labelledby_self_reference_flags_among_tokens_when_only_self_resolves():
    # labelledby lists only the own id (even with extra whitespace) → self only
    html = ('<button id="sw-2fa" role="switch" '
            'aria-labelledby="  sw-2fa  "></button>')
    assert "aria-labelledby-self-reference" in _kinds(html, "important")


def test_aria_labelledby_self_reference_does_not_fire_when_other_token_present():
    # points at its own id AND a real label id → has a name, do not flag
    html = ('<span id="lbl">Allow invites</span>'
            '<button id="sw" role="switch" aria-labelledby="lbl sw"></button>')
    assert "aria-labelledby-self-reference" not in _kinds(html, "important")


def test_aria_labelledby_self_reference_does_not_fire_for_external_label():
    html = ('<span id="lbl">Allow invites</span>'
            '<button id="sw" role="switch" aria-labelledby="lbl"></button>')
    assert "aria-labelledby-self-reference" not in _kinds(html, "important")


def test_aria_labelledby_self_reference_does_not_fire_without_own_id():
    # aria-labelledby with no matching id of its own can't self-reference
    html = '<button role="switch" aria-labelledby="lbl"></button>'
    assert "aria-labelledby-self-reference" not in _kinds(html, "important")


def test_malformed_html_does_not_crash():
    for junk in ("<img <<< alt", "<button><a href><img", "<<<>>>",
                 "<input type=text", "", "<html><body>", None):
        # must return a list, never raise
        out = check_a11y(junk if junk is not None else "")
        assert isinstance(out, list)


def test_known_good_fixtures_have_no_important_findings():
    files = glob.glob(os.path.join(KNOWN_GOOD, "*.html"))
    assert files, "expected known_good html fixtures"
    for f in files:
        html = open(f, encoding="utf-8").read()
        imp = [x for x in check_a11y(html) if x["severity"] == "important"]
        assert imp == [], f"{os.path.basename(f)} produced important a11y findings: {imp}"


# --- repo scan ------------------------------------------------------------

def test_scan_repo_tags_findings_with_file(tmp_path):
    (tmp_path / "page.html").write_text("<body><main><h1>x</h1><img src='a'></main></body>")
    (tmp_path / "clean.html").write_text(
        "<body><main><h1>x</h1><img src='a' alt='ok'></main></body>")
    out = scan_repo_a11y(str(tmp_path))
    bad = [f for f in out if f["severity"] == "important"]
    assert len(bad) == 1
    assert bad[0]["kind"] == "img-missing-alt"
    assert bad[0]["file"] == "page.html"


def test_scan_repo_empty_when_no_html(tmp_path):
    (tmp_path / "a.css").write_text("a{color:red}")
    assert scan_repo_a11y(str(tmp_path)) == []


# --- CLI ------------------------------------------------------------------

def test_cli_exits_1_on_important_and_0_on_clean(tmp_path):
    cli = os.path.join(SCRIPTS, "a11y_check.py")
    bad = tmp_path / "bad.html"
    bad.write_text("<body><main><h1>x</h1><img src='a'></main></body>")
    r = subprocess.run([sys.executable, cli, str(bad)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 1
    assert "img-missing-alt" in r.stdout

    good = tmp_path / "good.html"
    good.write_text("<body><main><h1>x</h1><img src='a' alt='ok'></main></body>")
    r2 = subprocess.run([sys.executable, cli, str(good)], capture_output=True, text=True, timeout=60)
    assert r2.returncode == 0


# --- check.py step (gate + config skip) -----------------------------------

CHECK = os.path.join(SCRIPTS, "check.py")


def _clean_repo(tmp_path):
    """A repo that passes the other four steps (matching contract, no drift)."""
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "design-tokens.json").write_text(
        '{"colors":{"ink":"#111111","paper":"#ffffff"}}')
    return str(tmp_path)


def _run_check(repo, *args):
    return subprocess.run([sys.executable, CHECK, repo, *args],
                          capture_output=True, text=True, timeout=120)


def test_check_a11y_step_gates_on_important(tmp_path):
    repo = _clean_repo(tmp_path)
    # clean repo with no HTML -> a11y step passes
    r0 = _run_check(repo)
    assert r0.returncode == 0, r0.stdout
    assert "a11y" in r0.stdout
    # add an HTML page with an unambiguous a11y violation -> gate FAILs
    (tmp_path / "page.html").write_text(
        "<body><main><h1>x</h1><img src='hero.png'></main></body>")
    r1 = _run_check(repo)
    assert r1.returncode == 1, r1.stdout
    assert "img-missing-alt" in r1.stdout


def test_check_a11y_step_is_skippable_via_config(tmp_path):
    repo = _clean_repo(tmp_path)
    (tmp_path / "page.html").write_text(
        "<body><main><h1>x</h1><img src='hero.png'></main></body>")
    # gating by default
    assert _run_check(repo).returncode == 1
    # disable the a11y step via .atelier.json -> SKIP, gate passes again
    (tmp_path / ".atelier.json").write_text('{"checks":{"a11y":false}}')
    r = _run_check(repo)
    assert r.returncode == 0, r.stdout
    assert "[SKIP] a11y" in r.stdout


def test_check_a11y_polish_only_does_not_gate(tmp_path):
    # a page whose ONLY a11y issue is polish (no landmarks) must NOT fail the gate.
    repo = _clean_repo(tmp_path)
    (tmp_path / "page.html").write_text("<body><div><h1>x</h1></div></body>")
    r = _run_check(repo)
    assert r.returncode == 0, r.stdout
