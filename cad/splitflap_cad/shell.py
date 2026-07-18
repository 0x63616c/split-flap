"""Motor-agnostic unit shell — shared by every motor variant.

The unit side plate is the build base (module assembled lying on its
left side). This module holds everything that doesn't care which motor
drives the drum: the bare base plate, back wall, flap stop rod, flap
guard, front lip, top/bottom cap walls, interior base chamfers, and the
interconnect fins with their magnet pockets.

Motor variants (unit.py = 28BYJ, unitnema.py = NEMA 14 pancake) compose
these builders and add their own motor harness + plate windows.
"""

from build123d import (
    Box,
    Cylinder,
    Plane,
    Polygon,
    Pos,
    Rectangle,
    Rot,
    chamfer,
    extrude,
    mirror,
)

from .geo import radial_plate
from .params import P


def window_profile(w, h):
    """The house window style: rectangle with 45°-chamfered corners."""
    return chamfer(Rectangle(w, h).vertices(), P.unit_window_chamfer)


def base_plate():
    """The bare base plate slab, nothing cut yet."""
    return extrude(Rectangle(P.unit_plate_w, P.unit_plate_h), amount=P.unit_plate_thick)


def back_wall():
    """Back wall: full length of the long (Y) edge, inset into the plate
    footprint — outer face flush with the -X plate edge (matches the
    vendor reference). Rises to unit_back_height total from plate bottom.
    Two windows [][] cut through: margin-wide frame at the outer edges,
    between them, and top/bottom."""
    wall_x = -(P.unit_plate_w / 2 - P.unit_wall_thick / 2)
    wall = Pos(wall_x, 0, P.unit_plate_thick) * extrude(
        Rectangle(P.unit_wall_thick, P.unit_plate_h), amount=P.unit_back_rise
    )
    win = extrude(
        Plane.YZ * window_profile(P.unit_window_w, P.unit_window_h),
        amount=P.unit_wall_thick,
        both=True,
    )
    y_off = (P.unit_window_w + P.unit_window_margin) / 2
    z_c = P.unit_plate_thick + P.unit_window_margin + P.unit_window_h / 2
    for y in (-y_off, y_off):
        wall -= Pos(wall_x, y, z_c) * win
    return wall


def stop_rod():
    """Flap stop rod: full-height pillar at the front (+Y) edge, plate
    top up to the wall-top height. Top flap rests against it."""
    rod_h = P.unit_back_height - P.unit_plate_thick
    return Pos(P.rod_x, P.rod_y, P.unit_plate_thick + rod_h / 2) * Cylinder(P.rod_r, rod_h)


def flap_guard():
    """Flap guard: angled prism wall on the front (+X/-Y) corner, plate
    top to wall top. Profile is corner-relative in params."""
    cx, cy = P.unit_plate_w / 2, -P.unit_plate_h / 2
    guard_pts = [(cx + dx, cy + dy) for dx, dy in P.guard_profile]
    # profile winding is clockwise, so pin the extrude direction to +Z
    guard = extrude(Polygon(*guard_pts, align=None), amount=P.unit_back_rise, dir=(0, 0, 1))
    return Pos(0, 0, P.unit_plate_thick) * guard


def front_lip():
    """Front lip: short wall on the front (+X) edge at the bottom (+Y)
    corner — the guard blade's counterpart at the other end of the flap
    opening, so the bottom flap shows framed."""
    return Pos(
        P.unit_plate_w / 2 - P.unit_top_thick / 2,
        P.unit_plate_h / 2 - P.unit_front_lip / 2,
        P.unit_plate_thick,
    ) * extrude(Rectangle(P.unit_top_thick, P.unit_front_lip), amount=P.unit_back_rise)


def cap_wall(y_sign, spans):
    """One top/bottom wall closing a Y side: full X width, same thickness
    as the guard's front blade, plate top to wall top.
    spans = (x_lo, x_hi) window openings along the wall."""
    y = y_sign * (P.unit_plate_h / 2 - P.unit_top_thick / 2)
    cap = Pos(0, y, P.unit_plate_thick) * extrude(
        Rectangle(P.unit_plate_w, P.unit_top_thick), amount=P.unit_back_rise
    )
    z_c = P.unit_plate_thick + P.unit_window_margin + P.unit_window_h / 2
    for x_lo, x_hi in spans:
        win = extrude(
            Plane.XZ * window_profile(x_hi - x_lo, P.unit_window_h),
            amount=P.unit_top_thick,
            both=True,
        )
        cap -= Pos((x_lo + x_hi) / 2, y, z_c) * win
    return cap


def cap_walls():
    """Both cap walls with the standard window layout: top (-Y) windows
    split at centre, front one stopping short of the guard prism;
    bottom (+Y) windows flanking the stop rod a margin shy of it."""
    edge = P.unit_plate_w / 2 - P.unit_window_margin  # outer window edge
    guard_back = P.unit_plate_w / 2 + min(dx for dx, _ in P.guard_profile)
    top = cap_wall(
        -1,
        [(-edge, -P.unit_window_margin / 2), (P.unit_window_margin / 2, guard_back - 2)],
    )
    bottom = cap_wall(
        +1,
        [
            (-edge, P.rod_x - P.rod_r - P.unit_window_margin),
            (P.rod_x + P.rod_r + P.unit_window_margin, edge),
        ],
    )
    return top + bottom


def base_chamfers():
    """Interior base chamfers: 45° wedge strips where the plate top meets
    the wall inner faces, so the inside corners aren't square."""
    c = P.unit_base_chamfer
    tri = Polygon(
        (0, P.unit_plate_thick),
        (c, P.unit_plate_thick),
        (0, P.unit_plate_thick + c),
        align=None,
    )

    def wedge(d, length, ang):
        """Wedge strip against an inner wall face d from centre, hypotenuse
        toward the box interior, run `length`, rotated ang about Z."""
        return Rot(0, 0, ang) * Pos(-d, 0, 0) * radial_plate(tri, length)

    return (
        wedge(P.unit_plate_w / 2 - P.unit_wall_thick, P.unit_plate_h, 0)  # back
        + wedge(P.unit_plate_h / 2 - P.unit_top_thick, P.unit_plate_w, 90)  # -Y
        + wedge(P.unit_plate_h / 2 - P.unit_top_thick, P.unit_plate_w, -90)  # +Y
    )


def with_fins(body):
    """body + interconnect fins, each tab's magnet pocket cut in.

    Pockets open at the mating faces so two modules meet magnet-to-
    magnet; a poke hole through the floor lets a magnet be pushed back
    out. Sites come from fins.magnet_locs(), the same list fins.py builds
    the tabs around, so a pocket can't land where there's no material.
    """
    from .fins import fins, magnet_locs

    unit = body + fins()
    for loc in magnet_locs():
        unit -= (
            loc
            * Pos(0, 0, P.fin_pocket_h / 2)
            * Cylinder((P.drum_magnet_d + P.drum_magnet_clear) / 2, P.fin_pocket_h)
        )
        unit -= loc * Pos(0, 0, P.fin_flat_t) * Cylinder(P.drum_poke_d / 2, 10)
    return unit
