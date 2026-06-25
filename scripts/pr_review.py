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

# A handler that makes an element interactive (click/key/pointer/mouse).
_HANDLER = re.compile(r"\bon[A-Za-z]*[Cc]lick\b|\bon[A-Za-z]*[Kk]ey(?:Down|Up|Press)?\b"
                      r"|\bonclick\s*=|\bonkey\w*\s*=")
# The element tag a handler/cursor sits on, scanning back over the opening tag.
_OPENTAG = re.compile(r"<([A-Za-z][\w.-]*)")
# A CSS selector that names a button / interactive control (the kind that needs a
# focus state when newly introduced).
_BTN_SELECTOR = re.compile(r"(?:^|[\s,])\.[\w-]*(?:btn|button)[\w-]*", re.I)
_CSS_EXT = (".css", ".scss", ".sass", ".less")
_JSX_EXT = (".jsx", ".tsx", ".js", ".ts", ".mjs", ".cjs", ".vue", ".svelte", ".astro", ".html", ".htm")


def _interactive_findings(repo, touched):
    """Accessibility findings the contract lint can't see, scoped to the lines a PR
    changed. Two durable, generalizable PR-review checks:

      1. A clickable NON-button on a changed line — an element carrying a click/key
         handler (or `cursor:pointer`) that is a <div>/<span> with no role and no
         tabindex: not keyboard-focusable, no semantics. A new interactive control
         must be reachable and operable by keyboard.
      2. A NEW button/interactive CSS variant introduced by the diff whose changed
         lines define NO `:focus`/`:focus-visible` rule — a new control with no
         visible focus state (WCAG 2.4.7).

    Returns findings in the same shape as lint_repo so review() can emit them
    uniformly. Only lines the PR actually changed are inspected, so pre-existing
    interactive code on unchanged lines is never flagged (stays in the diff's scope).
    """
    out = []
    for rel, lines_changed in touched.items():
        path = os.path.join(repo, rel)
        if not os.path.isfile(path):
            continue
        try:
            src = open(path, encoding="utf-8").read().splitlines()
        except Exception:
            continue
        lc = rel.lower()

        # 1. clickable non-button on a changed line (JSX/HTML/templates)
        if lc.endswith(_JSX_EXT):
            for ln in sorted(lines_changed):
                if ln < 1 or ln > len(src):
                    continue
                line = src[ln - 1]
                interactive = bool(_HANDLER.search(line)) or "cursor: pointer" in line or "cursor:pointer" in line
                if not interactive:
                    continue
                # find the opening tag this attribute belongs to: scan this line and
                # up to a few lines back for the nearest `<tag`.
                tag = None
                for back in range(ln - 1, max(ln - 8, 0) - 1, -1):
                    m = list(_OPENTAG.finditer(src[back]))
                    if m:
                        tag = m[-1].group(1)
                        break
                if tag is None:
                    continue
                tl = tag.lower()
                # only the generic, non-focusable containers are a problem; real
                # controls (button/a/input/select/textarea) and Capitalized custom
                # components (likely already-accessible wrappers) are left alone.
                if tl not in ("div", "span", "li", "p"):
                    continue
                # within the tag's opening (this line + the small window) is there a
                # role= or a tabindex/tabIndex that would make it focusable?
                window = "\n".join(src[max(ln - 8, 0):min(ln + 2, len(src))])
                if re.search(r"\brole\s*=", window) or re.search(r"\btab[Ii]ndex\s*=", window):
                    continue
                out.append({
                    "file": rel, "line": ln, "kind": "a11y",
                    "value": f"clickable <{tag}>",
                    "severity": "blocker",
                    "fix": (f"interactive <{tag}> is not keyboard-focusable and has no control "
                            "semantics — use a <button> (or add role + tabindex=0 + a key handler) "
                            "with a visible :focus-visible state"),
                })

        # 2. a new button/interactive variant with no focus rule among changed lines
        if lc.endswith(_CSS_EXT):
            changed_text = "\n".join(src[ln - 1] for ln in sorted(lines_changed)
                                     if 1 <= ln <= len(src))
            has_focus = ":focus" in changed_text  # covers :focus and :focus-visible
            if not has_focus:
                for ln in sorted(lines_changed):
                    if ln < 1 or ln > len(src):
                        continue
                    line = src[ln - 1]
                    # a selector line that opens a button-variant block (and isn't
                    # itself a :hover/:focus/:active state selector)
                    if _BTN_SELECTOR.search(line) and "{" in line and ":" not in line.split("{")[0]:
                        out.append({
                            "file": rel, "line": ln, "kind": "a11y",
                            "value": "new interactive variant without a focus state",
                            "severity": "important",
                            "fix": ("this PR adds an interactive variant but no :focus-visible rule "
                                    "for it on the changed lines — add a visible focus state "
                                    "(WCAG 2.4.7)"),
                        })
    return out


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


def annotation(path, line, message, severity="warning"):
    # GitHub annotation level: a blocker is an ::error (fails the check), the rest
    # are ::warning. Anything not a known level falls back to a warning.
    level = "error" if severity in ("error", "blocker") else "warning"
    msg = message.replace("\n", " ")
    return f"::{level} file={path},line={line}::{msg}"


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
            out.append(annotation(rel, f["line"], f"off-contract {f['value']} → {f['fix']}",
                                   f.get("severity", "warning")))
    # accessibility findings the contract lint can't see (clickable non-button, a new
    # interactive variant with no focus state) — already scoped to changed lines.
    for f in _interactive_findings(repo, touched):
        out.append(annotation(f["file"], f["line"], f"{f['value']} — {f['fix']}", f["severity"]))
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
