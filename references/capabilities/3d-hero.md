# Capability: 3D / shader hero (bridge — delegate the GPU, own the design)

A WebGPU/Three.js/TSL shader hero is a different discipline with its own maintained
skill. atelier does **not** build a GPU stack — it routes the 3D work to the
`webgpu-threejs-tsl` skill and contributes the part that keeps the result on-brand:
the design tokens, and the fallbacks.

## The specialist skill (separate, maintained)

The renderer/shader work belongs to a **separate, independently maintained skill**:

- **Skill name:** `webgpu-threejs-tsl`
- **Source repo:** `webgpu-claude-skill` (the skill ships from that repo; it is not
  vendored into atelier and is not maintained here).
- **Owns:** the WebGPU/WebGL renderer, Three.js scene graph, TSL node materials,
  shader authoring, and GPU performance craft.

If `webgpu-threejs-tsl` is not installed, say so and stop at the fallback: ship the
static on-contract hero (see below) rather than hand-rolling a renderer in atelier.

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
3. **Hand the skill a brief**, not a blank prompt. Use this exact handoff format so
   `webgpu-threejs-tsl` has everything it needs and nothing it must guess:

   ```text
   Skill: webgpu-threejs-tsl
   scene:    <intent — e.g. "slow-drifting particle field behind the H1">
   palette:  brand=<#hex> accent=<#hex> surface=<#hex>   (from the DESIGN.md contract)
   motion:   duration=<ms> easing=<token>                (match the page's tempo)
   depth:    <flat | subtle-elevation | layered>         (consistent with §4)
   mount:    <selector/region the canvas occupies>
   fallbacks: atelier owns them — render decorative, aria-hidden, must degrade per below.
   ```

   The brief is one-way: atelier supplies the contract values, the specialist returns
   the scene. atelier does not review the shader internals — it re-checks the result
   against the contract and the fallback requirements.

## The division of labour

Crisp split, so nothing falls between the two skills:

- **`webgpu-threejs-tsl` owns:** the renderer, the scene graph, TSL/shader materials,
  and GPU perf craft inside the working path.
- **atelier owns the fallbacks and the contract:** reduced-motion behaviour, the
  no-WebGPU / no-WebGL path, the performance budget (DPR/particle caps), and the
  accessibility contract (decorative, no focus trap, content never depends on it).
  These are atelier's responsibility whether or not the specialist skill is present.

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

The renderer, shader/TSL authoring, and node-material craft belong to the separate
`webgpu-threejs-tsl` skill (repo `webgpu-claude-skill`). atelier's job is the contract
handoff + the fallbacks — keep this bridge thin.
