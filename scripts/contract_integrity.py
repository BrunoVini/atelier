"""Contract-integrity governance.

A design-token contract is a *governed* artifact, not just config: a change that
WIDENS it (adds a color role) or NARROWS it (removes one) is a design-system
decision that must be reviewed, not slipped in. The common abuse this catches is
*laundering* an off-token or low-contrast color by simply declaring a new role
for it in `design/design-tokens.json` — the downstream drift/contrast steps may
then accept the now-"legal" token. Governing the role SET against a committed
baseline closes that hole.

Two checks, both gated only when a baseline is committed:

  • contract-drift   — a color role added to / removed from the contract vs the
                       committed baseline (`design/.contract-baseline.json`).
  • contract-mirror  — a `--color-<role>` in src/styles/tokens.css whose hex
                       disagrees with the contract (the CSS mirror silently
                       diverged from the source of truth).

When no baseline file is committed the whole step is a NO-OP and returns ``[]`` —
so existing repos (and every other test) are byte-for-byte unaffected. Adopt the
governance by committing the current contract as the baseline:

    cp design/design-tokens.json design/.contract-baseline.json

Findings use the codebase's standard drift shape
``{"file", "line", "value", "kind", "severity", "fix", "detail"}`` so they ride
SARIF, suppression, and the gate's verdict like any other finding.
"""
import json
import os
import re

from contract import resolve_contract

BASELINE_NAME = ".contract-baseline.json"

_COLOR_VAR = re.compile(r"--color-([\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})")


def _norm(h):
    h = h.strip().lower()
    if len(h) == 4:                       # #abc -> #aabbcc
        h = "#" + "".join(c * 2 for c in h[1:])
    if len(h) == 9:                       # #rrggbbaa -> drop alpha for comparison
        h = h[:7]
    return h


def _line_of(path, role):
    """1-based line of the role's declaration in a JSON/CSS file, else 1."""
    try:
        for idx, line in enumerate(open(path, encoding="utf-8"), start=1):
            if f'"{role}"' in line or re.search(rf"--color-{re.escape(role)}\s*:", line):
                return idx
    except OSError:
        pass
    return 1


def check_contract_integrity(repo, contract_path=None, baseline_path=None):
    """Return contract-integrity drift findings for *repo* (``[]`` if no baseline).

    *contract_path* / *baseline_path* default to ``design/design-tokens.json`` and
    ``design/.contract-baseline.json`` under *repo*. A missing or corrupt baseline
    degrades to a no-op (returns ``[]``) — never raises.
    """
    design = os.path.join(repo, "design")
    json_path = contract_path or os.path.join(design, "design-tokens.json")
    base_path = baseline_path or os.path.join(design, BASELINE_NAME)

    if not os.path.isfile(base_path):
        return []                          # governance not adopted -> no-op
    try:
        cur = resolve_contract(json_path)
        base = resolve_contract(base_path)
    except Exception:
        return []                          # corrupt/unreadable -> degrade silently

    cur_colors = cur.get("colors", {}) or {}
    base_colors = base.get("colors", {}) or {}
    cur_roles = set(cur_colors)
    base_roles = set(base_colors)

    findings = []
    rel_json = os.path.relpath(json_path, repo)

    for role in sorted(cur_roles - base_roles):       # widened
        findings.append({
            "file": rel_json, "line": _line_of(json_path, role),
            "value": f'"{role}": "{cur_colors[role]}"', "kind": "contract-drift",
            "severity": "important",
            "detail": f"color role '{role}' was ADDED to the contract (the palette "
                      "was widened) — not present in the committed baseline",
            "fix": "Map the design to an existing role instead. A genuine palette "
                   "change is a governance event: update design/.contract-baseline.json "
                   "in the same PR so the addition is reviewed explicitly.",
        })
    for role in sorted(base_roles - cur_roles):       # narrowed
        findings.append({
            "file": rel_json, "line": 1,
            "value": f'(removed role) "{role}"', "kind": "contract-drift",
            "severity": "important",
            "detail": f"color role '{role}' was REMOVED from the contract "
                      "(present in the committed baseline)",
            "fix": f"Restore '{role}', or ratify its removal by updating "
                   "design/.contract-baseline.json in the same PR.",
        })

    # tokens.css ↔ contract mirror: a --color-<role> whose hex disagrees with the
    # contract value for that role (the CSS mirror silently diverged).
    tokens_css = os.path.join(repo, "src", "styles", "tokens.css")
    if os.path.isfile(tokens_css):
        rel_css = os.path.relpath(tokens_css, repo)
        try:
            for idx, line in enumerate(open(tokens_css, encoding="utf-8"), start=1):
                m = _COLOR_VAR.search(line)
                if not m:
                    continue
                role, css_hex = m.group(1), _norm(m.group(2))
                want = cur_colors.get(role)
                if want is not None and _norm(want) != css_hex:
                    findings.append({
                        "file": rel_css, "line": idx,
                        "value": f"--color-{role}: {css_hex}", "kind": "contract-mirror",
                        "severity": "important",
                        "detail": f"tokens.css value for '{role}' ({css_hex}) does not "
                                  f"match the contract ({_norm(want)})",
                        "fix": f"Sync --color-{role} in {rel_css} to {_norm(want)} "
                               f"(or update {rel_json} if the new value is intended).",
                    })
        except OSError:
            pass

    return findings


if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    out = check_contract_integrity(repo)
    for f in out:
        print(f"  {f['kind']} {f['file']}:{f['line']} {f['value']} — {f['fix']}")
    print(f"\ncontract-integrity: {len(out)} finding(s)")
    sys.exit(1 if out else 0)
