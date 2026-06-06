# Capability: Design Review (screenshot + score)

Critique a design — yours or the user's — by actually *looking at it* (rendered
screenshots) and scoring it against the contract and craft standards. Fuses
huashu's screenshot-based expert review with the rigor of adversarial code review.

**Use when:** the user asks "is this good?", "review/score this layout", "does
this look right", or when you doubt your own output and want to QA before
delivery.

## 0. Pick the evaluation mode (ask the user when it's not obvious)

Two modes — confirm which the user wants before spending effort:

- **Visual review (recommended for layout/look).** Screenshots at breakpoints,
  then you *look*. Needs a renderable target. **First check if the app is already
  running** — `scripts/detect_server.sh` (or the URL the user gave) — and reuse
  that URL; never start a second server. If nothing is up and atelier can't run the
  app (backend/env/integrations), **ask the user to run it and paste the URL** (or
  just confirm it's up on a reachable port). If they can't either, review the
  component in isolation with mock data (`preview.md` → "When the app can't run
  standalone").
- **Non-visual review (faster, more limited).** Static, from the source + the
  contract — `lint_design` / `audit_contrast` / `slop_check` / structure. No
  rendering, so it CANNOT judge actual rendered hierarchy, spacing, or overflow;
  say so. Good when the user only wants a code/contract check, or rendering is
  impossible.

A "review this screen" usually means visual; "check this for issues" may not. When
in doubt, ask: *"Visual review (I'll screenshot it — need it running or a URL) or
a non-visual code/contract review?"*

## 1. Capture — look before you judge (visual mode)

Render the design to PNGs at real breakpoints and **view them** (don't review
from source alone — you miss spacing, hierarchy, and overflow that only show
visually):

```bash
node scripts/screenshot.mjs <page.html|url> /tmp/review-desktop.png 1440 900 --full
node scripts/screenshot.mjs <page.html|url> /tmp/review-mobile.png 390 844 --full
```

Then Read both images. If no headless browser is installed, the script says so;
fall back to reviewing the served preview (`preview.md`) or the source. **If the
app can't render standalone (needs a backend/env)**, don't screenshot a broken
page — review the component in isolation with mock data, or use a URL the user
provides (see preview.md → "When the app can't run standalone").

## 2. Score — five dimensions, 0–10 each

| # | Dimension | What you're judging |
|---|-----------|--------------------|
| 1 | Contract fit | Honors `DESIGN.md` (palette, type, spacing, motion)? Off-contract = capped low. |
| 2 | Visual hierarchy | Does the eye land where it should? Type scale, contrast, focal point. |
| 3 | Detail execution | Alignment, optical spacing, consistent radii/shadows, states, edge cases. |
| 4 | Functionality & a11y | Works / buildable / accessible (contrast, targets, reduced motion)? |
| 5 | Innovation | A memorable, non-generic idea — or AI slop? |

Compute a **total /50** and an overall verdict. The anti-slop check is mandatory —
and now backed by a script, not just judgement:

```bash
python3 scripts/slop_check.py <page.html> --contract <repo>   # visual + copy + structural tells
python3 scripts/slop_check.py <page.html> --profile codex     # add a generator's signature tells
```
It checks three layers of the current AI tell-set: **visual** (generic fonts, the
purple gradient, glassmorphism, card+left-border, too many fonts, and the 2026
**warm-neutral “paper/cream” default** — the monoculture the purple gradient used to
be); **copy** (em-dash cadence, marketing clichés, vague CTAs, all-caps body, scroll
cues, fake locale strips, version stamps); **structural** (numbered eyebrows, eyebrow
over-use, faux window chrome, decorative-dot filler, and intra-page **layout
monotony** — every section the same shape). `--profile codex|gemini` adds tells
specific to a given generator.

Contract-sanctioned choices are **not** flagged — fonts the DESIGN.md declares, and a
warm-paper ground when the *contract itself* declares it (pass `--contract`; a paper/
ink brand is law for that repo, not slop). Treat an `important` finding as a fail of
dimension 5 (Innovation). Still cross-check `design-philosophy.md` §3 by eye.

For dimensions 1 and 4, back the score with **measured evidence**, not vibes:

```bash
python3 scripts/audit_contrast.py design/design-tokens.json   # WCAG per pairing
python3 scripts/lint_design.py . --contract design/design-tokens.json  # drift
python3 scripts/check_rules.py .                              # house-rule violations
```

Cite the contrast ratios, any drift findings, and any **house-rule** violations
(DESIGN.md §9 — e.g. a flyout where the project mandates modals) in the report.
Honoring the project's component/data/interaction standards (§7–9) is part of
dimension 1 (contract fit).

## 3. Report — scorecard + actionable fixes

```
Verdict: <one line> — Total 38/50
  Contract fit 9 · Hierarchy 7 · Detail 6 · Functionality 8 · Innovation 8
Keep:  <what genuinely works, specific>
Fix:   ⚠️ critical  / ⚡ important / 💡 polish   (each: what + where + how)
Quick wins: <top 3 doable in ~5 min>
```

## 3b. Regression & weight checks (when editing an existing page)

```bash
node scripts/responsive_check.mjs <page.html> # sweep widths; flags overflow AND text collision
node scripts/diff_screens.mjs <page.html>     # vs saved baseline; proves "nothing else moved"
python3 scripts/perf_budget.py <page.html>    # font/image/CSS/motion weight vs budget
```
Cite "diff: hero changed, rest unchanged" and any over-budget metric in the report.
First run with `--baseline` to record the reference.

## 3c. Overlaps & collisions — diagnose the cause, don't nudge (and re-verify)

The sweep reports **element collisions** (text sitting on top of text) as well as
overflow. When you find one — or spot one by eye — do not "fix" it with a blind
nudge (a margin bump, a `top` tweak, a `z-index` bump). That hides it at one width
and lets it re-collide at another. Work the **root cause** instead:

| Cause | The real fix (not a nudge) |
|---|---|
| `position: absolute` child with no space reserved | Give the flow a real box (height/min-height/grid area), or make the layout flow instead of overlapping. |
| Missing `position: relative` on the parent | Anchor the coordinate system (animation-pitfalls §1) so the child positions against the box you mean. |
| Negative margin / fixed px width that doesn't reflow | Replace with `clamp()` / intrinsic layout (`responsive.md`) so the mid-range interpolates instead of stacking. |
| Two layers fighting in one cell | Decide the stacking explicitly (grid `place-items`, or separate rows) — overlap should be intentional, never accidental. |
| Label placed over same-colored / busy art | Move it onto a contrasting surface or outside the shape; never rely on it "usually" clearing. |

Then **re-verify the fix visually** — re-run `responsive_check.mjs` across the
whole sweep and re-screenshot the affected breakpoint. A fix you didn't re-render
is a guess. The collision is only resolved when the sweep is clean at *every*
width and the screenshot confirms it — not when one viewport happens to look right.

## 4. Adversarial pass (high-stakes)

For important work, run the critique as a skeptic trying to REFUTE that the design
is good, or escalate to the 5-agent **council** (`references/capabilities/council.md`)
when the call is hard or the user asks to weigh options. Default to "not done yet"
if a critical issue is unresolved. Critique the design, never the designer.
