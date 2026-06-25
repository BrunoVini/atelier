"""PR-diff-scoped review: governance lands at the point of change (C4)."""
from pr_review import changed_lines, annotation


SAMPLE_DIFF = """diff --git a/src/app.css b/src/app.css
index 1111111..2222222 100644
--- a/src/app.css
+++ b/src/app.css
@@ -10,0 +11,2 @@ body {
+  color: #1234ff;
+  background: #fff;
@@ -40,1 +42,1 @@
-  margin: 8px;
+  margin: 9px;
diff --git a/README.md b/README.md
index 3333333..4444444 100644
--- a/README.md
+++ b/README.md
@@ -1,0 +2,1 @@
+changed prose
"""


def test_changed_lines_parses_hunks_per_file():
    cl = changed_lines(SAMPLE_DIFF)
    assert cl["src/app.css"] == {11, 12, 42}
    assert cl["README.md"] == {2}


def test_annotation_emits_github_warning_format():
    line = annotation("src/app.css", 11, "off-contract color #1234ff → var(--primary)")
    assert line.startswith("::warning file=src/app.css,line=11::")
    assert "#1234ff" in line


def test_review_matches_repo_relative_paths_and_filters_to_changed_lines(tmp_path):
    """Regression for the P0: lint_repo returns repo-relative paths, so review()
    must NOT re-relativize them (that resolves against CWD and silently matches
    nothing — a vacuous clean review). Derive the real finding line from lint_repo
    so the test is robust to 0/1-based numbering."""
    from pr_review import review
    from lint_design import lint_repo
    repo = tmp_path
    (repo / "design").mkdir()
    (repo / "design" / "design-tokens.json").write_text('{"colors":{"ink":"#111111","paper":"#ffffff"}}')
    (repo / "app.css").write_text("a{color:#1234ff}\n")          # off-contract color
    contract = str(repo / "design" / "design-tokens.json")

    findings = [f for f in lint_repo(str(repo), contract) if f["file"] == "app.css"]
    assert findings, "sanity: lint should flag the off-contract color"
    ln = findings[0]["line"]

    hit = f"--- a/app.css\n+++ b/app.css\n@@ -{ln},0 +{ln},1 @@\n+a{{color:#1234ff}}\n"
    miss = "--- a/app.css\n+++ b/app.css\n@@ -99,0 +99,1 @@\n+unrelated\n"
    assert review(str(repo), contract, hit)          # path matched + line changed -> annotation (catches P0)
    assert not review(str(repo), contract, miss)     # finding's line not in the diff -> filtered out


def test_annotation_severity_picks_error_for_blocker():
    assert annotation("a.jsx", 3, "x", "blocker").startswith("::error file=a.jsx,line=3::")
    assert annotation("a.jsx", 3, "x", "important").startswith("::warning ")
    assert annotation("a.jsx", 3, "x").startswith("::warning ")  # default


def test_clickable_div_on_changed_line_is_flagged(tmp_path):
    """A new interactive <div onClick> on a changed line is an a11y blocker the
    contract lint can't see — flag it, but ONLY because the line is in the diff."""
    from pr_review import _interactive_findings, review
    repo = tmp_path
    (repo / "design").mkdir()
    (repo / "design" / "design-tokens.json").write_text('{"colors":{"ink":"#111111"}}')
    (repo / "Panel.jsx").write_text(
        'export function P({onExport}){\n'
        '  return (\n'
        '    <div\n'
        '      className="export"\n'
        '      onClick={onExport}\n'
        '      style={{cursor:"pointer"}}\n'
        '    >Export</div>\n'
        '  );\n'
        '}\n')
    touched = {"Panel.jsx": {3, 4, 5, 6, 7}}      # the new block
    fs = _interactive_findings(str(repo), touched)
    assert any(f["kind"] == "a11y" and f["severity"] == "blocker" for f in fs), fs
    # and it surfaces through review() as an ::error annotation
    diff = "--- a/Panel.jsx\n+++ b/Panel.jsx\n@@ -2,0 +3,5 @@\n+x\n+x\n+x\n+x\n+x\n"
    anns = review(str(repo), str(repo / "design" / "design-tokens.json"), diff)
    assert any(a.startswith("::error") and "Panel.jsx" in a for a in anns), anns


def test_clickable_div_on_unchanged_line_is_not_flagged(tmp_path):
    """Same clickable <div> but its lines are NOT in the diff -> out of scope, silent."""
    from pr_review import _interactive_findings
    repo = tmp_path
    (repo / "Panel.jsx").write_text(
        '<div onClick={f} style={{cursor:"pointer"}}>Go</div>\n')
    assert _interactive_findings(str(repo), {"Panel.jsx": {99}}) == []


def test_real_button_with_role_is_not_flagged(tmp_path):
    """A proper <button>, and a <div role=button tabindex=0>, are accessible — no flag."""
    from pr_review import _interactive_findings
    repo = tmp_path
    (repo / "ok.jsx").write_text(
        '<button onClick={f}>Save</button>\n'
        '<div role="button" tabIndex={0} onClick={f}>Go</div>\n')
    assert _interactive_findings(str(repo), {"ok.jsx": {1, 2}}) == []


def test_new_button_variant_without_focus_is_flagged(tmp_path):
    """A new .btn--danger introduced by the diff with no :focus rule among the
    changed lines is flagged; adding a :focus-visible rule clears it."""
    from pr_review import _interactive_findings
    repo = tmp_path
    (repo / "btn.css").write_text(
        ".btn--danger {\n  background: red;\n  color: #fff;\n}\n")
    touched = {"btn.css": {1, 2, 3, 4}}
    fs = _interactive_findings(str(repo), touched)
    assert any(f["kind"] == "a11y" and "focus" in f["fix"].lower() for f in fs), fs

    (repo / "btn2.css").write_text(
        ".btn--ok {\n  background: green;\n}\n"
        ".btn--ok:focus-visible {\n  outline: 2px solid;\n}\n")
    fs2 = _interactive_findings(str(repo), {"btn2.css": {1, 2, 3, 4, 5}})
    assert not any("focus" in f["fix"].lower() for f in fs2), fs2
