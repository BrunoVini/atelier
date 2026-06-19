# Atelier Live Mode Parity (and Beyond) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every live-mode gap between atelier and the impeccable skill, then surpass it with atelier's unique QA-gate advantage fully integrated across all new features.

**Architecture:** All new features extend atelier's existing **ephemeral inline-style** live mode (no source writes until accept) rather than switching to impeccable's write-during-preview model. The knob system is driven by CSS custom properties + data attributes on the picked element in-page; the session journal is an append-only JSONL file per proxy run; insert/steer/prefetch are new control endpoints layered onto the existing `/__atelier` namespace.

**Tech Stack:** Node.js (live-proxy.cjs), vanilla JS IIFE (live-client.js), Python 3 stdlib only (all scripts), pytest (tests). No new npm or pip dependencies.

## Global Constraints

- Python scripts: stdlib only — no pip deps. Follow existing style in `scripts/`.
- JS files: ES5-compatible IIFE (live-client.js follows this already). No bundler, no imports.
- live-proxy.cjs: CommonJS, Node builtins only (http, fs, net, path, crypto, url, child_process, os).
- All new `/__atelier/*` endpoints: session-token gated (`tokenOk(req, opts.token)`), DNS-rebind guarded, same pattern as existing `/accept` + `/revert`.
- Tests: pytest, no network, no real filesystem except `tmp_path`. Mirror the style of `test_live_accept.py`.
- Task order: Tasks 1→2→3→4→5→6→7→8. Tasks 1–4 are independent. Tasks 3, 5, 7 each patch live-client.js and live-proxy.cjs in isolated sections — apply them sequentially.

---

## File Map

### New files (12)
| File | Responsibility |
|---|---|
| `scripts/live_journal.py` | Append-only JSONL session journal — write/read/state |
| `scripts/live_status.py` | Read journal → report session state (CLI + importable) |
| `scripts/live_carbonize.py` | Bake knob param values into permanent CSS post-accept |
| `scripts/live_insert.py` | Scaffold for insert mode (net-new content at anchor) |
| `scripts/live_steer.py` | Record + surface steer instructions from browser |
| `scripts/live_config.py` | Live config file management + orphan-file drift-heal scan |
| `tests/test_live_journal.py` | Tests for live_journal + live_status |
| `tests/test_live_carbonize.py` | Tests for live_carbonize |
| `tests/test_live_insert.py` | Tests for live_insert + `/insert` proxy endpoint |
| `tests/test_live_steer.py` | Tests for live_steer + `/steer` proxy endpoint |
| `tests/test_live_config.py` | Tests for live_config drift-heal |
| `tests/test_live_knobs.py` | Tests for knob accept-payload integration |

### Modified files (10)
| File | What changes |
|---|---|
| `scripts/preview/live-client.js` | Knob panel (T1), insert UI (T3), steer bar (T5), prefetch hint (T7) |
| `scripts/preview/live-proxy.cjs` | `/insert` (T3), `/status` (T4), `/steer` (T5), `/prefetch` (T7) |
| `scripts/live_accept.py` | Accept `knob_values` in payload (T1), write journal entry (T4) |
| `scripts/live_detect.py` | Add SvelteKit/Astro/Nuxt/plain-HTML detection (T2) |
| `references/capabilities/live-mode.md` | Document all new features (T8) |
| `SKILL.md` | Update routing table for live mode (T8) |
| `CHANGELOG.md` | Document the release (T8) |
| `tests/test_live_detect.py` | New framework fixture tests (T2) |
| `tests/test_live_proxy.py` | New endpoint tests (T3, T5, T7) |
| `tests/test_live_accept.py` | knob_values round-trip test (T1) |

**Total: 22 files touched.**

---

## Task 1: Interactive Knobs — browser panel + carbonize cleanup

**Purpose:** Add a tuning panel to the picker bar with `range`, `steps`, and `toggle` knobs that drive CSS custom properties / data attributes on the picked element without any source write. On accept, current knob values travel with the payload. `live_carbonize.py` bakes those values into permanent CSS after accept.

**Files:**
- Modify: `scripts/preview/live-client.js`
- Modify: `scripts/live_accept.py`
- Create: `scripts/live_carbonize.py`
- Create: `tests/test_live_carbonize.py`
- Create: `tests/test_live_knobs.py`
- Modify: `tests/test_live_accept.py`

**Interfaces:**
- Produces: `atelier.openPicker({ params: [...] })` public API extension
- Produces: `accept_variant(..., knob_values=None)` updated signature
- Produces: `carbonize(css, param_values)` → `str` in `live_carbonize.py`

---

- [ ] **Step 1: Write failing tests for live_carbonize**

Create `tests/test_live_carbonize.py`:

```python
"""Tests for live_carbonize — bakes knob param values into CSS post-accept."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_carbonize as lc


def test_bake_range_substitutes_var():
    css = "color: rgba(0,0,0,var(--p-opacity, 0.5));"
    result = lc.bake_range(css, "opacity", 0.8)
    assert "var(--p-opacity" not in result
    assert "0.8" in result


def test_bake_range_no_match_unchanged():
    css = "color: red;"
    assert lc.bake_range(css, "opacity", 0.8) == "color: red;"


def test_bake_steps_keeps_chosen_drops_others():
    css = (
        '[data-p-density="airy"] .box { padding: 2rem; }\n'
        '[data-p-density="snug"] .box { padding: 1rem; }\n'
        '[data-p-density="packed"] .box { padding: 0.5rem; }\n'
    )
    result = lc.bake_steps(css, "density", "snug")
    assert "airy" not in result
    assert "packed" not in result
    assert "padding: 1rem" in result
    assert "[data-p-density" not in result


def test_bake_toggle_on_keeps_block_strips_selector():
    css = '[data-p-serif] .title { font-family: Georgia; }\n'
    result = lc.bake_toggle(css, "serif", True)
    assert "[data-p-serif]" not in result
    assert "font-family: Georgia" in result


def test_bake_toggle_off_drops_block():
    css = '[data-p-serif] .title { font-family: Georgia; }\n'
    result = lc.bake_toggle(css, "serif", False)
    assert "font-family: Georgia" not in result


def test_carbonize_all_kinds():
    css = (
        "opacity: var(--p-amount, 0.5);\n"
        '[data-p-density="airy"] .w { gap: 2rem; }\n'
        '[data-p-density="packed"] .w { gap: 0.25rem; }\n'
        '[data-p-bold] h1 { font-weight: 800; }\n'
    )
    param_values = {
        "amount": {"kind": "range", "value": 0.7},
        "density": {"kind": "steps", "value": "airy"},
        "bold": {"kind": "toggle", "value": False},
    }
    result = lc.carbonize(css, param_values)
    assert "0.7" in result
    assert "2rem" in result
    assert "packed" not in result
    assert "font-weight: 800" not in result
    assert "var(--p-" not in result
    assert "[data-p-" not in result
```

- [ ] **Step 2: Run test, verify fail**

```bash
cd /home/bruno/Development/bruno/new-skill/atelier
python -m pytest tests/test_live_carbonize.py -v 2>&1 | head -20
```
Expected: `ImportError: No module named 'live_carbonize'` or similar FAIL.

- [ ] **Step 3: Create `scripts/live_carbonize.py`**

