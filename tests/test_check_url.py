"""`check.py --url <url>` — static anti-slop battery on a remote page.

Network is unavailable in tests, so we monkeypatch check._fetch_html to inject
canned HTML (the swappable fetch seam the implementation provides)."""
import check


def _with_fetch(html):
    """Install a fake _fetch_html returning *html*; return the original."""
    orig = check._fetch_html
    check._fetch_html = lambda url: html
    return orig


def test_url_slop_tell_exits_1():
    orig = _with_fetch("<style>body{font-family:Inter}</style><a href='#'>Learn more</a>")
    try:
        # main() routes --url to run_url; generic-font is `important` -> exit 1
        rc = check.main(["--url", "https://example.com", "--quiet"])
    finally:
        check._fetch_html = orig
    assert rc == 1


def test_url_clean_html_exits_0():
    orig = _with_fetch("<style>h1{font-family:Georgia}</style><h1>Hi</h1>")
    try:
        rc = check.main(["--url", "https://example.com"])
    finally:
        check._fetch_html = orig
    assert rc == 0


def test_url_json_mode_returns_findings():
    orig = _with_fetch("<style>body{font-family:Inter}</style>")
    try:
        rc = check.run_url("https://example.com", as_json=True)
    finally:
        check._fetch_html = orig
    assert rc == 1


def test_non_http_scheme_exits_2_no_traceback():
    # file:// and ftp:// are rejected before any fetch is attempted
    assert check.run_url("file:///etc/passwd") == 2
    assert check.run_url("ftp://example.com/x") == 2


def test_network_error_exits_2_cleanly():
    def boom(url):
        raise OSError("connection refused")
    orig = check._fetch_html
    check._fetch_html = boom
    try:
        rc = check.run_url("https://example.com")
    finally:
        check._fetch_html = orig
    assert rc == 2


def test_url_does_not_attempt_fetch_for_bad_scheme():
    # guard: fetch must NOT be called for a rejected scheme
    called = []
    orig = check._fetch_html
    check._fetch_html = lambda url: called.append(url) or ""
    try:
        rc = check.run_url("ftp://example.com")
    finally:
        check._fetch_html = orig
    assert rc == 2 and called == []
