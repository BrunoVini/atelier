# Capability: SVG

Produce crisp, on-brand SVG — icons, decorative/geometric marks, diagrams, and
animated SVG — bound to the `DESIGN.md` contract.

**First:** resolve the DESIGN.md gate. SVG strokes/fills use the contract tokens
(`var(--color-*)`), not ad-hoc hexes.

## What atelier does well with SVG
- **Icons** — consistent stroke width, grid, and corner radius; one coherent set.
  Prefer a single style (outline OR filled), sized in `em` so they scale with text.
- **Decorative / geometric marks** — dividers, blobs, grain, marginalia, badges
  (the kind of hand-crafted decorative SVG a designer draws on purpose).
- **Diagrams** — architecture/flow/relationship diagrams with clear hierarchy and
  contract colors (pairs with the data/charts standards in DESIGN.md §8).
- **Animated SVG** — drive paths/strokes via the animation engines
  (`assets/engines/sprites.jsx`) — `stroke-dasharray` draw-on, transforms, morphs.
  Honor `prefers-reduced-motion`.

## Hard rule (inherited, intentional)
**Never AI-draw realistic people, faces, scenes, or product objects as SVG** — the
proportions/features come out wrong (design-philosophy §3). For those, use a real
image (Wikimedia / Unsplash / generated) or an honest placeholder. SVG is for
icons, geometry, type, and diagrams — not illustration of the real world.

## Practical
- Keep SVGs inline (themeable by `currentColor` / CSS vars) rather than as opaque
  `<img>` when they should pick up the palette.
- Mark decorative SVG `aria-hidden="true"`; give meaningful SVG a `<title>`.
- Optimize: drop editor metadata, round path precision, reuse `<symbol>`/`<use>`.