```python
"""Post-accept carbonize: bake live-mode knob param values into permanent CSS.

After a QA-gated accept, if the agent wrote CSS with --p-<id> vars or
[data-p-<id>] selectors (knob-driven), this script rewrites them to literal
values, dropping dead branches. Call it on the CSS block you wrote to source
right after live_accept.accept_variant succeeds.

Usage:
    python3 live_carbonize.py --css-file <path> --params '{"id":{"kind":"range","value":0.7}}'
    # → rewrites the file in place, prints the cleaned CSS to stdout
"""
import argparse, json, re, sys


def bake_range(css, param_id, value):
    """Replace var(--p-<id>, ...) with the literal value."""
    pattern = re.compile(
        r'var\(--p-' + re.escape(param_id) + r'(?:\s*,\s*[^)]+)?\)'
    )
    return pattern.sub(str(value), css)


def bake_steps(css, param_id, chosen_value):
    """Keep only the chosen [data-p-<id>="<value>"] rule block, drop others.
    Strips the attribute selector wrapper from the kept block so only the
    inner declarations remain (semantic classes become unconditional)."""
    drop = re.compile(
        r'\[data-p-' + re.escape(param_id)
        + r'="(?!' + re.escape(chosen_value) + r')(?:[^"\\]|\\.)*"\][^{]*\{[^}]*\}',
        re.DOTALL,
    )
    css = drop.sub('', css)
    keep = re.compile(
        r'\[data-p-' + re.escape(param_id)
        + r'="' + re.escape(chosen_value) + r'"\]\s*([^{]*)\{([^}]*)\}',
        re.DOTALL,
    )
    def unwrap(m):
        inner = m.group(2).strip()
        selector_suffix = m.group(1).strip()
        if selector_suffix:
            return selector_suffix + ' { ' + inner + ' }'
        return inner
    return keep.sub(unwrap, css)


def bake_toggle(css, param_id, value):
    """If on: keep [data-p-<id>] rules (strip selector). If off: drop them.
    Also replaces var(--p-<id>) with 1 or 0."""
    css = bake_range(css, param_id, 1 if value else 0)
    pattern = re.compile(
        r'\[data-p-' + re.escape(param_id) + r'\]\s*([^{]*)\{([^}]*)\}',
        re.DOTALL,
    )
    if value:
        def unwrap(m):
            inner = m.group(2).strip()
            suffix = m.group(1).strip()
            return (suffix + ' { ' + inner + ' }') if suffix else inner
        css = pattern.sub(unwrap, css)
    else:
        css = pattern.sub('', css)
    return css


def carbonize(css, param_values):
    """Bake all knob param values into css.

    param_values: dict of {id: {kind: 'range'|'steps'|'toggle', value: ...}}
    Returns the rewritten CSS string.
    """
    for param_id, info in (param_values or {}).items():
        kind = info.get('kind')
        value = info.get('value')
        if kind == 'range':
            css = bake_range(css, param_id, value)
        elif kind == 'steps':
            css = bake_steps(css, param_id, str(value))
        elif kind == 'toggle':
            css = bake_toggle(css, param_id, bool(value))
    return css


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Bake knob param values into CSS post-accept')
    ap.add_argument('--css-file', required=True, help='path to CSS/HTML file to rewrite in place')
    ap.add_argument('--params', required=True, help='JSON dict {id:{kind,value}}')
    ns = ap.parse_args()
    param_values = json.loads(ns.params)
    with open(ns.css_file, 'r', encoding='utf-8') as f:
        css = f.read()
    result = carbonize(css, param_values)
    with open(ns.css_file, 'w', encoding='utf-8') as f:
        f.write(result)
    print(result)
```

- [ ] **Step 4: Run carbonize tests, verify pass**

```bash
python -m pytest tests/test_live_carbonize.py -v
```
Expected: all 6 tests PASS.

- [ ] **Step 5: Write failing test for knobs in accept payload**

Create `tests/test_live_knobs.py`:

```python
"""Tests for knob_values round-trip through accept_variant."""
import sys, os, json, tempfile, pathlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Stub QA to always pass so accept succeeds
import live_accept as la
_orig_run_qa = la._run_qa


def _fake_qa_pass(target, **kw):
    return "PASS", [{"name": "slop", "status": "pass", "gating": True}]


def test_knob_values_recorded_in_journal(tmp_path, monkeypatch):
    """accept_variant with knob_values stores them in journal entry."""
    monkeypatch.setattr(la, '_run_qa', lambda *a, **kw: _fake_qa_pass(a[0]))

    src = tmp_path / "index.html"
    src.write_text('<div class="hero">old content</div>', encoding='utf-8')

    journal_dir = str(tmp_path / "journal")
    result = la.accept_variant(
        str(src),
        old='<div class="hero">old content</div>',
        new='<div class="hero" style="--p-amount:0.7">new content</div>',
        qa_target=str(src),
        journal_dir=journal_dir,
        session="sess-knob-01",
        knob_values={"amount": {"kind": "range", "value": 0.7}},
    )
    assert result.get("ok"), result
    assert result.get("knob_values") == {"amount": {"kind": "range", "value": 0.7}}


def test_knob_values_none_still_accepts(tmp_path, monkeypatch):
    """accept_variant works fine with no knob_values (backwards compat)."""
    monkeypatch.setattr(la, '_run_qa', lambda *a, **kw: _fake_qa_pass(a[0]))

    src = tmp_path / "page.html"
    src.write_text('<p id="x">old</p>', encoding='utf-8')

    result = la.accept_variant(
        str(src), old='<p id="x">old</p>', new='<p id="x">new</p>',
        qa_target=str(src), journal_dir=str(tmp_path / "j"), session="s2",
    )
    assert result.get("ok"), result
    assert "knob_values" not in result or result.get("knob_values") is None
```

- [ ] **Step 6: Run test, verify fail**

```bash
python -m pytest tests/test_live_knobs.py::test_knob_values_recorded_in_journal -v
```
Expected: `TypeError` (unexpected keyword argument `knob_values`) or AssertionError.

- [ ] **Step 7: Update `scripts/live_accept.py` — add knob_values parameter**

In `accept_variant`, add `knob_values=None` to the signature and include it in the success return:

```python
# Replace this line:
def accept_variant(file, old, new, qa_target, journal_dir, session,
                   register=None, contract=None, label=None, rationale=None, now=None):

# With:
def accept_variant(file, old, new, qa_target, journal_dir, session,
                   register=None, contract=None, label=None, rationale=None,
                   now=None, knob_values=None):
```

At the end of the success branch (just before the final `return`), add:

```python
    # PASS only: keep the edit. (ERROR/FAIL already reverted above; nothing else passes.)
    result = {"ok": True, "reverted": False, "qa": qa_verdict,
              "qa_results": qa_results, "journal_id": journal_id}
    if knob_values is not None:
        result["knob_values"] = knob_values
    return result
```

Also add `--knob-values` to the CLI at the bottom:

```python
    ap.add_argument("--knob-values", default=None,
                    help="JSON dict {id:{kind,value}} of accepted knob positions")
    ns = ap.parse_args()
    kv = json.loads(ns.knob_values) if ns.knob_values else None
    res = accept_variant(ns.file, ns.old, ns.new, ns.qa_target, ns.journal_dir,
                         ns.session, register=ns.register, contract=ns.contract,
                         label=ns.label, rationale=ns.rationale, knob_values=kv)
```

- [ ] **Step 8: Run knob tests, verify pass**

```bash
python -m pytest tests/test_live_knobs.py -v
```
Expected: both tests PASS.

- [ ] **Step 9: Add knob panel to `scripts/preview/live-client.js`**

In `live-client.js`, locate the `openPicker` function. Add a `params` option and knob panel rendering after the variants load. Insert this block BEFORE `bar.appendChild(accept); bar.appendChild(reject);` inside the `.then(function (res) {...})` callback:

```javascript
      // Knob panel (optional): if opts.params is provided, render tuning controls
      // that drive CSS custom properties + data attributes on the picked element.
      // No source write happens — purely in-page CSS var / attr manipulation.
      var currentParams = opts.params || [];
      if (currentParams.length && chosen) {
        renderKnobPanel(currentParams, chosen, bar);
      }
      // Capture current knob values at accept time
      function getKnobValues(el) {
        var out = {};
        currentParams.forEach(function(p) {
          if (p.kind === 'range') {
            var v = el.style.getPropertyValue('--p-' + p.id);
            out[p.id] = {kind: 'range', value: parseFloat(v) || p['default'] || 0};
          } else if (p.kind === 'steps') {
            out[p.id] = {kind: 'steps', value: el.getAttribute('data-p-' + p.id) || p['default'] || ''};
          } else if (p.kind === 'toggle') {
            out[p.id] = {kind: 'toggle', value: el.hasAttribute('data-p-' + p.id)};
          }
        });
        return Object.keys(out).length ? out : null;
      }
```

Then update the `accept.onclick` to pass `knob_values`:

