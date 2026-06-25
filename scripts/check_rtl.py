"""i18n/RTL lint — flag physical-direction CSS where logical properties are needed.

A site that must support RTL (Arabic/Hebrew) breaks when it uses `margin-left` /
`text-align: left` / `left:` instead of logical properties (`margin-inline-start`,
`text-align: start`, `inset-inline-start`). This flags those — but only when the
repo actually declares RTL/i18n support (or you pass --force), so LTR-only projects
aren't nagged.

It scans CSS/SCSS/SASS/LESS **and** HTML (the most common RTL deliverable is a single
`page.html` whose physical-direction CSS lives in an inline `<style>` block or a
`style="…"` attribute — those must be linted too, not silently passed).

Usage:
    python3 check_rtl.py <repo-or-file> [--force] [--json]
"""
import json
import os
import re
import sys

from scan_repo import _SKIP_DIRS, _CODE_EXT, _STYLE_EXT

# Files whose text can carry CSS directional properties. HTML carries them in inline
# <style> blocks and style="" attributes, so it must be linted like a stylesheet.
_MARKUP_EXT = (".html", ".htm", ".vue", ".svelte", ".astro")

_LOGICAL = [
    (re.compile(r"\bmargin-left\b", re.I), "margin-inline-start"),
    (re.compile(r"\bmargin-right\b", re.I), "margin-inline-end"),
    (re.compile(r"\bpadding-left\b", re.I), "padding-inline-start"),
    (re.compile(r"\bpadding-right\b", re.I), "padding-inline-end"),
    (re.compile(r"\bborder-left\b", re.I), "border-inline-start"),
    (re.compile(r"\bborder-right\b", re.I), "border-inline-end"),
    # logical border-radius corners (scan BEFORE the bare left:/right: rule so the
    # corner name isn't shadowed by it)
    (re.compile(r"\bborder-top-left-radius\b", re.I), "border-start-start-radius"),
    (re.compile(r"\bborder-top-right-radius\b", re.I), "border-start-end-radius"),
    (re.compile(r"\bborder-bottom-left-radius\b", re.I), "border-end-start-radius"),
    (re.compile(r"\bborder-bottom-right-radius\b", re.I), "border-end-end-radius"),
    # scroll-* directional variants
    (re.compile(r"\bscroll-margin-left\b", re.I), "scroll-margin-inline-start"),
    (re.compile(r"\bscroll-margin-right\b", re.I), "scroll-margin-inline-end"),
    (re.compile(r"\bscroll-padding-left\b", re.I), "scroll-padding-inline-start"),
    (re.compile(r"\bscroll-padding-right\b", re.I), "scroll-padding-inline-end"),
    (re.compile(r"text-align\s*:\s*left\b", re.I), "text-align: start"),
    (re.compile(r"text-align\s*:\s*right\b", re.I), "text-align: end"),
    (re.compile(r"float\s*:\s*left\b", re.I), "float: inline-start"),
    (re.compile(r"float\s*:\s*right\b", re.I), "float: inline-end"),
    (re.compile(r"clear\s*:\s*left\b", re.I), "clear: inline-start"),
    (re.compile(r"clear\s*:\s*right\b", re.I), "clear: inline-end"),
    # bare positional insets — must come LAST so the *-left/*-right property names above
    # (margin-left, scroll-margin-left, border-top-left-radius, …) match their own rule
    # first. The negative lookbehind keeps `margin-left:` etc. from also tripping this.
    (re.compile(r"(?<![\w-])left\s*:", re.I), "inset-inline-start"),
    (re.compile(r"(?<![\w-])right\s*:", re.I), "inset-inline-end"),
]
_RTL_SIGNALS = re.compile(
    r'dir\s*=\s*["\']?rtl|direction\s*:\s*rtl|i18next|react-i18next|next-intl|'
    r'rtl-?css|"ar"|"he"|"fa"|"ur"', re.I)


def _classify(line):
    """Return the logical-property suggestions a single line of CSS/markup trips.

    Each physical pattern is checked at most once per line, and only the FIRST matching
    rule per physical property wins (so `border-top-left-radius` reports the corner fix,
    not also the bare `left:` inset)."""
    hits = []
    consumed = []  # (start, end) spans already claimed by a more-specific rule
    for rx, logical in _LOGICAL:
        for m in rx.finditer(line):
            span = m.span()
            # skip if this match sits inside a span a more-specific earlier rule claimed
            if any(span[0] >= s and span[1] <= e for s, e in consumed):
                continue
            hits.append((rx.pattern, logical))
            consumed.append(span)
            break  # one report per physical pattern per line is enough
    return hits


