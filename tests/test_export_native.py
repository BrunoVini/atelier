"""Tests for the native theme exporter — focus on the idiomatic SwiftUI handoff.

The SwiftUI emitter must produce a COMPLETE, idiomatic theme from the contract:
dynamic light+dark colors (scheme-aware), a Theme value + EnvironmentKey, a named
type scale, spacing + radius, and honest disclosure of what SwiftUI can't express.
Token fidelity (every emitted value EXACTLY equals the source) is the load-bearing
property — verified here against known hexes.
"""
from export_native import (swiftui, flutter, react_native, _swift_weight, _camel,
                           _num, _parse_box_shadow, _flutter_weight)


def test_flutter_weight_maps_numeric_and_named():
    assert _flutter_weight("700") == "w700"
    assert _flutter_weight("400") == "w400"
    assert _flutter_weight("600") == "w600"
    assert _flutter_weight("bold") == "w700"
    assert _flutter_weight("regular") == "w400"
    # unknown -> a REAL weight, never fabricated
    assert _flutter_weight("zzz") == "w400"

COLORS = {
    "background": "#F7F8FA", "surface": "#FFFFFF", "text": "#1A1D24",
    "primary": "#2F6BFF", "onPrimary": "#FFFFFF", "danger": "#D6453D",
    "border": "#E2E6EC",
}
DARK = {
    "background": "#0E1116", "surface": "#171B22", "text": "#EDF0F5",
    "primary": "#6E9BFF", "onPrimary": "#0E1116", "danger": "#FF6B62",
    "border": "#2A313C",
}
TYPO = {
    "title": {"family": "Inter", "size": "28", "weight": "700", "line_height": "34"},
    "body": {"family": "Inter", "size": "16", "weight": "400", "line_height": "24"},
}
SPACING = ["4", "8", "12", "16", "24", "32", "48"]
ROUNDED = {"sm": "6", "md": "10", "lg": "14", "pill": "999"}
SHADOWS = {"card": "0 1px 2px rgba(0,0,0,0.06)"}


def test_camel_preserves_existing_camelcase():
    # The classic regression: onPrimary must NOT flatten to "onprimary".
    assert _camel("onPrimary") == "onPrimary"
    assert _camel("primary") == "primary"
    assert _camel("on-primary") == "onPrimary"
    assert _camel("text_secondary") == "textSecondary"


def test_swift_weight_maps_numeric_and_named():
    assert _swift_weight("700") == "bold"
    assert _swift_weight("400") == "regular"
    assert _swift_weight("600") == "semibold"
    assert _swift_weight("semibold") == "semibold"
    # Unknown -> a REAL case, never fabricated.
    assert _swift_weight("zzz") == "regular"


def test_num_strips_units():
    assert _num("16px") == "16"
    assert _num("999") == "999"
    assert _num("1.5rem") == "1.5"
    assert _num("auto") is None


def test_swiftui_dynamic_color_initializer():
    out = swiftui(COLORS, ["Inter"], dark=DARK)
    # The scheme-aware idiom: a Color(light:dark:) init backed by a dynamic UIColor.
    assert "init(light: Color, dark: Color)" in out
    assert "UIColor { traits in" in out
    assert "traits.userInterfaceStyle == .dark" in out
    # Uses sRGB, not a guessed colorspace.
    assert "Color(.sRGB" in out


def test_swiftui_token_fidelity_light_and_dark():
    out = swiftui(COLORS, ["Inter"], dark=DARK)
    # primary light #2F6BFF -> .184, .420, 1.000 ; dark #6E9BFF -> .431, .608, 1.000
    assert "light: .srgb(0.184, 0.420, 1.000)" in out
    assert "dark:  .srgb(0.431, 0.608, 1.000)" in out
    # text light #1A1D24 -> .102 .114 .141 ; dark #EDF0F5 -> .929 .941 .961
    assert "light: .srgb(0.102, 0.114, 0.141)" in out
    assert "dark:  .srgb(0.929, 0.941, 0.961)" in out


def test_swiftui_every_role_present_both_schemes():
    out = swiftui(COLORS, ["Inter"], dark=DARK)
    for role in COLORS:
        assert f"public let {_camel(role)} = Color(" in out, role
    # onPrimary survives as camelCase.
    assert "public let onPrimary = Color(" in out


def test_swiftui_theme_struct_and_environment():
    out = swiftui(COLORS, ["Inter"], dark=DARK, spacing=SPACING, rounded=ROUNDED,
                  typography=TYPO)
    assert "public struct Theme {" in out
    assert "public let colors = ThemeColors()" in out
    assert "struct ThemeKey: EnvironmentKey" in out
    assert "var theme: Theme {" in out
    # The usage example reads tokens via @Environment.
    assert "@Environment(\\.theme)" in out


