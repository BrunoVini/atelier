# Workflow: Component Census (reuse over reinvention)

Before generating UI, know what the repo already has — so output reuses
`<Button variant="primary">` instead of hand-rolling a new button. This is the
difference between a throwaway mockup and a page that's one PR from real.

## Run it

```bash
python3 scripts/census.py /path/to/repo            # human summary
python3 scripts/census.py /path/to/repo --json     # -> design/components.json
```

It catalogs exported components (PascalCase), any `cva` variant keys, a rough prop
list, and flags likely **duplicates** (same component name in multiple files) as
design debt.

## Use it

1. Populate `DESIGN.md` §7 (Components) from `design/components.json` — real names
   + variants, not a placeholder.
2. **Generation rule** (prototypes/variants/slides): before inventing a UI
   element, check `design/components.json`; if a matching component exists,
   reference it with its real props/variants. Only invent when nothing fits, and
   say so.
3. Duplicates → propose a consolidation; feed them to the design-debt report.

Re-run after adding components so the census (and the reuse rule) stays accurate.
