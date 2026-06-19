# Capability: Data-viz & dashboard craft (integrity + encoding discipline)

`knowledge/charts.csv` tells you *which* chart fits a data question. This file is the
craft layer for **dashboards and any data visualization**: the difference between a
dashboard that an analyst trusts and one that quietly lies. Read it whenever you build a
dashboard, KPI row, chart, funnel, cohort, or data table. Pair it with the universal QA
gates (focus-visible, honest working controls, anti-slop) — those apply here too.

This is a **product**-register surface (the design SERVES the product); see `references/registers/product.md` for the clarity bar and how QA escalates decorative-cost tells here.

## 1. Data integrity — a dashboard that's internally inconsistent is worse than none

An analyst reads these numbers literally. Any silent gap reads as "there is no value there."

- **Show every step or none.** A funnel that labels three of four drop-offs implies the
  unlabeled stage had zero drop. Show the count + % drop on *every* stage, or show none.
- **Parts reconcile to the stated total.** Stacked-bar / donut / breakdown segments must
  sum to the headline number (e.g. segment counts add up to the "9.3k" center label).
  Compute them so they actually reconcile — don't eyeball widths.
- **Deltas match arithmetic.** "vs prev 44.5k" with a "+18%" badge must be true against the
  shown current value. Wrong-direction or wrong-magnitude deltas destroy trust instantly.
- **A DERIVED figure must read as derived — or stay off the chart.** A computed roll-up (a YoY %,
  a peak, an average, a CAGR) is correct arithmetic but, dropped onto a chart as a bare badge, it
  reads as a *new asserted number* a reviewer can't tie back to the data — borderline scope-creep on
  a fixed-dataset brief. If you surface a derived figure, *show its derivation* in the label
  ("+53.7% vs Jul" / "12-mo growth") so it's transparently a function of shown values, or leave it
  off and let the trend speak. Never present a derived number with the same weight as a given KPI.
- **Chart geometry matches the data.** Bar widths / line endpoints / arc angles must
  reflect the real values, and the text/aria summary must match what's drawn.
- **One scale maps value→position — gridlines, axis labels, AND data marks all use it.**
  The single most common chart lie that passes a values-are-correct check: the bars are
  numerically right but the reference grid is drawn on a *different* scale, so a value reads
  wrong *against the grid* (e.g. a "20%" gridline sits where 23% should, and a correct 19% bar
  visibly pierces it, scanning as ">20%"). Derive gridline positions, tick-label positions,
  and bar/point positions from the SAME `value→pixel` function — never place the grid or its
  labels by hand at eyeballed offsets. Verify ON THE RENDER that the gridline labeled `V` sits
  exactly at the top of a hypothetical value-`V` bar, that the baseline gridline is at 0, and
  that each bar lands on its own value's gridline. (This is §19d "geometric truth" for charts:
  a misaligned reference grid is a fabricated reading even when the underlying numbers are right.)
- **A small-magnitude series clamped to a minimum pixel floor is BOTH a lie and illegible — never
  floor a magnitude to a constant height.** When one stacked/overlaid series is tiny against the
  shared scale (e.g. an error band of 0.16k–0.95k riding on an 80k traffic scale, or a 7% slice
  against a 100% bar), the lazy fix — `height = Math.max(value × scale, 1px)` so it's "visible" — is
  the trap. A 1px floor makes a 0.16 and a 0.95 render at the *same* height: the 6× difference
  vanishes, the series stops being proportional (a fabricated reading), AND a 1px hairline is too
  thin to read as data (it loses legibility too). Do NOT floor it. Instead pick an HONEST encoding
  that keeps proportion AND legibility: **(a)** if the small series carries real signal an operator
  must compare hour-to-hour (the error band IS the point of an error chart), give it its OWN faithful
  scale in a **linked secondary view** — a thin band/strip or a small-multiple directly below the
  primary, sharing the x-axis, on its own clearly-labeled value axis (so 0.95k vs 0.16k is a visible
  6× difference) — rather than crushing it into the primary's stack where it's sub-pixel; **(b)** if
  it must stay in the stack for the sum-to-total story, draw it strictly proportional (`value × scale`,
  no floor) and accept that it's a thin honest ribbon — then surface the spike via an annotation/marker
  and the legend ("errors peak 0.95k @ 15:00"), not by fattening the band. The test: two error
  values that differ MUST differ in drawn height; if your floor makes them equal, the encoding lies.
  (This is §19d "chart geometry matches the data" for a small overlaid series: proportionality is not
  optional just because the values are small.)
- **No triplicated magnitude.** Don't print the same number three ways in one row
  (label-count + in-bar count + percent). Pick the two that carry distinct meaning.

