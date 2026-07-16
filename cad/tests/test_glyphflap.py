"""Charset/artwork invariants — cheap 2D checks, no extrusion."""

from splitflap_cad.glyphflap import CHARSET, _glyph_halves, char_slug
from splitflap_cad.params import P


def test_charset_matches_drum():
    assert len(CHARSET) == P.drum_flap_count
    assert CHARSET[0] == " ", "blank must sit at slot 0 (homing)"
    assert len(set(CHARSET)) == len(CHARSET)


def test_slugs_unique_and_safe():
    slugs = [char_slug(c) for c in CHARSET]
    assert len(set(slugs)) == len(slugs)
    assert all(s.isalnum() for s in slugs)


def test_all_glyphs_render_and_fit():
    budget = P.flap_h - P.glyph_top_keepout
    for ch in CHARSET[1:]:
        top, bottom = _glyph_halves(ch)
        assert top is not None or bottom is not None, ch
        if top is not None:
            bb = top.bounding_box()
            assert bb.size.X <= P.glyph_w_max + 1e-6, ch
            assert bb.max.Y <= budget + 1e-6, ch
        if bottom is not None:
            bb = bottom.bounding_box()
            assert bb.size.X <= P.glyph_w_max + 1e-6, ch
            assert -bb.min.Y <= budget + 1e-6, ch
