"""Persisted critique snapshots + trend (#9)."""


def test_record_and_trend(tmp_path):
    from critique_ledger import record, load, trend, DIMENSIONS
    led = str(tmp_path / "critique.jsonl")
    record("landing.html", {"contract": 8, "hierarchy": 7, "detail": 6, "functionality": 9, "innovation": 7}, led)
    record("landing.html", {"contract": 9, "hierarchy": 8, "detail": 8, "functionality": 9, "innovation": 8}, led)
    rows = load(led)
    assert len(rows) == 2 and set(DIMENSIONS) <= set(rows[0]["scores"])
    # trend = latest total minus previous total for the same artifact
    assert trend("landing.html", led) == (42 - 37)


def test_trend_none_for_single_snapshot(tmp_path):
    from critique_ledger import record, trend
    led = str(tmp_path / "critique.jsonl")
    record("a.html", {"contract": 5, "hierarchy": 5, "detail": 5, "functionality": 5, "innovation": 5}, led)
    assert trend("a.html", led) is None


def test_tolerates_malformed_lines(tmp_path):
    from critique_ledger import trend
    led = tmp_path / "critique.jsonl"
    led.write_text("garbage\n{}\n")
    assert trend("x.html", str(led)) is None   # never crashes


def test_record_rejects_missing_or_typod_dimensions(tmp_path):
    from critique_ledger import record
    led = str(tmp_path / "c.jsonl")
    try:
        record("a.html", {"contract": 8, "heirarchy": 7, "detail": 6, "functionality": 9, "innovation": 7}, led)
        assert False, "typo'd dimension should raise"
    except ValueError:
        pass
