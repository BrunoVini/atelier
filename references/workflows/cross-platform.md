# Workflow: Cross-platform Coherence

Keep one design language across every surface — web, mobile, slides, marketing —
from a single `DESIGN.md`. The token files are the shared source; each platform
consumes them in its own dialect.

## Token mapping by surface

| Surface | Consumes | How |
|---|---|---|
| Web (CSS/vanilla) | `design/tokens.css` | `@import` and use `var(--color-primary)` |
| Web (Tailwind) | `design/tailwind-preset.js` | `presets: [require('./design/tailwind-preset')]` |
| Web (any build) | `design/design-tokens.json` | Style Dictionary / your token pipeline |
| iOS (SwiftUI) | `design-tokens.json` | generate a `Color`/`Font` extension from the JSON |
| React Native | `design-tokens.json` | generate a JS theme object |
| Flutter | `design-tokens.json` | generate a `ThemeData` / token Dart file |
| Slides | `tokens.css` | the deck engine reads the same vars |
| Marketing / preview | `tokens.css` | preview server links it (`capabilities/preview.md`) |

## Rule

`design-tokens.json` (W3C) is the **portable canonical form**. To support a new
platform, generate that platform's theme file from the JSON — never re-pick
colors per platform. A per-surface override (e.g. a denser mobile spacing scale)
belongs in a `DESIGN.<surface>.md` that inherits the global contract
(`design-md-spec.md` → Hierarchy), not in ad-hoc values.

## Multi-brand / dark mode / white-label theming

For several brands or a light/dark pair from one contract, give `export_tokens.py`
a base token dict plus per-theme overrides (only the tokens that differ):

```python
import sys; sys.path.insert(0, "scripts")
from export_tokens import to_themed_css
css = to_themed_css(base_tokens, {"dark": dark_overrides, "acme": acme_overrides})
# -> :root { ... }  [data-theme="dark"] { ... }  [data-theme="acme"] { ... }
```

Switch themes with `<html data-theme="dark">`; the preview frame already reads
`/design/tokens.css`, so the chrome follows. **Audit every theme** for contrast
(`audit_contrast.py`) — a brand override can silently break AA. Each theme that
diverges in more than color belongs in its own `DESIGN.<theme>.md`.
