# Workflow: Cross-platform Coherence

Keep one design language across every surface — web, mobile, slides, marketing —
from a single `DESIGN.md`. The token files are the shared source; each platform
consumes them in its own dialect.

## Token mapping by surface

| Surface | Consumes | How |
|---|---|---|
| Web (CSS/vanilla) | `design/tokens.css` | `@import` and use `var(--color-primary)` |
| Web (Tailwind) | `design/tailwind-preset.js` | `presets: [require('./design/tailwind-preset')]` |
| Web (any build) | `design/design-tokens.json` | Style Dictionary / your token pipeline |
| iOS (SwiftUI) | `design-tokens.json` | generate a `Color`/`Font` extension from the JSON |
| React Native | `design-tokens.json` | generate a JS theme object |
| Flutter | `design-tokens.json` | generate a `ThemeData` / token Dart file |
| Slides | `tokens.css` | the deck engine reads the same vars |
| Marketing / preview | `tokens.css` | preview server links it (`capabilities/preview.md`) |

## Rule

`design-tokens.json` (W3C) is the **portable canonical form**. Don't re-pick colors
per platform — **generate** each platform's theme file from the contract:

```bash
python3 scripts/export_native.py <repo>   # -> design/native/{AppColors.swift, app_colors.dart, theme.native.ts}
```

This emits idiomatic SwiftUI (`Color` extension), Flutter (`AppColors`/`AppFonts`),
and React Native (`theme` object) from the tokens. **Honest scope:** atelier does
*token + theme handoff* for native — it does NOT produce native-fidelity UI (the
device frames and engines are HTML/React). For native UI, hand these theme files to
the native team / agent; for web/RN, generate the components too. A per-surface override (e.g. a denser mobile spacing scale)
belongs in a `DESIGN.<surface>.md` that inherits the global contract
(`design-md-spec.md` → Hierarchy), not in ad-hoc values.

## Multi-brand / dark mode / white-label theming

For several brands or a light/dark pair from one contract, give `export_tokens.py`
a base token dict plus per-theme overrides (only the tokens that differ):

```python
import sys; sys.path.insert(0, "scripts")
from export_tokens import to_themed_css
css = to_themed_css(base_tokens, {"dark": dark_overrides, "acme": acme_overrides})
# -> :root { ... }  [data-theme="dark"] { ... }  [data-theme="acme"] { ... }
```

Switch themes with `<html data-theme="dark">`; the preview frame already reads
`/design/tokens.css`, so the chrome follows. **Audit every theme** for contrast
(`audit_contrast.py`) — a brand override can silently break AA. Each theme that
diverges in more than color belongs in its own `DESIGN.<theme>.md`.

### Each brand must be a complete identity, not a recolor

The point of a token-driven multi-brand system is that ONE component set yields
two builds that read as **genuinely different products**. A brand override that only
swaps the accent hue (and maybe a radius) produces "two recolors of the same vibe" —
which loses the *coherence-per-brand* bar even though the architecture is correct.
A brand's token scope owns its **whole surface treatment**, not just its accent:

- **Surface mode / luminance is part of the identity.** A brand scope may flip the
  entire surface family — `--bg`/`--surface`/`--card`/`--text`/`--border` — to a
  **dark** (or warm-paper, or cool-light) register if that is what the brand *is*. A
  serious fintech/instrument tool often reads more precise and trustworthy on a dark
  ink surface; a warm consumer brand on a light, warm one. Don't keep every brand on
  the same light surface and only tint the button — that is the recolor trap. Re-audit
  contrast for the brand's full role set when you flip the surface (a dark scope needs
  its own muted/border/on-fill pairs to hold AA).
- **Density, radius, and depth diverge with personality.** Generous radii + airy
  spacing + soft shadows for a playful brand; small/sharp radii + tight spacing +
  hairline borders (depth felt, not seen) for a precise one. These all live in the
  token layer (`--radius-*`, the spacing rhythm, `--shadow-*`/elevation), so the
  shared components inherit each brand's density automatically.
- **Type personality, including numerals.** A brand scope swaps the font stack AND
  numeric features — `font-feature-settings`/`font-variant-numeric: tabular-nums` (a
  `--num-feature` token) for a figures-heavy fintech brand, proportional for a
  consumer one. Wire it through a token so every figure across the system follows.
- **Verify the divergence on the render, per brand.** Screenshot EACH brand
  (`screenshot.mjs`) and confirm a stranger would not mistake one for the other —
  different surface, different density, different voice — while the DOM is identical.

### Demonstrating reuse (make it checkable)

When the deliverable's job is to *prove* the system is shared (a brand showcase, a
review artifact), render **both brands at once, side by side**, so a reviewer SEES
one component set themed two ways with zero interaction — and the second brand isn't
hidden behind a JS toggle (a static/no-JS reviewer would only ever see one). If you
do use a toggle, still render a complete default brand with no JS, and keep the toggle
keyboard-accessible. Either way, the **comparison/demo chrome itself must be
token-driven and quiet** (a neutral scaffold from `var(--token)`, not a pile of
hardcoded hexes) so it never competes with — or visually contaminates — the two
brands it frames.
