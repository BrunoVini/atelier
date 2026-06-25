"""Tests for design_report.py — the design-debt report + 0-100 coherence score.

Covers BOTH paths:
  - contract-based scoring (build_report, the original)
  - contract-FREE measured scoring (build_measured_report) for a repo that has
    design debt but no formal DESIGN.md / design-tokens.json — score derived from
    measured sprawl (palette/font/spacing/radius entropy, component dupes,
    off-token hardcoding) instead of drift-vs-contract.
"""
import os
import json

import design_report as dr


# ---- fixtures: write small repos --------------------------------------------

def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)


def _debt_repo(root):
    """A repo with REAL, measurable sprawl and a declared-but-ignored token file."""
    _write(root, "src/styles/tokens.css", """
:root {
  --color-primary: #2563eb;
  --color-text: #0f172a;
  --color-border: #e2e8f0;
  --space-2: 8px; --space-3: 16px; --space-4: 24px;
  --radius-md: 8px; --radius-lg: 12px;
  --font-sans: "Inter", sans-serif;
}
""")
    _write(root, "src/A.css", """
.a { font-family: "Roboto", sans-serif; color: #1a1a1a; background: #fafafa;
     padding: 17px; border-radius: 3px; border: 1px solid #eaeaea; }
.a2 { color: #2761e0; background: #fcfcfc; padding: 13px; border-radius: 5px; }
.a3 { color: #2569ee; padding: 11px; margin: 9px; border-radius: 4px; }
""")
    _write(root, "src/B.css", """
.b { font-family: "Helvetica Neue", sans-serif; color: #2c2c2c; background: #fbfbfb;
     padding: 23px; border-radius: 10px; }
.b2 { color: #2c66e8; padding: 7px; border-radius: 7px; border: 1px solid #d6d6d6; }
.b3 { color: #777777; padding: 15px; }
""")
    # one clean, token-driven file
    _write(root, "src/Clean.css", """
.c { font-family: var(--font-sans); color: var(--color-text);
     background: var(--color-bg); padding: var(--space-3);
     border-radius: var(--radius-md); border: 1px solid var(--color-border); }
""")
    _write(root, "src/Dash.jsx", "export function Card(){return null}")
    _write(root, "src/Bill.jsx", "export function Card(){return null}")


def _clean_repo(root):
    """A coherent repo: one font, tight palette, systematic spacing/radius, tokens used."""
    _write(root, "src/styles/tokens.css", """
:root {
  --color-primary: #2563eb; --color-text: #0f172a; --color-border: #e2e8f0;
  --color-bg: #ffffff; --color-muted: #64748b;
  --space-1: 4px; --space-2: 8px; --space-3: 16px; --space-4: 24px;
  --radius-md: 8px; --radius-lg: 12px;
  --font-sans: "Inter", sans-serif;
}
""")
    _write(root, "src/A.css", """
.a { font-family: var(--font-sans); color: var(--color-text);
     background: var(--color-bg); padding: var(--space-3);
     border-radius: var(--radius-md); border: 1px solid var(--color-border); }
.b { color: var(--color-primary); padding: var(--space-2); }
.c { color: var(--color-muted); padding: var(--space-4); border-radius: var(--radius-lg); }
""")


# ---- contract-free measured scoring -----------------------------------------

def test_measured_report_runs_without_a_contract(tmp_path):
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    assert "score" in rep and isinstance(rep["score"], int)
    assert 0 <= rep["score"] <= 100


def test_measured_report_scores_debt_repo_low_mid(tmp_path):
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    # heavy sprawl + competing fonts + off-grid spacing + dupes -> low-mid coherence
    assert rep["score"] <= 65, rep
    assert rep["score"] >= 15, rep


def test_measured_score_stays_defensible_not_floored(tmp_path):
    """A drifted-but-recoverable repo (real token system + a clean area) must NOT
    collapse to single digits — that would itself be a scoring-sanity miss."""
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    assert rep["score"] >= 28, rep   # not floored
    assert rep["credits"]["token_system"] > 0, rep  # credited the real declared system


