"""Contract-integrity governance (contract_integrity.py + check.py step).

A token contract is a governed artifact: a change that WIDENS it (adds a color
role) or NARROWS it (removes one) — e.g. to launder an off-token or low-contrast
color by simply declaring a new role — must be flagged as drift, not silently
accepted. This is checked against a committed baseline contract
(design/.contract-baseline.json). When no baseline is committed the step is a
no-op, so existing repos are unaffected.
"""
import json
import os
import sys

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from contract_integrity import check_contract_integrity, BASELINE_NAME


def _repo(tmp_path, tokens, baseline=None, tokens_css=None):
    design = tmp_path / "design"
    design.mkdir(parents=True, exist_ok=True)
    (design / "design-tokens.json").write_text(json.dumps(tokens))
    if baseline is not None:
        (design / BASELINE_NAME).write_text(json.dumps(baseline))
    if tokens_css is not None:
        styles = tmp_path / "src" / "styles"
        styles.mkdir(parents=True, exist_ok=True)
        (styles / "tokens.css").write_text(tokens_css)
    return str(tmp_path)


_BASE = {"colors": {"bg": "#0f1419", "text": "#e6edf3", "primary": "#2563eb"},
         "fonts": ["Inter"], "spacing": ["4", "8"], "radius": ["4", "8"],
         "depth": "borders-only"}


def test_no_baseline_is_a_noop(tmp_path):
    # without a committed baseline, the step never fires (existing repos unaffected)
    repo = _repo(tmp_path, _BASE)            # no baseline file
    assert check_contract_integrity(repo) == []


def test_added_color_role_is_flagged(tmp_path):
    # widen the contract: add a 4th role beyond the baseline 3 -> drift
    cur = json.loads(json.dumps(_BASE))
    cur["colors"]["text-faint"] = "#5a6573"
    repo = _repo(tmp_path, cur, baseline=_BASE)
    findings = check_contract_integrity(repo)
    kinds = {f["kind"] for f in findings}
    assert "contract-drift" in kinds
    assert any("text-faint" in f["value"] for f in findings)
    # carries a file + a fix, like every other gate finding
    f = next(f for f in findings if "text-faint" in f["value"])
    assert f["file"].endswith("design-tokens.json")
    assert f["fix"]


def test_removed_color_role_is_flagged(tmp_path):
    cur = json.loads(json.dumps(_BASE))
    del cur["colors"]["primary"]
    repo = _repo(tmp_path, cur, baseline=_BASE)
    findings = check_contract_integrity(repo)
    assert any("primary" in f["value"] for f in findings)


def test_unchanged_contract_is_clean(tmp_path):
    repo = _repo(tmp_path, _BASE, baseline=_BASE)
    assert check_contract_integrity(repo) == []


def test_only_value_change_is_not_a_role_drift(tmp_path):
    # changing a role's HEX (not its set of roles) is a value edit, governed by the
    # normal drift/contrast steps — contract-integrity governs the ROLE SET, so it
    # must NOT fire on a pure value change (no role added/removed).
    cur = json.loads(json.dumps(_BASE))
    cur["colors"]["primary"] = "#1d4ed8"
    repo = _repo(tmp_path, cur, baseline=_BASE)
    assert [f for f in check_contract_integrity(repo) if "role" in f.get("detail", "").lower()
            or f["kind"] == "contract-drift" and "primary" in f["value"]] == []


def test_tokens_css_out_of_sync_is_flagged(tmp_path):
    # tokens.css must MIRROR the contract: a --color-* whose hex disagrees with the
    # contract is a mirror drift (the CSS silently diverged from the source of truth).
    css = ":root {\n  --color-bg: #0f1419;\n  --color-text: #e6edf3;\n  --color-primary: #ff0000;\n}\n"
    repo = _repo(tmp_path, _BASE, baseline=_BASE, tokens_css=css)
    findings = check_contract_integrity(repo)
    assert any(f["kind"] == "contract-mirror" for f in findings)
    assert any("primary" in f["value"] for f in findings)


def test_tokens_css_in_sync_is_clean(tmp_path):
    css = ":root {\n  --color-bg: #0f1419;\n  --color-text: #e6edf3;\n  --color-primary: #2563eb;\n}\n"
    repo = _repo(tmp_path, _BASE, baseline=_BASE, tokens_css=css)
    assert [f for f in check_contract_integrity(repo) if f["kind"] == "contract-mirror"] == []


def test_corrupt_baseline_does_not_crash(tmp_path):
    design = tmp_path / "design"
    design.mkdir(parents=True)
    (design / "design-tokens.json").write_text(json.dumps(_BASE))
    (design / BASELINE_NAME).write_text("{ not json")
    # a corrupt baseline must degrade to a no-op, never raise
    out = check_contract_integrity(str(tmp_path))
    assert isinstance(out, list)
