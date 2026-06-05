"""Build a living style guide from the design tokens (+ census + contrast).

Renders the *actual measured* design system — swatches with contrast labels, the
type scale, spacing ruler, radius samples, and the component inventory — as a
self-contained HTML page that stays in sync because it's generated from
`design/design-tokens.json`. Serve it through the preview server or open directly.

Usage:
    python3 build_styleguide.py [design/design-tokens.json] [-o design/styleguide.html]
"""
import json
import os
import sys

from scan_repo import contrast_ratio, _hex_to_rgb


def _colors(tokens):
    out = {}
    for name, node in (tokens.get("color", {}) or {}).items():
        v = node.get("$value", node) if isinstance(node, dict) else node
        if isinstance(v, str):
            out[name] = v
    return out


def _scalar(tokens, group):
    out = {}
    for name, node in (tokens.get(group, {}) or {}).items():
        v = node.get("$value", node) if isinstance(node, dict) else node
        out[name] = v[0] if isinstance(v, list) else v
    return out


def _best_text_on(bg_hex, colors):
    """Pick the palette color with the best contrast on bg for the swatch label."""
    bg = _hex_to_rgb(bg_hex)
    inks = [colors.get("foreground", "#111"), colors.get("background", "#fff"), "#000", "#fff"]
    return max(inks, key=lambda c: contrast_ratio(_hex_to_rgb(c), bg))


def build(tokens, components=None):
    colors = _colors(tokens)
    fonts = _scalar(tokens, "font")
    space = _scalar(tokens, "space")
    radius = _scalar(tokens, "radius")
    bg = colors.get("background", "#ffffff")
    fg = colors.get("foreground", "#111111")
    display = fonts.get("display", fonts.get("heading", "Georgia, serif"))
    body = fonts.get("body", "system-ui, sans-serif")

    swatches = []
    for name, hexv in colors.items():
        label_on = _best_text_on(hexv, colors)
        ratio = round(contrast_ratio(_hex_to_rgb(label_on), _hex_to_rgb(hexv)), 1)
        swatches.append(
            f'<div class="sw" style="background:{hexv};color:{label_on}">'
            f'<b>{name}</b><span>{hexv}</span><span>{ratio}:1</span></div>')

    type_rows = "".join(
        f'<p style="font-size:{sz}px;font-family:{display},serif;margin:.2em 0">'
        f'<span style="opacity:.5;font-size:13px;font-family:{body}">{sz}px</span> '
        f'The quick brown fox</p>' for sz in (48, 32, 24, 18, 14))

    space_rows = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
        f'<span style="width:60px;font-size:12px;opacity:.6">{k}: {v}</span>'
        f'<span style="height:14px;width:{v};background:var(--accent,#888);display:inline-block"></span></div>'
        for k, v in space.items())

    radius_rows = "".join(
        f'<div style="width:72px;height:48px;background:#0001;border:1px solid #0003;'
        f'border-radius:{v};display:flex;align-items:center;justify-content:center;font-size:11px">{k}</div>'
        for k, v in radius.items())

    comp_list = ""
    if components:
        items = "".join(
            f"<li><b>{c['name']}</b> <span style='opacity:.5'>{c['file']}</span>"
            + (f" — {', '.join(c['variants'])}" if c.get("variants") else "") + "</li>"
            for c in components.get("components", []))
        comp_list = f"<section><h2>Components ({components.get('count',0)})</h2><ul>{items}</ul></section>"

    accent = colors.get("accent", colors.get("primary", "#888"))
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>atelier — style guide</title>
<style>
  :root {{ --accent:{accent}; }}
  body {{ background:{bg}; color:{fg}; font-family:{body},sans-serif; margin:0; padding:40px;
          max-width:980px; margin:0 auto; line-height:1.5; }}
  h1,h2 {{ font-family:{display},serif; }}
  h1 {{ font-size:42px; margin:0 0 4px; }}
  h2 {{ margin:40px 0 12px; border-bottom:1px solid #0002; padding-bottom:6px; }}
  .swatches {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px; }}
  .sw {{ padding:16px; border-radius:10px; display:flex; flex-direction:column; gap:2px;
         font-size:12px; min-height:84px; }}
  .sw b {{ font-size:13px; }}
  .radii {{ display:flex; gap:12px; flex-wrap:wrap; }}
</style></head><body>
<h1>Style guide</h1>
<p style="opacity:.6">Generated from <code>design/design-tokens.json</code>. Swatches show the
best in-palette contrast ratio.</p>
<section><h2>Palette</h2><div class="swatches">{''.join(swatches)}</div></section>
<section><h2>Type scale — {display} / {body}</h2>{type_rows}</section>
<section><h2>Spacing</h2>{space_rows or '<p style="opacity:.5">no spacing tokens</p>'}</section>
<section><h2>Radius</h2><div class="radii">{radius_rows or '<p style="opacity:.5">no radius tokens</p>'}</div></section>
{comp_list}
</body></html>"""


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    tokens_path = next((a for a in args if not a.startswith("-")), "design/design-tokens.json")
    out = args[args.index("-o") + 1] if "-o" in args else "design/styleguide.html"
    if not os.path.exists(tokens_path):
        print(f"no tokens at {tokens_path} — run export_tokens first")
        sys.exit(2)
    tokens = json.load(open(tokens_path, encoding="utf-8"))
    comp_path = os.path.join(os.path.dirname(tokens_path), "components.json")
    components = json.load(open(comp_path)) if os.path.exists(comp_path) else None
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write(build(tokens, components))
    print(f"Wrote {out}")
