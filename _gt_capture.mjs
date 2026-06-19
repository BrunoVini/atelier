// Ground-truth design-token capture for the t25 target site.
import { chromium } from 'playwright';
import fs from 'node:fs';

const URL = process.argv[2] || 'https://stripe.com';
const OUT = process.argv[3] || '/home/bruno/Development/bruno/new-skill/tests/t25/ground_truth';
fs.mkdirSync(OUT, { recursive: true });

const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(URL, { waitUntil: 'networkidle', timeout: 45000 });
await page.waitForTimeout(1500);

// Full-page screenshot for the judges + reference
await page.screenshot({ path: `${OUT}/reference.png`, fullPage: false });
await page.screenshot({ path: `${OUT}/reference_full.png`, fullPage: true });

const data = await page.evaluate(() => {
  const rgbToHex = (s) => {
    const m = s.match(/rgba?\(([^)]+)\)/);
    if (!m) return s;
    const p = m[1].split(',').map(x => parseFloat(x.trim()));
    const [r, g, bl, a] = p;
    if (a !== undefined && a < 1) return `rgba(${r}, ${g}, ${bl}, ${a})`;
    const h = (n) => Math.round(n).toString(16).padStart(2, '0');
    return `#${h(r)}${h(g)}${h(bl)}`.toLowerCase();
  };

  // 1. Color frequency across all visible elements
  const colorFreq = {}; const bgFreq = {};
  const fontFreq = {}; const sizeFreq = {}; const weightFreq = {};
  const radiusFreq = {}; const shadowFreq = {}; const spaceFreq = {};
  const all = document.querySelectorAll('body *');
  let counted = 0;
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    counted++;
    const cs = getComputedStyle(el);
    const col = rgbToHex(cs.color);
    colorFreq[col] = (colorFreq[col] || 0) + 1;
    const bg = cs.backgroundColor;
    if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
      const bh = rgbToHex(bg); bgFreq[bh] = (bgFreq[bh] || 0) + 1;
    }
    const ff = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
    if (ff) fontFreq[ff] = (fontFreq[ff] || 0) + 1;
    sizeFreq[cs.fontSize] = (sizeFreq[cs.fontSize] || 0) + 1;
    weightFreq[cs.fontWeight] = (weightFreq[cs.fontWeight] || 0) + 1;
    if (cs.borderTopLeftRadius && cs.borderTopLeftRadius !== '0px')
      radiusFreq[cs.borderTopLeftRadius] = (radiusFreq[cs.borderTopLeftRadius] || 0) + 1;
    if (cs.boxShadow && cs.boxShadow !== 'none')
      shadowFreq[cs.boxShadow] = (shadowFreq[cs.boxShadow] || 0) + 1;
    for (const prop of ['marginTop', 'paddingTop', 'paddingLeft', 'gap']) {
      const v = cs[prop];
      if (v && v !== '0px' && /px$/.test(v)) spaceFreq[v] = (spaceFreq[v] || 0) + 1;
    }
  }

  const sortObj = (o) => Object.entries(o).sort((a, b) => b[1] - a[1]);

  // 2. Key element samples (the design system's signature pieces)
  const sample = (sel, label) => {
    const el = document.querySelector(sel);
    if (!el) return { label, sel, found: false };
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return {
      label, sel, found: true,
      text: (el.textContent || '').trim().slice(0, 40),
      color: rgbToHex(cs.color),
      bg: cs.backgroundColor === 'rgba(0, 0, 0, 0)' ? 'transparent' : rgbToHex(cs.backgroundColor),
      fontFamily: cs.fontFamily,
      fontSize: cs.fontSize,
      fontWeight: cs.fontWeight,
      lineHeight: cs.lineHeight,
      letterSpacing: cs.letterSpacing,
      borderRadius: cs.borderRadius,
      boxShadow: cs.boxShadow,
      padding: `${cs.paddingTop} ${cs.paddingRight} ${cs.paddingBottom} ${cs.paddingLeft}`,
      width: Math.round(r.width), height: Math.round(r.height),
    };
  };

  const body = getComputedStyle(document.body);
  const h1 = document.querySelector('h1');
  const samples = [
    sample('body', 'body'),
    h1 ? sample('h1', 'h1') : null,
    sample('h2', 'h2'),
    sample('p', 'paragraph'),
    sample('a', 'link'),
    sample('button', 'button'),
    sample('nav a', 'nav-link'),
  ].filter(Boolean);

  // try common Stripe button/link patterns
  const buttons = [...document.querySelectorAll('a, button')].filter(el => {
    const cs = getComputedStyle(el);
    const bg = cs.backgroundColor;
    return bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
  }).slice(0, 6).map(el => {
    const cs = getComputedStyle(el);
    return {
      text: (el.textContent || '').trim().slice(0, 30),
      tag: el.tagName.toLowerCase(),
      bg: rgbToHex(cs.backgroundColor),
      color: rgbToHex(cs.color),
      borderRadius: cs.borderRadius,
      fontWeight: cs.fontWeight, fontSize: cs.fontSize,
      padding: `${cs.paddingTop} ${cs.paddingRight} ${cs.paddingBottom} ${cs.paddingLeft}`,
    };
  });

  return {
    url: location.href,
    title: document.title,
    elementsCounted: counted,
    body: { bg: rgbToHex(body.backgroundColor), color: rgbToHex(body.color), font: body.fontFamily, baseSize: body.fontSize },
    topColors: sortObj(colorFreq).slice(0, 25),
    topBackgrounds: sortObj(bgFreq).slice(0, 25),
    topFonts: sortObj(fontFreq).slice(0, 12),
    topSizes: sortObj(sizeFreq).slice(0, 18),
    topWeights: sortObj(weightFreq).slice(0, 10),
    topRadii: sortObj(radiusFreq).slice(0, 12),
    topShadows: sortObj(shadowFreq).slice(0, 10),
    topSpacing: sortObj(spaceFreq).slice(0, 20),
    keySamples: samples,
    filledButtons: buttons,
  };
});

fs.writeFileSync(`${OUT}/ground_truth.json`, JSON.stringify(data, null, 2));
console.log('Captured', data.url, '|', data.title);
console.log('elements:', data.elementsCounted);
console.log('body:', JSON.stringify(data.body));
console.log('topColors:', JSON.stringify(data.topColors.slice(0, 8)));
console.log('topBackgrounds:', JSON.stringify(data.topBackgrounds.slice(0, 8)));
console.log('topFonts:', JSON.stringify(data.topFonts.slice(0, 5)));
console.log('topRadii:', JSON.stringify(data.topRadii.slice(0, 6)));
console.log('filledButtons:', JSON.stringify(data.filledButtons.slice(0, 4)));
await b.close();