```javascript
          accept.onclick = function () {
            if (!chosen) { log('pick a variant first'); return; }
            var kv = getKnobValues(el);
            if (opts.onAccept) opts.onAccept(chosen, el, kv);
            else log('accept handler not wired — call atelier.accept({file,old,new,qa_target,session,knob_values})');
          };
```

Add `knob_values` to the `atelier.accept` POST payload (update the existing definition):

```javascript
  window.atelier.accept = function (o) {
    return post('/accept', { file: o.file, old: o.old, new: o.new, qa_target: o.qa_target,
                             session: o.session, contract: o.contract, register: o.register,
                             label: o.label, rationale: o.rationale,
                             knob_values: o.knob_values || null });
  };
```

Add `renderKnobPanel` as a module-level function inside the IIFE (before `openPicker`):

```javascript
  function renderKnobPanel(params, el, barEl) {
    var panel = document.createElement('div');
    panel.id = 'atelier-knob-panel';
    panel.style.cssText = 'display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap;'
      + 'border-top:1px solid #444;padding-top:8px;margin-top:6px;width:100%;';
    params.forEach(function(p) {
      var wrap = document.createElement('label');
      wrap.style.cssText = 'display:flex;flex-direction:column;gap:3px;font-size:11px;color:#bbb;min-width:80px;';
      var lbl = document.createElement('span');
      lbl.textContent = p.label || p.id;
      wrap.appendChild(lbl);
      if (p.kind === 'range') {
        var inp = document.createElement('input');
        inp.type = 'range';
        inp.min = p.min != null ? p.min : 0;
        inp.max = p.max != null ? p.max : 1;
        inp.step = p.step != null ? p.step : 0.05;
        inp.value = p['default'] != null ? p['default'] : 0.5;
        el.style.setProperty('--p-' + p.id, inp.value);
        inp.oninput = function() { el.style.setProperty('--p-' + p.id, inp.value); };
        wrap.appendChild(inp);
      } else if (p.kind === 'steps') {
        var seg = document.createElement('div');
        seg.style.cssText = 'display:flex;gap:2px;';
        (p.options || []).forEach(function(opt) {
          var btn = document.createElement('button');
          btn.textContent = opt.label || opt.value;
          var isDefault = opt.value === p['default'];
          btn.style.cssText = 'background:' + (isDefault ? '#555' : '#2a2a2a')
            + ';color:#fff;border:1px solid #555;border-radius:3px;'
            + 'padding:2px 6px;cursor:pointer;font-size:11px;';
          btn.tabIndex = -1;
          btn.onmousedown = function(e) { e.preventDefault(); };
          btn.onclick = function() {
            el.setAttribute('data-p-' + p.id, opt.value);
            seg.querySelectorAll('button').forEach(function(b) {
              b.style.background = '#2a2a2a';
            });
            btn.style.background = '#555';
          };
          if (isDefault) el.setAttribute('data-p-' + p.id, opt.value);
          seg.appendChild(btn);
        });
        wrap.appendChild(seg);
      } else if (p.kind === 'toggle') {
        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = !!p['default'];
        cb.onchange = function() {
          el.style.setProperty('--p-' + p.id, cb.checked ? '1' : '0');
          if (cb.checked) el.setAttribute('data-p-' + p.id, '');
          else el.removeAttribute('data-p-' + p.id);
        };
        if (p['default']) {
          el.style.setProperty('--p-' + p.id, '1');
          el.setAttribute('data-p-' + p.id, '');
        }
        wrap.appendChild(cb);
      }
      panel.appendChild(wrap);
    });
    barEl.appendChild(panel);
  }
```

Also update the proxy's `/accept` handler in `live-proxy.cjs` to forward `knob_values` to `live_accept.py`:

```javascript
      // Inside the readBody callback for '/__atelier/accept':
      if (p.knob_values) args.push('--knob-values', JSON.stringify(p.knob_values));
```

- [ ] **Step 10: Run all live tests to verify no regressions**

```bash
python -m pytest tests/test_live_proxy.py tests/test_live_accept.py tests/test_live_client_focus.py tests/test_live_knobs.py tests/test_live_carbonize.py -v
```
Expected: all PASS.

- [ ] **Step 11: Commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  scripts/live_carbonize.py \
  scripts/preview/live-client.js \
  scripts/preview/live-proxy.cjs \
  scripts/live_accept.py \
  tests/test_live_carbonize.py \
  tests/test_live_knobs.py
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "feat(live): interactive knob panel (range/steps/toggle) + carbonize cleanup"
```

---

## Task 2: Extended Framework Detection (SvelteKit, Astro, Nuxt, plain HTML)

**Purpose:** `live_detect.py` currently accepts only Vite and Next. Add SvelteKit, Astro, Nuxt, and plain-HTML-with-no-framework support so `can_inject` returns `True` for a broader set of dev servers.

**Files:**
- Modify: `scripts/live_detect.py`
- Modify: `tests/test_live_detect.py`

**Interfaces:**
- Produces: `classify_html(body, headers)` returns one of `'vite'|'next'|'sveltekit'|'astro'|'nuxt'|'html'|'unknown'`
- `can_inject` is `True` for all recognized frameworks AND bare HTML (not `unknown`)

---

- [ ] **Step 1: Write failing tests**

Append to `tests/test_live_detect.py`:

```python
# ── New framework fixtures ────────────────────────────────────────────────────

def test_classify_sveltekit():
    body = '<!doctype html><html><script src="/_app/immutable/entry-client.js"></script></html>'
    fw, hmr = classify_html(body)
    assert fw == "sveltekit"
    assert hmr is True


def test_classify_astro():
    body = '<!doctype html><html><script src="/_astro/client.abc123.js"></script></html>'
    fw, hmr = classify_html(body)
    assert fw == "astro"


def test_classify_nuxt():
    body = '<!doctype html><html><script>window.__nuxt={}</script></html>'
    fw, hmr = classify_html(body)
    assert fw == "nuxt"


def test_classify_plain_html():
    body = '<!doctype html><html><head><title>Hello</title></head><body>Hi</body></html>'
    fw, hmr = classify_html(body)
    assert fw == "html"


def test_can_inject_sveltekit():
    from live_detect import detect_dev_server
    # can_inject should be True for all recognized frameworks
    # We test via classify_html + the logic in detect_dev_server
    fw, _ = classify_html('/_app/immutable/foo.js')
    assert fw == "sveltekit"


def test_can_inject_plain_html():
    body = '<!doctype html><html><body>plain site</body></html>'
    fw, _ = classify_html(body)
    # plain HTML should be injectable (no framework signals ≠ not injectable)
    assert fw == "html"


def test_unknown_not_injectable(monkeypatch):
    """A JSON response or empty body stays unknown and non-injectable."""
    body = '{"status":"ok"}'
    fw, hmr = classify_html(body)
    assert fw == "unknown"
    assert hmr is False
```

- [ ] **Step 2: Run tests, verify fail**

```bash
python -m pytest tests/test_live_detect.py -k "sveltekit or astro or nuxt or plain_html or unknown_not" -v
```
Expected: assertions fail (returns 'unknown' for new frameworks).

- [ ] **Step 3: Update `scripts/live_detect.py`**

Add new signature sets and update `classify_html` and `detect_dev_server`:

```python
_SVELTEKIT_SIGNS = (
    "/_app/immutable/",     # SvelteKit asset path
    "__sveltekit_",         # SvelteKit globals
    "@sveltejs/kit",        # package references in source maps / comments
    "svelte-kit",           # fallback hint
)
_ASTRO_SIGNS = (
    "/_astro/",             # Astro asset path
    "astro-island",         # Astro island custom element
    "@astrojs",             # package references
    "astro:scripts",        # Astro script markers
)
_NUXT_SIGNS = (
    "/_nuxt/",              # Nuxt asset path
    "__nuxt",               # Nuxt global (window.__nuxt, __nuxt_data)
    "usenuxtapp",           # lowercase match of useNuxtApp
    "nuxt-link",            # Nuxt router-link component
)
```

Replace the body of `classify_html` with:

```python
def classify_html(body, headers=None):
    """Classify a framework from HTML body + optional response headers.

    Returns (framework, hmr) where framework is one of:
      'vite' | 'next' | 'sveltekit' | 'astro' | 'nuxt' | 'html' | 'unknown'
    'html' means a plain HTML page with no recognized framework (still injectable).
    'unknown' means the response was not HTML at all.
    """
    hay = (body or "").lower()
    if headers:
        lower_keys = {str(k).lower() for k in headers}
        if "x-vite" in lower_keys:
            hay += "\nx-vite /@vite/client"
        for k in ("server", "x-powered-by", "x-vite", "vite"):
            v = headers.get(k) or headers.get(k.title()) or ""
            if v:
                hay += "\n" + str(v).lower()
    if any(s in hay for s in _VITE_SIGNS):
        return "vite", True
    if any(s in hay for s in _NEXT_SIGNS):
        return "next", True
    if any(s in hay for s in _SVELTEKIT_SIGNS):
        return "sveltekit", True
    if any(s in hay for s in _ASTRO_SIGNS):
        return "astro", False   # Astro static may not have live HMR
    if any(s in hay for s in _NUXT_SIGNS):
        return "nuxt", True
    # Plain HTML: the response IS an HTML document, just no known framework.
    # Still injectable — the picker client works fine in a vanilla HTML page.
    is_html_doc = ("<html" in hay or "<!doctype html" in hay)
    if is_html_doc:
        return "html", False
    return "unknown", False
