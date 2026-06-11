"""The assertion engine — pure functions over a Trace.

This is the part that is unit-tested offline (via ReplayAgent + fixtures). It
knows nothing about Anthropic, networks, or workspaces: it takes a `Trace` and
an `expectations` spec (plain data from `scenarios.py`) and returns a structured
verdict with a human-readable reason.

An `expectations` spec is a list of assertion dicts, e.g.:

    {"type": "calls_before", "earlier": {...matcher...}, "later": {...matcher...}}
    {"type": "calls_tool",   "match": {...matcher...}}
    {"type": "not_before",   "earlier": {...matcher...}, "later": {...matcher...}}
    {"type": "reads_file",   "path_substr": "slides.md"}
    {"type": "final_text_claims_done"}
    {"type": "final_text_not_claims_done"}

A *matcher* describes which tool calls count, e.g.:

    {"tool": "bash", "arg_contains": "context.py"}      # a bash call mentioning context.py
    {"any_tool": True, "writes_artifact": True}          # any call that creates an .html/.css
    {"tool": "read", "arg_contains": "slides.md"}

The engine treats a `bash` command that invokes a script as equivalent to the
named tool (the model may `cat`/`python3` a path through bash rather than the
dedicated read tool — both count). Ordering assertions use the *first* matching
index on each side.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agent import Trace, ToolCall

# Patterns that indicate the agent produced/created a visual artifact.
_ARTIFACT_PATH = re.compile(r"\.(html?|css|scss|svelte|jsx?|tsx?|vue|astro)$", re.IGNORECASE)
# Phrases in the FINAL assistant text that claim the work is finished/shippable.
_DONE_CLAIM = re.compile(
    r"\b(done|finished|complete[d]?|ready|ship(?:ped|pable)?|all set|good to go|"
    r"here'?s your|polished and ready|passes? qa|qa pass(?:ed|es)?)\b",
    re.IGNORECASE,
)


@dataclass
class Verdict:
    ok: bool
    reason: str

    def __bool__(self) -> bool:
        return self.ok


# --- low-level matchers ------------------------------------------------------

def _call_text(call: ToolCall) -> str:
    """Flatten a call's args into one searchable string (command, path, etc.)."""
    parts = [call.name]
    for v in call.args.values():
        if isinstance(v, str):
            parts.append(v)
    return " ".join(parts)


def _writes_artifact(call: ToolCall) -> bool:
    """True if this call CREATES a visual artifact file (.html/.css/...).

    A `write` whose path is an artifact, OR a `bash` that redirects/heredocs/
    `cp`/`mv`/`tee`s into an artifact path. We look for an artifact-extension
    path anywhere in the call text but require a write-ish signal for bash so a
    mere `cat artifact.html` (a read) does not count as producing one.
    """
    if call.name == "write":
        return bool(_ARTIFACT_PATH.search(str(call.args.get("path", ""))))
    if call.name == "bash":
        cmd = str(call.args.get("command", ""))
        if not _ARTIFACT_PATH.search(cmd):
            return False
        # write-ish: output redirection, tee, cp/mv into, or a heredoc.
        return bool(re.search(r"(>>?|\btee\b|\bcp\b|\bmv\b|<<\s*['\"]?\w)", cmd))
    return False


def _matches(call: ToolCall, matcher: Dict[str, Any]) -> bool:
    if matcher.get("writes_artifact"):
        if not _writes_artifact(call):
            return False
    tool = matcher.get("tool")
    if tool and not matcher.get("any_tool"):
        if call.name != tool:
            return False
    substr = matcher.get("arg_contains")
    if substr:
        if substr.lower() not in _call_text(call).lower():
            return False
    return True


def _first_index(trace: Trace, matcher: Dict[str, Any]) -> Optional[int]:
    return trace.first_index(lambda c: _matches(c, matcher))


def _describe(matcher: Dict[str, Any]) -> str:
    bits = []
    if matcher.get("writes_artifact"):
        bits.append("an artifact-writing call")
    if matcher.get("tool"):
        bits.append(f"a {matcher['tool']} call")
    if matcher.get("arg_contains"):
        bits.append(f"mentioning {matcher['arg_contains']!r}")
    return " ".join(bits) or "a matching call"