def test_swiftui_type_scale_size_weight_lineheight():
    out = swiftui(COLORS, ["Inter"], dark=DARK, typography=TYPO)
    assert "public struct ThemeTypography {" in out
    # title: size 28, weight bold, lineHeight 34 -> lineSpacing 6
    assert '.custom("Inter", size: 28).weight(.bold)' in out
    assert "lineHeight: 34" in out
    assert "lineSpacing: 6" in out
    # the idiomatic .textStyle modifier exists
    assert "func textStyle(_ spec: TextStyleSpec) -> some View" in out
    # a NAMED text-style enum + an environment-reading named overload (ergonomic
    # .textStyle(.title) that does NOT rebuild ThemeTypography per call)
    assert "public enum TextStyle: CaseIterable {" in out
    assert "func textStyle(_ style: TextStyle) -> some View" in out
    assert "struct NamedTextStyle: ViewModifier" in out
    assert "@Environment(\\.theme) private var theme" in out
    assert "theme.typography[keyPath: style.keyPath]" in out


def test_swiftui_honest_about_lineheight_limit():
    out = swiftui(COLORS, ["Inter"], dark=DARK, typography=TYPO)
    # discloses that SwiftUI .lineSpacing only APPROXIMATES the token line height
    assert "lineSpacing" in out and "APPROXIMATE" in out.upper()
    assert "intrinsic" in out or "between lines" in out.lower() or "BETWEEN lines" in out


def test_swiftui_spacing_and_radius_named():
    out = swiftui(COLORS, ["Inter"], dark=DARK, spacing=SPACING, rounded=ROUNDED)
    assert "public struct ThemeSpacing {" in out
    assert "public let xs: CGFloat = 4" in out
    assert "public let xxxl: CGFloat = 48" in out
    assert "public struct ThemeRadius {" in out
    assert "public let pill: CGFloat = 999" in out


def test_parse_box_shadow_layers_and_color():
    layers = _parse_box_shadow(
        "0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)")
    assert len(layers) == 2
    # (r,g,b,a, offx, offy, blur)
    assert layers[0] == (16, 24, 40, 0.06, 0.0, 1.0, 2.0)
    assert layers[1] == (16, 24, 40, 0.1, 0.0, 1.0, 3.0)
    # hex color form
    h = _parse_box_shadow("0 2px 4px #101828")
    assert h and h[0][:3] == (16, 24, 40)
    # garbage -> [] so the caller falls back honestly
    assert _parse_box_shadow("inset") == []
    assert _parse_box_shadow("") == []


def test_swiftui_shadow_uses_real_token_color_per_layer():
    out = swiftui(COLORS, ["Inter"], dark=DARK,
                  shadows={"card": "0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)"})
    # the helper carries the token's REAL base color (#101828 -> .063 .094 .157), not
    # a hardcoded .black, and stacks BOTH layers (blur/2 -> radius 1 and 1.5)
    assert "red: 0.063, green: 0.094, blue: 0.157, opacity: 0.06" in out
    assert "red: 0.063, green: 0.094, blue: 0.157, opacity: 0.1" in out
    assert "radius: 1," in out and "radius: 1.5," in out
    # no hardcoded black guess when the token parses
    assert ".black.opacity(0.10)" not in out


def test_swiftui_honest_about_shadow_and_compile():
    out = swiftui(COLORS, ["Inter"], dark=DARK, shadows=SHADOWS)
    # Discloses the box-shadow limitation + that it was not compiled.
    assert "box-shadow" in out
    assert "NOT COMPILED" in out
    assert "func cardShadow()" in out


def test_swiftui_spacing_has_scale_array():
    out = swiftui(COLORS, ["Inter"], dark=DARK, spacing=SPACING)
    assert "var scale: [CGFloat]" in out


def test_swiftui_no_dark_falls_back_disclosed():
    out = swiftui(COLORS, ["Inter"])  # no dark map
    assert "no dark palette in the contract" in out
    # still a valid dynamic color (light used for both)
    assert "init(light: Color, dark: Color)" in out


def test_rn_still_emits():
    rn = react_native(COLORS, ["Inter"])
    assert "export const theme" in rn
    assert '"#2F6BFF"' in rn or '"#2f6bff"' in rn


# --- Flutter: a COMPLETE idiomatic Material 3 theme handoff -------------------

