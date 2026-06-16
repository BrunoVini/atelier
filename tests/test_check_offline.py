"""Offline-safety check: external_refs flags only what the browser fetches on load."""
from check_offline import external_refs, main


def test_flags_google_fonts_link_and_cdn_script():
    html = """<head>
      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces">
      <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    </head>"""
    refs = external_refs(html)
    kinds = {r["kind"] for r in refs}
    assert any("stylesheet" in k for k in kinds)
    assert "script[src]" in kinds
    assert len(refs) == 3


def test_does_not_flag_svg_xmlns_or_xlink_namespaces():
    # the single most common false positive — an inline icon set
    html = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><path d="M0 0"/></svg>'
    assert external_refs(html) == []


def test_does_not_flag_anchor_hyperlinks():
    # <a href=http> navigates on click; it is not a load-time fetch
    html = '<a href="https://example.com/help">Help</a>'
    assert external_refs(html) == []


def test_does_not_flag_data_uris_or_internal_refs():
    html = ('<img src="data:image/png;base64,AAAA">'
            '<use href="#leaf"><link rel="stylesheet" href="./local.css">'  # relative, not external scheme
            '<a href="#top">top</a>')
    assert external_refs(html) == []


def test_flags_css_url_and_import_and_font_face():
    html = """<style>
      @import "https://cdn.example.com/base.css";
      @font-face { font-family:X; src: url(https://fonts.gstatic.com/s/x.woff2) format('woff2'); }
      .hero { background: url("//images.example.com/bg.jpg"); }
    </style>"""
    kinds = {r["kind"] for r in external_refs(html)}
    assert "css-import" in kinds
    assert "css-url" in kinds


def test_flags_js_fetch_and_import():
    html = """<script>
      fetch("https://api.example.com/data");
      import("https://cdn.example.com/mod.js");
      import x from "https://cdn.example.com/lib.js";
    </script>"""
    kinds = {r["kind"] for r in external_refs(html)}
    assert "js-fetch" in kinds
    assert "js-import" in kinds


def test_self_contained_file_has_zero_refs():
    html = ('<head><style>body{font-family:-apple-system,system-ui,sans-serif}</style></head>'
            '<body><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
            '<img src="data:image/svg+xml;utf8,<svg/>"><script>const app={};</script></body>')
    assert external_refs(html) == []


def test_main_exit_codes(tmp_path):
    safe = tmp_path / "safe.html"
    safe.write_text("<body><script>const a=1;</script></body>", encoding="utf-8")
    assert main([str(safe)]) == 0
    bad = tmp_path / "bad.html"
    bad.write_text('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X">', encoding="utf-8")
    assert main([str(bad)]) == 1
