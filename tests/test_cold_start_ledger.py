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


def test_tolerates_malformed_ledger_lines(tmp_path):
    from cold_start_ledger import fingerprint, too_similar
    led = tmp_path / "cs.jsonl"
    led.write_text('not json\n{"font":"x"}\n' + '{"bad":')   # torn + missing fields + half-written
    # must not crash; just returns no collision
    assert too_similar(fingerprint("Sora", "saas", ["#2563eb"]), str(led)) is None


def test_centroid_collision_is_not_a_match(tmp_path):
    from cold_start_ledger import fingerprint, record, too_similar
    led = str(tmp_path / "cs.jsonl")
    record(fingerprint("Sora", "saas", ["#ff0000", "#0000ff"]), led)   # red+blue, centroid ~purple
    other = fingerprint("Sora", "saas", ["#800080", "#800080"])        # all purple, same centroid
    assert too_similar(other, led) is None        # different actual colors -> not "the same look"


def test_padding_with_a_neutral_cannot_evade(tmp_path):
    from cold_start_ledger import fingerprint, record, too_similar
    led = str(tmp_path / "cs.jsonl")
    record(fingerprint("Sora", "saas", ["#2563eb", "#111111", "#ffffff"]), led)
    padded = fingerprint("Sora", "saas", ["#2563eb", "#111111", "#ffffff", "#f8fafc"])
    assert too_similar(padded, led) is not None    # same look + one extra neutral still flags


def test_font_stack_is_normalized(tmp_path):
    from cold_start_ledger import fingerprint, record, too_similar
    led = str(tmp_path / "cs.jsonl")
    record(fingerprint("Sora, sans-serif", "saas", ["#2563eb", "#111111", "#ffffff"]), led)
    same = fingerprint("Sora", "saas", ["#2563eb", "#111111", "#ffffff"])
    assert too_similar(same, led) is not None      # "Sora, sans-serif" == "Sora"
