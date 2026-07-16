"""The unit side plate — holds the motor, wires, drum and hall sensor.

The module is assembled lying on its left side, so this plate is the build
base. Starts as a bare rectangle; motor boss, wire routing, drum bearing and
hall mount get added incrementally.

View it: `just cad unit` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Axis, Box, Cylinder, Plane, Polygon, Pos, Rectangle, Rot, chamfer, extrude, mirror

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
    # the guard side runs to the standard edge margin — the guard foot
    # only grazes the band's bottom corner, which the chamfer clears
    right_hi = x_hi
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
    # radius matches the vendor towers' relief arc (r=14.3, can d/2 +
    # 0.3) — a can-sized pad leaves an ugly 0.3 crescent gap against it
    pad = Pos(P.byj_can_x, P.byj_can_y, P.unit_plate_thick + P.byj_pad_h / 2) * Cylinder(
        P.byj_can_d / 2 + 0.3, P.byj_pad_h
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

    # Front lip: short wall on the front (+X) edge at the bottom (+Y)
    # corner — the guard blade's counterpart at the other end of the
    # flap opening, so the bottom flap shows framed.
    lip = Pos(
        P.unit_plate_w / 2 - P.unit_top_thick / 2,
        P.unit_plate_h / 2 - P.unit_front_lip / 2,
        P.unit_plate_thick,
    ) * extrude(
        Rectangle(P.unit_top_thick, P.unit_front_lip), amount=P.unit_back_rise
    )

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
    # the top wall's front window stops short of the guard prism, which
    # sits inside the corner and would bury the window's front chamfer
    guard_back = P.unit_plate_w / 2 + min(dx for dx, _ in P.guard_profile)
    top = cap_wall(
        -1,
        [(-edge, -P.unit_window_margin / 2), (P.unit_window_margin / 2, guard_back - 2)],
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

    # Interior base chamfers: 45° wedge strips where the plate top meets
    # the wall inner faces, so the inside corners aren't square.
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
        p = Pos(0, length / 2, 0) * Rot(90, 0, 0) * extrude(tri, amount=length)
        return Rot(0, 0, ang) * Pos(-d, 0, 0) * p

    base_cham = (
        wedge(P.unit_plate_w / 2 - P.unit_wall_thick, P.unit_plate_h, 0)  # back
        + wedge(P.unit_plate_h / 2 - P.unit_top_thick, P.unit_plate_w, 90)  # -Y
        + wedge(P.unit_plate_h / 2 - P.unit_top_thick, P.unit_plate_w, -90)  # +Y
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

    return plate + wall + rod + pad + guard + lip + top + bottom + base_cham + hall


# Interconnect tab holes, measured off the vendor STEP: 4 corner tabs
# (3mm thick) outboard of the back wall, holes on the Z axis at the
# mating faces z=0 (bottom pair) and z=53 (top pair).
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


# Motor screw towers, measured off the vendor STEP: screw bores Ø4.2 on
# (x, y=2.0), trapped-nut slots interrupting them z 11..14.6, flange
# seat (bore mouth) at z=25.
_TOWER_X = (-6.05, 29.05)
_TOWER_Y = 2.0
_TOWER_SLOT_Z = (11.0, 14.6)
_TOWER_SEAT_Z = 25.0
_TOWER_INSERT_DEPTH = 8.0  # M3 heat-set insert hole depth from the seat


def _tower_insert_mods(towers):
    """Adds deleting the vendor trapped-nut slots (we heat-set M3
    inserts instead): fill each slot with a shifted clone of the tower
    cross-section just above it (exact outline, keeps the bore), then
    plug the bore below insert depth — leaving a Ø4.2 blind hole,
    _TOWER_INSERT_DEPTH deep, opening at the flange seat."""
    z_lo, z_hi = _TOWER_SLOT_Z
    hole_bottom = _TOWER_SEAT_Z - _TOWER_INSERT_DEPTH
    adds = []
    for x in _TOWER_X:
        slab = towers & Pos(x, _TOWER_Y, z_hi + (z_hi - z_lo) / 2) * Box(
            16, 28, z_hi - z_lo
        )
        adds.append(Pos(0, 0, -(z_hi - z_lo)) * slab)
        adds.append(
            Pos(x, _TOWER_Y, (2.95 + hole_bottom) / 2)
            * Cylinder(2.6, hole_bottom - 2.95)
        )
    return adds


def full_unit():
    """The printable unit: parametric body + verbatim vendor pieces
    (interconnect fins, motor screw towers). Plate lightening windows
    are our own (plate_windows), cut in unit_plate; the tabs' screw
    holes become magnet pockets. Needs the STEP on disk."""
    from .vendor import vendor_fins, vendor_towers

    fins = vendor_fins()
    towers = vendor_towers()
    unit = unit_plate() + fins + towers
    adds, cuts = _tab_magnet_mods(fins)
    s_adds, s_cuts = _stack_tab_mods(fins)
    for a in adds + s_adds + _tower_insert_mods(towers):
        unit += a
    for c in cuts + s_cuts:
        unit -= c
    return unit
