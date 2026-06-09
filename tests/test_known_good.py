"""The binding gates must pass clean on excellent human-designed pages (E2).
Intentional warm-paper backgrounds, serif eyebrows, and em-dash-free copy are
NOT slop — if these flag, the gate will rot into noise and get rationalized
around, exactly the failure the binding hook exists to prevent."""
import glob
import os

from qa import _slop

CORPUS = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "known_good", "*.html")))


def _contract_for(html_path):
    """A page's warm/branded choices are legitimate only when the contract sanctions
    them — atelier always runs against a contract. Use a sibling `<page>.tokens.json`."""
    cand = os.path.splitext(html_path)[0] + ".tokens.json"
    return cand if os.path.exists(cand) else None


def test_corpus_is_present():
    assert len(CORPUS) >= 2


def test_known_good_pages_have_no_important_slop():
    offenders = {}
    for path in CORPUS:
        r = _slop(open(path, encoding="utf-8").read(), contract=_contract_for(path))
        if r.status != "pass":
            offenders[os.path.basename(path)] = r.detail
    assert not offenders, f"slop false-positives on known-good pages: {offenders}"