def test_measured_report_scores_clean_repo_high(tmp_path):
    root = str(tmp_path)
    _clean_repo(root)
    rep = dr.build_measured_report(root)
    assert rep["score"] >= 80, rep


def test_clean_repo_outscores_debt_repo(tmp_path):
    d = os.path.join(str(tmp_path), "debt"); os.makedirs(d)
    c = os.path.join(str(tmp_path), "clean"); os.makedirs(c)
    _debt_repo(d)
    _clean_repo(c)
    assert dr.build_measured_report(c)["score"] > dr.build_measured_report(d)["score"]


def test_measured_report_counts_sprawl(tmp_path):
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    m = rep["measured"]
    # 3 font families (Inter declared + Roboto + Helvetica Neue)
    assert m["font_count"] >= 3, m
    # raw colors >> clusters (the sprawl signal)
    assert m["raw_color_count"] > m["color_cluster_count"], m
    assert m["raw_color_count"] >= 10, m
    # off-grid spacing values detected
    assert m["spacing_count"] >= 6, m
    # duplicated component
    assert "Card" in rep["hotspots"]["duplicate_components"], rep["hotspots"]


def test_measured_report_has_transparent_penalties(tmp_path):
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    pen = rep["penalties"]
    cr = rep["credits"]
    # the score must equal 100 minus summed (capped) penalties plus credits, clamped —
    # a transparent, fully-reconstructable derivation.
    expected = max(0, min(100, 100 - sum(pen.values()) + sum(cr.values())))
    assert rep["score"] == expected, rep
    # penalties cover the debt dimensions
    for k in ("palette", "fonts", "spacing", "radius", "duplicates", "off_token"):
        assert k in pen, pen
    for k in ("token_system", "token_adoption"):
        assert k in cr, cr


def test_measured_report_ranks_hotspots_by_impact(tmp_path):
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    hs = rep["hotspots"]["files"]
    assert len(hs) >= 2
    # hotspots are ordered by a numeric impact score, descending
    scores = [h["impact"] for h in hs]
    assert scores == sorted(scores, reverse=True), hs
    # the clean file should NOT be the top hotspot
    assert "Clean.css" not in hs[0]["file"], hs


def test_measured_report_detects_token_source_and_off_token(tmp_path):
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    # it should know the de-facto token source exists
    assert rep["token_source"] is not None
    assert rep["token_source"]["kind"] == "css-vars"
    # and report off-token hardcodes (near-dup colors that ignore a declared token)
    assert rep["measured"]["off_token_color_count"] >= 1, rep["measured"]


def test_measured_markdown_includes_score_and_hotspots(tmp_path):
    root = str(tmp_path)
    _debt_repo(root)
    rep = dr.build_measured_report(root)
    md = dr.to_markdown_measured(rep)
    assert "coherence" in md.lower()
    assert str(rep["score"]) in md
    assert "Hotspots" in md or "hotspot" in md.lower()
    # the derivation table must be present (transparent scoring)
    assert "Penalty" in md or "penalty" in md.lower()


# ---- the original contract-based path still works ---------------------------

def test_build_report_with_contract_still_works(tmp_path):
    root = str(tmp_path)
    _clean_repo(root)
    # synthesize a minimal contract so the original path resolves
    tokens = {
        "colors": {"primary": "#2563eb", "text": "#0f172a", "border": "#e2e8f0",
                   "bg": "#ffffff", "muted": "#64748b"},
        "fonts": ["Inter"], "spacing": ["4px", "8px", "16px", "24px"],
        "radius": ["8px", "12px"],
    }
    _write(root, "design/design-tokens.json", json.dumps(tokens))
    from contract import has_contract
    assert has_contract(root)
    rep = dr.build_report(root, root)
    assert 0 <= rep["score"] <= 100
