---
description: Token-migration codemod — rewrite hardcoded values to var(--token)
argument-hint: [repo-path]
allowed-tools: Read, Edit, Bash(python3:*), Bash(node:*)
---

Run the token-migration codemod over `$ARGUMENTS`: rewrite hardcoded colors, spacing, radius and font-family literals to the semantically-correct `var(--token)` against the contract. The codemod is **pixel-safe and role-aware**: it rewrites only EXACT matches (never a near-but-unequal value, which would move pixels), maps by ROLE (an `8px` gap → a spacing token, an `8px` `border-radius` → a radius token), never rewrites a token *definition*'s own value, and leaves `calc()`/`@media`/rgba()/non-spacing dimensions and any block marked `/* atelier-ignore */` (vendor / non-themable) alone. Always dry-run first — `${CLAUDE_PLUGIN_ROOT}/scripts/migrate_to_tokens.py "$ARGUMENTS"` reports the proposed unified diff; re-run with `--apply` only after the user confirms. Follow `references/workflows/enforce-coherence.md`, then PROVE zero pixels moved: render before and after and diff the screenshots (must be 0).
