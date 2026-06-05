# Workflow: Architecture Fit (writing FRONTEND code into an existing repo)

Great design includes the architecture of the **frontend** code that renders it.
When atelier writes real UI code into an **existing** repo (a component, a page, a
feature), it acts like a senior *frontend* engineer: understand how the UI layer
is built, where it's weak, and what the change touches — then write code that
*fits and improves* it, not just looks good in isolation.

> **Scope: frontend / design only.** This is about the UI layer — component
> structure, styling approach, design tokens, UI file organization, client/UI
> state, accessibility. atelier does **not** inspect, judge, or touch **backend**
> code (APIs, databases, services, business logic, infra). That's not its job —
> if the repo has a backend, ignore it. Stay in the design/front lane.

**Use when:** generating/editing real UI code in an existing repo (not a
throwaway HTML mockup). Skip for standalone prototypes/demos.

## 1. Survey before you write

```bash
python3 scripts/survey_repo.py <repo>          # framework, styling, state, dirs, smells
python3 scripts/census.py <repo>               # components to reuse + duplicates
python3 scripts/lint_design.py <repo> --contract design/design-tokens.json
```

Read the survey: the **styling approach** (Tailwind vs CSS-in-JS vs CSS-modules
vs plain CSS), **framework + router**, **state management**, **directory
conventions** (where components/pages/hooks/styles live), **oversized files**, and
**duplicate components**.

## 2. Match the repo's conventions (don't impose your own)

- **Styling:** use the repo's existing approach. Don't drop Tailwind into a
  CSS-modules repo, or styled-components into a Tailwind repo. Bind to the
  contract tokens *in that approach* (`var(--token)`, the Tailwind preset, or the
  theme object).
- **Location & naming:** put files where the repo puts them; follow its naming.
- **State & data:** use the repo's state/data libraries and patterns, not a new one.
- **Components:** reuse from the census before inventing (prototypes.md rule).

## 3. Improve the weaknesses you touch (only those)

Like a good developer working in existing code: if a file you're modifying has
grown unwieldy, has tangled responsibilities, duplicates a component, or carries
off-contract styling, **fix that as part of the work** — extract a focused
component, dedupe, migrate hardcoded values to tokens (`migrate_to_tokens.py`).
Do **not** unilaterally refactor unrelated code; stay scoped to what serves the
change. (This mirrors the "working in existing codebases" discipline of
disciplined design — improve what you're in, don't sprawl.)

## 4. Best-practices checklist for the new code

- Small, focused files with one clear responsibility; clear component boundaries.
- Reuse tokens + components; zero hardcoded colors/spacing (lint-clean).
- Accessibility: semantic markup, labels, contrast (audit_contrast), focus, reduced-motion.
- Typed props / clear interfaces; no dead styles; no copy-paste of an existing component.
- Match the repo's import style, formatting, and test conventions.

## 5. State the fit plan, then write

Before generating, say briefly: *where* the files go, *which* components/tokens
you reuse, *which* styling approach you match, and *what* weakness (if any) you'll
improve along the way. For multi-file/feature work, escalate to
`references/workflows/design-plan.md` (each task carries this fit + acceptance
criteria). After writing, run `check.py` so the change lands lint-clean and
contrast-safe.
