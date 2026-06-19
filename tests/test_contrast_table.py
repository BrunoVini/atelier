"""A measured, provable contrast table the DESIGN.md can EMBED.

A design contract is more trustworthy when it PUBLISHES the per-pair WCAG ratios it
claims pass — a reader (or a second agent) can recompute and verify, instead of taking
"0 fails via the auditor" on faith. `contrast_table()` renders the enforced foreground/
background role pairs of a contract as a markdown table (ratio + AA verdict + required
level), per theme, ready to paste into §2/§10. This is the same math audit() already does;
it just makes the numbers visible in the doc.
"""
from audit_contrast import contrast_table, audit


def test_contrast_table_renders_markdown_with_measured_ratios():
    colors = {"foreground": "#111111", "background": "#ffffff",
              "primary": "#0b7285", "on-primary": "#ffffff"}
    md = contrast_table(colors)
    # a markdown table with a header row and a ratio column
    assert "|" in md and "Ratio" in md
    # the ink-on-paper pair is measured and present (21:1 black on white)
    assert "foreground" in md and "background" in md
    # ratios are printed as numbers like "21:1" / "21.0:1"
    import re
    assert re.search(r"\d+(\.\d+)?:1", md), "no measured ratio printed"
    # AA verdict per pair
    assert "AA" in md


def test_contrast_table_marks_a_failing_pair():
    # muted grey that fails AA on white must be shown as a FAIL, not hidden
    colors = {"foreground": "#111111", "background": "#ffffff",
              "muted": "#bbbbbb", "on-muted": "#cccccc"}
    md = contrast_table(colors)
    assert "FAIL" in md or "✗" in md.replace("✓", "")


def test_contrast_table_themed_emits_both_themes_when_dark_present():
    from audit_contrast import contrast_table_themed
    base = {"foreground": "#111111", "background": "#ffffff"}
    dark = {"foreground": "#f7f7f8", "background": "#0b0e12"}
    md = contrast_table_themed({"base": base, "dark": dark})
    assert "Light" in md and "Dark" in md
    # both themes contribute a ratio row
    assert md.count("foreground") >= 2


def test_contrast_table_themed_light_only_when_no_dark():
    from audit_contrast import contrast_table_themed
    base = {"foreground": "#111111", "background": "#ffffff"}
    md = contrast_table_themed({"base": base})
    assert "foreground" in md
    # no Dark section header when there is no dark theme
    assert "## Dark" not in md and "### Dark" not in md


def test_contrast_table_only_enforced_pairs_by_default():
    # informational brand×brand pairs are noise in a published table; default to enforced
    colors = {"foreground": "#111111", "background": "#ffffff",
              "primary": "#0b7285", "accent": "#e8590c"}
    md = contrast_table(colors)
    # primary-on-accent (brand×brand) is informational — should not appear by default
    assert "primary on accent" not in md and "accent on primary" not in md


def test_contrast_table_ratio_matches_audit():
    # the table's numbers must equal audit()'s numbers (same math, no drift)
    colors = {"foreground": "#3a4a5a", "background": "#ffffff"}
    rows = {(r["text"], r["surface"]): r["ratio"] for r in audit(colors)}
    md = contrast_table(colors)
    ratio = rows[("foreground", "background")]
    assert f"{ratio}" in md
