"""APCA (APCA-W3 / 0.0.98G-4g) perceptual contrast — anchor vectors, polarity, and the
OPT-IN APCA gate that leaves the default WCAG behavior byte-identical."""
from audit_contrast import (apca_lc, audit, gate_failures, apca_gate_failures,
                            APCA_DEFAULT_TARGET)


def _close(a, b, tol=1.5):
    return abs(a - b) <= tol


def test_apca_anchor_vectors():
    # The three published anchors, within ±1.5 Lc.
    assert _close(apca_lc("#000000", "#FFFFFF"), 106.0)   # black on white
    assert _close(apca_lc("#FFFFFF", "#000000"), -108.0)  # white on black
    assert _close(apca_lc("#888888", "#FFFFFF"), 63.0)    # mid-gray on white


def test_apca_lc_malformed_hex_returns_zero():
    # A malformed/non-hex input returns 0.0 (no contrast) rather than raising.
    assert apca_lc("#xyz", "#ffffff") == 0.0
    assert apca_lc("#000000", "rebeccapurple") == 0.0
    assert apca_lc("#abcdz", "#ffffff") == 0.0  # 5-char non-hex
    assert apca_lc(None, "#ffffff") == 0.0
    # valid colors are untouched (anchor stays byte-identical)
    assert _close(apca_lc("#000000", "#FFFFFF"), 106.0)


def test_apca_polarity_sign():
    # normal polarity (dark text on light) is POSITIVE; reverse (light on dark) NEGATIVE
    assert apca_lc("#111111", "#ffffff") > 0
    assert apca_lc("#eeeeee", "#111111") < 0


def test_apca_magnitude_symmetric_sign_not():
    # swapping text/bg flips the SIGN but the magnitudes are NOT identical (APCA is
    # polarity-asymmetric by design) — so the values are not simple negatives.
    fwd = apca_lc("#000000", "#FFFFFF")
    rev = apca_lc("#FFFFFF", "#000000")
    assert fwd > 0 and rev < 0
    assert abs(fwd) != abs(rev)             # 106 vs 108 — magnitude differs by polarity


def test_apca_rows_carry_lc_additively():
    rows = audit({"foreground": "#111111", "background": "#ffffff"})
    assert all("apca_lc" in r for r in rows)         # additive key, always present
    # existing row keys are untouched
    for k in ("text", "surface", "ratio", "passes", "informational"):
        assert all(k in r for r in rows)


def test_apca_gate_opt_in_fails_low_lc_but_default_wcag_unchanged():
    # A pair that PASSES WCAG default but has mediocre APCA: #777 on #fff is ~4.48 (just
    # under) — use a pair that clears WCAG but trails APCA at a strict target. #5e5e5e on
    # white clears AA (≈7) yet sits below an aggressive APCA body target of 90.
    colors = {"foreground": "#5e5e5e", "background": "#ffffff"}
    rows = audit(colors)
    # DEFAULT (WCAG) behavior is unchanged — this pair passes today and still passes
    assert gate_failures(rows) == []
    # OPT-IN APCA at a strict body target (90) catches the perceptual shortfall
    strict = apca_gate_failures(rows, target=90)
    assert any(r["text"] == "foreground" and r["surface"] == "background" for r in strict)
    # ...while at the default large/bold target (60) this same pair is acceptable
    assert apca_gate_failures(rows, target=APCA_DEFAULT_TARGET) == []


def test_apca_gate_does_not_touch_informational_pairs():
    # brand×brand pairs are advisory under WCAG and must also be exempt from the APCA gate
    rows = audit({"foreground": "#111", "background": "#fff", "accent": "#c9a227"})
    for r in apca_gate_failures(rows, target=90):
        assert r["informational"] is False


def test_apca_contract_config_opt_in(tmp_path):
    from audit_contrast import _resolve_apca_config
    # default: no APCA config -> gate off, no target
    (tmp_path / "DESIGN.md").write_text(
        "```json atelier-contract\n"
        '{"colors":{"background":"#ffffff","foreground":"#111111"},"fonts":["Sora"]}\n```\n')
    assert _resolve_apca_config(str(tmp_path)) == (False, None)
    # contrast.algorithm:"apca" opts into the gate; default target 60 when unset
    apca_dir = tmp_path / "apca"
    apca_dir.mkdir()
    (apca_dir / "DESIGN.md").write_text(
        "```json atelier-contract\n"
        '{"colors":{"background":"#ffffff","foreground":"#111111"},"fonts":["Sora"],'
        '"contrast":{"algorithm":"apca","apca_target":75}}\n```\n')
    gate_on, target = _resolve_apca_config(str(apca_dir))
    assert gate_on is True and target == 75.0
    # a bare apca_target number (no algorithm) reports a target but does NOT gate
    t_dir = tmp_path / "tonly"
    t_dir.mkdir()
    (t_dir / "DESIGN.md").write_text(
        "```json atelier-contract\n"
        '{"colors":{"background":"#ffffff","foreground":"#111111"},"fonts":["Sora"],'
        '"apca_target":60}\n```\n')
    gate_on, target = _resolve_apca_config(str(t_dir))
    assert gate_on is False and target == 60.0
