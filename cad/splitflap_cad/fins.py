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

from build123d import Cylinder, Plane, Polygon, Pos, Rot, extrude, mirror

from .geo import radial_plate
from .params import P


def _boss(loc):
    """Magnet boss: a disc inscribed in the tab's square footprint,
    standing fin_boss_h off the mating face into the module. `loc` puts
    its base on that face, axis pointing inward.

    The flat tabs are fin_tab_t thick — under half what a magnet needs
    behind it — so the material has to come from somewhere. A disc
    concentric with the magnet is the honest shape for that: it's thick
    exactly where the pocket is and nowhere else.
    """
    return loc * Pos(0, 0, P.fin_boss_h / 2) * Cylinder(P.fin_depth / 2, P.fin_boss_h)


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


def magnet_locs():
    """Every magnet axis, posed on its mating face pointing into the
    module: (location, is_flat_tab). THE latch interface — shell.py cuts
    pockets here and fins() bosses the flat tabs to suit.

    The top corner tabs are already deep enough at the axis, so they
    take no boss.
    """
    out = []
    for y_s in (+1, -1):
        y = y_s * P.fin_hole_y
        out.append((Pos(P.fin_hole_x, y, 0), True))  # bottom, +Z inward
        out.append(
            (Pos(P.fin_hole_x, y, P.unit_back_height) * Rot(180, 0, 0), False)
        )  # top, -Z inward
        out.append(
            (
                Pos(P.fin_hole_x, y_s * P.unit_plate_h / 2, P.fin_stack_hole_z)
                * Rot(-y_s * 90, 0, 0)
            , True)
        )  # stack, inward along -y_s
    return out


def fins():
    """All five tabs plus the -Y stacking tab the vendor lacks (mirrored
    on so a stack mates top-to-bottom, not just one way), with magnet
    bosses on the flat ones."""
    half = _corner_tab_bottom() + _corner_tab_top() + _stack_tab()
    body = half + mirror(half, Plane.XZ)
    for loc, flat in magnet_locs():
        if flat:
            body += _boss(loc)
    return body


def scene():
    from .viewer import Scene

    return Scene().add(fins(), "fins")
