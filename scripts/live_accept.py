"""The qa-gated accept flow for live mode (Phase 7) — the atelier differentiator.

A competing live-mode (impeccable) accepts a tweak straight into source. atelier GATES
it: on accept we apply the edit via edit_apply (journaled, reversible, generated-file
guarded), then run qa.py on the affected artifact, and if qa FAILS we AUTO-REVERT so a
bad variant can never stick in the user's source. The gate is the whole point, so this
lives in Python — unit-testable WITHOUT the browser or the proxy. The .cjs control
endpoint just shells `accept_variant`.

Scope (deliberately not magic): accept takes the explicit `file` + `old` anchor the
caller/agent provides; we do NOT build fragile CSS-rule-to-source mapping. The unique-
anchor safety in edit_apply.apply_edit is what makes a supplied anchor safe — `old` must
occur exactly once. The caller supplies `qa_target` (the artifact or repo dir to QA).

Usage (the proxy shells this; also runnable directly):
    python3 live_accept.py <file> --old <s> --new <s> --qa-target <html|dir> \\
        --journal-dir <dir> --session <id> [--contract <repo|tokens>] [--register r]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

import edit_apply  # noqa: E402  (same dir; conftest/run.py put scripts/ on the path)


# ── pluggable variant agent (Phase 7 #4) ─────────────────────────────────────
# Mirrors Phase 4's pattern: a thin agent interface for GENERATING variant proposals,
# with a deterministic default and a slot for an LLM agent later — NO LLM dependency.
# The real work already lives in edit_apply's on-contract engine (build_variants), so the
# default agent is a one-line delegate; an LLM agent would implement the same .propose()
# signature and still be funneled through the same on-contract guard.

class OnContractAgent:
    """Deterministic, dependency-free variant agent: delegates to the contract-bound
    engine in edit_apply. Every proposal it returns is already proven on-contract by
    build_variants' guard, so the accept gate is the ONLY thing that can reject it."""

    def propose(self, current, contract, mode="steps", prop=None, n=3):
        return edit_apply.build_variants(current, contract, mode, prop=prop, n=n)


def get_agent(name="on-contract"):
    """Return a variant agent by name. Today only the deterministic on-contract agent
    exists; this is the seam where an LLM-backed agent would slot in later (it would
    implement the same .propose() and feed build_variants' guard, never bypass it)."""
    if name in (None, "on-contract", "default"):
        return OnContractAgent()
    raise ValueError(f"unknown variant agent: {name!r}")


def _run_qa(qa_target, contract=None, register=None, timeout=200):
    """Run qa.py --json on `qa_target` and return (verdict, results_list). The static
    path runs with no browser (rendered checks come back `unknown` and never gate), so
    this is deterministic offline — slop/contrast/overlap still gate. Returns
    ('UNKNOWN', []) only if qa.py itself could not be run/parsed (never silently passes)."""
    cmd = [sys.executable, os.path.join(HERE, "qa.py"), qa_target, "--json"]
    if contract:
        cmd += ["--contract", contract]
    if register:
        cmd += ["--register", register]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return "UNKNOWN", [{"name": "qa", "status": "unknown", "detail": str(e)}]
    out = p.stdout or ""
    try:
        results = json.loads(out[out.index("["):out.rindex("]") + 1])
    except (ValueError, IndexError):
        return "UNKNOWN", [{"name": "qa", "status": "unknown",
                            "detail": (p.stderr or out).strip()[-500:]}]
    # Mirror qa.verdict: FAIL iff a gating check actually failed; unknown never gates.
    failed = any(r.get("gating") and r.get("status") == "fail" for r in results)
    return ("FAIL" if failed else "PASS"), results


def accept_variant(file, old, new, qa_target, journal_dir, session,
                   register=None, contract=None, label=None, rationale=None, now=None):
    """Apply a variant to source, QA it, and auto-revert on failure.

    Flow:
      (a) edit_apply.accept(file, old, new, …)  — journaled, reversible, refuses
          generated files, requires a unique `old` anchor;
      (b) run qa.py on `qa_target` (static path works offline);
      (c) if qa FAILS, edit_apply.revert the edit so the source is byte-restored, and
          return the failure so the picker shows it and the bad variant never sticks;
      (d) if qa PASSES, keep it; the session accept is already recorded by step (a).

    Returns {ok, qa, reverted, journal_id?, reason?}:
      • ok True  -> edit applied AND qa passed (kept).
      • ok False, reverted True  -> edit applied but qa failed; auto-reverted.
      • ok False, reverted False -> edit never applied (anchor/guard rejected it),
        nothing to revert.
    A qa verdict of UNKNOWN does NOT auto-revert (we don't trust a null we can't
    explain — same contract as qa.py's `unknown`); it's reported and the edit is kept."""
    applied = edit_apply.accept(file, old, new, journal_dir, session,
                                label=label, rationale=rationale, now=now)
    if not applied.get("ok"):
        # The edit never landed (generated file / anchor not found / not unique). No
        # write happened, so there is nothing to revert.
        return {"ok": False, "reverted": False, "qa": None,
                "reason": applied.get("reason", "edit rejected")}

    journal_id = applied["journal_id"]
    qa_verdict, qa_results = _run_qa(qa_target, contract=contract, register=register)

    if qa_verdict == "FAIL":
        rev = edit_apply.revert(journal_dir, journal_id)
        return {"ok": False, "reverted": bool(rev.get("ok")), "qa": qa_verdict,
                "qa_results": qa_results, "journal_id": journal_id,
                "revert": rev,
                "reason": "qa failed — auto-reverted; variant did not stick"}

    # PASS or UNKNOWN: keep the edit (UNKNOWN never gates, so it never reverts).
    return {"ok": True, "reverted": False, "qa": qa_verdict,
            "qa_results": qa_results, "journal_id": journal_id}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="qa-gated accept for live mode")
    ap.add_argument("file")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--qa-target", required=True, help="artifact .html or repo dir to QA")
    ap.add_argument("--journal-dir", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--contract")
    ap.add_argument("--register", choices=("brand", "product"))
    ap.add_argument("--label")
    ap.add_argument("--rationale")
    ns = ap.parse_args()
    res = accept_variant(ns.file, ns.old, ns.new, ns.qa_target, ns.journal_dir,
                         ns.session, register=ns.register, contract=ns.contract,
                         label=ns.label, rationale=ns.rationale)
    print(json.dumps(res))
    sys.exit(0 if res.get("ok") else 1)
