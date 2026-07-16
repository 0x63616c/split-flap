"""Dimensional guards on the flap. Introspection instead of eyeballing.

Why build123d: these are plain asserts on real geometry queries — the
feedback loop OpenSCAD can't give.
"""

from splitflap_cad.flap import flap
from splitflap_cad.params import P


def test_flap_is_one_solid():
    part = flap()
    assert part.is_valid
    assert part.volume > 0
    assert len(part.solids()) == 1


def test_flap_overall_dims():
    bb = flap().bounding_box()
    assert bb.size.X == P.flap_w_over_pins
    assert bb.size.Y == P.flap_h
    assert round(bb.size.Z, 6) == P.flap_thick


def test_pin_tabs_near_pivot_edge():
    # tabs live in the lower part of the card, below the wide top section
    assert P.flap_pin_y0 + P.flap_pin_h < P.flap_wide_y0


def test_pin_tab_fits_drum_ring_hole():
    # tab cross-section (flap_pin_h x flap_thick) must pass the round
    # ring hole (diameter drum_slot_w): check the diagonal
    diag = (P.flap_pin_h**2 + P.flap_thick**2) ** 0.5
    assert diag < P.drum_slot_w


def test_pin_span_vs_drum():
    # tabs must reach into the ring holes on both sides: overall span
    # over the pins exceeds the inner clear width between the two rings
    inner_span = P.drum_barrel_len  # ring inner faces are barrel ends
    assert P.flap_w_over_pins > inner_span
    # ...but the card body itself must fit between the rings
    assert P.flap_w < inner_span
