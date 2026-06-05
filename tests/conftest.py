"""Make the scripts importable regardless of where the skill lives.

Tests import `scan_repo` / `export_tokens` / `search_kb` directly, so this works
whether the skill sits at a repo root or as a subdirectory. Run with:

    python3 -m pytest atelier/tests/ -v      # (from the parent of atelier/)
    cd atelier && python3 -m pytest tests/   # (from the skill root)
"""
import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
