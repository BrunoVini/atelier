# Capability: Layering & elevation (depth as a system)

Depth is the most-improvised part of a UI. A generator reaches for a fresh `box-shadow`
on every component, mixes a border here and a drop shadow there, and the page ends up
with six near-identical shadows and no readable sense of which surface sits above which.
Depth is not a per-component decision — it's a **finite, named system** you define once
and apply consistently. This guide is the doctrine; the numbers live in
`../design-laws.md` and two of the rules are mechanically enforced (below).

Read this whenever the deliverable layers surfaces: **dashboards, card grids, panels,
overlays, modals, popovers** — anywhere more than one surface stacks. It pairs with
`landing-craft.md` (hero surfaces) and `data-viz-craft.md` (KPI cards, panels).

## Elevation ladders — a finite set of named levels

Define **3 to 5 elevation levels**, no more, and give each a name. A typical ladder:

| Level | Name | Used for |
|---|---|---|
| 0 | `base` | the page itself; no elevation |
| 1 | `raised` | cards, tiles, KPIs sitting on the page |
| 2 | `overlay` | dropdowns, popovers, tooltips |
| 3 | `modal` | dialogs and the surfaces above a backdrop |

Each level is **one consistent treatment** — one shadow value, one tint step, or one
border weight — reused everywhere that level appears. A raised card and a raised KPI
tile share the *same* level-1 token; they do not each invent their own shadow. The fast
test: count the distinct `box-shadow` values on the page. If you have 5 cards and 5
different shadows, you have no ladder — you have 5 improvisations. A real ladder shows
**one shadow per level**, so 3 to 5 distinct values total across the whole page.

Steps between levels should be perceptible but not theatrical. If you build the ladder
in shadows, each level is roughly **1.5× to 2× the blur radius and offset** of the one
below it (e.g. `0 1px 2px` → `0 4px 8px` → `0 12px 24px`), so the jump from `raised` to
`overlay` reads as a clear step, not a guess.

## Border-opacity progressions — hairlines as foreground-at-low-alpha

A hairline is **the foreground (text) color at low alpha**, never a hardcoded gray.
`#e5e5e5` looks right on white and disappears on a tinted or dark surface; the same
hairline authored as `rgba(0,0,0,0.08)` (or `color-mix(in oklch, var(--fg) 8%,
transparent)`) sits correctly on *any* ground because it derives from the surface.

The opacity rises slightly with elevation, so higher surfaces read as having a crisper
edge:

```css
--hairline:        color-mix(in oklch, var(--fg) 6%,  transparent);  /* base dividers */
--hairline-strong: color-mix(in oklch, var(--fg) 12%, transparent);  /* raised edges  */
```

Keep the range to roughly **6% to 12%**. Above ~15% the line stops being a hairline and
becomes a *visible border* — which is a different (and load-bearing) elevation strategy,
not a finishing edge. That distinction is exactly what the depth check keys on: a 6-12%
hairline on a tinted surface is one coherent strategy (a tint with a defined edge); an
opaque 1px-plus border that you then *also* shadow is two strategies stacked.

## Control tokens — depth is tokenized, not per-component magic

Name the surfaces, lines, and interactive fills per level so nothing is a one-off
literal:

```css
:root {
  --surface:         <page base>;
  --surface-raised:  <one lightness step up (light) or down-toward-fg (dark)>;
  --hairline:        color-mix(in oklch, var(--fg) 6%,  transparent);
  --hairline-strong: color-mix(in oklch, var(--fg) 12%, transparent);
  --control:         <resting fill of a button / input>;
  --control-hover:   <one step from --control>;
  --elevation-1:     0 1px 2px rgba(0,0,0,.06);
  --elevation-2:     0 4px 12px rgba(0,0,0,.08);
}
```

A card reads `background: var(--surface-raised)`; it never writes `#fafafa` inline. When
every surface, line, and control pulls from these tokens, the ladder is enforceable and
a theme switch (light ↔ dark, or a re-skin) moves one block, not forty components.

## Pick-one depth strategy — the core law

**A given surface earns its elevation with ONE strategy.** The three on offer:

- **shadow** — a soft drop shadow lifts the surface off the page.
- **border / hairline** — a defined edge separates it without lifting it.
- **tint / fill** — a lightness step (raised surface is lighter on light, lighter-toward-
  the-foreground on dark) reads as nearer.

