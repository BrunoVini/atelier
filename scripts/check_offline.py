"""atelier offline-safety check — does a self-contained artifact actually boot offline?

A prototype / app mockup is judged on the one bar it most easily fails: it must open
correctly by double-click with NO network. A single runtime fetch (a Google-Fonts
`<link>`, a CDN `<script src>`, a `@font-face` whose src is an http URL, an `<img>` from
a remote host) means the artifact reaches out on load: offline it fails that request,
logs a console error, and renders with the wrong type / a blank image. That is a real,
measurable violation of "boots offline" — not a nitpick — and the t08 battery proved a
blind judge weighs it heavily on the brief's #1 hard requirement.

`external_refs(html)` returns the runtime-network references it finds (pure, testable).
It flags only references the BROWSER FETCHES ON LOAD:
  - <link href=http(s)/protocol-relative>   (stylesheet / preconnect / preload / dns-prefetch)
  - <script src=http…>, and <img/iframe/source/video/audio/track/embed/object src|data=http…>
  - CSS `url(http…)` / `@import "http…"` (in <style>, inline style attrs, anywhere)
  - JS `fetch("http…")`, `import("http…")`, `import … from "http…"`
It does NOT flag things the browser never fetches on load:
  - `data:` URIs (inlined — the whole point)
  - XML namespaces (`xmlns="http://www.w3.org/2000/svg"`, xlink) — declarations, never fetched
  - `<a href="http…">` hyperlinks — navigation on click, not a load-time fetch
"""
import re
import sys

# scheme tells for "the browser will go to the network": absolute http(s) or protocol-relative //host.
_EXT = r"""(?:https?:)?//"""           # https://  http://  //cdn…
_NAMESPACE_HOSTS = ("www.w3.org", "www.w3.org/2000/svg", "www.w3.org/1999/xlink",
                    "www.w3.org/1999/xhtml", "schema.org", "purl.org/dc")

# resource tags whose src/data the browser fetches on load (NOT <a>/<area> — those navigate on click)
_SRC_TAGS = ("script", "img", "iframe", "source", "video", "audio", "track", "embed", "object")


def _is_namespace(url):
    u = url.lower().lstrip("/")
    if u.startswith("http://") or u.startswith("https://"):
        u = u.split("://", 1)[1]
    return any(u.startswith(h) for h in _NAMESPACE_HOSTS)


def _attr(tag_html, name):
    m = re.search(rf"""{name}\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))""", tag_html, re.I)
    if not m:
        return None
    return (m.group(2) or m.group(3) or m.group(4) or "").strip()


def _external(url):
    """True if this URL value is a load-time network fetch (absolute http(s) or // host),
    excluding data:/about: and XML-namespace declaration URLs."""
    if not url:
        return False
    u = url.strip()
    if u.lower().startswith(("data:", "about:", "blob:", "#", "javascript:", "mailto:", "tel:")):
        return False
    if re.match(_EXT, u, re.I) and not _is_namespace(u):
        return True
    return False


def external_refs(html):
    """Return a list of {kind, url, snippet} runtime-network references (deduped, ordered)."""
    found = []
    seen = set()

    def add(kind, url, snippet):
        key = (kind, url)
        if url and key not in seen:
            seen.add(key)
            found.append({"kind": kind, "url": url, "snippet": snippet.strip()[:120]})

    # <link href=…> — resources (stylesheet/preload/preconnect/dns-prefetch/prefetch), never anchors
    for m in re.finditer(r"<link\b[^>]*>", html, re.I):
        href = _attr(m.group(0), "href")
        if _external(href):
            rel = (_attr(m.group(0), "rel") or "").lower() or "link"
            add(f"link[{rel}]", href, m.group(0))

    # resource tags with src= / data=
    for tag in _SRC_TAGS:
        for m in re.finditer(rf"<{tag}\b[^>]*>", html, re.I):
            for attr in ("src", "data"):
                val = _attr(m.group(0), attr)
                if _external(val):
                    add(f"{tag}[{attr}]", val, m.group(0))

    # CSS url(…) anywhere (style blocks, inline style attrs, @font-face src)
    for m in re.finditer(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", html, re.I):
        if _external(m.group(1)):
            add("css-url", m.group(1).strip(), m.group(0))

    # @import "…"  (without url())
    for m in re.finditer(r"""@import\s+['"]([^'"]+)['"]""", html, re.I):
        if _external(m.group(1)):
            add("css-import", m.group(1).strip(), m.group(0))

    # JS fetch("…") / import("…") / import … from "…"
    for m in re.finditer(r"""\b(?:fetch|import)\s*\(\s*['"]([^'"]+)['"]""", html, re.I):
        if _external(m.group(1)):
            add("js-fetch", m.group(1).strip(), m.group(0))
    for m in re.finditer(r"""\bimport\b[^;{]*?\bfrom\s*['"]([^'"]+)['"]""", html, re.I):
        if _external(m.group(1)):
            add("js-import", m.group(1).strip(), m.group(0))

    return found


def main(argv):
    if not argv:
        print("usage: check_offline.py <artifact.html>", file=sys.stderr)
        return 2
    path = argv[0]
    try:
        html = open(path, encoding="utf-8").read()
    except Exception as e:
        print(f"::error:: check_offline could not read {path}: {e}", file=sys.stderr)
        return 2
    refs = external_refs(html)
    if not refs:
        print(f"offline-safe: {path} has 0 runtime network references (boots offline).")
        return 0
    print(f"NOT offline-safe: {path} reaches the network on load ({len(refs)} reference(s)):")
    for r in refs:
        print(f"  - {r['kind']}: {r['url']}")
    print("Inline these (base64 woff2 fonts / data: images) or use a system-font stack — "
          "a single runtime fetch white-screens or mis-renders the artifact offline.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
