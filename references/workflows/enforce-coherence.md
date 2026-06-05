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
