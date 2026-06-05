# GREEN — designmd-gate (WITH the skill)

Run date: 2026-06-05. A general-purpose agent told to read and follow
`atelier/SKILL.md`, given the same scenario prompt and fixture.

## What it did (all success criteria met)
1. Hit the **DESIGN.md gate first**; no `DESIGN.md` existed, so it offered + ran
   the empirical path.
2. Ran `scan_repo.py` → framework react, lib radix/shadcn, colors
   #0b3d2e/#c9a227/#14110e/#f7f5ef, fonts Fraunces/Newsreader.
3. Generated `DESIGN.md` + `design/tokens.css` + `tailwind-preset.js` +
   `design-tokens.json`, and wired the preset into the existing `tailwind.config.js`.
4. Landing page used the repo's exact tokens; **0** occurrences of Inter / Roboto /
   Arial / system-ui / purple / indigo / violet (grep-verified by the agent).
5. `search_kb --domain palettes` returned a *generic* fintech navy/green; the
   workflow's "empirical scan WINS over KB" rule made the agent **discard** it in
   favor of the repo's real palette. (KB typography independently confirmed the
   Fraunces+Newsreader direction.)
6. Started + stopped the live preview server.

## Quote
> "The skill's explicit 'Quick is exactly when design drifts' line is what kept me
> from skipping straight to HTML. The skill drove correct behavior here."

## Issues surfaced (fed into REFACTOR)
- `/design/tokens.css` link was not reachable in project-dir sessions, and the
  frame hardcoded a non-contract aesthetic → both fixed (see `../refactor/`).
- Background server can die in sandboxed hosts even when the launcher returns 0 →
  preview.md needs a "validate the artifact on disk if the port is unreachable"
  fallback.
