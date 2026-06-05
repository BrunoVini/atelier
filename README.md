# atelier

**A repo-aware design studio for Claude Code.** atelier measures the real design
language of your codebase, writes it down as an enforceable `DESIGN.md` (plus
design tokens), and then generates every visual artifact — prototypes,
components, slides, animations, and live previews — so they obey that one source
of truth. One bold, intentional aesthetic per project; never generic AI slop.

It fuses four lineages into one skill:
- **huashu-design** — generative HTML quality (prototypes, slides, narrated
  animations, device frames, MP4/GIF export).
- **frontend-design** (Anthropic) — the anti-generic-aesthetics philosophy.
- **ui-ux-pro-max** — a structured design knowledge base (palettes, type, UX).
- **superpowers** — authoring rigor and the local **preview server**.

## Install

```bash
# Add the marketplace, then install the plugin (Claude Code):
/plugin marketplace add /path/to/atelier
/plugin install atelier@atelier-dev
```

Then just ask for design work in any repo — the skill triggers on prototypes,
pages, components, slides, animations, previews, variants, reviews, or "make it
look good".

## The DESIGN.md contract

The first time you do visual work in a repo with no `DESIGN.md`, atelier offers
to generate one by **measuring** your code (clustered colors, fonts, framework,
component library) and enriching it from the knowledge base. The result:

- `DESIGN.md` at the repo root — palette, type, spacing, motion, anti-slop rules.
- `design/tokens.css`, `design/tailwind-preset.js`, `design/design-tokens.json`
  — the enforceable, machine-readable half.

Every later generation reads the contract and stays inside it. More specific than
`CLAUDE.md`, and enforceable in code.

## Capabilities

| Ask for… | What you get |
|---|---|
| A DESIGN.md / design system | Empirical extraction + tokens |
| A live preview / demo / "show me" | Local server, click-to-select, themed by your tokens |
| A hi-fi prototype / app mockup | Interactive HTML in real device frames |
| Slides / a deck | HTML deck with speaker notes (+ optional PDF/PPTX) |
| An animation / explainer / video | Narrated motion + MP4/GIF export |
| 2–4 design directions | Parallel variants + a scoring jury |
| A design review | 5-dimension critique with severities |

## Scripts

```bash
python3 scripts/scan_repo.py <repo>          # empirical design report (JSON)
python3 scripts/export_tokens.py tokens.json # -> design/tokens.css + preset + W3C json
python3 scripts/search_kb.py "fintech" --domain palettes   # KB lookup
node scripts/screenshot.mjs page.html shot.png             # capture for review/scoring
scripts/preview/start.sh --project-dir <repo>              # live preview server
scripts/export_video.sh anim.html out.mp4                  # render to video
```

## Development

```bash
python3 -m pytest atelier/tests/ -v   # run the script test suite
```

## License

MIT — see `LICENSE`.

## Credits

atelier stands on the shoulders of, and adapts material from, these projects —
each under a permissive license whose attribution is preserved here:

- **huashu-design** (MIT) — generative HTML components (device frames, narration
  stage, deck/canvas engines) and the anti-AI-slop design philosophy.
- **frontend-design** by Anthropic (Apache-2.0) — distinctive-frontend guidance.
- **ui-ux-pro-max** by nextlevelbuilder (MIT) — the structured design knowledge
  base (palettes, type pairings, product types, UX guidelines, charts).
- **superpowers** by Jesse Vincent (MIT) — SKILL authoring conventions and the
  local preview server (adapted into `scripts/preview/`).
