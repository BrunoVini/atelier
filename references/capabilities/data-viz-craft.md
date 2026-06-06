# Capability: Data-viz & dashboard craft (integrity + encoding discipline)

`knowledge/charts.csv` tells you *which* chart fits a data question. This file is the
craft layer for **dashboards and any data visualization**: the difference between a
dashboard that an analyst trusts and one that quietly lies. Read it whenever you build a
dashboard, KPI row, chart, funnel, cohort, or data table. Pair it with the universal QA
gates (focus-visible, honest working controls, anti-slop) — those apply here too.

## 1. Data integrity — a dashboard that's internally inconsistent is worse than none

An analyst reads these numbers literally. Any silent gap reads as "there is no value there."

- **Show every step or none.** A funnel that labels three of four drop-offs implies the
  unlabeled stage had zero drop. Show the count + % drop on *every* stage, or show none.
- **Parts reconcile to the stated total.** Stacked-bar / donut / breakdown segments must
  sum to the headline number (e.g. segment counts add up to the "9.3k" center label).
  Compute them so they actually reconcile — don't eyeball widths.
- **Deltas match arithmetic.** "vs prev 44.5k" with a "+18%" badge must be true against the
  shown current value. Wrong-direction or wrong-magnitude deltas destroy trust instantly.
- **Chart geometry matches the data.** Bar widths / line endpoints / arc angles must
  reflect the real values, and the text/aria summary must match what's drawn.
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
- **Never encode by color alone.** Deltas carry a sign + arrow glyph (colorblind-safe), not
  just red/green. Series get labels/patterns, not only hue.

## 3. Numbers & density

- **Tabular numerals on every figure** (`font-feature-settings:"tnum"` / a mono) so columns
  align and values don't jitter when they update.
- **Dense but scannable:** a clear KPI row, one primary chart with real hierarchy, secondary
  panels that don't compete, a table with aligned right-set numerics. Show a prior-value
  reference on KPIs ("vs 44.5k", "2.2pp") — more informative than "vs prev period".
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

## Definition of done for a dashboard / data viz

- [ ] Every funnel stage shows its drop (or none do); parts sum to the stated total
- [ ] Deltas are arithmetically correct and carry sign+arrow, not color alone
- [ ] Each color has ONE consistent meaning; status colors aren't reused as categories
- [ ] Cohort/heatmap is a single-hue sequential scale with values + legend
- [ ] Tabular numerals everywhere; no triplicated magnitudes
- [ ] Chart type fits each data question (`knowledge/charts.csv`)
- [ ] Controls work; tooltip sits on the point with a crosshair + keyboard path
- [ ] `:focus-visible` everywhere; SVG charts have aria text equivalents; AA contrast
- [ ] `slop_check.py` clean of `important`
