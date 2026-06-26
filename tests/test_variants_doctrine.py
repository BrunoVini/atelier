"""Variants doctrine checks (references/capabilities/variants.md).

t44 lesson: against a careful hand-build, three distinct directions lose the
differentiation + finish axes when (a) two directions share one layout skeleton
re-skinned (the recolor/reskin trap reaches only type+color, not the layout
system), (b) a direction is bare type-on-a-ground with no signature visual moment
native to its language, or (c) the rationale is prose-only, not scannable metadata.

These guard that the variants capability TEACHES the three durable fixes, so a
regeneration reading the live reference inherits them. Doctrine-presence tests,
the same pattern as the layering / multi-brand doctrine guards.
"""
import os

HERE = os.path.dirname(__file__)
REF = os.path.join(HERE, "..", "references", "capabilities", "variants.md")


def _ref():
    with open(REF, encoding="utf-8") as fh:
        return fh.read().lower()


def test_variants_ref_exists():
    assert os.path.exists(REF), "variants capability reference must exist"


def test_doctrine_differentiate_the_layout_system():
    # differentiation must reach the structural skeleton, not only type+palette.
    t = _ref()
    assert "layout system" in t
    assert "skeleton" in t
    # the explicit failure mode must be named (recolor / reskin trap)
    assert "reskin" in t or "recolor" in t
    # density/rhythm called out as a differentiator
    assert "rhythm" in t and "density" in t


def test_doctrine_each_direction_has_a_signature_visual_moment():
    t = _ref()
    assert "signature" in t
    # a production comp, not styled placeholder text
    assert "comp" in t
    # product-native motif examples are taught (e.g. chart/gradient/masthead)
    assert "motif" in t
    assert any(k in t for k in ("chart", "gradient", "masthead"))
    # parity of visual ambition — don't ship a bare text direction next to comps
    assert "ambition" in t or "weakest direction" in t


def test_doctrine_surface_rationale_as_scannable_metadata():
    t = _ref()
    # rationale must be structured/scannable, not prose-only
    assert "metadata" in t or "scannable" in t
    # the parallel For/Optimizes/Tradeoff structure
    assert "tradeoff" in t and "optimizes" in t
    # a design-language descriptor + tags for at-a-glance comparison
    assert "design-language" in t or "design language" in t


def test_content_parity_still_taught():
    # the original, load-bearing rule must survive the additions.
    t = _ref()
    assert "content" in t and "identical" in t
    assert "parity" in t
