"""Step-0 context resolver (Phase 3).

context.py is a thin orchestrator over contract.resolve_contract/validate_contract
(register parsing) and scan_repo.detect_token_source/detect_framework. These prove:

  - a repo with a valid DESIGN.md contract -> design_md path, contract_valid True,
    register surfaced, next = "load DESIGN.md as contract";
  - a repo with CSS but NO DESIGN.md -> has_design_signals True, contract null,
    next = offer to generate;
  - an empty/nonexistent dir -> all nulls, no crash, valid JSON shape.
"""
import json
import subprocess
import sys
from context import resolve_context


_CONTRACT_MD = (
    "# DESIGN\n\n"
    "```json atelier-contract\n"
    '{"register":"product","colors":{"bg":"#0a0a0a","fg":"#ffffff"},"fonts":["Sora"]}\n'
    "```\n"
)


def test_repo_with_valid_design_md(tmp_path):
    (tmp_path / "DESIGN.md").write_text(_CONTRACT_MD, encoding="utf-8")
    (tmp_path / "styles.css").write_text(":root{--color-bg:#0a0a0a}\n", encoding="utf-8")
    ctx = resolve_context(str(tmp_path))
    assert ctx["design_md"] == str(tmp_path / "DESIGN.md")
    assert ctx["contract_valid"] is True
    assert ctx["register"] == "product"
    assert ctx["has_design_signals"] is True
    assert ctx["next"] == "load DESIGN.md as contract"


def test_repo_with_css_but_no_design_md(tmp_path):
    (tmp_path / "main.css").write_text("body{color:#123456;font-family:Sora}\n", encoding="utf-8")
    ctx = resolve_context(str(tmp_path))
    assert ctx["design_md"] is None
    assert ctx["contract_valid"] is None
    assert ctx["register"] is None
    assert ctx["has_design_signals"] is True
    assert ctx["next"] == "offer to generate DESIGN.md (signals present)"


def test_empty_dir_all_nulls(tmp_path):
    ctx = resolve_context(str(tmp_path))
    assert ctx["design_md"] is None
    assert ctx["contract_valid"] is None
    assert ctx["register"] is None
    assert ctx["token_source"] is None
    assert ctx["framework"] is None
    assert ctx["has_design_signals"] is False
    assert "no contract" in ctx["next"]


def test_nonexistent_dir_does_not_crash(tmp_path):
    ctx = resolve_context(str(tmp_path / "does-not-exist"))
    assert ctx["contract_valid"] is None
    assert ctx["has_design_signals"] is False
    assert ctx["next"]   # a non-empty next step, no traceback


def test_framework_detected_from_package_json(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"next": "14.0.0", "react": "18.0.0"}}), encoding="utf-8")
    (tmp_path / "app.css").write_text("body{color:#222}", encoding="utf-8")
    ctx = resolve_context(str(tmp_path))
    assert ctx["framework"] == "next"        # meta-framework beats react
    assert ctx["has_design_signals"] is True


def test_cli_emits_valid_json(tmp_path):
    import os
    (tmp_path / "DESIGN.md").write_text(_CONTRACT_MD, encoding="utf-8")
    script = os.path.join(os.path.dirname(__file__), "..", "scripts", "context.py")
    r = subprocess.run([sys.executable, script, str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0
    parsed = json.loads(r.stdout)            # must be valid JSON
    assert parsed["register"] == "product"
