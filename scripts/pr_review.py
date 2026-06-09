"""atelier PR review — run the design lint but report ONLY findings on lines the
PR actually changed, in GitHub annotation format. Governance lands at the point
of change instead of flooding a legacy file's pre-existing drift.

Usage:
    git diff --unified=0 origin/main...HEAD | python3 pr_review.py <repo> [--contract <c>]
    python3 pr_review.py <repo> --base origin/main   # runs the git diff for you
"""
import os
import re
import subprocess
import sys

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_FILE = re.compile(r"^\+\+\+ b/(.+)$")


def changed_lines(diff_text):
    """Map {file: set(added/changed line numbers)} from `git diff --unified=0`."""
    out, current = {}, None
    for line in diff_text.splitlines():
        mf = _FILE.match(line)
        if mf:
            current = mf.group(1)
            out.setdefault(current, set())
            continue
        mh = _HUNK.match(line)
        if mh and current is not None:
            start = int(mh.group(1))
            count = int(mh.group(2)) if mh.group(2) is not None else 1
            for i in range(count):                       # count 0 == pure deletion -> no added lines
                out[current].add(start + i)
    return {f: lines for f, lines in out.items() if lines}


def annotation(path, line, message):
    msg = message.replace("\n", " ")
    return f"::warning file={path},line={line}::{msg}"


def review(repo, contract, diff_text):
    from lint_design import lint_repo
    touched = changed_lines(diff_text)
    out = []
    for f in lint_repo(repo, contract):
        # lint_repo already returns repo-relative paths; only relativize a stray
        # absolute one. (Relativizing an already-relative path resolves against CWD
        # and silently matches nothing — a vacuous "clean" review.)
        rel = (os.path.relpath(f["file"], repo) if os.path.isabs(f["file"]) else f["file"]).replace(os.sep, "/")
        if f["line"] in touched.get(rel, ()):  # only lines this PR changed
            out.append(annotation(rel, f["line"], f"off-contract {f['value']} → {f['fix']}"))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args:
        print("usage: pr_review.py <repo> [--contract <c>] [--base <ref>]  (or pipe a unified=0 diff on stdin)")
        sys.exit(2)
    repo = args[0]
    contract = args[args.index("--contract") + 1] if "--contract" in args else repo
    if "--base" in args:
        base = args[args.index("--base") + 1]
        proc = subprocess.run(["git", "-C", repo, "diff", "--unified=0", f"{base}...HEAD"],
                              capture_output=True, text=True)
        if proc.returncode != 0:               # bad ref / not a repo — don't pass a silent vacuous review
            sys.stderr.write(f"pr_review: git diff failed for base '{base}': {proc.stderr.strip()}\n")
            sys.exit(2)
        diff_text = proc.stdout
    else:
        diff_text = "" if sys.stdin.isatty() else sys.stdin.read()
    for line in review(repo, contract, diff_text):
        print(line)
    sys.exit(0)
