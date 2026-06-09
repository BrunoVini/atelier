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
