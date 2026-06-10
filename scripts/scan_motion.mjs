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

  // @keyframes (name -> cssText so "make it move like X" can reproduce it), recursing into
  // @media/@supports groups — atelier's own reduced-motion pattern wraps keyframes there.
  const keyframes = {};
  let crossOrigin = 0;
  const walk = (rules) => {
    for (const r of rules || []) {
      if (r.type === CSSRule.KEYFRAMES_RULE) keyframes[r.name] = r.cssText;
      else if (r.cssRules) { try { walk(r.cssRules); } catch {} }
    }
  };
  for (const ss of document.styleSheets) {
    let rules; try { rules = ss.cssRules; } catch { crossOrigin++; continue; }   // cross-origin
    walk(rules);
  }

  // Elements that animate/transition (timing), and sticky count — one pass, independent caps.
  const animated = [], transitions = [];
  let sticky = 0;
  for (const el of document.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.position === 'sticky') sticky++;
    if (cs.animationName && cs.animationName !== 'none' && animated.length < 40)
      animated.push({ sel: sel(el), name: cs.animationName,
        duration: cs.animationDuration, easing: cs.animationTimingFunction,
        iteration: cs.animationIterationCount });
    if (cs.transitionProperty && cs.transitionProperty !== 'none' && cs.transitionDuration !== '0s'
        && transitions.length < 40)
      transitions.push({ sel: sel(el), property: cs.transitionProperty,
        duration: cs.transitionDuration, easing: cs.transitionTimingFunction });
  }
  const truncated = animated.length >= 40 || transitions.length >= 40;

  // Animation libraries — SHAPE-checked globals (a global named Motion/AOS isn't proof),
  // then filename-boundary <script src> (not bare substrings: 'chaos.js' ≠ aos).
  const libs = new Set();
  const g = window;
  const get = (k) => { try { return g[k]; } catch { return undefined; } };
  if (get('gsap')?.to || get('TweenMax') || get('TweenLite')) libs.add('gsap');
  if (get('ScrollTrigger')?.create || get('gsap')?.ScrollTrigger) libs.add('gsap/ScrollTrigger');
  if (typeof get('lottie')?.loadAnimation === 'function' || get('bodymovin')) libs.add('lottie');
  if (get('THREE')?.Scene) libs.add('three');
  if (typeof get('Motion')?.animate === 'function' || get('framerMotion')) libs.add('framer-motion');
  if (typeof get('AOS')?.init === 'function') libs.add('aos');
  if (typeof get('anime') === 'function' || typeof get('anime')?.timeline === 'function') libs.add('anime');
  if (typeof get('LocomotiveScroll') === 'function') libs.add('locomotive-scroll');
  if (get('Matter')?.Engine) libs.add('matter-js');
  for (const s of document.querySelectorAll('script[src]')) {
    const u = ((s.getAttribute('src') || '').toLowerCase().split('?')[0].split('/').pop()) || '';
    if (/(^|\\W)gsap(\\W|$)/.test(u)) libs.add('gsap');
    if (/scrolltrigger/.test(u)) libs.add('gsap/ScrollTrigger');
    if (/(^|\\W)lottie(\\W|$)/.test(u)) libs.add('lottie');
    if (/(^|\\W)three(\\.min|\\.module|\\.core)?\\.js$/.test(u)) libs.add('three');
    if (/framer-motion|(^|\\W)motion(\\.min)?\\.js$/.test(u)) libs.add('framer-motion');
    if (/(^|\\W)aos(\\.min)?\\.js$/.test(u)) libs.add('aos');
    if (/(^|\\W)anime(\\.min|\\.es)?\\.js$/.test(u)) libs.add('anime');
    if (/locomotive/.test(u)) libs.add('locomotive-scroll');
    if (/(^|\\W)matter(\\.min)?\\.js$/.test(u)) libs.add('matter-js');
  }

  const scroll = {
    sticky,
    aos: document.querySelectorAll('[data-aos]').length,
    locomotive: document.querySelectorAll('[data-scroll]').length,
    scroll_timeline: [...document.styleSheets].some(ss => {
      try { return [...(ss.cssRules || [])].some(r => /animation-timeline|scroll\\(|view\\(/.test(r.cssText)); }
      catch { return false; }
    }),
  };
  return { keyframes, animated, transitions, libraries: [...libs], scroll, truncated,
           crossOriginSheets: crossOrigin };
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
      console.error(`@keyframes: ${Object.keys(spec.keyframes).join(', ') || '(none)'}`);
      console.error(`animated elements: ${spec.animated.length}${spec.truncated ? '+' : ''}; transitions: ${spec.transitions.length}` +
                    (spec.crossOriginSheets ? `  (${spec.crossOriginSheets} cross-origin sheet(s) not read)` : ''));
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
