// atelier live-mode client (Phase 7) — injected by live-proxy.cjs into HTML responses
// from the user's REAL dev server (Vite/Next). It lets the user pick an element, request
// contract-bound variants, preview them as EPHEMERAL inline styles in the live app, and
// accept/reject. Accept is QA-GATED on the server (capabilities/live-mode.md): the proxy
// shells live_accept.py, which applies → runs qa.py → auto-reverts on failure, so a bad
// variant never sticks in the user's source.
//
// It must survive HMR: when the framework hot-replaces the DOM, the picker bar and any
// preview styles are wiped, so we watch for DOM mutations and re-attach. It is fully
// defensive — every entry point is wrapped so a failure here can NEVER break the user's
// app (we are guests in their page).
(function () {
  if (window.__atelierLive) return;            // idempotent: HMR can re-inject the script
  window.__atelierLive = true;

  var CONTROL = '/__atelier';                   // control endpoints the proxy serves
  var selected = null;                          // currently picked element
  var savedInline = null;                       // its inline style to restore on reject

  function log(m) { try { console.debug('[atelier-live] ' + m); } catch (_) {} }

  function applyStyles(el, styles) {
    if (!el || !styles) return;
    for (var k in styles) { try { el.style.setProperty(k, styles[k]); } catch (_) {} }
  }

  // Is `el` something the user might be typing into? We must never steal focus from these
  // (#241): selecting via alt+click must not blur an input/textarea/select/contenteditable.
  function isEditableTarget(el) {
    try {
      if (!el) return false;
      var tag = el.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
      if (el.isContentEditable) return true;
      return false;
    } catch (_) { return false; }
  }

  // POST JSON to a control endpoint, resolve parsed JSON (or {ok:false,reason}). Echoes the
  // session token (window.__atelierToken, injected same-origin by the proxy) as
  // X-Atelier-Token so the server's token gate accepts the write.
  function post(path, payload) {
    var headers = { 'Content-Type': 'application/json' };
    try { if (window.__atelierToken) headers['X-Atelier-Token'] = window.__atelierToken; } catch (_) {}
    return fetch(CONTROL + path, {
      method: 'POST', headers: headers,
      body: JSON.stringify(payload || {})
    }).then(function (r) { return r.json(); })
      .catch(function (e) { return { ok: false, reason: (e && e.message) || 'network error' }; });
  }

  // Public API the agent/user drives from the console (mirrors the preview client).
  window.atelier = window.atelier || {};
  window.atelier.live = true;
  window.atelier.variants = function (mode, opts) {
    opts = opts || {};
    return post('/variants', { mode: mode, prop: opts.prop, current: opts.current || {},
                               n: opts.n, contract: opts.contract });
  };
  // Accept is qa-gated server-side; caller MUST supply file + old anchor + qa_target
  // (no magic source-mapping — capabilities/live-mode.md).
  window.atelier.accept = function (o) {
    return post('/accept', { file: o.file, old: o.old, new: o.new, qa_target: o.qa_target,
                             session: o.session, contract: o.contract, register: o.register,
                             label: o.label, rationale: o.rationale,
                             knob_values: o.knob_values || null });
  };
  window.atelier.revert = function (journalId) {
    return post('/revert', { journal_id: journalId });
  };
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
  // Steer: send a page-level direction without picking an element.
  window.atelier.steer = function (text) {
    return post('/steer', {
      session: window.__atelierSession || 'default',
      message: text,
      page_url: location.href,
    });
  };

  // ── Knob panel ───────────────────────────────────────────────────────────
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

  // ── Picker bar ───────────────────────────────────────────────────────────
  function teardown() {
    var bar = document.getElementById('atelier-live-bar');
    if (bar) bar.remove();
    if (selected && savedInline !== null) {
      try { selected.setAttribute('style', savedInline); } catch (_) {}
    }
    selected = null; savedInline = null;
  }

  window.atelier.openPicker = function (opts) {
    opts = opts || {};
    try {
      var el = opts.element || selected;
      if (!el) { log('openPicker: no element selected — click one first'); return; }
      selected = el;
      savedInline = el.getAttribute('style') || '';
      var mode = opts.mode || 'steps';
      teardownBarOnly();

      var bar = document.createElement('div');
      bar.id = 'atelier-live-bar';
      bar.style.cssText = 'position:fixed;bottom:16px;left:50%;transform:translateX(-50%);'
        + 'z-index:2147483647;background:#1a1a1a;color:#fff;padding:10px 14px;border-radius:8px;'
        + 'font:13px system-ui,sans-serif;display:flex;gap:8px;align-items:center;flex-wrap:wrap;'
        + 'box-shadow:0 4px 16px rgba(0,0,0,.3);max-width:92vw;';
      bar.innerHTML = '<span style="opacity:.7">atelier · ' + mode + '</span>';
      document.body.appendChild(bar);

      var chosen = null;
      function pick(v, btn) {
        chosen = v; applyStyles(el, v.styles);
        bar.querySelectorAll('button[data-v]').forEach(function (x) { x.style.outline = ''; });
        if (btn) btn.style.outline = '2px solid #6cf';
      }

      window.atelier.variants(mode, { prop: opts.prop, current: opts.current || {},
                                      n: opts.n, contract: opts.contract })
        .then(function (res) {
          if (!res || !res.ok || !Array.isArray(res.variants)) {
            bar.insertAdjacentHTML('beforeend',
              '<span style="color:#f88">' + ((res && res.reason) || 'no variants') + '</span>');
            return;
          }
          res.variants.forEach(function (v, i) {
            var b = document.createElement('button');
            b.textContent = v.label || ('v' + (i + 1));
            b.setAttribute('data-v', '1');
            b.style.cssText = 'background:#333;color:#fff;border:1px solid #555;border-radius:5px;'
              + 'padding:4px 8px;cursor:pointer;';
            // Don't steal focus from whatever the user was typing in (#241): preventDefault
            // on mousedown keeps the click firing without moving focus; tabIndex -1 keeps it
            // out of the tab order entirely.
            b.tabIndex = -1;
            b.onmousedown = function (e) { e.preventDefault(); };
            b.onclick = function () { pick(v, b); };
            bar.appendChild(b);
          });
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
          var accept = document.createElement('button');
          accept.textContent = 'Accept (qa-gated)';
          accept.style.cssText = 'background:#2a7;color:#fff;border:0;border-radius:5px;'
            + 'padding:4px 10px;cursor:pointer;margin-left:6px;';
          accept.tabIndex = -1;
          accept.onmousedown = function (e) { e.preventDefault(); };   // never steal focus (#241)
          accept.onclick = function () {
            if (!chosen) { log('pick a variant first'); return; }
            var kv = getKnobValues(el);
            if (opts.onAccept) opts.onAccept(chosen, el, kv);
            else log('accept handler not wired — call atelier.accept({file,old,new,qa_target,session,knob_values})');
          };
          var reject = document.createElement('button');
          reject.textContent = 'Reject';
          reject.style.cssText = 'background:#a33;color:#fff;border:0;border-radius:5px;'
            + 'padding:4px 10px;cursor:pointer;';
          reject.tabIndex = -1;
          reject.onmousedown = function (e) { e.preventDefault(); };   // never steal focus (#241)
          reject.onclick = function () { teardown(); };
          bar.appendChild(accept); bar.appendChild(reject);
        });
    } catch (e) { log('openPicker failed: ' + (e && e.message)); }
  };

  function teardownBarOnly() {
    var bar = document.getElementById('atelier-live-bar');
    if (bar) bar.remove();
  }

  // Click-to-select: alt+click an element to pick it (alt avoids hijacking normal
  // clicks in the user's app). Defensive — never preventDefault unless alt is held. We must
  // NOT disturb focus (#241): if the user is mid-edit in an input/textarea/contenteditable,
  // alt+click still selects the target, but we never blur or refocus that editable element.
  function onClick(e) {
    try {
      if (!e.altKey) return;
      // Preserve the editable element the user is typing in so a transient outline tweak
      // below can't steal focus from it.
      var active = null;
      try { active = document.activeElement; } catch (_) {}
      var keepFocus = isEditableTarget(active);
      e.preventDefault(); e.stopPropagation();
      selected = e.target;
      savedInline = selected.getAttribute('style') || '';
      log('selected <' + selected.tagName.toLowerCase() + '> — call atelier.openPicker()');
      // Only paint a selection outline on the picked element; never call .focus() on it.
      selected.style.outline = '2px dashed #6cf';
      setTimeout(function () { try { selected && (selected.style.outline = ''); } catch (_) {} }, 600);
      // If the user was editing, make sure focus is still where it was.
      if (keepFocus && active && active !== document.activeElement) {
        try { active.focus({ preventScroll: true }); } catch (_) {}
      }
    } catch (_) {}
  }

  // ── HMR survival ──────────────────────────────────────────────────────────
  // When the framework hot-replaces DOM, listeners on document survive (we bind on
  // document, not on nodes), but a stale `selected` node may be detached and the bar
  // wiped. Re-attach defensively after mutations settle.
  function attach() {
    try {
      document.removeEventListener('click', onClick, true);
      document.addEventListener('click', onClick, true);
    } catch (_) {}
  }

  var reattachTimer = null;
  function watchHMR() {
    try {
      var mo = new MutationObserver(function () {
        if (reattachTimer) clearTimeout(reattachTimer);
        reattachTimer = setTimeout(function () {
          // If our selected node detached during HMR, drop the stale reference.
          if (selected && !document.contains(selected)) { teardown(); }
          attach();
        }, 150);
      });
      mo.observe(document.documentElement || document.body, { childList: true, subtree: true });
    } catch (_) { /* MutationObserver absent -> picker still works, just no auto-reattach */ }
  }

  // ── Steer bar ────────────────────────────────────────────────────────────
  // Floating bottom-right input for page-level directions. Always visible.
  // Visually distinct from the picker bar (bottom-left center vs. bottom-right corner,
  // smaller, darker bg, labelled "steer:"). Web Speech API is optional — gracefully absent.
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
    inp.onkeydown = function (e) {
      if (e.key === 'Enter' && inp.value.trim()) {
        var msg = inp.value.trim();
        inp.value = '';
        window.atelier.steer(msg).then(function (r) {
          log('steer sent: ' + msg + (r.ok ? '' : ' (warn: ' + (r.reason || '') + ')'));
        });
      }
    };
    // Voice input (Web Speech API, graceful degradation)
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SR) {
      var mic = document.createElement('button');
      mic.textContent = '🎙';
      mic.title = 'Click to speak a steer instruction';
      mic.style.cssText = 'background:none;border:none;cursor:pointer;font-size:14px;padding:0 2px;';
      mic.tabIndex = -1;
      mic.onclick = function () {
        var rec = new SR();
        rec.lang = 'en-US';
        rec.maxAlternatives = 1;
        mic.style.color = '#f88';
        rec.onresult = function (ev) {
          var transcript = ev.results[0][0].transcript;
          inp.value = transcript;
          mic.style.color = '';
          inp.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        };
        rec.onerror = function () { mic.style.color = ''; };
        rec.onend = function () { mic.style.color = ''; };
        rec.start();
      };
      bar.appendChild(mic);
    }
    bar.appendChild(lbl);
    bar.appendChild(inp);
    document.body.appendChild(bar);
  }

  function boot() {
    attach(); watchHMR();
    log('ready — alt+click an element, then atelier.openPicker()');
    try { addSteerBar(); } catch (_) {}
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
