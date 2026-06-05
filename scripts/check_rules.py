"""Enforce the project's house rules from DESIGN.md (§9).

A user encodes company/project conventions as rules with a machine-checkable
directive, e.g.:

    - Overlays: use a modal for any blocking choice. [forbid: flyout, popover | prefer: Modal]
    - Dense data uses the shared table. [forbid: ad-hoc table | prefer: DataTable]
    - Icon buttons need a label. [require: aria-label on icon buttons]

This parses those directives and flags occurrences of the forbidden terms in the
repo's UI files, pointing at the preferred alternative — so "no flyouts, only
modals" becomes enforceable (in review and in CI). `require:` rules are surfaced
as advisory reminders.

Usage:
    python3 check_rules.py <repo> [--design DESIGN.md] [--json]
"""
import json
import os
import re
import sys

from scan_repo import _SKIP_DIRS, _CODE_EXT, _STYLE_EXT

_FORBID = re.compile(r"\[forbid:\s*([^\]|]+?)\s*(?:\|\s*prefer:\s*([^\]]+?))?\]", re.I)
_REQUIRE = re.compile(r"\[require:\s*([^\]]+?)\]", re.I)


def parse_rules(design_md):
    """Return ({forbidden_term: prefer_or_None}, [require_text, ...])."""
    forbids, requires = {}, []
    for terms, prefer in _FORBID.findall(design_md):
        for term in (t.strip() for t in terms.split(",")):
            if term:
                forbids[term] = (prefer or "").strip() or None
    requires = [r.strip() for r in _REQUIRE.findall(design_md)]
    return forbids, requires


def scan_violations(root, forbids):
    if not forbids:
        return []
    matchers = [(term, prefer, re.compile(r"\b" + re.escape(term), re.I))
                for term, prefer in forbids.items()]
    findings = []
    design_path = os.path.realpath(os.path.join(root, "DESIGN.md"))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if not (fn.endswith(_CODE_EXT) or fn.endswith(_STYLE_EXT)):
                continue
            p = os.path.join(dirpath, fn)
            if os.path.realpath(p) == design_path:
                continue  # don't flag the rule text itself
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except Exception:
                continue
            rel = os.path.relpath(p, root)
            for i, line in enumerate(lines, 1):
                for term, prefer, rx in matchers:
                    if rx.search(line):
                        findings.append({
                            "file": rel, "line": i, "forbidden": term,
                            "prefer": prefer, "severity": "important",
                            "snippet": line.strip()[:100],
                        })
    return findings


def check(root, design_path):
    with open(design_path, encoding="utf-8") as fh:
        design_md = fh.read()
    forbids, requires = parse_rules(design_md)
    return scan_violations(root, forbids), requires, forbids


def _format(findings, requires, forbids):
    lines = []
    if not forbids and not requires:
        return "No house rules with directives found in DESIGN.md §9 (add [forbid:…|prefer:…] to enforce)."
    lines.append(f"House rules: {len(forbids)} forbid, {len(requires)} require directive(s).")
    if findings:
        lines.append(f"\n{len(findings)} violation(s):")
        for f in findings:
            tip = f" → use {f['prefer']}" if f["prefer"] else ""
            lines.append(f"  {f['file']}:{f['line']}  forbidden '{f['forbidden']}'{tip}")
            lines.append(f"      {f['snippet']}")
    else:
        lines.append("✓ no forbidden patterns found.")
    for r in requires:
        lines.append(f"  reminder (require): {r}")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: check_rules.py <repo> [--design DESIGN.md] [--json]")
        sys.exit(2)
    root = args[0]
    design = args[args.index("--design") + 1] if "--design" in args else os.path.join(root, "DESIGN.md")
    if not os.path.exists(design):
        print(f"no DESIGN.md at {design} — run generate-design-md first")
        sys.exit(2)
    findings, requires, forbids = check(root, design)
    if "--json" in args:
        print(json.dumps({"violations": findings, "require": requires}, indent=2))
    else:
        print(_format(findings, requires, forbids))
    sys.exit(1 if findings else 0)
