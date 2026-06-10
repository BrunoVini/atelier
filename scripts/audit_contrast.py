"""WCAG contrast audit against the project's locked palette.

atelier already extracted the *real* colors into design tokens, so it can do the
math the knowledge-base skills only describe: for every text/foreground color
paired with every surface/background color, compute the WCAG contrast ratio and
report AA/AAA pass per size class — and suggest the nearest passing shade.

Usage:
    python3 audit_contrast.py design/design-tokens.json
    python3 audit_contrast.py design/design-tokens.json --json
"""
import json
import sys

from scan_repo import contrast_ratio, _hex_to_rgb, _rgb_to_hex

# Name heuristics: which token roles are "ink" (text) vs "surface" (background).
_TEXT_HINTS = ("foreground", "text", "on-", "on_", "ink", "heading", "body")
_SURFACE_HINTS = ("background", "bg", "surface", "card", "muted", "base", "paper")

AA_NORMAL, AA_LARGE, AAA_NORMAL = 4.5, 3.0, 7.0


def _load_colors(target):
    """Return {name: '#hex'} resolved from a tokens.json OR the repo's DESIGN.md."""
    from contract import resolve_contract
    return {n: v for n, v in resolve_contract(target)["colors"].items()
            if isinstance(v, str) and v.startswith("#")}


def load_themed_colors(target):
    """Return {"base": {name: hex}, "dark": {name: hex}} — the contract's light
    palette plus, when the machine block ships a co-equal DARK palette, the dark
    one. Each theme is audited independently so a dark-only contrast failure is
    caught by the gate instead of hiding in prose."""
    from contract import resolve_contract
    c = resolve_contract(target)
    def hexes(d):
        return {n: v for n, v in (d or {}).items() if isinstance(v, str) and v.startswith("#")}
    out = {"base": hexes(c.get("colors"))}
    dark = hexes(c.get("dark_colors"))
    if dark:
        out["dark"] = dark
    return out


def _role(name):
    low = name.lower()
    if any(h in low for h in _TEXT_HINTS):
        return "text"
    if any(h in low for h in _SURFACE_HINTS):
        return "surface"
    return "both"  # primary/accent can be either text or fill


def _on_base(name):
    """For an `on-primary`/`on_accent` token, return its base ('primary')."""
    low = name.lower().replace("_", "-")
    return low[3:] if low.startswith("on-") else None


def _enforced(t, s):
    """A pairing the design certainly needs (so it may fail the gate):
    a real text color on a real surface, or an `on-X` token on its `X`.
    Pairings involving a brand fill as the surface are advisory only — the real
    text there is an `on-*` token, which may not be in the palette."""
    base = _on_base(t)
    if base is not None:
        return s.lower() == base or s.lower().endswith(base)
    return _role(t) == "text" and _role(s) == "surface"


def _nearest_passing(text_hex, surface_hex, target=AA_NORMAL):
    """Blend the text color toward black/white until it clears `target`."""
    sr = _hex_to_rgb(surface_hex)
    best = None
    for towards in ((0, 0, 0), (255, 255, 255)):
        for step in range(1, 21):
            t = step / 20
            mixed = tuple(round(o + (d - o) * t) for o, d in zip(_hex_to_rgb(text_hex), towards))
            if contrast_ratio(mixed, sr) >= target:
                cand = _rgb_to_hex(*mixed)
                if best is None:
                    best = cand
                break
    return best


# Tokens whose text is genuinely large (headings/display) only need AA-large (3:1).
_LARGE_HINTS = ("heading", "display", "title", "hero", "h1", "h2", "h3", "lead")


def audit(colors):
    """Return a list of pairings with ratios and AA/AAA verdicts.

    Each enforced pair carries a `required` threshold: AA-normal (4.5:1) for body
    text, AA-large (3:1) only for heading/display roles — so the gate no longer
    green-lights real AA-normal failures.
    """
    texts = [n for n in colors if _role(n) in ("text", "both")]
    surfaces = [n for n in colors if _role(n) in ("surface", "both")]
    rows = []
    for t in texts:
        for s in surfaces:
            if t == s:
                continue
            ratio = round(contrast_ratio(_hex_to_rgb(colors[t]), _hex_to_rgb(colors[s])), 2)
            # Only enforced pairings (real text on a real surface, or on-X on X)
            # can fail the gate; brand-fill pairings are advisory.
            informational = not _enforced(t, s)
            large = any(h in t.lower() for h in _LARGE_HINTS)
            required = AA_LARGE if large else AA_NORMAL
            passes = ratio >= required
            row = {
                "text": t, "surface": s, "ratio": ratio,
                "aa_normal": ratio >= AA_NORMAL,
                "aa_large": ratio >= AA_LARGE,
                "aaa_normal": ratio >= AAA_NORMAL,
                "required": required, "passes": passes,
                "informational": informational,
            }
            if not passes and not informational:
                row["suggest"] = _nearest_passing(colors[t], colors[s], required)
            rows.append(row)
    return rows


def gate_failures(rows):
    """Enforced pairs that fail their required WCAG threshold (for the CI gate)."""
    return [r for r in rows if not r["informational"] and not r["passes"]]


def _format(rows):
    lines = ["Contrast audit (WCAG):", ""]
    for r in sorted(rows, key=lambda x: x["ratio"]):
        if r.get("informational"):
            tag = "low (brand×brand — informational)"
        elif r["passes"]:
            tag = "AA✓" if r["aa_normal"] else "AA-large ✓ (heading role)"
        else:
            need = "AA-large 3:1" if r["required"] == AA_LARGE else "AA 4.5:1"
            tag = f"FAIL (needs {need}; suggest {r.get('suggest', '?')})"
        lines.append(f"  {r['ratio']:>5}:1  {r['text']} on {r['surface']:<14} {tag}")
    fails = len(gate_failures(rows))
    lines.append("")
    lines.append(f"{len(rows)} pairings, {fails} fail their required WCAG level "
                 "(AA 4.5:1 for text, 3:1 for heading roles).")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: audit_contrast.py <repo | design-tokens.json | DESIGN.md> [--json]")
        sys.exit(2)
    themes = load_themed_colors(args[0])
    by_theme = {name: audit(cols) for name, cols in themes.items()}
    fails = sum(len(gate_failures(rows)) for rows in by_theme.values())
    if "--json" in args:
        print(json.dumps(by_theme if len(by_theme) > 1 else by_theme["base"], indent=2))
    else:
        for name, rows in by_theme.items():
            if len(by_theme) > 1:
                print(f"\n=== {name} theme ===")
            print(_format(rows))
    sys.exit(1 if fails else 0)
