# Workflow: Design QA in CI

Make the contract enforceable on every change: run `atelier check` (drift lint +
contrast audit) as a merge gate, like tests.

```bash
python3 scripts/check.py .
# resolves the contract from design/design-tokens.json OR DESIGN.md automatically;
# exits non-zero on drift / contrast / house-rule failure; honors design/atelier.config.json
# (pass --contract <path> only to force a specific tokens file)
```

## Config (optional) — `design/atelier.config.json`

```json
{
  "check": { "max_drift": 0, "allow_contrast_fail": false },
  "perf_budget": { "font_weights_max": 5, "image_kb_max": 800 }
}
```

## GitHub Actions

Drop `templates/ci/github-actions.yml` into the target repo as
`.github/workflows/atelier.yml`. It runs `check.py` on push/PR (zero extra deps —
pure Python). Visual-regression (`diff_screens.mjs`) is opt-in because it needs a
headless browser; keep the always-on gate to lint + contrast.

## Azure DevOps

`templates/ci/azure-pipelines.yml` is the equivalent for Azure Pipelines.

## What runs

- **design-lint** — file+line drift vs the token contract (perceptual ΔE).
- **contrast-audit** — every text/surface token pairing vs WCAG AA-large.
- **house-rules** — violations of DESIGN.md §9 directives (e.g. a flyout where the
  project mandates modals), via `check_rules.py`.
- **overlap-risk** — static collision-risk lint (gating severities only).

These are dependency-light (stdlib Python), so the gate is fast and reliable.
Generate `design/design-tokens.json` (via `generate-design-md`) before enabling.

**Adopting on a legacy repo:** baseline existing drift with `check.py <repo> --update-baseline`,
then gate with `check.py <repo> --ratchet` — drift may only shrink (the baseline auto-tightens).

**Optional extra gates** (in the GitHub Actions template):
- **prose gate** — `prose_check.py README.md docs/**/*.md` fails on AI-tell vocabulary in
  the project's own copy.
- **render gate** — `qa.py <built-page> --hook` catches rendered collisions/overflow/illegible
  charts the static check can't see (needs a headless browser).
- **PR-scoped review** — `pr_review.py <repo> --base <ref>` annotates only the lines a PR changed.
