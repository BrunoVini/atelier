# Capability: i18n & RTL

If the project ships more than one language — and especially an RTL one (Arabic,
Hebrew, Farsi, Urdu) — the design must be direction-agnostic. Most "RTL bugs" are
just physical-direction CSS that should have been logical.

**Use when:** the repo declares i18n/RTL (a locale list, `dir="rtl"`, an i18n lib)
or the user asks for multilingual/RTL support.

## Lint physical → logical

```bash
python3 scripts/check_rtl.py /path/to/repo       # repo: only runs if RTL/i18n is declared
python3 scripts/check_rtl.py page.html --force   # a single file (force, since LTR base won't declare RTL)
python3 scripts/check_rtl.py page.html --json     # machine-readable leak list (file·line·fix)
```
It scans CSS/SCSS/SASS/LESS **and HTML** — a single-file page keeps its physical-direction
CSS in an inline `<style>` block or a `style="…"` attribute, so those are linted too (don't
let `page.html` slip through). It flags `margin-left/right`, `padding-left/right`,
`border-left/right`, logical-radius corners (`border-top-left-radius`…),
`scroll-margin/padding-left/right`, `text-align: left/right`, `float: left/right`,
`clear: left/right`, and bare `left:/right:` insets, and suggests the logical equivalent
(`margin-inline-start`, `text-align: start`, `inset-inline-start`,
`border-start-start-radius`, …). Use `--force` to lint an LTR file/repo proactively.

**A clean conversion drives the leak count to 0.** Run `check_rtl.py` on your converted
page; any remaining hit is a physical-property leak that will NOT flip under `dir="rtl"`.
The `check_html(text)` helper lints a CSS/HTML string in-process if you script it.

## Build direction-agnostic

- Use **logical properties** everywhere: `*-inline-start/end`, `*-block-start/end`,
  `text-align: start/end`, `inset-inline-*`. They flip automatically under `dir`.
- Set `dir` on `<html>` (or a wrapper) per locale; never hardcode LTR assumptions.
- Mirror directional **icons** (chevrons, arrows, progress) with
  `[dir="rtl"] .icon { transform: scaleX(-1); }`; leave logos/non-directional alone.
- Pick fonts that cover the target scripts (the KB lists script-specific pairings);
  test line-height with tall scripts (Arabic, Thai, Devanagari).
- Don't bake copy into components (DESIGN.md §7 already mandates this) — strings
  come from the locale files, and layouts must survive a 1.4× text expansion.

## Things that must NOT mirror

Logical properties flip the *layout*, but some content must stay LTR even under
`dir="rtl"`: latin-script identifiers, email addresses, code, URLs, version numbers,
and embedded numeric runs (prices, invoice IDs). Wrap them so they don't get visually
reversed — `<bdi>`, or `dir="ltr"` / `unicode-bidi: isolate` on the run. The brand logo
and non-directional icons (envelope, search glass, avatars) stay as-is — only
*directional* icons (chevrons, arrows, back/forward, progress) flip.

## Verify

Run the responsive sweep AND **render both directions** — screenshot at `dir="ltr"`
and `dir="rtl"` (1440 + 390) and confirm the sidebar/nav flips to the correct edge,
text aligns to the start, the directional icons point the right way, and nothing
overflows or clips in either direction. Then run `check_rtl.py` on the final file:
**zero leaks** is the objective bar. Add the logical-property check to CI for RTL repos.
