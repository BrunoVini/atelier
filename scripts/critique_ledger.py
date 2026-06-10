"""Persisted critique snapshots + trend (#9).

A one-shot review is a number you forget; a tracked metric is a backlog. Record each
review's 5-dimension scorecard (see review.md) per artifact, and report the trend so the
next pass knows whether the design got better or worse. Pairs with the review discipline
(two isolated assessors: LLM judgment vs. detector evidence — see review.md §"Rigor").

    python3 critique_ledger.py record <artifact> contract=8 hierarchy=7 detail=6 functionality=9 innovation=7
    python3 critique_ledger.py trend  <artifact>
"""
import json
import os
import sys

DIMENSIONS = ["contract", "hierarchy", "detail", "functionality", "innovation"]
DEFAULT_LEDGER = os.environ.get("ATELIER_CRITIQUE_LEDGER") or os.path.expanduser("~/.atelier/critique.jsonl")


def record(artifact, scores, ledger=DEFAULT_LEDGER):
    row = {"artifact": artifact, "scores": {d: float(scores[d]) for d in DIMENSIONS if d in scores}}
    row["total"] = round(sum(row["scores"].values()), 2)
    os.makedirs(os.path.dirname(ledger) or ".", exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def load(ledger=DEFAULT_LEDGER):
    """Tolerant: a torn/malformed line never kills the trend."""
    if not os.path.exists(ledger):
        return []
    out = []
    for line in open(ledger, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict) and "artifact" in row and "total" in row:
                out.append(row)
        except Exception:
            pass
    return out


def trend(artifact, ledger=DEFAULT_LEDGER):
    """Latest total minus the previous total for `artifact`, or None if < 2 snapshots."""
    totals = [r["total"] for r in load(ledger) if r.get("artifact") == artifact]
    return round(totals[-1] - totals[-2], 2) if len(totals) >= 2 else None


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "record":
        scores = dict(kv.split("=", 1) for kv in a[2:] if "=" in kv)
        print(json.dumps(record(a[1], scores)))
    elif len(a) >= 2 and a[0] == "trend":
        t = trend(a[1])
        print(f"trend for {a[1]}: {'+' if (t or 0) >= 0 else ''}{t}" if t is not None else "no prior snapshot")
    else:
        print("usage: critique_ledger.py record <artifact> contract=.. hierarchy=.. detail=.. "
              "functionality=.. innovation=..  |  trend <artifact>")
        sys.exit(2)
