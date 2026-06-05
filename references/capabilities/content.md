# Capability: Content Fidelity

Mockups built on lorem-ipsum and gray avatars look fine and hide the failures that
ship: long names, empty lists, 4-line headlines, missing images. Seed realistic
content and render the hard states up front — that's the difference between a demo
and a usable starting point.

## Seed the structure + states

```bash
python3 scripts/seed_content.py "fintech SaaS" --layout landing
```
Emits a content scaffold (the slots a first render must fill), real image-source
URLs (per `design-philosophy.md` §3 — real images, never drawn SVG), and a
**stress-state manifest**. You (the agent) fill the `<AGENT: ...>` slots with
domain-appropriate copy.

## Render every state

For each `stress_state`, render the variant — don't stop at the happy path:
- **default** · **empty** (real empty state, not a blank box) · **loading**
  (skeletons/feedback) · **long_text** (4-line headline / 40-char name must not
  break layout) · **error** (clear, on-brand).

Pair with `screenshot.mjs` to capture the stress states and `review.md` to score
whether the layout survives them. Real content + real states = fewer iterations,
because the first render already faces reality.