## 2. Color is an encoding, not decoration

- **Same color = same meaning, everywhere.** If green is "primary series", it is the
  primary series in every panel — not also a category dot, not also "positive delta" by
  coincidence. A hue that appears once and never reconnects is decoration, not an encoding.
- **A categorical hue must not also signal delta direction.** If red already encodes a
  category (e.g. the "fully remote" series), don't *also* paint the ▲ positive-delta arrows
  red — now red means two things at once. Give delta direction its own consistent treatment
  (e.g. up = ink/green ▲, down = gray ▼) kept distinct from any categorical palette.
- **Don't use a status color as a category.** Amber/"warn" and red/"negative" are reserved
  for status. Using amber as the dot for a metric whose delta is *positive* contradicts the
  system. Use the neutral/series palette for categories; keep semantic colors for status.
- **Cohort/heatmap = single-hue sequential scale** (light→dark = low→high), not a rainbow.
  Expose the value in every cell and ship a scale legend.
  **A heatmap cell's shade is a function of its VALUE — never its row/column position.** The single
  most common heatmap lie that still "looks like a heatmap": you band by column (M0 darkest, M1
  lighter, M2 lighter, M3 lightest) or by row, so cells with the *same* value get *different* shades
  and a higher value can read lighter than a lower one. That's a fabricated reading — the color no
  longer encodes the number. Map shade from the value through the SAME scale for every cell: pick a
  domain (e.g. the legend's 80→100% range), and `shade = ramp((value − min) / (max − min))` applied
  identically across the whole grid. Then **equal values MUST get equal shades, and a strictly higher
  value MUST be strictly darker** — verify this ON THE RENDER (two 100% cells look identical; an 83%
  cell is visibly lighter than a 92% cell *regardless of which column they sit in*). If your domain is
  narrow (e.g. 83–100), stretch the ramp across that domain so the steps are perceptible rather than
  collapsing 90/91/92 into one shade — but the mapping stays value-driven, not positional. Not-yet-
  elapsed / missing cells get a distinct non-color treatment (hatch / "—"), never a zero-value shade.
  Keep the ramp's LIGHT end legible AND substantial: flip the in-cell value to dark ink on light
  cells so every value stays AA-readable, and don't begin the scale so pale that the low-value cells
  read as washed-out/empty next to a competitor's (even if incorrectly) uniformly-saturated grid —
  start the sequential ramp at a visible tint, not near-white, so the whole grid reads as a confident
  instrument while staying strictly value-monotonic.
- **Never encode by color alone.** Deltas carry a sign + arrow glyph (colorblind-safe), not
  just red/green. Series get labels/patterns, not only hue.
- **Chromatic restraint = engineered calm — a dense instrument UI should hold FEW hues.** On a
  data-dense surface (a dashboard, a trace waterfall, an observability landing) the fastest way to
  look *busy* — and to lose "restraint" against a sparser competitor — is to encode with a rainbow
  of distinct hues. Prefer **tints/shades of one or two hues** (a mono or duotone ramp: e.g. one
  cool series hue stepped light→dark, plus ink/neutral) for bars, spans, and chart series, and keep
  the page's ONE reserved accent (the CTA / the alert-hot state) out of the routine data. A trace
  waterfall in five different colors reads as decoration; the same waterfall in stepped tints of a
  single hue reads as a precision instrument. Density is fine — *chromatic* density is what reads as
  noise. When you've made everything legible and still feel busy, the fix is almost always "collapse
  the palette," not "remove data."

## 3. Numbers & density

- **Tabular numerals on every figure** (`font-feature-settings:"tnum"` / a mono) so columns
  align and values don't jitter when they update.
- **Density is rich, NOT cramped — the dense surface still has a comfortable floor.** "Dense" is the
  *amount* of information per screen, not *small* type and *tight* rows. The fastest way to lose the
  legibility dimension on a dashboard is to win density by shrinking everything: 11px labels, 12px
  body, 4px row gaps, a hero KPI that's barely larger than its caption. A dense instrument that "runs
  hot" reads as harder to scan, not more capable. Hold a real type hierarchy with a comfortable floor:
  the **hero KPI value commands its card** (a clear, large figure — not a number only a touch bigger
  than its label), supporting **labels and table body stay at a readable size** (≈13px+ for data rows,
  never sub-12px for values an operator reads all day), and rows get enough vertical rhythm that the
  eye tracks a line without effort. Achieve density by *fitting more well-sized panels into the grid*
  (2-up rows, a packed but aligned layout), not by miniaturizing the type inside them. The win is
  "rich AND comfortable to read," which beats both "sparse" and "cramped"; a competitor that types its
  KPIs larger and breathes its rows will out-score a technically-denser surface on legibility — match
  its comfort while keeping your higher information density.
- **Dense but scannable:** a clear KPI row, one primary chart with real hierarchy, secondary
  panels that don't compete, a table with aligned right-set numerics. Show a prior-value
  reference on KPIs ("vs 44.5k", "2.2pp") — more informative than "vs prev period".
- **A panel must be FILLED by its content — true-zero is not licence for a dead upper void.** The
  most common way a correct, honest dashboard loses the *density* dimension: a primary trend on a
  true-zero axis where the series sits in the upper band (e.g. $96k–$148k against a 0–160k scale)
  floats in the bottom third of an over-tall full-width panel, leaving the top half empty air. The
  axis is right; the *panel proportion* is wrong. Fixes (keep the honest zero baseline): size the
  plot height so the data spans most of it (a trend panel roughly 2:1–3:1 wide, not a tall square
  with acres above the line); add a faint zero-band shading or a `// axis break` indicator ONLY if
  you also keep the true zero visible (never a silent truncation); or — better for density —
  **don't let the commanding chart span full-width with empty air beside/above it: pair it in a row
  with a secondary panel** (composition, a stat stack) so the screen reads as a packed instrument,
  not a lone chart over a void. A dashboard is judged on *uniform richness per screen*: a 2-column
  trend+composition row above a 2-column breakdown row reads denser and more instrument-like than
  four full-width bands stacked with gaps. No dead voids inside or beside a panel; no claustrophobic
  cramming either — every panel earns its box and breathes within it (the deck/poster no-void rule,
  applied to a dashboard grid).
- **Cap categories to what stays legible — aggregate or re-type the rest.** A categorical chart
  (bar / stacked-bar) must label and visually separate *every* mark it draws. If the data has
  more categories than fit at a readable mark size (rule of thumb: each bar needs enough height
  for its own axis label — ~10–15 rows in a short panel, not 100), do ONE of: show **top-N with
  the remainder aggregated** ("Top 12 · +88 more"), switch to a type that scales (treemap, or a
  ranked table with inline mini-bars), or make the panel **scrollable with a header summary**
  (the same top-N-plus-remainder pattern a long entity list uses). A panel that renders dozens of
  sub-pixel, unlabeled bars is an illegible smear — it conveys *nothing* actionable, and is a
  **P0 legibility failure, not a "small labels" nit.** The **rendered mark count must match any
  "top N" caption** — a "showing top 10" label over a chart that actually draws 100 bars is both
  illegible *and* dishonest. Each visible row needs its **identity (a name/label, not only an
  opaque id)** and its **value on the row**, not hidden in a hover tooltip.
- **Realistic data, never lorem.** Plausible magnitudes, consistent across panels.

## 4. Interactive chart controls must actually work

- **The date range IS the dashboard's core interaction — make it actually re-slice.** On a
  data dashboard, a date-range/granularity control must re-render the series (slice the
  existing data array to the window) and update the KPIs, not just rewrite labels. A
  label-only toggle reads as broken on the one control that matters most. (Relabeling alone
  is acceptable only on a non-data marketing page.)
- **Chart tooltips sit on the data point**, with a vertical crosshair so "nearest point" is
  visible — not parked at a fixed y. Position from the point's own coordinates, not fragile
  `scrollY` math, and **clamp/edge-flip** so the tip never clips off the panel at the last
  data point. Provide a keyboard/focus path (not mouse-only) and announce value changes via
  a polite `aria-live` region (a changing `aria-valuetext` alone isn't reliably read).
- `:focus-visible` on every control; `aria-label` text equivalents on each SVG chart
  ("rising from ~37k to 52.8k over 30 days"); `prefers-reduced-motion` honored.
- **Give the dashboard a real document skeleton — it's part of hierarchy, not just a11y polish.** An
  analytics surface is keyboard-and-screen-reader operated by analysts; in this register a judge reads
  the structure as hierarchy. Wrap the primary content in a `<main>` landmark (header/nav/footer
  outside it), open with a real visible `<h1>` (the page/product title — not a hidden one), and nest
  each panel's heading correctly (`<h2>` per region, `<h3>` per panel) so the heading outline mirrors
  the visual reading order KPIs → trend → breakdowns. Ship a **skip-to-content link** as the first
  focusable element. Don't hide the page's only structural heading: a `visually-hidden` `<h2>` over the
  KPI row is fine as a label, but the document must still expose a coherent, *visible* heading spine.
  A page that renders perfectly but has no `<main>`, no skip link, and a flat/hidden heading tree
  loses the hierarchy dimension to one that's structured — same pixels, weaker instrument.

## Print posters & infographics (one-page, export-grade)

A single-page data poster (→ PDF) is judged like a printed spread, on top of the integrity rules
above. Where a dashboard is a screen, a poster is an object on a wall AND a close read:

- **A commanding, print-editorial hero — loud in scale AND color.** The poster's single biggest
  takeaway (the hero number / headline) must read from across a room — set it large and confident
  in a print-magazine voice (a strong editorial display serif, or a heavy grotesque at real size),
  the loudest element on the sheet by a wide margin. **Loudness is scale + chromatic punch, not size
  alone:** a huge near-black hero gets out-punched by a smaller hero set in a bold signal/accent
  colour, so carry the hero in the brand's accent (or maximal value contrast against the ground),
  not quiet ink — it should be unmistakably the single most arresting element as a thumbnail. A
  timid hero that reads like a dashboard card is the most common way a poster loses type-craft; the
  hero carries the room, the charts reward the approach.
- **Every panel earns its space — no sparse cards.** Poster density should be *uniform richness*:
  a single big stat or a lone circle marooned in a large empty card reads as unfinished next to
  dense neighbors. Give each panel enough — a supporting breakdown, an annotation, a caption, a
  derived figure, a small secondary chart — that it carries weight, or tighten its box. (This is the
  deck no-void rule applied to a poster's grid: a one-sided void inside a panel is still a void.)
  Keep a clear reading order (a numbered or visually-weighted path top→bottom) through the richness.
- **Make it a real PRINT artifact, not a screen PDF at the trim size.** Export production-ready:
  include a **bleed** (~3mm / ~12px past the trim on every edge, with full-bleed color reaching into
  it) and **crop/trim marks** at the four corners (draw them in the HTML; size the page box to
  trim+bleed via `export_pdf.mjs --width/--height` or the page's own `@page`), and **embed every
  font** (inline base64 woff2) so the PDF carries them. Keep charts as vector (HTML/CSS/inline-SVG,
  never a `<canvas>` bitmap) so the text stays selectable and the marks stay crisp. A poster a
  printer could run beats a screenshot-grade PDF on export fidelity.
  **Keep the WHOLE artifact vector — not just the text/charts.** Headless Chromium *rasterizes*
  certain decoration into image XObjects on print: `box-shadow`/`filter:`/`backdrop-filter` (soft
  shadows, blurs), `radial-gradient`/`conic-gradient`, and gradients painted onto large full-bleed
  bands. A poster that's vector type over rasterized gradient/shadow bands is NOT a fully-vector PDF
  and loses to one that is. For a print poster prefer **flat fills or simple `linear-gradient`s**
  (which Chromium keeps vector) for big bands, and drop soft shadows/blurs from the print artifact.
  Verify: count image XObjects in the exported PDF — it should be **0** (or only genuine photos),
  not a pile of rasterized gradient bands.

## Definition of done for a dashboard / data viz

- [ ] Every funnel stage shows its drop (or none do); parts sum to the stated total
- [ ] Deltas are arithmetically correct and carry sign+arrow, not color alone
- [ ] Each color has ONE consistent meaning; status colors aren't reused as categories
- [ ] Cohort/heatmap is a single-hue sequential scale with values + legend; shade is a function of the cell VALUE (not its row/column) — equal values → equal shades, higher value → strictly darker (verified on the render)
- [ ] Tabular numerals everywhere; no triplicated magnitudes
- [ ] No magnitude floored to a constant pixel height — a small overlaid/stacked series is drawn strictly proportional (two differing values differ in drawn height), or moved to a linked secondary view on its own faithful scale; never a `max(value×scale, 1px)` clamp
- [ ] Dense but comfortable: hero KPI value commands its card; data labels/table body ≥~13px (never sub-12px); rows have readable vertical rhythm — density from more well-sized panels, not miniaturized type
- [ ] Categorical charts cap to a legible mark count (top-N + aggregated remainder / re-typed / scrollable); no sub-pixel unlabeled smear; rendered marks match the "top N" caption; each row shows its label + value (not tooltip-only)
- [ ] Chart type fits each data question (`knowledge/charts.csv`)
- [ ] Controls work; tooltip sits on the point with a crosshair + keyboard path
- [ ] `:focus-visible` everywhere; SVG charts have aria text equivalents; AA contrast
- [ ] Real document skeleton: `<main>` landmark, a visible `<h1>`, correct `<h2>`/`<h3>` panel nesting mirroring the reading order, and a skip-to-content link as the first focusable element
- [ ] `slop_check.py` clean of `important`
