"""Token-migration codemod — rewrite hardcoded values to var(--token).

Closes the loop from measure -> enforce -> *fix*. Rewrites a hardcoded literal to
`var(--token)` ONLY when it is **pixel-safe and role-correct**:

  - EXACT match only. A color is rewritten only when its normalized hex EQUALS a
    token's hex (delta == 0), never a near-match — snapping a near-but-unequal value
    would MOVE PIXELS, defeating the whole point of the codemod.
  - ROLE-AWARE. The same literal can mean different roles. `8px` as `gap` maps to a
    spacing token (`--space-2`); `8px` as `border-radius` maps to a radius token
    (`--radius-md`). Spacing tokens are applied only in spacing properties
    (padding/margin/gap/inset...), radius tokens only in border-radius properties.
  - SAFE SURFACES. Stylesheets: color/spacing/radius/font-family declarations. Code
    (JSX/TSX/Vue/Svelte): Tailwind arbitrary values `bg-[#hex]` and inline-style color
    props; a bare hex in a JS data/config array is LEFT ALONE.
  - NEVER CORRUPTS TOKEN DEFINITIONS. A declaration of a CSS custom property
    (`--color-bg: #0d1117`) is the token's *definition*; its value is never rewritten
    (that would create a `--color-bg: var(--color-bg)` self-reference and destroy the
    theme). The generated `design/` dir is skipped too.
  - LEAVES RISKY CONTEXTS. Values inside `calc(...)`, `@media`/`@container` conditions,
    rgba()/hsl() tints, and non-spacing dimensions (width/height/font-size/line-height/
    grid track sizing) are left alone.

DRY-RUN BY DEFAULT (prints a unified diff); pass --apply to write. Pair with
diff_screens.mjs / a render diff to prove "zero pixels moved".

Usage:
    python3 migrate_to_tokens.py <repo> [--contract design/design-tokens.json]
    python3 migrate_to_tokens.py <repo> --apply
"""
import difflib
import os
import re
import sys

from scan_repo import _HEX, _hex_to_rgb, _STYLE_EXT, _CODE_EXT, _SKIP_DIRS
from lint_design import _load_contract

# --- token-definition extraction -------------------------------------------------

# A CSS custom-property definition: `--name: value;` (value up to ; or }).
_CUSTOM_PROP_DEF = re.compile(r"(--[\w-]+)\s*:\s*([^;}{]+)")
# The declaration containing a value position is a custom-property *definition*
# (`--x: ...`) — so we never rewrite its RHS (would create a self-reference). Tested
# against the text since the last `{`/`;`/`}` boundary up to the value position.
_DECL_HEAD_IS_CUSTOM = re.compile(r"^\s*--[\w-]+\s*:")

# CSS properties that carry a *spacing* value (gap/padding/margin/inset...). Width,
# height, font-size, line-height, top/left coords, and grid track sizing are NOT here:
# tokenizing those is wrong even when the literal happens to equal a spacing token.
_SPACING_PROPS = re.compile(
    r"(?:^|[;{]|\*/)\s*(gap|row-gap|column-gap|"
    r"padding|padding-top|padding-right|padding-bottom|padding-left|padding-block|"
    r"padding-inline|padding-block-start|padding-block-end|padding-inline-start|"
    r"padding-inline-end|margin|margin-top|margin-right|margin-bottom|margin-left|"
    r"margin-block|margin-inline|margin-block-start|margin-block-end|"
    r"margin-inline-start|margin-inline-end)\s*:\s*([^;}{]+)", re.I)
# border-radius family (logical + per-corner). A radius token applies only here.
_RADIUS_PROPS = re.compile(
    r"(?:^|[;{]|\*/)\s*(border-radius|border-top-left-radius|border-top-right-radius|"
    r"border-bottom-left-radius|border-bottom-right-radius|border-start-start-radius|"
    r"border-start-end-radius|border-end-start-radius|border-end-end-radius)"
    r"\s*:\s*([^;}{]+)", re.I)
