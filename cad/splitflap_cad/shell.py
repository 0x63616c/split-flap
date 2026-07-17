"""Motor-agnostic unit shell — shared by every motor variant.

The unit side plate is the build base (module assembled lying on its
left side). This module holds everything that doesn't care which motor
drives the drum: the bare base plate, back wall, flap stop rod, flap
guard, front lip, top/bottom cap walls, interior base chamfers, and the
vendor interconnect fins with their magnet-pocket mods.

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


# Interconnect tabs, measured off the vendor STEP: hole centres at
# (x=-51.89, y=+-54.61), mating faces z=0 (bottom tabs, flat 3mm
# plates spanning x -56.28..-47.5) and z=53 (top tabs, 45-deg ramped
# gussets ~6.6mm thick at the hole).
_TAB_HOLE_X = -51.89
_TAB_HOLE_Y = 54.61
_TAB_W_X = 8.78   # tab footprint width along X
_TAB_Y_IN = 41.56  # bottom tab arm inner edge |y| (arm runs to the +-59 edge)
_TAB_THICK = 3.0  # bottom tab plate thickness
_TAB_FLOOR = 1.5  # pocket floor thickness behind the magnet


def _tab_magnet_mods(fins):
    """(adds, cuts) turning the tabs' screw holes into magnet pockets
    (same rhinocats 6x3 magnet + clearances as the drum), opening at
    the mating faces, poke hole through the floor to eject. The top
    tabs' ramped gussets are deep enough as-is; each flat bottom tab
    arm gets thickened by stacking a shifted copy of itself, so the
    pad follows the vendor outline exactly."""
    pocket_h = P.drum_magnet_t + 0.3
    pad_h = pocket_h + _TAB_FLOOR - _TAB_THICK
    adds, cuts = [], []
    for y_s in (-1, +1):
        y = y_s * _TAB_HOLE_Y
        for z_face, s in ((0.0, +1), (P.unit_back_height, -1)):
            # s points into the module from the mating face
            at = Pos(_TAB_HOLE_X, y, 0)
            if s > 0:  # flat bottom tab: clone the arm, shift up, union
                y_edge = P.unit_plate_h / 2  # arm runs out to the plate edge
                arm = fins & Pos(
                    _TAB_HOLE_X,
                    y_s * (_TAB_Y_IN + y_edge) / 2,
                    _TAB_THICK / 2,
                ) * Box(_TAB_W_X + 2, y_edge - _TAB_Y_IN + 2, _TAB_THICK)
                adds.append(Pos(0, 0, pad_h) * arm)
            cuts.append(
                at
                * Pos(0, 0, z_face + s * pocket_h / 2)
                * Cylinder((P.drum_magnet_d + P.drum_magnet_clear) / 2, pocket_h)
            )
            cuts.append(
                at
                * Pos(0, 0, z_face + s * 4)
                * Cylinder(P.drum_poke_d / 2, 10)
            )
    return adds, cuts


# Stacking tab, measured off the vendor STEP: middle of the back frame's
# +Y edge, 3mm plate (y 56..59), magnet hole axis Y at the mating face
# y=59. The vendor has no -Y counterpart; we mirror one on so units
# stack vertically.
_STACK_TAB_Y = (56.0, 59.0)
_STACK_HOLE_Z = 26.5


def _stack_tab_mods(fins):
    """(adds, cuts): clone + mirror the bottom stacking tab onto the -Y
    (top) edge, thicken both inward by a shifted self-clone (the 3mm
    plate can't hold pocket + floor), then magnet pocket at each mating
    face and a poke hole through the floor — same scheme as the corner
    tabs."""
    pocket_h = P.drum_magnet_t + 0.3
    tab_t = _STACK_TAB_Y[1] - _STACK_TAB_Y[0]
    pad_h = pocket_h + _TAB_FLOOR - tab_t
    tab = fins & Pos(
        _TAB_HOLE_X, (_STACK_TAB_Y[0] + _STACK_TAB_Y[1]) / 2, _STACK_HOLE_Z
    ) * Box(12, tab_t, 20)
    adds, cuts = [], []
    for y_s in (+1, -1):
        t = tab if y_s > 0 else mirror(tab, Plane.XZ)
        adds.append(t + Pos(0, -y_s * pad_h, 0) * t)
        y_face = y_s * _STACK_TAB_Y[1]
        cuts.append(
            Pos(_TAB_HOLE_X, y_face - y_s * pocket_h / 2, _STACK_HOLE_Z)
            * Rot(90, 0, 0)
            * Cylinder((P.drum_magnet_d + P.drum_magnet_clear) / 2, pocket_h)
        )
        cuts.append(
            Pos(_TAB_HOLE_X, y_face - y_s * 4, _STACK_HOLE_Z)
            * Rot(90, 0, 0)
            * Cylinder(P.drum_poke_d / 2, 10)
        )
    return adds, cuts


def with_vendor_fins(body):
    """body + verbatim vendor interconnect fins, the tabs' screw holes
    turned into magnet pockets. Needs the STEP on disk."""
    from .vendor import vendor_fins

    fins = vendor_fins()
    unit = body + fins
    adds, cuts = _tab_magnet_mods(fins)
    s_adds, s_cuts = _stack_tab_mods(fins)
    for a in adds + s_adds:
        unit += a
    for c in cuts + s_cuts:
        unit -= c
    return unit
