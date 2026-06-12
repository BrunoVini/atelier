/*
 * focusorder.mjs — pure helpers for the keyboard focus-order rendered check
 * (focus_order.mjs). Factored out so they're unit-testable via `node -e` WITHOUT a
 * browser: cycle detection over a recorded tab sequence, and the one load-bearing
 * judgement — given a focused node's computed metrics, is it a REAL `focusable-hidden`
 * bug (you tab to something you can't see) or just a legitimate screen-reader skip-link?
 *
 * The browser side (focus_order.mjs) presses Tab repeatedly, records each
 * document.activeElement's metrics into a plain object, then feeds them here. Keeping
 * the predicate here means a browser isn't needed to test the gating logic.
 */

/*
 * detectCycle — given the ordered list of focus "keys" recorded by pressing Tab
 * (each key uniquely identifies the focused element for this walk), return how many
 * DISTINCT stops were seen before the sequence started repeating, and whether it
 * cycled at all. The tab loop stops when activeElement repeats a key we've already
 * seen (the ring wrapped) OR when a cap is hit. This is pure list logic.
 *
 *   keys: string[]  — activeElement identity per Tab press, in order
 *   returns { stops: string[] (deduped, in first-seen order), cycled: bool,
 *             repeatedAt: index of the first repeat or -1 }
 */
export function detectCycle(keys) {
  const seen = new Set();
  const stops = [];
  let repeatedAt = -1;
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    if (seen.has(k)) { repeatedAt = i; break; }
    seen.add(k);
    stops.push(k);
  }
  return { stops, cycled: repeatedAt !== -1, repeatedAt };
}

/*
 * isFocusableHidden — the ADVISORY classifier. Given a focused element's computed
 * metrics, decide whether it looks like the keyboard smell: an element that RECEIVES
 * keyboard focus while it is visually hidden. focus_order REPORTS this as advisory and
 * NEVER gates on it (the custom-form-control and closed-drawer idioms make it FP-prone),
 * but we still keep the predicate PRECISE so the advisory is signal, not noise.
 *
 * `display:none` can't reach this code (browsers never focus it). The real bug shapes:
 *   • zero-size box      — width<=0 or height<=0 while focused
 *   • visibility:hidden  — laid out but invisible, yet took focus
 *   • opacity:0          — fully transparent and NOT mid-transition (a transitioning
 *                          element is briefly 0 — don't gate that)
 *   • fully offscreen     — positioned entirely outside the viewport/document
 *
 * EXCEPTION (do NOT gate): the well-known "visually-hidden but screen-reader-intended"
 * skip-link / a11y pattern. A skip-link is SUPPOSED to be invisible until focused and is
 * a feature, not a bug. We recognise it by intent signals on the node (an in-page hash
 * href, a skip-link-ish class/text, or the canonical clip-rect visually-hidden recipe)
 * so we never punish correct accessibility work. When unsure, return false (don't gate).
 *
 * metrics shape (all optional; missing -> treated as "not hidden in that dimension"):
 *   { width, height, visibility, opacity, transitioning, rectLeft, rectTop,
 *     rectRight, rectBottom, viewportWidth, viewportHeight, tag, href, className,
 *     text, clip, clipPath, position }
 */
export function isFocusableHidden(m) {
  if (!m || typeof m !== 'object') return false;

  // Intent-based allowlist FIRST: a deliberate screen-reader skip-link / visually-hidden
  // control is correct a11y, never a bug — bail before any "hidden" check can fire.
  if (isIntentionalSkipLink(m)) return false;

  const w = num(m.width);
  const h = num(m.height);
  const zeroSize = (w !== null && w <= 0.5) || (h !== null && h <= 0.5);

  const visHidden = m.visibility === 'hidden' || m.visibility === 'collapse';

  // opacity:0 only counts when NOT actively transitioning (a fade-in is briefly 0).
  const op = num(m.opacity);
  const opacityZero = op !== null && op <= 0.01 && !m.transitioning;

  const offscreen = isFullyOffscreen(m);

  return Boolean(zeroSize || visHidden || opacityZero || offscreen);
}

/*
 * isIntentionalSkipLink — recognise the legitimate "hidden until focused" a11y pattern
 * so isFocusableHidden never gates it. Signals (any one is enough — we err toward NOT
 * gating): an in-page hash href (#main / #content) typical of skip links; a skip-ish
 * class or text; or the canonical visually-hidden CSS recipe (clip-rect / clip-path
 * inset with a 1px box), which is the documented screen-reader-only technique.
 */
export function isIntentionalSkipLink(m) {
  if (!m || typeof m !== 'object') return false;
  const cls = String(m.className || '').toLowerCase();
  const text = String(m.text || '').toLowerCase().trim();
  const href = String(m.href || '');

  // Canonical visually-hidden recipe: a 1px clipped box. This is the screen-reader-only
  // pattern — present it and we treat the element as intentionally hidden.
  const clip = String(m.clip || '') + ' ' + String(m.clipPath || '');
  if (/\brect\(/.test(clip) || /\binset\(/.test(clip)) {
    const w = num(m.width), h = num(m.height);
    if ((w !== null && w <= 2) && (h !== null && h <= 2)) return true;
  }
  if (/\b(sr-only|visually-hidden|visuallyhidden|screen-reader|skip-link|skip-to|skiplink|skipnav)\b/.test(cls)) return true;
  if (/\bskip to\b|\bskip nav|\bskip to (main|content)/.test(text)) return true;
  // (a bare in-page anchor like <a href="#main"> with no skip wording is NOT treated as a
  // skip-link — the class/text "skip" signals above already cover the labelled cases, and
  // a hash href alone is too weak a signal to suppress a hidden-focus advisory.)
  return false;
}

/*
 * isFullyOffscreen — the element's box sits entirely outside the visible document on
 * every side (e.g. left:-9999px). We require a known viewport to judge right/bottom and
 * require the box to be fully past an edge (not merely partially scrolled out — that's
 * normal for long pages, and the tab walk scrolls focus into view anyway).
 */
export function isFullyOffscreen(m) {
  const l = num(m.rectLeft), t = num(m.rectTop), r = num(m.rectRight), b = num(m.rectBottom);
  if (l === null || t === null || r === null || b === null) return false;
  const vw = num(m.viewportWidth), vh = num(m.viewportHeight);
  // entirely past the left or top edge (the classic -9999px hide)
  if (r <= 0 || b <= 0) return true;
  // entirely past the right/bottom edge of a KNOWN viewport
  if (vw !== null && l >= vw) return true;
  if (vh !== null && t >= vh) return true;
  return false;
}

function num(x) {
  if (x === null || x === undefined || x === '') return null;
  const n = typeof x === 'number' ? x : parseFloat(x);
  return Number.isFinite(n) ? n : null;
}
