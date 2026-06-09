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
 * Browser resolution (fast + portable — works on any machine with Chrome):
 *   1. playwright, if importable        (best: full-page, waits, fonts.ready)
 *   2. puppeteer, if importable
 *   3. a SYSTEM Chrome/Chromium binary, driven via its built-in headless
 *      `--screenshot` — ZERO npm dependencies. This is what makes the script
 *      "just work" on a fresh WSL/box that has google-chrome but no node driver.
 * The playwright/puppeteer paths also fall back to a discovered system binary as
 * `executablePath`, so they work even without `npx playwright install`.
 *
 * Overrides (env):
 *   ATELIER_SHOT_ENGINE = playwright | puppeteer | chrome   (force one path)
 *   ATELIER_CHROME / PUPPETEER_EXECUTABLE_PATH / CHROME_PATH / CHROMIUM_PATH
 *                       = explicit path to a Chrome/Chromium binary
 *
 * Degrades gracefully: if nothing is found it prints exactly what to install
 * (or which binary to point at) and exits non-zero, instead of failing opaquely.
 */
import path from 'node:path';
import process from 'node:process';
import os from 'node:os';
import { existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const [input, out, w = '1440', h = '900'] = process.argv.slice(2);
const fullPage = process.argv.includes('--full');

if (!input || !out) {
  console.error('usage: screenshot.mjs <input.html|url> <out.png> [width] [height] [--full]');
  process.exit(2);
}

const url = /^https?:\/\//.test(input) ? input : 'file://' + path.resolve(input);
const outAbs = path.resolve(out);
const viewport = { width: Number(w), height: Number(h) };

// Find a Chrome/Chromium binary without needing any node package. Checks, in
// order: explicit env paths, the PATH, the browsers playwright/puppeteer already
// cached, and (on WSL) the Windows-side Chrome.
function findChrome() {
  const c = [];
  for (const e of ['ATELIER_CHROME', 'PUPPETEER_EXECUTABLE_PATH', 'CHROME_PATH', 'CHROMIUM_PATH']) {
    if (process.env[e]) c.push(process.env[e]);
  }
  for (const n of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'microsoft-edge']) {
    const p = spawnSync('sh', ['-c', `command -v ${n} 2>/dev/null`], { encoding: 'utf8' }).stdout.trim();
    if (p) c.push(p);
  }
  const home = os.homedir();
  const pw = `${home}/.cache/ms-playwright`;
  if (existsSync(pw)) {
    for (const d of readdirSync(pw)) {
      if (d.startsWith('chromium-')) c.push(`${pw}/${d}/chrome-linux/chrome`);
    }
  }
  const pp = `${home}/.cache/puppeteer/chrome`;
  if (existsSync(pp)) {
    for (const d of readdirSync(pp)) c.push(`${pp}/${d}/chrome-linux64/chrome`);
  }
  c.push('/mnt/c/Program Files/Google/Chrome/Application/chrome.exe');
  c.push('/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe');
  return c.find((p) => p && existsSync(p)) || null;
}

async function withPlaywright() {
  const { chromium } = await import('playwright');
  let browser;
  try {
    browser = await chromium.launch();
  } catch (e) {
    const bin = findChrome();
    if (!bin) throw e; // no managed browser AND no system binary — let caller fall through
    browser = await chromium.launch({ executablePath: bin });
  }
  const page = await browser.newPage({ viewport });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});
  await page.screenshot({ path: outAbs, fullPage });
  await browser.close();
}

async function withPuppeteer() {
  const puppeteer = (await import('puppeteer')).default;
  let browser;
  try {
    browser = await puppeteer.launch();
  } catch (e) {
    const bin = findChrome();
    if (!bin) throw e;
    browser = await puppeteer.launch({ executablePath: bin });
  }
  const page = await browser.newPage();
  await page.setViewport(viewport);
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.evaluate(() => (document.fonts ? document.fonts.ready : null)).catch(() => {});
  await page.screenshot({ path: outAbs, fullPage });
  await browser.close();
}

// Zero-dependency fallback: drive a system Chrome via its built-in headless
// screenshot. No npm packages — only a browser binary. Viewport-only: the CLI
// has no true full-page mode (that needs a node driver), so we say so and capture
// the viewport rather than failing.
function withSystemChrome(bin) {
  if (fullPage) {
    console.error('⚠ system-chrome: --full (full-page) needs playwright/puppeteer; capturing the viewport instead.');
  }
  const r = spawnSync(
    bin,
    [
      '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars',
      `--screenshot=${outAbs}`,
      `--window-size=${viewport.width},${viewport.height}`,
      '--force-device-scale-factor=1',
      '--virtual-time-budget=10000', // best-effort wait for async render
      url,
    ],
    { encoding: 'utf8', timeout: 120000 },
  );
  if (r.error) throw r.error;
  if (r.status !== 0 || !existsSync(outAbs)) {
    throw new Error(`chrome --screenshot failed (exit ${r.status}): ${(r.stderr || '').slice(0, 400)}`);
  }
}

function noBrowserHelp() {
  console.error('⚠ screenshot: no headless browser found.');
  console.error('   Fastest: install Chrome/Chromium so the system path works with zero npm deps');
  console.error('     • Debian/Ubuntu/WSL: sudo apt-get install -y chromium  (or install Google Chrome)');
  console.error('     • already have one elsewhere? point at it: ATELIER_CHROME=/path/to/chrome');
  console.error('   Or install a node driver: npm i -D playwright && npx playwright install chromium');
  console.error('     (or: npm i -D puppeteer). The HTML is still valid — open it in a browser to review.');
}

const engine = process.env.ATELIER_SHOT_ENGINE;

try {
  if (engine === 'chrome') {
    const bin = findChrome();
    if (!bin) { noBrowserHelp(); process.exit(3); }
    withSystemChrome(bin);
  } else if (engine === 'puppeteer') {
    await withPuppeteer();
  } else if (engine === 'playwright') {
    await withPlaywright();
  } else {
    // auto: playwright → puppeteer → system Chrome
    try {
      await withPlaywright();
    } catch (e1) {
      if (e1?.code !== 'ERR_MODULE_NOT_FOUND') throw e1;
      try {
        await withPuppeteer();
      } catch (e2) {
        if (e2?.code !== 'ERR_MODULE_NOT_FOUND') throw e2;
        const bin = findChrome();
        if (!bin) { noBrowserHelp(); process.exit(3); }
        console.error(`→ no node browser driver installed; using system Chrome at ${bin}`);
        withSystemChrome(bin);
      }
    }
  }
  console.error(`✓ wrote ${out} (${viewport.width}x${viewport.height}${fullPage ? ', full page' : ''})`);
} catch (e) {
  if (e?.code === 'ERR_MODULE_NOT_FOUND') {
    noBrowserHelp();
    process.exit(3);
  }
  console.error('screenshot failed:', e?.message || e);
  process.exit(1);
}