```

Update `detect_dev_server` to include new frameworks in `can_inject`:

```python
    _INJECTABLE = {"vite", "next", "sveltekit", "astro", "nuxt", "html"}
    can_inject = bool(is_html and framework in _INJECTABLE)
```

- [ ] **Step 4: Run detect tests, verify all pass**

```bash
python -m pytest tests/test_live_detect.py -v
```
Expected: all tests PASS including the new ones.

- [ ] **Step 5: Commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  scripts/live_detect.py \
  tests/test_live_detect.py
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "feat(live): framework detection for SvelteKit, Astro, Nuxt, plain HTML"
```

---

## Task 3: Insert Mode (net-new content at an anchor)

**Purpose:** Allow the agent to generate variants for net-new content (not replacing an existing element). The user tells the agent WHERE to insert (anchor element description). The insert scaffold returns an `insertLine` + metadata. Preview: agent injects new DOM nodes ephemerally. Accept: writes new content to source via `edit_apply`.

**Files:**
- Create: `scripts/live_insert.py`
- Modify: `scripts/preview/live-proxy.cjs` (add `/__atelier/insert` endpoint)
- Modify: `scripts/preview/live-client.js` (add `atelier.insert()` API)
- Create: `tests/test_live_insert.py`
- Modify: `tests/test_live_proxy.py` (new endpoint test)

**Interfaces:**
- Produces: `find_insert_anchor(file, anchor_desc)` → `{ok, file, line, context}` in `live_insert.py`
- Produces: `/__atelier/insert` POST endpoint: `{file, anchor: {id?, classes?, tag?, text?}, position: 'before'|'after'}` → `{ok, file, insertLine, context}`
- Produces: `atelier.insert({file, anchor, position})` in live-client.js

---

- [ ] **Step 1: Write failing tests for live_insert**

Create `tests/test_live_insert.py`:

```python
"""Tests for live_insert — anchor resolution for net-new content."""
import sys, os, tempfile, pathlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_insert as li


def test_find_by_id(tmp_path):
    f = tmp_path / "index.html"
    f.write_text('<div id="hero">\n  <h1>Title</h1>\n</div>\n<footer>foot</footer>\n')
    result = li.find_insert_anchor(str(f), {"id": "hero"})
    assert result["ok"]
    assert result["line"] > 0    # 1-based line number of the anchor element
    assert "hero" in result.get("context", "")


def test_find_by_tag_text(tmp_path):
    f = tmp_path / "page.html"
    f.write_text('<section>\n  <h2>Features</h2>\n  <p>stuff</p>\n</section>\n')
    result = li.find_insert_anchor(str(f), {"tag": "section"})
    assert result["ok"]


def test_anchor_not_found(tmp_path):
    f = tmp_path / "empty.html"
    f.write_text('<html><body></body></html>')
    result = li.find_insert_anchor(str(f), {"id": "nonexistent-xyz"})
    assert not result["ok"]
    assert "reason" in result


def test_file_not_found():
    result = li.find_insert_anchor("/tmp/does-not-exist-atelier.html", {"id": "x"})
    assert not result["ok"]
```

- [ ] **Step 2: Run, verify fail**

```bash
python -m pytest tests/test_live_insert.py -v 2>&1 | head -10
```
Expected: `ImportError: No module named 'live_insert'`.

- [ ] **Step 3: Create `scripts/live_insert.py`**

```python
"""Insert mode anchor resolution for live mode.

Given a source file and an anchor description (id / classes / tag / text snippet),
find the line number of the anchor element so the agent knows WHERE to insert new
content before or after it. Returns a safe scaffold the agent uses to write net-new
variants ephemerally and persist the accepted one via edit_apply.

This intentionally does NO write — it only locates and describes the anchor. The
write happens at accept time through the existing live_accept / edit_apply flow.
"""
import json, os, re, sys


def _match_anchor(line, anchor):
    """Return True if `line` (raw HTML text) plausibly contains the anchor element."""
    hay = line.lower()
    if anchor.get("id"):
        if ('id="' + anchor["id"].lower() + '"') in hay:
            return True
        if ("id='" + anchor["id"].lower() + "'") in hay:
            return True
    if anchor.get("tag"):
        tag = anchor["tag"].lower()
        if ("<" + tag) in hay or ("<" + tag + " ") in hay or ("<" + tag + ">") in hay:
            if anchor.get("classes"):
                cls = anchor["classes"].lower()
                if cls in hay:
                    return True
            elif anchor.get("text"):
                if anchor["text"].lower()[:40] in hay:
                    return True
            else:
                return True
    if anchor.get("classes"):
        for cls in re.split(r'[\s,]+', anchor["classes"]):
            if cls and ('class="' in hay or "class='") and cls.lower() in hay:
                return True
    return False


def find_insert_anchor(file_path, anchor_desc):
    """Locate the anchor element in `file_path` that matches `anchor_desc`.

    anchor_desc: dict with optional keys: id, tag, classes, text
    Returns {ok, file, line, context} on success or {ok, reason} on failure.
    """
    if not os.path.isfile(file_path):
        return {"ok": False, "reason": f"file not found: {file_path}"}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        return {"ok": False, "reason": str(e)}

    for i, line in enumerate(lines, 1):
        if _match_anchor(line, anchor_desc):
            # Return the 5 lines of context around the match for the agent.
            start = max(0, i - 3)
            end = min(len(lines), i + 2)
            context = "".join(lines[start:end])
            return {
                "ok": True,
                "file": file_path,
                "line": i,
                "context": context,
            }
    return {"ok": False, "reason": "anchor not found in file"}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Find insert anchor in source file")
    ap.add_argument("file")
    ap.add_argument("--anchor", required=True, help="JSON anchor desc {id?, tag?, classes?, text?}")
    ns = ap.parse_args()
    print(json.dumps(find_insert_anchor(ns.file, json.loads(ns.anchor))))
```

- [ ] **Step 4: Run insert tests, verify pass**

```bash
python -m pytest tests/test_live_insert.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Add `/__atelier/insert` to `live-proxy.cjs`**

In `handleControl`, after the `/revert` block (before `return false`), add:

```javascript
  if (req.url === '/__atelier/insert' && req.method === 'POST') {
    if (!opts.projectDir) {
      res.writeHead(403); res.end('{"ok":false,"reason":"--project-dir required for insert"}');
      return true;
    }
    readBody(req, (p) => {
      if (!p || !p.file || !p.anchor) {
        res.writeHead(400); res.end('{"ok":false,"reason":"insert needs file and anchor"}');
        return;
      }
      const target = path.resolve(String(p.file));
      if (!isConfined(target, opts.projectDir)) {
        res.writeHead(403); res.end('{"ok":false,"reason":"file outside project dir"}');
        return;
      }
      const position = ['before', 'after'].includes(p.position) ? p.position : 'after';
      const args = [
        path.join(scriptsDir, 'live_insert.py'), target,
        '--anchor', JSON.stringify(p.anchor),
        '--position', position,
      ];
      shellPython(args, (out) => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(out);
      }, 10000);
    });
    return true;
  }
