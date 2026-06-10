"""Cold-start anti-sameness ledger (F1)."""


def test_flags_a_repeat_look_but_not_a_distinct_one(tmp_path):
    from cold_start_ledger import fingerprint, record, too_similar
    led = str(tmp_path / "cs.jsonl")
    a = fingerprint("Sora", "saas-dashboard", ["#2563eb", "#111111", "#ffffff"])
    record(a, led)
    # near-identical palette + same font + same archetype -> "the same look"
    b = fingerprint("Sora", "saas-dashboard", ["#2c66ea", "#121212", "#fefefe"])
    assert too_similar(b, led) is not None
    # a genuinely different direction -> not flagged
    c = fingerprint("Fraunces", "editorial", ["#b08947", "#1a1714", "#f5f1ea"])
    assert too_similar(c, led) is None


def test_same_palette_different_archetype_is_allowed(tmp_path):
    from cold_start_ledger import fingerprint, record, too_similar
    led = str(tmp_path / "cs.jsonl")
    record(fingerprint("Sora", "saas-dashboard", ["#2563eb", "#111111", "#ffffff"]), led)
    other = fingerprint("Sora", "marketing-landing", ["#2563eb", "#111111", "#ffffff"])
    assert too_similar(other, led) is None
