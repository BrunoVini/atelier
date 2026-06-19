# Capability: Type systems & specimen pages (pairing · scale · coverage · fallback)

`knowledge/typography.csv` gives proven display+body pairings; `knowledge/fonts-catalog.csv`
tells you which families carry which **subsets** (latin-ext / Cyrillic / Greek / Vietnamese /
CJK / Arabic) and which expose **variable axes**; `knowledge/font-substitutes.csv` maps a
proprietary face to an open analogue. Read this file whenever you build a **type system**, a
**type-specimen / type-system spec page**, a brand DESIGN.md type section, or any artifact where
the typography *is* the deliverable (not just dressing on a layout). Pair it with the typographic
laws in `design-laws.md` (modular-scale ratio, cap-3-families, measure, leading, tracking floors)
and the pre-scan `scripts/typography_preflight.py`.

A type system is judged on five things, and each must be **demonstrated on the rendered page**, not
asserted in prose: the **pairing**, the **scale**, **language coverage**, **fallback**, and the
**rationale** that ties every choice to the brand.

## 1. The pairing — cohere by construction, contrast by role

- **Pick a trio that shares a skeleton or contrasts on purpose — never a sample-zoo.** The
  strongest, most defensible answer to "display + body + mono" is usually **one engineered
  superfamily** (e.g. the IBM Plex family: Plex Sans Condensed / Plex Sans / Plex Mono; or the
  Adobe Source family: Source Serif 4 / Source Sans 3 / Source Code Pro). One design program means
  the three already share upm, x-height, cap-height, and terminal cuts — they *cannot* clash, and
  the contrast lives where it should: in **role** (display has presence, body recedes, mono is true
  fixed-pitch), not in mismatched DNA. State the shared metrics as the coherence argument.
- **An all-one-family trio must still MANUFACTURE display presence — don't let the display read as
  just bigger body.** A superfamily's great strength (coherence) is also its risk: if display, body,
  and mono are all the same upright sans at the same weight, the only contrast is size, and a judge
  reads the display as "a larger paragraph," not a voice. Engineer real separation between roles
  using the axes the one family gives you: a **distinct optical/condensed/expanded cut** for display
  (e.g. a condensed or display-optical face vs the text cut), a **decisive weight jump** (e.g. body
  400 → display 700/800, never 600), **tracking contrast** (tight display vs neutral body), and a
  **large size jump** at the top of the scale. The display should command the specimen on its own
  line; if it doesn't, the pairing reads safe even when the family choice is right. (A cross-family
  contrast serif gets this presence for free — match it from within your family rather than concede
  it.)
- **A deliberate cross-family pairing is fine when the contrast is the point** (a contrast serif
  display over a neutral grotesque body), but then you must *justify the relationship* — what they
  share (proportion, era, mood) and what they deliberately oppose.
- **Match the pairing to the brand register, not to fashion.** A precise/instrument brand wants an
  all-grotesque, condensed-display, machined read; an editorial/literary brand wants a contrast
  serif; a warm/human brand wants humanist terminals. A high-contrast Didone reads
  *fashion-editorial* — wrong for most product/instrument/business brands (a recurring miscue).
- **Never** the generic-default triple (Inter + Inter + a generic mono) — that's the monoculture
  the slop gate already flags; it reads as *no decision made*.
- **The mono must earn its place.** In a money / data / coordinates / code product, show the mono
  doing real work (tabular figures, reference codes, bearings) — don't include it for completeness.

## 2. The scale — a true modular scale, rendered

- **State the generating ratio and build off it.** A real scale is `size = base × ratio^step` with
  a stated ratio (≈1.2 minor third for tight/dense systems → 1.25 major third → 1.333 for airy
  editorial). The rendered px must actually hold that ratio per step (verify on the render to
  rounding) — an arbitrary hand-picked size list is *not* a scale.
- **Document each named step in a tabular-numeral table:** size (px + rem), the ratio, line-height,
  weight, and tracking — AND show each step **applied to real text at that size**, so rhythm and
  size relationships are visible, not just tabulated.
- **Pair line-height to size, not one global value:** tight at display (~1.0–1.1), open at body
  (1.5–1.6), snug on small UI labels (~1.2–1.3). Weight may rise as size falls for small-label
  legibility.
- **Honest exceptions are a strength, not a flaw.** If the smallest step would fall below a
  legibility floor (e.g. a pure-ratio caption computing to <10px), lift it to the floor and *label
  the exception* in the table — a documented deviation reads as engineering judgment, a silent one
  reads as a broken scale.
- **Set a measure.** Body prose at 65–75ch; show the comfortable line length as part of the system.

## 3. Language coverage — demonstrated and HONEST (never faked, never silently dropped)

Coverage is judged on **breadth, correctness, AND honesty on the render**:

- **Typeset the real strings as live selectable text** at a legible size — Latin + extended
  diacritics (Polish/Czech/Turkish/Vietnamese: `ą ć ę ł ń ó ś ż`, `č ř š ž`, `ı ğ ş`, `ạ ệ ơ ư`),
  plus any non-Latin script you claim (Greek, Cyrillic, …), plus the symbol set the product needs
  (degree °, prime ′ ″, true minus −, currencies incl. unusual ones, № §, fractions, em-dash).
