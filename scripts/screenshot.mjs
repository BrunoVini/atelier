#!/usr/bin/env node
/*
 * screenshot.mjs — capture a PNG of an HTML page (local file or URL) so the
 * studio can *look at* a layout and score it, the way a designer reviews a comp.
 *
 * Usage:
 *   node screenshot.mjs <input.html|url> <out.png> [width] [height] [--full]
 *
 * Examples:
 *   node screenshot.mjs landing.html shot.png 1440 900
 *   node screenshot.mjs http://localhost:52341 shot.png 1440 900 --full
 *
 * Degrades gracefully: if no headless browser is installed it prints exactly
 * what to install and exits non-zero, instead of failing opaquely.
 */
import path from 'node:path';
import process from 'node:process';

const [input, out, w = '1440', h = '900'] = process.argv.slice(2);
const fullPage = process.argv.includes('--full');

if (!input || !out) {
  console.error('usage: screenshot.mjs <input.html|url> <out.png> [width] [height] [--full]');
  process.exit(2);
}

const url = /^https?:\/\//.test(input) ? input : 'file://' + path.resolve(input);
const viewport = { width: Number(w), height: Number(h) };

async function withPlaywright() {
  const { chromium } = await import('playwright');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});
  await page.screenshot({ path: out, fullPage });
  await browser.close();
}

async function withPuppeteer() {
  const puppeteer = (await import('puppeteer')).default;
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport(viewport);
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});
  await page.screenshot({ path: out, fullPage });
  await browser.close();
}

try {
  try {
    await withPlaywright();
  } catch (e1) {
    if (e1?.code !== 'ERR_MODULE_NOT_FOUND') throw e1;
    await withPuppeteer();
  }
  console.error(`✓ wrote ${out} (${viewport.width}x${viewport.height}${fullPage ? ', full page' : ''})`);
} catch (e) {
  if (e?.code === 'ERR_MODULE_NOT_FOUND') {
    console.error('⚠ screenshot: no headless browser found.');
    console.error('   Install one: npm i -D playwright && npx playwright install chromium');
    console.error('   (or: npm i -D puppeteer). The HTML is still valid — open it in a browser to review.');
    process.exit(3);
  }
  console.error('screenshot failed:', e?.message || e);
  process.exit(1);
}
