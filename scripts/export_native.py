"""Generate native theme code from the design tokens — real cross-platform handoff.

Beyond CSS/Tailwind/W3C-JSON, this emits the platform-idiomatic theme files so the
SAME contract drives SwiftUI, Flutter, and React Native — not just "export the JSON
and figure it out". The canonical source stays `design-tokens.json` / DESIGN.md.

Usage:
    python3 export_native.py <repo | design-tokens.json> [--out design/native]
"""
import os
import re
import sys

from contract import resolve_contract
from scan_repo import _hex_to_rgb


def _pascal(name):
    return "".join(p.capitalize() for p in name.replace("-", " ").replace("_", " ").split())


def _camel(name):
    # Preserve an already-camelCase token (e.g. "onPrimary") rather than flattening it
    # via _pascal's per-word .capitalize() (which would yield "onprimary"). Only split
    # + recombine when the name carries an explicit separator.
    if name and not any(sep in name for sep in ("-", "_", " ")):
        return name[:1].lower() + name[1:]
    p = _pascal(name)
    return p[:1].lower() + p[1:] if p else name


def _swift_weight(w):
    """Map a numeric/string CSS font-weight to a SwiftUI `Font.Weight` case.
    Unknown/absent -> `.regular` (a real case, never a fabricated one)."""
    table = {"100": "ultraLight", "200": "thin", "300": "light", "400": "regular",
             "500": "medium", "600": "semibold", "700": "bold", "800": "heavy",
             "900": "black", "normal": "regular", "regular": "regular",
             "bold": "bold", "semibold": "semibold", "medium": "medium",
             "light": "light", "thin": "thin", "heavy": "heavy", "black": "black"}
    return table.get(str(w).strip().lower(), "regular")


def _num(v):
    """A CSS length/number token -> a Swift CGFloat literal string (strips a `px`/`pt`
    unit, keeps the number). Non-numeric -> None so the caller can skip it honestly."""
    if v is None:
        return None
    s = str(v).strip().lower()
    for unit in ("px", "pt", "rem", "em"):
        if s.endswith(unit):
            s = s[:-len(unit)].strip()
    try:
        f = float(s)
    except ValueError:
        return None
    return str(int(f)) if f == int(f) else f"{f:g}"


def _parse_box_shadow(css):
    """Parse a CSS `box-shadow` string into [(r,g,b,alpha, offX, offY, blur), ...] —
    one tuple per comma-separated layer. Returns [] on anything it can't parse, so the
    caller can fall back honestly. Handles `<x> <y> <blur> rgba(r,g,b,a)` and hex colors;
    units (px) are stripped. This lets the SwiftUI shadow helper carry the token's REAL
    color(s) and every layer, not a hardcoded guess."""
    if not isinstance(css, str) or not css.strip():
        return []
    # split layers on commas that are NOT inside rgba(...)
    layers, depth, cur = [], 0, ""
    for ch in css:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            layers.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        layers.append(cur)

    def numpx(tok):
        t = tok.strip().lower().replace("px", "")
        try:
            return float(t)
        except ValueError:
            return None

    out = []
    for layer in layers:
        s = layer.strip()
        col = (1.0,)  # placeholder
        r = g = b = 0
        a = 1.0
        m = re.search(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+%?))?\s*\)", s)
        if m:
            r, g, b = (int(float(m.group(i))) for i in (1, 2, 3))
            av = m.group(4)
            if av:
                a = float(av.rstrip("%")) / (100 if av.endswith("%") else 1)
            s = s[:m.start()] + " " + s[m.end():]
        else:
            mh = re.search(r"#([0-9a-fA-F]{6})", s)
            if mh:
                r, g, b = _hex_to_rgb("#" + mh.group(1))
                s = s.replace(mh.group(0), " ")
        nums = [n for n in (numpx(t) for t in s.split()) if n is not None]
        if len(nums) < 2:
            return []  # need at least x + y to be a real shadow layer
        offx, offy = nums[0], nums[1]
        blur = nums[2] if len(nums) >= 3 else 0.0
        out.append((r, g, b, round(a, 4), offx, offy, blur))
    return out


