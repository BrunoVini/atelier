"""Typography preflight — a deterministic PRE-SCAN that surfaces the typographic
FACTS of a page (font families, the size set + smallest body size, line-heights,
the modular-scale ratio span, the measure/max-width signal) and runs the existing
typographic tells in ONE place, BEFORE generation or judgment.

It does NOT add a CI gate — it's advisory. The findings reuse the deterministic rules
already living in slop_ported / slop_check (no regex is duplicated): the body-typography
tells (tiny-body-text, tight-leading, label-line-height, wide-tracking, justified-text…)
come from `ported_tells`, and the page-level ones (flat-type-hierarchy, oversized-h1,
single-font, too-many-fonts) come from `slop_check.check_html`. The preflight keeps only
the typography-relevant kinds so the pre-scan is focused.

Usage:
    python3 typography_preflight.py <page.html>
    python3 typography_preflight.py <page.html> --json
"""
import json
import re
import sys

from slop_ported import (FONT_DECL, GFONT, TAG, css_blocks, ported_tells,
                         _FONT_FALLBACKS, _TW_TEXT_SIZES)

# Which finding kinds are TYPOGRAPHY (the preflight's remit) — others (color, motion,
# layout) belong to the full slop battery, not this pre-scan.
TYPO_KINDS = {
    "tiny-body-text", "tight-leading", "label-line-height", "wide-tracking",
    "justified-text", "extreme-negative-tracking", "line-length-risk",
    "flat-type-hierarchy", "oversized-h1", "single-font", "too-many-fonts",
    "overused-font", "generic-font", "skipped-heading", "all-caps-body",
}

_FS_RX = re.compile(r"font-size\s*:\s*([\d.]+)(px|rem|em)\b", re.I)
_FS_CLAMP_RX = re.compile(r"font-size\s*:\s*clamp\(\s*([\d.]+)(px|rem|em)\s*,[^,]+,"
                          r"\s*([\d.]+)(px|rem|em)\s*\)", re.I)
_LH_RX = re.compile(r"line-height\s*:\s*([\d.]+)(px|rem|em|%)?\b", re.I)
_MAXW_RX = re.compile(r"max-width|max-inline-size|\bmax-w-|[\d.]+\s*ch\b", re.I)


def _px(value, unit):
    return round(float(value) * (1 if unit.lower() == "px" else 16), 1)


def _fonts(html):
    """Distinct real font families in play (first family of each stack + Google Fonts)."""
    fonts = set()
    for decl in FONT_DECL.findall(html):
        first = decl.split(",")[0].strip().strip("'\"").lower()
        if first and "var(" not in first and "fallback" not in first \
                and first not in _FONT_FALLBACKS:
            fonts.add(first)
    for fam in GFONT.findall(html):
        fonts.add(fam.replace("+", " ").lower())
    return sorted(fonts)


def _sizes(html, class_attrs):
    """The set of px-normalized font-sizes declared anywhere (CSS, clamp, Tailwind)."""
    sizes = set()
    for m in _FS_RX.finditer(html):
        px = _px(m.group(1), m.group(2))
        if 0 < px < 400:
            sizes.add(px)
    for m in _FS_CLAMP_RX.finditer(html):
        for v, u in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
            sizes.add(_px(v, u))
    for cls in class_attrs:
        for tok, px in _TW_TEXT_SIZES.items():
            if re.search(rf"\b{tok}\b", cls):
                sizes.add(float(px))
    return sorted(sizes)


def _line_heights(html):
    """Distinct line-height values seen (unitless kept as-is; px/rem/em/%% tagged)."""
    out = set()
    for m in _LH_RX.finditer(html):
        unit = (m.group(2) or "").lower()
        out.add(f"{m.group(1)}{unit}" if unit else m.group(1))
    return sorted(out)


def preflight(html):
    """Return {"facts": {...}, "findings": [...]} — typography facts plus the
    typography-relevant findings (reused from the existing deterministic rules)."""
    html = html or ""
    class_attrs = re.findall(r'class\s*=\s*["\']([^"\']*)["\']', html, re.I)
    fonts = _fonts(html)
    sizes = _sizes(html, class_attrs)
    line_heights = _line_heights(html)
    # smallest body-ish size: smallest declared size at body scale (< 24px); else the
    # overall smallest; None when no sizes are declared.
    body_sizes = [s for s in sizes if s < 24]
    smallest_body = min(body_sizes) if body_sizes else (min(sizes) if sizes else None)
    scale_span = round(max(sizes) / min(sizes), 2) if len(sizes) >= 2 and min(sizes) else None
    has_measure = bool(_MAXW_RX.search(html))

    facts = {
        "fonts": fonts,
        "font_count": len(fonts),
        "sizes_px": sizes,
        "smallest_body_px": smallest_body,
        "line_heights": line_heights,
        "scale_span": scale_span,
        "has_measure": has_measure,
    }

    # Reuse existing rules — don't re-implement any regex. ported_tells covers the
    # body/label typography tells; check_html adds the page-level type rules.
    findings = list(ported_tells(html))
    try:
        from slop_check import check_html
        findings += check_html(html)
    except Exception:
        pass
    # de-dup (kind, detail) and keep only typography-relevant kinds
    seen, typo = set(), []
    for f in findings:
        if f.get("kind") not in TYPO_KINDS:
            continue
        key = (f["kind"], f.get("detail"))
        if key in seen:
            continue
        seen.add(key)
        typo.append(f)
    return {"facts": facts, "findings": typo}


def _format(result):
    f = result["facts"]
    lines = ["Typography preflight:", ""]
    lines.append(f"  fonts ({f['font_count']}): {', '.join(f['fonts']) or '—'}")
    lines.append(f"  sizes (px): {f['sizes_px'] or '—'}")
    lines.append(f"  smallest body size: "
                 f"{(str(f['smallest_body_px']) + 'px') if f['smallest_body_px'] else '—'}")
    lines.append(f"  line-heights: {', '.join(f['line_heights']) or '—'}")
    lines.append(f"  modular-scale span: "
                 f"{(str(f['scale_span']) + ':1') if f['scale_span'] else '—'}")
    lines.append(f"  measure/max-width set: {'yes' if f['has_measure'] else 'no'}")
    lines.append("")
    if result["findings"]:
        lines.append(f"  {len(result['findings'])} typography finding(s):")
        for fi in result["findings"]:
            lines.append(f"    [{fi['severity']}] {fi['kind']}: {fi['detail']}")
    else:
        lines.append("  no typography findings.")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    path = next((a for a in args if not a.startswith("-")), None)
    if not path:
        print("usage: typography_preflight.py <page.html> [--json]")
        sys.exit(2)
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    result = preflight(html)
    if "--json" in args:
        print(json.dumps(result, indent=2))
    else:
        print(_format(result))
