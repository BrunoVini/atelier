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
