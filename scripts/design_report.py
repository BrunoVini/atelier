"""Design-debt report — one coherence score a team can track over time.

Composes the other measurements (drift lint, contrast fails, component
duplicates, palette entropy) into a single 0-100 coherence score + a
DESIGN-DEBT.md with hotspots, and appends to a history file so the trend is
visible. The PM/lead-facing artifact none of the source skills produce.

Two modes:
  - CONTRACT mode (`build_report`): the repo has a formal DESIGN.md /
    design-tokens.json — score drift, contrast fails, dupes, off-palette
    AGAINST that declared contract.
  - MEASURED / contract-free mode (`build_measured_report`): the repo has design
    debt but NO formal contract (the common case — tokens live in a `:root`
    block the components ignore, or nowhere at all). The score is derived from
    the repo's OWN measured sprawl: palette entropy (raw colors vs perceptual
    clusters), competing font families, an unsystematic spacing scale, radius
    sprawl, duplicated components, and off-token hardcoding (raw values that are
    near-duplicates of a declared `:root` token). This is what a design-debt
    audit of a real, drifted codebase actually needs.

Usage:
    python3 design_report.py <repo> [--contract design/design-tokens.json]
    # if no contract is given/found, falls back to measured (contract-free) mode

Contract-mode scoring (published so it's defensible, not a black box):
    start 100; -2 per drift finding (cap -40); -5 per contrast AA-large fail;
    -3 per duplicated component; -1 per off-palette color cluster (cap -15).
Measured-mode scoring is published the same way (see build_measured_report).
"""
import json
import os
import sys

from lint_design import lint_repo, _load_contract
from audit_contrast import audit, gate_failures
from census import build_census
from scan_repo import (scan_directory, check_drift, _parse_colors, _cluster_colors,
                       _delta_e, _hex_to_rgb, _rgb_to_hex, detect_token_source,
                       extract_token_props, _SKIP_DIRS, _STYLE_EXT, _CODE_EXT,
                       _MARKUP_EXT, _css_from_markup, _LEN)
from collections import Counter
import re


def _contract_colors(contract_path):
    colors_by_hex, fonts, _ = _load_contract(contract_path)
    return {name: hexv for hexv, name in colors_by_hex.items()}, sorted(fonts)


def build_report(repo, contract_path):
    drift = lint_repo(repo, contract_path)
    colors, fonts = _contract_colors(contract_path)
    contrast_rows = audit(colors)
    contrast_fails = gate_failures(contrast_rows)
    census = build_census(repo)
    dupes = census["duplicates"]
    scan = scan_directory(repo)
    off = check_drift(scan, {"colors": list(colors.values()), "fonts": fonts})
    off_palette = off["off_palette_colors"]

    penalties = {
        "drift": min(len(drift) * 2, 40),
        "contrast": len(contrast_fails) * 5,
        "duplicates": len(dupes) * 3,
        "palette_entropy": min(len(off_palette), 15),
    }
    score = max(0, 100 - sum(penalties.values()))
    grade = ("A" if score >= 90 else "B" if score >= 75 else
             "C" if score >= 60 else "D" if score >= 40 else "F")
    return {
        "score": score, "grade": grade, "penalties": penalties,
        "drift_count": len(drift), "contrast_fail_count": len(contrast_fails),
        "duplicate_count": len(dupes), "off_palette_count": len(off_palette),
        "hotspots": {
            "drift": drift[:10],
            "contrast_fails": [f"{r['text']} on {r['surface']} ({r['ratio']}:1)" for r in contrast_fails],
            "duplicates": dupes,
            "off_palette": off_palette[:10],
        },
    }


