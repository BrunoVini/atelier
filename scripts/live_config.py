"""Live-mode config utilities — drift-heal scan for orphan HTML files.

find_orphan_html scans project_dir for .html files not covered by the list of
files the proxy is already injecting into. Called at proxy start-up to warn the
agent about pages live mode can't see. Never mutates anything.
"""
import json, os, sys

_HARD_EXCLUDE = {"node_modules", ".git", ".svn", "dist", "build", ".next", ".nuxt", ".astro"}


def find_orphan_html(project_dir, injected_files):
    """Return HTML files in project_dir not in injected_files.

    injected_files: list of absolute paths already being injected.
    Skips node_modules, .git, and other build artifacts.
    Returns {orphans: [str], count: int, hint: str}.
    """
    injected = {os.path.realpath(p) for p in (injected_files or [])}
    orphans = []
    for dirpath, dirnames, filenames in os.walk(project_dir):
        # Prune excluded dirs in-place (prevents os.walk from descending)
        rel = os.path.relpath(dirpath, project_dir)
        top = rel.split(os.sep)[0] if rel != '.' else ''
        if top in _HARD_EXCLUDE:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in _HARD_EXCLUDE and not d.startswith('.')]
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            full = os.path.realpath(os.path.join(dirpath, fname))
            if full not in injected:
                orphans.append(os.path.relpath(full, project_dir))
    count = len(orphans)
    hint = (
        f"{count} HTML file(s) found in project that aren't covered by the proxy inject. "
        f"Live mode won't see: {', '.join(orphans[:3])}"
        + (" …" if count > 3 else "")
    ) if count else "All HTML files are covered."
    return {"orphans": orphans, "count": count, "hint": hint}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Drift-heal scan")
    ap.add_argument("project_dir")
    ap.add_argument("--injected", default="[]", help="JSON array of injected file paths")
    ns = ap.parse_args()
    injected = json.loads(ns.injected)
    print(json.dumps(find_orphan_html(ns.project_dir, injected)))
