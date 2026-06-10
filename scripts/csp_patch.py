"""CSP classification for the live preview (#8, scoped).

atelier's themed preview injects a small client script (click-to-select, live edits). A
project's Content-Security-Policy blocks inline/injected scripts, so the preview must relax
it — but HOW differs by framework. Classify the patch mechanism so the preview server can
apply the right dev-only relaxation. Pure classification here; the deeper live-iteration
features (per-variant parameter knobs, real component compilation, freehand annotations)
are deferred.

    python3 csp_patch.py <repo>
"""
import glob
import os
import re
import sys

_CSP_META = re.compile(r"http-equiv\s*=\s*[\"']?content-security-policy", re.I)


def classify_csp(repo):
    """Return {mechanism, hint} — how a CSP would need to be relaxed for the preview.
    mechanism ∈ next | sveltekit | nuxt | headers-file | meta-tag | none."""
    def has(*names):
        return any(os.path.exists(os.path.join(repo, n)) for n in names)

    if has("next.config.js", "next.config.ts", "next.config.mjs"):
        return {"mechanism": "next", "hint": "relax the CSP in next.config headers()/middleware (dev only)"}
    if has("svelte.config.js", "svelte.config.ts"):
        return {"mechanism": "sveltekit", "hint": "add the preview origin to kit.csp.directives (dev only)"}
    if has("nuxt.config.js", "nuxt.config.ts"):
        return {"mechanism": "nuxt", "hint": "relax routeRules CSP headers (dev only)"}
    if has("netlify.toml", "_headers", "vercel.json"):
        return {"mechanism": "headers-file", "hint": "the CSP is set in a headers file — not active on a dev server"}
    # A meta CSP tag in any top-level/2-level HTML.
    for p in glob.glob(os.path.join(repo, "*.html")) + glob.glob(os.path.join(repo, "*", "*.html")):
        try:
            if _CSP_META.search(open(p, encoding="utf-8", errors="replace").read(2000)):
                return {"mechanism": "meta-tag", "hint": f"strip/relax the <meta> CSP in {os.path.relpath(p, repo)} for the preview"}
        except OSError:
            pass
    return {"mechanism": "none", "hint": "no CSP detected — the preview client injects freely"}


if __name__ == "__main__":
    import json
    print(json.dumps(classify_csp(sys.argv[1] if len(sys.argv) > 1 else "."), indent=2))
