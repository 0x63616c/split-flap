"""Interconnect fins — the five tabs that latch modules together.

Replaces the verbatim vendor STEP crop these used to be. Five separate
solids, nothing joining them: a flat corner tab pair on the z=0 mating
face, a ramped pair on z=53, and one stacking tab per +-Y edge.

What's fixed and what's ours: the magnet axes (all five at fin_hole_x)
and the mating faces they open onto (z=0, z=53, y=+-59) are the latch
interface, carried in params as INTERFACE dims. The outlines around them
are drawn clean — every ramp here is a rise-over-run of dims we already
have, not a measured angle.

Bare geometry only. shell.with_fins() unions these onto a body and turns
the holes into magnet pockets.
"""

from build123d import Plane, Polygon, Pos, extrude, mirror

from .geo import radial_plate
from .params import P


def _corner_tab_bottom():
    """Flat plate on the z=0 mating face, +Y corner.

    Trapezoid: full fin_depth width at the outer edge, widening inward
    on a 45 deg diagonal so the arm meets the plate with some root.
    """
    y_out = P.unit_plate_h / 2
    profile = Polygon(
        (P.fin_wall_face, y_out),
        (P.fin_x_out, y_out),
        (P.fin_x_out, y_out - P.fin_depth),
        (P.fin_wall_face, y_out - 2 * P.fin_depth),  # 45 deg: run == fin_depth
        align=None,
    )
    return extrude(profile, amount=P.fin_tab_t)


def _corner_tab_top():
    """Ramped gusset hanging off the z=53 mating face, +Y corner.

    Full height at the wall, ramping down to plate thickness at the
    outer edge — so the drop is fin_top_tab_h - fin_tab_t over a
    fin_depth run, and no angle needs stating.
    """
    z_top = P.unit_back_height
    profile = Polygon(
        (P.fin_wall_face, z_top - P.fin_top_tab_h),
        (P.fin_wall_face, z_top),
        (P.fin_x_out, z_top),
        (P.fin_x_out, z_top - P.fin_tab_t),
        align=None,
    )
    return Pos(0, P.fin_hole_y, 0) * radial_plate(profile, P.fin_depth)


def _stack_tab():
    """Stacking tab on the +Y (y=59) mating face, so units stack
    vertically. Ramp below it is 45 deg — a fin_depth run again."""
    y_face = P.unit_plate_h / 2
    z_in = P.fin_stack_z_top - P.fin_stack_h
    profile = Polygon(
        (P.fin_wall_face, z_in),
        (P.fin_wall_face, P.fin_stack_z_top),
        (P.fin_x_out, P.fin_stack_z_top),
        (P.fin_x_out, z_in + P.fin_depth),  # 45 deg
        align=None,
    )
    return Pos(0, y_face - P.fin_tab_t / 2, 0) * radial_plate(profile, P.fin_tab_t)


def fins():
    """All five tabs, mirrored onto both +-Y edges.

    The vendor had no -Y stacking tab; we mirror one on so a stack mates
    top-to-bottom instead of only in one direction.
    """
    half = _corner_tab_bottom() + _corner_tab_top() + _stack_tab()
    return half + mirror(half, Plane.XZ)


def scene():
    from .viewer import Scene

    return Scene().add(fins(), "fins")


def compare_scene():
    """Ours solid, the vendor crop ghosted over it. TEMPORARY — goes when
    the fins are signed off, along with vendor.py."""
    from .vendor import vendor_fins
    from .viewer import Scene

    return (
        Scene()
        .add(fins(), "fins_ours", "orange")
        .add(vendor_fins(), "fins_vendor", "gray", alpha=0.35)
    )
