# Knowledge base — source & license

The structured design knowledge in this folder (palettes, font pairings, product
types, UX guidelines, chart recommendations, named styles, stack guidance, cold-start
reasoning, font substitutes, and brand exemplars) is **original content authored for
atelier**. It is a curated distillation of established, publicly-known design and
accessibility principles — color theory, type pairing, WCAG contrast, data-viz best
practice, and framework idioms — expressed in atelier's own selection and wording.

- **License:** part of atelier; covered by the repository `LICENSE` (Apache-2.0).
- **Facts vs. expression:** individual data points (e.g. "fintech → navy/trust",
  "4.5:1 text contrast", a font family name) are facts and carry no copyright. The
  selection, arrangement, and notes are atelier's own.

## Files

| File | Contents |
|---|---|
| `palettes.csv` | product-type → role'd color palette (WCAG-conscious) |
| `typography.csv` | font pairings (display + body) by mood and use case |
| `products.csv` | product-type → style + landing pattern + considerations |
| `ux-guidelines.csv` | do/don't UX rules with code examples and severity |
| `charts.csv` | data type → recommended chart, library, a11y tip |
| `styles.csv` | named visual styles, where to use/avoid, effects, a11y/perf |
| `stack-guidance.csv` | framework-idiomatic do/don't (react/next/vue/svelte/…) |
| `reasoning.csv` | greenfield cold-start aid: pattern + style + mood per category |
| `font-substitutes.csv` | proprietary face → closest open-source analogue + tracking |
| `brand-exemplars.csv` | real-brand design languages as cold-start *seeds* only |
| `reflex-reject.csv` | product-category → the *second-order* reflex choices (the "safe" post-correction cliché) to push past |
| `defensive-css.csv` | the 25 Defensive CSS techniques (tip → problem, defensive pattern, whether statically checkable, severity) |

## Attribution — reflex-reject

The `reflex-reject.csv` entry encodes the *second-order anti-slop* idea: after a
designer learns to avoid the obvious AI tells, the next most predictable "safe"
choice is itself a category cliché. That framing — and the term *reflex-reject* —
is informed by **impeccable** (Apache-2.0, `pbakaus/impeccable`). The concept is a
fact/idea, not protected expression; the category rows, hue anchors, and notes here
are atelier's own observation and wording, cross-referenced with `products.csv`.

## Attribution — defensive-css

The `defensive-css.csv` catalog and `../capabilities/defensive-css.md` guide encode the
25 **Defensive CSS** techniques by **Ahmad Shadeed** (defensivecss.dev, `defensive-css/tip/<slug>/`).
Defensive CSS — writing styles that survive long content, varying viewports, the user's
scrollbar, missing images, and touch input — is Shadeed's framing and term. The individual
techniques (e.g. `img { max-width: 100% }`, `font-size: 16px` on inputs to stop iOS zoom,
`overscroll-behavior: contain`) are publicly-known CSS facts and carry no copyright; atelier's
selection into `static`/`rendered`/`judgment` classes, the severity hints, the per-tip notes,
and the three ported deterministic checks (`input-zoom-ios`, `img-no-max-width`,
`bg-no-no-repeat` in `scripts/slop_ported.py`) are atelier's own observation and wording.
The `slug` column maps each row back to its `defensivecss.dev/tip/<slug>/` source page.

## How it's used

`scripts/search_kb.py` runs a dependency-free BM25 search over these CSVs. The
knowledge base only **fills gaps** when the empirical scan of a repo is sparse, or
seeds a direction on greenfield work — the empirical scan always wins when both
exist, and output still terminates in atelier's `DESIGN.md`.

To extend: add rows in the same schema (keep the `keywords` column), or register a
new domain in `_DOMAIN_FILE` in `scripts/search_kb.py`.
