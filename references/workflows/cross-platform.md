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
| iOS (SwiftUI) | `design-tokens.json` | generate a dynamic-color `Theme` + `Environment` from the JSON (`export_native.py`) |
| React Native | `design-tokens.json` | generate a JS theme object |
| Flutter | `design-tokens.json` | generate a Material 3 `ThemeData` (light+dark) + a `ThemeExtension` (`export_native.py`) |
| Slides | `tokens.css` | the deck engine reads the same vars |
| Marketing / preview | `tokens.css` | preview server links it (`capabilities/preview.md`) |

## Rule

`design-tokens.json` (W3C) is the **portable canonical form**. Don't re-pick colors
per platform — **generate** each platform's theme file from the contract:

```bash
python3 scripts/export_native.py <repo>   # -> design/native/{Theme.swift, app_theme.dart, theme.native.ts}
```

This emits a **complete, idiomatic** theme per platform from the tokens — not a flat
color dump. The SwiftUI file (`Theme.swift`) carries:

- **Dynamic light+dark colors** done the right way — a `Color(light:dark:)`
  initializer backed by a `UIColor`/`NSColor` *dynamic provider* (resolves per
  `ColorScheme` at runtime; `#if canImport(UIKit)`/`AppKit` so it builds on iOS *and*
  macOS). NOT a flat `Color(red:…)` per role, and NOT a stringly-typed hex everywhere.
  Every role from the contract's light **and** `dark` palette is emitted; the light
  value is used for both schemes (disclosed in the header) only when no dark palette
  exists.
- **A named type scale** (`ThemeTypography`) — each text style as a `TextStyleSpec`
  (font with the right `.weight(...)`, plus `lineSpacing` derived from the token's
  `lineHeight − size`), consumed via an idiomatic `.textStyle(_:)` `View` modifier.
- **Spacing + radius** as typed `CGFloat` constants (`ThemeSpacing`, `ThemeRadius`).
- **A `Theme` value + `EnvironmentKey`** so a view reads `@Environment(\.theme)` and
  writes `theme.colors.primary` / `theme.spacing.lg` / `theme.radius.md` — discoverable,
  no globals.
- **Honesty in the header**: the file states it was NOT compiled here (generate +
  verify in Xcode) and that the web multi-layer `box-shadow` elevation token has no 1:1
  SwiftUI form — it is surfaced as a single-layer `.cardShadow()` approximation, called
  out as an approximation rather than a fabricated equivalence.

The Flutter file (`app_theme.dart`) carries the **Material 3 canonical** form — NOT a
flat `class AppColors { static const … }` dump:

- **`ColorScheme.light`/`.dark`** mapping the contract's roles onto the canonical M3
  slots, each `brightness`-correct, so a stock Material widget is themed right out of
  the box. The full modern-M3 mapping: `danger`→`error`, `accent`→`tertiary` (kept
  verbatim on the extension too), `secondary` ink→`onSurfaceVariant`, `muted`→
  `outlineVariant`, `border`→`outline`, and the surface elevation ladder
  (`background` < `surface` < `elevated`) onto the **`surfaceContainer*` ramp**
  (3.22+; disclosed with a downgrade path). `onSecondary`/`onTertiary` have no source
  token, so they're set to a readable contrast (not fabricated). M3 dropped
  `background`/`onBackground` — don't emit them (use `scaffoldBackgroundColor`).
- **A `ThemeExtension<AppTokens>`** — the Flutter-canonical carrier for everything that
  has no ColorScheme slot (the brand `accent`, the full semantic palette
  success/warning, the complete role set, spacing, radii). It implements `copyWith` AND
  `lerp` (colors via `Color.lerp`, doubles via `lerpDouble` from `dart:ui`) so tokens
  animate across a theme transition. NOTHING from the contract is dropped: every role
  appears both on the ColorScheme (where it fits) and on `AppTokens`.
