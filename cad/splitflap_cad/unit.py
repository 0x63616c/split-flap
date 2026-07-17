"""The 28BYJ unit side plate — shell + 28BYJ motor harness + hall mount.

Motor-agnostic geometry lives in shell.py; this module adds everything
the 28BYJ-48 needs: motor screw towers, can support pad, in-plate wire
channel, hall-sensor post, and the plate lightening windows (cut around
those features, so they're per-motor too).

View it: `just cad unit` (see cad/splitflap_cad/catalog.py).
"""

from build123d import (
    Axis,
    Box,
    Circle,
    Cylinder,
    Polygon,
    Pos,
    Rectangle,
    chamfer,
    extrude,
    fillet,
)

from .params import P
from .shell import (
    back_wall,
    base_chamfers,
    base_plate,
    cap_walls,
    flap_guard,
    front_lip,
    stop_rod,
    window_profile,
    with_vendor_fins,
)


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
    hall_lo = P.hall_x - P.hall_post_w / 2 - g
    hall_hi = P.hall_x + P.hall_post_w / 2 + g
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


def motor_towers():
    """Motor screw towers, ours (replaces the vendored pair): one curved
    arm per motor ear. Footprint = rectangular bound ∩ the flap-swing
    clearance arc (about the shaft axis) − the can relief circle, corner
    fillets; flat seat at the flange height with an M3 heat-set insert
    bore at each ear hole (we heat-set instead of the vendor's trapped
    nuts). Bounds measured off the vendor STEP."""
    towers = None
    for side in (-1, +1):
        x_in = P.mount_x + side * P.tower_x_in_off
        x_out = P.mount_x + side * P.tower_x_out_off
        fp = Pos((x_in + x_out) / 2, (P.tower_y_lo + P.tower_y_hi) / 2) * Rectangle(
            abs(x_out - x_in), P.tower_y_hi - P.tower_y_lo
        )
        fp &= Pos(P.byj_can_x, P.byj_shaft_y) * Circle(P.tower_flap_relief_r)
        fp -= Pos(P.byj_can_x, P.byj_can_y) * Circle(P.byj_can_d / 2 + 0.3)
        fp = fillet(fp.vertices(), P.tower_corner_fillet)
        t = Pos(0, 0, P.unit_plate_thick) * extrude(
            fp, amount=P.byj_flange_seat - P.unit_plate_thick
        )
        t -= Pos(
            P.mount_x + side * P.byj_ear_pitch / 2,
            P.mount_y,
            P.byj_flange_seat - P.byj_insert_depth / 2,
        ) * Cylinder(P.byj_insert_d / 2, P.byj_insert_depth)
        towers = t if towers is None else towers + t
    return towers


def unit_plate():
    """Return the unit side plate Part: shell + 28BYJ harness."""
    plate = base_plate()

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
    # break the slot's cut edges so wires don't rub sharp corners — the
    # only vertical edges on the pad are the slot faces meeting the
    # inner/outer cylinder walls
    pad = chamfer(pad.edges().filter_by(Axis.Z), P.byj_pad_slot_chamfer)

    # Wire channel: enclosed tunnel inside the plate from the pad hole
    # to the -X edge — skin-thick roof and floor with the cavity
    # between, and a narrower push-in slit through the floor so the
    # wires snap in and stay held.
    chan_len = P.byj_can_x + P.unit_plate_w / 2
    cavity_h = P.unit_plate_thick - 2 * P.wire_chan_skin
    chan_pos = (P.byj_can_x - chan_len / 2, P.byj_can_y)
    plate -= Pos(*chan_pos, P.unit_plate_thick / 2) * Box(
        chan_len, P.wire_chan_w, cavity_h
    )
    # slit hugs the cavity's +Y wall — one wide floor lip instead of two
    slit_y = P.byj_can_y + (P.wire_chan_w - P.wire_chan_slit_w) / 2
    plate -= Pos(chan_pos[0], slit_y, 0) * Box(
        chan_len, P.wire_chan_slit_w, P.wire_chan_skin * 2
    )
    # flare the -X mouth 45 deg per side so the wires exit without a
    # sharp corner; open from the plate bottom up to the cavity roof
    # (full channel depth — only the roof skin runs to the edge)
    x_edge = -P.unit_plate_w / 2
    f = P.wire_chan_flare
    hw = P.wire_chan_w / 2
    mouth = Polygon(
        (x_edge, P.byj_can_y - hw - f),
        (x_edge, P.byj_can_y + hw + f),
        (x_edge + f, P.byj_can_y + hw),
        (x_edge + f, P.byj_can_y - hw),
        align=None,
    )
    plate -= extrude(mouth, amount=P.wire_chan_skin + cavity_h, dir=(0, 0, 1))

    # Lightening windows through the plate, house style.
    plate -= plate_windows()

    # Hall sensor mount: the PCB screws flat onto one narrow post block
    # spanning both holes on the hole line (-X edge, M2 self-tap
    # pilots); the rest of the board cantilevers over the pad's
    # wire-slot corridor, which stays open so the motor wires slide
    # under the board into the pad hole. The hall element hangs off the
    # -X edge on bent legs, under the magnet sweep; header wires leave
    # the same edge toward the back wall.
    post_h = P.hall_seat - P.unit_plate_thick

    def _post(x, y, w, l):
        b = Pos(x, y, P.unit_plate_thick + post_h / 2) * Box(w, l, post_h)
        # vertical edges only (bottom merges into the plate; top square)
        return chamfer(b.edges().filter_by(Axis.Z), P.hall_post_chamfer)

    hall = _post(P.hall_x, P.hall_y, P.hall_post_w, P.hall_post_l)
    for dy in (-P.hall_hole_pitch / 2, P.hall_hole_pitch / 2):
        hall -= Pos(
            P.hall_x, P.hall_y + dy, P.hall_seat - P.hall_pilot_depth / 2
        ) * Cylinder(P.hall_pilot_d / 2, P.hall_pilot_depth)

    return (
        plate + back_wall() + stop_rod() + pad + motor_towers() + flap_guard()
        + front_lip() + cap_walls() + base_chamfers() + hall
    )


def full_unit():
    """The printable unit: parametric body (incl. our motor towers) +
    verbatim vendor interconnect fins. Plate lightening windows are our
    own (plate_windows), cut in unit_plate; the tabs' screw holes become
    magnet pockets. Needs the STEP on disk."""
    return with_vendor_fins(unit_plate())


def scene():
    """Printable unit; falls back to the bare plate when the vendor STEP
    (gitignored) isn't on disk."""
    from .viewer import Scene

    try:
        u = full_unit()
    except FileNotFoundError:
        u = unit_plate()
    return Scene().add(u, "unit")


def plate_scene():
    from .viewer import Scene

    return Scene().add(unit_plate(), "plate")
