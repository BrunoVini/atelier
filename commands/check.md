---
description: Run the deterministic design gate (drift + contrast + house-rules + overlap)
argument-hint: [repo-path]
allowed-tools: Read, Bash(python3:*)
---

Run the deterministic design gate over `$ARGUMENTS` as a CI or local merge gate: `${CLAUDE_PLUGIN_ROOT}/scripts/check.py "$ARGUMENTS"`. It lints drift against the contract (off-palette colors via perceptual ΔE, off-contract fonts, off-scale spacing & non-token radius, elevation-rule breaks), audits contrast, enforces the project's house rules, flags overlap, and runs a static a11y scan — see `references/workflows/ci.md`. Summarize the result as a single PASS/FAIL with the offending findings; a FAIL blocks the merge until fixed.

When the ask is to **report drift to a human** (not just gate), also run `${CLAUDE_PLUGIN_ROOT}/scripts/lint_design.py "$ARGUMENTS" --json` and present the findings per the "Reporting a drift audit to a human" guidance in `references/workflows/ci.md`: a one-line verdict + gate summary, findings grouped by severity (identity drift first) with file:line + the exact value + the exact token fix, a **"Verified clean — NOT drift"** section for near-token / token-defining values (state the ΔE reason), and no hand-added findings the scanner didn't flag. Precise beats noisy.