def test_flutter_color_fidelity_argb():
    out = flutter(COLORS, ["Inter"], dark=DARK)
    # hex -> 0xFF + RRGGBB ARGB (opaque); both schemes.
    assert "Color(0xFF2F6BFF)" in out  # primary light
    assert "Color(0xFF6E9BFF)" in out  # primary dark
    assert "Color(0xFF1A1D24)" in out  # text light
    assert "Color(0xFFEDF0F5)" in out  # text dark
    assert "Color(0xFFD6453D)" in out  # danger light
    assert "Color(0xFFFF6B62)" in out  # danger dark


def test_flutter_uses_material3():
    out = flutter(COLORS, ["Inter"], dark=DARK)
    assert "useMaterial3: true" in out


def test_flutter_builds_both_themedata():
    out = flutter(COLORS, ["Inter"], dark=DARK)
    # a light AND a dark ThemeData, brightness-correct
    assert "static ThemeData get light" in out
    assert "static ThemeData get dark" in out
    assert "brightness: Brightness.light" in out
    assert "brightness: Brightness.dark" in out


def test_flutter_colorscheme_maps_roles():
    out = flutter(COLORS, ["Inter"], dark=DARK)
    # the canonical ColorScheme slots are wired from the contract roles
    assert "ColorScheme(" in out
    assert "primary:" in out
    assert "onPrimary:" in out
    assert "surface:" in out
    assert "error:" in out  # danger -> error


def test_flutter_colorscheme_surface_container_ramp():
    # Modern M3: when a contract carries a surface elevation ramp
    # (background < surface < elevated), wire the surfaceContainer* slots +
    # onSurfaceVariant / outlineVariant — not just the minimal slots.
    full = dict(COLORS)
    full.update({"elevated": "#FFFFFF", "secondary": "#4A5160", "muted": "#8A92A3"})
    fulld = dict(DARK)
    fulld.update({"elevated": "#1F242D", "secondary": "#AEB6C4", "muted": "#717B8C"})
    out = flutter(full, ["Inter"], dark=fulld)
    assert "surfaceContainerLowest:" in out
    assert "surfaceContainerHighest:" in out
    assert "onSurfaceVariant:" in out
    assert "outlineVariant:" in out


def test_flutter_colorscheme_accent_to_tertiary():
    full = dict(COLORS); full["accent"] = "#7A5CFF"
    fulld = dict(DARK); fulld["accent"] = "#A78BFF"
    out = flutter(full, ["Inter"], dark=fulld)
    assert "tertiary:" in out
    # accent light #7A5CFF -> 0xFF7A5CFF on the tertiary slot
    assert "tertiary: Color(0xFF7A5CFF)" in out


def test_flutter_theme_extension_with_copywith_and_lerp():
    out = flutter(COLORS, ["Inter"], dark=DARK, spacing=SPACING, rounded=ROUNDED,
                  typography=TYPO)
    # the Flutter-canonical token carrier for things outside ColorScheme
    assert "class AppTokens extends ThemeExtension<AppTokens>" in out
    assert "AppTokens copyWith(" in out
    assert "AppTokens lerp(" in out
    # lerp must actually interpolate colors (not a non-null-safe stub)
    assert "Color.lerp(" in out


def test_flutter_extension_carries_brand_and_semantic_colors():
    out = flutter(COLORS, ["Inter"], dark=DARK)
    # roles that don't fit ColorScheme (accent/success/warning/border + brand aliases)
    # live on the extension so nothing is dropped
    assert "border" in out
    # both light and dark instances of the extension exist
    assert "AppTokens.light" in out or "static const AppTokens light" in out or "_lightTokens" in out
    assert "AppTokens.dark" in out or "static const AppTokens dark" in out or "_darkTokens" in out


def test_flutter_texttheme_weights_and_sizes():
    out = flutter(COLORS, ["Inter"], dark=DARK, typography=TYPO)
    assert "TextTheme(" in out
    # title: size 28 weight 700 -> FontWeight.w700, height = 34/28
    assert "fontSize: 28" in out
    assert "FontWeight.w700" in out
    assert "fontSize: 16" in out
    assert "FontWeight.w400" in out
    # fontFamily wired
    assert "fontFamily: 'Inter'" in out
    # line height expressed as the EXACT unitless ratio (lineHeight / size), not a
    # pre-rounded decimal — full double precision + self-documenting.
    assert "height:" in out
    # title: lineHeight 34 / size 28 — emitted as the exact division expression
    assert "height: 34 / 28" in out
    # body: 24 / 16
    assert "height: 24 / 16" in out
    # no lossy pre-rounded decimal for these ratios
    assert "1.2143" not in out and "1.5," not in out.replace("height: 24 / 16", "")