# --- public helpers (also usable directly in tests) -------------------------

def calls_tool(trace: Trace, matcher: Dict[str, Any]) -> bool:
    return _first_index(trace, matcher) is not None


def calls_before(trace: Trace, earlier: Dict[str, Any], later: Dict[str, Any]) -> bool:
    """True iff `earlier` occurs AND occurs before the first `later` (or `later`
    never occurs but `earlier` does — i.e. the measure step happened and no
    artifact was written, which still satisfies measure-before-generate)."""
    ei = _first_index(trace, earlier)
    if ei is None:
        return False
    li = _first_index(trace, later)
    return li is None or ei < li


def final_text_claims_done(trace: Trace) -> bool:
    return bool(_DONE_CLAIM.search(trace.final_text or ""))


# --- spec evaluator ----------------------------------------------------------

def _eval_one(trace: Trace, spec: Dict[str, Any]) -> Verdict:
    t = spec["type"]

    if t == "calls_tool":
        m = spec["match"]
        if calls_tool(trace, m):
            return Verdict(True, f"found {_describe(m)}")
        return Verdict(False, f"expected {_describe(m)}, but no call matched")

    if t == "calls_before":
        e, l = spec["earlier"], spec["later"]
        ei = _first_index(trace, e)
        if ei is None:
            return Verdict(False, f"expected {_describe(e)} (the 'earlier' step) but it never happened")
        li = _first_index(trace, l)
        if li is None:
            return Verdict(True, f"{_describe(e)} happened and {_describe(l)} never did (ordering vacuously holds)")
        if ei < li:
            return Verdict(True, f"{_describe(e)} (idx {ei}) precedes {_describe(l)} (idx {li})")
        return Verdict(False, f"{_describe(e)} (idx {ei}) did NOT precede {_describe(l)} (idx {li})")

    if t == "not_before":
        # Assert `earlier` does NOT come before `later` — used for negative checks.
        e, l = spec["earlier"], spec["later"]
        ei = _first_index(trace, e)
        li = _first_index(trace, l)
        if ei is None:
            return Verdict(True, f"{_describe(e)} never happened, so it cannot precede {_describe(l)}")
        if li is None:
            return Verdict(False, f"{_describe(e)} happened but {_describe(l)} never did")
        if ei >= li:
            return Verdict(True, f"{_describe(e)} (idx {ei}) does not precede {_describe(l)} (idx {li})")
        return Verdict(False, f"{_describe(e)} (idx {ei}) WRONGLY precedes {_describe(l)} (idx {li})")

    if t == "reads_file":
        sub = spec["path_substr"]
        m = {"any_tool": True, "arg_contains": sub}
        if calls_tool(trace, m):
            return Verdict(True, f"a call references {sub!r}")
        return Verdict(False, f"expected a call referencing {sub!r}, none found")

    if t == "final_text_claims_done":
        if final_text_claims_done(trace):
            return Verdict(True, "final assistant text claims completion")
        return Verdict(False, "final assistant text does not claim completion")

    if t == "final_text_not_claims_done":
        if not final_text_claims_done(trace):
            return Verdict(True, "final assistant text does not (prematurely) claim completion")
        return Verdict(False, "final assistant text prematurely claims completion")

    raise ValueError(f"unknown expectation type: {t!r}")


def evaluate(trace: Trace, expectations: List[Dict[str, Any]]) -> Verdict:
    """Evaluate every expectation; PASS iff all pass. Reason aggregates the
    individual results so a failure points at the exact assertion that broke."""
    results = [(spec, _eval_one(trace, spec)) for spec in expectations]
    failures = [(s, v) for (s, v) in results if not v.ok]
    if not failures:
        reasons = "; ".join(v.reason for (_s, v) in results)
        return Verdict(True, f"all {len(results)} expectation(s) held: {reasons}")
    lead = failures[0][1].reason
    detail = "; ".join(f"[{s['type']}] {v.reason}" for (s, v) in failures)
    return Verdict(False, f"{len(failures)}/{len(results)} expectation(s) failed: {lead} :: ({detail})")
