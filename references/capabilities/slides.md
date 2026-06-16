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

## Deck craft — defects that quietly cost you

These are not polish; each is a real, judge-visible defect:

- **Embed/inline every font (base64 woff2 in the deck).** A title slide that
  falls back to a system serif because a face didn't load is a defect, not a
  fallback — and it's the most-noticed slide in the deck. Subset to the weights
  you use and inline them as `@font-face` so *no* slide ever degrades, online or
  off. (See "Fonts & true offline use" below; for a judged deck, treat inlining
  as the default, not the exception.)
- **Compose to the full slide — no one-sided voids ANYWHERE on the frame.** Every
  slide fills its frame intentionally. A void is any sizable *one-sided* dead region
  — not only a bottom band, but a hollow central stripe, an empty right (or left)
  half, or an abandoned quadrant. The recurring defects, all judged: a chart that
  ends mid-slide leaving dead air above the footer; a thesis line stranded at the
  top with a vacant center; KPI chips clustered in one corner leaving the opposite
  half empty. Fix by composing the WHOLE canvas: size content to the space (a taller
  chart, a baseline-anchored axis), add a lower-band takeaway/source line, span a
  full-height two-column layout, or distribute elements across the frame — not by
  leaving the gap. A statement slide may breathe, but its negative space must be
  **deliberately centered and symmetric** (top ≈ bottom AND left ≈ right), never a
  one-sided field. **Self-check every rendered slide as a whole:** mentally quarter
  it — if any quadrant or half is accidentally empty while the others carry weight,
  it's unbalanced; rebalance before exporting.
