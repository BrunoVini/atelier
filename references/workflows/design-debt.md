# Workflow: Design-Debt Report

Turn the scattered checks into one number a team can track and a lead can put on a
roadmap: a 0-100 coherence score with hotspots and a trend. **Always MEASURE the
repo — never eyeball the score.** Two modes, picked automatically:

## Contract mode — the repo has a formal DESIGN.md / design-tokens.json

```bash
python3 scripts/design_report.py . --contract design/design-tokens.json --stamp 2026-06-05
# writes DESIGN-DEBT.md (+ appends design/debt-history.jsonl for the trend)
```

Composes, scoring everything AGAINST the declared contract:

- **Drift** findings (from `lint_design.py`) — -2 each (cap -40).
- **Contrast** AA-large fails (from `audit_contrast.py`) — -5 each.
- **Duplicated components** (from `census.py`) — -3 each.
- **Off-palette colors** (palette entropy vs the locked set) — -1 each (cap -15).

## Measured / contract-free mode — a drifted repo with NO formal contract

This is the COMMON case for a debt audit: tokens live in a `:root` block the
components ignore, or there is no token file at all. The contract path bails here;
use measured mode (it runs automatically when no contract is found, or force it):

```bash
python3 scripts/design_report.py /path/to/repo --measured
# scores the repo from its OWN measured sprawl, writes DESIGN-DEBT.md
```

The score is derived from the repo's measured sprawl (each penalty capped so no
single axis sinks it), then small coherence CREDITS are added back:

- **palette** — raw distinct colors vs their perceptual ΔE clusters (the entropy
  between them IS the sprawl) + cluster count over a ~12 budget (cap -22).
- **fonts** — competing font families beyond ~2 (-5 each, cap -10).
- **spacing** — distinct values over a ~7-step scale + off-grid values not on the
  8px grid (cap -16).
- **radius** — distinct radii over ~4 (-3 each, cap -8).
- **duplicates** — duplicated component implementations (-6 each, cap -8).
- **off-token** — raw colors that are near-dups (≤12 ΔE) of a declared `:root`
  token but hardcoded anyway: the token system exists and is being ignored (cap -12).
- **+credits** — +6 if a real declared token system exists, +0–8 for how widely
  `var(--token)` is actually adopted. These keep a drifted-but-recoverable repo in a
  defensible low-mid band instead of flooring at single digits (a 4/100 for a repo
  that has a real token system + a clean area is itself a scoring-sanity miss).

Hotspots are ranked by per-file impact (colors + off-token hardcodes + competing
fonts + off-grid spacing, credited for `var()` usage) so the worst file is first.

Both modes print Score = 100 − penalties (+ credits, measured mode); grade A–F; the
full derivation table is in the report, so it's defensible, not a black box.

## Use it

- Track the score over time (`debt-history.jsonl`) — "coherence 62 → 81 after the
  token migration" is a real, reportable outcome.
- The hotspots are the to-do list: each maps to a fix (token migration, a
  contrast tweak, a component consolidation).
- Run it after big changes, or on a schedule, to catch drift before it compounds.
