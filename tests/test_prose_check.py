"""Prose anti-slop gate (#13)."""


def test_flags_high_signal_ai_tells():
    from prose_check import prose_tells
    bad = ("Let's delve into this seamless, game-changing platform. In today's fast-paced "
           "world, it's not just a tool, it's a revolution that will supercharge your workflow.")
    labels = {label for _, label in prose_tells(bad)}
    assert {"delve", "seamless", "game-changing", "not just X, it's Y"} <= labels


def test_clean_prose_has_no_tells():
    from prose_check import prose_tells
    clean = "A studio for serious products. Measure the repo first, then generate on-contract."
    assert prose_tells(clean) == []


def test_does_not_flag_common_legitimate_words():
    # words an honest doc uses all the time must NOT be tells (false positives kill trust)
    from prose_check import prose_tells
    assert prose_tells("This robust, flexible system lets you leverage existing tokens.") == []


def test_does_not_flag_the_projects_own_docs(tmp_path):
    # Regression guard: a doc that documents the banned vocabulary (in code spans) must
    # not fail its own gate.
    import os
    from prose_check import prose_tells
    root = os.path.join(os.path.dirname(__file__), "..")
    for doc in ("README.md", "CHANGELOG.md"):
        text = open(os.path.join(root, doc), encoding="utf-8").read()
        assert prose_tells(text) == [], f"{doc} trips the prose gate: {prose_tells(text)}"
