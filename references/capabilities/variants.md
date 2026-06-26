# Capability: Design Variants & Direction Picking

Generate 2–4 differentiated design directions and let the user choose — a
parallel fan-out across directions with a scoring jury.

**Use when:** the brief is open ("give me options", "what could this look like"),
or you're at the start of a design and a direction hasn't been committed.

## Generate (parallel fan-out)

1. Pick differentiated directions, not minor tweaks — draw from distinct schools
   (design-philosophy §5): e.g. editorial / brutalist / soft-organic. Each must
   commit to ONE tone.

### Differentiation must reach the LAYOUT SYSTEM, not just the type+color skin

The most common variants failure is **three directions that share one layout
skeleton, re-skinned** — same grid, same card model, same section rhythm, only the
font and palette swapped. A stakeholder reads that as one design in three colorways,
not three real choices. Each direction must vary its **structural skeleton**, not only
its surface:

- **Layout/grid system** — a single-column editorial measure vs a dense
  multi-column instrument grid vs a roomy card-and-whitespace consumer layout. If two
  of your directions have the same section rhythm, one of them isn't a real
  alternative — push its structure until a wireframe of the two would look different.
- **Compositional density** — generous airy spacing vs tight tabular data-density vs
  big-radius breathing room are themselves a differentiator; don't hold one density
  across all three.
- **The recolor/reskin trap** (the explicit failure mode): same layout + same rhythm,
  different font/palette = NOT differentiated. Two of three directions reading "close
  in layout rhythm" is the symptom — diverge their structure.

### Each direction earns a SIGNATURE visual moment in its own language

A direction reads as a *complete production comp* — not styled placeholder text — when
it carries at least one **signature visual element native to that language**, rendered
inline (SVG/CSS, offline). Type-on-a-ground with no focal moment reads "quieter" and
loses the differentiation + finish axes against a direction that commits:

- a **product-native motif** — e.g. a technical/observability direction earns an
  inline telemetry line-chart or terminal/measurement-grid hero; a soft consumer
  direction earns a true gradient hero or an organic blob; an editorial direction
  earns a masthead rule system / drop-cap / column figure.
- the motif must be **on that direction's contract** (its own tokens, its own
  restraint) and `aria-hidden` if decorative — a signature moment, not ornament slop.
- aim for **rough parity of visual ambition** across the three: don't ship two
  comp-grade directions and one bare text layout. The weakest direction sets the
  finish score for the set.
2. Generate them **in parallel** if the host supports subagents (one agent per
   direction); otherwise generate them serially — same outcome. Each variant
   obeys the DESIGN.md tokens for anything locked (e.g. brand color), and varies
   the unlocked dimensions (layout, type personality, motion).
3. Lay them out for comparison with `assets/engines/canvas.jsx` (side-by-side), or
   serve them as `cards`/`split` on the preview server (`capabilities/preview.md`)
   so the user clicks to pick. **Can't render a comparison** (no renderable target,
   terminal-only)? Sketch each direction as an **ASCII mockup** rather than describing
   it in prose, and use that in the `AskUserQuestion` preview when you ask them to pick
   — see the fidelity ladder in `capabilities/preview.md`.
4. **Hold the CONTENT identical across directions — vary only the design.** The point
   of a comparison is to isolate the design choice, so the headline, subhead, CTA
   label, and feature names must be the *same words* in every direction; only type,
   color, layout, and motion change. Don't reword the copy per direction (that
   confounds the comparison), and never claim "same content, different design" while
   actually changing the words — the framing and the artifact must agree. (If a
   direction's *voice* is itself the thing being explored, say so explicitly and keep
   the structure/feature-set parallel.)

**Two craft notes for comparison pages:** (1) keep the *icon medium* consistent across
directions — if two directions use drawn inline-SVG icons, the third shouldn't fall back
to unicode glyphs (↻ ♪ ☾); it reads as less crafted at close range. (2) `slop_check`'s
`too-many-fonts` will fire on a multi-direction page (each direction commits its own type
system) — that flag is *expected and acceptable here*, since the families ARE the
comparison; don't collapse them to clear it.

## Jury (score before recommending)

Before recommending, score each variant against:
- **Contract fit** — does it honor DESIGN.md? (hard fail if it breaks a locked
  token without reason)
- **Tone clarity** — is the chosen direction unmistakable and intentional?
- **Anti-slop** — does it avoid the blocklist (design-philosophy §3)?
- **Fitness for purpose** — does it serve the product type / audience?

Recommend the winner, and graft the single best idea from the runners-up into it.

### Surface the rationale as structured, scannable metadata (not only prose)

When the directions are shown side by side for a decision, each direction's rationale
should be **legible at a glance in the render**, not buried in a paragraph. Give each
direction a short, parallel block:

- **who it's for** (the persona/buyer), **what it optimizes**, and **the tradeoff**
  (the honest cost of choosing it — every real direction has one).
- a one-line **design-language descriptor** plus compact **type / palette / layout /
  mood** tags, so a stakeholder can compare the languages without reading the CSS.

Keep the structure identical across the three (parallel For / Optimizes / Tradeoff +
the same tag set) so the comparison is fair — the same discipline as content parity,
applied to the rationale.

## Then

Build the chosen direction out fully as a prototype/page, and (if no DESIGN.md
existed) feed the committed decisions back into `generate-design-md`.
