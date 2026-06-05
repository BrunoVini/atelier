# DESIGN.md — Format & Token Contract

`DESIGN.md` is a repo's design constitution: more specific than `CLAUDE.md`,
extracted *empirically* from the code, and enforceable via exported tokens. It
lives at the repo root. Generated artifacts must obey it.

## Sections (use the template in `templates/DESIGN.md.template`)

1. **Identity & tone** — inferred product type, audience, and the ONE committed
   tone (see design-philosophy §1). 1–3 sentences.
2. **Palette** — semantic colors with hex + role:
   `primary, secondary, accent, background, foreground, muted, border,
   destructive` (+ their `on-*` contrast pairs). Note WCAG status.
3. **Typography** — display font + body font, the type scale, weights, line-height.
4. **Spacing & radius** — the spacing scale (e.g. 4/8/12/16/24/32), border-radius
   scale, grid.
5. **Motion** — durations, easing, and the motion philosophy (high-impact vs
   micro).
6. **Anti-slop rules** — project-specific prohibitions (e.g. "display font is
   Sora; never Inter", "no purple gradients", "cards are flat, no left-border
   accent").
7. **Components** — inventory of existing components + reuse conventions
   (prefer reuse over reinvention).
8. **Accessibility** — WCAG target (AA/AAA), minimum contrast, motion-reduction.
9. **Overrides** — pointers to per-route/feature overrides (see below).

## Hierarchy (global + overrides)

- The root `DESIGN.md` is the global contract.
- Optional overrides live as `DESIGN.<scope>.md` (e.g. `DESIGN.marketing.md`) or
  in a `design/overrides/<scope>.md` file, and inherit from the global one —
  only the differences are stated. This mirrors the MASTER + page-overrides
  pattern from the upstream knowledge base.

## Token artifacts (the enforceable half)

`scripts/export_tokens.py` renders a token dict into three files under `design/`
(or into whatever token location the repo already uses — detect first):

- **`design/tokens.css`** — `:root { --color-primary: #…; --space-2: 8px; … }`
- **`design/tailwind-preset.js`** — `module.exports = { theme: { extend: { … } } }`,
  consumed via `presets: [require('./design/tailwind-preset')]`.
- **`design/design-tokens.json`** — W3C Design Tokens
  (`{ "color": { "primary": { "$value": "#…", "$type": "color" } } }`).

### Token dict shape (input to export_tokens.py)

```json
{
  "color":  { "primary": "#2563eb", "accent": "#ea580c", "background": "#f8fafc" },
  "space":  { "1": "4px", "2": "8px", "4": "16px", "6": "24px" },
  "radius": { "sm": "4px", "md": "8px", "lg": "16px" },
  "font":   { "display": "Sora", "body": "Inter" }
}
```

Keep `DESIGN.md` (prose, for humans + the agent) and the token files (machine,
for the build) in sync — regenerating tokens after editing the palette/scale is
part of the generate-design-md workflow.
