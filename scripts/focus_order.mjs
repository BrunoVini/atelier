#!/usr/bin/env node
/*
 * focus_order.mjs — rendered KEYBOARD focus-order check.
 *
 * Loads the page headless and programmatically walks the Tab sequence: press Tab from
 * the top repeatedly, recording document.activeElement at each stop (with the computed
 * metrics needed to judge it) until the focus ring cycles back to a seen element or a
 * sane cap (200 stops) is hit. Then it classifies what it found.
 *
 * ADVISORY-ONLY DISCIPLINE — this check NEVER GATES. The Stop hook gates on exit 1, and
 * the focus heuristics here are too false-positive-prone for a hook gate:
 *   • the custom-form-control pattern (a native <input type=file|checkbox|radio> hidden
 *     with opacity:0 / width:0;height:0 behind a styled <label>) is ubiquitous, fully
 *     accessible, and would otherwise be wrongly flagged `focusable-hidden`;
 *   • a closed mobile drawer hidden via transform:translateX(-100%) (links left in tab
 *     order) is the common closed-nav idiom.
 * So whenever the browser actually runs we exit 0, REPORTING (in --json / human output)
 * the observations as ADVISORY only:
 *   • `focusable-hidden` — an element that RECEIVES keyboard focus while visually hidden
 *     (zero-size box, visibility:hidden, opacity:0 and not transitioning, or positioned
 *     fully offscreen) and is NOT a legitimate skip-link / visually-hidden pattern;
 *   • tab-order vs visual-order mismatch; positive tabindex; possible focus-trap.
 *   • No focusable elements -> exit 0 (nothing to check).
 *   • No browser -> exit 3 (never gates). Crash -> exit 1 WITH the "focus_order failed:"
 *     stderr marker so _rendered() maps it to `unknown` (never a false gate).
 *
 * Usage: node focus_order.mjs <page.html|url> [--json]
 * Exit:  0 ran (clean or advisory findings) · 2 usage · 3 no browser.
 */
import path from 'node:path';
import process from 'node:process';
import { findChrome } from './lib/browser.mjs';
import { detectCycle, isFocusableHidden } from './lib/focusorder.mjs';

const input = process.argv[2];
if (!input || input.startsWith('-')) {
  console.error('usage: focus_order.mjs <page.html|url> [--json]');
  process.exit(2);
}
const asJson = process.argv.includes('--json');
const isUrl = /^https?:\/\//.test(input);
const url = isUrl ? input : 'file://' + path.resolve(input);
const VIEWPORT = { width: 1440, height: 900 };
const MAX_STOPS = 200;       // cap the Tab walk — never loop forever on a page with no ring wrap
const GOTO_MS = 20000;
const STEP_MS = 1500;        // per-Tab-press budget; the whole loop is also wall-clock capped

// Runs in the page: focus the top of the document, then return the metrics of whatever
// is focused right now. Called once per Tab press from Node (Node owns the keyboard so
// the real browser focus engine — including its skip of display:none — is exercised).
const READ_ACTIVE = `(() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) {
    return { none: true };
  }
  const cs = getComputedStyle(el);
  const r = el.getBoundingClientRect();
  // a stable-enough identity for this walk: tag + id + a couple classes + dom index
  const idx = Array.prototype.indexOf.call(document.querySelectorAll('*'), el);
  const sel = el.tagName.toLowerCase() +
    (el.id ? '#' + el.id : '') +
    (el.className && typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');
  // mid-transition? if any running transition/animation touches opacity, an opacity:0
  // reading is a transient fade, not a hidden control — don't gate it.
  let transitioning = false;
  try {
    if (document.getAnimations) {
      for (const a of el.getAnimations ? el.getAnimations() : []) {
        const p = a.effect && a.effect.getKeyframes ? a.effect.getKeyframes() : [];
        if (a.playState === 'running' && (String(a.transitionProperty || '').includes('opacity') ||
            p.some(k => 'opacity' in k))) { transitioning = true; break; }
      }
    }
  } catch {}
  return {
    none: false,
    key: idx + '|' + sel,
    sel,
    idx,
    tag: el.tagName.toLowerCase(),
    href: el.getAttribute ? (el.getAttribute('href') || '') : '',
    className: typeof el.className === 'string' ? el.className : '',
    text: (el.textContent || '').slice(0, 60),
    tabindex: el.getAttribute ? el.getAttribute('tabindex') : null,
    width: r.width, height: r.height,
    rectLeft: r.left, rectTop: r.top, rectRight: r.right, rectBottom: r.bottom,
    viewportWidth: window.innerWidth, viewportHeight: window.innerHeight,
    visibility: cs.visibility, opacity: cs.opacity,
    clip: cs.clip, clipPath: cs.clipPath, position: cs.position,
    transitioning,
    // visual order anchor: absolute document position (for tab-vs-visual advisory)
    docTop: Math.round(r.top + window.scrollY), docLeft: Math.round(r.left + window.scrollX),
  };
})()`;

