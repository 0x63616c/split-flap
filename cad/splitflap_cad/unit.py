"""The unit side plate — holds the motor, wires, drum and hall sensor.

The module is assembled lying on its left side, so this plate is the build
base. Starts as a bare rectangle; motor boss, wire routing, drum bearing and
hall mount get added incrementally.

View it: `just cad unit` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Axis, Box, Cylinder, Plane, Polygon, Pos, Rectangle, chamfer, extrude

from .params import P


def window_profile(w, h):
    """The house window style: rectangle with 45°-chamfered corners."""
    return chamfer(Rectangle(w, h).vertices(), P.unit_window_chamfer)


def plate_windows():
    """Lightening cutouts through the base plate — same chamfered-rect
    style as the wall windows; replaces the vendor's cutouts. Bounds sit
    plate_web off the neighbouring features (back wall, screw-tower zone,
    motor pad, hall pedestal, stop rod, guard) and window_margin off the
    plate edges. Returns one compound to subtract."""
    g = P.plate_web
    m = P.unit_window_margin
    x_lo = -P.unit_plate_w / 2 + P.unit_wall_thick + g
    x_hi = P.unit_plate_w / 2 - m
    y_cap = P.unit_plate_h / 2 - P.unit_top_thick - g

    # +Y band: above the tower zone, short of the flap stop rod, [][]
    # split with the same margin scheme as the walls
    lo = P.tower_zone_y + P.tower_zone_half_y + g
    hi = min(y_cap, P.rod_y - P.rod_r - g)
    w = (x_hi - x_lo - m) / 2
    cuts = [
        (x_lo + w / 2, (lo + hi) / 2, w, hi - lo),
        (x_hi - w / 2, (lo + hi) / 2, w, hi - lo),
    ]

    # -Y band: below the tower zone and motor pad, split around the hall
    # pedestal; the right window also stops short of the guard corner
    lo2 = -y_cap
    hi2 = min(P.tower_zone_y - P.tower_zone_half_y, P.byj_can_y - P.byj_can_d / 2) - g
    hall_lo = P.hall_post_x - P.hall_post_w / 2 - g
    hall_hi = P.hall_post_x + P.hall_post_w / 2 + g
    guard_lo = P.unit_plate_w / 2 + min(dx for dx, _ in P.guard_profile) - g
    right_hi = min(x_hi, guard_lo)
    cuts += [
        ((x_lo + hall_lo) / 2, (lo2 + hi2) / 2, hall_lo - x_lo, hi2 - lo2),
        ((hall_hi + right_hi) / 2, (lo2 + hi2) / 2, right_hi - hall_hi, hi2 - lo2),
    ]

    windows = None
    for x_c, y_c, w_, h_ in cuts:
        cut = Pos(x_c, y_c) * extrude(
            window_profile(w_, h_), amount=P.unit_plate_thick, both=True
        )
        windows = cut if windows is None else windows + cut
    return windows


def unit_plate():
    """Return the unit side plate Part: base plate + back wall."""
    outline = Rectangle(P.unit_plate_w, P.unit_plate_h)
    plate = extrude(outline, amount=P.unit_plate_thick)

    # Back wall: full length of the long (Y) edge, inset into the plate
    # footprint — outer face flush with the -X plate edge (matches the
    # vendor reference). Rises to unit_back_height total from plate bottom.
    wall_x = -(P.unit_plate_w / 2 - P.unit_wall_thick / 2)
    wall = Pos(wall_x, 0, P.unit_plate_thick) * extrude(
        Rectangle(P.unit_wall_thick, P.unit_plate_h), amount=P.unit_back_rise
    )

    # Two windows [][] cut through the wall: margin-wide frame at the
    # outer edges, between them, and top/bottom. Opening outline is a
    # rectangle with 45°-chamfered corners, sketched in the wall plane
    # (YZ) and extruded both ways so it punches clean through.
    win = extrude(
        Plane.YZ * window_profile(P.unit_window_w, P.unit_window_h),
        amount=P.unit_wall_thick,
        both=True,
    )
    y_off = (P.unit_window_w + P.unit_window_margin) / 2
    z_c = P.unit_plate_thick + P.unit_window_margin + P.unit_window_h / 2
    for y in (-y_off, y_off):
        wall -= Pos(wall_x, y, z_c) * win

    # --- 28BYJ harness ---
    # Support pad: pedestal under the can's end face. The can rests on it;
    # the ear screws on the towers do the clamping.
    pad = Pos(P.byj_can_x, P.byj_can_y, P.unit_plate_thick + P.byj_pad_h / 2) * Cylinder(
        P.byj_can_d / 2, P.byj_pad_h
    )
    # hole continues through the plate below — open to the outside
    pad_hole = Pos(P.byj_can_x, P.byj_can_y, (P.unit_plate_thick + P.byj_pad_h) / 2) * Cylinder(
        P.byj_pad_hole_r, (P.unit_plate_thick + P.byj_pad_h) * 2
    )
    pad -= pad_hole
    plate -= pad_hole

    # Wire slot: cut straight through the pad ring on both sides (along Y,
    # same width as the underside channel) so wires can pass either way.
    pad -= Pos(P.byj_can_x, P.byj_can_y, P.unit_plate_thick + P.byj_pad_h / 2) * Box(
        P.wire_chan_w, P.byj_can_d * 2, P.byj_pad_h * 2
    )

    # Wire channel: groove in the plate underside from the pad hole to the
    # -X edge (z=0 up to wire_chan_d).
    chan_len = P.byj_can_x + P.unit_plate_w / 2
    plate -= Pos(
        P.byj_can_x - chan_len / 2, P.byj_can_y, P.wire_chan_d / 2
    ) * Box(chan_len, P.wire_chan_w, P.wire_chan_d)

    # Lightening windows through the plate, house style.
    plate -= plate_windows()

    # Screw towers: imported verbatim from the vendor STEP (vendor.py) —
    # their bridges, trapped-nut slots and drum-corner relief replace the
    # plain boxes we had. Composed in full_unit(), not here, so this
    # module stays importable without the STEP on disk.

    # Flap stop rod: full-height pillar at the front (+Y) edge, plate top
    # up to the wall-top height. Top flap rests against it.
    rod_h = P.unit_back_height - P.unit_plate_thick
    rod = Pos(P.rod_x, P.rod_y, P.unit_plate_thick + rod_h / 2) * Cylinder(P.rod_r, rod_h)

    # Flap guard: angled prism wall on the front (+X/-Y) corner, plate top
    # to wall top. Profile is corner-relative in params.
    cx, cy = P.unit_plate_w / 2, -P.unit_plate_h / 2
    guard_pts = [(cx + dx, cy + dy) for dx, dy in P.guard_profile]
    # profile winding is clockwise, so pin the extrude direction to +Z
    guard = extrude(Polygon(*guard_pts, align=None), amount=P.unit_back_rise, dir=(0, 0, 1))
    guard = Pos(0, 0, P.unit_plate_thick) * guard

    # Top/bottom walls: close the -Y side (module top once standing) and
    # the +Y side. Full X width, same thickness as the guard's front
    # blade, plate top to wall top, two [][] windows each.
    def cap_wall(y_sign, spans):
        """spans = (x_lo, x_hi) window openings along the wall."""
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

    edge = P.unit_plate_w / 2 - P.unit_window_margin  # outer window edge
    top = cap_wall(
        -1, [(-edge, -P.unit_window_margin / 2), (P.unit_window_margin / 2, edge)]
    )
    # bottom: two windows flanking the stop rod, a margin shy of it on
    # both sides — wide one to the back, narrow one to the front edge
    bottom = cap_wall(
        +1,
        [
            (-edge, P.rod_x - P.rod_r - P.unit_window_margin),
            (P.rod_x + P.rod_r + P.unit_window_margin, edge),
        ],
    )

    # Hall sensor mount (Kingsman-style): pedestal level with the motor
    # ear seat, sensor PCB screws flat on top — two M2 pilots on the same
    # X line, hall_hole_pitch apart in Y.
    post_h = P.hall_seat - P.unit_plate_thick
    hall = Pos(P.hall_post_x, P.hall_y, P.unit_plate_thick + post_h / 2) * Box(
        P.hall_post_w, P.hall_post_l, post_h
    )
    # chamfer the vertical + top edges (bottom stays square, it merges
    # into the plate)
    hall = chamfer(
        hall.edges().filter_by(Axis.Z) + hall.edges().group_by(Axis.Z)[-1],
        P.hall_post_chamfer,
    )
    for dy in (-P.hall_hole_pitch / 2, P.hall_hole_pitch / 2):
        hall -= Pos(
            P.hall_x, P.hall_y + dy, P.hall_seat - P.hall_pilot_depth / 2
        ) * Cylinder(P.hall_pilot_d / 2, P.hall_pilot_depth)

    return plate + wall + rod + pad + guard + top + bottom + hall


def full_unit():
    """The printable unit: parametric body + verbatim vendor pieces
    (interconnect fins, motor screw towers). Plate lightening windows
    are our own (plate_windows), cut in unit_plate. Needs the STEP on
    disk."""
    from .vendor import vendor_fins, vendor_towers

    return unit_plate() + vendor_fins() + vendor_towers()