def to_markdown(rep, stamp=""):
    p = rep["penalties"]
    lines = [
        f"# DESIGN-DEBT — coherence {rep['score']}/100 (grade {rep['grade']})",
        f"_{stamp}_" if stamp else "",
        "",
        "| Factor | Count | Penalty |",
        "|--------|------:|--------:|",
        f"| Drift findings | {rep['drift_count']} | -{p['drift']} |",
        f"| Contrast AA-large fails | {rep['contrast_fail_count']} | -{p['contrast']} |",
        f"| Duplicated components | {rep['duplicate_count']} | -{p['duplicates']} |",
        f"| Off-palette colors | {rep['off_palette_count']} | -{p['palette_entropy']} |",
        "",
        "## Hotspots",
    ]
    for r in rep["hotspots"]["contrast_fails"]:
        lines.append(f"- contrast: {r}")
    for d in rep["hotspots"]["drift"]:
        lines.append(f"- drift: {d['file']}:{d['line']} {d['value']} → {d['fix']}")
    for name, files in rep["hotspots"]["duplicates"].items():
        lines.append(f"- duplicate component `{name}`: {', '.join(files)}")
    lines.append("")
    lines.append("> Scoring: -2/drift (cap 40), -5/contrast fail, -3/duplicate, -1/off-palette (cap 15).")
    return "\n".join(l for l in lines if l is not None)


# =============================================================================
# MEASURED / contract-free coherence score
# =============================================================================
#
# A design-debt audit usually runs on a repo that has NO formal contract — the
# tokens, if they exist at all, live in a `:root` block the components ignore.
# We can still produce a defensible 0-100 coherence score by measuring the
# repo's OWN sprawl. The score is published as transparent per-dimension
# penalties so it is auditable, not a black box:
#
#   start 100, then subtract (each penalty capped so one dimension can't sink it):
#     palette    : the entropy between raw distinct colors and their perceptual
#                  clusters + the absolute cluster count over a healthy budget
#     fonts      : competing font families beyond ~2
#     spacing    : distinct spacing values beyond a systematic scale (~7)
#     radius     : distinct radii beyond ~4
#     duplicates : duplicated component implementations
#     off_token  : raw color literals that are near-duplicates of a declared
#                  `:root` token but were hardcoded anyway (token system ignored)
#   then ADD BACK small coherence credits (so a repo with a real token system and
#   genuinely clean areas never floors at ~0 the way a sum-of-caps otherwise would —
#   a coherence score must stay defensible at the low end, not collapse to single
#   digits for a drifted-but-recoverable codebase):
#     +token_credit : a real declared token source exists (the INTENT is coherent)
#     +adoption     : proportional to how many design files actually use var(--token)
#
# The caps are sized so the WORST realistic repo lands in the low 30s, not 0:
# sum of all caps ≈ 72, minus up to ~14 of credits → a fully-drifted repo ≈ 40,
# a chaotic-no-system repo ≈ low-mid 20s, a coherent repo ≥ 80.
#
# Healthy budgets (what a coherent small/mid frontend keeps):
_PALETTE_BUDGET = 12      # distinct color clusters
_FONT_BUDGET = 2          # font families (one display + one body, say)
_SPACING_BUDGET = 7       # steps in a sane spacing scale
_RADIUS_BUDGET = 4        # radius steps
# Per-dimension penalty caps (so the score stays defensible / no single sink):
_CAP = {"palette": 22, "fonts": 10, "spacing": 16, "radius": 8,
        "duplicates": 8, "off_token": 12}


