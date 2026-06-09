/*
 * browser.mjs — shared headless-browser discovery for atelier's capture/introspection
 * scripts (screenshot.mjs, chart_legibility.mjs, …). One source of truth so the
 * discovery logic can't drift between scripts.
 *
 *   findChrome()   → a Chrome/Chromium binary path, or null. Drives the zero-dep
 *                    `--headless --screenshot` CLI AND serves as executablePath for
 *                    playwright/puppeteer when their managed browser is absent.
 *   findElectron() → an Electron binary path, or null. Electron is NOT a Chrome-CLI
 *                    drop-in and NOT a valid playwright/puppeteer executablePath — it
 *                    captures only via the bundled electron-capture.cjs wrapper. It's
 *                    the portability fallback for a WSL that has Electron but no Chrome.
 *
 * Preference is the caller's: capture scripts try playwright/puppeteer → system Chrome
 * (simpler, native) → Electron (needs the wrapper) last.
 */
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { existsSync, readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const which = (n) => spawnSync('sh', ['-c', `command -v ${n} 2>/dev/null`], { encoding: 'utf8' }).stdout.trim();

export function findChrome() {
  const c = [];
  for (const e of ['ATELIER_CHROME', 'PUPPETEER_EXECUTABLE_PATH', 'CHROME_PATH', 'CHROMIUM_PATH'])
    if (process.env[e]) c.push(process.env[e]);
  for (const n of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome', 'microsoft-edge']) {
    const p = which(n); if (p) c.push(p);
  }
  const pw = `${os.homedir()}/.cache/ms-playwright`;
  if (existsSync(pw)) for (const d of readdirSync(pw)) if (d.startsWith('chromium-')) c.push(`${pw}/${d}/chrome-linux/chrome`);
  const pp = `${os.homedir()}/.cache/puppeteer/chrome`;
  if (existsSync(pp)) for (const d of readdirSync(pp)) c.push(`${pp}/${d}/chrome-linux64/chrome`);
  c.push('/mnt/c/Program Files/Google/Chrome/Application/chrome.exe');
  c.push('/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe');
  return c.find((p) => p && existsSync(p)) || null;
}

export function findElectron() {
  const c = [];
  if (process.env.ATELIER_ELECTRON) c.push(process.env.ATELIER_ELECTRON);
  const p = which('electron'); if (p) c.push(p);
  // node_modules/electron/dist/electron, walking up from cwd (covers monorepos)
  let dir = process.cwd();
  for (let i = 0; i < 6; i++) {
    c.push(path.join(dir, 'node_modules/electron/dist/electron'));
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return c.find((x) => x && existsSync(x)) || null;
}
