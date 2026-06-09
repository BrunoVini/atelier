/*
 * electron-capture.cjs — capture a PNG of a URL using Electron's bundled Chromium.
 * Electron has no `--screenshot` CLI like Chrome and can't be a playwright/puppeteer
 * executablePath, so this tiny app is how atelier uses an Electron runtime to render.
 * It's the portability fallback for a WSL that has Electron but no Chrome.
 *
 * Run WITH the electron binary (not node):
 *   electron electron-capture.cjs <url> <out.png> [width] [height]
 *
 * Viewport-only (capturePage grabs the window, like Chrome's CLI --screenshot) —
 * true full-page needs a node driver (playwright/puppeteer).
 */
const { app, BrowserWindow } = require('electron');
const fs = require('fs');

const [, , url, out, w = '1440', h = '900'] = process.argv;

app.disableHardwareAcceleration();
app.commandLine.appendSwitch('disable-gpu');
app.commandLine.appendSwitch('no-sandbox');

if (!url || !out) {
  process.stderr.write('usage: electron electron-capture.cjs <url> <out.png> [width] [height]\n');
  app.exit(2);
}

app.whenReady().then(async () => {
  const win = new BrowserWindow({
    width: Number(w),
    height: Number(h),
    show: false,
    webPreferences: { offscreen: true, backgroundThrottling: false },
  });
  try {
    await win.loadURL(url);
    // wait for web fonts, then let async render settle (mirrors the playwright path)
    await win.webContents.executeJavaScript('document.fonts ? document.fonts.ready.then(() => true) : true').catch(() => {});
    await new Promise((r) => setTimeout(r, 2500));
    const img = await win.webContents.capturePage();
    fs.writeFileSync(out, img.toPNG());
    process.stderr.write(`✓ electron wrote ${out} (${w}x${h})\n`);
    app.exit(0);
  } catch (e) {
    process.stderr.write('electron capture failed: ' + ((e && e.message) || e) + '\n');
    app.exit(1);
  }
});