- **Number sections consistently and correctly.** If you run an eyebrow/section
  system, each section gets its own number and no number repeats across two
  different sections (don't ship two "03"s). Number all content sections or none
  — and keep it off-by-one-free through the CTA.
- **Build chart bars/segments as solid-fill rectangles, not baked gradients.** A
  bar drawn as a `<div>` with a flat `background-color` (no gradient, no image,
  no inner SVG) exports as a **native, restylable PPTX shape** — the recipient can
  recolor it in PowerPoint. A bar painted with a CSS gradient or rendered inside an
  `<svg>`/`<canvas>` bakes into the background image and can't be restyled. Same
  for KPI/accent blocks, rules, and solid panels: flat fills nativize, gradients
  bake. Reserve gradients for genuinely un-translatable art — and **keep that baked
  layer minimal** (a small accent, not a full-slide raster): the more of the slide
  that is native text + flat-fill shapes, the more of it the recipient can restyle,
  which is what "editable PPTX" means. A deck whose every element nativizes (text +
  flat charts + flat panels) is both pixel-faithful AND almost entirely editable.
- **Match the type to the register.** A business/main-stage keynote wants a
  confident, legible system (a strong grotesque, or a restrained transitional serif
  paired with a clean sans) — *not* a high-contrast Didone/fashion display at large
  sizes, which reads as a magazine cover, the wrong register. Pick the family for
  the room, not for drama; let scale + weight contrast carry the impact.

## The narrative carries the deck — design serves the story

A pitch/keynote is judged on its *argument*, not just its surfaces. Two content
rules that decide whether a deck persuades:

- **The proof/traction slide must be concrete and multi-signal.** One lone abstract
  number ("9 hours saved") reads as thin. Real launch decks stack *specific*,
  varied proof: a named funding line ($X seed, lead investor), a recognizable
  customer/logo wall, AND 3–4 distinct metrics (waitlist, retention, time saved,
  revenue) — each labeled with its unit and period. Specificity is what sells; a
  reader believes "$3.1M seed · 1,200 on the waitlist · 94% of questions answered"
  far more than a single round figure. **Be concrete AND honest at once:** if the
  numbers are illustrative, you can still show the full multi-signal layout and add
  a quiet "illustrative beta-cohort figures" footnote — honesty and richness are not
  a trade-off, and a lean-but-honest slide still loses to a rich-and-honest one.
- **Hold the problem→solution→how→proof→ask arc** and make each slide advance it;
  don't let a beautiful slide stall the argument. The closing slide states one clear
  ask. Keep any section-numbering/eyebrow system consistent and off-by-one-free
  (number all content sections or none — don't let the CTA read "07" of 8).
- **Give the pivot its own beat — but a DISTINCT one, not a second copy of the chart.**
  The turn the talk hinges on (the reversal, the surge→correction) earns emphasis, but the
  pivot slide and the data slide must do *different* work: the pivot states the *interpretive
  claim* ("It wasn't a collapse — it was a correction"), the chart supplies the *evidence*.
  If a "turn" slide shows the same 28→19→22 numbers the very next chart slide plots, a judge
  reads it as the same beat twice, not setup→payoff — collapse them or make the pivot a claim
  the chart then proves. And close ONCE: two near-identical concluding slides dilute the
  landing — one decisive takeaway.
- **Plant a hook and pay it off.** A keynote that lands carries one figure or phrase from the
  thesis through to the close (e.g. seed "the 22% that held" on the thesis beat, reference it
  at the turn, and pay it off in the final takeaway "plan for 22%, not 4%"). A deck where every
  slide is a fresh fact with no carried thread reads as a list, not an argument; the through-line
  is what makes the ending feel earned.

## Export (optional, ask first)

Offer derivatives only if the user wants them. Both exporters need the headless
browser; `export PATH="$HOME/.local/bin:$PATH"` first if ffmpeg/chromium live there.

- **PDF — `scripts/export_pdf.mjs <deck.html> <out.pdf>`.** Flattens the `<deck-stage>`
  (the shadow-DOM slot doesn't paginate headlessly) and prints one slide per page at the
  deck's native pixel size. Output is **vector** — selectable text, embedded fonts, sharp at
  any zoom — not an image bed. Works on any page too (infographics: pass `--format A4` or
  `--width/--height`, or let the page's own `@page` rule win).
- **PPTX — editable, two steps, stdlib-only on the Python side:**
  1. `node scripts/extract_deck.mjs <deck.html> <specDir>` — captures each slide's text runs
     (box/font/color/align) AND its **nativizable shapes** (solid-fill rectangles: bars,
     KPI/accent blocks, rules, panels — with corner radius and any solid border), then hides
     both and screenshots a background PNG that keeps only un-translatable art
     (gradients/SVG/photos/complex backgrounds).
  2. `python3 scripts/export_pptx.py <specDir> <out.pptx>` — lays each background full-bleed,
     then emits every shape as a **native, restylable OOXML object** (`<a:prstGeom>` rect /
     roundRect with `solidFill` + optional `<a:ln>`) and every text run as a **real, editable
     text frame**. Z-order is bg < shapes < text. Opens looking identical, but words AND
     simple shapes are individually selectable/editable in PowerPoint — not an image-bed fake.
  Honest limit: only genuinely un-translatable art (gradients, SVG paths, photos, complex
  backgrounds) rides in the background image — so author chart bars/KPI blocks as flat
  solid-fill rects (see "Deck craft" above) to keep them native and restylable. Speaker-notes
  export is not yet wired into the PPTX path — note that if the user needs editable notes.

**Fonts & true offline use.** A Google-Fonts `<link>` is fine for most decks (the deck
boots and degrades to a fallback face offline). But when the deck must look *pixel-correct
offline* — kiosk, air-gapped demo, a judged "fully self-contained" bar — inline the faces as
base64 `@font-face` (subset to the weights you use) instead of the link, so the intended type
renders with zero network. Same option applies to prototypes and any single-file deliverable.

The same `export_pdf.mjs` is the print-grade export for **infographics / data-viz** (vector
PDF); for raster use `screenshot.mjs --full` (300dpi-ish via deviceScaleFactor), and for SVG
deliverables author the art as inline `<svg>` and save it directly (already vector).

## Preview

Serve the deck through the live preview server for the user to click through —
see `capabilities/preview.md`.
