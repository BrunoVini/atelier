"""Inline suppression directives: parser + lint (line-aware) + slop (file-scoped)."""
from suppressions import LineSuppressions, file_disabled_kinds
from lint_design import lint_repo
import slop_check


# --- parser: three forms, with/without kinds, comment styles ---

def test_disable_line_no_kinds_suppresses_all_on_that_line():
    s = LineSuppressions(["a{} // atelier-disable-line"])
    assert s.suppressed(1, "color") is True
    assert s.suppressed(1, "font") is True
    assert s.suppressed(2, "color") is False


def test_disable_line_with_kind_matches_only_that_kind():
    s = LineSuppressions(["a{} /* atelier-disable-line color */"])
    assert s.suppressed(1, "color") is True
    assert s.suppressed(1, "font") is False


def test_disable_next_line_targets_following_line():
    s = LineSuppressions(["# atelier-disable-next-line font", "body{}"])
    assert s.suppressed(2, "font") is True
    assert s.suppressed(2, "color") is False
    assert s.suppressed(1, "font") is False


def test_bare_disable_is_file_scoped():
    s = LineSuppressions(["<!-- atelier-disable depth -->", "x", "y"])
    assert s.suppressed(3, "depth") is True
    assert s.suppressed(99, "depth") is True
    assert s.suppressed(3, "color") is False


def test_bare_disable_no_kinds_suppresses_everything():
    s = LineSuppressions(["// atelier-disable"])
    assert s.suppressed(5, "anything") is True


def test_directive_outside_comment_is_ignored():
    # bare word in body text (not in a comment) must NOT trip suppression
    s = LineSuppressions(["content: 'atelier-disable-line color';"])
    assert s.suppressed(1, "color") is False


def test_no_directive_means_no_suppression():
    s = LineSuppressions(["a{color:red}", "b{}"])
    assert s.any_directive() is False
    assert s.suppressed(1, "color") is False


def test_file_disabled_kinds_union_and_all_flag():
    kinds, all_flag = file_disabled_kinds(
        "<!-- atelier-disable-line purple-gradient -->\n// atelier-disable generic-font")
    assert all_flag is False
    assert kinds == {"purple-gradient", "generic-font"}
    k2, all2 = file_disabled_kinds("# atelier-disable")
    assert all2 is True


def test_file_disabled_kinds_none():
    assert file_disabled_kinds("<p>hello</p>") == (set(), False)


# --- lint_design integration ---

def _lint_repo(tmp_path, css):
    (tmp_path / "design").mkdir()
    (tmp_path / "design" / "design-tokens.json").write_text(
        '{"colors":{"ink":"#111111","paper":"#ffffff"}}')
    (tmp_path / "a.css").write_text(css)
    return lint_repo(str(tmp_path), str(tmp_path))


def test_lint_suppress_by_line(tmp_path):
    findings = _lint_repo(tmp_path, "a{color:#ff00ff} /* atelier-disable-line color */")
    assert findings == []


def test_lint_suppress_by_next_line(tmp_path):
    findings = _lint_repo(tmp_path, "/* atelier-disable-next-line color */\na{color:#ff00ff}")
    assert findings == []


def test_lint_suppress_by_kind_does_not_hide_other_kinds(tmp_path):
    # disable font but a color drift remains -> still reported
    findings = _lint_repo(tmp_path, "a{color:#ff00ff} /* atelier-disable-line font */")
    assert len(findings) == 1 and findings[0]["kind"] == "color"


def test_lint_no_directive_unchanged(tmp_path):
    findings = _lint_repo(tmp_path, "a{color:#ff00ff}")
    assert len(findings) == 1 and findings[0]["kind"] == "color"


# --- slop_check integration (file-scoped by kind) ---

def test_slop_file_scoped_by_kind():
    html = ("<style>body{font-family:Inter}</style>"
            "<!-- atelier-disable generic-font -->")
    kinds = {f["kind"] for f in slop_check.check_html(html, [])}
    assert "generic-font" not in kinds


def test_slop_no_directive_unchanged():
    html = "<style>body{font-family:Inter}</style>"
    kinds = {f["kind"] for f in slop_check.check_html(html, [])}
    assert "generic-font" in kinds


def test_slop_bare_disable_clears_all():
    html = ("<style>body{font-family:Inter;background:linear-gradient(90deg,#7c3aed,#6366f1)}</style>"
            "<!-- atelier-disable -->")
    assert slop_check.check_html(html, []) == []


def test_slop_kind_scoped_removes_only_that_kind():
    # disable purple-gradient but a generic-font tell survives (parallel to the lint negative test)
    html = ("<style>body{font-family:Inter;background:linear-gradient(90deg,#7c3aed,#6366f1)}</style>"
            "<!-- atelier-disable purple-gradient -->")
    kinds = {f["kind"] for f in slop_check.check_html(html, [])}
    assert "purple-gradient" not in kinds
    assert "generic-font" in kinds


# --- over-suppression guards: a directive must be the FIRST token of a comment
# body inside real comment SYNTAX; incidental mentions / hex colors / prefix words
# / trailing prose must NOT suppress. ---

def test_mention_of_token_does_not_suppress():
    # a comment that merely MENTIONS the token is parsed as prose, not a directive
    s = LineSuppressions(["a{color:#ff00ff} /* never use atelier-disable */"])
    assert s.suppressed(1, "color") is False
    assert s.any_directive() is False


def test_css_hex_color_is_not_a_comment_opener():
    # `#00ff00` (hex) must not open a `#` line-comment; a `://` URL must not open `//`
    s = LineSuppressions(['<div style="color:#00ff00"> atelier-disable'])
    assert s.suppressed(1, "color") is False
    s2 = LineSuppressions(['<a href="https://x/atelier-disable">x</a>'])
    assert s2.suppressed(1, "color") is False


def test_prefix_word_does_not_match_directive():
    # `my-atelier-disable-line` is a different word, not a directive
    s = LineSuppressions(["a{} /* my-atelier-disable-line color */"])
    assert s.suppressed(1, "color") is False
    assert s.any_directive() is False


def test_trailing_prose_is_not_slurped_as_kinds():
    # prose after a real kind must not be slurped; here a real kind IS named, the
    # rest is prose — kind scoping holds for the named kind, prose is ignored.
    s = LineSuppressions(["a{} /* atelier-disable-line color because purple-gradient looks bad */"])
    assert s.suppressed(1, "color") is True          # the named kind is honored
    assert s.suppressed(1, "purple-gradient") is False  # prose word NOT slurped as a kind


def test_slop_mention_of_token_does_not_suppress():
    # whole-document path: a comment mentioning the token must not wipe findings
    html = ("<style>body{font-family:Inter}</style>"
            "<!-- never use atelier-disable in production -->")
    kinds = {f["kind"] for f in slop_check.check_html(html, [])}
    assert "generic-font" in kinds
