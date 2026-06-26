# Workflow: Generate DESIGN.md

Produce a repo's design constitution by measuring what exists, enriching with the
knowledge base, and writing both the prose contract and the enforceable tokens.

**When:** the repo has no `DESIGN.md` and the user accepts the offer to create one
(see the gate in `SKILL.md`), or explicitly asks to (re)generate / refresh it.

## Steps

### 1. Measure the repo (empirical)

```bash
python3 scripts/scan_repo.py /path/to/repo > /tmp/atelier-scan.json
```

This returns the dominant clustered colors, referenced fonts, the framework, the
component library, the spacing/radius scales, and the **breakpoints** in use
(from `@media` + Tailwind `screens`). Treat the most frequent colors as palette
candidates and the referenced fonts as the existing type choices. Use the
breakpoints + framework to fill §4's **target surfaces** (responsive / pc-only /
mobile-only) and fluid strategy — ask the user the target if it's ambiguous.

Each color now carries `files` + `top_file_share` (provenance) — prefer colors that
are used across many files / carry a high share as palette roles, and treat a color
that lives in a single low-share file as a candidate one-off, not a role.

**Reconcile with what users actually SEE** — a string count over-weights dead code and
vendored CSS. If the repo (or the artifact) renders, run the paint-weighted measurement
and let it arbitrate which static colors are real:

```bash
node scripts/scan_rendered.mjs <built-page.html|url> --static /tmp/atelier-scan.json
```

The reconciliation distinguishes three things a static read CANNOT:
- **`dead`** — declared in CSS but paints **zero** pixels (a never-mounted class, a
  never-activated theme). Genuinely dead palette: don't promote to roles. Note the trap
  that the *most-mentioned* color in the static scan can be dead (e.g. a `#fff` used only
  in unmounted classes + an inactive light theme) — mention-count ranks it #1, the render
  shows zero. Always call this out by name when it happens; it's the sharpest reconciliation insight.
