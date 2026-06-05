# Capability: Hi-fi Prototypes & App Mockups

Build production-looking, interactive prototypes in HTML — web pages, dashboards,
and mobile app screens wrapped in real device frames.

**First:** resolve the DESIGN.md gate (SKILL.md). Read `design/tokens.css` (or the
contract) and build to `references/design-philosophy.md`.

## Device frames (vendored assets)

- `assets/frames/ios.jsx` — iPhone 15 Pro frame (exact dimensions, notch/home bar)
- `assets/frames/android.jsx` — Android device frame
- `assets/frames/browser.jsx` — browser chrome
- `assets/frames/macos.jsx` — macOS window chrome

Render your screen *inside* the frame; the frame reserves the status bar / home
indicator — you only manage the content region.

## Rules that make prototypes feel real

- **Single-file inline React by default** — put JSX, data, and styles in one
  `<script type="text/babel">…</script>` in the main HTML. Don't load external
  JS via `<script src>`: under `file://` the browser blocks it cross-origin and
  forces an HTTP server, breaking the "double-click to open" intuition. Inline
  local images as base64 data URLs.
- **Real images, not drawn SVG** — pull from Wikimedia / the Met / Unsplash, or
  generated images. Never hand-draw faces/objects as SVG.
- **Make it interactive** — wrap an app prototype in a small state manager (e.g.
  an `AppPhone` component) so taps actually navigate between screens, instead of
  a dead screenshot.
- **Split only when large** — for a >10-screen app or a >1000-line file, split
  into `components.jsx` + `data.js` and include the `python3 -m http.server`
  startup command + URL in the delivery note.

## Verify before delivery

Run a quick Playwright check (click the primary flows; screenshot):

```bash
npx playwright screenshot file:///abs/path.html out.png --viewport-size=1200,900
```

To let the user **see and click** the prototype live, hand it to the preview
server — see `capabilities/preview.md`.
