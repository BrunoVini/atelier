"""i18n/RTL lint — flag physical-direction CSS where logical properties are needed.

A site that must support RTL (Arabic/Hebrew) breaks when it uses `margin-left` /
`text-align: left` / `left:` instead of logical properties (`margin-inline-start`,
`text-align: start`, `inset-inline-start`). This flags those — but only when the
repo actually declares RTL/i18n support (or you pass --force), so LTR-only projects
aren't nagged.

Usage:
    python3 check_rtl.py <repo> [--force] [--json]
"""
import json
import os
import re
import sys

from scan_repo import _SKIP_DIRS, _CODE_EXT, _STYLE_EXT

_LOGICAL = [
    (re.compile(r"\bmargin-left\b", re.I), "margin-inline-start"),
    (re.compile(r"\bmargin-right\b", re.I), "margin-inline-end"),
    (re.compile(r"\bpadding-left\b", re.I), "padding-inline-start"),
    (re.compile(r"\bpadding-right\b", re.I), "padding-inline-end"),
    (re.compile(r"\bborder-left\b", re.I), "border-inline-start"),
    (re.compile(r"\bborder-right\b", re.I), "border-inline-end"),
    (re.compile(r"text-align\s*:\s*left\b", re.I), "text-align: start"),
    (re.compile(r"text-align\s*:\s*right\b", re.I), "text-align: end"),
    (re.compile(r"float\s*:\s*left\b", re.I), "float: inline-start"),
    (re.compile(r"float\s*:\s*right\b", re.I), "float: inline-end"),
    (re.compile(r"(?<![\w-])left\s*:", re.I), "inset-inline-start"),
    (re.compile(r"(?<![\w-])right\s*:", re.I), "inset-inline-end"),
]
_RTL_SIGNALS = re.compile(
    r'dir\s*=\s*["\']?rtl|direction\s*:\s*rtl|i18next|react-i18next|next-intl|'
    r'rtl-?css|"ar"|"he"|"fa"|"ur"', re.I)


def declares_rtl(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(_CODE_EXT) or fn.endswith(_STYLE_EXT) or fn == "package.json":
                try:
                    if _RTL_SIGNALS.search(open(os.path.join(dirpath, fn), encoding="utf-8").read()):
                        return True
                except Exception:
                    pass
    return False


def lint_rtl(root):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(_STYLE_EXT):  # physical props live in CSS/SCSS
                continue
            p = os.path.join(dirpath, fn)
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except Exception:
                continue
            rel = os.path.relpath(p, root)
            for i, line in enumerate(lines, 1):
                for rx, logical in _LOGICAL:
                    if rx.search(line):
                        findings.append({"file": rel, "line": i,
                                         "physical": rx.pattern, "use": logical})
    return findings


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: check_rtl.py <repo> [--force] [--json]")
        sys.exit(2)
    root = args[0]
    if not ("--force" in args or declares_rtl(root)):
        print("RTL/i18n not declared in this repo — skipping (use --force to lint anyway).")
        sys.exit(0)
    findings = lint_rtl(root)
    if "--json" in args:
        print(json.dumps(findings, indent=2))
    else:
        if not findings:
            print("✓ no physical-direction properties found — RTL-safe.")
        for f in findings:
            print(f"  {f['file']}:{f['line']}  physical property → use `{f['use']}`")
    sys.exit(1 if findings else 0)
