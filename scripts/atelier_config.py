"""Atelier config loader — merges a repo-ROOT `.atelier.json` over the legacy
`design/atelier.config.json`.

Two config locations are supported, merged with the ROOT file winning:

  1. ``design/atelier.config.json`` (legacy; the ``check`` section CI already reads)
  2. ``.atelier.json`` at the repo root (new; project-level overrides)

The merge is shallow per top-level section but deep for the nested ``check`` and
``checks``/``rules`` objects, so a root file can override a single threshold or
toggle a single step without restating the whole config. When neither file
exists, ``load_config`` returns ``{}`` and callers fall back to their built-in
defaults — exactly the pre-existing behavior.

Schema (all optional):

    {
      "check": {                 # thresholds (same keys as today)
        "max_drift": 0,
        "max_overlap_risk": 0,
        "allow_contrast_fail": false,
        "drift_baseline": 0      # written by --update-baseline (untouched here)
      },
      "checks": {                # (alias: "rules") toggle gate STEPS on/off
        "design-lint": true,
        "contrast-audit": true,
        "house-rules": true,
        "overlap-risk": true
      }
    }
"""
import json
import os

# The four gate steps a config may toggle. Anything else under `checks`/`rules`
# is ignored (forward-compatible).
GATE_STEPS = ("design-lint", "contrast-audit", "house-rules", "overlap-risk")


def _read_json(path):
    """Return parsed JSON dict at *path*, or {} if missing/empty/not-a-dict.
    A corrupt file raises (callers that care can catch) — but a missing file is
    simply {} so the no-config path stays clean."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _deep_merge(base, over):
    """Return base merged with over; nested dicts merged recursively, over wins."""
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(repo):
    """Load and merge atelier config for *repo*.

    Reads ``design/atelier.config.json`` (legacy) then ``.atelier.json`` (root),
    deep-merging the second OVER the first. Returns the merged dict (possibly
    empty). The two known nested objects (``check`` thresholds and
    ``checks``/``rules`` toggles) are merged key-by-key so a root file can
    override one value without restating the section.
    """
    legacy = _read_json(os.path.join(repo, "design", "atelier.config.json"))
    root = _read_json(os.path.join(repo, ".atelier.json"))
    return _deep_merge(legacy, root)


def check_section(repo, cfg=None):
    """Return the merged ``check`` thresholds object ({} if none)."""
    cfg = load_config(repo) if cfg is None else cfg
    sec = cfg.get("check", {})
    return sec if isinstance(sec, dict) else {}


def step_enabled(name, cfg):
    """Return whether gate STEP *name* is enabled per *cfg* (default True).

    Honors a ``checks`` object, falling back to ``rules`` as an alias. An entry
    must be explicitly ``false`` to disable a step; anything else (missing, true,
    non-bool) leaves it enabled.
    """
    toggles = cfg.get("checks")
    if not isinstance(toggles, dict):
        toggles = cfg.get("rules")
    if not isinstance(toggles, dict):
        return True
    return toggles.get(name, True) is not False
