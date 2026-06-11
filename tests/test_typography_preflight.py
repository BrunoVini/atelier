"""Typography preflight (pre-scan) — facts extraction + reused typography findings."""
from typography_preflight import preflight


PAGE = "<!doctype html><html><head><style>{css}</style></head><body>{body}</body></html>"


def test_preflight_extracts_facts():
    css = ("body{font-family:'Sohne',sans-serif;line-height:1.6}"
           "h1{font-family:'Tiempos',serif;font-size:48px;line-height:1.1}"
           "p{font-size:16px;max-width:65ch}"
           ".eyebrow{font-size:12px}")
    out = preflight(PAGE.format(css=css, body="<h1>Hi</h1><p>Body</p>"))
    f = out["facts"]
    assert set(f["fonts"]) == {"sohne", "tiempos"}
    assert f["font_count"] == 2
    # sizes are px-normalized and sorted
    assert f["sizes_px"] == [12.0, 16.0, 48.0]
    assert f["smallest_body_px"] == 12.0          # smallest body-scale size (< 24px)
    assert f["scale_span"] == 4.0                  # 48 / 12
    assert "1.6" in f["line_heights"] and "1.1" in f["line_heights"]
    assert f["has_measure"] is True                # max-width / 65ch present


def test_preflight_findings_include_typography_kinds():
    # a tiny body size + a loose-leading label → both surface as typography findings
    css = ("body{font-family:Inter,sans-serif}"
           "p{font-size:10px}"                      # tiny-body-text
           ".eyebrow{font-size:12px;line-height:1.7}")  # label-line-height
    out = preflight(PAGE.format(css=css, body="<p>x</p>"))
    kinds = {f["kind"] for f in out["findings"]}
    assert "tiny-body-text" in kinds
    assert "label-line-height" in kinds
    # a non-typography kind (e.g. the Inter generic-font tell IS typography and allowed,
    # but color/motion kinds must never leak in)
    assert all(k in __import__("typography_preflight").TYPO_KINDS for k in kinds)


def test_preflight_clean_page_has_no_findings_but_valid_facts():
    css = ("body{font-family:'Sohne',sans-serif;line-height:1.6}"
           "h1{font-family:'Tiempos',serif;font-size:48px}"
           "p{font-size:16px;max-width:65ch}")
    out = preflight(PAGE.format(css=css, body="<h1>Ledger</h1><p>Honest copy.</p>"))
    assert out["findings"] == []
    assert out["facts"]["font_count"] == 2
    assert out["facts"]["smallest_body_px"] == 16.0


def test_preflight_empty_page_is_safe():
    out = preflight("")
    assert out["findings"] == []
    f = out["facts"]
    assert f["fonts"] == [] and f["sizes_px"] == []
    assert f["smallest_body_px"] is None and f["scale_span"] is None
    assert f["has_measure"] is False


def test_preflight_json_shape():
    out = preflight(PAGE.format(css="p{font-size:16px}", body="<p>x</p>"))
    assert set(out) == {"facts", "findings"}
    assert isinstance(out["findings"], list)
    facts = out["facts"]
    for k in ("fonts", "font_count", "sizes_px", "smallest_body_px",
              "line_heights", "scale_span", "has_measure"):
        assert k in facts
