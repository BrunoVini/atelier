"""Tests for the contrast audit (#1) and design lint (#5)."""
import json
import os

from audit_contrast import audit, _nearest_passing
from lint_design import lint_repo


def test_audit_flags_low_contrast_pair():
    colors = {"foreground": "#14110e", "background": "#f7f5ef", "accent": "#c9a227"}
    rows = audit(colors)
    by_pair = {(r["text"], r["surface"]): r for r in rows}
    # ink on warm paper is excellent
    assert by_pair[("foreground", "background")]["aa_normal"] is True
    # gold on warm paper is low contrast -> fails AA-large
    assert by_pair[("accent", "background")]["aa_large"] is False
    assert "suggest" in by_pair[("accent", "background")]


def test_nearest_passing_returns_a_passing_shade():
    from scan_repo import contrast_ratio, _hex_to_rgb
    suggestion = _nearest_passing("#c9a227", "#f7f5ef", target=4.5)
    assert suggestion is not None
    assert contrast_ratio(_hex_to_rgb(suggestion), _hex_to_rgb("#f7f5ef")) >= 4.5


def test_lint_repo_flags_rogue_color_and_font(tmp_path):
    (tmp_path / "design").mkdir()
    contract = {
        "color": {"primary": {"$value": "#0b3d2e", "$type": "color"},
                  "accent": {"$value": "#c9a227", "$type": "color"}},
        "font": {"display": {"$value": ["Fraunces"], "$type": "fontFamily"}},
    }
    (tmp_path / "design" / "design-tokens.json").write_text(json.dumps(contract))
    (tmp_path / "rogue.css").write_text('.x{color:#ff00ff;font-family:"Comic Sans MS";}')
    (tmp_path / "ok.css").write_text('.y{color:#0b3d2e;}')  # near-exact -> no drift
    findings = lint_repo(str(tmp_path), str(tmp_path / "design" / "design-tokens.json"))
    kinds = {(f["kind"], f["value"]) for f in findings}
    assert ("color", "#ff00ff") in kinds
    assert ("font", "Comic Sans MS") in kinds
    assert not any(f["value"] == "#0b3d2e" for f in findings)  # contract color is clean
