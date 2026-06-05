"""`atelier check` — design QA gate for CI / pre-commit.

Runs the contract checks (drift lint + contrast audit) and exits non-zero on
failure, so design coherence becomes a merge gate like tests. Thresholds come
from design/atelier.config.json (or sensible defaults).

Usage:
    python3 check.py <repo> [--contract design/design-tokens.json] [--max-drift N]
"""
import json
import os
import sys

from lint_design import lint_repo
from audit_contrast import audit, _load_colors
from check_rules import check as check_house_rules


def run(repo, contract, max_drift=0, allow_contrast_fail=False):
    results = {"ok": True, "steps": []}

    drift = lint_repo(repo, contract)
    drift_ok = len(drift) <= max_drift
    results["steps"].append({"step": "design-lint", "findings": len(drift), "ok": drift_ok})
    results["ok"] &= drift_ok

    colors = _load_colors(contract)
    fails = [r for r in audit(colors) if not r["aa_large"] and not r.get("informational")]
    contrast_ok = allow_contrast_fail or not fails
    results["steps"].append({"step": "contrast-audit", "fails": len(fails), "ok": contrast_ok})
    results["ok"] &= contrast_ok

    # House rules from DESIGN.md §9 (e.g. "no flyouts, only modals").
    rule_violations = []
    design = os.path.join(repo, "DESIGN.md")
    if os.path.exists(design):
        rule_violations, _requires, _forbids = check_house_rules(repo, design)
    rules_ok = not rule_violations
    results["steps"].append({"step": "house-rules", "violations": len(rule_violations), "ok": rules_ok})
    results["ok"] &= rules_ok

    results["drift"] = drift
    results["contrast_fails"] = [f"{r['text']} on {r['surface']} ({r['ratio']}:1)" for r in fails]
    results["rule_violations"] = rule_violations
    return results


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args:
        print("usage: check.py <repo> [--contract <json>] [--max-drift N] [--allow-contrast-fail]")
        sys.exit(2)
    repo = args[0]
    contract = args[args.index("--contract") + 1] if "--contract" in args else os.path.join(repo, "design", "design-tokens.json")
    cfg_path = os.path.join(repo, "design", "atelier.config.json")
    cfg = json.load(open(cfg_path)).get("check", {}) if os.path.exists(cfg_path) else {}
    max_drift = int(args[args.index("--max-drift") + 1]) if "--max-drift" in args else cfg.get("max_drift", 0)
    allow_contrast = "--allow-contrast-fail" in args or cfg.get("allow_contrast_fail", False)
    if not os.path.exists(contract):
        print(f"::error:: no contract at {contract} — run generate-design-md first")
        sys.exit(2)
    res = run(repo, contract, max_drift, allow_contrast)
    for s in res["steps"]:
        print(f"  [{'PASS' if s['ok'] else 'FAIL'}] {s['step']}: {json.dumps({k:v for k,v in s.items() if k not in ('step','ok')})}")
    for d in res["drift"][:20]:
        print(f"    drift {d['file']}:{d['line']} {d['value']} → {d['fix']}")
    for c in res["contrast_fails"]:
        print(f"    contrast {c}")
    for v in res.get("rule_violations", [])[:20]:
        tip = f" → use {v['prefer']}" if v.get("prefer") else ""
        print(f"    house-rule {v['file']}:{v['line']} forbidden '{v['forbidden']}'{tip}")
    print("\natelier check:", "PASS" if res["ok"] else "FAIL")
    sys.exit(0 if res["ok"] else 1)
