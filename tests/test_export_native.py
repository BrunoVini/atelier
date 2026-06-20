"""Tests for the native theme exporter — focus on the idiomatic SwiftUI handoff.

The SwiftUI emitter must produce a COMPLETE, idiomatic theme from the contract:
dynamic light+dark colors (scheme-aware), a Theme value + EnvironmentKey, a named
type scale, spacing + radius, and honest disclosure of what SwiftUI can't express.
Token fidelity (every emitted value EXACTLY equals the source) is the load-bearing
property — verified here against known hexes.
"""
from export_native import swiftui, flutter, react_native, _swift_weight, _camel, _num

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


def test_swiftui_spacing_and_radius_named():
    out = swiftui(COLORS, ["Inter"], dark=DARK, spacing=SPACING, rounded=ROUNDED)
    assert "public struct ThemeSpacing {" in out
    assert "public let xs: CGFloat = 4" in out
    assert "public let xxxl: CGFloat = 48" in out
    assert "public struct ThemeRadius {" in out
    assert "public let pill: CGFloat = 999" in out


def test_swiftui_honest_about_shadow_and_compile():
    out = swiftui(COLORS, ["Inter"], dark=DARK, shadows=SHADOWS)
    # Discloses the box-shadow limitation + that it was not compiled.
    assert "box-shadow" in out
    assert "NOT COMPILED" in out
    assert "func cardShadow()" in out


def test_swiftui_no_dark_falls_back_disclosed():
    out = swiftui(COLORS, ["Inter"])  # no dark map
    assert "no dark palette in the contract" in out
    # still a valid dynamic color (light used for both)
    assert "init(light: Color, dark: Color)" in out


def test_flutter_and_rn_still_emit():
    f = flutter(COLORS, ["Inter"])
    assert "class AppColors {" in f
    assert "0xFF2F6BFF" in f
    rn = react_native(COLORS, ["Inter"])
    assert "export const theme" in rn
    assert '"#2F6BFF"' in rn or '"#2f6bff"' in rn