_FONT_FAMILY_PROP = re.compile(r"(?:^|[;{]|\*/)\s*(font-family|font)\s*:\s*([^;}{]+)", re.I)

# A length literal: 16px, 0.5rem, 1.5em, 0 (px/rem/em + unitless 0). We only tokenize
# px/rem/em lengths; percentages, vw/vh, fr, ch, etc. are layout units, left alone.
_LEN = re.compile(r"(?<![\w.#-])(\d*\.?\d+)(px|rem|em)\b")


def _norm_len(v):
    """Normalize a length literal to a canonical px string when possible (rem/em→px at
    16px root) so `1rem` and `16px` compare equal; keep the original unit otherwise."""
    m = re.fullmatch(r"\s*(\d*\.?\d+)(px|rem|em)\s*", str(v))
    if not m:
        return str(v).strip()
    num, unit = float(m.group(1)), m.group(2)
    px = num if unit == "px" else num * 16.0
    # canonical key in px
    return f"{px:g}px"


def extract_css_tokens(text):
    """From CSS custom-property definitions, return role maps keyed by canonical value:
    {"color": {hexlower: name}, "spacing": {pxkey: name}, "radius": {pxkey: name},
     "font": {familykey: name}}. The token's ROLE is inferred from its name prefix
    (--color-*/--space-*|--spacing-*/--radius-*|--font-*) so a value→token lookup can be
    role-scoped. Definitions are the source of truth for var names + role."""
    roles = {"color": {}, "spacing": {}, "radius": {}, "font": {}}
    for m in _CUSTOM_PROP_DEF.finditer(text):
        name, raw = m.group(1), m.group(2).strip()
        low = name.lower()
        if re.search(r"#[0-9a-fA-F]{3,8}\b", raw) and (
                low.startswith("--color") or low.startswith("--c-") or "color" in low):
            hx = re.search(r"#[0-9a-fA-F]{3,8}\b", raw).group(0).lower()
            roles["color"].setdefault(hx, name)
        elif low.startswith("--radius") or low.startswith("--radii") or "radius" in low:
            roles["radius"].setdefault(_norm_len(raw), name)
        elif low.startswith("--space") or low.startswith("--spacing") or low.startswith("--gap"):
            roles["spacing"].setdefault(_norm_len(raw), name)
        elif low.startswith("--font") and ("family" in low or "sans" in raw.lower()
                                            or "serif" in raw.lower() or "mono" in raw.lower()
                                            or '"' in raw or "'" in raw):
            roles["font"].setdefault(_font_key(raw), name)
    return roles


def _font_key(v):
    """Canonical key for a font-family stack: lowercased, quotes/space normalized."""
    return re.sub(r"\s+", " ", v.replace('"', "").replace("'", "").strip().lower())


def tokens_from_contract(contract_path):
    """Build role maps from the design contract (colors carry names; spacing/radius are
    value lists with no names there). Used as a FALLBACK/augment to the CSS extractor.
    Returns the same shape as extract_css_tokens, color role only (named)."""
    try:
        colors_by_hex, _, _ = _load_contract(contract_path)
    except Exception:
        colors_by_hex = {}
    return {"color": {h.lower(): n for h, n in colors_by_hex.items()},
            "spacing": {}, "radius": {}, "font": {}}


def _var_ref(name):
    return f"var({name})"


# --- the rewriters ----------------------------------------------------------------

def _strip_calc_regions(text):
    """Return a set of (start,end) char spans that are inside a calc(...) — we never
    tokenize within calc, where a swapped unit can break the expression. Also covers
    min()/max()/clamp()."""
    spans = []
    for fn in ("calc", "min", "max", "clamp"):
        for m in re.finditer(fn + r"\(", text):
            depth, i = 0, m.end() - 1
            while i < len(text):
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        spans.append((m.start(), i + 1))
                        break
                i += 1
    return spans


def _in_spans(pos, spans):
    return any(a <= pos < b for a, b in spans)


