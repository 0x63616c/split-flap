"""Interconnect fins — the six tabs that latch modules together.

Replaces the verbatim vendor STEP crop these used to be. Six separate
solids, nothing joining them: a flat corner tab pair on the z=0 mating
face, a ramped pair on z=53, and one stacking tab per +-Y edge (the
vendor had only the +Y one).

What's fixed and what's ours: the screw axes (all six at fin_hole_x)
and the mating faces they open onto (z=0, z=53, y=+-59) are the joint
interface, carried in params as INTERFACE dims. The outlines around them
are drawn clean — every ramp here is a rise-over-run of dims we already
have, not a measured angle.

Every tab is at least fin_flat_t thick, because every tab has to take
either half of an M3 joint. test_fins.py enforces that against
joint_locs() — golden tests freeze whatever shape they are handed, so
they will happily preserve a bore cut into thin air.

Bare geometry only — no bores. shell.with_fins() unions these onto a
body and cuts each site per its kind.
"""

from build123d import Plane, Polygon, Pos, Rot, extrude, mirror

from .geo import radial_plate
from .params import P


def _corner_tab_bottom():
    """Flat plate on the z=0 mating face, +Y corner.

    Trapezoid: full fin_depth width at the outer edge, widening inward
    on a 45 deg diagonal so the arm meets the plate with some root.

    fin_flat_t thick throughout: an insert needs bore + floor behind it,
    more than the vendor's screw tabs carried. The whole arm grows inward
    to suit rather than a boss being stuck on around the hole — a
    thickened arm can't leave material cantilevered off an edge the way a
    disc on a tapering tab does.
    """
    y_out = P.unit_plate_h / 2
    profile = Polygon(
        (P.fin_wall_face, y_out),
        (P.fin_x_out, y_out),
        (P.fin_x_out, y_out - P.fin_depth),
        (P.fin_wall_face, y_out - 2 * P.fin_depth),  # 45 deg: run == fin_depth
        align=None,
    )
    return extrude(profile, amount=P.fin_flat_t)


def _corner_tab_top():
    """Ramped gusset hanging off the z=53 mating face, +Y corner.

    Full height at the wall, ramping down to fin_flat_t at the outer
    edge — so the drop is fin_top_tab_h - fin_flat_t over a fin_depth
    run, and no angle needs stating.

    It bottoms out at fin_flat_t, not at the thinner mating edge the
    vendor used, because the ramp thins toward that edge and the bore
    has width: measured at the axis this tab looks deep enough, but the
    outer lip of the bore ends up short. The vendor could taper to 3
    there — those tabs took a through screw, which doesn't care what's
    behind it; a blind insert bore does.
    """
    z_top = P.unit_back_height
    profile = Polygon(
        (P.fin_wall_face, z_top - P.fin_top_tab_h),
        (P.fin_wall_face, z_top),
        (P.fin_x_out, z_top),
        (P.fin_x_out, z_top - P.fin_flat_t),
        align=None,
    )
    return Pos(0, P.fin_hole_y, 0) * radial_plate(profile, P.fin_depth)


def _stack_tab():
    """Stacking tab on the +Y (y=59) mating face, so units stack
    vertically. Ramp below it is 45 deg — a fin_depth run again.
    fin_flat_t thick, same reason as the bottom corner tabs."""
    y_face = P.unit_plate_h / 2
    z_in = P.fin_stack_z_top - P.fin_stack_h
    profile = Polygon(
        (P.fin_wall_face, z_in),
        (P.fin_wall_face, P.fin_stack_z_top),
        (P.fin_x_out, P.fin_stack_z_top),
        (P.fin_x_out, z_in + P.fin_depth),  # 45 deg
        align=None,
    )
    return Pos(0, y_face - P.fin_flat_t / 2, 0) * radial_plate(profile, P.fin_flat_t)


def joint_locs():
    """Every M3 joint site as (pose, kind), posed on its mating face with
    +Z pointing into the module. THE interconnect interface: shell.py
    cuts each site down this axis, and every tab is built thick enough to
    take either kind, so a bore can't land where there's nothing behind
    it.

    kind is "screw" (clearance + counterbore) or "insert" (blind heat-set
    bore). Antisymmetric, because modules are identical prints: the faces
    that meet each other when units are stacked always pair a screw site
    against an insert site. See the params note.
    """
    out = []
    for y_s in (+1, -1):
        y = y_s * P.fin_hole_y
        # bottom corner, +Z inward — this face lands on a neighbour's z=53
        out.append((Pos(P.fin_hole_x, y, 0), "screw"))
        # top corner, -Z inward
        out.append((Pos(P.fin_hole_x, y, P.unit_back_height) * Rot(180, 0, 0), "insert"))
        # stack, inward off the y=+-59 face; +Y takes the insert, -Y the screw
        out.append(
            (
                Pos(P.fin_hole_x, y_s * P.unit_plate_h / 2, P.fin_stack_hole_z)
                * Rot(y_s * 90, 0, 0),
                "insert" if y_s > 0 else "screw",
            )
        )
    return out


def fins():
    """All six tabs. The vendor had no -Y stacking tab; mirroring the +Y
    half puts one on, so a stack mates top-to-bottom rather than only one
    way round."""
    half = _corner_tab_bottom() + _corner_tab_top() + _stack_tab()
    return half + mirror(half, Plane.XZ)


def scene():
    from .viewer import Scene

    return Scene().add(fins(), "fins")