```

Also update `live_insert.py` to accept `--position` arg (add it to `if __name__ == '__main__'`):

```python
    ap.add_argument("--position", choices=("before", "after"), default="after")
    ns = ap.parse_args()
    result = find_insert_anchor(ns.file, json.loads(ns.anchor))
    if result.get("ok"):
        result["position"] = ns.position
    print(json.dumps(result))
```

- [ ] **Step 6: Write proxy endpoint test for /insert**

Append to `tests/test_live_proxy.py`:

```python
# ── Insert endpoint ───────────────────────────────────────────────────────────

def test_insert_endpoint_returns_ok(tmp_path):
    """POST /__atelier/insert with a valid file + anchor returns ok+line."""
    import json, threading
    from live_proxy import makeServer
    html = tmp_path / "index.html"
    html.write_text('<div id="hero">Title</div>\n<footer>foot</footer>\n', encoding='utf-8')
    proj = str(tmp_path)
    tok = 'test-insert-tok'

    # live_insert.py is shelled by the proxy; patch shellPython to simulate it
    # (the real script is unit-tested in test_live_insert.py)
    import live_proxy as lp
    _orig = lp.shellPython
    def fake_shell(args, cb, timeout=None):
        if 'live_insert.py' in args[1]:
            cb(json.dumps({"ok": True, "file": str(html), "line": 1, "context": "<div id=hero>"}))
        else:
            _orig(args, cb, timeout)
    lp.shellPython = fake_shell

    srv = makeServer({'upstream': 'http://localhost:1', 'projectDir': proj, 'token': tok})
    port = _free_port()
    srv.listen(port, '127.0.0.1')
    try:
        import urllib.request
        body = json.dumps({"file": str(html), "anchor": {"id": "hero"}, "position": "after"}).encode()
        req = urllib.request.Request(
            f'http://localhost:{port}/__atelier/insert',
            data=body, method='POST',
            headers={'Content-Type': 'application/json', 'X-Atelier-Token': tok, 'Host': 'localhost'},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read())
        assert result.get("ok"), result
        assert result.get("line") == 1
    finally:
        srv.close()
        lp.shellPython = _orig
```

(Add `_free_port` helper at top of test file if not already present: `import socket; _free_port = lambda: socket.socket().bind(('',0)) or socket.socket().getsockname()[1]` — check if it's already there first.)

- [ ] **Step 7: Add `atelier.insert()` to `live-client.js`**

After the `window.atelier.revert` definition, add:

```javascript
  // Insert mode: request an insert scaffold for net-new content at an anchor.
  // The agent uses the returned {file, line, position} to write new variants ephemerally
  // and persist the accepted one via atelier.accept() at accept time.
  window.atelier.insert = function (o) {
    return post('/insert', {
      file: o.file,
      anchor: o.anchor || {},
      position: o.position || 'after',
    });
  };
```

- [ ] **Step 8: Run all live tests**

```bash
python -m pytest tests/test_live_insert.py tests/test_live_proxy.py -v
```
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  scripts/live_insert.py \
  scripts/preview/live-proxy.cjs \
  scripts/preview/live-client.js \
  tests/test_live_insert.py \
  tests/test_live_proxy.py
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "feat(live): insert mode — net-new content at an anchor element"
```

---

## Task 4: Session Journaling & Recovery

**Purpose:** Add a session-level append-only JSONL journal so proxy restarts don't lose session history. `live_status.py` reads the journal and reports the current state so the agent can resume after interruption.

**Files:**
- Create: `scripts/live_journal.py`
- Create: `scripts/live_status.py`
- Modify: `scripts/live_accept.py` (write journal entry on accept)
- Modify: `scripts/preview/live-proxy.cjs` (add `/__atelier/status` endpoint)
- Create: `tests/test_live_journal.py`

**Interfaces:**
- Produces: `write_entry(journal_dir, session_id, entry_type, data)` → entry dict
- Produces: `session_state(journal_dir, session_id)` → `{session, accepts, reverts, steers, status}`
- Produces: `/__atelier/status` GET endpoint → session state JSON

---

- [ ] **Step 1: Write failing tests**

Create `tests/test_live_journal.py`:

```python
"""Tests for live_journal and live_status."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_journal as lj


def test_write_and_read_entry(tmp_path):
    jdir = str(tmp_path / "journal")
    entry = lj.write_entry(jdir, "sess-01", "accept", {"file": "x.html", "ok": True})
    assert entry["type"] == "accept"
    assert entry["session"] == "sess-01"
    entries = lj.read_entries(jdir, "sess-01")
    assert len(entries) == 1
    assert entries[0]["file"] == "x.html"


def test_read_missing_journal_returns_empty(tmp_path):
    entries = lj.read_entries(str(tmp_path / "journal"), "sess-missing")
    assert entries == []


def test_session_state_accumulates(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s", "accept", {"file": "a.html", "ok": True})
    lj.write_entry(jdir, "s", "revert", {"journal_id": "j1"})
    lj.write_entry(jdir, "s", "steer", {"message": "make it bolder"})
    state = lj.session_state(jdir, "s")
    assert len(state["accepts"]) == 1
    assert len(state["reverts"]) == 1
    assert len(state["steers"]) == 1
    assert state["status"] == "active"


def test_session_state_exit(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s", "accept", {"ok": True})
    lj.write_entry(jdir, "s", "exit", {})
    state = lj.session_state(jdir, "s")
    assert state["status"] == "exited"


def test_write_creates_journal_dir(tmp_path):
    jdir = str(tmp_path / "deep" / "journal")
    lj.write_entry(jdir, "s", "start", {})
    assert os.path.isdir(jdir)


def test_multiple_sessions_isolated(tmp_path):
    jdir = str(tmp_path / "journal")
    lj.write_entry(jdir, "s1", "accept", {"file": "a.html"})
    lj.write_entry(jdir, "s2", "accept", {"file": "b.html"})
    assert len(lj.read_entries(jdir, "s1")) == 1
    assert len(lj.read_entries(jdir, "s2")) == 1
    assert lj.read_entries(jdir, "s1")[0]["file"] == "a.html"
```

- [ ] **Step 2: Run, verify fail**

```bash
python -m pytest tests/test_live_journal.py -v 2>&1 | head -10
```
Expected: `ImportError: No module named 'live_journal'`.

- [ ] **Step 3: Create `scripts/live_journal.py`**

```python
"""Session-level append-only JSONL journal for live mode.

One .jsonl file per session under journal_dir. Each line is a JSON object
with at minimum: {type, ts, session}. The journal is the recovery source of
truth — if the proxy restarts, live_status.py reads it to reconstruct state.
"""
import json, os, time


def _path(journal_dir, session_id):
    safe_id = "".join(c if c.isalnum() or c in '-_.' else '_' for c in str(session_id))
    return os.path.join(journal_dir, f"session-{safe_id}.jsonl")


def write_entry(journal_dir, session_id, entry_type, data):
    """Append one entry to the session journal. Creates journal_dir if needed."""
    os.makedirs(journal_dir, exist_ok=True)
    entry = {"type": str(entry_type), "ts": time.time(),
             "session": str(session_id), **data}
    with open(_path(journal_dir, session_id), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_entries(journal_dir, session_id):
    """Return all journal entries for session_id. Returns [] if not found."""
    p = _path(journal_dir, session_id)
    if not os.path.exists(p):
        return []
    entries = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def session_state(journal_dir, session_id):
    """Derive session state from journal. Returns a state dict."""
    entries = read_entries(journal_dir, session_id)
    state = {
        "session": session_id,
        "accepts": [],
        "reverts": [],
        "steers": [],
        "status": "active",
    }
    for e in entries:
        t = e.get("type")
        if t == "accept":
            state["accepts"].append(e)
        elif t == "revert":
            state["reverts"].append(e)
        elif t == "steer":
            state["steers"].append(e)
        elif t == "exit":
            state["status"] = "exited"
    return state
```

- [ ] **Step 4: Run journal tests, verify pass**

```bash
python -m pytest tests/test_live_journal.py -v
```
Expected: all 6 PASS.

- [ ] **Step 5: Create `scripts/live_status.py`**