- **`faint`** — declared AND painted, but a sub-1% sliver (a 1px border, one link, an accent
  declared all over the CSS that paints under 1%). These are **LIVE, not dead** — never
  label a small-but-real token dead. Flagging an over-declared/under-painted accent is a real
  finding (the brand color that's "a rounding error"); calling it dead is a false positive.
- **`painted_not_declared`** — painted but absent from the CSS source (a color applied at
  runtime by JS/inline). The render catches it even at a small *visible* (not just ≥1%) share,
  flagged `accent` vs `major`. This is exactly what a static CSS scan misses.

**Report the painted-area measurement HONESTLY — disclosure is a deliverable, not a footnote.**
A painted-area number is only trustworthy if its method + limits are stated; a measurement
presented without them reads as less rigorous than an *honest estimate that admits it's an
estimate*. State, every time:
- **What you did** — rendered with a headless browser at a stated viewport (default 1440×900),
  over the full document, painted-area per color **alpha-weighted** (translucent paint counts
  proportionally), colors canvas-normalized so oklch/lab/inline are read.
- **What painted-share IS and is NOT** — it is *pixel coverage*, NOT perceived visual
  prominence or importance (a 0.98% accent can still be the focal point); a dominant neutral
  surface is not "the most important color" just because it covers the most pixels.
- **The standard limits** — viewport-dependent (a different width shifts surface-vs-text
  ratios); one route / one rendered state (activating a theme or mounting a class would
  resurrect dead colors — they are dead *as shipped*, not unreachable in principle); shadow
  DOM / cross-origin iframes are not traversed; the static `count` is a *reference tally*, not
  a literal-occurrence count, and near-colors merge at ΔE 8 (so a 2nd-dominant color can be
  absorbed into a neighbor's static entry).
- **Never fabricate** — report only shares you actually measured; if you could not render,
  say so plainly and frame any ranking as a static estimate, not a painted-area measurement.

### 1b. Assess consistency — DON'T write a confident contract for a messy repo

```bash
python3 scripts/assess.py /path/to/repo            # clean | minor | messy, per dimension
```

Be honest, and scale the response to the inconsistency level:

- **clean / minor** → auto-pick the recommended dominant pattern (assess gives a
  `recommend` per dimension) and write the DESIGN.md. State the variance honestly
  ("measured 14 colors; consolidated to a 5-role palette around the dominant ones").
- **messy** (assess `needs_user_input: true`) → STOP. Tell the user *which*
  dimensions are inconsistent and why (e.g. "23 colors with no dominant set",
  "mixed Tailwind + styled-components", "3 duplicate Button components"). For each
  messy dimension, present the **best options with atelier's pick pre-selected**
  (use the multiple-choice question tool), let the user choose, then write the
  DESIGN.md from their choices. Never silently invent a contract over chaos.

### 1c. Offer to standardize — only when the inconsistency would cause problems

After writing the DESIGN.md, if the repo was **messy** in a way that will bite
(off-contract colors everywhere, duplicate components, mixed approaches), OFFER —
don't force — a standardization pass grounded in the new contract:
`migrate_to_tokens.py` for hardcoded values, a component-dedupe plan from the
census, and `check.py` to verify. If the repo was clean/minor, skip this.

### 1d. Hunt overlaps across screen sizes (default — don't wait to be asked)

Scanning a repo includes checking for element overlaps/collisions across widths —
it's part of the scan, not a separate request. Overlaps surface in the **tablet
mid-range** (≈760–1100px), so endpoint-only looks miss them.

```bash
node scripts/responsive_check.mjs <running-url-or-html>   # if it can render: overflow + collision + deco-over-text
python3 scripts/overlap_risk.py /path/to/repo             # always: static risk patterns (no render needed)
```

- **If you can render** (a server is up, or you start one on a free port —
  `review.md` NEVER-COLLIDE), sweep widths: confirmed collisions and
  decoration-over-text candidates come back per width.
- **If you can't render**, run `overlap_risk.py` — it flags absolutely-positioned
  decorations with %-offsets, negative margins, and decoration clusters (the exact
  pattern that drifts onto content mid-range), as risks to verify.
- Report findings with the scan; record unresolved ones under DESIGN.md §12 (Known
  gaps). Fix the **cause**, then re-verify across the whole sweep (`review.md` §3c).

### 2. Classify the product type

From `package.json`, `README`, route/page names, and on-screen copy, infer the
product type (SaaS, fintech, e-commerce, portfolio, docs, dashboard, …). This
drives which knowledge-base recommendations apply.

### 3. Enrich from the knowledge base

```bash
python3 scripts/search_kb.py "<product type + tone keywords>" --domain palettes
python3 scripts/search_kb.py "<product type + tone keywords>" --domain typography
python3 scripts/search_kb.py "<product type + tone keywords>" --domain styles    # named styles
python3 scripts/search_kb.py "<stack>" --domain stack-guidance                   # react/next/shadcn/…
```

Use the KB to (a) fill gaps when the scan is sparse (new/empty repo), and
(b) sanity-check accessibility (contrast, WCAG). The empirical scan WINS over KB
suggestions when both exist — the KB only fills holes.

**Greenfield only (gated):** when there is **no repo signal at all** (empty/new
project, or "make it like Stripe"), you may consult the cold-start reasoning aid
(`--domain reasoning`) and the brand seeds (`--domain brand-exemplars`) to propose a
direction. These are SEEDS, not a contract: they NEVER override a repo that already
speaks, and the output still terminates in atelier's `DESIGN.md` (not a separate
persistent file). The moment real signal exists, the empirical scan wins.

### 4. Write DESIGN.md — thin contract when the repo already owns its tokens

Start from `templates/DESIGN.md.template`. **Fill the `atelier-contract` machine block**
(fenced ```json) — it is the canonical, machine-read contract; the tools parse it FIRST and
the prose tables are the human-facing fallback. It MUST be valid JSON: colors are hex strings,
`spacing` is a quoted list (`"4px", "8px", …`). **If the system ships a co-equal dark theme,
fill the block's `dark` map** (same roles, hex) so `audit_contrast.py` and `contract.py`
enforce the dark tokens too — otherwise dark mode is prose-only and unchecked; delete the
`dark` key for a light-only system. After writing, run
`python3 scripts/contract.py --validate <repo>` — it fails loudly if the contract parsed too
thin (e.g. the block was malformed and silently fell back to prose) — and
`python3 scripts/audit_contrast.py <repo>` to confirm every enforced pair clears AA in
**both** themes. Then **publish the numbers**: `python3 scripts/audit_contrast.py <repo>
--table` prints a measured per-pair markdown ratio table (per theme) — paste it into §2 so
the contract proves its AA claim instead of asserting it. For a hard hue that can't be both
on-brand AND AA as text, split the role (`warning-fill` vs `warning-text`) and document the
split (see design-md-spec → "Role taxonomy").

**Close the contract — define every scale your components reference.** If you fill the
optional `components` map, also define the named scales they point at IN the block:
`rounded`/`radii` (a named radii map `{sm,md,lg,…}`), `shadows` (named elevation), plus
the `typography` roles and color roles. `contract.py --validate` reports
`component_ref_issues` for any `{rounded.md}` / `{colors.surface}` / `{typography.x}` a
component references but the block never defines — and a non-empty list FAILS validation.
A contract that declares components styled by `{rounded.md}` while defining no `rounded`
map LOOKS complete but is internally inconsistent: the refs dangle and a second agent
can't resolve them. Keep iterating until `component_ref_issues` is empty. For an
enforceable state machine, give each interaction state its own component entry
(`button-primary-hover`, `text-input-error`, `tide-chart-loading`) so the whole catalog —
not just rest — is machine-readable.

First check `scan_repo`'s `token_source`. **If it is set** (the repo already owns
its tokens in a TS/JS theme module, a CSS custom-property theme, or a Tailwind
config — `kind` + `path`), write a **thin, pointer contract**, not a second copy of
the theme:

- **KEEP (the real value — governance + analysis the code doesn't carry):** §1
  identity/tone; §6 anti-slop rules; §7 canonical components + dedupe targets +
  interaction-state gaps (from the census); §8 data/chart standards; §9 house rules;
  §10 the *audited* contrast results/exceptions; §11 overrides; §12 known gaps. And
  the **canonical-source pointer**: name the `token_source` path as the source of
  truth and the access pattern (e.g. `useTheme()` / CSS vars).
- **TRIM to pointers — do NOT re-transcribe token values:** for §2 palette, §3 type
  scale/weights, §4 spacing/radius/depth, §5 motion, state the **roles/structure**
  and point at the source ("Palette roles: `brand.*`, `severity.*`, `surface.*` —
  values live in `<token_source.path>`; read via the theme. Don't duplicate hexes
  here."). Re-typing values into prose just creates a copy that drifts (the same
  failure as a stale CLAUDE.md).
- **Carry per-token provenance IN the machine block (`sources`).** Measuring is
  atelier's edge over eyeballing — so the machine block must be traceable, not just the
  prose. Fill the contract block's `"sources"` map: `{role: "file:line"}` (+ a nested
  `"dark"` sub-map for the dark theme), pointing each token at its `token_source` line /
  selector / config key. A block that lists `{role:"#hex"}` with no `sources` strips the
  provenance out of the artifact a tool consumes. After writing, confirm with
  `contract.py --validate` that `token_sources` covers your color roles. (See
  design-md-spec → "Token-source provenance".)
- **Measure only what is bespoke — point at the rest.** If the repo's spacing / type
  scale / shadows are a **framework default** (Tailwind defaults, etc.) and only the
  colors + `--radius` are bespoke, say so plainly and keep the block's measured surface
  to what the repo actually owns — don't transcribe the framework's default px values
  into `spacing`/`shadows` as if they were measured project tokens (that inflates the
  measured surface and reads as padding).
- **Show the source-format value beside the derived hex.** When the palette is stored in
  a non-hex format (HSL channel triples, `oklch(...)`, …), the prose palette table must
  show the **authoritative source value** AND the derived hex (label the hex *derived*),
  so the read is provably faithful and re-derivable — `--foreground | 222.2 47.4% 11.2% |
  #0f172a (derived) | globals.css:8`. The block stays hex (tools need it). A doc that
  shows only resolved hex for an HSL-stored palette reads as a weaker measurement.
- **Re-derive computed scale values — never guess.** For a scale defined by arithmetic on
  a bespoke token (e.g. `calc(var(--radius) - 4px)` with `--radius: 0.5rem` = 8px → 4px,
  NOT 2px), read the real base and compute each value; an off-by-one slip makes the block
  contradict its own prose. (See design-md-spec → "Show the value AS STORED" / "Re-derive
  computed scale values".)

**If `token_source` is null** (no existing source), fill
`templates/DESIGN.md.template` with the measured values directly — name the exact
fonts, hex values, and the anti-slop blocklist.

Either way, **scale §7–§9 to the repo** (design-md-spec → "Scale the contract"):
component standards (§7) from the census, data/chart standards (§8) for data-heavy
products, house rules (§9) for the team's conventions. A portfolio stays light; a
large/standardized repo gets the full governance treatment. Tell the user (in plain
language — not "§9") that the **House rules** section is where they drop company
conventions so atelier obeys and enforces them.

### 5. Export the tokens — ONLY if there's no existing token source

```dot
"token_source set?" -> "DON'T create design/. Point DESIGN.md at it. Stop." [yes];
"token_source set?" -> "export_tokens -> <repo>/design/" [no];
```

**Hard gate:** if `scan_repo` reported a `token_source`, do **NOT** run
`export_tokens` / create a `design/` folder — that's a parallel copy that will
drift from the real source, and it contradicts the contract you just wrote. Point
DESIGN.md at the existing source and stop. Export portable tokens only if the user
**explicitly asks** for them, and then label them a generated mirror.

Only when there is **no** existing source, build a token dict (shape in
`references/design-md-spec.md`) and export:

```bash
python3 scripts/export_tokens.py /tmp/atelier-tokens.json <repo>/design
# -> <repo>/design/{tokens.css, design-tokens.json (+ tailwind-preset.js IF Tailwind)}
# Always pass the repo's design dir explicitly — the default is the CWD.
```
Pass `tailwind=False` to `write_all` (or skip the preset) when the repo isn't
Tailwind (styled-components / CSS modules) — a Tailwind preset is noise there.

### 6. Build the living style guide (offer)

```bash
python3 scripts/census.py <repo>                       # component inventory for §7 (prints; --out to save)
python3 scripts/build_styleguide.py <tokens.json> -o /tmp/styleguide.html
```
The style guide renders the palette (with contrast labels), type scale,
spacing/radius, and the inventory — serve it via the preview server. Build it from
the token dict (a `/tmp` JSON derived from the repo's token source is fine) — you do
**not** need a `design/` folder, and don't create one just to render a preview.

### 7. Offer to commit

Show the user the `DESIGN.md` + token files (+ style guide) and offer to commit
them. Remind them the tokens can be imported by the build (CSS `@import`, tailwind
`presets`).

## Cold start (no repo / one-off artifact / "make it like this")

This is the case where atelier looks *least* different from free-handing it — there's
no design to measure, so the measurement thesis doesn't apply. Don't just "pick a tone
and generate" (that's the free-hand path). Earn the skill's keep by GROUNDING the
direction in the distilled knowledge a blank model doesn't have, giving a real choice,
and closing with the self-QA loop.

**First, the design read (one line, before anything):** state *"Reading this as: a `<page
kind>` for `<audience>`, in a `<vibe>` language"* — the model's default-aesthetic reflex is
the main reason cold-start output is generic; naming the read up front breaks it.

1. **Ground the direction in the KB** (don't invent from nothing):
   ```bash
   python3 scripts/search_kb.py "<product type + tone>" --domain styles          # named styles
   python3 scripts/search_kb.py "<product type + tone>" --domain palettes        # role'd palettes
   python3 scripts/search_kb.py "<named brand or vibe>"  --domain brand-exemplars # cold-start seeds
   python3 scripts/search_kb.py "<product type>"         --domain reasoning       # greenfield reasoning
   python3 scripts/import_reference.py --url https://… / --image ref.png          # or import a reference
   ```
2. **Offer 2–3 distinct directions**, not one — let the user pick (see `variants.md`).
   Each is a committed tone + palette + type + motion, named (not "modern/clean").
3. **Capture a tiny inline contract** from the pick (tone + palette roles + the one
   display/body/mono + motion) so generation is constrained even without a repo. With only
   a brand color or two, synthesize a full WCAG-correct token set (on-colors, muted, card,
   border, ring) instead of hand-picking:
   ```bash
   python3 scripts/synthesize_tokens.py '{"primary":"#2563eb","background":"#ffffff"}'
   ```
   Then **guard against your own sameness** — check the pick differs from recent
   cold-start work, and record it once committed. **Always pass `--category` when the
   brief names a product category** — it fires the *second-order* check (the predictable
   "safe" look for that category) which the recent-collision check alone cannot see:
   ```bash
   python3 scripts/cold_start_ledger.py check  "<display font>" "<archetype>" "#p" "#ink" "#paper" --category "<category>"
   python3 scripts/cold_start_ledger.py record "<display font>" "<archetype>" "#p" "#ink" "#paper"
   ```
   If `check` warns it's too similar to a recent output **or that it's the category
   reflex**, pick a different palette/font family — follow the `reach for instead:` line
   it prints. The category trap is the one that bites a 2nd brief in a NEW register: you
   escape your *previous* project's look but land on the new register's *default* look
   (every warm/heritage food brand → unbleached-cream paper + a Playfair/Palatino serif +
   terracotta; every fintech → emerald + Space Grotesk). Diverging from the prior is NOT
   enough if you land on the register's cliché.
   - **Treat a `slop_check` `*-default` finding as a divergence signal, not just a lint.**
     `oklch-warm-neutral-default` (the cream/sand/paper monoculture) and the
     purple/indigo-gradient defaults are the *same* second-order trap the reflex-reject
     names: a generic, un-owned ground. Source a real ground color from the product's own
     material (the grain, the stone, the liquid, the room), not the register's safe cream.
4. **Generate** using the craft refs (design-philosophy, prototypes/animations).
5. **Run the self-QA loop and FIX** (see SKILL.md "Definition of done") — `slop_check`,
   `audit_contrast`, `overlap_risk`/`responsive_check`. This is the part a blank model
   cannot do, and it's the concrete reason to run atelier on a from-scratch artifact.

Imported/KB values are a *starting* direction — confirm with the user before committing.

## Notes

- This is empirical-first: never skip step 1 and invent a palette. The whole
  point of atelier is that the contract reflects reality.
- For a brand-new repo with no CSS at all, say so plainly, then drive the palette
  from product type + a chosen tone (design-philosophy §5), the KB, or an imported
  reference (above).
