"""Mirror backlight: the arch maths and the spacer layout.

Geometry shape is covered by the golden guard; this file guards the
*derivations* — the arch fitted to three tape measurements, the strip
budget, and the layout rule that no spacer may straddle the straight/arch
junction or collide with its neighbour.
"""

import math

import pytest
from build123d import Pos, Rot
from splitflap_cad.mirrorlight import (
    arch_angles,
    layout,
    report,
    spacer_corner,
    spacer_count,
    spacer_straight,
)
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


def test_loop_closes_with_the_roll_to_spare():
    """Wrapping the bottom is what lets the uncut 16.4ft roll go all the way
    round. What is left over gets tucked behind the glass by hand — it just
    must never go NEGATIVE, which would mean a dark stretch."""
    assert P.ml_path_len == pytest.approx(
        P.ml_bottom_run + 2 * P.ml_corner_run + 2 * P.ml_side_run + P.ml_arch_run,
        abs=1e-9,
    )
    assert 0 < P.ml_slack < 24 * IN, "no strip left, or more than a tuck's worth"


def test_corner_turns_are_tangent_to_both_contours():
    """A corner spacer only works if its arc leaves the bottom run and
    joins the side run tangentially — otherwise the strip kinks."""
    assert P.ml_corner_cx == pytest.approx(P.ml_path_x - P.ml_corner_r)
    assert P.ml_corner_cy == pytest.approx(P.ml_inset + P.ml_corner_r)
    assert P.ml_corner_r >= 1.5 * IN, "tighter than the strip will bend"


def test_layout_gaps_are_all_near_target():
    bottom, corner, side, arch, *_ = layout()
    assert corner.n == 1 and corner.gap == 0
    junction = 0.5 * side.gap + arch.lead
    for g in (bottom.gap, side.gap, arch.gap, junction, side.lead):
        # the segments solve independently, so the family spreads a little;
        # an inch either side of target still reads as "evenly spaced"
        assert abs(g - P.ml_gap) < 1.0 * IN, "gap wanders too far from 6in"


def test_no_spacer_straddles_or_overruns_a_segment_end():
    half = P.ml_spacer_len / 2
    for run in layout():
        assert run.at[0] - half >= run.lead - 1e-9
        assert run.at[-1] + half <= run.length - run.tail_k * run.gap + 1e-9


def test_spacers_never_collide_within_a_segment():
    for run in layout():
        for a, b in zip(run.at, run.at[1:]):
            assert b - a - P.ml_spacer_len > 0.5 * IN


def test_bottom_seam_lands_on_the_centreline():
    """The strip's two ends meet in the bottom run's middle gap — so that
    gap has to straddle x=0, or the seam sits under a spacer."""
    bottom = layout()[0]
    mid = [a + b for a, b in zip(bottom.at, reversed(bottom.at))]
    assert all(m == pytest.approx(bottom.length) for m in mid)
    assert bottom.n % 2 == 0, "an odd count puts a spacer on the seam"


def test_curved_spacers_have_a_flat_inner_face():
    """Flattening the chord is what makes them print as stable blocks."""
    for part in (spacer_corner(),):
        bb = part.bounding_box()
        slab = bb.max.X - bb.min.X
        assert slab > P.ml_spacer_t, "no chord material — inner face still arced"
    assert spacer_count()["total"] == sum(
        (spacer_count()[k] for k in ("straight", "arch", "corner"))
    )


def test_spacers_carry_their_own_name():
    """20 near-identical blocks in a bag is a sorting problem; the label is
    cut into the WALL face, which nobody sees once the mirror is up."""
    plain = spacer_straight().volume
    assert plain < P.ml_spacer_t * P.ml_spacer_len * P.ml_standoff, (
        "no material removed at all — rebate, breaks and label all missing"
    )
    for part in (spacer_straight(), spacer_corner()):
        top = [f for f in part.faces() if abs(f.center().Z - P.ml_standoff) < 1e-6]
        assert len(top) > 1, "engraved label missing from the wall face"


