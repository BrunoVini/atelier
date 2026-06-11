"""Inline suppression directives for atelier checks (ESLint-style).

Three directive forms, each optionally followed by space-separated rule KINDS
(no kinds => all kinds). A directive is honored only inside comment SYNTAX
(``/* */``, ``<!-- -->``, ``//``, ``#``) AND only when it is the FIRST token of
the comment body. That means body text that merely MENTIONS the token (e.g.
``/* never use atelier-disable */``) does NOT suppress anything, and a CSS hex
color (``#00ff00``) or a URL ``://`` is never mistaken for a comment opener.

    atelier-disable-line   [kinds...]   suppress findings ON this line
    atelier-disable-next-line [kinds...]   suppress findings on the NEXT line
    atelier-disable        [kinds...]   suppress findings for the WHOLE file

Kinds are matched against a finding's ``kind`` field (e.g. ``color``, ``font``,
``depth`` in lint_design; ``purple-gradient``, ``generic-font`` in slop_check).
Only KNOWN kinds are slurped after the directive; the first prose/unknown token
ends the kind list, so trailing prose can't silently scope the suppression.

Usage models
------------
* **Line-numbered findings** (lint_design): build a per-file ``LineSuppressions``
  from the source lines, then for each finding ask
  ``suppressed(line_no, kind)``. A finding at line N is suppressed when line N
  carries ``atelier-disable-line`` (matching kind / no-kind) OR line N-1 carries
  ``atelier-disable-next-line``. A file-level ``atelier-disable`` suppresses all
  matching kinds regardless of line.

* **Whole-document findings** (slop_check): line→finding mapping is impossible
  (rules run over the whole document), so all three forms DEGRADE to FILE-scoped
  by-kind suppression: ``file_disabled_kinds(text)`` returns the union of kinds
  named by any directive, plus a flag for a bare directive (no kinds = disable
  all kinds for the file).

No directive present => empty results => identical (unchanged) behavior.
"""
import re

# Directive must be the FIRST token of a comment BODY (anchored at the body start,
# after the comment opener + optional whitespace). A left word-boundary lookbehind
# is redundant here given the `^\s*` anchor, but the token still ends on a word/`-`
# boundary so a SUFFIX word can't match. Trailing kinds are space-separated and must
# look like rule kinds; bare prose after the directive is NOT slurped as kinds — only
# the run of well-formed kind tokens immediately after the directive is captured, and
# parsing stops at the first non-kind token (see `_parse_body_directive`).
_DIRECTIVE = re.compile(
    r"^\s*(?<![\w-])atelier-disable(?P<scope>-next-line|-line)?(?![\w-])"  # anchored directive
    r"(?P<rest>.*)$",                                                       # remainder (kinds + prose)
    re.S,
)
# A single kind token: a rule kind like `color`, `purple-gradient`, `generic-font`.
_KIND_TOKEN = re.compile(r"^[A-Za-z][\w-]*$")

# Known rule kinds emitted by lint_design + slop_check. Trailing tokens after a
# directive are taken as kinds only while they are KNOWN kinds; the first unknown
# token (i.e. prose) stops the slurp, so `atelier-disable-line color because the
# purple-gradient looks bad` scopes ONLY `color` — the prose word `purple-gradient`
# is never silently slurped as a phantom kind. Keep in sync with the `kind` strings
# produced by the rule modules.
KNOWN_KINDS = frozenset({
    # lint_design
    "color", "font", "depth", "token-ref",
    # slop_check — visual
    "generic-font", "overused-font", "single-font", "purple-gradient",
    "oklch-warm-neutral-default", "glassmorphism", "card-left-border",
    "too-many-fonts", "flat-type-hierarchy", "monotonous-spacing",
    "oversized-h1", "dark-glow",
    # slop_check — copy
    "em-dash-cadence", "marketing-cliche", "vague-cta", "all-caps-body",
    "scroll-cue", "section-number-label", "decorative-locale-strip",
    "version-stamp", "decorative-dots",
    # slop_check — structural / a11y / proof
    "eyebrow-overuse", "fake-window-chrome", "native-control", "layout-monotony",
    "no-focus-visible", "fabricated-social-proof", "too-many-dead-links",
    "dead-anchors",
    # slop_check — overlap / ported / profiles
    "positioned-percent", "negative-margin", "decoration-cluster",
    "codex-big-radius", "codex-sketchy-svg", "codex-stripe-gradient",
    "gpt-ghost-card", "gpt-theater-copy", "gemini-img-hover-scale",
})

