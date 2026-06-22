"""Static accessibility audit (stdlib `html.parser` only).

A defensive, low-false-positive WCAG smoke test over a single HTML document or
fragment. `check_a11y(html) -> [findings]` returns the codebase's standard
finding shape — ``{"severity", "kind", "detail"}`` (+ optional ``line``) — so it
rides suppressions, SARIF, and register modulation for free.

Severity discipline (per the gate's contract): an ``important`` finding only
fires on an UNAMBIGUOUS violation (an image with no alt at all, a form control
with no accessible name, an icon-only control with no name). Everything
heuristic — landmarks, h1 count, positive tabindex — is ``polish`` (advisory).
A present-but-empty ``alt=""`` is VALID (decorative) and is never flagged.

Rules (WCAG success criteria cited informally in the detail):
  • img-missing-alt        important  (1.1.1)
  • input-missing-label    important  (1.3.1 / 4.1.2 / 3.3.2)
  • control-missing-name   important  (2.4.4 / 4.1.2)
  • missing-landmarks      polish     (1.3.1 / 2.4.1)
  • no-h1 / multiple-h1    polish     (1.3.1 / 2.4.6)
  • positive-tabindex      polish     (2.4.3)

Usage:
    python3 a11y_check.py <page.html> [--json]
"""
import json
import sys
from html.parser import HTMLParser

# Void elements never carry text content / close themselves.
_VOID = {"img", "br", "hr", "input", "meta", "link", "source", "area",
         "base", "col", "embed", "track", "wbr"}

# Form-control input types that DON'T need an associated label:
#  hidden            — not perceivable;
#  submit/button     — accessible name comes from `value` (or text);
#  image             — accessible name comes from `alt`;
# everything else (text, email, checkbox, radio, range, …) needs a name.
_INPUT_NO_LABEL_NEEDED = {"hidden", "submit", "button", "image"}

# Tokens (tag or role) that count as a document landmark.
_LANDMARK_TAGS = {"main", "header", "footer", "nav"}
_LANDMARK_ROLES = {"main", "navigation", "banner", "contentinfo"}

# Checkable ARIA widget roles: each REQUIRES aria-checked (an explicit role
# overrides a native control's :checked, so the state must be on the ARIA layer).
_ARIA_CHECKED_ROLES = {"switch", "checkbox", "radio",
                       "menuitemcheckbox", "menuitemradio"}


def _attr_map(attrs):
    """Fold an HTMLParser (name, value) attr list to a dict; later wins.
    A boolean attribute (value None) maps to "" so presence is detectable."""
    out = {}
    for k, v in attrs:
        out[k.lower()] = (v if v is not None else "")
    return out


def _has(attrs, name):
    """True iff the attribute is present at all (even empty/boolean)."""
    return any(k.lower() == name for k, _ in attrs)


def _nonblank(attrs, name):
    """True iff the attribute is present AND has non-whitespace text."""
    return bool((_attr_map(attrs).get(name) or "").strip())


def _has_aria_name(am):
    """An accessible name from ARIA / title attributes (not from content)."""
    return bool((am.get("aria-label") or "").strip()
                or (am.get("aria-labelledby") or "").strip()
                or (am.get("title") or "").strip())


def _is_hidden_img(am):
    """An <img> exempt from alt: aria-hidden or a presentational role."""
    if (am.get("aria-hidden") or "").strip().lower() == "true":
        return True
    role = (am.get("role") or "").strip().lower()
    return role in ("presentation", "none")