// Quick census of statically-focusable elements — if there are none, there's nothing
// to walk and we exit 0 cleanly (no FP on a brochure page with no controls).
const COUNT_FOCUSABLE = `(() => {
  const sel = 'a[href], button, input:not([type=hidden]), select, textarea, ' +
    '[tabindex], [contenteditable=""], [contenteditable=true], audio[controls], video[controls], details>summary';
  let n = 0, positiveTabindex = 0;
  for (const el of document.querySelectorAll(sel)) {
    if (el.disabled) continue;
    const ti = el.getAttribute('tabindex');
    if (ti !== null && parseInt(ti, 10) > 0) positiveTabindex++;
    n++;
  }
  return { n, positiveTabindex };
})()`;

async function launch() {
  let chromium;
  try {
    ({ chromium } = await import('playwright'));
  } catch (e) {
    if (e?.code !== 'ERR_MODULE_NOT_FOUND') throw e;
    return null;   // signal: no browser
  }
  try {
    return await chromium.launch();
  } catch {
    // managed launch failed — fall back to a system Chrome. Any failure HERE (none found,
    // findChrome hiccup, second launch throws) means "no usable browser": return null so
    // main() exits 3 (unknown, never gates) rather than letting an exception escape and
    // exit 1 (which the hook would treat as a BLOCK — a false gate).
    try {
      const bin = findChrome();
      if (!bin) return null;
      return await chromium.launch({ executablePath: bin });
    } catch {
      return null;
    }
  }
}

function withTimeout(promise, ms, label) {
  let t;
  const timeout = new Promise((_, rej) => { t = setTimeout(() => rej(new Error(label + ' timed out')), ms); });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(t));
}

// Build the advisory tab-order-vs-visual-order mismatch report from the recorded stops.
// Visual order = sort by (docTop rounded to a row band, then docLeft). A mismatch is when
// the tab sequence visits stops in a meaningfully different order than reading order.
function visualOrderMismatch(stops) {
  const withPos = stops.filter(s => Number.isFinite(s.docTop) && Number.isFinite(s.docLeft));
  if (withPos.length < 3) return null;
  const band = 24;   // group rows within 24px so a single nav row isn't "out of order"
  const visual = withPos.slice().sort((a, b) => {
    const ra = Math.round(a.docTop / band), rb = Math.round(b.docTop / band);
    return ra !== rb ? ra - rb : a.docLeft - b.docLeft;
  });
  let mism = 0;
  for (let i = 0; i < withPos.length; i++) if (withPos[i].key !== visual[i].key) mism++;
  if (mism === 0) return null;
  return { mismatched_stops: mism, total: withPos.length };
}

