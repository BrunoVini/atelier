"""Import a design direction from a reference image or a live URL.

Solves the cold-start problem (a brand-new repo with no CSS) and the "make it
like *this*" brief: derive *measured* colors (and, for URLs, real fonts) from a
reference, so atelier can immediately turn them into a DESIGN.md + tokens.

Usage:
    python3 import_reference.py --image shot.png        # quantize dominant colors
    python3 import_reference.py --url https://stripe.com # read live computed styles

Image mode decodes PNG in pure Python (8-bit truecolor / truecolor-alpha) and
clusters the dominant colors perceptually (reusing scan_repo's ΔE). URL mode uses
a headless browser to read computed styles; it degrades gracefully if none.
"""
import json
import struct
import subprocess
import sys
import zlib

from scan_repo import extract_colors, _rgb_to_hex


def _decode_png(path):
    """Return (width, height, [ (r,g,b), ... ]) for an 8-bit PNG (RGB/RGBA)."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG (image mode supports PNG; convert JPG to PNG)")
    pos = 8
    width = height = bitd = colort = 0
    idat = b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, bitd, colort = struct.unpack(">IIBB", chunk[:10])
        elif ctype == b"IDAT":
            idat += chunk
        elif ctype == b"IEND":
            break
        pos += 12 + length
    if bitd != 8 or colort not in (2, 6):
        raise ValueError("unsupported PNG (need 8-bit RGB or RGBA)")
    channels = 4 if colort == 6 else 3
    raw = zlib.decompress(idat)
    stride = width * channels
    pixels, prev = [], bytearray(stride)
    i = 0
    for _ in range(height):
        ftype = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if ftype == 1:
                line[x] = (line[x] + a) & 255
            elif ftype == 2:
                line[x] = (line[x] + b) & 255
            elif ftype == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif ftype == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        prev = line
        for x in range(0, stride, channels):
            pixels.append((line[x], line[x + 1], line[x + 2]))
    return width, height, pixels


def colors_from_image(path, sample_step=7):
    w, h, pixels = _decode_png(path)
    # Quantize to a coarse grid, then perceptually cluster the dominant cells.
    hexes = []
    for idx in range(0, len(pixels), sample_step):
        r, g, b = pixels[idx]
        hexes.append(_rgb_to_hex(r - r % 16, g - g % 16, b - b % 16))
    return extract_colors(" ".join(hexes))[:8]


_NODE_COMPUTED = r"""
const url = process.argv[1];
(async () => {
  let b; try { b = await (await import('playwright')).chromium.launch(); }
  catch { b = await (await import('puppeteer')).default.launch(); }
  const p = await (b.newPage ? b.newPage() : (await b.pages())[0]);
  await p.goto(url, { waitUntil: 'load', timeout: 30000 });
  const out = await p.evaluate(() => {
    const cs = el => el ? getComputedStyle(el) : null;
    const body = cs(document.body), h1 = cs(document.querySelector('h1,h2'));
    const btn = cs(document.querySelector('button,.btn,a[role=button]'));
    return {
      background: body && body.backgroundColor, foreground: body && body.color,
      bodyFont: body && body.fontFamily, displayFont: h1 && h1.fontFamily,
      accent: btn && btn.backgroundColor,
    };
  });
  console.log(JSON.stringify(out)); await b.close();
})().catch(e => { console.error(e.message); process.exit(3); });
"""


def styles_from_url(url):
    try:
        out = subprocess.run(["node", "-e", _NODE_COMPUTED, url],
                             capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return {"error": "node not found — install Node + playwright to read URLs"}
    if out.returncode != 0:
        return {"error": out.stderr.strip() or "browser unavailable; install playwright"}
    return json.loads(out.stdout)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--image" in args:
        path = args[args.index("--image") + 1]
        colors = colors_from_image(path)
        print(json.dumps({"source": path, "dominant_colors": colors}, indent=2))
        print("\nNext: assign roles (primary/accent/bg/fg) and feed into generate-design-md.", file=sys.stderr)
    elif "--url" in args:
        url = args[args.index("--url") + 1]
        print(json.dumps({"source": url, "computed": styles_from_url(url)}, indent=2))
    else:
        print("usage: import_reference.py --image <png> | --url <url>")
        sys.exit(2)