def swiftui(colors, fonts, dark=None, typography=None, spacing=None,
            radius=None, rounded=None, shadows=None):
    """Emit a complete, idiomatic SwiftUI theme from the contract.

    Produces ONE Swift file: a `Color(light:dark:)` dynamic-color initializer (correct
    scheme-aware pattern via `UIColor`/`NSColor` dynamic providers), a `Theme` value
    type with nested `colors`/`spacing`/`radius`/`typography` groups, an
    `EnvironmentKey` + `@Environment(\\.theme)` so views read `theme.colors.primary`,
    a `TextStyle` enum + `.textStyle(_:)` view modifier carrying size+weight+lineHeight,
    and a usage example. Every color role resolves per `ColorScheme`. Honest about the
    one thing SwiftUI can't express verbatim (the web box-shadow elevation string).

    `dark` is the dark-scheme {role: hex} map; when absent, each role falls back to its
    light value for both schemes (still a valid dynamic color, disclosed in the header).
    """
    dark = dark or {}
    typography = typography or {}
    rounded = rounded or {}

    def comp(hexv):
        r, g, b = _hex_to_rgb(hexv)
        return r / 255, g / 255, b / 255

    out = []
    out.append("import SwiftUI")
    out.append("")
    out.append("// Generated by atelier from the design contract. Do not edit by hand.")
    out.append("// Every color role resolves dynamically per ColorScheme (light/dark).")
    if colors and not dark:
        out.append("// NOTE: no dark palette in the contract — each role uses its light")
        out.append("//       value for both schemes (still a valid dynamic color).")
    if shadows:
        out.append("// NOTE: the web box-shadow elevation token has no 1:1 SwiftUI form;")
        out.append("//       it is surfaced as a `.cardShadow()` helper that stacks one")
        out.append("//       `.shadow` per CSS layer using the token's REAL color + offsets")
        out.append("//       (blur/2 as the Gaussian radius — a Gaussian radius is not the")
        out.append("//       same primitive as a CSS blur, so this is a disclosed approximation).")
    if typography:
        out.append("// NOTE: SwiftUI has no precise total-line-height control — `.lineSpacing`")
        out.append("//       adds gap BETWEEN lines on top of the font's intrinsic leading. Each")
        out.append("//       style's `lineSpacing` (= token lineHeight − size) APPROXIMATES the")
        out.append("//       token line height; the exact token `lineHeight` is kept on the spec.")
    out.append("// NOT COMPILED in this environment — generated deterministically; verify in Xcode.")
    out.append("")

    # --- dynamic Color(light:dark:) — the correct scheme-aware idiom ----------
    out.append("public extension Color {")
    out.append("    /// A color that resolves to `light` in light mode and `dark` in dark mode.")
    out.append("    init(light: Color, dark: Color) {")
    out.append("        #if canImport(UIKit)")
    out.append("        self.init(uiColor: UIColor { traits in")
    out.append("            traits.userInterfaceStyle == .dark ? UIColor(dark) : UIColor(light)")
    out.append("        })")
    out.append("        #elseif canImport(AppKit)")
    out.append("        self.init(nsColor: NSColor(name: nil) { appearance in")
    out.append("            let isDark = appearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua")
    out.append("            return NSColor(isDark ? dark : light)")
    out.append("        })")
    out.append("        #else")
    out.append("        self = light")
    out.append("        #endif")
    out.append("    }")
    out.append("")
    out.append("    /// sRGB color from 0–255 channels (matches the source token exactly).")
    out.append("    static func srgb(_ r: Double, _ g: Double, _ b: Double) -> Color {")
    out.append("        Color(.sRGB, red: r, green: g, blue: b, opacity: 1)")
    out.append("    }")
    out.append("}")
    out.append("")

    # --- ThemeColors ---------------------------------------------------------
    out.append("public struct ThemeColors {")
    for name in colors:
        lr, lg, lb = comp(colors[name])
        if name in dark:
            dr, dg, db = comp(dark[name])
        else:
            dr, dg, db = lr, lg, lb
        out.append(f"    public let {_camel(name)} = Color(")
        out.append(f"        light: .srgb({lr:.3f}, {lg:.3f}, {lb:.3f}),")
        out.append(f"        dark:  .srgb({dr:.3f}, {dg:.3f}, {db:.3f}))")
    out.append("}")
    out.append("")

    # --- ThemeSpacing --------------------------------------------------------
    sp = [s for s in (_num(x) for x in (spacing or [])) if s is not None]
    if sp:
        names = ["xs", "sm", "md", "lg", "xl", "xxl", "xxxl"]
        used = []
        out.append("public struct ThemeSpacing {")
        for i, v in enumerate(sp):
            nm = names[i] if i < len(names) else f"s{i}"
            used.append(nm)
            out.append(f"    public let {nm}: CGFloat = {v}")
        # An ordered array for programmatic iteration (e.g. a spacing legend / debug grid).
        out.append("    /// The scale in token order, for programmatic iteration.")
        out.append("    public var scale: [CGFloat] { [" + ", ".join(used) + "] }")
        out.append("}")
        out.append("")

    # --- ThemeRadius ---------------------------------------------------------
    rad_map = {}
    if rounded:
        for k, v in rounded.items():
            n = _num(v)
            if n is not None:
                rad_map[_camel(k)] = n
    elif radius:
        names = ["sm", "md", "lg", "pill"]
        for i, v in enumerate(radius):
            n = _num(v)
            if n is not None:
                rad_map[names[i] if i < len(names) else f"r{i}"] = n
    if rad_map:
        out.append("public struct ThemeRadius {")
        for nm, v in rad_map.items():
            out.append(f"    public let {nm}: CGFloat = {v}")
        out.append("}")
        out.append("")

    # --- Typography: a TextStyle spec carrying size/weight/lineHeight --------
    first_family = fonts[0] if fonts else None
    if typography:
        out.append("public struct TextStyleSpec {")
        out.append("    public let font: Font")
        out.append("    public let lineSpacing: CGFloat")
        out.append("    public let lineHeight: CGFloat")
        out.append("}")
        out.append("")
        out.append("public struct ThemeTypography {")
        for role, spec in typography.items():
            fam = spec.get("family") or first_family
            size = _num(spec.get("size")) or "16"
            weight = _swift_weight(spec.get("weight"))
            lh = _num(spec.get("line_height"))
            # lineSpacing = lineHeight - fontSize (SwiftUI adds spacing BETWEEN lines).
            ls = "0"
            if lh is not None:
                try:
                    ls = str(int(float(lh) - float(size)))
                except ValueError:
                    ls = "0"
            if fam:
                font_expr = f'.custom("{fam}", size: {size}).weight(.{weight})'
            else:
                font_expr = f'.system(size: {size}, weight: .{weight})'
            out.append(f"    public let {_camel(role)} = TextStyleSpec(")
            out.append(f"        font: {font_expr},")
            out.append(f"        lineSpacing: {ls},")
            out.append(f"        lineHeight: {lh if lh is not None else size})")
        out.append("}")
        out.append("")
        # A named text-style enum keyed to the typography roles, for ergonomic
        # `.textStyle(.title)` access. The KeyPath maps each case to its stored spec
        # on the live, in-environment ThemeTypography — so the named API reads the
        # SAME values the theme carries and can never drift, and does NOT rebuild a
        # fresh ThemeTypography per call.
        roles = list(typography.keys())
        out.append("public enum TextStyle: CaseIterable {")
        out.append("    case " + ", ".join(_camel(r) for r in roles))
        out.append("    /// KeyPath into ThemeTypography for this style.")
        out.append("    public var keyPath: KeyPath<ThemeTypography, TextStyleSpec> {")
        out.append("        switch self {")
        for r in roles:
            cm = _camel(r)
            out.append(f"        case .{cm}: return \\.{cm}")
        out.append("        }")
        out.append("    }")
        out.append("}")
        out.append("")
        # The .textStyle() view modifiers. The spec overload is a plain helper; the
        # named overload reads the in-environment theme so it stays in sync.
        out.append("public extension View {")
        out.append("    /// Apply a theme text style (font + line spacing) to a view.")
        out.append("    func textStyle(_ spec: TextStyleSpec) -> some View {")
        out.append("        self.font(spec.font).lineSpacing(spec.lineSpacing)")
        out.append("    }")
        out.append("")
        out.append("    /// Apply a NAMED theme text style, e.g. `.textStyle(.title)`.")
        out.append("    /// Resolves against the in-environment theme so it tracks any")
        out.append("    /// theme override rather than a hard-coded default.")
        out.append("    func textStyle(_ style: TextStyle) -> some View {")
        out.append("        modifier(NamedTextStyle(style: style))")
        out.append("    }")
        out.append("}")
        out.append("")
        out.append("private struct NamedTextStyle: ViewModifier {")
        out.append("    @Environment(\\.theme) private var theme")
        out.append("    let style: TextStyle")
        out.append("    func body(content: Content) -> some View {")
        out.append("        content.textStyle(theme.typography[keyPath: style.keyPath])")
        out.append("    }")
        out.append("}")
        out.append("")
    elif fonts:
        # No typography map: still expose a Font helper per family.
        out.append("public extension Font {")
        for i, f in enumerate(fonts):
            role = "display" if i == 0 else ("body" if i == 1 else _camel(f))
            out.append(f'    static func {role}(_ size: CGFloat) -> Font {{ .custom("{f}", size: size) }}')
        out.append("}")
        out.append("")

    # --- Theme value + Environment integration -------------------------------
    out.append("public struct Theme {")
    out.append("    public let colors = ThemeColors()")
    if sp:
        out.append("    public let spacing = ThemeSpacing()")
    if rad_map:
        out.append("    public let radius = ThemeRadius()")
    if typography:
        out.append("    public let typography = ThemeTypography()")
    out.append("    public init() {}")
    out.append("}")
    out.append("")
    out.append("private struct ThemeKey: EnvironmentKey {")
    out.append("    static let defaultValue = Theme()")
    out.append("}")
    out.append("")
    out.append("public extension EnvironmentValues {")
    out.append("    var theme: Theme {")
    out.append("        get { self[ThemeKey.self] }")
    out.append("        set { self[ThemeKey.self] = newValue }")
    out.append("    }")
    out.append("}")
    out.append("")

    # --- Shadow helper (faithful, per-layer approximation of the CSS token) ---
    if shadows:
        # Use the FIRST elevation token (the canonical card shadow). Parse its CSS into
        # layers so the helper carries the token's REAL color(s) + every layer, not a
        # hardcoded guess. CSS blur -> SwiftUI Gaussian radius via the blur/2 heuristic.
        first_shadow = next(iter(shadows.values())) if isinstance(shadows, dict) else str(shadows)
        css_layers = _parse_box_shadow(first_shadow)
        out.append("public extension View {")
        out.append("    /// Card elevation, derived from the contract's CSS box-shadow token:")
        out.append(f"    ///   `{first_shadow}`")
        out.append("    /// SwiftUI shadows are single-layer with a Gaussian `radius` (not a CSS")
        out.append("    /// blur), so each CSS layer is approximated as a stacked `.shadow` using")
        out.append("    /// the token's real color + offsets and blur/2 as the radius.")
        out.append("    func cardShadow() -> some View {")
        if css_layers:
            body = "self"
            for (r, g, b, a, ox, oy, blur) in css_layers:
                rad = blur / 2 if blur else 0
                rad_s = str(int(rad)) if rad == int(rad) else f"{rad:g}"
                ox_s = str(int(ox)) if ox == int(ox) else f"{ox:g}"
                oy_s = str(int(oy)) if oy == int(oy) else f"{oy:g}"
                body += (f"\n            .shadow(color: Color(.sRGB, red: {r/255:.3f}, "
                         f"green: {g/255:.3f}, blue: {b/255:.3f}, opacity: {a:g}), "
                         f"radius: {rad_s}, x: {ox_s}, y: {oy_s})")
            out.append("        " + body)
        else:
            out.append("        self.shadow(color: .black.opacity(0.10), radius: 3, x: 0, y: 1)")
        out.append("    }")
        out.append("}")
        out.append("")

    # --- Usage example -------------------------------------------------------
    out.append("// MARK: - Usage")
    out.append("struct ThemedCard: View {")
    out.append("    @Environment(\\.theme) private var theme")
    out.append("    var body: some View {")
    style = "headline" if "headline" in typography else (
        _camel(next(iter(typography))) if typography else None)
    pad = "theme.spacing.lg" if sp else "16"
    rad = "theme.radius.md" if "md" in rad_map else (
        f"theme.radius.{next(iter(rad_map))}" if rad_map else "10")
    out.append("        VStack(alignment: .leading, spacing: " + (("theme.spacing.sm" if sp else "8")) + ") {")
    if style:
        out.append(f'            Text("Aurora").textStyle(.{style})  // named, reads @Environment theme')
    else:
        out.append('            Text("Aurora")')
    out.append("                .foregroundStyle(theme.colors.text)")
    out.append(f"        }}")
    out.append(f"        .padding({pad})")
    out.append("        .background(theme.colors.surface)")
    out.append(f"        .clipShape(RoundedRectangle(cornerRadius: {rad}, style: .continuous))")
    out.append("        .overlay(")
    out.append(f"            RoundedRectangle(cornerRadius: {rad}, style: .continuous)")
    out.append("                .stroke(theme.colors.border, lineWidth: 1))")
    if shadows:
        out.append("        .cardShadow()")
    out.append("    }")
    out.append("}")
    out.append("")
    out.append("// Inject the theme once near the root; descendants read @Environment(\\.theme).")
    out.append("// Swap in a different Theme() here (or per preview) to retheme the subtree.")
    out.append("struct ThemedRoot: View {")
    out.append("    var body: some View {")
    out.append("        ThemedCard()")
    out.append("            .padding()")
    out.append("            .background(Theme().colors.background)")
    out.append("            .environment(\\.theme, Theme())")
    out.append("    }")
    out.append("}")
    out.append("")
    out.append("#if DEBUG")
    out.append('#Preview("Light") { ThemedRoot().preferredColorScheme(.light) }')
    out.append('#Preview("Dark")  { ThemedRoot().preferredColorScheme(.dark) }')
    out.append("#endif")

    return "\n".join(out) + "\n"


