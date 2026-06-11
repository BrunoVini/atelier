"""`.atelier.json` (repo root) merges OVER design/atelier.config.json."""
import json
import os

from atelier_config import load_config, check_section, step_enabled


def _legacy(tmp_path, obj):
    (tmp_path / "design").mkdir(exist_ok=True)
    (tmp_path / "design" / "atelier.config.json").write_text(json.dumps(obj))


def _root(tmp_path, obj):
    (tmp_path / ".atelier.json").write_text(json.dumps(obj))


def test_missing_files_yield_empty_defaults(tmp_path):
    cfg = load_config(str(tmp_path))
    assert cfg == {}
    assert check_section(str(tmp_path)) == {}
    # all steps default enabled
    for name in ("design-lint", "contrast-audit", "house-rules", "overlap-risk"):
        assert step_enabled(name, cfg) is True


def test_legacy_only_is_read(tmp_path):
    _legacy(tmp_path, {"check": {"max_drift": 3, "allow_contrast_fail": True}})
    sec = check_section(str(tmp_path))
    assert sec["max_drift"] == 3
    assert sec["allow_contrast_fail"] is True


def test_root_overrides_legacy_per_key(tmp_path):
    _legacy(tmp_path, {"check": {"max_drift": 3, "max_overlap_risk": 5}})
    _root(tmp_path, {"check": {"max_drift": 0}})       # override one key only
    sec = check_section(str(tmp_path))
    assert sec["max_drift"] == 0                        # root wins
    assert sec["max_overlap_risk"] == 5                 # legacy key preserved (deep merge)


def test_root_only_works_without_legacy(tmp_path):
    _root(tmp_path, {"check": {"max_drift": 7}})
    assert check_section(str(tmp_path))["max_drift"] == 7


def test_checks_toggle_parsed(tmp_path):
    _root(tmp_path, {"checks": {"contrast-audit": False, "overlap-risk": False}})
    cfg = load_config(str(tmp_path))
    assert step_enabled("contrast-audit", cfg) is False
    assert step_enabled("overlap-risk", cfg) is False
    assert step_enabled("design-lint", cfg) is True     # unspecified -> enabled
    assert step_enabled("house-rules", cfg) is True


def test_rules_alias_for_checks(tmp_path):
    _root(tmp_path, {"rules": {"design-lint": False}})
    cfg = load_config(str(tmp_path))
    assert step_enabled("design-lint", cfg) is False


def test_root_toggle_overrides_legacy_toggle(tmp_path):
    _legacy(tmp_path, {"checks": {"house-rules": False}})
    _root(tmp_path, {"checks": {"house-rules": True}})
    cfg = load_config(str(tmp_path))
    assert step_enabled("house-rules", cfg) is True


def test_non_dict_toplevel_json_is_ignored(tmp_path):
    # a top-level JSON that isn't an object (e.g. a list) must read as {}, not the list
    (tmp_path / ".atelier.json").write_text('["not", "a", "dict"]')
    cfg = load_config(str(tmp_path))
    assert cfg == {}
    assert check_section(str(tmp_path)) == {}
