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

A repo-ROOT **`.atelier.json`** is also read and **merged OVER**
`design/atelier.config.json` (the root file wins per key; deep-merged, so you can
override one threshold without restating the section). It adds a `checks` object
(alias `rules`) that toggles individual gate **steps** on/off — `design-lint`,
`contrast-audit`, `house-rules`, `overlap-risk` (default `true`). A disabled step
is **skipped** (not computed, not gating) and prints `[SKIP] <step> (disabled in
config)`. An explicit CLI flag (e.g. `--max-drift N`) still overrides config.

```jsonc
// .atelier.json (repo root)
{
  "check": { "max_drift": 0, "max_overlap_risk": 0, "allow_contrast_fail": false },
  "checks": { "overlap-risk": false }
}
```

## Inline suppression

ESLint-style directives, inside any comment (`//`, `/* */`, `<!-- -->`, `#`),
optionally followed by space-separated rule kinds (no kinds = all kinds):

```css
a { color: #ff00ff } /* atelier-disable-line color */
/* atelier-disable-next-line font */
.brand { font-family: "Comic Sans" }
/* atelier-disable depth */        /* whole-file, for depth findings */
```

- **`design-lint`** findings have real line numbers, so `-line` / `-next-line`
  suppress per line, matched by the finding's `kind` (`color`, `font`, `depth`).
- **slop-check** rules run over the whole document (no line numbers), so all
  three forms degrade to **file-scoped by-kind** suppression there.

No directive present → output is unchanged.

## `--quiet`

`python3 scripts/check.py . --quiet` hides the verbose per-finding detail lines
but keeps the per-step `[PASS|FAIL|SKIP]` summary and the final
`atelier check: PASS|FAIL`. Exit codes are unchanged; it composes with `--sarif`
(quiet only affects human stdout, never the SARIF file).

## `--url` — static slop battery on a remote page

`python3 scripts/check.py --url https://example.com` fetches a remote page
(stdlib `urllib`, http/https only, 10s timeout, ~5 MB cap) and runs the
contract-free anti-slop battery on it — the standalone-detector use case. No token
contract is involved (so no contrast/drift). Exits 1 if any finding is
`important`, else 0; honors `--quiet` and `--json`. Other schemes or a network
error exit 2 with a clean `::error::` message (no traceback).

## GitHub Actions

Drop `templates/ci/github-actions.yml` into the target repo as
`.github/workflows/atelier.yml`. It runs `check.py` on push/PR (zero extra deps —
pure Python). Visual-regression (`diff_screens.mjs`) is opt-in because it needs a
headless browser; keep the always-on gate to lint + contrast.

## SARIF / code scanning

Pass `--sarif <path>` to emit a [SARIF 2.1.0](https://sarifweb.azurewebsites.net/)
report alongside the human output, so findings land in GitHub's **Security ›
Code scanning** tab (and any SARIF consumer):

```bash
python3 scripts/check.py . --sarif atelier.sarif   # file (written on pass OR fail)
python3 scripts/check.py . --sarif -               # SARIF JSON to stdout (human lines suppressed)
```

The SARIF is written **regardless of pass/fail**, then the process still exits
0/1 — so findings surface in code-scanning while the gate keeps blocking merges.
RuleId → level: drift → `atelier/design-lint` (warning), contrast →
`atelier/contrast-audit` (error), house rules → `atelier/house-rule` (error),
overlap risk → `atelier/overlap-risk` (critical→error / important→warning /
polish→note; polish is reported even though it doesn't gate).

### Reusable action

Consumers can skip the copy-in workflow and use the composite action directly
(it runs the gate, writes SARIF, uploads to code-scanning, and fails on a gate
failure). Needs `security-events: write`:

```yaml
permissions: { contents: read, security-events: write }
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with: { python-version: "3.12" }
  - uses: BrunoVini/atelier@v0.1.0
    with:
      path: .
      # contract: design/design-tokens.json   # optional
      # max-drift: 0                            # optional
      # sarif-file: atelier.sarif               # optional
      # upload: 'true'                          # optional
```

The copy-in `templates/ci/github-actions.yml` also ships an optional
`design-check-sarif` job that does the same with inline steps.

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
