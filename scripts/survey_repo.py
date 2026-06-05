"""Architecture survey — read the existing repo before writing code into it.

Great design includes great *frontend* architecture. Before atelier adds a
component or a page to an existing repo, it should understand how that repo's UI
layer is built — styling approach, framework, client/UI state, file conventions —
and where it's weak, so the new code fits in and improves rather than degrades it.

This surfaces those signals (composed with scan_repo + census):
  - framework, component library, styling approach, client/UI state management
  - directory conventions (where components / pages / hooks / styles live)
  - oversized UI files (refactor candidates) and duplicate components (design debt)
  - flagged smells to weigh before writing

Scope: FRONTEND / design only. It looks at the UI layer (components, styles,
tokens). It deliberately does NOT inspect or judge backend code (APIs, DB,
services, business logic) — out of atelier's lane. The oversized-file scan is
restricted to UI component + style files so backend files are never flagged.

Usage:
    python3 survey_repo.py <repo> [--json] [--max-lines N]
"""
import json
import os
import sys

from scan_repo import scan_directory, _SKIP_DIRS, _STYLE_EXT
from census import build_census

# UI component files only — NOT generic .ts/.js, which are often backend.
_UI_EXT = (".jsx", ".tsx", ".vue", ".svelte", ".astro")

_BIG_FILE_LINES = 400


def _read_pkg(root):
    p = os.path.join(root, "package.json")
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _styling_approach(root, pkg, deps):
    approaches = []
    if any(os.path.exists(os.path.join(root, f"tailwind.config{e}")) for e in (".js", ".ts", ".cjs", ".mjs")) or "tailwindcss" in deps:
        approaches.append("tailwind")
    if "styled-components" in deps or "@emotion/react" in deps or "@emotion/styled" in deps:
        approaches.append("css-in-js")
    if "@stitches/react" in deps or "@vanilla-extract/css" in deps:
        approaches.append("css-in-js (compiled)")
    return approaches


def _state_mgmt(deps):
    libs = {"redux": "redux", "@reduxjs/toolkit": "redux-toolkit", "zustand": "zustand",
            "jotai": "jotai", "recoil": "recoil", "mobx": "mobx",
            "@tanstack/react-query": "react-query", "react-query": "react-query",
            "valtio": "valtio", "xstate": "xstate"}
    return sorted({name for dep, name in libs.items() if dep in deps})


def _dir_conventions(root):
    found = {}
    for marker in ("components", "pages", "app", "hooks", "lib", "utils", "styles",
                   "features", "src", "ui", "context", "store", "design"):
        for dirpath, dirnames, _ in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            if marker in dirnames:
                found[marker] = os.path.relpath(os.path.join(dirpath, marker), root)
                break
    router = "app-router" if "app" in found else ("pages-router" if "pages" in found else "unknown")
    return found, router


def _oversized(root, max_lines):
    big = []
    has_css_module = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".module.css") or fn.endswith(".module.scss"):
                has_css_module = True
            # UI components + stylesheets only — never flag backend .ts/.js files.
            if not (fn.endswith(_UI_EXT) or fn.endswith(_STYLE_EXT)):
                continue
            p = os.path.join(dirpath, fn)
            try:
                n = sum(1 for _ in open(p, encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            if n > max_lines:
                big.append({"file": os.path.relpath(p, root), "lines": n})
    big.sort(key=lambda x: x["lines"], reverse=True)
    return big[:15], has_css_module


def survey(root, max_lines=_BIG_FILE_LINES):
    scan = scan_directory(root)
    pkg = _read_pkg(root)
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    styling = _styling_approach(root, pkg, deps)
    big, has_css_module = _oversized(root, max_lines)
    if has_css_module:
        styling.append("css-modules")
    if not styling:
        styling = ["plain-css/scss"]
    dirs, router = _dir_conventions(root)
    census = build_census(root)

    smells = []
    if big:
        smells.append(f"{len(big)} file(s) over {max_lines} lines — refactor candidates if you touch them")
    if census["duplicates"]:
        smells.append(f"{len(census['duplicates'])} duplicated component name(s) — consolidate")
    if len(styling) > 2:
        smells.append(f"mixed styling approaches ({', '.join(styling)}) — pick the repo's primary and match it")
    if "components" not in dirs and census["count"] == 0:
        smells.append("no components/ dir and no components found — UI may be inlined; consider extracting")

    return {
        "framework": scan["framework"],
        "component_lib": scan["component_lib"],
        "styling": styling,
        "state_management": _state_mgmt(deps) or ["none/local"],
        "router": router,
        "dir_conventions": dirs,
        "components": census["count"],
        "duplicate_components": census["duplicates"],
        "oversized_files": big,
        "smells": smells,
    }


def _format(s):
    lines = [
        "Architecture survey:",
        f"  framework:    {s['framework']}   component lib: {s['component_lib']}",
        f"  styling:      {', '.join(s['styling'])}",
        f"  state:        {', '.join(s['state_management'])}   router: {s['router']}",
        f"  conventions:  {', '.join(f'{k}={v}' for k, v in s['dir_conventions'].items()) or '—'}",
        f"  components:   {s['components']}",
    ]
    if s["oversized_files"]:
        lines.append("  oversized (refactor candidates if touched):")
        for f in s["oversized_files"][:8]:
            lines.append(f"    {f['lines']:>5} loc  {f['file']}")
    if s["smells"]:
        lines.append("  ⚠ weigh before writing:")
        for sm in s["smells"]:
            lines.append(f"    - {sm}")
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: survey_repo.py <repo> [--json] [--max-lines N]")
        sys.exit(2)
    root = args[0]
    max_lines = int(args[args.index("--max-lines") + 1]) if "--max-lines" in args else _BIG_FILE_LINES
    s = survey(root, max_lines)
    print(json.dumps(s, indent=2) if "--json" in args else _format(s))
