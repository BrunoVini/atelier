"""Fabricated-social-proof + dead-link gates (t01 battery finding). A greenfield page
shipped a fake customer/logo wall, two invented testimonials, and 6 aria-disabled links
— the canonical AI-SaaS-slop kit — and the old slop_check reported it clean. These must
flag `important`, WITHOUT false-positiving on a real site's lone testimonials or a single
header logo (the known-good editorial page has 3 legitimate pull-quote blockquotes)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from slop_check import check_html


def _kinds(html, severity=None):
    return {f["kind"] for f in check_html(html) if severity is None or f["severity"] == severity}


PROOF_KIT = (
    '<!doctype html><html><body>'
    '<section class="logos"><p>Trusted by</p>'
    '<span class="logo">Northwind</span><span class="logo">Acme</span>'
    '<span class="logo">Globex</span><span class="logo">Initech</span></section>'
    '<section><blockquote>It changed how we ship. — Jane Smith, VP Eng at Northwind</blockquote>'
    '<blockquote>Indispensable. — Bob Lee, SRE at Acme</blockquote></section>'
    '</body></html>'
)

# A real editorial page: pull-quote blockquotes, but NO logo/clients wall and no "trusted by".
EDITORIAL = (
    '<!doctype html><html><body>'
    '<article><blockquote>The sea is calm tonight.</blockquote>'
    '<blockquote>The tide is full, the moon lies fair.</blockquote>'
    '<blockquote>Only from the long line of spray.</blockquote></article>'
    '</body></html>'
)

SINGLE_LOGO = (
    '<!doctype html><html><body><header><img class="logo" alt="Brand"></header>'
    '<main><p>One honest product description with no fabricated proof at all here.</p></main>'
    '</body></html>'
)


def test_fabricated_proof_kit_is_important():
    assert "fabricated-social-proof" in _kinds(PROOF_KIT, "important"), check_html(PROOF_KIT)


def test_editorial_pullquotes_are_not_flagged():
    # testimonials-without-a-wall must NOT trip the combined detector
    assert "fabricated-social-proof" not in _kinds(EDITORIAL)


def test_single_header_logo_not_flagged():
    assert "fabricated-social-proof" not in _kinds(SINGLE_LOGO)


def test_too_many_dead_links_is_important():
    links = "".join('<a href="#" aria-disabled="true">x</a>' for _ in range(6))
    assert "too-many-dead-links" in _kinds(f"<html><body><nav>{links}</nav></body></html>", "important")


def test_a_few_disabled_links_are_fine():
    links = "".join('<a href="#" aria-disabled="true">x</a>' for _ in range(3))
    assert "too-many-dead-links" not in _kinds(f"<html><body><nav>{links}</nav></body></html>")