def _flutter_weight(w):
    """Map a numeric/string CSS font-weight to a Flutter `FontWeight` case name
    (`w100`..`w900`). Unknown/absent -> `w400` (a real weight, never fabricated)."""
    table = {"100": "w100", "200": "w200", "300": "w300", "400": "w400",
             "500": "w500", "600": "w600", "700": "w700", "800": "w800",
             "900": "w900", "normal": "w400", "regular": "w400",
             "bold": "w700", "semibold": "w600", "medium": "w500",
             "light": "w300", "thin": "w100", "heavy": "w800", "black": "w900"}
    return table.get(str(w).strip().lower(), "w400")


def flutter(colors, fonts, dark=None, typography=None, spacing=None,
            radius=None, rounded=None, shadows=None):
    """Emit a COMPLETE, idiomatic Material 3 Flutter theme from the contract.

    Produces ONE Dart file carrying:

    - `ColorScheme.light`/`.dark` with the contract's color roles mapped to the
      canonical Material 3 slots (primary/onPrimary/surface/error/outline/…), so a
      stock Material widget is themed correctly out of the box.
    - A `ThemeExtension<AppTokens>` (`copyWith` + `lerp`) carrying every role that
      does NOT fit a ColorScheme slot (brand accent, semantic success/warning, the
      full role palette, spacing, radii) — the Flutter-canonical token carrier — so
      NOTHING is dropped and tokens animate across theme transitions via `lerp`.
    - A named `TextTheme`/`TextStyle` for the type scale (correct `FontWeight`,
      `fontFamily`, and `height` = lineHeight/size as a unitless multiple).
    - Spacing + radius constants (`AppSpacing`, `AppRadii` as `BorderRadius`).
    - `ThemeData get light`/`get dark` (`useMaterial3: true`) wiring the colorScheme,
      textTheme, and the extension.
    - An ergonomic `context.tokens` accessor reading
      `Theme.of(context).extension<AppTokens>()`.
    - An honest header: NOT compiled here; the web multi-layer box-shadow has no 1:1
      Flutter primitive (surfaced as a derived `List<BoxShadow>`), and `height` only
      approximates total line height.

    `dark` is the dark-scheme {role: hex} map; when absent each role uses its light
    value for both brightnesses (disclosed in the header) — still a valid dark theme.
    """
    dark = dark or {}
    typography = typography or {}
    rounded = rounded or {}
    has_dark = bool(dark)

    def argb(hexv):
        r, g, b = _hex_to_rgb(hexv)
        return f"0xFF{r:02X}{g:02X}{b:02X}"

    def dval(name):
        """The dark hex for a role (falls back to light when no dark palette)."""
        return dark.get(name, colors[name])

    # Material 3 ColorScheme slots we can map confidently from common role names.
    # `danger`/`error` -> error; surfaces -> surface/surfaceContainerHighest.
    def first(*names):
        for n in names:
            if n in colors:
                return n
        return None

    role_primary = first("primary", "brand")
    role_onprimary = first("onPrimary")
    role_secondary = first("secondary", "accent")
    role_surface = first("surface", "background", "elevated")
    role_bg = first("background", "surface")
    role_elevated = first("elevated", "surface")
    role_text = first("text")
    role_error = first("danger", "error")
    role_border = first("border", "outline")

    out = []
    out.append("import 'dart:ui' show lerpDouble;")
    out.append("")
    out.append("import 'package:flutter/material.dart';")
    out.append("")
    out.append("// Generated by atelier from the design contract. Do not edit by hand.")
    out.append("// A complete Material 3 theme: ColorScheme (light+dark) + a typed")
    out.append("// ThemeExtension<AppTokens> for the roles that don't fit a ColorScheme slot.")
    if not has_dark:
        out.append("// NOTE: no dark palette in the contract — the dark theme reuses the")
        out.append("//       light values (still a valid ThemeData.dark). Disclosed.")
    if typography:
        out.append("// NOTE: TextStyle `height` is a unitless multiple of fontSize; it")
        out.append("//       APPROXIMATES the token's pixel lineHeight (height = lineHeight/size).")
    if shadows:
        out.append("// NOTE: the web multi-layer box-shadow has no single Flutter primitive;")
        out.append("//       it is surfaced as a derived `List<BoxShadow>` on AppTokens using")
        out.append("//       each layer's REAL color + offset + (blur as the Gaussian sigma·2),")
        out.append("//       a disclosed approximation, not a fabricated 1:1 equivalence.")
    out.append("// NOT COMPILED in this environment — generated deterministically; verify with")
    out.append("// `dart analyze` / `flutter test` in a Flutter project.")
    out.append("")

    # ---- ColorScheme slot builder ------------------------------------------
    def color_scheme(scheme):
        getv = (lambda n: dval(n)) if scheme == "dark" else (lambda n: colors[n])
        brightness = "dark" if scheme == "dark" else "light"
        L = []
        L.append(f"const ColorScheme _{scheme}Scheme = ColorScheme(")
        L.append(f"  brightness: Brightness.{brightness},")
        if role_primary:
            L.append(f"  primary: Color({argb(getv(role_primary))}),")
        if role_onprimary:
            L.append(f"  onPrimary: Color({argb(getv(role_onprimary))}),")
        if role_secondary:
            L.append(f"  secondary: Color({argb(getv(role_secondary))}),")
            # a sensible onSecondary: reuse onPrimary if present else text
            on_sec = role_onprimary or role_text
            if on_sec:
                L.append(f"  onSecondary: Color({argb(getv(on_sec))}),")
        if role_error:
            L.append(f"  error: Color({argb(getv(role_error))}),")
            on_err = role_onprimary
            if on_err:
                L.append(f"  onError: Color({argb(getv(on_err))}),")
        if role_surface:
            L.append(f"  surface: Color({argb(getv(role_surface))}),")
        if role_text:
            L.append(f"  onSurface: Color({argb(getv(role_text))}),")
        if role_border:
            L.append(f"  outline: Color({argb(getv(role_border))}),")
        L.append(");")
        return L

    out += color_scheme("light")
    out.append("")
    out += color_scheme("dark")
    out.append("")

    # ---- AppTokens ThemeExtension ------------------------------------------
    # Carry the FULL role palette (so nothing is dropped) + spacing + radii.
    color_roles = list(colors.keys())
    sp = [s for s in (_num(x) for x in (spacing or [])) if s is not None]
    rad_map = {}
    if rounded:
        for k, v in rounded.items():
            n = _num(v)
            if n is not None:
                rad_map[_camel(k)] = n
    elif radius:
        rnames = ["sm", "md", "lg", "pill"]
        for i, v in enumerate(radius):
            n = _num(v)
            if n is not None:
                rad_map[rnames[i] if i < len(rnames) else f"r{i}"] = n

    out.append("/// Design tokens that don't fit a Material ColorScheme slot — the brand")
    out.append("/// accent, the semantic palette, the full role set, spacing and radii.")
    out.append("/// Read via `Theme.of(context).extension<AppTokens>()` or `context.tokens`.")
    out.append("@immutable")
    out.append("class AppTokens extends ThemeExtension<AppTokens> {")
    # fields: every color role
    for nm in color_roles:
        out.append(f"  final Color {_camel(nm)};")
    for nm in rad_map:
        out.append(f"  final double radius{nm[:1].upper()}{nm[1:]};")
    if sp:
        out.append("  final List<double> spacing;")
    out.append("")
    out.append("  const AppTokens({")
    for nm in color_roles:
        out.append(f"    required this.{_camel(nm)},")
    for nm in rad_map:
        out.append(f"    required this.radius{nm[:1].upper()}{nm[1:]},")
    if sp:
        out.append("    required this.spacing,")
    out.append("  });")
    out.append("")

    # copyWith
    out.append("  @override")
    out.append("  AppTokens copyWith({")
    for nm in color_roles:
        out.append(f"    Color? {_camel(nm)},")
    for nm in rad_map:
        out.append(f"    double? radius{nm[:1].upper()}{nm[1:]},")
    if sp:
        out.append("    List<double>? spacing,")
    out.append("  }) {")
    out.append("    return AppTokens(")
    for nm in color_roles:
        cm = _camel(nm)
        out.append(f"      {cm}: {cm} ?? this.{cm},")
    for nm in rad_map:
        fld = f"radius{nm[:1].upper()}{nm[1:]}"
        out.append(f"      {fld}: {fld} ?? this.{fld},")
    if sp:
        out.append("      spacing: spacing ?? this.spacing,")
    out.append("    );")
    out.append("  }")
    out.append("")

    # lerp
    out.append("  @override")
    out.append("  AppTokens lerp(ThemeExtension<AppTokens>? other, double t) {")
    out.append("    if (other is! AppTokens) return this;")
    out.append("    return AppTokens(")
    for nm in color_roles:
        cm = _camel(nm)
        out.append(f"      {cm}: Color.lerp({cm}, other.{cm}, t)!,")
    for nm in rad_map:
        fld = f"radius{nm[:1].upper()}{nm[1:]}"
        out.append(f"      {fld}: lerpDouble({fld}, other.{fld}, t)!,")
    if sp:
        out.append("      spacing: spacing,")
    out.append("    );")
    out.append("  }")
    out.append("")

    # the two instances
    def tokens_instance(scheme):
        getv = (lambda n: dval(n)) if scheme == "dark" else (lambda n: colors[n])
        L = [f"  static const AppTokens {scheme} = AppTokens("]
        for nm in color_roles:
            L.append(f"    {_camel(nm)}: Color({argb(getv(nm))}),")
        for nm, v in rad_map.items():
            L.append(f"    radius{nm[:1].upper()}{nm[1:]}: {v},")
        if sp:
            L.append("    spacing: <double>[" + ", ".join(sp) + "],")
        L.append("  );")
        return L

    out += tokens_instance("light")
    out += tokens_instance("dark")
    out.append("}")
    out.append("")

    # ---- BuildContext accessor ---------------------------------------------
    out.append("/// Ergonomic accessor: `context.tokens.accent`, `context.tokens.spacing[3]`.")
    out.append("extension AppTokensContext on BuildContext {")
    out.append("  AppTokens get tokens =>")
    out.append("      Theme.of(this).extension<AppTokens>() ?? AppTokens.light;")
    out.append("}")
    out.append("")

    # ---- spacing + radius plain constants (handy outside a context) --------
    if sp:
        out.append("/// Spacing scale (logical pixels), in token order.")
        out.append("abstract final class AppSpacing {")
        snames = ["xs", "sm", "md", "lg", "xl", "xxl", "xxxl"]
        for i, v in enumerate(sp):
            nm = snames[i] if i < len(snames) else f"s$i"
            out.append(f"  static const double {nm} = {v};")
        out.append("  static const List<double> scale = <double>[" + ", ".join(sp) + "];")
        out.append("}")
        out.append("")
    if rad_map:
        out.append("/// Corner radii as ready-to-use `BorderRadius` values.")
        out.append("abstract final class AppRadii {")
        for nm, v in rad_map.items():
            out.append(f"  static const double {nm} = {v};")
        out.append("")
        for nm, v in rad_map.items():
            out.append(f"  static const BorderRadius {nm}Radius = "
                       f"BorderRadius.all(Radius.circular({v}));")
        out.append("}")
        out.append("")

    # ---- Elevation (from the CSS box-shadow token) -------------------------
    if shadows:
        first_shadow = next(iter(shadows.values())) if isinstance(shadows, dict) else str(shadows)
        css_layers = _parse_box_shadow(first_shadow)
        out.append("/// Card elevation, derived from the contract's CSS box-shadow token:")
        out.append(f"///   `{first_shadow}`")
        out.append("/// Flutter has no single box-shadow primitive, so each CSS layer becomes")
        out.append("/// a `BoxShadow` using the token's REAL color + offset (blur as blurRadius;")
        out.append("/// a Gaussian blurRadius is not identical to a CSS blur — disclosed).")
        out.append("abstract final class AppElevation {")
        if css_layers:
            out.append("  static const List<BoxShadow> card = <BoxShadow>[")
            for (r, g, b, a, ox, oy, blur) in css_layers:
                a8 = max(0, min(255, round(a * 255)))
                ox_s = str(int(ox)) if ox == int(ox) else f"{ox:g}"
                oy_s = str(int(oy)) if oy == int(oy) else f"{oy:g}"
                bl_s = str(int(blur)) if blur == int(blur) else f"{blur:g}"
                out.append(f"    BoxShadow(")
                out.append(f"      color: Color(0x{a8:02X}{r:02X}{g:02X}{b:02X}),")
                out.append(f"      offset: Offset({ox_s}, {oy_s}),")
                out.append(f"      blurRadius: {bl_s},")
                out.append(f"    ),")
            out.append("  ];")
        else:
            out.append("  // token unparseable — a conservative single-layer fallback.")
            out.append("  static const List<BoxShadow> card = <BoxShadow>[")
            out.append("    BoxShadow(color: Color(0x14000000), offset: Offset(0, 1), blurRadius: 3),")
            out.append("  ];")
        out.append("}")
        out.append("")

    # ---- TextTheme ----------------------------------------------------------
    # Map the contract's type roles onto Material 3 TextTheme slots where the names
    # line up, else keep the role name. Always emit each style with the exact size,
    # FontWeight, fontFamily and height = lineHeight/size.
    first_family = fonts[0] if fonts else None
    m3_slot = {
        "largeTitle": "displaySmall", "title": "headlineMedium",
        "headline": "titleLarge", "body": "bodyLarge", "callout": "bodyMedium",
        "caption": "bodySmall", "mono": "labelMedium",
    }
    if typography:
        def style_expr(spec, indent):
            fam = spec.get("family") or spec.get("fontFamily") or first_family
            size = _num(spec.get("size") or spec.get("fontSize")) or "16"
            weight = _flutter_weight(spec.get("weight") or spec.get("fontWeight"))
            lh = _num(spec.get("line_height") or spec.get("lineHeight"))
            parts = [f"fontSize: {size}", f"fontWeight: FontWeight.{weight}"]
            if fam:
                parts.append(f"fontFamily: '{fam}'")
            if lh is not None:
                try:
                    h = float(lh) / float(size)
                    parts.append(f"height: {round(h, 4)}")
                except (ValueError, ZeroDivisionError):
                    pass
            pad = " " * indent
            return ("TextStyle(\n" + ",\n".join(pad + "  " + p for p in parts)
                    + ",\n" + pad + ")")

        out.append("/// The type scale as a Material 3 TextTheme. Token roles map to the")
        out.append("/// closest M3 slot; the exact role names are also exposed on AppTextStyles.")
        out.append("const TextTheme _textTheme = TextTheme(")
        for role, spec in typography.items():
            slot = m3_slot.get(role)
            if slot:
                out.append(f"  {slot}: {style_expr(spec, 2)},")
        out.append(");")
        out.append("")
        # Also expose each role by its CONTRACT name (so nothing is renamed-away).
        out.append("/// Every type role under its CONTRACT name (nothing renamed away).")
        out.append("abstract final class AppTextStyles {")
        for role, spec in typography.items():
            out.append(f"  static const TextStyle {_camel(role)} = {style_expr(spec, 2)};")
        out.append("}")
        out.append("")

    # ---- AppTheme: the two ThemeData --------------------------------------
    out.append("/// The app themes. Inject via `MaterialApp(theme: AppTheme.light,")
    out.append("/// darkThemeMode: ..., darkTheme: AppTheme.dark)`.")
    out.append("abstract final class AppTheme {")
    for scheme in ("light", "dark"):
        out.append(f"  static ThemeData get {scheme} => ThemeData(")
        out.append("        useMaterial3: true,")
        out.append(f"        colorScheme: _{scheme}Scheme,")
        if role_bg:
            getv = dval if scheme == "dark" else (lambda n: colors[n])
            out.append(f"        scaffoldBackgroundColor: Color({argb(getv(role_bg))}),")
        if typography:
            out.append("        textTheme: _textTheme,")
        if first_family:
            out.append(f"        fontFamily: '{first_family}',")
        out.append(f"        extensions: const <ThemeExtension<dynamic>>[AppTokens.{scheme}],")
        out.append("      );")
    out.append("}")
    out.append("")

    # ---- Usage example ------------------------------------------------------
    pad = "context.tokens.spacing[3]" if sp else "16"
    rad = "AppRadii.mdRadius" if "md" in rad_map else (
        f"AppRadii.{next(iter(rad_map))}Radius" if rad_map else
        "BorderRadius.circular(12)")
    out.append("// MARK: usage")
    out.append("class ThemedCard extends StatelessWidget {")
    out.append("  const ThemedCard({super.key});")
    out.append("  @override")
    out.append("  Widget build(BuildContext context) {")
    out.append("    final scheme = Theme.of(context).colorScheme;")
    out.append("    final tokens = context.tokens;")
    out.append(f"    return Container(")
    out.append(f"      padding: EdgeInsets.all({pad}),")
    out.append("      decoration: BoxDecoration(")
    out.append("        color: scheme.surface,")
    out.append(f"        borderRadius: {rad},")
    out.append("        border: Border.all(color: tokens.border),")
    out.append("      ),")
    if typography:
        out.append("      child: Text('Aurora',")
        out.append("          style: Theme.of(context).textTheme.titleLarge),")
    else:
        out.append("      child: Text('Aurora', style: TextStyle(color: scheme.onSurface)),")
    out.append("    );")
    out.append("  }")
    out.append("}")

    return "\n".join(out) + "\n"