def test_flutter_spacing_and_radius_constants():
    out = flutter(COLORS, ["Inter"], dark=DARK, spacing=SPACING, rounded=ROUNDED)
    # spacing scale present as doubles
    assert "4" in out and "48" in out
    # radii named
    assert "999" in out  # pill
    # radius helper as BorderRadius is ergonomic but at minimum the values present
    assert "sm" in out and "md" in out and "lg" in out and "pill" in out


def test_flutter_context_accessor_ergonomic():
    out = flutter(COLORS, ["Inter"], dark=DARK)
    # an ergonomic accessor: context.tokens reading Theme.of(context).extension<AppTokens>()
    assert "extension" in out and "AppTokens get tokens" in out
    assert "Theme.of(context).extension<AppTokens>()" in out


def test_flutter_accessor_asserts_instead_of_silent_fallback():
    # A missing extension must fail LOUDLY (assert with a clear message), not
    # silently return the light tokens — a silent fallback masks an unthemed
    # subtree showing light tokens in dark mode.
    out = flutter(COLORS, ["Inter"], dark=DARK)
    assert "assert(" in out
    # no silent `?? AppTokens.light` fallback in the accessor
    assert "?? AppTokens.light" not in out


def test_flutter_lerp_interpolates_spacing():
    # Every lerp-able field must actually interpolate — including the spacing list.
    out = flutter(COLORS, ["Inter"], dark=DARK, spacing=SPACING)
    # spacing is interpolated element-wise, not returned verbatim
    assert "spacing: spacing," not in out


def test_flutter_typography_is_lerpable_extension():
    # Typography participates in theme transitions: a ThemeExtension with copyWith
    # + a lerp that uses TextStyle.lerp, registered on ThemeData, read via
    # context.type — not just a static const class.
    out = flutter(COLORS, ["Inter"], dark=DARK, typography=TYPO)
    assert "class AppTypography extends ThemeExtension<AppTypography>" in out
    assert "TextStyle.lerp(" in out
    assert "AppTypography get type" in out
    assert "toTextTheme()" in out  # builds the M3 TextTheme from itself


def test_flutter_elevation_is_lerpable_extension():
    out = flutter(COLORS, ["Inter"], dark=DARK, shadows=SHADOWS)
    assert "class AppElevation extends ThemeExtension<AppElevation>" in out
    # lerps a List<BoxShadow> the idiomatic way
    assert "BoxShadow.lerpList(" in out
    assert "AppElevation get elevation" in out


def test_flutter_extensions_registered_on_themedata():
    out = flutter(COLORS, ["Inter"], dark=DARK, spacing=SPACING, rounded=ROUNDED,
                  typography=TYPO, shadows=SHADOWS)
    # every concern is registered as a ThemeExtension so context.<x> resolves
    assert "AppTypography" in out
    assert "AppElevation" in out
    # the extensions list carries the typography + elevation extensions
    assert "extensions:" in out


def test_flutter_full_m3_texttheme_slots():
    # The TextTheme should fill the canonical M3 slots across the families, not
    # just a sparse 7 — so stock widgets (AppBar, ListTile, chips, labels) inherit.
    out = flutter(COLORS, ["Inter"], dark=DARK, typography={
        "largeTitle": {"family": "Inter", "size": "34", "weight": "700", "line_height": "41"},
        "title": {"family": "Inter", "size": "28", "weight": "700", "line_height": "34"},
        "headline": {"family": "Inter", "size": "20", "weight": "600", "line_height": "26"},
        "body": {"family": "Inter", "size": "16", "weight": "400", "line_height": "24"},
        "callout": {"family": "Inter", "size": "15", "weight": "500", "line_height": "21"},
        "caption": {"family": "Inter", "size": "13", "weight": "400", "line_height": "18"},
        "mono": {"family": "JetBrains Mono", "size": "14", "weight": "400", "line_height": "20"},
    })
    for slot in ("displayLarge:", "headlineLarge:", "titleLarge:", "titleMedium:",
                 "bodyLarge:", "bodyMedium:", "labelLarge:", "labelSmall:"):
        assert slot in out, slot


def test_flutter_honest_header():
    out = flutter(COLORS, ["Inter"], dark=DARK, shadows=SHADOWS)
    assert "NOT COMPILED" in out
    # discloses the box-shadow mapping caveat
    assert "shadow" in out.lower()


def test_flutter_no_dark_falls_back_disclosed():
    out = flutter(COLORS, ["Inter"])  # no dark map
    assert "no dark palette" in out.lower()
    # still emits both ThemeData (dark uses light values, disclosed)
    assert "static ThemeData get dark" in out