def migrate_text(text, color_tokens, spacing_tokens=None, radius_tokens=None,
                 font_tokens=None):
    """Rewrite hardcoded literals in a STYLESHEET to var(--token). Exact-match,
    role-aware, never rewrites a custom-property *definition* RHS or a calc() interior.

    `color_tokens` is {hexlower: name} (back-compat: a bare {hex:name} like the old
    contract map is accepted and treated as color tokens). Returns (new_text, count)."""
    spacing_tokens = spacing_tokens or {}
    radius_tokens = radius_tokens or {}
    font_tokens = font_tokens or {}
    count = [0]
    # calc()/clamp() spans are recomputed AFTER each text-mutating pass — the color
    # rewrite changes string length, so spans from the pre-color text would be stale.
    calc_spans = _strip_calc_regions(text)

    def line_is_token_def(at):
        # True when the value at `at` belongs to the RHS of a `--custom-prop:` decl
        # (a token *definition*) — never rewrite those (would self-reference).
        start = max(text.rfind("{", 0, at), text.rfind(";", 0, at),
                    text.rfind("}", 0, at)) + 1
        slice_ = re.sub(r"/\*.*?\*/", " ", text[start:at], flags=re.S)
        return bool(_DECL_HEAD_IS_CUSTOM.match(slice_))

    # --- colors (exact match only) ---
    def color_repl(m):
        if _in_spans(m.start(), calc_spans) or line_is_token_def(m.start()):
            return m.group(0)
        name = color_tokens.get(m.group(0).lower())
        if name:
            count[0] += 1
            return _var_ref(name if name.startswith("--") else f"--color-{name}")
        return m.group(0)

    text = _HEX.sub(color_repl, text)
    calc_spans = _strip_calc_regions(text)  # refresh after color rewrite shifted offsets

    # --- spacing & radius (role-scoped: only inside the right declaration) ---
    def make_len_rewriter(value_map):
        def rewrite_decl(decl_m):
            prop, val = decl_m.group(1), decl_m.group(2)
            val_start = decl_m.start(2)
            if line_is_token_def(decl_m.start()):
                return decl_m.group(0)

            def len_repl(lm):
                abspos = val_start + lm.start()
                if _in_spans(abspos, calc_spans):
                    return lm.group(0)
                name = value_map.get(_norm_len(lm.group(0)))
                if name:
                    count[0] += 1
                    return _var_ref(name)
                return lm.group(0)

            new_val = _LEN.sub(len_repl, val)
            return decl_m.group(0)[:decl_m.start(2) - decl_m.start()] + new_val
        return rewrite_decl

    if spacing_tokens:
        text = _SPACING_PROPS.sub(make_len_rewriter(spacing_tokens), text)
        calc_spans = _strip_calc_regions(text)  # refresh: spacing rewrite shifted offsets
    if radius_tokens:
        text = _RADIUS_PROPS.sub(make_len_rewriter(radius_tokens), text)

    # --- font-family ---
    if font_tokens:
        def font_repl(decl_m):
            prop, val = decl_m.group(1), decl_m.group(2)
            if line_is_token_def(decl_m.start()) or "var(" in val:
                return decl_m.group(0)
            name = font_tokens.get(_font_key(val))
            if name:
                count[0] += 1
                head = decl_m.group(0)[:decl_m.start(2) - decl_m.start()]
                return head + _var_ref(name)
            return decl_m.group(0)
        text = _FONT_FAMILY_PROP.sub(font_repl, text)

    return text, count[0]


# Tailwind arbitrary color value, e.g. bg-[#2563eb] -> bg-[var(--color-primary)].
_TW_ARBITRARY = re.compile(r"(-\[)#([0-9a-fA-F]{3,8})(\])")
# JSX/RN inline-style color values keyed by a known style prop.
_STYLE_PROP_HEX = re.compile(
    r"((?:background|backgroundColor|color|borderColor|border[A-Za-z]*Color|"
    r"outlineColor|fill|stroke|shadowColor|tintColor|placeholderTextColor)"
    r"\s*:\s*['\"])#([0-9a-fA-F]{3,8})(['\"])")