def react_native(colors, fonts):
    cols = ",\n".join(f'    {_camel(n)}: "{h}"' for n, h in colors.items())
    fnt = ",\n".join(f'    {("display" if i==0 else "body" if i==1 else _camel(f))}: "{f}"'
                     for i, f in enumerate(fonts))
    return ("// Generated by atelier from the design contract. Do not edit by hand.\n"
            "export const theme = {\n"
            f"  colors: {{\n{cols}\n  }},\n"
            f"  fonts: {{\n{fnt}\n  }},\n"
            "} as const;\n")


def write_all(colors, fonts, out_dir, dark=None, typography=None, spacing=None,
              radius=None, rounded=None, shadows=None):
    os.makedirs(out_dir, exist_ok=True)
    files = {"Theme.swift": swiftui(colors, fonts, dark=dark, typography=typography,
                                    spacing=spacing, radius=radius, rounded=rounded,
                                    shadows=shadows),
             "app_theme.dart": flutter(colors, fonts, dark=dark, typography=typography,
                                       spacing=spacing, radius=radius, rounded=rounded,
                                       shadows=shadows),
             "theme.native.ts": react_native(colors, fonts)}
    for fn, content in files.items():
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(content)
    return [os.path.join(out_dir, fn) for fn in files]


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a]
    if not args or args[0].startswith("-"):
        print("usage: export_native.py <repo | design-tokens.json> [--out design/native]")
        sys.exit(2)
    c = resolve_contract(args[0])
    colors = {n: v for n, v in c["colors"].items() if isinstance(v, str) and v.startswith("#")}
    dark = {n: v for n, v in (c.get("dark_colors") or {}).items()
            if isinstance(v, str) and v.startswith("#")}
    out = args[args.index("--out") + 1] if "--out" in args else "design/native"
    written = write_all(colors, c["fonts"], out, dark=dark,
                        typography=c.get("typography"), spacing=c.get("spacing"),
                        radius=c.get("radius"), rounded=c.get("rounded"),
                        shadows=c.get("shadows"))
    print("Wrote " + ", ".join(written))
