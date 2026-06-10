#!/usr/bin/env node
/*
 * scan_motion.mjs — MEASURE a page's motion system (not just its colors). Renders the
 * page and extracts the @keyframes it defines, which elements animate (with duration /
 * easing / iteration), the animation libraries in use (by globals + script src), and the
 * scroll-driven patterns present (sticky, scroll-reveal, parallax hints). No tool measures
 * motion; "make it move like notion.so" needs this. Emits a motion spec as JSON.
 *
 * Usage: node scan_motion.mjs <page.html|url> [--json]
 * Exit: 0 ok, 2 usage, 3 no headless browser (same `unknown`-not-failure contract).
 */
import path from 'node:path';
import process from 'node:process';

const input = process.argv[2];
if (!input || input.startsWith('-')) {
  console.error('usage: scan_motion.mjs <page.html|url> [--json]');
  process.exit(2);
}
const asJson = process.argv.includes('--json');
const url = /^https?:\/\//.test(input) ? input : 'file://' + path.resolve(input);

async function launch() {
  try {
    const { chromium } = await import('playwright');
    const b = await chromium.launch();
    return { b, page: await b.newPage({ viewport: { width: 1440, height: 900 } }), idle: 'networkidle' };
  } catch (e1) {
    if (e1?.code !== 'ERR_MODULE_NOT_FOUND') throw e1;
    const puppeteer = (await import('puppeteer')).default;
    const b = await puppeteer.launch();
    const page = await b.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    return { b, page, idle: 'networkidle0' };
  }
}

const PROBE = `(() => {
  const sel = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    (el.className && typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.') : '');

  // @keyframes defined across all (same-origin) stylesheets.
  const keyframes = new Set();
  for (const ss of document.styleSheets) {
    let rules; try { rules = ss.cssRules; } catch { continue; }   // cross-origin -> skip
    for (const r of rules || []) if (r.type === CSSRule.KEYFRAMES_RULE) keyframes.add(r.name);
  }

  // Elements that actually animate or transition, with timing.
  const animated = [], transitions = [];
  for (const el of document.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.animationName && cs.animationName !== 'none') {
      animated.push({ sel: sel(el), name: cs.animationName,
        duration: cs.animationDuration, easing: cs.animationTimingFunction,
        iteration: cs.animationIterationCount });
      if (animated.length >= 40) break;
    }
    if (cs.transitionProperty && cs.transitionProperty !== 'none' && cs.transitionDuration !== '0s')
      transitions.push({ sel: sel(el), property: cs.transitionProperty,
        duration: cs.transitionDuration, easing: cs.transitionTimingFunction });
  }

  // Animation libraries — globals first, then <script src>.
  const libs = new Set();
  const g = window;
  if (g.gsap || g.TweenMax || g.TweenLite) libs.add('gsap');
  if (g.ScrollTrigger || (g.gsap && g.gsap.ScrollTrigger)) libs.add('gsap/ScrollTrigger');
  if (g.lottie || g.bodymovin) libs.add('lottie');
  if (g.THREE) libs.add('three');
  if (g.Motion || g.framerMotion) libs.add('framer-motion');
  if (g.AOS) libs.add('aos');
  if (g.anime) libs.add('anime');
  if (g.LocomotiveScroll) libs.add('locomotive-scroll');
  if (g.Matter) libs.add('matter-js');
  for (const s of document.querySelectorAll('script[src]')) {
    const u = (s.getAttribute('src') || '').toLowerCase();
    for (const [k, lib] of [['gsap', 'gsap'], ['scrolltrigger', 'gsap/ScrollTrigger'],
      ['lottie', 'lottie'], ['three', 'three'], ['framer', 'framer-motion'], ['aos', 'aos'],
      ['anime', 'anime'], ['locomotive', 'locomotive-scroll'], ['matter', 'matter-js']])
      if (u.includes(k)) libs.add(lib);
  }

  // Scroll-driven patterns.
  const scroll = {
    sticky: document.querySelectorAll('*[style*="sticky"], .sticky').length +
            [...document.querySelectorAll('*')].filter(e => getComputedStyle(e).position === 'sticky').length,
    aos: document.querySelectorAll('[data-aos]').length,
    locomotive: document.querySelectorAll('[data-scroll]').length,
    scroll_timeline: [...document.styleSheets].some(ss => {
      try { return [...(ss.cssRules || [])].some(r => /animation-timeline|scroll\\(|view\\(/.test(r.cssText)); }
      catch { return false; }
    }),
  };
  return { keyframes: [...keyframes], animated, transitions: transitions.slice(0, 40),
           libraries: [...libs], scroll };
})()`;

(async () => {
  let ctx;
  try { ctx = await launch(); }
  catch { console.error('⚠ scan_motion: no headless browser. Install: npm i -D playwright && npx playwright install chromium'); process.exit(3); }
  try {
    await ctx.page.goto(url, { waitUntil: ctx.idle }).catch(() => ctx.page.goto(url));
    const spec = await ctx.page.evaluate(PROBE);
    if (asJson) {
      console.log(JSON.stringify(spec, null, 2));
    } else {
      console.error(`@keyframes: ${spec.keyframes.join(', ') || '(none)'}`);
      console.error(`animated elements: ${spec.animated.length}; transitions: ${spec.transitions.length}`);
      console.error(`libraries: ${spec.libraries.join(', ') || '(none)'}`);
      console.error(`scroll: sticky=${spec.scroll.sticky} aos=${spec.scroll.aos} ` +
                    `locomotive=${spec.scroll.locomotive} scroll-timeline=${spec.scroll.scroll_timeline}`);
    }
    await ctx.b.close();
    process.exit(0);
  } catch (e) {
    try { await ctx.b.close(); } catch {}
    console.error('scan_motion failed:', e?.message || e);
    process.exit(1);
  }
})();
