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
    role_accent = first("accent")
    role_surface = first("surface", "background", "elevated")
    role_bg = first("background", "surface")
    role_elevated = first("elevated", "surface")
    role_text = first("text")
    role_secondary_ink = first("secondary")
    role_muted = first("muted")
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
        out.append("//       it is surfaced as a derived `List<BoxShadow>` (one BoxShadow per CSS")
        out.append("//       layer) on AppElevation, carrying each layer's REAL color + offset; the")
        out.append("//       CSS blur is passed straight to BoxShadow.blurRadius — a disclosed")
        out.append("//       approximation (a Flutter Gaussian blurRadius is not identical to a CSS")
        out.append("//       blur), not a fabricated 1:1 equivalence.")
    if role_elevated and role_elevated != role_surface:
        out.append("// NOTE: the `surfaceContainer*` ColorScheme slots require Flutter 3.22+.")
        out.append("//       On older Flutter, delete those five lines (the minimal surface/")
        out.append("//       onSurface/outline slots above still theme correctly).")
    if role_accent:
        out.append("// NOTE: `accent` has no canonical ColorScheme slot — it is mapped to")
        out.append("//       `tertiary` AND kept verbatim on `AppTokens.accent`.")
    if role_secondary or role_accent:
        out.append("// NOTE: `onSecondary`/`onTertiary` have no source token; they are set to a")
        out.append("//       readable contrast (onPrimary/surface), not a fabricated value.")
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
            # a sensible onSecondary: reuse onPrimary if present else surface.
            # (No source token for onSecondary; a readable contrast, not fabricated.)
            on_sec = role_onprimary or role_surface or role_text
            if on_sec:
                L.append(f"  onSecondary: Color({argb(getv(on_sec))}),")
        # accent -> tertiary (its closest canonical M3 slot; the exact value also
        # lives on AppTokens.accent so a widget can read the unblended token).
        if role_accent:
            L.append(f"  tertiary: Color({argb(getv(role_accent))}),")
            on_ter = role_onprimary or role_surface
            if on_ter:
                L.append(f"  onTertiary: Color({argb(getv(on_ter))}),")
        if role_error:
            L.append(f"  error: Color({argb(getv(role_error))}),")
            on_err = role_onprimary
            if on_err:
                L.append(f"  onError: Color({argb(getv(on_err))}),")
        if role_surface:
            L.append(f"  surface: Color({argb(getv(role_surface))}),")
        if role_text:
            L.append(f"  onSurface: Color({argb(getv(role_text))}),")
        # secondary ink -> onSurfaceVariant (the M3 slot for muted-on-surface text).
        if role_secondary_ink:
            L.append(f"  onSurfaceVariant: Color({argb(getv(role_secondary_ink))}),")
        # The M3 tonal surface-container ramp: map the contract's elevation ladder
        # (background < surface < elevated) onto the container slots so stock M3
        # widgets pick the right tonal surface. Emitted only when an `elevated`
        # role distinguishes the ramp (else the minimal slots above suffice).
        # surfaceContainer* require Flutter 3.22+ (disclosed in the header).
        if role_elevated and role_elevated != role_surface:
            lowest = role_bg or role_surface
            L.append(f"  surfaceContainerLowest: Color({argb(getv(lowest))}),")
            L.append(f"  surfaceContainerLow: Color({argb(getv(role_surface))}),")
            L.append(f"  surfaceContainer: Color({argb(getv(role_surface))}),")
            L.append(f"  surfaceContainerHigh: Color({argb(getv(role_elevated))}),")
            L.append(f"  surfaceContainerHighest: Color({argb(getv(role_elevated))}),")
        if role_border:
            L.append(f"  outline: Color({argb(getv(role_border))}),")
        # muted -> outlineVariant (the faint divider/disabled-border slot).
        if role_muted:
            L.append(f"  outlineVariant: Color({argb(getv(role_muted))}),")
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
        # Interpolate the spacing scale element-wise so EVERY field participates in
        # a theme transition (not returned verbatim). Lengths are equal across
        # themes generated from one contract; guarded for safety.
        out.append("      spacing: <double>[")
        out.append("        for (var i = 0; i < spacing.length; i++)")
        out.append("          lerpDouble(spacing[i],")
        out.append("              i < other.spacing.length ? other.spacing[i] : spacing[i], t)!,")
        out.append("      ],")
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
    out.append("/// Ergonomic accessors: `context.tokens.accent`, `context.spacing.lg`,")
    out.append("/// `context.radii.md`, `context.type.headline`, `context.elevation.card`.")
    out.append("/// Asserts (with an actionable message) when the extension isn't registered,")
    out.append("/// rather than silently falling back to the light tokens — a silent fallback")
    out.append("/// would show LIGHT tokens in an unthemed dark subtree and mask the bug.")
    out.append("extension AppTokensContext on BuildContext {")
    out.append("  AppTokens get tokens {")
    out.append("    final tokens = Theme.of(this).extension<AppTokens>();")
    out.append("    assert(")
    out.append("      tokens != null,")
    out.append("      'AppTokens ThemeExtension not found. Build ThemeData via '")
    out.append("      'AppTheme.light / AppTheme.dark so the tokens are registered.',")
    out.append("    );")
    out.append("    return tokens!;")
    out.append("  }")
    if sp:
        out.append("")
        out.append("  /// Spacing scale by semantic name: `context.spacing.lg`.")
        out.append("  AppSpacing get spacing => AppSpacing._i;")
    if rad_map:
        out.append("")
        out.append("  /// Corner radii by semantic name: `context.radii.md` / `.mdRadius`.")
        out.append("  AppRadii get radii => AppRadii._i;")
    if typography:
        out.append("")
        out.append("  /// The type scale: `context.type.headline`.")
        out.append("  AppTypography get type {")
        out.append("    final t = Theme.of(this).extension<AppTypography>();")
        out.append("    assert(t != null, 'AppTypography ThemeExtension not found. Use AppTheme.light/.dark.');")
        out.append("    return t!;")
        out.append("  }")
    if shadows:
        out.append("")
        out.append("  /// Elevation shadows: `context.elevation.card`.")
        out.append("  AppElevation get elevation {")
        out.append("    final e = Theme.of(this).extension<AppElevation>();")
        out.append("    assert(e != null, 'AppElevation ThemeExtension not found. Use AppTheme.light/.dark.');")
        out.append("    return e!;")
        out.append("  }")
    out.append("}")
    out.append("")

    # ---- spacing + radius scales: const namespace + named accessors --------
    # Each scale is BOTH a static const namespace (`AppSpacing.lg` — usable in
    # const contexts / outside a widget) AND a const-singleton with named
    # INSTANCE getters (so `context.spacing.lg` reads by semantic name at the
    # call site instead of an opaque positional index like `spacing[3]`).
    snames = ["xs", "sm", "md", "lg", "xl", "xxl", "xxxl"]
    if sp:
        out.append("/// Spacing scale (logical pixels). Use `AppSpacing.lg` in const")
        out.append("/// contexts, or `context.spacing.lg` inside a widget — both name the")
        out.append("/// step semantically rather than by a positional index.")
        out.append("final class AppSpacing {")
        out.append("  const AppSpacing._();")
        out.append("  static const AppSpacing _i = AppSpacing._();")
        for i, v in enumerate(sp):
            nm = snames[i] if i < len(snames) else f"s{i}"
            out.append(f"  static const double {nm} = {v};")
        out.append("  static const List<double> scale = <double>[" + ", ".join(sp) + "];")
        # named instance getters (delegate to the consts) for `context.spacing.lg`
        for i, v in enumerate(sp):
            nm = snames[i] if i < len(snames) else f"s{i}"
            out.append(f"  double get {nm} => {v};")
        out.append("  List<double> get all => scale;")
        out.append("  double operator [](int i) => scale[i];")
        out.append("}")
        out.append("")
    if rad_map:
        out.append("/// Corner radii. `AppRadii.md` / `AppRadii.mdRadius` for const contexts,")
        out.append("/// `context.radii.md` / `context.radii.mdRadius` inside a widget — both")
        out.append("/// read by semantic name.")
        out.append("final class AppRadii {")
        out.append("  const AppRadii._();")
        out.append("  static const AppRadii _i = AppRadii._();")
        for nm, v in rad_map.items():
            out.append(f"  static const double {nm} = {v};")
        out.append("")
        for nm, v in rad_map.items():
            out.append(f"  static const BorderRadius {nm}Radius = "
                       f"BorderRadius.all(Radius.circular({v}));")
        out.append("")
        for nm, v in rad_map.items():
            out.append(f"  double get {nm} => {v};")
        for nm, v in rad_map.items():
            out.append(f"  BorderRadius get {nm}Radius => "
                       f"const BorderRadius.all(Radius.circular({v}));")
        out.append("}")
        out.append("")

    # ---- Elevation (from the CSS box-shadow token) -------------------------
    if shadows:
        first_shadow = next(iter(shadows.values())) if isinstance(shadows, dict) else str(shadows)
        css_layers = _parse_box_shadow(first_shadow)
        def card_list_literal(indent):
            pad = " " * indent
            L = ["<BoxShadow>["]
            if css_layers:
                for (r, g, b, a, ox, oy, blur) in css_layers:
                    a8 = max(0, min(255, round(a * 255)))
                    ox_s = str(int(ox)) if ox == int(ox) else f"{ox:g}"
                    oy_s = str(int(oy)) if oy == int(oy) else f"{oy:g}"
                    bl_s = str(int(blur)) if blur == int(blur) else f"{blur:g}"
                    L.append(f"{pad}  BoxShadow(")
                    L.append(f"{pad}    color: Color(0x{a8:02X}{r:02X}{g:02X}{b:02X}),")
                    L.append(f"{pad}    offset: Offset({ox_s}, {oy_s}),")
                    L.append(f"{pad}    blurRadius: {bl_s},")
                    L.append(f"{pad}  ),")
            else:
                L.append(f"{pad}  // token unparseable — a conservative single-layer fallback.")
                L.append(f"{pad}  BoxShadow(color: Color(0x14000000), offset: Offset(0, 1), blurRadius: 3),")
            L.append(f"{pad}]")
            return ("\n").join(L)

        out.append("/// Card elevation, derived from the contract's CSS box-shadow token:")
        out.append(f"///   `{first_shadow}`")
        out.append("/// Flutter has no single box-shadow primitive, so each CSS layer becomes")
        out.append("/// a `BoxShadow` using the token's REAL color + offset (blur as blurRadius;")
        out.append("/// a Gaussian blurRadius is not identical to a CSS blur — disclosed).")
        out.append("/// A ThemeExtension so shadows animate on a theme transition and are read")
        out.append("/// via `context.elevation.card`.")
        out.append("@immutable")
        out.append("class AppElevation extends ThemeExtension<AppElevation> {")
        out.append("  final List<BoxShadow> card;")
        out.append("  const AppElevation({required this.card});")
        out.append("")
        out.append("  static const AppElevation standard = AppElevation(")
        out.append("    card: " + card_list_literal(4) + ",")
        out.append("  );")
        out.append("")
        out.append("  @override")
        out.append("  AppElevation copyWith({List<BoxShadow>? card}) =>")
        out.append("      AppElevation(card: card ?? this.card);")
        out.append("")
        out.append("  @override")
        out.append("  AppElevation lerp(ThemeExtension<AppElevation>? other, double t) {")
        out.append("    if (other is! AppElevation) return this;")
        out.append("    return AppElevation(")
        out.append("      card: BoxShadow.lerpList(card, other.card, t) ?? card,")
        out.append("    );")
        out.append("  }")
        out.append("}")
        out.append("")

    # ---- TextTheme ----------------------------------------------------------
    # Map the contract's type roles onto Material 3 TextTheme slots where the names
    # line up, else keep the role name. Always emit each style with the exact size,
    # FontWeight, fontFamily and height = lineHeight/size.
    first_family = fonts[0] if fonts else None
    # Fill the FULL canonical M3 TextTheme slot set so stock widgets (AppBar,
    # ListTile, chips, buttons, labels) inherit the contract's scale — not just a
    # sparse few. Each M3 slot points at the contract role whose visual weight it
    # matches; when the contract has fewer roles than slots, a nearby role is
    # reused (a real role, never a fabricated style).
    def role_for(*prefs):
        for p in prefs:
            if p in typography:
                return p
        return next(iter(typography)) if typography else None

    if typography:
        r_large = role_for("largeTitle", "display", "title")
        r_title = role_for("title", "largeTitle", "headline")
        r_head = role_for("headline", "title")
        r_body = role_for("body")
        r_callout = role_for("callout", "body")
        r_caption = role_for("caption", "callout", "body")
        # Map every M3 TextTheme slot to a contract role.
        m3_full = {
            "displayLarge": r_large, "displayMedium": r_large, "displaySmall": r_title,
            "headlineLarge": r_title, "headlineMedium": r_head, "headlineSmall": r_head,
            "titleLarge": r_head, "titleMedium": r_callout, "titleSmall": r_callout,
            "bodyLarge": r_body, "bodyMedium": r_body, "bodySmall": r_caption,
            "labelLarge": r_callout, "labelMedium": r_caption, "labelSmall": r_caption,
        }
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
                    # Emit the EXACT unitless ratio as a division expression
                    # (`lineHeight / size`) rather than a pre-rounded decimal — it
                    # evaluates at full double precision and is self-documenting, so
                    # the token's line height is reproduced exactly, not to 4 dp.
                    lh_s = str(int(float(lh))) if float(lh) == int(float(lh)) else f"{float(lh):g}"
                    size_s = str(int(float(size))) if float(size) == int(float(size)) else f"{float(size):g}"
                    parts.append(f"height: {lh_s} / {size_s}")
                except (ValueError, ZeroDivisionError):
                    pass
            pad = " " * indent
            return ("TextStyle(\n" + ",\n".join(pad + "  " + p for p in parts)
                    + ",\n" + pad + ")")

        typo_roles = list(typography.keys())
        out.append("/// The type scale as a lerp-able ThemeExtension: every contract role is a")
        out.append("/// field (exact size / FontWeight / family / lineHeight-as-ratio), it builds")
        out.append("/// the FULL 15-slot Material 3 TextTheme via `toTextTheme()` so stock widgets")
        out.append("/// inherit the scale, and it interpolates on a theme transition. Read named")
        out.append("/// roles via `context.type.headline`.")
        out.append("@immutable")
        out.append("class AppTypography extends ThemeExtension<AppTypography> {")
        for role in typo_roles:
            out.append(f"  final TextStyle {_camel(role)};")
        out.append("")
        out.append("  const AppTypography({")
        for role in typo_roles:
            out.append(f"    required this.{_camel(role)},")
        out.append("  });")
        out.append("")
        out.append("  static const AppTypography standard = AppTypography(")
        for role in typo_roles:
            out.append(f"    {_camel(role)}: {style_expr(typography[role], 4)},")
        out.append("  );")
        out.append("")
        # toTextTheme: fill every canonical M3 slot from the closest role field.
        out.append("  /// Build the FULL Material 3 [TextTheme] from this scale so stock")
        out.append("  /// widgets (AppBar, ListTile, chips, buttons, labels) inherit it.")
        out.append("  TextTheme toTextTheme() => TextTheme(")
        for slot, role in m3_full.items():
            if role and role in typography:
                out.append(f"        {slot}: {_camel(role)},")
        out.append("      );")
        out.append("")
        out.append("  @override")
        out.append("  AppTypography copyWith({")
        for role in typo_roles:
            out.append(f"    TextStyle? {_camel(role)},")
        out.append("  }) {")
        out.append("    return AppTypography(")
        for role in typo_roles:
            cm = _camel(role)
            out.append(f"      {cm}: {cm} ?? this.{cm},")
        out.append("    );")
        out.append("  }")
        out.append("")
        out.append("  @override")
        out.append("  AppTypography lerp(ThemeExtension<AppTypography>? other, double t) {")
        out.append("    if (other is! AppTypography) return this;")
        out.append("    return AppTypography(")
        for role in typo_roles:
            cm = _camel(role)
            out.append(f"      {cm}: TextStyle.lerp({cm}, other.{cm}, t)!,")
        out.append("    );")
        out.append("  }")
        out.append("}")
        out.append("")

    # ---- AppTheme: the two ThemeData --------------------------------------
    out.append("/// The app themes. Inject via `MaterialApp(theme: AppTheme.light,")
    out.append("/// darkTheme: AppTheme.dark, themeMode: ThemeMode.system)`.")
    # Shared (brightness-independent) extensions: typography + elevation.
    shared_exts = []
    if typography:
        shared_exts.append("AppTypography.standard")
    if shadows:
        shared_exts.append("AppElevation.standard")
    out.append("abstract final class AppTheme {")
    for scheme in ("light", "dark"):
        out.append(f"  static ThemeData get {scheme} => ThemeData(")
        out.append("        useMaterial3: true,")
        out.append(f"        colorScheme: _{scheme}Scheme,")
        if role_bg:
            getv = dval if scheme == "dark" else (lambda n: colors[n])
            out.append(f"        scaffoldBackgroundColor: Color({argb(getv(role_bg))}),")
        if typography:
            out.append("        textTheme: AppTypography.standard.toTextTheme(),")
        if first_family:
            out.append(f"        fontFamily: '{first_family}',")
        exts = [f"AppTokens.{scheme}"] + shared_exts
        out.append("        extensions: const <ThemeExtension<dynamic>>[")
        out.append("          " + ", ".join(exts) + ",")
        out.append("        ],")
        out.append("      );")
    out.append("}")
    out.append("")

    # ---- Usage example ------------------------------------------------------
    # Demonstrate the SEMANTIC, named surface (`context.spacing.lg`,
    # `context.radii.md`) — not an opaque positional index.
    pad = "context.spacing.lg" if sp else "16"
    if rad_map:
        rname = "md" if "md" in rad_map else next(iter(rad_map))
        rad = f"context.radii.{rname}Radius"
    else:
        rad = "BorderRadius.circular(12)"
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
    if shadows:
        out.append("        boxShadow: context.elevation.card,")
    out.append("      ),")
    if typography:
        out.append("      child: Text('Aurora', style: context.type.headline),")
    else:
        out.append("      child: Text('Aurora', style: TextStyle(color: scheme.onSurface)),")
    out.append("    );")
    out.append("  }")
    out.append("}")

    return "\n".join(out) + "\n"


