"""Empirical design extraction from a repository.

atelier measures the *actual* design language of a codebase instead of guessing
it: it parses every color format used in stylesheets and clusters near-duplicates
perceptually (CIE76 ΔE in Lab space), collects real font families, reads the
spacing and radius scales actually in use, and infers the framework and component
library from package.json.

The output of `scan_directory` is the raw material the `generate-design-md`
workflow turns into a DESIGN.md plus exported tokens.

Usage:
    python3 scan_repo.py <repo-root>      # prints a JSON design report
"""
import json
import os
import re
import sys
from collections import Counter

# --- color parsing (hex 3/6/8, rgb/rgba, hsl/hsla, common named) ------------

_HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
_RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", re.I)
_HSL = re.compile(r"hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%", re.I)
_NAMED = {  # only the few that genuinely appear as design choices
    "white": (255, 255, 255), "black": (0, 0, 0),
}


def _hex_to_rgb(h):
    h = h.lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:  # #rrggbbaa -> drop alpha
        h = h[:6]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hsl_to_rgb(h, s, l):
    h, s, l = float(h) % 360, float(s) / 100, float(l) / 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    r, g, b = {
        0: (c, x, 0), 1: (x, c, 0), 2: (0, c, x),
        3: (0, x, c), 4: (x, 0, c), 5: (c, 0, x),
    }[int(h // 60) % 6]
    return round((r + m) * 255), round((g + m) * 255), round((b + m) * 255)


def _rgb_to_hex(r, g, b):
    return "#%02x%02x%02x" % (int(r), int(g), int(b))


def _parse_colors(text):
    """Yield (r, g, b) for every color occurrence in any common CSS format."""
    out = []
    for m in _HEX.findall(text):
        out.append(_hex_to_rgb(m))
    for r, g, b in _RGB.findall(text):
        out.append((int(r), int(g), int(b)))
    for h, s, l in _HSL.findall(text):
        out.append(_hsl_to_rgb(h, s, l))
    lowered = text.lower()
    for name, rgb in _NAMED.items():
        out.extend([rgb] * len(re.findall(r"[:\s]" + name + r"\b", lowered)))
    return out


# --- perceptual clustering (CIE76 ΔE in CIELAB) ------------------------------


def _srgb_to_lab(r, g, b):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    rl, gl, bl = lin(r), lin(g), lin(b)
    # sRGB -> XYZ (D65)
    x = rl * 0.4124 + gl * 0.3576 + bl * 0.1805
    y = rl * 0.2126 + gl * 0.7152 + bl * 0.0722
    z = rl * 0.0193 + gl * 0.1192 + bl * 0.9505
    # XYZ -> Lab
    xn, yn, zn = 0.95047, 1.0, 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _delta_e(c1, c2):
    l1 = _srgb_to_lab(*c1)
    l2 = _srgb_to_lab(*c2)
    return sum((a - b) ** 2 for a, b in zip(l1, l2)) ** 0.5


def extract_colors(text, delta_e_threshold=8.0):
    """Return colors sorted by frequency, with near-duplicates merged.

    Colors in any format are normalized to rgb, then greedily clustered: two
    colors within `delta_e_threshold` (perceptual CIE76 ΔE) collapse into one,
    summing their counts and keeping the most frequent member as the
    representative. Returns [{"hex": "#2563eb", "count": 3}, ...] most-common
    first.
    """
    counter = Counter(_parse_colors(text))
    # Greedy perceptual clustering, most-frequent colors seed clusters first.
    clusters = []  # list of [rep_rgb, total_count]
    for rgb, n in counter.most_common():
        for cluster in clusters:
            if _delta_e(rgb, cluster[0]) <= delta_e_threshold:
                cluster[1] += n
                break
        else:
            clusters.append([rgb, n])
    clusters.sort(key=lambda c: c[1], reverse=True)
    return [{"hex": _rgb_to_hex(*rgb), "count": n} for rgb, n in clusters]


# --- font extraction --------------------------------------------------------

_FONT_FAMILY = re.compile(r"font-family:\s*([^;{}]+)", re.I)
_GFONT = re.compile(r"family=([A-Za-z0-9+]+)")
_GENERIC_FONTS = {
    "sans-serif", "serif", "monospace", "system-ui", "inherit", "ui-sans-serif",
    "ui-serif", "ui-monospace", "-apple-system", "blinkmacsystemfont",
    "segoe ui", "cursive", "fantasy", "emoji", "math", "fangsong",
}


def extract_fonts(text):
    """Return distinct, real font family names referenced in CSS.

    Google Fonts `family=` query params are read first (intent even when only
    imported), then the first family in each `font-family` declaration. Generic
    keywords, system stacks, and `var(...)` indirection are filtered out.
    """
    found = []

    def add(name):
        name = name.strip().strip("'\"").strip()
        low = name.lower()
        if (name and low not in _GENERIC_FONTS and not low.startswith("var(")
                and "var(" not in low and name not in found):
            found.append(name)

    for m in _GFONT.findall(text):
        add(m.replace("+", " "))
    for decl in _FONT_FAMILY.findall(text):
        first = decl.split(",")[0]
        add(first)
    return found


# --- spacing & radius extraction --------------------------------------------

_SPACING_PROP = re.compile(
    r"(?:padding|margin|gap|top|bottom|left|right|inset)[^:;{}]*:\s*([^;{}]+)", re.I)
_LEN = re.compile(r"\b(\d+(?:\.\d+)?)(px|rem)\b")
_RADIUS = re.compile(r"border-radius:\s*([^;{}]+)", re.I)


def _scale_from(values):
    """Return the distinct numeric scale (sorted) from a Counter of 'Npx'/'Nrem'."""
    seen = {}
    for token, _ in values.most_common():
        m = _LEN.match(token)
        if not m:
            continue
        num = float(m.group(1))
        if num <= 0 or num > 256:  # ignore 0 and absurd values
            continue
        seen[token] = num
    return [t for t, _ in sorted(seen.items(), key=lambda kv: kv[1])]


def extract_spacing(text):
    counter = Counter()
    for decl in _SPACING_PROP.findall(text):
        for num, unit in _LEN.findall(decl):
            counter[f"{num}{unit}"] += 1
    return _scale_from(counter)


def extract_radius(text):
    counter = Counter()
    for decl in _RADIUS.findall(text):
        for num, unit in _LEN.findall(decl):
            counter[f"{num}{unit}"] += 1
        if "%" in decl:
            counter["9999px"] += 1  # pill / fully-rounded signal
    return _scale_from(counter) + (["9999px"] if "9999px" in counter else [])


# --- dependency inference ---------------------------------------------------

_FRAMEWORKS = ["react", "vue", "svelte", "@angular/core", "solid-js", "preact"]


def detect_framework(pkg):
    """Infer the frontend framework from a parsed package.json dict."""
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for f in _FRAMEWORKS:
        if f in deps:
            return f.split("/")[0].replace("@", "")
    return "unknown"


def detect_component_lib(pkg):
    """Infer the component library from a parsed package.json dict."""
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    if any(d.startswith("@radix-ui") for d in deps) or "shadcn" in " ".join(deps):
        return "radix/shadcn"
    if "@mui/material" in deps:
        return "mui"
    if "@chakra-ui/react" in deps:
        return "chakra"
    if "antd" in deps:
        return "antd"
    return "none"


# --- directory scan ---------------------------------------------------------

_STYLE_EXT = (".css", ".scss", ".sass", ".less")
_SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "out", "coverage"}


def scan_directory(root):
    """Walk a repo and return an empirical design report.

    {
      "framework": "react",
      "component_lib": "radix/shadcn",
      "colors":  [{"hex": "#2563eb", "count": 12}, ...],
      "fonts":   ["Sora", "Inter"],
      "spacing": ["4px", "8px", "16px"],
      "radius":  ["8px"]
    }
    """
    style_text, pkg = [], {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            if fn == "package.json" and not pkg:
                try:
                    with open(p, encoding="utf-8") as fh:
                        pkg = json.loads(fh.read())
                except Exception:
                    pass
            elif fn.endswith(_STYLE_EXT):
                try:
                    with open(p, encoding="utf-8") as fh:
                        style_text.append(fh.read())
                except Exception:
                    pass
    blob = "\n".join(style_text)
    return {
        "framework": detect_framework(pkg),
        "component_lib": detect_component_lib(pkg),
        "colors": extract_colors(blob),
        "fonts": extract_fonts(blob),
        "spacing": extract_spacing(blob),
        "radius": extract_radius(blob),
    }


# --- drift detection (perceptual) -------------------------------------------


def check_drift(report, allowed, delta_e_threshold=8.0):
    """Compare a scan report against the contract's allowed colors/fonts.

    `allowed` is {"colors": ["#2563eb", ...], "fonts": ["Sora", ...]}. A color
    is "off-palette" when its nearest allowed color is more than
    `delta_e_threshold` ΔE away (perceptual), so near-duplicates of a contract
    color do NOT register as drift. Fonts are matched exactly.
    """
    allowed_rgb = [_hex_to_rgb(c) for c in allowed.get("colors", [])]
    allowed_fonts = set(allowed.get("fonts", []))
    off_colors = []
    for c in report.get("colors", []):
        rgb = _hex_to_rgb(c["hex"])
        nearest = min((_delta_e(rgb, a) for a in allowed_rgb), default=999)
        if nearest > delta_e_threshold:
            off_colors.append(c["hex"])
    off_fonts = [f for f in report.get("fonts", []) if f not in allowed_fonts]
    return {"off_palette_colors": off_colors, "off_contract_fonts": off_fonts}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(scan_directory(target), indent=2))
