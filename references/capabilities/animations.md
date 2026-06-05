# Capability: Animations, Explainers & Narrated Video

Produce motion pieces in HTML — from a single hero animation to a long-form
narrated explainer — and export them to MP4/GIF.

**First:** resolve the DESIGN.md gate. Motion durations/easing and the palette
come from the contract.

## Engines (vendored assets)

- `assets/engines/sprites.jsx` — Stage + Sprite engine for timeline-driven motion.
- `assets/engines/narration.jsx` — narration-driven animation: a measured timeline
  drives the visuals in lockstep with a voiceover.

## Ironclad rule for narrated pieces

A narrated explainer is **one continuous motion narrative** — NOT a slideshow.
No PowerPoint-style hard cuts between "slides". Elements enter, transform, and
exit as a single flowing piece. This is the single biggest quality lever.

## Pipeline (long-form narrated)

1. Write the script; generate voiceover with a TTS engine (e.g. Doubao TTS for
   human-like delivery). Measure each clip's real duration.
2. Build a `timeline.json` keyed to those measured durations.
3. `NarrationStage` drives the visuals against the timeline.
4. Mix down with ducking (BGM under voice). Ship the **live-play HTML** and the
   **MP4** in parallel.

## Export to video

```bash
scripts/export_video.sh path/to/animation.html out.mp4   # or out.gif
```

- Default delivery is an **MP4 with audio** (SFX + BGM) — a silent version feels
  cheap. Base 25fps + 60fps interpolation; palette-optimized GIF; auto fade.
- Requires `ffmpeg` + a headless browser (puppeteer/playwright). If missing, the
  script warns and produces what it can (e.g. silent / frames only) — see
  `assets/media/README.md` for BGM/SFX.

## Preview

For a live, scrubbable view, serve the HTML through the preview server
(`capabilities/preview.md`).

## Deep craft (read on demand for sophisticated / cinematic work)

For anything beyond a simple reveal — narrated explainers, hero films, multi-scene
pieces — read the craft references under `capabilities/animation/` (vendored from
huashu-design, MIT):

- **`animation/animation-pitfalls.md`** — the failure modes: fallback-font width
  measurement (wrap DOM measurement in `document.fonts.ready`), first-frame jumps,
  timing drift. Read this BEFORE shipping motion.
- **`animation/cinematic-patterns.md`** — the vocabulary of good motion (entrances,
  holds, transitions as one continuous narrative).
- **`animation/scene-templates.md`** — ready scene structures to adapt.
- **`animation/animation-best-practices.md`** — the full reference.

The engines (`assets/engines/narration.jsx`, `sprites.jsx`) are the runtime; these
are the craft that keeps the output from looking cheap.
