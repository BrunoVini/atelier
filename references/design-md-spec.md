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
4. **Layout & responsiveness** — the spacing scale (e.g. 4/8/12/16/24/32),
   border-radius scale, grid, PLUS the responsive contract: **target surfaces**
   (`responsive` / `pc-only` with a min–max range / `mobile-only`), the
   **breakpoints** (measured from the repo's `@media` + Tailwind `screens`), and
   the **fluid strategy** (clamp type/space, intrinsic grids, container queries).
   See `references/capabilities/responsive.md`.
5. **Motion** — durations, easing, and the motion philosophy (high-impact vs
   micro).
6. **Anti-slop rules** — project-specific prohibitions (e.g. "display font is
   Sora; never Inter", "no purple gradients", "cards are flat, no left-border
   accent").
7. **Components & standards** — the canonical components to reuse, PLUS
   standardization rules ("use `<Button variant>`, never a raw `<button>`"; "one
   `<DataTable>`, not ad-hoc tables").
8. **Data & charts** — how the project presents data: chart choices ("trends →
   Line; never pie > 5 slices"), dense-data patterns ("tabular → DataTable, not
   card grids"), and empty/loading/error state conventions.
9. **House rules** — the project's interaction/pattern law (see below).
10. **Accessibility** — WCAG target (AA/AAA), minimum contrast, motion-reduction.
11. **Overrides** — pointers to per-route/feature overrides (see below).

## Scale the contract to the repo

A small repo (a portfolio, a landing page) keeps §7–§9 light — a short inventory
and maybe no house rules. A **large or standardized** repo (a design system, an
enterprise app) is where these earn their keep: a full component standardization
list, chart/data-presentation standards, and explicit house rules. Don't bloat a
small project; don't under-specify a big one. Measure what exists, then write the
sections the repo actually needs.

## House rules (machine-checkable)

§9 captures conventions atelier MUST obey and that `scripts/check_rules.py` can
enforce. A user adds these by hand (e.g. a company standard like "no flyouts").
Each rule may carry an inline directive so it's checkable, not just prose:

```md
- Overlays: use a modal for any blocking choice. [forbid: flyout, popover, drawer | prefer: Modal]
- Dense data uses the shared table. [forbid: ad-hoc <table> | prefer: DataTable]
- Icon-only buttons need a label. [require: aria-label on icon buttons]
```

`check_rules.py` parses `[forbid: a, b | prefer: X]` directives and flags
occurrences of the forbidden terms in UI files (with the preferred alternative).
`[require: ...]` is advisory (shown to the agent/reviewer). atelier obeys house
rules when generating; they OVERRIDE its defaults; the design-review and CI gate
check them.

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
  "font":   { "display": "Sora", "body": "Newsreader" }
}
```

Keep `DESIGN.md` (prose, for humans + the agent) and the token files (machine,
for the build) in sync — regenerating tokens after editing the palette/scale is
part of the generate-design-md workflow.