async function main() {
  const browser = await launch();
  if (!browser) {
    console.error('⚠ focus_order: no headless browser. Install: npm i -D playwright && npx playwright install chromium');
    process.exit(3);
  }

  let exitCode = 0;
  try {
    const page = await browser.newPage({ viewport: VIEWPORT });
    await withTimeout(
      page.goto(url, { waitUntil: 'networkidle' }).catch(() => page.goto(url, { waitUntil: 'load' })),
      GOTO_MS, 'goto'
    );
    await page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});

    const census = await page.evaluate(COUNT_FOCUSABLE);
    if (!census || census.n === 0) {
      await browser.close();
      const out = { focusable_count: 0, stops: 0, hidden: [], advisories: [], finding: null };
      if (asJson) console.log(JSON.stringify(out, null, 2));
      else console.error('✓ focus_order: no focusable elements — nothing to check.');
      process.exit(0);
    }

    // Park focus at the very top of the document, before the first focusable element.
    await page.evaluate(() => {
      window.scrollTo(0, 0);
      if (document.body) document.body.focus();
      try { document.activeElement && document.activeElement.blur(); } catch {}
    });

    const stops = [];
    const seenKeys = new Set();
    const orderedKeys = [];
    const deadline = Date.now() + 60000;   // hard wall-clock cap on the whole walk
    for (let i = 0; i < MAX_STOPS; i++) {
      if (Date.now() > deadline) break;
      try {
        await withTimeout(page.keyboard.press('Tab'), STEP_MS, 'tab');
        const m = await withTimeout(page.evaluate(READ_ACTIVE), STEP_MS, 'read');
        if (!m || m.none) {
          // focus fell off (body/null) — the ring effectively ended.
          break;
        }
        orderedKeys.push(m.key);
        if (seenKeys.has(m.key)) break;   // cycled back to a seen stop -> ring complete
        seenKeys.add(m.key);
        stops.push(m);
      } catch {
        // a single flaky step must not crash the whole walk; stop the loop conservatively.
        break;
      }
    }

    await browser.close();

    const cyc = detectCycle(orderedKeys);

    // ADVISORY: stops that receive focus while visually hidden and are not a legitimate
    // skip-link / visually-hidden pattern. Reported, NEVER gated (the custom-form-control
    // and closed-drawer idioms make this too FP-prone to block a hook on).
    const hidden = stops
      .filter((s) => isFocusableHidden(s))
      .map((s) => ({
        sel: s.sel, tag: s.tag, text: (s.text || '').trim().slice(0, 40),
        width: Math.round(s.width), height: Math.round(s.height),
        visibility: s.visibility, opacity: s.opacity,
        why: hiddenWhy(s),
      }));

    // Advisories (never gate):
    const advisories = [];
    if (hidden.length) {
      advisories.push({ kind: 'focusable-hidden', count: hidden.length,
        elements: hidden,
        note: `${hidden.length} element(s) receive keyboard focus while visually hidden: ` +
          hidden.map((h) => `${h.sel} (${h.why})`).join('; ') +
          '. A keyboard user may tab to a control they cannot see — unless it is an ' +
          'intentional screen-reader skip-link or a custom form control hidden behind a ' +
          'styled label (advisory — verify, never gated).' });
    }
    if (census.positiveTabindex > 0) {
      advisories.push({ kind: 'positive-tabindex', count: census.positiveTabindex,
        note: 'positive tabindex values fight the natural DOM order (also flagged statically)' });
    }
    const vmis = visualOrderMismatch(stops);
    if (vmis) {
      advisories.push({ kind: 'tab-visual-order-mismatch', ...vmis,
        note: 'tab order differs from visual reading order (advisory — geometry heuristic, may be intentional)' });
    }
    // focus-trap suspicion: the ring closed via a repeat (cyc.cycled) but onto a SMALL
    // distinct set that does not begin at the first stop — i.e. focus kept circling a
    // sub-cycle (a modal/widget) rather than the whole page ring. A modal legitimately
    // traps focus, so this is LOW confidence and advisory only.
    if (cyc.cycled && cyc.repeatedAt > 0) {
      const repeatedKey = orderedKeys[cyc.repeatedAt];
      const trapStart = cyc.stops.indexOf(repeatedKey);
      const trappedCount = trapStart >= 0 ? cyc.stops.length - trapStart : 0;
      // a sub-cycle that doesn't start at the page's first stop AND is small (<= 8 stops)
      // looks like a contained trap rather than a normal full-page ring wrap.
      if (trapStart > 0 && trappedCount > 0 && trappedCount <= 8) {
        advisories.push({ kind: 'possible-focus-trap', confidence: 'low',
          trapped_stops: trappedCount,
          note: 'tab focus circled a small contained set rather than the whole page ring — ' +
            'a modal may legitimately trap focus (advisory only, never gated)' });
      }
    }

    const out = {
      focusable_count: census.n,
      stops: stops.length,
      cycled: cyc.cycled,
      hidden,
      advisories,
      finding: null,   // retained for shape stability; focus_order never produces a gating finding
    };

    if (asJson) {
      console.log(JSON.stringify(out, null, 2));
    } else if (advisories.length) {
      console.error(`⚠ focus_order: walked ${stops.length} focus stop(s) — advisory: ` +
        advisories.map(a => a.kind).join(', ') + '.');
    } else {
      console.error(`✓ focus_order: walked ${stops.length} focus stop(s), no advisory findings.`);
    }
    exitCode = 0;   // ADVISORY ONLY: whenever the browser ran we exit 0, never gate.
  } catch (e) {
    try { await browser.close(); } catch {}
    // crash -> exit 1 WITH the "<name> failed:" marker so _rendered() maps it to unknown
    // (never a false gate). The marker is what distinguishes a crash from a real finding.
    console.error('focus_order failed:', e?.message || e);
    process.exit(1);
  }
  process.exit(exitCode);
}

function hiddenWhy(s) {
  const w = Math.round(s.width), h = Math.round(s.height);
  if (w <= 0 || h <= 0) return `${w}x${h} box`;
  if (s.visibility === 'hidden' || s.visibility === 'collapse') return `visibility:${s.visibility}`;
  if (parseFloat(s.opacity) <= 0.01) return 'opacity:0';
  return 'positioned fully offscreen';
}

main();