- **A FULL Material 3 `TextTheme`** — every canonical slot (`displayLarge`…`labelSmall`)
  filled from the contract's closest role so stock widgets (AppBar, ListTile, chips,
  buttons) inherit the scale — plus an `AppTextStyles` class keeping every role under its
  CONTRACT name. Each `TextStyle` has the exact `fontSize`, `FontWeight.wNNN`,
  `fontFamily`, and `height` = `lineHeight / size` (the unitless multiple Flutter uses —
  disclosed as approximating the token's pixel line height).
- **`AppSpacing` / `AppRadii`** const scales (radii also as ready `BorderRadius`), and
  **`AppElevation.card`** as a derived `List<BoxShadow>` (one `BoxShadow` per CSS layer,
  the token's REAL color + offset, blur→`blurRadius`; disclosed as not a 1:1 primitive).
- **`AppTheme.light`/`.dark`** (`useMaterial3: true`) wiring the colorScheme, textTheme,
  `scaffoldBackgroundColor`, and the extension; plus an ergonomic **`context.tokens`**
  `BuildContext` extension reading `Theme.of(context).extension<AppTokens>()` — which
  **asserts** (with an actionable message) when the extension isn't registered rather
  than silently falling back to the light tokens (a silent fallback would show LIGHT
  tokens in an unthemed dark subtree and mask the bug).

The `ThemeExtension`'s `lerp` interpolates **every** field — colors via `Color.lerp`,
radii + the spacing scale (element-wise) via `lerpDouble` (imported from `dart:ui`, since
`package:flutter/material.dart` does NOT re-export it — a common compile-error trap) — so
the whole token set animates across a theme transition, nothing returned verbatim.

The idiom hinge for Flutter: **dark is a real `ColorScheme.dark` + a dark `AppTokens`
instance, NOT a single flat const class**; the token carrier is a `ThemeExtension` (with
`copyWith`+`lerp`), NOT loose globals — that's what a Flutter dev expects and what makes
`Theme.of(context)` Just Work. Honest header: NOT compiled here (verify with
`dart analyze` / `flutter test`); the line-height + box-shadow caveats are stated inline.

**Token fidelity is the load-bearing property:** every emitted sRGB triple is the exact
`channel/255` of the source hex (3-dp), and every Flutter `Color(0xAARRGGBB)` is the
exact `0xFF` + uppercase `RRGGBB` of the source hex, so the native theme can't silently
drift from the contract. Run `export_native.py` — never hand-pick colors per platform,
and never claim "it compiles" for code a headless environment never built.

**Honest scope:** atelier does *token + theme handoff* for native — it does NOT produce
native-fidelity UI (the device frames and engines are HTML/React). For native UI, hand
these theme files to the native team / agent; for web/RN, generate the components too. A
per-surface override (e.g. a denser mobile spacing scale) belongs in a
`DESIGN.<surface>.md` that inherits the global contract (`design-md-spec.md` →
Hierarchy), not in ad-hoc values.

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


### Dark-theme FINISH and RESTRAINT (beyond just passing AA)

Two careful dark themes can BOTH pass WCAG AA on every pair and still differ in
quality. AA is the floor; what separates a finished dark theme from an adequate one is
elevation craft and palette discipline. Bake these into the dark token scope:

- **Lift the surface off pure black; soften the ink off pure white.** `#000` canvas with
  `#fff` text passes AA at a maximal 21:1, but that maximum *vibrates* — it reads cheap
  and harsh, and it kills your ability to show elevation (you can only go lighter). Set
  the canvas to a near-black with a slight cool/neutral tint (e.g. `#0e1420`), the top
  ink to a soft off-white (`#e6eaf2`, not `#fff`). The `harsh-dark-contrast` slop check
  flags the `#000`+`#fff` pairing.
- **Build a real elevation ladder in luminance, not just borders.** Dark UIs read depth
  by getting *lighter* as they come forward: canvas < card < inset/raised. Define at
  least three distinct surface steps (`--bg` < `--surface` < `--surface-2`) with visibly
  separated luminance so cards sit ABOVE the canvas and table-headers/search inset sit
  above the card. One flat near-black for everything is the low-finish tell — the page
  has no depth. (Shadows do little work on dark; surface luminance carries elevation.)
- **Desaturate and lift the accent for a dark surface — don't reuse the light hex.** The
  light primary is tuned for white; on dark it must be a *lighter, less-saturated* tint
  of the same hue (a light `#2563cc` becomes ~`#6ea8ff`) so it reads as a calm accent,
  not a glaring chip. Same for status colors (success/danger/warning foregrounds get
  their own dark hexes). Reserve the accent — primary action, links, the active nav,
  one chart series; everything else stays neutral. Saturated fills everywhere, or the
  light accent left unchanged, reads neon-on-black (the opposite of restraint).
- **Give status chips their OWN dark tokens, not a `color-mix()` of the light fill.**
  A `color-mix(in srgb, var(--success) 14%, var(--surface))` chip background that worked
  on a white surface produces an unpredictable muddy tint on a dark one, and couples the
  chip's legibility to a hue meant for fills. Define explicit `--ok-bg/--ok-fg`,
  `--risk-bg/--risk-fg`, `--warn-bg/--warn-fg` per theme so each chip is deliberately
  tuned and audited.
- **A dark theme is half the deliverable — finish BOTH themes.** When the task is "add a
  dark theme", the light theme is now ALSO yours to stand behind: re-audit it too. Parity
  means *equal finish across themes* — shipping a clean dark theme while leaving real AA
  failures (or slop) in the light one is not an equal-finish peer, and claiming "all pass"
  while you only audited one half is a HONESTY miss. Run `audit_contrast.py` on BOTH
  palettes and `qa.py --hook` on the page in BOTH states; report ratios for both and flag
  any borderline pair truthfully (a pair that clears 4.5 by 0.1, a UI border at ~3.1).

- **Reserve the accent in data viz too — neutral by default, accent for meaning.** The
  most common restraint slip in a dark dashboard is painting EVERY chart bar and EVERY
  progress track in the brand accent. A calmer, more deliberate read uses a neutral
  surface tone for the resting data (bars, tracks) and spends the accent only where it
  carries meaning — the current/active bar, the value portion of a progress track, the
  active nav, primary actions, links. Accent everywhere reads as decoration; accent
  reserved for the one thing that matters reads as restraint. (Status colors — success/
  warning/danger — stay semantic and are not "the accent.")
