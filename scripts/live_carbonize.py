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
