# Capability: i18n & RTL

If the project ships more than one language — and especially an RTL one (Arabic,
Hebrew, Farsi, Urdu) — the design must be direction-agnostic. Most "RTL bugs" are
just physical-direction CSS that should have been logical.

**Use when:** the repo declares i18n/RTL (a locale list, `dir="rtl"`, an i18n lib)
or the user asks for multilingual/RTL support.

## Lint physical → logical

```bash
python3 scripts/check_rtl.py /path/to/repo      # only runs if RTL/i18n is declared
```
It flags `margin-left/right`, `padding-left/right`, `border-left/right`,
`text-align: left/right`, `float: left/right`, and `left:/right:` positioning, and
suggests the logical equivalent (`margin-inline-start`, `text-align: start`,
`inset-inline-start`, …). Use `--force` to lint an LTR repo proactively.

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

## Verify

Run the responsive sweep AND check both directions — set `dir="rtl"` and confirm
no overflow or clipped layout. Add the logical-property check to CI for RTL repos.
