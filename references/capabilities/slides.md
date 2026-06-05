# Capability: Slides & Decks

Build presentation decks in HTML with a real slide engine, speaker notes, and
optional PDF/PPTX export.

**First:** resolve the DESIGN.md gate. The deck's palette/type/motion come from
the contract; a deck is just another surface that must match the brand.

## Engine (vendored assets)

- `assets/engines/deck.js` — slide-deck web component (navigation, transitions,
  speaker notes, progress).
- `assets/engines/deck-index.html` — multi-file deck aggregator.

## How to build

1. Answer the four design questions (design-philosophy §1) for the deck's purpose
   and audience, then derive the layout rhythm from the DESIGN.md tokens.
2. Author slides as sections the engine drives. Keep one idea per slide; let the
   type scale and spacing carry hierarchy.
3. Add **speaker notes** per slide (the engine supports them) — a deck without
   notes is half-delivered for a real presentation.
4. Motion: slide-to-slide transitions are fine here (unlike narrated animations,
   which are one continuous motion). Keep them consistent and subtle.

## Export (optional, ask first)

Offer derivatives only if the user wants them:
- **PDF** — print-to-PDF of the deck (headless browser print).
- **PPTX** — editable export via an external slides-to-pptx step (not bundled).

## Preview

Serve the deck through the live preview server for the user to click through —
see `capabilities/preview.md`.
