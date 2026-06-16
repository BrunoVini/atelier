# Capability: Hi-fi Prototypes & App Mockups

Build production-looking, interactive prototypes in HTML — web pages, dashboards,
and mobile app screens wrapped in real device frames.

**First:** resolve the DESIGN.md gate (SKILL.md). Read `design/tokens.css` (or the
contract) and build to `references/design-philosophy.md`. Then **check the
component census** (`design/components.json` via `workflows/census.md`): reuse the
repo's real components/variants before inventing new UI — it makes the output
belong in *this* codebase.

**Writing real UI code into an existing repo** (not a standalone mockup)? First
run the **architecture-fit** pass (`references/workflows/architecture-fit.md`):
match the repo's styling approach, file conventions, and component patterns, and
improve only the frontend weakness you touch. (Backend is out of scope — ignore it.)

## Device frames (vendored assets)

- `assets/frames/ios.jsx` — iPhone 15 Pro frame (exact dimensions, notch/home bar)
- `assets/frames/android.jsx` — Android device frame
- `assets/frames/browser.jsx` — browser chrome
- `assets/frames/macos.jsx` — macOS window chrome

Render your screen *inside* the frame; the frame reserves the status bar / home
indicator — you only manage the content region.

## Rules that make prototypes feel real

- **Truly self-contained — it MUST boot offline by double-click.** This is the
  bar a prototype is judged against, and the easiest one to fail. Concretely:
  **never depend on a CDN runtime.** A `<script type="text/babel">` block needs the
  Babel transpiler, and React needs React/ReactDOM — if those come from `unpkg`/a
  CDN, the file is a **blank white screen offline** and pays a slow in-browser
  transpile on every load. That is a real, disqualifying defect, not a nitpick.
  So:
  - **Default to vanilla JS** (plain DOM + a tiny state object). No transpiler, no
    framework runtime, nothing to fetch — the most robust prototype and usually the
    fastest to write for ≤~8 screens.
  - **If you genuinely want React/JSX**, you must keep it self-contained: either
    author with `React.createElement` (no JSX → no Babel at all), OR inline a
    pre-compiled bundle. NEVER ship `<script src="…unpkg…/babel">` + `type="text/babel"`.
  - The `assets/frames/*.jsx` device frames are **authoring references** — translate
    them into the deliverable's actual runtime (vanilla JS or inlined), don't drag a
    CDN Babel along to run raw JSX.
  - **Type must be self-contained too — NO runtime `<link>` to Google Fonts (or any
    web-font host).** It is tempting to think a font link is harmless because the page
    "still boots and degrades." It is not harmless for an OFFLINE deliverable: offline the
    request fails, the browser logs a **console error**, and the screen renders in the
    *wrong* typeface — the exact display face you art-directed is gone, so the finish you
    shipped is not the finish that's seen. A blind judge that measures network attempts on
    an offline load will count that failed fetch against the brief's #1 requirement (it did,
    and it cost a head-to-head). So: either **inline the font** (`@font-face` with a base64
    `woff2` `src`) for a true display face, OR use a **native system-font stack**
    (`-apple-system, system-ui, "SF Pro", …`) — which on iOS *is* the real platform face and
    reads perfectly native. Never a `<link rel=preconnect>`/`<link rel=stylesheet>` to a font
    CDN. Inline local images as base64 data URLs.
  - **Verify it mechanically, don't eyeball it:** run `python3 scripts/qa.py --kind prototype
    <file>` — the `offline-safe` gate fails on ANY runtime network reference (font link, CDN
    script, remote `@font-face`/image, `fetch`/`import` to http). Zero is the only passing
    number. (A self-report of "fully offline" is not evidence — the t-battery proved generators
    miss their own font link; the gate doesn't.)
- **The frame must read as a held physical device, not a screen with rounded corners.**
  Give the iPhone a real **black bezel with depth** (a thin outer band, a hint of edge
  highlight, accurate ~44–52px corner radius, side/volume button nibs) sitting on a calm
  **neutral studio backdrop** (a soft warm-grey/sand or a gentle vignette) — NOT the app's
  own background colour bled out to the window edges. A frame floating on a flat colour void
  reads as a mockup canvas; a bezel with depth on a neutral ground reads as a device you could
  pick up, and a blind judge calls the difference explicitly. The status bar, Dynamic Island,
  and home indicator must be present and correctly proportioned (use `assets/frames/ios.jsx`
  geometry; don't hand-eyeball the island).
- **Make it interactive** — wrap an app prototype in a small state manager (an
  `app` object / `render()` switch, or an `AppPhone` component) so taps actually
  navigate between screens, instead of a dead screenshot. Verify every tab/button
  does something — no dead controls.
- **Surface the core action on the top-level screen, not only behind a drill-in.** A real
  app lets you *do the main thing* from the home/list — a per-row quick-action button (Water,
  Mark done, Add) right where the item lives — and reserves the detail screen for depth. A
  prototype where the home is read-only and every action hides one tap deep reads thinner and
  less real than one with inline actions, AND it leaves the home with fewer (and less generous)
  tap targets. Inline the primary verb; it raises functional density, realism, and the count of
  comfortable hit areas all at once.
- **When state changes, propagate it richly and honestly — every field it truly touches.**
  A one-badge flip ("Needs water" → "Watered") is the floor, not the finish. Tapping the primary
  action should update *every* field that genuinely changed — next-due ("Today" → "in 7 days"),
  last-done ("7 days ago" → "Just now"), a streak/count (+1), the action button's own label/state
  ("Water now" → "Watered · log again") — and surface a brief confirmation. The richer the
  truthful propagation, the more the prototype feels like a working app rather than a slideshow;
  a blind judge that diffs the before/after screen rewards multi-field feedback over a single
  badge. (Never fabricate a change that didn't happen — honesty still governs; see review.md.)
- **Motion & delight are first-class — a prototype is felt in motion, not as stills.** The
  difference between a prototype that feels *pleasant* (agradável) and one that feels flat is
  almost entirely motion and micro-feedback, and it is the easiest quality to under-build because
  a screenshot can't show it. Build it deliberately:
  - **Fluid screen transitions.** Pushing to a detail should *animate* (a slide-in / shared-element
    or a soft fade-scale), tab switches should cross-fade or slide — not hard-cut. Use real
    **eased/spring curves** (`cubic-bezier(...)`, a spring), centralised as easing tokens, never the
    browser's default linear/ease on everything.
  - **A transition must be CONTAINED — never double-expose two screens.** This is the single most
    common way an animated router looks broken, and it is a *correctness* bug, not a taste one (a
    transition can have perfect easing and still be visually wrong). Two failures to design out:
    (1) **Ghosting on a cross-fade:** fading screen A's opacity 1→0 while B's goes 0→1 means at the
    midpoint BOTH opaque full-screens are ~50% visible and you see one *through* the other. Don't
    cross-fade two opaque full-screen views by opacity. Instead animate **one** view (the incoming
    one slides/fades IN on top, fully opaque, at a higher `z-index`) while the other stays put
    beneath, then hide the covered one. (2) **The previous screen lingering behind a pushed detail:**
    when you push a detail in, give the detail an **opaque background that fully covers**, and drive
    the underlying screen to a **terminal hidden state** (`visibility:hidden`/`display:none`) once
    the push settles — don't leave it painted behind. Because exit animations need the leaving view
    to stay rendered *while* it animates out, set its hidden end-state with `animation-fill-mode:both`
    (so it holds the final `opacity:0`/off-screen frame) AND flip it to `display:none`/`hidden` on
    `animationend` — base `.view{visibility:hidden;opacity:0}` competing with a running exit animation
    is exactly what produces the flicker/overlap. **Verify on the rendered mid-transition frames**
    (capture frames *during* the animation — see the verify step): at no instant should two different
    screens both be visible. (This is §19d "construct it truthfully and verify on the render" applied
    to UI motion: present is not the same as coherent.)
  - **Tactile press feedback.** Every tappable control responds on touch (`:active` scale-down ~0.96
    + opacity, a ripple, or a highlight) so taps feel registered.
  - **Toasts and state changes ease in and out** (rise + fade on a spring, auto-dismiss), they
    don't pop. A well-built toast is a signature delight beat — make it land.
  - **Considered colour & depth.** A cohesive palette with intentional accent, soft shadows/blur for
    elevation, gentle gradients — warmth over flat grey. This is a real differentiator a judge sees
    instantly.
  - **Honor `prefers-reduced-motion`** — collapse transitions to instant/opacity-only. Considered
    motion includes its off-switch.
  These are not garnish; on the *finish* dimension they are most of the score. Build the motion
  system as carefully as the layout.
- **iOS tap targets ≥ 44×44px** (Apple HIG); Android ≥ 48dp. A 30px check button
  is a real ergonomics miss on a device prototype — size the hit area up even if the
  visual glyph is smaller. **And mind the fit-to-viewport scale:** if you shrink the
  whole device frame with `transform: scale(...)` to fit small windows, that scale
  multiplies your tap targets too — a 44px control inside `scale(.84)` renders at 37px
  and silently fails the bar. Only trigger the down-scale when the viewport is
  *genuinely narrower than the frame's own CSS width* (e.g. `@media (max-width: 393px)`
  for a 393px iPhone), not at some loose 460px breakpoint where the frame already fits;
  and verify the *rendered* target size at the width you'll be judged on, not just the
  CSS value.
- **Images** — for a real brand/product, use real images (Wikimedia / the Met /
  press kits / generated), never hand-drawn faces or product photos as SVG. For a
  fictional app, an offline-self-contained build, or UI iconography, crisp **inline
  SVG icons/marks are correct** (one coherent set — see `svg.md`); don't reach for a
  CDN image host just to avoid drawing an icon.
- **Split only when large** — for a >10-screen app or a >1000-line file, split into
  modules and include the `python3 -m http.server` startup command + URL in the
  delivery note (this is the one case where an HTTP server is justified — say so).

## Verify before delivery

1. **Offline gate (mechanical, non-negotiable):**
   ```bash
   python3 scripts/qa.py --kind prototype file.html
   ```
   `offline-safe` must read `network_refs=0`. Any runtime network reference fails the gate —
   inline it (base64 woff2 / data: image) or drop to a system-font stack.

2. **Click-through (flows actually work):**
   ```bash
   npx playwright screenshot file:///abs/path.html out.png --viewport-size=1200,900
   ```
   Click the primary flows; confirm `pageerror`/`console.error` are 0, and re-load with the
   network OFF (block all non-`file:`/`data:` requests) to confirm it boots — not just that it
   *should*.

3. **Capture the motion, not just the screens.** A still cannot show the thing a prototype is
   judged on most — how it *feels* in motion. Record the signature beats so the craft is visible
   to a reviewer (and to anyone judging from afar): grab a **rapid frame sequence across a tab
   switch and a list→detail push** (e.g. screenshot every ~60ms for ~0.5s through the transition),
   and a **toast rising and settling**. A flat hard-cut prototype and a fluidly-eased one look
   identical in a single screenshot and completely different across a 6-frame strip — that strip is
   the evidence. (Pair it with the structural motion facts: keyframes / eased-or-spring transitions
   / reduced-motion honored — a prototype with `@keyframes`, spring easing, and tactile `:active`
   states is doing real motion work that a rival of flat default-eased transitions is not.)

To let the user **see and click** the prototype live, hand it to the preview
server — see `capabilities/preview.md`.
