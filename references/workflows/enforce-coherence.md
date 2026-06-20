# Workflow: Enforce Coherence (drift detection)

Check that the repo (or a set of changed files) hasn't drifted from `DESIGN.md` —
a "design lint". Use on demand, in review of changed files, or before a release.

## Steps

The primary tool is the **design linter** — it reports drift with file, line,
severity, and a suggested fix, and exits non-zero (so it works in CI / #9):

```bash
python3 scripts/lint_design.py /path/to/repo --contract design/design-tokens.json
# text report; or add --json for a CI/editor-consumable list
```

It reads the same surface as the scanner (stylesheets + Tailwind/JSX/theme.ts/
CSS-in-JS), compares colors perceptually (ΔE, so near-duplicates of a contract
color don't false-positive), and suggests the nearest token for each rogue value.

To enforce the project's **house rules** (DESIGN.md §9 — e.g. "no flyouts, only
modals"):

```bash
python3 scripts/check_rules.py /path/to/repo
# parses [forbid: … | prefer: …] directives and flags forbidden patterns in UI files
```

Both are bundled into the `atelier check` CI gate (`check.py`).

For a repo-wide summary (not per-line), or to script your own checks, use the
`check_drift` library directly:

```python
import sys; sys.path.insert(0, "scripts")  # the atelier scripts dir
from scan_repo import scan_directory, check_drift
report = scan_directory("/path/to/repo")
allowed = {"colors": ["#2563eb", "#ea580c", "#f8fafc"], "fonts": ["Sora", "Inter"]}
drift = check_drift(report, allowed)
#  -> {"off_palette_colors": ["#ff00ff"], "off_contract_fonts": ["Roboto"]}
```

For each finding, propose the fix the linter suggests: map the off-palette color
to the nearest token, or replace the rogue font with the contract's fonts. To
rewrite at scale, hand off to the token-migration codemod
(`scripts/migrate_to_tokens.py`).

## What counts as drift

- A color used in stylesheets that isn't in the contract palette (ignore
  one-off near-duplicates only if within a tight delta — start strict).
- A font family referenced that isn't the contract's display/body font.
- (Future) spacing values outside the contract scale.

Keep it advisory by default: report + propose, don't auto-rewrite unless asked.

## Token migration (hardcoded → var(--token)), zero pixels moved

When you DO rewrite at scale, run the codemod as a tight, provable loop and write a
report a reviewer can audit line-by-line. The codemod (`scripts/migrate_to_tokens.py`)
rewrites only EXACT, role-correct matches across **colors, spacing, radius and fonts**
and never touches a token *definition*, a `calc()`/`@media`/rgba value, a non-spacing
dimension, a JS data array, or an `/* atelier-ignore */` block.

```bash
# 1. DRY-RUN — read the proposed unified diff, confirm every edit before writing.
python3 scripts/migrate_to_tokens.py <repo>
# 2. BASELINE render at the breakpoints that matter (incl. any @media boundary).
node scripts/screenshot.mjs <repo>/index.html before_1440.png 1440 900 --full
node scripts/screenshot.mjs <repo>/index.html before_390.png  390  844 --full
# 3. APPLY.
python3 scripts/migrate_to_tokens.py <repo> --apply
# 4. RE-RENDER + diff — prove 0 pixels moved at EACH width (a desktop-only diff can
#    miss a regression that only shows past a media query).
node scripts/screenshot.mjs <repo>/index.html after_1440.png 1440 900 --full
node scripts/diff_screens.mjs <repo>/index.html   # or a pixel diff vs the baselines
```

The report that closes the loop should be exhaustively auditable — completeness and
clarity are scored on whether a reviewer can verify it without re-reading the repo:

- **Counts up front:** migrations by KIND (color / spacing / radius / font) and the
  total; note where one declaration yields several substitutions (`padding: 8px 16px`
  → two), so declaration-count vs substitution-count is unambiguous.
- **Mapping table grouped by kind:** `file:line · literal · → var(--token) · role`, and
  explicitly flag every ROLE TRAP (the same literal mapping to different tokens by role,
  e.g. `8px` gap → `--space-2` vs `8px` border-radius → `--radius-md`).
- **A complete "Left alone — with reason" table** that names EVERY non-migrated case,
  including the easy-to-miss ones: near-but-unequal hexes (snapping moves pixels),
  off-scale lengths, **unitless/`0` values** (no `--space-0`), element `width`/`height`
  and **grid track sizing** (dimensions, not spacing), hairline `1px`/`borderWidth:1`,
  `font-size`/`line-height`, `min-height`/`100vh`, rgba()/tints, `calc()` interiors,
  `@media` breakpoints, **Tailwind scale classes** (`p-4`) vs arbitrary values (`bg-[#…]`),
  bare-hex JS data arrays, `/* atelier-ignore */` vendor blocks, any `.html` outside the
  codemod's `.css`/JSX scope, and the token *definitions* (confirm 0 `var()` self-refs
  in the tokens file).
- **Render-regression proof:** the measured `pixels_changed` at each width (must be 0),
  plus a one-line note that the change is source-only and reversible (dry-run-first).
