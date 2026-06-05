# RED baseline — designmd-gate (WITHOUT the skill)

Run date: 2026-06-05. A general-purpose agent, no atelier skill, given the
scenario prompt and the fixture repo.

## What it did
- **Inspected** the existing `tailwind.config.js`, `theme.ts`, `styles.css` before
  designing (a capable model does this on its own).
- **Matched** the load-bearing tokens: used #0B3D2E / #C9A227 / #F7F5EF / #14110E
  and Fraunces + Newsreader. No Inter, no purple gradient.
- **Did NOT create or propose a `DESIGN.md`**, and produced **no exported tokens**.
- Introduced a couple of undeclared values (white card bg, alpha tints) on its own
  judgement.

## Verbatim rationalization
> "The repo already had a working design system spread across three files, so a
> new design-system doc would have been redundant invention."

## Reading
The baseline is better than the worst case (a good model inspects and matches),
but it leaves **no durable, enforceable contract** behind: no `DESIGN.md`, no
tokens, nothing to stop the *next* change (or a less careful contributor/model)
from drifting. The skill's value is making the contract + tokens **guaranteed**,
not dependent on the model's diligence — and catching the cases where the model
would have defaulted to slop.
