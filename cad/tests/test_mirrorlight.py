"""Mirror backlight: the arch maths and the spacer layout.

Geometry shape is covered by the golden guard; this file guards the
*derivations* — the arch fitted to three tape measurements, the strip
budget, and the layout rule that no spacer may straddle the straight/arch
junction or collide with its neighbour.
"""

import math

import pytest
from splitflap_cad.mirrorlight import arch_angles, layout, report
from splitflap_cad.params import IN, P


def test_arch_passes_through_the_measured_points():
    """R and centre are derived — check the circle actually hits both top
    corners and the apex."""
    cy, r = P.ml_arch_cy, P.ml_arch_r
    apex = (0.0, P.ml_mirror_h)
    corner = (P.ml_mirror_w / 2, P.ml_mirror_side_h)
    for x, y in (apex, corner):
        assert math.hypot(x, y - cy) == pytest.approx(r, abs=1e-9)


def test_arch_centre_sits_below_the_springline():
    """Rise (16in) < half width (17in), so the arc is a touch over a
    semicircle: the sides meet it with a small kink, not tangentially."""
    assert P.ml_arch_cy < P.ml_mirror_side_h
    assert 170 < 180 - 2 * P.ml_path_phi < 175


def test_junction_is_on_both_inset_curves():
    x, y = P.ml_path_x, P.ml_path_junction_y
    assert math.hypot(x, y - P.ml_arch_cy) == pytest.approx(P.ml_path_r, abs=1e-9)
    assert P.ml_path_x == pytest.approx(P.ml_mirror_w / 2 - P.ml_inset)


def test_strip_budget_has_slack_and_never_needs_cutting():
    assert P.ml_path_len == pytest.approx(
        2 * P.ml_side_run + P.ml_arch_run, abs=1e-9
    )
    assert P.ml_slack > 0, "lit path longer than the strip — nothing to cut it with"
    assert P.ml_slack / IN == pytest.approx(36.7, abs=0.2)


def test_layout_gaps_are_all_near_target():
    side, arch, _ = layout()
    junction = side.tail + arch.lead
    assert junction == pytest.approx(P.ml_gap)
    for g in (side.gap, arch.gap, junction):
        assert abs(g - P.ml_gap) < 0.5 * IN, "gap wanders too far from 6in"


def test_no_spacer_straddles_or_overruns_a_segment_end():
    half = P.ml_spacer_len / 2
    for run in layout()[:2]:
        assert run.at[0] - half >= run.lead - 1e-9
        assert run.at[-1] + half <= run.length - run.tail + 1e-9


def test_spacers_never_collide_within_a_segment():
    for run in layout()[:2]:
        for a, b in zip(run.at, run.at[1:]):
            assert b - a - P.ml_spacer_len > 0.5 * IN


def test_arch_spacers_are_inside_the_arch_and_symmetric():
    angles = arch_angles()
    span = P.ml_spacer_dphi / 2
    for a in angles:
        assert P.ml_path_phi < a - span and a + span < 180 - P.ml_path_phi
    mid = [a + b for a, b in zip(angles, reversed(angles))]
    assert all(m == pytest.approx(180) for m in mid), "arch layout not symmetric"


def test_groove_holds_the_strip_with_clearance_and_sits_near_flush():
    assert P.ml_groove_w - P.ml_strip_w == pytest.approx(2 * P.ml_groove_clear)
    proud = P.ml_groove_depth - P.ml_groove_over - P.ml_strip_t
    assert -0.5 <= proud <= 0.0, "emitting face should sit ~flush with the mouth"
    assert P.ml_groove_z0 > 0 and P.ml_groove_z0 + P.ml_groove_w < P.ml_standoff


def test_screw_pocket_has_walls_on_both_sides_and_meat_under_the_head():
    head_r = P.ml_screw_head_d / 2
    inner_wall = P.ml_screw_r - head_r
    to_groove = P.ml_spacer_t - P.ml_groove_depth - (P.ml_screw_r + head_r)
    assert inner_wall >= 2.0, "counterbore too close to the wall-side face"
    assert to_groove >= 2.0, "counterbore breaks into the groove floor"
    assert P.ml_cbore_depth + P.ml_screw_meat == pytest.approx(P.ml_standoff)
    assert P.ml_screw_meat >= 8.0, "not enough plastic under the head to pull on"
    assert P.ml_screw_pitch + P.ml_screw_head_d < P.ml_spacer_len


def test_report_covers_the_numbers_worth_buying_from():
    text = "\n".join(report())
    for want in ("lit path", "slack", "spacers", "gaps", "groove", "#8"):
        assert want in text