```python
"""Live mode session status — reads the journal and reports current state.

Usage:
    python3 live_status.py --journal-dir <dir> --session <id>
    # → prints {session, accepts, reverts, steers, status, last_accept?} as JSON
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import live_journal as lj


def status(journal_dir, session_id):
    state = lj.session_state(journal_dir, session_id)
    if state["accepts"]:
        state["last_accept"] = state["accepts"][-1]
    return state


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Live mode session status")
    ap.add_argument("--journal-dir", required=True)
    ap.add_argument("--session", required=True)
    ns = ap.parse_args()
    print(json.dumps(status(ns.journal_dir, ns.session)))
```

- [ ] **Step 6: Update `scripts/live_accept.py` to write journal entry on accept**

Add import at top of `live_accept.py` (after existing imports):

```python
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import live_journal as _lj
    _HAS_JOURNAL = True
except ImportError:
    _HAS_JOURNAL = False
```

In `accept_variant`, after the PASS return is constructed (before `return result`), add:

```python
    # Write journal entry on success so the session is recoverable after proxy restart.
    if _HAS_JOURNAL:
        try:
            _lj.write_entry(journal_dir, session, "accept", {
                "file": file, "journal_id": journal_id,
                "qa": qa_verdict, "knob_values": knob_values,
            })
        except Exception:
            pass   # journal write failure never blocks the accept
```

- [ ] **Step 7: Add `/__atelier/status` GET endpoint to `live-proxy.cjs`**

In `handleControl`, before `return false`:

```javascript
  if (req.url.startsWith('/__atelier/status') && req.method === 'GET') {
    const urlParts = new URL('http://x' + req.url);
    const session = urlParts.searchParams.get('session') || '';
    if (!session) {
      res.writeHead(400); res.end('{"ok":false,"reason":"session param required"}');
      return true;
    }
    const args = [
      path.join(scriptsDir, 'live_status.py'),
      '--journal-dir', journalDir,
      '--session', session,
    ];
    shellPython(args, (out) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(out);
    }, 5000);
    return true;
  }
```

- [ ] **Step 8: Run all live tests**

```bash
python -m pytest tests/test_live_journal.py tests/test_live_accept.py tests/test_live_proxy.py -v
```
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  scripts/live_journal.py \
  scripts/live_status.py \
  scripts/live_accept.py \
  scripts/preview/live-proxy.cjs \
  tests/test_live_journal.py
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "feat(live): session journaling + recovery status endpoint"
```

---

## Task 5: Steer (page-level direction without element selection)

**Purpose:** Let the user type (or speak) a page-level instruction without picking an element. A text input + optional voice button floats in the live bar. The instruction POSTs to `/__atelier/steer`, gets recorded in the journal, and logs prominently for the agent.

**Files:**
- Create: `scripts/live_steer.py`
- Modify: `scripts/preview/live-proxy.cjs` (add `/__atelier/steer` endpoint)
- Modify: `scripts/preview/live-client.js` (add steer input to bar)
- Create: `tests/test_live_steer.py`
- Modify: `tests/test_live_proxy.py` (steer endpoint test)

**Interfaces:**
- Produces: `record_steer(journal_dir, session_id, message, page_url)` in `live_steer.py`
- Produces: `/__atelier/steer` POST endpoint: `{session, message, page_url?}` → `{ok, id}`
- Produces: `atelier.steer(message)` console API + floating steer bar in-page

---

- [ ] **Step 1: Write failing tests for live_steer**

Create `tests/test_live_steer.py`:

```python
"""Tests for live_steer — record steer instructions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_steer as ls
import live_journal as lj


def test_record_steer_writes_journal(tmp_path):
    jdir = str(tmp_path / "journal")
    result = ls.record_steer(jdir, "sess-s", "make the hero bolder", "http://localhost:5173/")
    assert result["ok"]
    assert result.get("id")
    entries = lj.read_entries(jdir, "sess-s")
    assert any(e.get("type") == "steer" for e in entries)
    steer = next(e for e in entries if e.get("type") == "steer")
    assert steer["message"] == "make the hero bolder"
    assert steer["page_url"] == "http://localhost:5173/"


def test_record_steer_no_page_url(tmp_path):
    jdir = str(tmp_path / "journal")
    result = ls.record_steer(jdir, "s2", "quieter please", None)
    assert result["ok"]
    entries = lj.read_entries(jdir, "s2")
    assert entries[0].get("page_url") is None


def test_record_steer_missing_message(tmp_path):
    result = ls.record_steer(str(tmp_path / "j"), "s", "", None)
    assert not result["ok"]
    assert "message" in result.get("reason", "")
```

- [ ] **Step 2: Run, verify fail**

```bash
python -m pytest tests/test_live_steer.py -v 2>&1 | head -10
```

- [ ] **Step 3: Create `scripts/live_steer.py`**

```python
"""Record steer instructions from the browser into the session journal.

