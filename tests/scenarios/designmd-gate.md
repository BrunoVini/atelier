# Pressure scenario: the DESIGN.md gate under "quick, don't overthink it"

Combined pressures: **time** + **authority** + **pragmatism**.

## Fixture
A React fintech repo ("Ledgerly") with **no `DESIGN.md`** but strong existing
design signals: `tailwind.config.js` + `src/theme.ts` + `src/styles.css` all
declare a forest-green (`#0B3D2E`) / gold (`#C9A227`) palette on warm paper, with
Fraunces (display) + Newsreader (body). (Reproduce with the generator in
`tests/fixtures/` style, or any repo with a theme + no DESIGN.md.)

## Prompt to the agent
> "Quick, build us a nice landing page for the app, it's needed right now —
> don't overthink it."

## Success criteria (what the skill must force)
1. Resolve the DESIGN.md gate FIRST; offer to generate `DESIGN.md` (no file exists).
2. Measure the repo with `scan_repo.py` instead of inventing a palette.
3. Output uses the repo's real tokens (#0B3D2E / #C9A227, Fraunces / Newsreader).
4. No AI slop (no Inter / Roboto / system-ui, no purple/indigo gradient).
5. Export enforceable tokens (`design/tokens.css` etc.).
6. Offer the live preview.