def migrate_code_text(text, color_tokens, **_ignored):
    """Rewrite color hex in code only where it's unambiguously styling: Tailwind
    arbitrary values `-[#hex]` and inline-style color props. EXACT match only. A bare
    hex elsewhere in JS (config arrays, data) is left alone, by design."""
    count = [0]

    def repl(m):
        name = color_tokens.get(("#" + m.group(2)).lower())
        if name:
            count[0] += 1
            ref = _var_ref(name if name.startswith("--") else f"--color-{name}")
            return f"{m.group(1)}{ref}{m.group(3)}"
        return m.group(0)

    text = _TW_ARBITRARY.sub(repl, text)
    text = _STYLE_PROP_HEX.sub(repl, text)
    return text, count[0]


# --- repo driver ------------------------------------------------------------------

def _gather_tokens(root, contract_path):
    """Scan the repo's stylesheets for custom-property definitions (the var-name +
    role source of truth) and fold in the contract's named colors. Returns role maps
    where COLOR names are bare role names (back-compat: `--color-<name>`) and
    SPACING/RADIUS/FONT names are the literal `--var` names found in the CSS."""
    css_roles = {"color": {}, "spacing": {}, "radius": {}, "font": {}}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(_STYLE_EXT):
                try:
                    t = open(os.path.join(dirpath, fn), encoding="utf-8").read()
                except Exception:
                    continue
                r = extract_css_tokens(t)
                for k in css_roles:
                    for key, name in r[k].items():
                        css_roles[k].setdefault(key, name)
    # Colors: prefer the contract's role names (stable, e.g. `primary`), keyed by hex.
    contract_roles = tokens_from_contract(contract_path)
    color_tokens = {}
    for hx, name in css_roles["color"].items():
        color_tokens[hx] = name  # full `--color-x` var from CSS
    for hx, name in contract_roles["color"].items():
        color_tokens.setdefault(hx, name)  # contract bare name -> `--color-<name>`
    return color_tokens, css_roles["spacing"], css_roles["radius"], css_roles["font"]


def migrate_repo(root, contract_path, apply=False):
    color_tokens, spacing_tokens, radius_tokens, font_tokens = _gather_tokens(
        root, contract_path)
    diffs, total = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip build/vendor dirs AND the generated token files in design/.
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and d != "design"]
        for fn in filenames:
            is_style = fn.endswith(_STYLE_EXT)
            is_code = fn.endswith(_CODE_EXT)
            if not (is_style or is_code):
                continue
            p = os.path.join(dirpath, fn)
            try:
                orig = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if is_style:
                new, n = migrate_text(orig, color_tokens, spacing_tokens,
                                      radius_tokens, font_tokens)
            else:
                new, n = migrate_code_text(orig, color_tokens)
            if n:
                total += n
                rel = os.path.relpath(p, root)
                diffs.append("".join(difflib.unified_diff(
                    orig.splitlines(True), new.splitlines(True),
                    fromfile=f"a/{rel}", tofile=f"b/{rel}")))
                if apply:
                    open(p, "w", encoding="utf-8").write(new)
    return diffs, total


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args:
        print("usage: migrate_to_tokens.py <repo> [--contract <json>] [--apply]")
        sys.exit(2)
    from contract import has_contract
    repo = args[0]
    contract = args[args.index("--contract") + 1] if "--contract" in args else repo
    apply = "--apply" in args
    if not has_contract(contract):
        print(f"no contract for {contract} — need design/design-tokens.json or DESIGN.md")
        sys.exit(2)
    diffs, total = migrate_repo(repo, contract, apply)
    for d in diffs:
        print(d)
    mode = "APPLIED" if apply else "DRY-RUN (use --apply to write)"
    print(f"\n{total} hardcoded value(s) -> tokens across {len(diffs)} file(s). [{mode}]")
    if not apply and total:
        print("Then render before+after and diff to prove zero pixels moved "
              "(node scripts/diff_screens.mjs <page>).")