- **Verify on the RENDER that every claimed glyph is a real letter, not tofu (□ / ? / .notdef).**
  Pick faces whose embedded subsets *genuinely carry* the scripts (the catalog lists subsets) — a
  blind judge will look straight at the Greek/Cyrillic line for boxes. A single dropped accent or
  tofu box is a visible, scored failure.
- **HONEST DEGRADATION IS SHOWN IN PLACE — never silently omitted (lesson, decisive).** When a
  glyph is genuinely out of every embedded subset, **leave the codepoint in the rendered string and
  show its real fall-through in situ** — the actual `.notdef` box (or a clearly marked slot) right
  where it occurs — with a one-line note naming the codepoint and the face that would cover it
  (e.g. "U+1260 Ethiopic → would need Noto Sans Ethiopic"). **Do NOT delete the character from the
  string and explain it only in prose.** Showing the uncovered glyph *on the render* is exactly the
  "surface coverage honestly" the brief rewards; quietly dropping it — even with an accurate prose
  footnote — reads as hiding the gap and scores below a visibly-shown box. Surgically backfilling a
  missing codepoint with a unicode-range-scoped companion subset is good engineering, but the
  *uncovered* cases must still be shown, not omitted.
- **Prove tabular vs proportional figures.** Show a small column of figures aligning under tabular
  numerals (`font-variant-numeric: tabular-nums`) — essential for any data/money UI.

## 4. Fallback — show the WORST case AND the engineered fix (both, side by side)

This is the proving ground for an offline, self-contained type system. The bar is *honest +
engineered*, and the demonstration must let the reader **see** both halves:

- **Embed the custom faces** as base64 `woff2` `@font-face` (`src: url("data:font/woff2;base64,…")`)
  of openly-licensed faces (OFL/Apache) — so the page boots fully offline with the real type and
  **never** a runtime font `<link>`/CDN (gate with `scripts/check_offline.py` → zero refs).
- **Document a complete fallback stack per role:** embedded face → a metric-compatible web-safe face
  → the generic family. Name the real per-face metric shift; never claim "metric-identical" if it
  isn't.
- **SHOW BOTH DEGRADATION STATES, not just one (lesson).** A reader must see *how bad it gets* AND
  *how the engineering tames it*. So render, side by side and labeled, against the embedded face:
  1. the **raw, untuned system fallback** (`local('Arial')` / `local('Georgia')` / `local('Consolas')`
     with NO overrides) — the true worst case, so the reflow/shift is visible; and
  2. the **metric-tuned fallback** — the same system face wrapped in an `@font-face` carrying real
     `size-adjust` / `ascent-override` / `descent-override` / `line-gap-override` derived from the
     embedded face's metrics — proving the shift is engineered down.
  Showing only the tuned column *understates* the shift (reads as hiding it); showing only the raw
  column proves honesty but not engineering. The pairing of the two is what earns the dimension.
- **The metric overrides must be APPLIED, not merely printed in a code block.** A documented
  `size-adjust: 99%` that the shipped `@font-face` doesn't actually carry is *asserted, not
  engineered* — a blind typographer who reads the CSS will catch and penalize the gap between the
  prose and the rule. Ship the overrides on a real `@font-face` and force it into the comparison
  column so the rendered fallback genuinely reflects the documented tuning.
- **Handle the load transition:** `font-display: swap` (FOUT — text visible immediately in the
  fallback, no invisible FOIT) is the safe default for body; pair it with a metric-tuned fallback so
  the swap doesn't reflow. State the FOUT/FOIT decision explicitly.

## 5. Rationale — brand-tied, decision-grade, matches the artifact

- **Every choice traces to the brand**, in one tight line each: why these three faces, why this
  pairing relationship, why this ratio, why these fallbacks — specific to *this* brand's voice and
  to type engineering, not "modern and clean" filler.
- **The rationale must not oversell the artifact.** Do not claim engineering the CSS doesn't do
  (e.g. metric tuning that isn't applied). A reasoning block that describes the *real* decisions —
  including honest residual shift — is worth more than polished claims the file can't back up.

## Build & verify checklist
1. Choose the trio from `knowledge/typography.csv` + `fonts-catalog.csv`; confirm the subsets cover
   every script you'll typeset. Search: `python3 scripts/search_kb.py "<register>" --domain typography`.
2. Build the scale off one stated ratio; tabulate + apply every named step.
3. Embed faces as base64 woff2; typeset the real coverage strings; **leave uncovered glyphs in place
   and show their box + note**.
4. Build per-role fallback stacks; ship BOTH a raw-`local()` column and a metric-tuned-`@font-face`
   column, forced into the comparison and labeled.
5. `python3 scripts/typography_preflight.py <file>` (typographic facts), `python3 scripts/check_offline.py <file>`
   (zero remote refs), `python3 scripts/qa.py <file> --hook` (clean), then **read the render**: no
   tofu in any script, the fallback columns show the genuine faces, holds at 1440 + 390.
