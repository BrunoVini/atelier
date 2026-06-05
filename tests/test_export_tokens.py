import json
from pathlib import Path

from export_tokens import (
    to_css_vars,
    to_w3c_tokens,
    to_tailwind_preset,
    write_all,
)

TOKENS = {
    "color": {"primary": "#2563eb", "accent": "#ea580c"},
    "space": {"2": "8px", "4": "16px"},
    "font": {"display": "Sora", "body": "Inter"},
}


def test_to_css_vars():
    css = to_css_vars(TOKENS)
    assert css.strip().startswith(":root {")
    assert "--color-primary: #2563eb;" in css
    assert "--space-2: 8px;" in css


def test_to_w3c_tokens():
    w3c = to_w3c_tokens(TOKENS)
    assert w3c["color"]["primary"]["$value"] == "#2563eb"
    assert w3c["color"]["primary"]["$type"] == "color"
    assert w3c["space"]["2"]["$type"] == "dimension"
    assert w3c["font"]["display"]["$type"] == "fontFamily"
    assert w3c["font"]["display"]["$value"] == ["Sora"]  # W3C: fontFamily is an array


def test_to_tailwind_preset_is_valid_js_object():
    js = to_tailwind_preset(TOKENS)
    assert js.startswith("module.exports = ")
    payload = json.loads(js[len("module.exports = "):].rstrip(";\n"))
    assert payload["theme"]["extend"]["colors"]["primary"] == "#2563eb"
    assert payload["theme"]["extend"]["fontFamily"]["display"] == ["Sora"]


def test_breakpoints_export_to_screens_and_vars():
    tokens = {"breakpoint": {"md": "768px", "lg": "1280px"}}
    js = to_tailwind_preset(tokens)
    payload = json.loads(js[len("module.exports = "):].rstrip(";\n"))
    assert payload["theme"]["screens"] == {"md": "768px", "lg": "1280px"}
    assert "--breakpoint-md: 768px;" in to_css_vars(tokens)


def test_write_all(tmp_path):
    out = tmp_path / "design"
    written = write_all(TOKENS, str(out))
    assert len(written) == 3
    assert (out / "tokens.css").exists()
    assert (out / "tailwind-preset.js").exists()
    data = json.loads((out / "design-tokens.json").read_text())
    assert data["color"]["accent"]["$value"] == "#ea580c"
