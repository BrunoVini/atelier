# Workflow: Enforce Coherence (drift detection)

Check that the repo (or a set of changed files) hasn't drifted from `DESIGN.md` —
a "design lint". Use on demand, in review of changed files, or before a release.

## Steps

1. Load the contract's allowed colors and fonts (from `design/design-tokens.json`
   or by parsing `DESIGN.md`).
2. Scan the target (whole repo or just changed files):

```bash
python3 scripts/scan_repo.py /path/to/repo > /tmp/scan.json
# then compare scan.json colors/fonts against the contract
```

3. Report drift with `check_drift(report, allowed)` from `scan_repo.py`:

```python
import sys; sys.path.insert(0, "scripts")  # the atelier scripts dir
from scan_repo import scan_directory, check_drift
report = scan_directory("/path/to/repo")
allowed = {"colors": ["#2563eb", "#ea580c", "#f8fafc"], "fonts": ["Sora", "Inter"]}
drift = check_drift(report, allowed)
#  -> {"off_palette_colors": ["#ff00ff"], "off_contract_fonts": ["Roboto"]}
```

4. For each drift item, propose the fix: map the off-palette color to the nearest
   token, or replace the rogue font with the contract's display/body font.

## What counts as drift

- A color used in stylesheets that isn't in the contract palette (ignore
  one-off near-duplicates only if within a tight delta — start strict).
- A font family referenced that isn't the contract's display/body font.
- (Future) spacing values outside the contract scale.

Keep it advisory by default: report + propose, don't auto-rewrite unless asked.