def _iter_repo_files(root):
    """Yield (relpath, style_or_code_text) for every design-bearing file, with
    HTML reduced to its CSS so body copy is never read as colors."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if not (fn.endswith(_STYLE_EXT) or fn.endswith(_CODE_EXT)
                    or fn.endswith(_MARKUP_EXT) or fn.startswith("tailwind.config")):
                continue
            try:
                if os.path.getsize(p) > 400_000:
                    continue
                text = open(p, encoding="utf-8").read()
            except Exception:
                continue
            rel = os.path.relpath(p, root)
            if fn.endswith(_MARKUP_EXT):
                text = _css_from_markup(text)
            yield rel, text


def _declared_token_colors(root, token_source):
    """Hexes declared in the repo's de-facto token source (a `:root --color-*`
    block or a tokens file). Used to detect off-token hardcoding."""
    if not token_source:
        return []
    path = os.path.join(root, token_source.get("path", ""))
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return []
    props = extract_token_props(text)
    out = []
    for hexv in props.get("colors", []):
        try:
            out.append(_hex_to_rgb(hexv))
        except Exception:
            pass
    # also any raw colors that appear inside a --color-* / --*-color declaration
    for m in re.findall(r"--[\w-]*colou?r[\w-]*\s*:\s*([^;}]+)", text, re.I):
        for rgb in _parse_colors(m):
            out.append(rgb)
    # de-dupe
    seen, uniq = set(), []
    for rgb in out:
        if rgb not in seen:
            seen.add(rgb); uniq.append(rgb)
    return uniq


def _uses_token_indirection(text):
    """True-ish count of var(--token) references — evidence the file uses the
    token system instead of hardcoding."""
    return len(re.findall(r"var\(\s*--", text))


def _spacing_off_grid(values, grid=8):
    """Spacing tokens (e.g. '7px','1.1rem') that are NOT a multiple of the grid
    (rem treated as 16px). 0 and grid multiples are on-system."""
    off = []
    for tok in values:
        m = _LEN.match(tok)
        if not m:
            continue
        n, unit = float(m.group(1)), m.group(2)
        px = n * (16 if unit == "rem" else 1)
        if px > 0 and px % grid != 0:
            off.append(tok)
    return off


def build_measured_report(root):
    """Contract-free coherence score from the repo's measured sprawl. See the
    module docstring + the budget/cap constants above for the published formula."""
    scan = scan_directory(root)

    # --- raw vs clustered palette (the sprawl signal) ---
    raw = Counter()
    file_color_reps = {}   # rel -> set of representative hexes (for hotspot scoring)
    per_file_raw = {}
    for rel, text in _iter_repo_files(root):
        cs = _parse_colors(text)
        per_file_raw[rel] = cs
        for c in cs:
            raw[c] += 1
    clusters, rep_of = _cluster_colors(raw)
    raw_color_count = len(raw)
    cluster_count = len(clusters)
    for rel, cs in per_file_raw.items():
        file_color_reps[rel] = set(rep_of.get(c) for c in cs)

    fonts = scan.get("fonts", [])
    spacing = scan.get("spacing", [])
    radius = scan.get("radius", [])
    off_grid = _spacing_off_grid(spacing)

    census = build_census(root)
    dupes = census.get("duplicates", {})

    # --- off-token hardcoding: raw colors that are near-dups of a declared token ---
    token_source = scan.get("token_source")
    declared = _declared_token_colors(root, token_source)
    off_token_colors = []
    if declared:
        for rgb in raw:
            nearest = min((_delta_e(rgb, d) for d in declared), default=999)
            # within 12 ΔE of a declared token but NOT identical to it => a
            # near-dup hardcode that should have been the token.
            if 0 < nearest <= 12:
                off_token_colors.append(_rgb_to_hex(*rgb))
            elif nearest == 0:
                pass  # an exact reuse of the token value (still hardcoded, milder)

    # --- penalties (each capped) ---
    # palette: cluster-count overflow + raw/cluster entropy (sprawl ratio)
    cluster_over = max(0, cluster_count - _PALETTE_BUDGET)
    entropy = max(0, raw_color_count - cluster_count)   # raw dups collapsed away
    palette_pen = min(cluster_over * 2 + entropy * 1, _CAP["palette"])
    font_pen = min(max(0, len(fonts) - _FONT_BUDGET) * 5, _CAP["fonts"])
    spacing_pen = min(max(0, len(spacing) - _SPACING_BUDGET) * 2 + len(off_grid) * 1,
                      _CAP["spacing"])
    radius_pen = min(max(0, len(radius) - _RADIUS_BUDGET) * 3, _CAP["radius"])
    dup_pen = min(len(dupes) * 6, _CAP["duplicates"])
    off_token_pen = min(len(set(off_token_colors)) * 2, _CAP["off_token"])

    penalties = {
        "palette": palette_pen, "fonts": font_pen, "spacing": spacing_pen,
        "radius": radius_pen, "duplicates": dup_pen, "off_token": off_token_pen,
    }

    # --- coherence credits (keep the low end defensible) ---
    # adoption: share of design files that reference var(--token) at all.
    design_files = [(rel, t) for rel, t in _iter_repo_files(root)
                    if rel.endswith(_STYLE_EXT) or rel.endswith(_CODE_EXT)]
    n_design = len(design_files) or 1
    n_token_using = sum(1 for _, t in design_files if _uses_token_indirection(t) > 0)
    adoption_share = n_token_using / n_design
    token_credit = 6 if token_source else 0          # a real declared system exists
    adoption_credit = round(adoption_share * 8)       # up to +8 for full adoption
    credits = {"token_system": token_credit, "token_adoption": adoption_credit}

    raw_score = 100 - sum(penalties.values()) + sum(credits.values())
    score = max(0, min(100, raw_score))
    grade = ("A" if score >= 90 else "B" if score >= 75 else
             "C" if score >= 60 else "D" if score >= 40 else "F")

    # --- hotspots: rank files by how much debt they carry ---
    off_token_set = set(off_token_colors)
    declared_reps = set()
    if declared:
        for d in declared:
            declared_reps.add(rep_of.get(d))
    hotspots = []
    for rel, text in _iter_repo_files(root):
        if not rel.endswith(_STYLE_EXT + _CODE_EXT + _MARKUP_EXT):
            pass
        reps = file_color_reps.get(rel, set())
        raw_here = per_file_raw.get(rel, [])
        n_colors = len(set(_rgb_to_hex(*c) for c in raw_here))
        n_off_token = len(set(_rgb_to_hex(*c) for c in raw_here) & off_token_set)
        # fonts/spacing/radius hardcoded in this file
        n_fonts = len(set(re.findall(r"font-family:\s*[\"']?([A-Za-z][\w\s-]+)", text)))
        n_offgrid = len(_spacing_off_grid(_file_spacing(text)))
        n_var = _uses_token_indirection(text)
        impact = (n_colors * 1.0 + n_off_token * 2.0 + n_fonts * 1.5
                  + n_offgrid * 1.0 - min(n_var, 12) * 0.5)
        if impact <= 0:
            continue
        hotspots.append({
            "file": rel, "impact": round(impact, 1),
            "colors": n_colors, "off_token_colors": n_off_token,
            "font_families": n_fonts, "off_grid_spacing": n_offgrid,
            "uses_tokens": n_var,
        })
    hotspots.sort(key=lambda h: h["impact"], reverse=True)

    return {
        "mode": "measured",
        "score": int(score), "grade": grade, "penalties": penalties,
        "credits": credits,
        "token_source": token_source,
        "measured": {
            "raw_color_count": raw_color_count,
            "color_cluster_count": cluster_count,
            "font_count": len(fonts), "fonts": fonts,
            "spacing_count": len(spacing), "off_grid_spacing_count": len(off_grid),
            "radius_count": len(radius),
            "duplicate_component_count": len(dupes),
            "off_token_color_count": len(set(off_token_colors)),
        },
        "hotspots": {
            "files": hotspots[:10],
            "duplicate_components": dupes,
            "off_grid_spacing": off_grid,
            "off_token_colors": sorted(set(off_token_colors))[:20],
            "top_clusters": [{"hex": c["hex"], "count": c["count"]} for c in clusters[:12]],
            "fonts": fonts,
        },
    }


_FILE_SPACING_PROP = re.compile(
    r"(?:padding|margin|gap|top|bottom|left|right|inset)[^:;{}]*:\s*([^;{}]+)", re.I)


def _file_spacing(text):
    vals = []
    for decl in _FILE_SPACING_PROP.findall(text):
        for num, unit in _LEN.findall(decl):
            vals.append(f"{num}{unit}")
    return list(dict.fromkeys(vals))


def to_markdown_measured(rep, stamp=""):
    p = rep["penalties"]
    cr = rep.get("credits", {})
    m = rep["measured"]
    ts = rep.get("token_source")
    lines = [
        f"# DESIGN-DEBT — coherence {rep['score']}/100 (grade {rep['grade']})",
        f"_{stamp}_" if stamp else "",
        "",
        "_Contract-free score: derived from the repo's own measured sprawl "
        "(no formal DESIGN.md found)._",
        "",
        "## Score derivation",
        "| Dimension | Measured | Penalty |",
        "|-----------|----------|--------:|",
        f"| Palette | {m['raw_color_count']} raw colors → {m['color_cluster_count']} perceptual clusters | -{p['palette']} |",
        f"| Fonts | {m['font_count']} families: {', '.join(m['fonts']) or '—'} | -{p['fonts']} |",
        f"| Spacing | {m['spacing_count']} distinct values ({m['off_grid_spacing_count']} off-grid) | -{p['spacing']} |",
        f"| Radius | {m['radius_count']} distinct values | -{p['radius']} |",
        f"| Duplicated components | {m['duplicate_component_count']} | -{p['duplicates']} |",
        f"| Off-token hardcodes | {m['off_token_color_count']} near-dup colors of a declared token | -{p['off_token']} |",
        f"| _Credit:_ declared token system exists | {'yes' if cr.get('token_system') else 'no'} | +{cr.get('token_system', 0)} |",
        f"| _Credit:_ token adoption in design files | — | +{cr.get('token_adoption', 0)} |",
        f"| **Total** | | **{rep['score']}/100** |",
        "",
    ]
    if ts:
        lines.append(f"> De-facto token source: `{ts.get('path')}` ({ts.get('kind')}, "
                     f"{ts.get('confidence')} confidence) — declared but largely ignored.")
        lines.append("")
    lines.append("## Hotspots (worst files first)")
    lines.append("| File | Impact | Colors | Off-token | Fonts | Off-grid | var() |")
    lines.append("|------|-------:|-------:|----------:|------:|---------:|------:|")
    for h in rep["hotspots"]["files"]:
        lines.append(f"| `{h['file']}` | {h['impact']} | {h['colors']} | "
                     f"{h['off_token_colors']} | {h['font_families']} | "
                     f"{h['off_grid_spacing']} | {h['uses_tokens']} |")
    lines.append("")
    if rep["hotspots"]["duplicate_components"]:
        lines.append("## Duplicated components")
        for n, files in rep["hotspots"]["duplicate_components"].items():
            lines.append(f"- `{n}`: {', '.join(files)}")
        lines.append("")
    lines.append("> Scoring (published): start 100; "
                 "palette -2/cluster over 12 + -1/raw-dup (cap 22); fonts -5 over 2 (cap 10); "
                 "spacing -2/value over 7 + -1/off-grid (cap 16); radius -3 over 4 (cap 8); "
                 "-6/duplicate component (cap 8); off-token -2/near-dup hardcode (cap 12); "
                 "then +6 if a declared token system exists and +0–8 for token adoption.")
    return "\n".join(l for l in lines if l is not None)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args:
        print("usage: design_report.py <repo> [--contract design/design-tokens.json] [--stamp <iso>]")
        sys.exit(2)
    from contract import has_contract
    repo = args[0]
    contract = args[args.index("--contract") + 1] if "--contract" in args else repo
    stamp = args[args.index("--stamp") + 1] if "--stamp" in args else ""
    measured = "--measured" in args
    if measured or not has_contract(contract):
        rep = build_measured_report(repo)
        md = to_markdown_measured(rep, stamp)
        score, penalties = rep["score"], rep["penalties"]
    else:
        rep = build_report(repo, contract)
        md = to_markdown(rep, stamp)
        score, penalties = rep["score"], rep["penalties"]
    open(os.path.join(repo, "DESIGN-DEBT.md"), "w", encoding="utf-8").write(md + "\n")
    # append to history (trend)
    hist = os.path.join(repo, "design", "debt-history.jsonl")
    os.makedirs(os.path.dirname(hist), exist_ok=True)
    with open(hist, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"stamp": stamp, "score": score, "penalties": penalties}) + "\n")
    print(md)
