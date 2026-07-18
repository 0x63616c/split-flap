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


def wire_tunnel(plate, y, x_in):
    """Cut the motor-wire tunnel into `plate`: an enclosed cavity buried
    inside the plate on centreline `y`, running from x_in out to the -X
    edge, where it flares open.

    Skin-thick roof and floor with the cavity between, plus a narrower
    push-in slit through the floor (hugging the cavity's +Y wall, so one
    wide floor lip rather than two) — the wires snap in and stay held.
    The -X mouth flares 45 deg per side, open from the plate bottom up
    to the cavity roof, so only the roof skin runs to the edge and the
    wires leave without a sharp corner.

    Motor-agnostic: each variant picks its own y and x_in and feeds the
    wires in however its motor presents them.
    """
    chan_len = x_in + P.unit_plate_w / 2
    cavity_h = P.unit_plate_thick - 2 * P.wire_chan_skin
    x_mid = x_in - chan_len / 2
    plate -= Pos(x_mid, y, P.unit_plate_thick / 2) * Box(
        chan_len, P.wire_chan_w, cavity_h
    )
    slit_y = y + (P.wire_chan_w - P.wire_chan_slit_w) / 2
    plate -= Pos(x_mid, slit_y, 0) * Box(
        chan_len, P.wire_chan_slit_w, P.wire_chan_skin * 2
    )
    x_edge = -P.unit_plate_w / 2
    f = P.wire_chan_flare
    hw = P.wire_chan_w / 2
    mouth = Polygon(
        (x_edge, y - hw - f),
        (x_edge, y + hw + f),
        (x_edge + f, y + hw),
        (x_edge + f, y - hw),
        align=None,
    )
    return plate - extrude(mouth, amount=P.wire_chan_skin + cavity_h, dir=(0, 0, 1))


def with_fins(body):
    """body + interconnect fins, each tab's half of its M3 joint cut in.

    A "screw" site gets an M3 clearance hole right through the tab, with
    the head counterbore on the FAR face — the one pointing away from the
    joint. That is the only face a driver can reach: the mating face is
    pressed flat against the neighbour's tab, so a head sunk there would
    be sealed inside the joint line, unreachable and clamping nothing.
    The screw goes in from outside, crosses the tab, and lands in the
    neighbour's insert.

    An "insert" site gets a blind heat-set bore opening AT the mating
    face — that one really does face the joint, because it's the thread
    the screw arrives into — with fin_joint_floor of solid behind it.

    Sites and kinds come from fins.joint_locs(), the same list fins.py
    builds the tabs around, so a bore can't land where there's no
    material.
    """
    from .fins import fins, joint_locs

    unit = body + fins()
    for loc, kind in joint_locs():
        if kind == "insert":
            unit -= (
                loc
                * Pos(0, 0, P.fin_insert_depth / 2)
                * Cylinder(P.fin_insert_d / 2, P.fin_insert_depth)
            )
        else:
            # through-hole first, run past both faces rather than flush
            # with them (no coplanar boolean). It only ever pokes into
            # air: the screw tabs are the flat ones, with nothing inboard
            # of them.
            unit -= loc * Pos(0, 0, P.fin_flat_t / 2) * Cylinder(
                P.screw_hole_d / 2, 3 * P.fin_flat_t
            )
            # counterbore on the far face (local +Z is INTO the module,
            # away from the joint), open outward so a driver can reach it
            unit -= (
                loc
                * Pos(0, 0, P.fin_flat_t - P.fin_cbore_depth / 2)
                * Cylinder(P.fin_cbore_d / 2, P.fin_cbore_depth)
            )
    return unit
