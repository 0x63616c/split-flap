"""Charset/artwork invariants — cheap 2D checks, no extrusion."""

from collections import Counter

from splitflap_cad.glyphflap import CHARSET, _glyph_halves, char_slug, flap_at
from splitflap_cad.params import P
from splitflap_cad.prusa3mf import _mesh_part


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


def _non_manifold_edges(tris):
    e = Counter()
    for a, b, c in tris:
        for u, v in ((a, b), (b, c), (c, a)):
            e[frozenset((u, v))] += 1
    return sum(1 for ct in e.values() if ct != 2)


def test_flap_meshes_are_manifold():
    """The exported card/glyph meshes must be watertight — Bambu rejects
    non-manifold meshes and won't apply per-volume colours. Sample a few
    flaps incl. multi-solid (Q) and a descender (+)."""
    center = (0.0, P.flap_h / 2, P.flap_thick / 2)
    for i in (0, 17, 50):
        card, glyphs = flap_at(i)
        for shape in (card, glyphs):
            if shape is None:
                continue
            _, tris = _mesh_part(shape, center)
            assert _non_manifold_edges(tris) == 0, f"flap {i} non-manifold"
