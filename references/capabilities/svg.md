# Capability: SVG

Produce crisp, on-brand SVG — icons, decorative/geometric marks, diagrams, and
animated SVG — bound to the `DESIGN.md` contract.

**First:** resolve the DESIGN.md gate. SVG strokes/fills use the contract tokens
(`var(--color-*)`), not ad-hoc hexes.

## What atelier does well with SVG
- **Icons** — consistent stroke width, grid, and corner radius; one coherent set.
  Prefer a single style (outline OR filled), sized in `em` so they scale with text.
  **QA the family by zooming in:** render the grid large and check every icon shares the
  same optical weight, grid, and cap/join, and that each metaphor is unmistakable (a savings
  icon must read as savings, not a chat bubble; a gear must read as settings, not a sun) —
  redraw any outlier. Verify legibility at the smallest size you ship (16px). And **don't
  overclaim in the showcase copy**: if the small sizes are just the master scaled down, don't
  label them "optically hinted / drawn per size" — either actually hint each size, or describe
  it honestly. Claiming a craft property you didn't implement is the same integrity miss as a
  dead control (see landing-craft "finish interactions honestly").
- **Decorative / geometric marks** — dividers, blobs, grain, marginalia, badges
  (the kind of hand-crafted decorative SVG a designer draws on purpose).
- **Diagrams** — architecture/flow/relationship diagrams with clear hierarchy and
  contract colors (pairs with the data/charts standards in DESIGN.md §8).
- **Animated SVG** — drive paths/strokes via the animation engines
  (`assets/engines/sprites.jsx`) — `stroke-dasharray` draw-on, transforms, morphs.
  Honor `prefers-reduced-motion`.

## Hard rule (refined) — photoreal NO, stylized vector illustration YES
**Never attempt PHOTOREALISTIC people, faces, or product hero shots as SVG** — the
proportions/features come out wrong (design-philosophy §3); use a real image or an honest
placeholder for those. BUT **stylized / flat / geometric vector illustration is squarely in
scope and a real deliverable** — landscapes, abstract scenes, spot illustrations, isometric
scenes, editorial hero art. Brands ship these constantly. When asked for one, don't refuse
and don't half-it — make it genuinely good (see "Illustration craft" below).

## Illustration craft (when the SVG IS the artwork, e.g. a hero scene)
A stylized scene is judged as *art*, not as a UI. The craft that separates "polished brand
illustration" from "a few flat shapes":

- **Full-bleed presence — do NOT mat it.** A hero illustration fills its canvas edge-to-edge.
  Wrapping the art in a card/border/dark frame shrinks it and kills impact. Let it bleed.
- **One off-center focal point + a lead-line.** Place the focal element on a rule-of-thirds
  intersection (not dead center), and add a directional device — a winding path, a furrow, a
  river, a power-line run, a road — that routes the eye to it. A scene with no lead-line lets
  the gaze wander.
- **Real depth via atmospheric perspective — push it hard.** 4–6 receding planes with
  *distinct value steps*. The farthest hills should go genuinely hazy: desaturate them toward
  a lavender-grey, LIFT their value (lighter, lower-contrast), and let them sit *behind* the
  focal light's air — not a saturated green ridge on the same plane as the midground. Nearer
  layers saturate + darken. Vary element sizes by distance (big turbine near the focal point,
  tiny ghosted ones on far ridges). A flat, equally-saturated set of hills is the #1 tell that
  depth was faked; if the back ridge reads as "same paint, smaller", redo it hazier.
  **Value discipline beats richness.** Depth reads from CLEAN separation between a few planes,
  not from cramming elements into the middle distance — extra detail in the mid-ground muddies
  the value steps and *destroys* the recession. Keep the mid-ground quiet and value-distinct;
  let each plane be one clear tone lighter/hazier than the one in front. 3–4 crisply-stepped
  planes beat 6 muddy ones. Don't fight your own focal sun with a second heavy attractor.
- **Give the foreground a near-field hero anchor — and MODEL it, don't silhouette it.** The
  closest row of repeated elements (the front solar panels, the nearest tree, the near rocks)
  should jump in size and carry the strongest detail + a real specular highlight — a clear
  near-field entry point for the eye, then recession behind. Critically, the foreground must
  carry its OWN internal value range: a lit plane, a core shadow, a touch of reflected/bounce
  light, and a crisp specular edge. A foreground rendered as ONE flat dark shape is not "depth"
  — it's a *value hole* that reads as a hard cut-out pasted on the scene, and a blind judge will
  dock depth for it every time. The nearest mass should be the richest-modeled region on the
  canvas, not the emptiest.
