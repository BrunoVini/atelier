"""Tests for live_carbonize — bakes knob param values into CSS post-accept."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_carbonize as lc


def test_bake_range_substitutes_var():
    css = "color: rgba(0,0,0,var(--p-opacity, 0.5));"
    result = lc.bake_range(css, "opacity", 0.8)
    assert "var(--p-opacity" not in result
    assert "0.8" in result


def test_bake_range_no_match_unchanged():
    css = "color: red;"
    assert lc.bake_range(css, "opacity", 0.8) == "color: red;"


def test_bake_steps_keeps_chosen_drops_others():
    css = (
        '[data-p-density="airy"] .box { padding: 2rem; }\n'
        '[data-p-density="snug"] .box { padding: 1rem; }\n'
        '[data-p-density="packed"] .box { padding: 0.5rem; }\n'
    )
    result = lc.bake_steps(css, "density", "snug")
    assert "airy" not in result
    assert "packed" not in result
    assert "padding: 1rem" in result
    assert "[data-p-density" not in result


def test_bake_toggle_on_keeps_block_strips_selector():
    css = '[data-p-serif] .title { font-family: Georgia; }\n'
    result = lc.bake_toggle(css, "serif", True)
    assert "[data-p-serif]" not in result
    assert "font-family: Georgia" in result


def test_bake_toggle_off_drops_block():
    css = '[data-p-serif] .title { font-family: Georgia; }\n'
    result = lc.bake_toggle(css, "serif", False)
    assert "font-family: Georgia" not in result


def test_carbonize_all_kinds():
    css = (
        "opacity: var(--p-amount, 0.5);\n"
        '[data-p-density="airy"] .w { gap: 2rem; }\n'
        '[data-p-density="packed"] .w { gap: 0.25rem; }\n'
        '[data-p-bold] h1 { font-weight: 800; }\n'
    )
    param_values = {
        "amount": {"kind": "range", "value": 0.7},
        "density": {"kind": "steps", "value": "airy"},
        "bold": {"kind": "toggle", "value": False},
    }
    result = lc.carbonize(css, param_values)
    assert "0.7" in result
    assert "2rem" in result
    assert "packed" not in result
    assert "font-weight: 800" not in result
    assert "var(--p-" not in result
    assert "[data-p-" not in result