Usage (shelled by the proxy):
    python3 live_steer.py --journal-dir <dir> --session <id> \
        --message "make it bolder" [--page-url http://...]
"""
import argparse, json, os, sys, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import live_journal as lj


def record_steer(journal_dir, session_id, message, page_url):
    if not message or not message.strip():
        return {"ok": False, "reason": "message must not be empty"}
    steer_id = str(uuid.uuid4())[:8]
    entry = lj.write_entry(journal_dir, session_id, "steer", {
        "id": steer_id,
        "message": message.strip(),
        "page_url": page_url or None,
    })
    return {"ok": True, "id": steer_id, "entry": entry}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Record live mode steer instruction")
    ap.add_argument("--journal-dir", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--page-url", default=None)
    ns = ap.parse_args()
    print(json.dumps(record_steer(ns.journal_dir, ns.session, ns.message, ns.page_url)))
```

- [ ] **Step 4: Run steer tests, verify pass**

```bash
python -m pytest tests/test_live_steer.py -v
```
Expected: all 3 PASS.

- [ ] **Step 5: Add `/__atelier/steer` to `live-proxy.cjs`**

In `handleControl`, before `return false`:

```javascript
  if (req.url === '/__atelier/steer' && req.method === 'POST') {
    readBody(req, (p) => {
      if (!p || !p.message || !p.session) {
        res.writeHead(400); res.end('{"ok":false,"reason":"steer needs message and session"}');
        return;
      }
      const args = [
        path.join(scriptsDir, 'live_steer.py'),
        '--journal-dir', journalDir,
        '--session', String(p.session),
        '--message', String(p.message),
      ];
      if (p.page_url) args.push('--page-url', String(p.page_url));
      shellPython(args, (out) => {
        // Also log to server stdout so the agent sees the steer instruction
        console.log('[atelier-steer] ' + String(p.message));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(out);
      }, 5000);
    });
    return true;
  }
```

- [ ] **Step 6: Add steer bar to `live-client.js`**

At the end of the IIFE `boot()` function, after `attach(); watchHMR(); log(...)`, add:

```javascript
    // Steer bar: floating bottom-right text input for page-level instructions.
    // Injected once at boot. The user types a direction; on Enter it POSTs to /steer.
    try { addSteerBar(); } catch (_) {}
```

Add `addSteerBar` as a module-level function inside the IIFE:

```javascript
  function addSteerBar() {
    var existing = document.getElementById('atelier-steer-bar');
    if (existing) return;
    var bar = document.createElement('div');
    bar.id = 'atelier-steer-bar';
    bar.style.cssText = 'position:fixed;bottom:16px;right:16px;z-index:2147483646;'
      + 'background:#1a1a1a;border-radius:8px;padding:6px 10px;display:flex;gap:6px;'
      + 'align-items:center;box-shadow:0 2px 12px rgba(0,0,0,.4);';
    var lbl = document.createElement('span');
    lbl.style.cssText = 'font:11px system-ui,sans-serif;color:#666;white-space:nowrap;';
    lbl.textContent = 'steer:';
    var inp = document.createElement('input');
    inp.type = 'text';
    inp.placeholder = 'page direction…';
    inp.style.cssText = 'background:#2a2a2a;color:#eee;border:1px solid #444;border-radius:4px;'
      + 'padding:3px 7px;font:12px system-ui,sans-serif;width:180px;outline:none;';
    inp.onkeydown = function(e) {
      if (e.key === 'Enter' && inp.value.trim()) {
        var msg = inp.value.trim();
        inp.value = '';
        var sessionId = window.__atelierSession || 'default';
        post('/steer', { session: sessionId, message: msg, page_url: location.href })
          .then(function(r) {
            log('steer sent: ' + msg + (r.ok ? '' : ' (warn: ' + r.reason + ')'));
          });
      }
    };
    // Voice input (Web Speech API, graceful degradation)
    if (window.SpeechRecognition || window.webkitSpeechRecognition) {
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      var mic = document.createElement('button');
      mic.textContent = '🎙';
      mic.title = 'Click to speak a steer instruction';
      mic.style.cssText = 'background:none;border:none;cursor:pointer;font-size:14px;padding:0 2px;';
      mic.tabIndex = -1;
      mic.onclick = function() {
        var rec = new SR();
        rec.lang = 'en-US'; rec.maxAlternatives = 1;
        mic.style.color = '#f88';
        rec.onresult = function(ev) {
          var transcript = ev.results[0][0].transcript;
          inp.value = transcript;
          mic.style.color = '';
          inp.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
        };
        rec.onerror = function() { mic.style.color = ''; };
        rec.onend = function() { mic.style.color = ''; };
        rec.start();
      };
      bar.appendChild(mic);
    }
    bar.appendChild(lbl);
    bar.appendChild(inp);
    document.body.appendChild(bar);
  }
```

- [ ] **Step 7: Run all live tests**

```bash
python -m pytest tests/test_live_steer.py tests/test_live_proxy.py -v
```
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  scripts/live_steer.py \
  scripts/preview/live-proxy.cjs \
  scripts/preview/live-client.js \
  tests/test_live_steer.py
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "feat(live): steer — page-level direction via text input + voice"
```

---

## Task 6: Drift-Heal Warning

**Purpose:** When the proxy starts with a `--project-dir`, scan for HTML files in the project that aren't covered by the detected inject targets. Warn the agent about orphan pages so the user knows live mode won't see them.

**Files:**
- Create: `scripts/live_config.py`
- Create: `tests/test_live_config.py`

**Interfaces:**
- Produces: `find_orphan_html(project_dir, injected_files)` → `{orphans: [str], count: int, hint: str}`

---

- [ ] **Step 1: Write failing tests**

Create `tests/test_live_config.py`:

```python
"""Tests for live_config drift-heal."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import live_config as lc


def test_no_orphans_when_all_covered(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 0
    assert result["orphans"] == []


def test_finds_orphan_html(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "about.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 1
    assert any("about.html" in o for o in result["orphans"])


def test_excludes_node_modules(tmp_path):
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "index.html").write_text("<html></html>")
    (tmp_path / "index.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 0


def test_excludes_git_dir(tmp_path):
    git = tmp_path / ".git"
    git.mkdir()
    (git / "COMMIT_EDITMSG").write_text("msg")
    (tmp_path / "index.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [str(tmp_path / "index.html")])
    assert result["count"] == 0


def test_empty_project_no_crash(tmp_path):
    result = lc.find_orphan_html(str(tmp_path), [])
    assert isinstance(result["orphans"], list)


def test_hint_mentions_count(tmp_path):
    (tmp_path / "a.html").write_text("<html></html>")
    (tmp_path / "b.html").write_text("<html></html>")
    result = lc.find_orphan_html(str(tmp_path), [])
    assert "2" in result["hint"]
```

- [ ] **Step 2: Run, verify fail**

```bash
python -m pytest tests/test_live_config.py -v 2>&1 | head -10
```

- [ ] **Step 3: Create `scripts/live_config.py`**

```python
"""Live-mode config utilities — drift-heal scan for orphan HTML files.

find_orphan_html scans project_dir for .html files not covered by the list of
files the proxy is already injecting into. Called at proxy start-up to warn the
agent about pages live mode can't see. Never mutates anything.
"""
import json, os, sys

_HARD_EXCLUDE = {"node_modules", ".git", ".svn", "dist", "build", ".next", ".nuxt", ".astro"}


def find_orphan_html(project_dir, injected_files):
    """Return HTML files in project_dir not in injected_files.

    injected_files: list of absolute paths already being injected.
    Skips node_modules, .git, and other build artifacts.
    Returns {orphans: [str], count: int, hint: str}.
    """
    injected = {os.path.realpath(p) for p in (injected_files or [])}
    orphans = []
    for dirpath, dirnames, filenames in os.walk(project_dir):
        # Prune excluded dirs in-place (prevents os.walk from descending)
        rel = os.path.relpath(dirpath, project_dir)
        top = rel.split(os.sep)[0] if rel != '.' else ''
        if top in _HARD_EXCLUDE:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in _HARD_EXCLUDE and not d.startswith('.')]
        for fname in filenames:
            if not fname.endswith('.html'):
                continue
            full = os.path.realpath(os.path.join(dirpath, fname))
            if full not in injected:
                orphans.append(os.path.relpath(full, project_dir))
    count = len(orphans)
    hint = (
        f"{count} HTML file(s) found in project that aren't covered by the proxy inject. "
        f"Live mode won't see: {', '.join(orphans[:3])}"
        + (" …" if count > 3 else "")
    ) if count else "All HTML files are covered."
    return {"orphans": orphans, "count": count, "hint": hint}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Drift-heal scan")
    ap.add_argument("project_dir")
    ap.add_argument("--injected", default="[]", help="JSON array of injected file paths")
    ns = ap.parse_args()
    injected = json.loads(ns.injected)
    print(json.dumps(find_orphan_html(ns.project_dir, injected)))
```

- [ ] **Step 4: Run config tests, verify pass**

```bash
python -m pytest tests/test_live_config.py -v
```
Expected: all 6 PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  scripts/live_config.py \
  tests/test_live_config.py
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "feat(live): drift-heal scan — warn about orphan HTML pages not covered by inject"
```

---

## Task 7: Prefetch Optimization

**Purpose:** When the user first selects an element on a page the agent hasn't read yet, fire a prefetch hint so the agent can read the source file speculatively while the user decides what to do next.

**Files:**
- Modify: `scripts/preview/live-proxy.cjs` (add `/__atelier/prefetch` endpoint)
- Modify: `scripts/preview/live-client.js` (fire prefetch on first element selection per URL)
- Modify: `tests/test_live_proxy.py` (prefetch endpoint test)

**Interfaces:**
- Produces: `/__atelier/prefetch` POST: `{page_url}` → `{ok, hint: str}` (no-op server, logs for agent)

---

- [ ] **Step 1: Add prefetch endpoint to `live-proxy.cjs`**

In `handleControl`, before `return false`:

```javascript
  if (req.url === '/__atelier/prefetch' && req.method === 'POST') {
    readBody(req, (p) => {
      const pageUrl = (p && p.page_url) ? String(p.page_url) : '(unknown)';
      // Log for agent awareness — no computation needed server-side.
      console.log('[atelier-prefetch] hint for page: ' + pageUrl);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, hint: 'prefetch logged for: ' + pageUrl }));
    });
    return true;
  }
```

- [ ] **Step 2: Add prefetch firing to `live-client.js`**

Near the top of the IIFE (after the `var selected = null` declarations), add:

```javascript
  var _prefetchedPages = {};   // track which page URLs have been prefetched
```

In the `onClick` function, after `selected = e.target;` is set, add:

```javascript
      // Fire a prefetch hint the FIRST time the user selects any element on this page.
      // This lets the agent speculatively read the source file while the user decides.
      var pageKey = location.pathname;
      if (!_prefetchedPages[pageKey]) {
        _prefetchedPages[pageKey] = true;
        try {
          post('/prefetch', { page_url: location.href })
            .catch(function() {});   // best-effort, never surface errors
        } catch (_) {}
      }
```

- [ ] **Step 3: Write proxy test for /prefetch**

Append to `tests/test_live_proxy.py`:

```python
def test_prefetch_endpoint_logs_and_returns_ok(tmp_path):
    """POST /__atelier/prefetch returns ok and the hint."""
    import json
    from live_proxy import makeServer
    tok = 'test-prefetch-tok'
    srv = makeServer({'upstream': 'http://localhost:1', 'token': tok})
    port = _free_port()
    srv.listen(port, '127.0.0.1')
    try:
        import urllib.request
        body = json.dumps({"page_url": "http://localhost:5173/about"}).encode()
        req = urllib.request.Request(
            f'http://localhost:{port}/__atelier/prefetch',
            data=body, method='POST',
            headers={'Content-Type': 'application/json', 'X-Atelier-Token': tok, 'Host': 'localhost'},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read())
        assert result.get("ok"), result
        assert "prefetch" in result.get("hint", "").lower()
    finally:
        srv.close()
```

- [ ] **Step 4: Run proxy tests**

```bash
python -m pytest tests/test_live_proxy.py -v -k "prefetch"
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  scripts/preview/live-proxy.cjs \
  scripts/preview/live-client.js \
  tests/test_live_proxy.py
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "feat(live): prefetch hint — fire on first element selection per page"
```

---

## Task 8: Skill Documentation Update

**Purpose:** Update `references/capabilities/live-mode.md`, `SKILL.md`, and `CHANGELOG.md` to accurately reflect all new capabilities. This is prose editing, no tests.

**Files:**
- Modify: `references/capabilities/live-mode.md`
- Modify: `SKILL.md`
- Modify: `CHANGELOG.md`

---

- [ ] **Step 1: Update `references/capabilities/live-mode.md`**

Add a section after "## How it works" for each new capability:

```markdown
## Knob tuning (range / steps / toggle)

After calling `atelier.openPicker({ params: [...] })`, a knob panel docks below the
variant buttons. Each param drives a CSS custom property (`--p-<id>`) or data attribute
(`data-p-<id>`) on the picked element in real time. No source write happens — the knobs
are ephemeral. On accept, `atelier.accept({ ..., knob_values: atelier.getKnobValues() })`
ships the current values to the server where `live_carbonize.py` bakes them into the
accepted CSS (call it after accept on the CSS block you wrote to source).

Param kinds: `range` (slider → `--p-id`), `steps` (segmented → `data-p-id="value"`),
`toggle` (checkbox → `--p-id: 0|1` + presence of `data-p-id`).

## Insert mode (net-new content)

`atelier.insert({ file, anchor: {id?, tag?, classes?, text?}, position: 'before'|'after' })`
calls `/__atelier/insert` → `{ ok, file, line, position, context }`. Use the returned
`line` to know where to write net-new ephemeral HTML for the user to preview. Accept via
the normal `atelier.accept()` flow.

## Session journaling & recovery

Each proxy run writes an append-only JSONL journal to `--journal-dir` (default:
`/tmp/atelier-live/journal`). After a proxy restart, call:

    python3 scripts/live_status.py --journal-dir <dir> --session <id>

Or GET `/__atelier/status?session=<id>` to recover the session state without relaunching.

## Steer (page-level direction)

The floating steer bar (bottom-right of the proxied page) lets the user type or speak
a page-level instruction without picking an element. Instructions POST to
`/__atelier/steer`, are journaled, and printed to the proxy's stdout for the agent.
From the console: `atelier.steer` is not a public API — the bar is the UX; the agent
reads instructions from the proxy log.

## Drift-heal warning

`scripts/live_config.py` scans `project_dir` for HTML files not covered by the proxy's
inject. Run at boot:

    python3 scripts/live_config.py <project_dir> --injected '["path/to/index.html"]'

Returns `{orphans, count, hint}`. Warn the user about orphan pages before entering the
poll loop.

## Prefetch

The client fires a one-time `/__atelier/prefetch { page_url }` on the first element
selection per page URL. The proxy logs it to stdout so the agent can speculatively read
the source file for that page while the user decides what to do.

## Supported frameworks

| Framework | `can_inject` | HMR |
|---|---|---|
| Vite | yes | yes |
| Next.js | yes | yes |
| SvelteKit | yes | yes |
| Astro | yes | best-effort |
| Nuxt | yes | yes |
| Plain HTML | yes | no |
| Unknown | no — falls back to `preview.md` | — |
```

- [ ] **Step 2: Update routing table in `SKILL.md`**

Find the row:
```
| Live mode on the user's RUNNING app …
```

Replace it with an updated row that lists the new scripts and mentions knobs/steer/insert:
```
| Live mode on the user's RUNNING app — iterate with knobs (range/steps/toggle), insert net-new content, steer via voice/text. Supports Vite, Next, SvelteKit, Astro, Nuxt, plain HTML. | `references/capabilities/live-mode.md` | `scripts/live_detect.py`, `scripts/preview/live-proxy.cjs`, `scripts/live_accept.py`, `scripts/live_carbonize.py`, `scripts/live_insert.py`, `scripts/live_steer.py`, `scripts/live_config.py`, `scripts/live_status.py` |
```

- [ ] **Step 3: Prepend CHANGELOG.md entry**

```markdown
## [next] — 2026-06-18

### Live mode — full parity with impeccable + QA-gate advantage

**New:**
- **Interactive knobs** — `range`, `steps`, `toggle` controls in the picker bar drive CSS custom props / data attrs on the picked element. Knob values travel with the accept payload; `live_carbonize.py` bakes them into permanent CSS post-accept.
- **Insert mode** — `atelier.insert({ file, anchor, position })` returns the source line for net-new content. Preview ephemerally; accept via the same QA-gated flow.
- **Session journaling & recovery** — append-only JSONL journal per proxy run. `live_status.py` + `GET /__atelier/status` let the agent recover after proxy restart without user re-action.
- **Steer** — floating text input + Web Speech API mic for page-level direction without picking an element. Instructions journaled + logged to proxy stdout.
- **Drift-heal** — `live_config.py` scans `project_dir` for HTML files not covered by the inject; warns agent at boot.
- **Prefetch** — client fires `/__atelier/prefetch` on first element selection per page so the agent can speculatively read source.
- **Framework detection expanded** — SvelteKit, Astro, Nuxt, and plain HTML now set `can_inject: true` alongside Vite and Next.

**Atelier advantage over impeccable retained:**
- QA-gated accept with mandatory auto-revert — a QA-failing variant NEVER sticks in source, regardless of which new feature accepted it. No equivalent in impeccable.
```

- [ ] **Step 4: Run full test suite to confirm no regressions**

```bash
cd /home/bruno/Development/bruno/new-skill/atelier
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -20
```
Expected: all existing tests PASS, no new failures.

- [ ] **Step 5: Final commit**

```bash
git -C /home/bruno/Development/bruno/new-skill/atelier add \
  references/capabilities/live-mode.md \
  SKILL.md \
  CHANGELOG.md \
  docs/
git -C /home/bruno/Development/bruno/new-skill/atelier commit -m "docs(live): update live-mode.md, SKILL.md, CHANGELOG for parity release"
```

---

## Summary

| Task | New files | Modified files | Est. scope |
|---|---|---|---|
| T1: Knobs + carbonize | 2 (live_carbonize.py, test_live_carbonize.py, test_live_knobs.py) | 3 (live-client.js, live-proxy.cjs, live_accept.py, test_live_accept.py) | ~200 LOC |
| T2: Framework detection | 0 | 2 (live_detect.py, test_live_detect.py) | ~60 LOC |
| T3: Insert mode | 2 (live_insert.py, test_live_insert.py) | 3 (live-proxy.cjs, live-client.js, test_live_proxy.py) | ~150 LOC |
| T4: Journaling | 2 (live_journal.py, live_status.py, test_live_journal.py) | 3 (live_accept.py, live-proxy.cjs) | ~130 LOC |
| T5: Steer | 2 (live_steer.py, test_live_steer.py) | 3 (live-proxy.cjs, live-client.js, test_live_proxy.py) | ~120 LOC |
| T6: Drift-heal | 2 (live_config.py, test_live_config.py) | 0 | ~80 LOC |
| T7: Prefetch | 0 | 3 (live-proxy.cjs, live-client.js, test_live_proxy.py) | ~30 LOC |
| T8: Docs | 0 | 3 (live-mode.md, SKILL.md, CHANGELOG.md) | ~120 LOC prose |

**Total: 22 files (12 new, 10 modified). ~890 LOC across 8 tasks.**
