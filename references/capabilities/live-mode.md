# Capability: Live Mode (iterate on the user's running app)

Live mode lets the user refine their **actual running dev server** — a Vite or Next app
— instead of atelier's own preview. atelier puts a small reverse proxy in front of the
user's dev server: it forwards every request to the upstream server and injects the
atelier picker client into HTML responses. The user opens the proxy URL, picks an
element, asks for contract-bound variants, previews them live, and accepts the winner
back into source — **gated by `qa.py`**. It never changes the user's config and never
touches their project files except through the guarded, journaled accept.

This is the live cousin of `preview.md` (which serves atelier's OWN output) and
`refine.md` (the named-move vocabulary). Use it when the design lives in a real app the
user is already running.

**When to use live mode:**
- The user says "iterate on my running app", "tweak my Vite/Next app live", "live
  preview of my dev server", "modo ao vivo", "ajustar meu app Vite/Next rodando".
- There is a real dev server up (you found it with `scripts/detect_server.sh`) and the
  design work is on the live app, not a fresh artifact.

If there is **no** running dev server, or the framework isn't Vite/Next, fall back to
atelier's own preview server (`preview.md`).

## How it works

1. **The user runs their dev server** (e.g. `npm run dev` → Vite on `:5173`, Next on
   `:3000`). atelier does not start it — it's the user's app, env, and backend.

2. **Find it.** `scripts/detect_server.sh` probes the common dev-server ports and prints
   the first reachable URL.

   ```bash
   URL=$(bash scripts/detect_server.sh)
   ```

3. **Classify it.** `scripts/live_detect.py` fetches `/` and classifies the framework
   from response signatures — Vite (`/@vite/client`, `import.meta.hot`), Next
   (`/_next/`, `__NEXT_DATA__`), SvelteKit, Astro, Nuxt, or plain HTML. It returns
   `{url, framework, hmr, can_inject}`. Garbage or unreachable resolves to `unknown` with
   `can_inject:false` (no crash).

   ```bash
   python3 scripts/live_detect.py "$URL"
   # {"url":"http://localhost:5173/","framework":"vite","hmr":true,"can_inject":true}
   ```

4. **Start the proxy in front of it**, on a guaranteed-free port (`scripts/free_port.sh`).

   ```bash
   PORT=$(bash scripts/free_port.sh)
   node scripts/preview/live-proxy.cjs --upstream "$URL" --port "$PORT" \
     --project-dir /path/to/repo --journal-dir /tmp/atelier-live/journal
   ```

   Open the proxy URL (printed as JSON on startup). The user's app loads normally,
   with the atelier picker client injected.

5. **Pick → variant → accept.** In the proxied page, **alt+click** an element to select
   it, then call `atelier.openPicker({ mode: 'steps' })` (or `range` / `toggle`) from the
   console. Variants are contract-bound (the same on-contract engine as `refine.md`) and
   preview as **ephemeral inline styles** — nothing is written until accept.

## Knob tuning (range / steps / toggle)

After calling `atelier.openPicker({ params: [...] })`, a knob panel docks below the
variant buttons. Each param drives a CSS custom property (`--p-<id>`) or data attribute
(`data-p-<id>`) on the picked element in real time. No source write happens — the knobs
are ephemeral. On accept, `atelier.accept({ ..., knob_values: atelier.getKnobValues() })`
ships the current values to the server where `live_carbonize.py` bakes them into the
accepted CSS (call it after accept on the CSS block you wrote to source).

Param kinds: `range` (slider → `--p-id`), `steps` (segmented → `data-p-id="value"`),
`toggle` (checkbox → `--p-id: 0|1` + presence of `data-p-id`).

## Insert mode (net-new content)

`atelier.insert({ file, anchor: {id?, tag?, classes?, text?}, position: 'before'|'after' })`
calls `/__atelier/insert` → `{ ok, file, line, position, context }`. Use the returned
`line` to know where to write net-new ephemeral HTML for the user to preview. Accept via
the normal `atelier.accept()` flow.

## Session journaling & recovery

Each proxy run writes an append-only JSONL journal to `--journal-dir` (default:
`/tmp/atelier-live/journal`). After a proxy restart, call:

    python3 scripts/live_status.py --journal-dir <dir> --session <id>

Or GET `/__atelier/status?session=<id>` to recover the session state without relaunching.

## Steer (page-level direction)

The floating steer bar (bottom-right of the proxied page) lets the user type or speak
a page-level instruction without picking an element. Instructions POST to
`/__atelier/steer`, are journaled, and printed to the proxy's stdout for the agent.
From the console: `atelier.steer` is not a public API — the bar is the UX; the agent
reads instructions from the proxy log.

## Drift-heal warning

`scripts/live_config.py` scans `project_dir` for HTML files not covered by the proxy's
inject. Run at boot:

    python3 scripts/live_config.py <project_dir> --injected '["path/to/index.html"]'

Returns `{orphans, count, hint}`. Warn the user about orphan pages before entering the
poll loop.

## Prefetch

The client fires a one-time `/__atelier/prefetch { page_url }` on the first element
selection per page URL. The proxy logs it to stdout so the agent can speculatively read
the source file for that page while the user decides what to do.

## The qa-gated accept (the differentiator)

Accepting writes the durable change back to the user's **source**, but only through the
gate. On accept (`scripts/live_accept.py`, also runnable standalone):

1. Apply the edit via `edit_apply` — journaled, reversible, refuses generated/minified/
   vendored files, and requires the `old` anchor to occur **exactly once**.
2. Run `qa.py` on the affected artifact.
3. **If `qa.py` fails, auto-revert the edit** so the user's source is byte-identical to
   the original, and return the failure to the picker. A bad variant never sticks.
4. If `qa.py` passes, keep it and record the session accept.

A `qa` verdict of `unknown` (e.g. no headless browser, so the rendered checks can't run)
does **not** auto-revert — atelier never trusts a null it can't explain (`review.md` §3c)
— but the static checks (slop, contrast, overlap) still gate, and those run without a
browser, so the gate is real offline.

**Accept needs an explicit file + anchor.** atelier does **not** build fragile
CSS-rule-to-source mapping. The caller (agent or user) supplies the source `file`, the
unique `old` snippet to replace, the `new` snippet, and the `qa_target` to QA:

```js
atelier.accept({
  file: '/repo/src/components/Card.tsx',
  old: 'className="card"',
  new: 'className="card card--flat"',
  qa_target: '/repo/dist/index.html',   // or the repo dir
  session: '<session-id>',
  contract: '/repo',                     // repo dir | tokens.json | DESIGN.md
});
```

The unique-anchor safety in `edit_apply` is what makes a supplied anchor safe — if the
snippet isn't unique, the edit is refused rather than rewriting the wrong place.

## Supported frameworks and fallback

| Framework | `can_inject` | HMR |
|---|---|---|
| Vite | yes | yes |
| Next.js | yes | yes |
| SvelteKit | yes | yes |
| Astro | yes | best-effort |
| Nuxt | yes | yes |
| Plain HTML | yes | no |
| Unknown | no — falls back to `preview.md` | — |

The proxy is framework-agnostic for any dev server that serves HTML; detection just
decides whether atelier *claims* live mode or routes to its own preview server.

## HMR and WebSocket passthrough — honest limits

Vite and Next push hot updates over a WebSocket upgrade. The proxy **tunnels the upgrade
transparently** (raw socket pipe to the upstream) so HMR keeps working through it. This
tunneling is **best-effort**: it is exercised against a fake server in the test suite, but
the full Vite/Next HMR handshake is only validated in the opt-in real-framework E2E
(`tests/live_e2e/`). If the tunnel fails, the proxy tears down its own side without
crashing and the **page never breaks** — the injected client degrades to its
`MutationObserver` re-attach (it re-binds the picker after the framework replaces the DOM)
but loses the live HMR push. When in doubt, a full reload of the proxy URL re-syncs.

The injected client is **idempotent** (HMR can re-inject the script) and fully
defensive: every entry point is wrapped so a failure in atelier's client can never break
the user's app — atelier is a guest in that page.

## Monorepo: scope to the active app's contract

In a monorepo, live-mode scopes to the **active app's inherited contract**. Pass
`--app <subdir>` to the proxy (or `app` in a `/__atelier/variants` request body) and the
variant engine resolves the contract via `contract.resolve_contract_for_app(app_dir,
repo_root=projectDir)` — folding the root `DESIGN.md` base with the app's per-app
`DESIGN.md` override (app wins; see design-md-spec.md §Monorepo). Without `--app`, or for
a single-contract repo, resolution is byte-identical to plain `resolve_contract`, so
nothing regresses. This keeps the picker → variant loop bound to exactly the contract the
app you're editing answers to.

## Safety summary

- **No config changes, no project-file writes** except the guarded accept.
- **Accept is qa-gated with mandatory auto-revert** — a qa-failing variant leaves source
  byte-identical to the original.
- **Writes are confined to `--project-dir`** and refuse generated files.
- **Never commits, never pushes.** Grouping accepts into a committable session is the
  separate, opt-in `session_commit` (see `edit_apply.py`); accept never calls it.
- `--inject-only` runs the proxy as a pure preview (injection only; the accept/revert
  endpoints are disabled).

See also: `preview.md` (atelier's own preview server), `refine.md` (the named-move
vocabulary and variant modes), `design-laws.md` (what the contract enforces).