def test_every_part_prints_off_the_mirror_face():
    """z=0 is the bond face and the bed; nothing may hang below it."""
    for part in (spacer_straight(), spacer_corner()):
        assert part.bounding_box().min.Z == pytest.approx(0, abs=1e-6)
        assert part.bounding_box().max.Z == pytest.approx(P.ml_standoff, abs=1e-6)


def test_arch_spacers_are_inside_the_arch_and_symmetric():
    angles = arch_angles()
    span = P.ml_spacer_dphi / 2
    for a in angles:
        assert P.ml_path_phi < a - span and a + span < 180 - P.ml_path_phi
    mid = [a + b for a, b in zip(angles, reversed(angles))]
    assert all(m == pytest.approx(180) for m in mid), "arch layout not symmetric"


def test_rebate_locates_the_strip_without_swallowing_it():
    """It is a placement guide: deep enough to register the sleeve, shallow
    enough that the strip is never buried in it."""
    assert P.ml_groove_w - P.ml_strip_w == pytest.approx(2 * P.ml_groove_clear)
    assert 0.2 < P.ml_groove_depth / P.ml_strip_t < 0.45, "not a rebate"
    assert P.ml_strip_proud > 2.0, "strip sits too deep in the channel"
    assert P.ml_groove_z0 >= 3.0, "too little plastic between channel and glass"
    assert P.ml_groove_wall_far >= 6.0, "channel too close to the wall face"
    assert P.ml_groove_z0 < (P.ml_standoff - P.ml_groove_w) / 2, (
        "channel should ride tight to the glass, not centred in the gap"
    )
    assert P.ml_emitter_hide_deg < 8.0, "emitter visible too easily"


def test_bond_face_is_unbroken_and_the_channel_clears_it():
    """No fasteners: the mirror face is pure bonding area, and the channel
    must not eat into it."""
    part = spacer_straight()
    bond = [f for f in part.faces() if abs(f.center().Z) < 1e-6]
    assert len(bond) == 1, "the glue face should be one unbroken face"
    nominal = (P.ml_spacer_t - 2 * P.ml_break) * (P.ml_spacer_len - 2 * P.ml_break)
    assert bond[0].area == pytest.approx(nominal, rel=1e-6), (
        "something other than the edge break is eating the glue face"
    )
    assert P.ml_groove_z0 > P.ml_break, "rebate opens onto the bond face"


def test_report_covers_the_numbers_worth_buying_from():
    text = "\n".join(report())
    for want in ("loop", "spare", "spacers", "gaps", "rebate", "no fasteners"):
        assert want in text


def test_every_spacer_lands_behind_the_glass():
    """Catches a pose applied in the wrong frame: seating the parts on the
    left of a site transform mirrors the whole wall and drops every spacer
    off the mirror entirely, which still passes a bounding-box check."""
    from build123d import extrude
    from splitflap_cad.mirrorlight import mirror_profile, posed_spacers

    behind = extrude(mirror_profile(), amount=P.ml_standoff)
    for part in posed_spacers():
        assert (part - behind).volume == pytest.approx(0, abs=1e-3), (
            "spacer sticks out past the glass outline"
        )


def test_posed_spacers_put_the_channel_against_the_glass():
    """The parts are modelled bond-face-down but hang bond-face-UP on the
    wall — if the pose forgets to flip them, the strip ends up firing from
    the wall side of the gap."""
    from splitflap_cad.mirrorlight import posed_spacers, strip_solids

    strip = strip_solids()[0].bounding_box()
    glass = P.ml_standoff
    assert glass - strip.max.Z == pytest.approx(P.ml_groove_wall, abs=0.5)
    assert strip.min.Z > 2.0, "strip hard against the wall face"
    for part in posed_spacers()[:3]:
        bb = part.bounding_box()
        assert bb.min.Z == pytest.approx(0, abs=1e-6)
        assert bb.max.Z == pytest.approx(glass, abs=1e-6)
