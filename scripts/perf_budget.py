"""Performance budget tied to design decisions.

A beautiful page that ships four font weights and a 2 MB hero is a senior-level
trade-off the other tools never surface. This estimates the weight a *design*
choice implies — web-font payload, image bytes, CSS size, animation layers — and
checks it against a budget, so "add a third font weight" comes with "+90 KB".

Usage:
    python3 perf_budget.py <page.html> [--config design/atelier.config.json] [--json]
"""
import json
import os
import re
import sys

# Rough per-(family,weight,latin-subset) WOFF2 cost.
_KB_PER_FONT_WEIGHT = 25

DEFAULT_BUDGET = {
    "font_weights_max": 5,      # total distinct family×weight
    "font_kb_max": 150,
    "image_kb_max": 800,
    "css_kb_max": 100,
    "animation_layers_max": 12,
}

_GFONT_WGHT = re.compile(r"family=([A-Za-z0-9+]+):wght@([\d;]+)")
_GFONT_PLAIN = re.compile(r"family=([A-Za-z0-9+]+)(?=&|\")")
_FONTFACE = re.compile(r"@font-face", re.I)
_IMG = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
_URL = re.compile(r'url\(["\']?([^"\')]+)["\']?\)')
_STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
_ANIM = re.compile(r"@keyframes|animation\s*:|transition\s*:", re.I)


def _estimate_fonts(html):
    weights = 0
    for fam, wghts in _GFONT_WGHT.findall(html):
        weights += len([w for w in wghts.split(";") if w])
    # plain family= with no wght implies ~1 weight
    plain = set(_GFONT_PLAIN.findall(html)) - {f for f, _ in _GFONT_WGHT.findall(html)}
    weights += len(plain)
    weights += len(_FONTFACE.findall(html))
    return weights, weights * _KB_PER_FONT_WEIGHT


def _estimate_images(html, base_dir):
    total = 0
    refs = _IMG.findall(html) + _URL.findall(html)
    for ref in refs:
        if ref.startswith("data:"):
            total += len(ref) * 3 // 4 // 1024  # base64 -> ~KB
        elif not ref.startswith(("http://", "https://", "/")):
            p = os.path.join(base_dir, ref)
            if os.path.exists(p):
                total += os.path.getsize(p) // 1024
            else:
                total += 150  # unknown local image, assume 150KB
        else:
            total += 150  # remote/absolute, assume 150KB
    return len(refs), total


def analyze(html_path, budget=None):
    budget = {**DEFAULT_BUDGET, **(budget or {})}
    html = open(html_path, encoding="utf-8").read()
    base = os.path.dirname(os.path.abspath(html_path))
    weights, font_kb = _estimate_fonts(html)
    img_count, img_kb = _estimate_images(html, base)
    css_kb = sum(len(b) for b in _STYLE_BLOCK.findall(html)) // 1024
    anim_layers = len(_ANIM.findall(html))

    checks = [
        ("font weights", weights, budget["font_weights_max"]),
        ("font KB (est)", font_kb, budget["font_kb_max"]),
        ("image KB (est)", img_kb, budget["image_kb_max"]),
        ("inline CSS KB", css_kb, budget["css_kb_max"]),
        ("animation layers", anim_layers, budget["animation_layers_max"]),
    ]
    results = [{"metric": m, "value": v, "budget": b, "over": v > b} for m, v, b in checks]
    return {"file": os.path.basename(html_path), "image_refs": img_count, "checks": results,
            "pass": not any(r["over"] for r in results)}


def _format(report):
    lines = [f"Performance budget — {report['file']}", ""]
    for r in report["checks"]:
        tag = "⚠ OVER" if r["over"] else "ok"
        lines.append(f"  {r['metric']:<18} {r['value']:>6}  / {r['budget']:<6} {tag}")
    lines.append("")
    lines.append("PASS" if report["pass"] else "OVER BUDGET — trim fonts/images/CSS or raise the budget")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: perf_budget.py <page.html> [--config <json>] [--json]")
        sys.exit(2)
    page = args[0]
    budget = None
    if "--config" in args:
        cfg = args[args.index("--config") + 1]
        if os.path.exists(cfg):
            budget = json.load(open(cfg)).get("perf_budget")
    report = analyze(page, budget)
    print(json.dumps(report, indent=2) if "--json" in args else _format(report))
    sys.exit(0 if report["pass"] else 1)