Pick one per surface. Stacking two or three — a tint *and* a shadow *and* a border — is
the **"ghost card"**: the surface looks muddy and over-finished, and the eye can't tell
which cue is doing the work. The classic tell is a 1px hairline border plus a wide
diffuse shadow on the same card (atelier flags that exact pair as `gpt-ghost-card`); the
broader form is any surface stacking shadow+tint, border+tint, or all three.

And **one system per page.** Don't ship a dashboard where some cards are shadowed, some
are bordered, and some are tinted — that's three competing depth languages on one screen
and it reads as three different designers. Choose the page's dominant strategy (most
flat product UIs are best served by **tint + hairline, no shadows**; marketing surfaces
can carry soft shadows) and hold every surface to it.

## The quietest sufficient cue wins "subtle layering"

Picking one strategy keeps you *correct*; on a calm product instrument (a dashboard, an
admin surface), the surface that *wins* the **subtle-layering** dimension is the one that
groups with the **least visible chrome that still reads** — depth *felt*, not *seen*. Two
builds can both be one-strategy-per-surface and tokenized, yet one reads as a quiet
instrument and the other as a grid of outlined boxes. The difference is how hard the cue
works:

- **Prefer tonal step + spacing over a drawn edge.** A raised surface that's one lightness
  step up on generous spacing already reads as grouped; adding a hairline outline to *every*
  panel on top of that reprints the grid as visible boxes. Reserve the outline for where the
  tonal step alone isn't enough (an inset well, a table head), and let whitespace + the tint
  carry the rest. The squint test is the judge: if you blur the screen and see a lattice of
  rectangles, your edges are doing work the spacing should do.
- **Don't let a "heavy graphic" element undo the calm.** A saturated multi-color donut, a row
  of filled high-chroma status pills, or a boldly bordered widget is *read*, not *felt* — it
  pulls the eye and reads louder than the restrained surfaces around it, costing layering even
  when every panel is technically one-strategy. Quiet these to match the instrument: a
  composition reads calmer as a single horizontal 100%-stacked bar or a tonal ranked list than
  as a bright donut; status reads calmer as a **tinted glyph chip** (a low-alpha tonal fill +
  a shaped glyph + a label) than as a saturated solid pill. Keep the one reserved accent for
  the single thing that must shout (an active alert), not sprinkled across every status and
  segment.
- **A side rail of navigation/context is part of the grouping, not noise.** Grounding the
  content in a quiet nav rail (same or near-same ground as the canvas, separated by a single
  hairline — never a different hue) lets the working area read as one calm plane instead of a
  free-floating stack of panels; it reads as a *product*, and it makes the main surface feel
  more layered-into-an-app, not less. (See `data-viz-craft.md` §4 "real document skeleton" and
  the navigation-context note — grounding and quiet layering reinforce each other.)

The bar: against an equally-correct competitor, the calmer instrument wins this dimension.
When you've made every surface one-strategy and it *still* reads busy, the fix is to **remove
a cue** (drop a per-panel outline, de-saturate a graphic, collapse the palette), not add one.

## What atelier auto-checks vs. what you hold by hand

Two of these are cheap to verify from static CSS with a low false-positive rate, so
atelier flags them mechanically (`scripts/qa.py` → `slop_ported.py`):

- **`mixed-elevation`** *(polish)* — one surface stacks ≥2 load-bearing strategies among
  {shadow, border, tint}. Scoped to the pairs `gpt-ghost-card` does **not** own
  (shadow+tint, border+tint, all three), so the two checks never double-fire — a plain
  hairline-border + wide-shadow card stays `gpt-ghost-card`. A 6-12% hairline is treated
  as a tint's finishing edge, not a load-bearing border, so the standard tinted-surface-
  with-a-hairline pattern does **not** flag.
- **`no-single-elevation-system`** *(polish)* — the page has ≥3 card-like surfaces using
  ≥2 different strategies with no dominant one (a split system). One shadowed hero plus
  flat content passes (flat content declares no strategy, so it isn't counted).

The ladder size (3-5 levels), the hairline opacity range, and the per-step ratio are
**judgment** — real and worth holding, but flagging them statically would be noise.

See `../design-laws.md` (the Depth / Elevation law) and `defensive-css.md` (the related
"give light avatars an edge" robustness note).