- **Kill gradient banding — it reads as cheap.** Big smooth sky/sea gradients band into visible
  stripes on most displays, and banding torpedoes both depth and craft. Defeat it: overlay a
  faint film-grain / dither (a low-opacity `feTurbulence` or a tiled noise), use enough stops
  (or a subtle hue shift across the ramp, not just lightness), and avoid a single 2-stop ramp
  spanning the whole sky. Render and ZOOM: if you can see stair-steps in the gradient, fix it
  before shipping. Evenly-stepped, perfectly-parallel bands also flatten depth — break the
  horizon with atmospheric haze and let the value steps be *unequal* (the air compresses tones
  toward the distance), not a tidy equal-interval ladder.
- **Balance mass around the off-center focal.** If the headline + the dense element field both
  sit left, the right goes empty and the frame tips. Earn the off-center focal by placing one
  mid-distance counterweight (a substation, a turbine cluster, a built element) on the lighter
  side. Check the rendered composition for a lopsided frame.
- **Repeated elements must READ at scale.** A solar field / crowd / forest can't be thin
  tilted dashes — that reads as "a field of commas." Draw each unit as a real dimensional
  object (a panel = framed module + glass face + cell grid + mount + cast shadow + one sky-
  specular glint), in perspective-scaled receding rows (larger/darker front → smaller/hazier
  back). Render and ZOOM IN: does each unit unmistakably read as the thing it represents?
- **Even quality across the whole canvas.** A gorgeous sky over a flat/noisy foreground loses.
  Bring the foreground/midground craft up to the level of the best region.
- **Commit to the scene's real palette — don't let UI anti-slop rules distort the art.**
  `slop_check`'s warm-neutral and generic-font flags target UI *surfaces/chrome*, not artwork.
  A sunset sky is legitimately warm; do NOT add a dark mat or recolor the scene just to clear
  a UI-oriented flag (that's gaming the check at the cost of the art). Run slop_check against
  the page's chrome/caption, and judge the illustration on its own merits.
- **Copy over busy artwork needs a plate.** A headline/dek sitting directly on a detailed
  region (a panel grid, foliage) loses contrast and reads muddy. Back it with a scrim,
  gradient plate, or a calm zone of the art reserved for type — never let copy fight a
  texture. And proof the text: a stray "the. sun" / odd kerning on the hero line is a
  credibility-killer.
- **The lead-line must terminate AT the focal point.** If the road/river points toward the
  buildings while the sun is the focal, the strongest line and the strongest light disagree
  and the composition feels off. Route the lead-line to the focal element itself.
- **When iterating, HOLD every prior win — don't trade.** Fixing the targeted dimension
  (e.g. depth) must NOT regress headline legibility, lead-line→focal alignment, balance, or
  the near→mid→far chain. They're not in tension — you can satisfy all at once. Before
  shipping a revision, re-run the WHOLE illustration checklist against the render, not just
  the thing you just changed; a fix that breaks two other dimensions is a net loss.
- **Originality — commit to ONE specific, non-default concept.** The single biggest separator
  between "polished brand illustration" and "competent stock" is a memorable, *specific* idea —
  and it's the dimension a generic best-effort always ties on. Decide the one thing a viewer
  remembers BEFORE you draw: an unexpected vantage (worm's-eye, from-the-water, behind a
  near-field object), a committed time-of-day/weather moment (the green flash, fog burning off,
  storm light), or a signature compositional spine (a single bold diagonal, a strong silhouette
  read, a deliberate asymmetry). Then make that idea the loudest thing on the canvas. The
  textbook arrangement — subject centered-ish, "layered dusk sky," symmetric calm — is exactly
  the default a generic generator also lands on, so it reads as a trope and scores a tie, not a
  win. If your concept could describe a hundred other images of the same subject, it isn't
  specific enough yet. (This does NOT mean clutter or gimmick — one strong idea, cleanly
  executed, beats five competing ones.)
- **Self-QA an illustration by LOOKING.** Screenshot it (`scripts/screenshot.mjs`), open the
  PNG, and critique your own composition, depth, focal clarity, flat/empty areas, gradient
  banding, and whether each element reads. Iterate on the render — code-reading isn't enough.

## Practical
- Keep SVGs inline (themeable by `currentColor` / CSS vars) rather than as opaque
  `<img>` when they should pick up the palette.
- Mark decorative SVG `aria-hidden="true"`; give meaningful SVG a `<title>`.
- Optimize: drop editor metadata, round path precision, reuse `<symbol>`/`<use>`.
