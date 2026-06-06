# Capability: 3D / shader hero (bridge — delegate the GPU, own the design)

A WebGPU/Three.js/TSL shader hero is a different discipline with its own maintained
skill. atelier does **not** build a GPU stack — it routes the 3D work to the
`webgpu-threejs-tsl` skill and contributes the part that keeps the result on-brand:
the design tokens, and the fallbacks.

## Route the 3D work out

When the user wants a shader background, a WebGPU/Three.js hero, a TSL material, a
particle field, or any GPU-driven 3D scene: hand the scene construction to the
**`webgpu-threejs-tsl`** skill. That's where the renderer, node materials, and
shader craft live. Don't reimplement it here.

## What atelier contributes (do this before/with the handoff)

1. **Resolve the contract** (the DESIGN.md gate). The scene must obey the project's
   palette and motion, not invent neon.
2. **Feed tokens into the scene** so it reads as part of the brand, not a generic demo:
   - **Palette → color nodes.** Pass the contract's colors as the scene's material /
     gradient / light colors (e.g. TSL `color(...)` nodes, fog, background). The hero
     uses `brand`/`accent`/`surface`, not arbitrary shader rainbows.
   - **Motion tokens → time.** Drive oscillation/rotation speed from the contract's
     motion durations/easing so the 3D motion matches the rest of the page's tempo.
   - **Depth/elevation** stays consistent with §4 — a 3D hero shouldn't fight a
     flat (borders-only) system elsewhere.
3. **Hand the skill a brief**, not a blank prompt: "scene = <intent>; palette =
   `<brand/accent/surface hexes from the contract>`; motion tempo = `<duration/ease>`;
   must degrade per below."

## Fallbacks are mandatory (atelier owns these)

A 3D hero that breaks for a third of users is a failure, not a flourish:

- **No WebGPU / no WebGL** (or context-creation fails) → render a static,
  on-contract fallback: a gradient or image hero using the same palette. Feature-
  detect (`navigator.gpu`, a WebGL context probe) and swap; never show a blank canvas.
- **`prefers-reduced-motion`** → freeze to a still frame (or a very low-amplitude
  loop). No autoplaying heavy motion.
- **Performance budget** → cap DPR/particle count on low-power devices; keep the
  hero from tanking the page's interaction. Pair with `perf_budget.py`.
- **Accessibility** → the hero is decorative: it must not trap focus, must have
  `aria-hidden` where appropriate, and real content/contrast must not depend on it.

## Out of scope (don't build it here)

The renderer, shader/TSL authoring, and node-material craft belong to
`webgpu-threejs-tsl`. atelier's job is the contract handoff + the fallbacks — keep
this bridge thin.