_RN_WEIGHTS = {"100", "200", "300", "400", "500", "600", "700", "800", "900",
               "normal", "bold"}


def _rn_weight(w):
    """Map a CSS font-weight to a value in React Native's `TextStyle.fontWeight`
    STRING union (`'100'..'900' | 'normal' | 'bold'`). RN wants the weight as a
    STRING, never a number, and only those exact members typecheck. Unknown/absent
    -> `'400'` (a real member, never fabricated)."""
    s = str(w).strip().lower()
    if s in _RN_WEIGHTS:
        return s
    named = {"regular": "400", "semibold": "600", "medium": "500", "light": "300",
             "thin": "100", "heavy": "800", "black": "900", "ultralight": "100"}
    return named.get(s, "400")


def _ts_str(s):
    """A TS double-quoted string literal with embedded quotes/backslashes escaped."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def react_native(colors, fonts, dark=None, typography=None, spacing=None,
                 radius=None, rounded=None, shadows=None):
    """Emit a COMPLETE, idiomatic React Native + TypeScript theme from the contract.

    Produces ONE `.ts` file carrying:

    - A typed `Theme` interface (color roles, named spacing, named radii, the type
      scale as `TextStyle` presets, an elevation/shadow style) and concrete
      `lightTheme` / `darkTheme` objects implementing it — every color role in BOTH
      schemes (the dark map falls back to light per-role when absent, disclosed).
    - A React `Context` `ThemeProvider` + a `useTheme()` hook; the provider defaults
      to the OS scheme via `useColorScheme()` and can be pinned. No JSX (uses
      `React.createElement`) so the whole theme is a single self-contained `.ts`.
    - StyleSheet-friendly shapes: colors are hex STRINGS; spacing + radii are
      NUMBERS (RN style values are unitless); text presets carry numeric
      `fontSize`/`lineHeight` and `fontWeight` as RN's STRING union.
    - Named spacing (`theme.spacing.md`) AND named radii (`theme.radii.lg`), plus a
      positional `spacingScale` array for iteration.
    - Elevation derived from the CSS box-shadow token, expressed the only way RN can:
      `shadowColor`/`shadowOffset`/`shadowOpacity`/`shadowRadius` (iOS) + `elevation`
      (Android). Multi-layer box-shadow can't be expressed exactly — disclosed; the
      layers collapse to a representative single shadow + an elevation estimate.
    - A usage example and an honest header (what RN can't express; whether typechecked).

    `dark` is the dark-scheme {role: hex} map; when absent each role uses its light
    value for both schemes (disclosed). All scales are driven from the contract, so
    this works for any role set / type scale / spacing length / radii names.
    """
    dark = dark or {}
    typography = typography or {}
    rounded = rounded or {}
    has_dark = bool(dark)

    def hexv(h):
        # Uppercase 6-digit hex, the conventional source form (`#F7F8FA`).
        return h.upper() if isinstance(h, str) else h

    def dval(name):
        return dark.get(name, colors[name])

    color_roles = list(colors.keys())

    # --- spacing: named steps + a positional scale --------------------------
    sp = [s for s in (_num(x) for x in (spacing or [])) if s is not None]
    snames = ["xs", "sm", "md", "lg", "xl", "xxl", "xxxl"]
    spacing_named = []  # [(name, numliteral)]
    for i, v in enumerate(sp):
        spacing_named.append((snames[i] if i < len(snames) else f"s{i}", v))

    # --- radii: named map (from `rounded`, else positional `radius`) --------
    rad_map = []  # [(name, numliteral)]
    if rounded:
        for k, v in rounded.items():
            n = _num(v)
            if n is not None:
                rad_map.append((_camel(k), n))
    elif radius:
        rnames = ["sm", "md", "lg", "pill"]
        for i, v in enumerate(radius):
            n = _num(v)
            if n is not None:
                rad_map.append((rnames[i] if i < len(rnames) else f"r{i}", n))

    # --- typography presets -------------------------------------------------
    first_family = fonts[0] if fonts else None
    typo_roles = list(typography.keys())

    def text_preset(spec):
        fam = spec.get("family") or spec.get("fontFamily") or first_family
        size = _num(spec.get("size") or spec.get("fontSize")) or "16"
        weight = _rn_weight(spec.get("weight") or spec.get("fontWeight"))
        lh = _num(spec.get("line_height") or spec.get("lineHeight"))
        parts = []
        if fam:
            parts.append(f"fontFamily: {_ts_str(fam)}")
        parts.append(f"fontSize: {size}")
        parts.append(f"fontWeight: {_ts_str(weight)}")
        if lh is not None:
            parts.append(f"lineHeight: {lh}")
        return "{ " + ", ".join(parts) + " }"

    # --- shadow: parse the (first) CSS box-shadow token ---------------------
    first_shadow = None
    if shadows:
        first_shadow = next(iter(shadows.values())) if isinstance(shadows, dict) else str(shadows)
    css_layers = _parse_box_shadow(first_shadow) if first_shadow else []

    out = []
    # ---- header ------------------------------------------------------------
    out.append("// Generated by atelier from the design contract. Do not edit by hand.")
    out.append("// React Native + TypeScript theme: a typed `Theme`, light + dark theme")
    out.append("// objects, a Context `ThemeProvider`, and a `useTheme()` hook.")
    out.append("//")
    out.append("// What React Native CANNOT express verbatim (disclosed, not faked):")
    if first_shadow:
        out.append("//   - CSS `box-shadow`: RN has no box-shadow. Elevation is mapped to the")
        out.append("//     iOS shadow* props + Android `elevation`. A MULTI-LAYER box-shadow")
        out.append("//     cannot be reproduced exactly; the token's layers are collapsed to a")
        out.append(f"//     single representative shadow (+ elevation). Source token:")
        out.append(f"//       {first_shadow}")
    out.append("//   - CSS line-height units: RN `lineHeight` is a unitless number (px-like),")
    out.append("//     so the token's pixel line height is carried as-is (no `em`/unit-less ratio).")
    if fonts:
        fam_list = ", ".join(str(f) for f in fonts)
        out.append("//   - Custom fonts are NOT bundled by RN: the families above")
        out.append(f"//     ({fam_list}) must be LINKED by the app (expo-font, or")
        out.append("//     react-native.config.js + `npx react-native-asset`), otherwise RN")
        out.append("//     silently falls back to the system font. `fontFamily` here only")
        out.append("//     names them; it does not load them.")
    if not has_dark:
        out.append("//   - No dark palette in the contract: each role reuses its light value for")
        out.append("//     both schemes (still a valid dark theme).")
    out.append("//")
    out.append("// Typecheck: this file is written to typecheck under `tsc --strict --noEmit`")
    out.append("// against @types/react + the react-native type stub. It is NOT executed/")
    out.append("// rendered here — verify in an app. No web-only APIs (no className/rem/px).")
    out.append("")
    out.append("import React, { createContext, useContext, useMemo } from 'react';")
    out.append("import { useColorScheme } from 'react-native';")
    out.append("import type { TextStyle, ViewStyle } from 'react-native';")
    out.append("")

    # ---- token type aliases ------------------------------------------------
    out.append("export type ColorScheme = 'light' | 'dark';")
    out.append("")
    out.append("/** Every color role in the contract (hex strings, StyleSheet-ready). */")
    out.append("export interface ThemeColors {")
    for nm in color_roles:
        out.append(f"  {_camel(nm)}: string;")
    out.append("}")
    out.append("")
    if spacing_named:
        out.append("/** Named spacing steps (unitless RN numbers). */")
        out.append("export interface ThemeSpacing {")
        for nm, _v in spacing_named:
            out.append(f"  {nm}: number;")
        out.append("}")
        out.append("")
    if rad_map:
        out.append("/** Named corner radii (unitless RN numbers). */")
        out.append("export interface ThemeRadii {")
        for nm, _v in rad_map:
            out.append(f"  {nm}: number;")
        out.append("}")
        out.append("")
    if typo_roles:
        out.append("/** The type scale; each preset is a StyleSheet-ready `TextStyle`. */")
        out.append("export interface ThemeTypography {")
        for role in typo_roles:
            out.append(f"  {_camel(role)}: TextStyle;")
        out.append("}")
        out.append("")
    if first_shadow:
        out.append("/** Elevation as a RN style fragment: iOS shadow* props + Android elevation. */")
        out.append("export type ElevationStyle = Pick<")
        out.append("  ViewStyle,")
        out.append("  'shadowColor' | 'shadowOffset' | 'shadowOpacity' | 'shadowRadius' | 'elevation'")
        out.append(">;")
        out.append("export interface ThemeElevation {")
        out.append("  card: ElevationStyle;")
        out.append("}")
        out.append("")

    # ---- Theme interface ---------------------------------------------------
    out.append("export interface Theme {")
    out.append("  scheme: ColorScheme;")
    out.append("  colors: ThemeColors;")
    if spacing_named:
        out.append("  spacing: ThemeSpacing;")
        out.append("  /** The spacing scale in token order, for programmatic iteration. */")
        out.append("  spacingScale: readonly number[];")
    if rad_map:
        out.append("  radii: ThemeRadii;")
    if typo_roles:
        out.append("  typography: ThemeTypography;")
    if first_shadow:
        out.append("  elevation: ThemeElevation;")
    out.append("  fonts: readonly string[];")
    out.append("}")
    out.append("")

    # ---- shared (scheme-independent) groups --------------------------------
    if spacing_named:
        out.append("const spacing: ThemeSpacing = {")
        for nm, v in spacing_named:
            out.append(f"  {nm}: {v},")
        out.append("};")
        out.append("")
        out.append("const spacingScale: readonly number[] = ["
                   + ", ".join(v for _n, v in spacing_named) + "];")
        out.append("")
    if rad_map:
        out.append("const radii: ThemeRadii = {")
        for nm, v in rad_map:
            out.append(f"  {nm}: {v},")
        out.append("};")
        out.append("")
    if typo_roles:
        out.append("const typography: ThemeTypography = {")
        for role in typo_roles:
            out.append(f"  {_camel(role)}: {text_preset(typography[role])},")
        out.append("};")
        out.append("")
    if first_shadow:
        # Collapse the layers to a single representative shadow: deepest (max |offsetY|)
        # layer for color/offset/blur; the strongest opacity; elevation ~= max offsetY.
        if css_layers:
            rep = max(css_layers, key=lambda L: abs(L[5]))  # max |offY|
            r, g, b, a, ox, oy, blur = rep
            max_a = max(L[3] for L in css_layers)
            max_oy = max(abs(L[5]) for L in css_layers)
            max_blur = max(L[6] for L in css_layers)
            elev_android = int(round(max_oy + max_blur))
            shadow_color = f"#{r:02X}{g:02X}{b:02X}"
            ox_s = str(int(ox)) if ox == int(ox) else f"{ox:g}"
            oy_s = str(int(oy)) if oy == int(oy) else f"{oy:g}"
            blur_s = str(int(max_blur)) if max_blur == int(max_blur) else f"{max_blur:g}"
            opacity_s = f"{round(max_a, 4):g}"
            n_layers = len(css_layers)
        else:
            shadow_color, ox_s, oy_s, blur_s, opacity_s, elev_android, n_layers = (
                "#000000", "0", "1", "3", "0.1", 2, 0)
        out.append("// Elevation from the CSS box-shadow token. RN has no box-shadow, and a")
        out.append(f"// MULTI-LAYER shadow can't be expressed exactly — the {n_layers} CSS layer(s)")
        out.append("// collapse to one representative iOS shadow (deepest layer's color/offset,")
        out.append("// strongest opacity) + an Android `elevation` estimate. Disclosed approximation.")
        out.append(f"// Source token (verbatim, for traceability): {first_shadow}")
        out.append("// The raw string is kept in THIS COMMENT, not as a field on the style object,")
        out.append("// so `...theme.elevation.card` spreads cleanly into StyleSheet.create (a `raw`")
        out.append("// property would be an invalid RN style key).")
        out.append("const elevation: ThemeElevation = {")
        out.append("  card: {")
        out.append(f"    shadowColor: {_ts_str(shadow_color)},")
        out.append(f"    shadowOffset: {{ width: {ox_s}, height: {oy_s} }},")
        out.append(f"    shadowOpacity: {opacity_s},")
        out.append(f"    shadowRadius: {blur_s},")
        out.append(f"    elevation: {elev_android},")
        out.append("  },")
        out.append("};")
        out.append("")

    # ---- color palettes + theme objects ------------------------------------
    def color_obj(getv):
        L = ["{"]
        for nm in color_roles:
            L.append(f"  {_camel(nm)}: {_ts_str(hexv(getv(nm)))},")
        L.append("}")
        return "\n".join(L)

    out.append(f"const fonts: readonly string[] = ["
               + ", ".join(_ts_str(f) for f in fonts) + "];")
    out.append("")
    out.append("const lightColors: ThemeColors = " + color_obj(lambda n: colors[n]) + ";")
    out.append("")
    out.append("const darkColors: ThemeColors = " + color_obj(dval) + ";")
    out.append("")

    def theme_obj(scheme, colors_ref):
        L = [f"export const {scheme}Theme: Theme = {{"]
        L.append(f"  scheme: '{scheme}',")
        L.append(f"  colors: {colors_ref},")
        if spacing_named:
            L.append("  spacing,")
            L.append("  spacingScale,")
        if rad_map:
            L.append("  radii,")
        if typo_roles:
            L.append("  typography,")
        if first_shadow:
            L.append("  elevation,")
        L.append("  fonts,")
        L.append("};")
        return "\n".join(L)

    out.append(theme_obj("light", "lightColors"))
    out.append("")
    out.append(theme_obj("dark", "darkColors"))
    out.append("")
    out.append("export const themes: Record<ColorScheme, Theme> = {")
    out.append("  light: lightTheme,")
    out.append("  dark: darkTheme,")
    out.append("};")
    out.append("")

    # ---- Context + Provider + hook -----------------------------------------
    out.append("// The active theme defaults to the OS scheme; descendants read it via useTheme().")
    out.append("const ThemeContext = createContext<Theme>(lightTheme);")
    out.append("")
    out.append("export interface ThemeProviderProps {")
    out.append("  /** Pin a scheme; omit to follow the OS appearance via useColorScheme(). */")
    out.append("  scheme?: ColorScheme;")
    out.append("  children?: React.ReactNode;")
    out.append("}")
    out.append("")
    out.append("export function ThemeProvider(props: ThemeProviderProps): React.ReactElement {")
    out.append("  const system = useColorScheme();")
    out.append("  const active: ColorScheme = props.scheme ?? (system === 'dark' ? 'dark' : 'light');")
    out.append("  const value = useMemo<Theme>(() => themes[active], [active]);")
    out.append("  // JSX-free so this whole theme lives in one .ts file.")
    out.append("  return React.createElement(ThemeContext.Provider, { value }, props.children);")
    out.append("}")
    out.append("")
    out.append("/** The active theme. Use inside a component rendered under <ThemeProvider>. */")
    out.append("export function useTheme(): Theme {")
    out.append("  return useContext(ThemeContext);")
    out.append("}")
    out.append("")

    # ---- usage example -----------------------------------------------------
    pad = "t.spacing.lg" if any(n == "lg" for n, _ in spacing_named) else (
        f"t.spacing.{spacing_named[0][0]}" if spacing_named else "16")
    rname = None
    for n, _v in rad_map:
        if n == "md":
            rname = "md"
            break
    if rname is None and rad_map:
        rname = rad_map[0][0]
    rad = f"t.radii.{rname}" if rname else "10"
    titlerole = None
    for cand in ("headline", "title", "largeTitle", "body"):
        if cand in typography:
            titlerole = _camel(cand)
            break
    if titlerole is None and typo_roles:
        titlerole = _camel(typo_roles[0])

    out.append("/*")
    out.append(" * Usage")
    out.append(" * -----")
    out.append(" * Wrap your app once, then read the theme with useTheme():")
    out.append(" *")
    out.append(" *   import { ThemeProvider, useTheme } from './theme';")
    out.append(" *   import { StyleSheet, Text, View } from 'react-native';")
    out.append(" *")
    out.append(" *   const App = () => (")
    out.append(" *     <ThemeProvider>")
    out.append(" *       <Card />")
    out.append(" *     </ThemeProvider>")
    out.append(" *   );")
    out.append(" *")
    out.append(" *   function Card() {")
    out.append(" *     const t = useTheme();")
    out.append(" *     const styles = makeStyles(t);")
    out.append(" *     return (")
    out.append(" *       <View style={styles.card}>")
    out.append(" *         <Text style={styles.title}>Aurora</Text>")
    out.append(" *       </View>")
    out.append(" *     );")
    out.append(" *   }")
    out.append(" *")
    out.append(" *   const makeStyles = (t: Theme) =>")
    out.append(" *     StyleSheet.create({")
    out.append(" *       card: {")
    out.append(" *         backgroundColor: t.colors.surface,")
    out.append(f" *         padding: {pad},")
    out.append(f" *         borderRadius: {rad},")
    out.append(" *         borderWidth: 1,")
    out.append(" *         borderColor: t.colors.border,")
    if first_shadow:
        out.append(" *         ...t.elevation.card,")
    out.append(" *       },")
    if titlerole:
        out.append(f" *       title: {{ ...t.typography.{titlerole}, color: t.colors.text }},")
    else:
        out.append(" *       title: { color: t.colors.text },")
    out.append(" *     });")
    out.append(" */")

    return "\n".join(out) + "\n"


def write_all(colors, fonts, out_dir, dark=None, typography=None, spacing=None,
              radius=None, rounded=None, shadows=None):
    os.makedirs(out_dir, exist_ok=True)
    files = {"Theme.swift": swiftui(colors, fonts, dark=dark, typography=typography,
                                    spacing=spacing, radius=radius, rounded=rounded,
                                    shadows=shadows),
             "app_theme.dart": flutter(colors, fonts, dark=dark, typography=typography,
                                       spacing=spacing, radius=radius, rounded=rounded,
                                       shadows=shadows),
             "theme.native.ts": react_native(colors, fonts, dark=dark,
                                              typography=typography, spacing=spacing,
                                              radius=radius, rounded=rounded,
                                              shadows=shadows)}
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