class _A11yWalk(HTMLParser):
    """Single-pass walk collecting everything the rules need.

    Two-phase: collect raw events + ``<label for=...>`` targets during the walk,
    then resolve control-name rules after parsing (a label can appear before OR
    after the control it names, so association can't be decided inline)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.findings = []
        # document-shape signals
        self.has_body = False
        self.has_landmark = False
        self.h1_count = 0
        # control bookkeeping resolved post-parse
        self.label_for = set()          # ids targeted by <label for=ID>
        self.controls = []              # (tag, am, line) needing a name decision
        # stacks for content-bearing controls (button / a / label)
        self._ctrl_stack = []           # frames: dict with tag/am/line/text/inner
        self._label_depth = 0           # >0 ⇒ inside a <label> (wraps a control)

    # --- helpers -----------------------------------------------------------
    def _line(self):
        # getpos() is 1-based line, 0-based col; report the 1-based line.
        return self.getpos()[0]

    def _add(self, sev, kind, detail, line=None):
        f = {"severity": sev, "kind": kind, "detail": detail}
        if line is not None:
            f["line"] = line
        self.findings.append(f)

    # --- parser events -----------------------------------------------------
    def handle_starttag(self, tag, attrs):
        self._on_open(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        # An explicit self-closing tag (<img/>, <input/>): open + immediate close.
        self._on_open(tag, attrs, self_closing=True)

    def _on_open(self, tag, attrs, self_closing):
        am = _attr_map(attrs)
        line = self._line()

        # positive-tabindex — any element, any phase (polish).
        tabindex = (am.get("tabindex") or "").strip()
        if tabindex.lstrip("+").lstrip("-").isdigit():
            try:
                if int(tabindex) > 0:
                    self._add("polish", "positive-tabindex",
                              f"<{tag}> has tabindex={tabindex} (>0) — positive tabindex "
                              "disrupts the natural focus order (WCAG 2.4.3); use 0 or -1",
                              line)
            except ValueError:
                pass

        # aria-labelledby-self-reference (important) — an element whose
        # aria-labelledby resolves ONLY to its own id has no real name (a
        # recursive/empty reference). Common on custom controls built from
        # <button role=switch>/<div role=checkbox>. Only flag when EVERY token
        # is the element's own id (if any other token is present, that token
        # may resolve to a real label, so it's not unambiguously broken).
        lb = (am.get("aria-labelledby") or "").strip()
        own_id = (am.get("id") or "").strip()
        if lb and own_id:
            tokens = [t for t in lb.split() if t]
            if tokens and all(t == own_id for t in tokens):
                self._add("important", "aria-labelledby-self-reference",
                          f"<{tag} id=\"{own_id}\"> has aria-labelledby pointing only "
                          "at its own id — a self-reference yields an empty accessible "
                          "name; point aria-labelledby at the LABEL element's id (or use "
                          "aria-label / a real <label for>) (WCAG 4.1.2)", line)

        # aria-checked-missing (important) — an element with a checkable ARIA
        # widget role MUST carry aria-checked. The role is explicit, so it
        # overrides any native :checked (a <input type=checkbox role=switch>
        # without aria-checked announces no/incorrect state to AT). Unambiguous.
        wrole = (am.get("role") or "").strip().lower()
        if wrole in _ARIA_CHECKED_ROLES and "aria-checked" not in am:
            self._add("important", "aria-checked-missing",
                      f"<{tag} role=\"{wrole}\"> has no aria-checked — a checkable "
                      "ARIA widget role requires aria-checked kept in sync (the role "
                      "overrides any native :checked, so AT reads no/incorrect state) "
                      "(WCAG 4.1.2)", line)

        # document-shape signals
        if tag == "body":
            self.has_body = True
        if tag in _LANDMARK_TAGS:
            self.has_landmark = True
        role = (am.get("role") or "").strip().lower()
        if role in _LANDMARK_ROLES:
            self.has_landmark = True
        if tag == "h1":
            self.h1_count += 1

        # img-missing-alt (important) — no alt attribute AT ALL. alt="" is valid.
        if tag == "img" and not _is_hidden_img(am) and not _has(attrs, "alt"):
            self._add("important", "img-missing-alt",
                      "<img> has no alt attribute — add alt text describing the image, "
                      'or alt="" if it is purely decorative (WCAG 1.1.1)', line)

        # input-missing-label (important) — resolved post-parse (needs label_for + wrapping).
        if tag in ("input", "select", "textarea"):
            itype = (am.get("type") or "").strip().lower() if tag == "input" else ""
            if not (tag == "input" and itype in _INPUT_NO_LABEL_NEEDED):
                self.controls.append((tag, am, line, self._label_depth > 0))

        # label association: collect `for` targets; track wrapping depth.
        if tag == "label":
            self._label_depth += 1
            tgt = (am.get("for") or "").strip()
            if tgt:
                self.label_for.add(tgt)

        # content-bearing controls (button / a[href]) — accumulate inner text/alt.
        is_control = tag == "button" or (tag == "a" and (am.get("href") or "").strip() != "" and _has(attrs, "href"))
        if is_control and not self_closing:
            self._ctrl_stack.append({"tag": tag, "am": am, "line": line,
                                     "text": "", "named_child": False})
        elif is_control and self_closing:
            # degenerate <button/> — judge immediately on its own attrs.
            self._judge_control({"tag": tag, "am": am, "line": line,
                                 "text": "", "named_child": False})

        # a named child satisfies a control's name: <img alt="..."> or any element
        # carrying aria-label/title; <svg><title> handled via handle_data in <title>.
        if self._ctrl_stack:
            if tag == "img" and _nonblank(attrs, "alt"):
                self._ctrl_stack[-1]["named_child"] = True
            if _has_aria_name(am):
                self._ctrl_stack[-1]["named_child"] = True

    def handle_endtag(self, tag):
        if tag == "label" and self._label_depth > 0:
            self._label_depth -= 1
        # close the nearest matching open control frame
        if self._ctrl_stack and self._ctrl_stack[-1]["tag"] == tag:
            self._judge_control(self._ctrl_stack.pop())

    def handle_data(self, data):
        if data.strip() and self._ctrl_stack:
            self._ctrl_stack[-1]["text"] += data

    # --- post-parse resolution --------------------------------------------
    def _judge_control(self, frame):
        """control-missing-name (important): a button/link control with empty
        text AND no aria/title AND no named child (img alt / svg title)."""
        am = frame["am"]
        if frame["text"].strip() or frame["named_child"] or _has_aria_name(am):
            return
        tag = frame["tag"]
        what = "icon-only <button>" if tag == "button" else "icon-only link (<a href>)"
        self._add("important", "control-missing-name",
                  f"{what} has no accessible name — empty text and no "
                  "aria-label/aria-labelledby/title (WCAG 4.1.2 / 2.4.4)", frame["line"])

    def resolve(self):
        # any control frames still open at EOF (malformed/unclosed) — judge them.
        while self._ctrl_stack:
            self._judge_control(self._ctrl_stack.pop())

        # input-missing-label: a control with no name from any source.
        for tag, am, line, wrapped in self.controls:
            cid = (am.get("id") or "").strip()
            named = (wrapped
                     or (cid and cid in self.label_for)
                     or _has_aria_name(am))
            if not named:
                self._add("important", "input-missing-label",
                          f"<{tag}> has no accessible name — associate a <label for=ID>, "
                          "wrap it in a <label>, or add aria-label/aria-labelledby/title "
                          "(WCAG 1.3.1 / 4.1.2 / 3.3.2)", line)

        # document-level rules only fire for a real document (a <body> present).
        if self.has_body:
            if not self.has_landmark:
                self._add("polish", "missing-landmarks",
                          "document has no landmark region — add <main> (and ideally "
                          "<header>/<nav>/<footer>) or a role= so assistive tech can "
                          "navigate by region (WCAG 1.3.1 / 2.4.1)")
            if self.h1_count == 0:
                self._add("polish", "no-h1",
                          "document has no <h1> — every page needs one main heading "
                          "(WCAG 1.3.1 / 2.4.6)")
            elif self.h1_count > 1:
                self._add("polish", "multiple-h1",
                          f"document has {self.h1_count} <h1> headings — use a single "
                          "top-level heading and demote the rest (WCAG 1.3.1 / 2.4.6)")


def check_a11y(html):
    """Run the static a11y audit over *html*; return a list of findings.

    Never raises on malformed input — HTMLParser is tolerant and any internal
    error degrades to an empty/partial result rather than a crash (so this can
    sit on the QA hook without ever blocking on its own bug)."""
    walker = _A11yWalk()
    try:
        walker.feed(html or "")
        walker.close()
    except Exception:
        pass
    try:
        walker.resolve()
    except Exception:
        pass
    return walker.findings


def scan_repo_a11y(root):
    """Scan every ``.html``/``.htm`` file under *root* (skipping vendor/build dirs;
    a subset of the overlap-risk surface — real HTML documents only, not JSX/Vue/
    Svelte fragments) and return findings tagged with ``file``/``line``.

    Defensive: an unreadable file is skipped, never fatal."""
    import os
    from scan_repo import _SKIP_DIRS
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith((".html", ".htm")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8") as fh:
                    html = fh.read()
            except Exception:
                continue
            rel = os.path.relpath(p, root)
            for f in check_a11y(html):
                g = dict(f)
                g["file"] = rel
                out.append(g)
    return out


def _format(findings):
    if not findings:
        return "✓ no static accessibility violations found."
    sev = {"important": 0, "polish": 1}
    out = [f"{len(findings)} accessibility finding(s):", ""]
    for f in sorted(findings, key=lambda x: (sev.get(x["severity"], 9), x["kind"])):
        loc = f":{f['line']}" if "line" in f else ""
        out.append(f"  [{f['severity']:<9}] {f['kind']}{loc} — {f['detail']}")
    return "\n".join(out)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: a11y_check.py <page.html> [--json]")
        sys.exit(2)
    try:
        with open(args[0], encoding="utf-8") as fh:
            html = fh.read()
    except Exception as e:
        print(f"::error:: could not read {args[0]}: {e}", file=sys.stderr)
        sys.exit(2)
    findings = check_a11y(html)
    if "--json" in args:
        print(json.dumps(findings, indent=2))
    else:
        print(_format(findings))
    sys.exit(1 if any(f["severity"] == "important" for f in findings) else 0)