def check_html(text):
    """Lint a CSS/HTML string directly. Returns a list of {line, physical, use}.

    Handy for a single-file page: `check_html(open('page.html').read())`."""
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        for pattern, logical in _classify(line):
            findings.append({"line": i, "physical": pattern, "use": logical})
    return findings


_BDI_RE = re.compile(r"<bdi\b[^>]*>.*?</bdi>", re.I | re.S)


def lint_bidi_runs(text):
    """Flag the fragment-bidi anti-pattern.

    A `<bdi>`/isolate around a FRAGMENT (with loose visible text on the SAME line) floats
    to the wrong end under `dir="rtl"`. The fix is to isolate the WHOLE logical run as one
    `<bdi>` with no loose neighbour text. We only inspect a line that contains a `<bdi>`;
    if, after removing the `<bdi>…</bdi>` islands and all other tags, any visible text
    remains on that line, the isolate is a fragment (its neighbours are loose) → flag it.
    Whole-run isolation (the bdi IS the whole run, nothing loose beside it) is clean.
    """
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if "<bdi" not in line.lower():
            continue
        rest = _BDI_RE.sub("", line)          # drop the isolated islands
        rest = re.sub(r"<[^>]+>", "", rest)   # drop remaining tags
        rest = re.sub(r"&[a-z]+;", "", rest, flags=re.I)  # drop entities (e.g. &lt;)
        if rest.strip():                      # loose visible text remained beside the bdi
            out.append({"line": i,
                        "issue": "fragment-bdi: <bdi> isolates a fragment with loose text "
                                 "on the same line — isolate the WHOLE run instead "
                                 "(it will reorder to the wrong end under dir=rtl)"})
    return out


def declares_rtl(root):
    if os.path.isfile(root):
        try:
            return bool(_RTL_SIGNALS.search(open(root, encoding="utf-8").read()))
        except Exception:
            return False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if (fn.endswith(_CODE_EXT) or fn.endswith(_STYLE_EXT)
                    or fn.endswith(_MARKUP_EXT) or fn == "package.json"):
                try:
                    if _RTL_SIGNALS.search(open(os.path.join(dirpath, fn), encoding="utf-8").read()):
                        return True
                except Exception:
                    pass
    return False


def _lint_file(p, root):
    try:
        lines = open(p, encoding="utf-8").read().splitlines()
    except Exception:
        return []
    rel = os.path.relpath(p, root) if os.path.isdir(root) else os.path.basename(p)
    out = []
    for i, line in enumerate(lines, 1):
        for pattern, logical in _classify(line):
            out.append({"file": rel, "line": i, "physical": pattern, "use": logical})
    return out


def lint_rtl(root):
    # physical props live in CSS/SCSS AND in HTML (inline <style> / style="" attrs)
    exts = _STYLE_EXT + _MARKUP_EXT
    if os.path.isfile(root):
        return _lint_file(root, root) if root.endswith(exts) else []
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(exts):
                continue
            findings.extend(_lint_file(os.path.join(dirpath, fn), root))
    return findings


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: check_rtl.py <repo-or-file> [--force] [--json]")
        sys.exit(2)
    root = args[0]
    if not ("--force" in args or declares_rtl(root)):
        print("RTL/i18n not declared here — skipping (use --force to lint anyway).")
        sys.exit(0)
    findings = lint_rtl(root)
    # bidi fragment-isolation advisory (single file only — needs the markup text)
    bidi = []
    if os.path.isfile(root) and root.endswith(_MARKUP_EXT):
        try:
            bidi = lint_bidi_runs(open(root, encoding="utf-8").read())
        except Exception:
            bidi = []
    if "--json" in args:
        print(json.dumps({"physical": findings, "bidi": bidi}, indent=2))
    else:
        if not findings:
            print("✓ no physical-direction properties found — RTL-safe.")
        for f in findings:
            print(f"  {f['file']}:{f['line']}  physical property → use `{f['use']}`")
        for b in bidi:
            print(f"  bidi advisory line {b['line']}: {b['issue']}")
    sys.exit(1 if findings else 0)
