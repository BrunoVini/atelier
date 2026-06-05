# Capability: Motion Spec

Generate a precise, contract-bound motion specification so every surface in the
product moves the same way — instead of each page easing differently (the most
common AI-output inconsistency).

**First:** resolve the DESIGN.md gate. Motion belongs in the contract.

## Motion tokens

Add a `duration` and `easing` group to the token dict; `export_tokens.py` renders
them to CSS vars, a Tailwind preset (`transitionDuration` /
`transitionTimingFunction`), and W3C tokens:

```json
{
  "duration": { "fast": "150ms", "base": "220ms", "slow": "400ms" },
  "easing":   { "standard": "cubic-bezier(.2,0,0,1)", "emphasized": "cubic-bezier(.3,0,0,1)" }
}
```
→ `--duration-base`, `--easing-standard`, Tailwind `duration-base`, etc.

## The spec (DESIGN.md §5)

State, in `DESIGN.md`:
- **Durations** and **easings** (the tokens above).
- **Philosophy** — high-impact moments over scattered micro-interactions
  (design-philosophy §3): one orchestrated page-load with staggered reveals beats
  ten random hovers.
- **Patterns** — enter/exit, hover, press, page-transition — each pinned to a
  duration+easing token.
- **Reduced motion** — every motion must have a `prefers-reduced-motion` fallback.

## Ready snippets

Emit CSS that uses the tokens, so generated pages inherit the same motion:

```css
@media (prefers-reduced-motion: no-preference) {
  .reveal { animation: rise var(--duration-base) var(--easing-standard) both; }
  .reveal:nth-child(2) { animation-delay: 80ms; }
  .reveal:nth-child(3) { animation-delay: 160ms; }
}
@keyframes rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
```

Prototypes, slides, and animations all pull motion from these tokens — never
invent per-piece timing.
