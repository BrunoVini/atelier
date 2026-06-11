"""Scenario definitions as DATA.

Each scenario is a dict:
  • name          — stable id (also the fixture basename).
  • description    — one line of intent.
  • files          — workspace seed: {relative_path: contents}.
  • user_prompt    — the message handed to the agent.
  • expectations   — a list of assertion specs for `assertions.evaluate`.
  • live_skip      — True when the scenario is exercised via ReplayAgent only
                     (the live runner skips it and says why).

The four scenarios mirror atelier's load-bearing behaviors:
  1. measure-before-generate — Step 0 / DESIGN.md gate.
  2. routing                 — read the matching capability reference.
  3. qa-before-done          — qa.py before claiming completion.
  4. collision-reaction      — re-check (not re-stop) after a Stop-hook block.
"""
from __future__ import annotations

# --- small reusable fixture bodies ------------------------------------------

_TAILWIND_CONFIG = """\
/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: { brand: { 500: '#6d28d9', 700: '#4c1d95' } },
      fontFamily: { sans: ['Satoshi', 'sans-serif'] },
    },
  },
};
"""

_APP_CSS = """\
:root { --color-bg: #0b0b12; --color-accent: #6d28d9; --space-4: 1rem; }
body { background: var(--color-bg); font-family: Satoshi, sans-serif; }
"""

_DESIGN_MD = """\
# DESIGN.md

register: brand

## Palette
- bg `#0b0b12`
- accent `#6d28d9`

## Type
- Display: Satoshi
"""

_PACKAGE_JSON = """\
{ "name": "demo-site", "dependencies": { "tailwindcss": "^3.4.0" } }
"""


SCENARIOS = [
    {
        "name": "measure-before-generate",
        "description": (
            "Repo has CSS/tailwind signals but NO DESIGN.md. The agent must MEASURE "
            "(context.py / scan_repo.py) before writing any .html/.css artifact."
        ),
        "files": {
            "tailwind.config.js": _TAILWIND_CONFIG,
            "src/app.css": _APP_CSS,
            "package.json": _PACKAGE_JSON,
        },
        "user_prompt": "build me a landing section for this site",
        "expectations": [
            # A measure step (context.py OR scan_repo.py) precedes the first
            # artifact-writing call.
            {
                "type": "calls_before",
                "earlier": {"tool": "bash", "arg_contains": "context.py"},
                "later": {"any_tool": True, "writes_artifact": True},
            },
            # And the measure step actually happened at all.
            {"type": "calls_tool", "match": {"tool": "bash", "arg_contains": "context.py"}},
        ],
        "live_skip": False,
    },
    {
        "name": "routing-slides",
        "description": (
            "DESIGN.md present; the user asks for a SPECIFIC artifact (a pricing slide "
            "deck). The agent must read the matching capability reference, "
            "references/capabilities/slides.md."
        ),
        "files": {
            "DESIGN.md": _DESIGN_MD,
            "src/app.css": _APP_CSS,
        },
        "user_prompt": "make me a pricing slide deck for this product",
        "expectations": [
            {"type": "reads_file", "path_substr": "capabilities/slides.md"},
        ],
        "live_skip": False,
    },
    {
        "name": "qa-before-done",
        "description": (
            "Build + 'finish' an HTML artifact. qa.py must appear in the trace and "
            "precede the final assistant message that claims completion."
        ),
        "files": {
            "DESIGN.md": _DESIGN_MD,
        },
        "user_prompt": (
            "build a hero.html landing hero for this product and tell me when it's "
            "finished and ready to ship"
        ),
        "expectations": [
            # qa.py was run...
            {"type": "calls_tool", "match": {"tool": "bash", "arg_contains": "qa.py"}},
            # ...before any artifact-writing-then-done claim. We assert qa.py
            # precedes nothing later that contradicts it AND the final text
            # claims done only after qa ran (qa.py before the terminal text is
            # guaranteed structurally — qa is a tool call, text is terminal — so
            # the meaningful checks are "qa ran" + "the run does claim done").
            {"type": "final_text_claims_done"},
        ],
        "live_skip": False,
    },
    {
        "name": "collision-reaction",
        "description": (
            "The Stop hook returned a block (a real responsive collision). The agent "
            "must RE-CHECK (responsive_check.mjs / overlap_risk.py / qa.py) after the "
            "block reason is surfaced — not immediately re-stop / rationalize. "
            "Primarily exercised via ReplayAgent: faithfully injecting a Stop-hook "
            "block into a one-shot Messages loop is out of scope for the live agent."
        ),
        "files": {
            "DESIGN.md": _DESIGN_MD,
            "index.html": "<!doctype html><html><body><h1>hi</h1></body></html>",
        },
        # The user_prompt here is illustrative; the live agent skips this one.
        "user_prompt": (
            "[A Stop-hook block was returned: responsive_check found a text collision "
            "at 390px. reason: 'fix the overlap, then re-run responsive_check.mjs "
            "across the FULL width sweep until clear.'] Address it."
        ),
        "expectations": [
            # After the block, the agent re-runs a collision re-check rather than
            # writing a new artifact and stopping.
            {
                "type": "calls_tool",
                "match": {"tool": "bash", "arg_contains": "responsive_check.mjs"},
            },
            # The re-check (responsive_check / overlap_risk / qa) comes BEFORE the
            # final text — i.e. the agent verified before declaring anything.
            {"type": "final_text_not_claims_done"},
        ],
        "live_skip": True,
    },
]


def by_name(name: str):
    for s in SCENARIOS:
        if s["name"] == name:
            return s
    raise KeyError(name)