# Comment SPANS — the directive is only honored inside one of these comment
# syntaxes, so a stray word in body text can't trip a rule. Each alternative
# captures the comment BODY (the text after the opener, before any closer) in a
# named group so we can anchor the directive at the body's start.
#
# `#` line-comments are intentionally NARROW: only at start-of-line or after
# whitespace, and NOT a CSS hex color (`#00ff00`) — a bare `#hex` or a `://` in a
# URL must never read as a comment opener. `//` is likewise only honored at
# start-of-line or after whitespace so `https://…` is not a pseudo-comment.
_COMMENT = re.compile(
    r"/\*(?P<block>.*?)\*/"                          # /* block */
    r"|<!--(?P<html>.*?)-->"                          # <!-- html -->
    r"|(?:^|(?<=\s))//(?P<line>[^\n]*)"               # // line comment (start/ws only)
    r"|(?:^|(?<=\s))#(?![0-9A-Fa-f]{3}\b|[0-9A-Fa-f]{6}\b|[0-9A-Fa-f]{8}\b)(?P<hash>[^\n]*)",  # # comment, not a hex
    re.S,
)
_COMMENT_GROUPS = ("block", "html", "line", "hash")


def _comment_bodies(text):
    """Yield the BODY of each comment span in *text* (one of the four styles)."""
    for m in _COMMENT.finditer(text):
        for g in _COMMENT_GROUPS:
            body = m.group(g)
            if body is not None:
                yield body
                break


def _parse_body_directive(body):
    """Parse a comment *body* for a LEADING atelier-disable directive.

    Returns ``(scope, kinds_set, all_flag)`` if the body STARTS with the directive
    (after optional whitespace), else ``None``. Trailing tokens are taken as kinds
    only while they look like rule kinds; parsing stops at the first token that
    doesn't (so prose after the kinds isn't slurped as phantom kinds).
    """
    m = _DIRECTIVE.match(body)
    if not m:
        return None
    scope = m.group("scope") or ""        # "" | "-line" | "-next-line"
    kinds = []
    for tok in m.group("rest").split():
        if _KIND_TOKEN.match(tok) and tok in KNOWN_KINDS:
            kinds.append(tok)
        else:
            break                          # prose (or unknown kind) begins — stop slurping
    all_flag = not kinds
    return scope, set(kinds), all_flag


class LineSuppressions:
    """Per-file, line-aware suppression index built from source *lines*.

    ``lines`` is a list of source lines WITHOUT trailing newlines (as produced
    by ``str.splitlines()``); line numbers are 1-based to match lint findings.
    """

    def __init__(self, lines):
        # 1-based line -> (kinds_set, all_flag) for atelier-disable-line on that line
        self._this = {}
        # 1-based line -> (kinds_set, all_flag) for the line FOLLOWING a -next-line
        self._next = {}
        # file-level: accumulated kinds + all-flag for bare atelier-disable
        self._file_kinds = set()
        self._file_all = False
        for idx, raw in enumerate(lines, 1):
            # Restrict to comment spans, and require the directive to be the FIRST
            # token of the comment body, so neither body text nor a comment that
            # merely MENTIONS the token can trip a directive.
            for body in _comment_bodies(raw):
                parsed = _parse_body_directive(body)
                if parsed is None:
                    continue
                scope, kinds, all_flag = parsed
                if scope == "-line":
                    self._merge(self._this, idx, kinds, all_flag)
                elif scope == "-next-line":
                    self._merge(self._next, idx + 1, kinds, all_flag)
                else:  # bare atelier-disable => whole file
                    if all_flag:
                        self._file_all = True
                    self._file_kinds |= kinds

    @staticmethod
    def _merge(table, line, kinds, all_flag):
        cur_kinds, cur_all = table.get(line, (set(), False))
        table[line] = (cur_kinds | kinds, cur_all or all_flag)

    @staticmethod
    def _matches(entry, kind):
        kinds, all_flag = entry
        return all_flag or kind in kinds

    def suppressed(self, line, kind):
        """True if a finding of *kind* at 1-based *line* is suppressed."""
        if self._file_all or kind in self._file_kinds:
            return True
        e = self._this.get(line)
        if e and self._matches(e, kind):
            return True
        e = self._next.get(line)
        if e and self._matches(e, kind):
            return True
        return False

    def any_directive(self):
        """True if the file carried ANY atelier-disable* directive."""
        return bool(self._this or self._next or self._file_kinds or self._file_all)


def file_disabled_kinds(text):
    """File-scoped by-kind suppression for whole-document checks.

    Scans *text* for ANY of the three directive forms and returns
    ``(kinds_set, all_flag)``: the union of all named kinds and whether a bare
    directive (no kinds) disables ALL kinds for the file. For whole-document
    rules ``-line``/``-next-line`` cannot map to a finding line, so they degrade
    here to the same file-scoped by-kind semantics as a bare ``atelier-disable``.

    No directive present => (empty set, False) => caller filters nothing.
    """
    kinds = set()
    all_flag = False
    for body in _comment_bodies(text):
        parsed = _parse_body_directive(body)
        if parsed is None:
            continue
        _scope, ks, af = parsed
        kinds |= ks
        all_flag = all_flag or af
    return kinds, all_flag
