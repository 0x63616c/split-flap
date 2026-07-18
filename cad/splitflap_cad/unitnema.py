"""The NEMA unit side plate + bridge — pancake motor variant.

The pancake NEMA 14 sits face-UP on the base plate, sunk nema_recess
into a shallow pocket that locates it laterally, body inside the drum
barrel's interior, shaft coaxial with the 28BYJ variant's (mount_x,
byj_shaft_y). Its tapped mount holes open upward, so a printed BRIDGE
drops over it: a ring deck on the face (pilot bore + 4 M3 clearance
holes — the motor's own screws clamp deck to face) with a solid
chord-segment leg down each ±X body flat landing on the plate, each
held by an M3x8 from above into a flush heat-set insert. Full-height well
channels through the deck rim and wall faces give the bolts + hex key
a straight vertical drop onto spot-faced seats.

Deck, legs and feet share ONE plan radius (nema_mount_r), so the
outline is a single arc — no ledge and no lens-tip points where a
wider leg used to overhang a narrower deck. The deck is flat
nema_flange_t throughout: the motor's taps are only 2.5 deep, so an
M3x6 through anything thinner would bottom out before it clamped.

Printability: print deck-face down. Walls and bolt bosses rise
vertically; the only ceiling is each bolt seat, a small flat bridge
over its U-slot. The plan is clipped to a cylinder about the shaft so
every outer edge runs concentric with the drum, inside the barrel
wall sweep.

Homing: a BARE hall head (no PCB) drops into a pocket in the deck's
top face, on the drum's magnet sweep circle (drum_magnet_r) at the -Y
azimuth. Its leads drop straight DOWN through a hole beside the
pocket, not out to the rim — the deck edge is r 25.5 and the barrel
wall sweeps 26.5, so a rim exit would pinch the wires against the
turning drum in a 1.0 gap. The deck is a full disc over r <= mount_r,
so it is the only solid thing that reaches the sweep — a post up from
the plate cannot, the deck is in the way. Magnet boss face 28.96, deck
top 26.30: the head sits in that gap.

Motor wires leave the body edge flush at -Y, drop into an open trench
in the plate and run out the buried wire_tunnel to the -X edge, clear
of the ±X legs and feet.

Bridge local frame: shaft axis at the motor MOUNTING FACE plane, +Z up
(same convention as motor.py); frames.py poses it at nema_face_z.

View it: `just cad unit-nema` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Box, Circle, Cylinder, Pos, Rot, extrude

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
    wire_tunnel,
    with_fins,
)


def plate_windows():
    """Lightening cutouts through the base plate, same chamfered-rect
    style as the walls. The 28BYJ variant has its own set (unit.py); the
    obstacles here are different enough that sharing one would mean a
    shape keyed to neither motor.

    What the plate must keep:
      - everything under the bridge. Its feet are the only things
        touching the plate, but they land wherever the mount circle
        allows, so the whole nema_mount_r disc about the shaft is
        reserved rather than two foot patches — the feet carry the
        motor's whole reaction torque into the plate, and a window
        edge running past them is where that would tear out.
      - the buried wire channel and its feed trench, which are already
        cavities: a window crossing one would open the tunnel's side
        and let the wires fall out.

    Both keepouts are grown by plate_web, and the windows are the bands
    left over: a wide pair above the bridge, one strip out at -X beside
    it (split off the channel, which runs under it to the edge), and a
    pair below. Returns one compound to subtract.
    """
    g = P.plate_web
    m = P.unit_window_margin
    x_lo = -P.unit_plate_w / 2 + P.unit_wall_thick + g
    x_hi = P.unit_plate_w / 2 - m
    y_cap = P.unit_plate_h / 2 - P.unit_top_thick - g

    bridge_r = P.nema_mount_r + g            # keepout disc about the shaft
    bridge_hi = P.byj_shaft_y + bridge_r     # 23.5
    bridge_lo = P.byj_shaft_y - bridge_r     # -35.5
    bridge_x_lo = P.mount_x - bridge_r
    chan_hi = P.nema_wire_y + P.wire_chan_w / 2 + g   # channel roof edge
    chan_lo = P.nema_wire_y - P.wire_chan_w / 2 - g

    # +Y band: clear above the bridge, stopping short of the stop rod.
    # [][] split on the same margin scheme as the walls.
    lo = bridge_hi
    hi = min(y_cap, P.rod_y - P.rod_r - g)
    w = (x_hi - x_lo - m) / 2
    cuts = [
        (x_lo + w / 2, (lo + hi) / 2, w, hi - lo),
        (x_hi - w / 2, (lo + hi) / 2, w, hi - lo),
    ]

    # -X strip beside the bridge. Its bottom is the wire channel, not the
    # bridge: the channel runs out to the -X edge right through here.
    cuts.append(
        (
            (x_lo + bridge_x_lo) / 2, (chan_hi + bridge_hi) / 2,
            bridge_x_lo - x_lo, bridge_hi - chan_hi,
        )
    )

    # -Y band: below whichever reaches further down, bridge or channel.
    lo2 = -y_cap
    hi2 = min(bridge_lo, chan_lo)
    cuts += [
        (x_lo + w / 2, (lo2 + hi2) / 2, w, hi2 - lo2),
        (x_hi - w / 2, (lo2 + hi2) / 2, w, hi2 - lo2),
    ]

    windows = None
    for x_c, y_c, w_, h_ in cuts:
        cut = Pos(x_c, y_c) * extrude(
            window_profile(w_, h_), amount=P.unit_plate_thick, both=True
        )
        windows = cut if windows is None else windows + cut
    return windows


def nema_plate():
    """Return the NEMA unit side plate Part: shell + motor recess +
    wire tunnel + bridge-foot inserts."""
    plate = base_plate()

    # Motor recess: square pocket the body sits down into, so the plate
    # locates the motor laterally instead of leaving that to the bridge
    # walls alone. Shallow — the bolt feet still land on the plate top.
    pocket_w = P.motor_body_w + 2 * P.nema_recess_clear
    plate -= Pos(
        P.mount_x, P.byj_shaft_y, P.unit_plate_thick - P.nema_recess / 2
    ) * Box(pocket_w, pocket_w, P.nema_recess)

    # Wire tunnel. The pancake's leads leave the body edge flush at the
    # rear face, so unlike the 28BYJ there is no centre hole to feed
    # through — the motor is rotated to present its leads at -Y and an
    # open trench takes them from the body edge down to the buried
    # channel. -Y is the only free azimuth: the bridge legs and feet own
    # ±X out to r 25.35, and the channel has to clear them.
    plate = wire_tunnel(plate, P.nema_wire_y, P.mount_x)
    # Feed trench: roof open from just under the body edge all the way
    # onto the channel centreline, so BOTH bundles land in open air. The
    # motor leads come off the body edge at the top of it; the hall
    # leads fall out of the bridge deck at the magnet sweep radius,
    # which is over the buried channel's roof — without this they would
    # drop onto solid plastic. Wider than the channel: two bundles.
    # It runs under the barrel sweep, but the drum's lowest feature
    # clears the plate top by 3.3 and nothing here rises above it.
    y_hi = P.byj_shaft_y - P.motor_body_w / 2 + P.nema_wire_entry_bite
    y_lo = P.nema_wire_y
    plate -= Pos(
        P.mount_x, (y_lo + y_hi) / 2,
        P.unit_plate_thick - (P.unit_plate_thick - P.wire_chan_skin) / 2
    ) * Box(
        P.nema_wire_entry_w, y_hi - y_lo,
        P.unit_plate_thick - P.wire_chan_skin,
    )

    # Bridge foot inserts: M3x3 heat-set straight into the plate from
    # the top, flush — screws come down through the feet, module's
    # outer (bottom) face stays untouched.
    for side in (-1, +1):
        x = P.mount_x + side * P.nema_screw_x_off
        plate -= Pos(
            x, P.byj_shaft_y, P.unit_plate_thick - P.nema_insert_depth / 2
        ) * Cylinder(P.byj_insert_d / 2, P.nema_insert_depth)

    # Lightening windows through the plate, house style.
    plate -= plate_windows()

    return (
        plate + back_wall() + stop_rod() + flap_guard() + front_lip()
        + cap_walls() + base_chamfers()
    )


def nema_bridge():
    """The bridge, one printed part (local frame: shaft axis at the
    motor face plane, +Z up): a ring DECK over the whole face (pilot
    bore + all 4 M3 clearance holes) joining a solid chord-segment LEG
    down each ±X body flat — the leg fills everything outboard of the
    flat, out to the mount circle. Every outer edge is clipped
    concentric with the drum. Each bolt gets an open-back U-slot down
    its leg — bolt + hex key drop straight in from above onto a flat
    seat."""
    wall_in = P.motor_body_w / 2 + P.nema_body_clear
    drop = P.nema_face_z - P.unit_plate_thick  # face plane -> plate top

    # Deck: full ring on the face, flat, clipped to the SAME radius as
    # the legs so the plan is one arc — no ledge, no lens tips.
    # Pilot-boss bore + 4 M3 through.
    deck = extrude(Circle(P.nema_mount_r), amount=P.nema_flange_t)
    half = P.motor_hole_pitch / 2
    bore_h = P.nema_flange_t * 3
    deck -= Cylinder(P.pilot_hole_d / 2, bore_h)
    for x in (-half, half):
        for y in (-half, half):
            deck -= Pos(x, y, 0) * Cylinder(P.screw_hole_d / 2, bore_h)

    body = deck
    z_seat = -drop + P.nema_foot_h
    rise = drop + P.nema_flange_t  # plate top -> deck TOP, flush with it
    z_mid = (P.nema_flange_t - drop) / 2
    slab_out = P.nema_mount_r + 2  # overshoot; the mount-circle clip trims it
    for side in (-1, +1):
        # Leg: one solid chord segment — everything outboard of the body
        # flat, out to the mount circle, plate top to the deck top. The
        # inner face is the chord; the plan clip below cuts the arc.
        leg = Pos(side * (wall_in + slab_out) / 2, 0, z_mid) * Box(
            slab_out - wall_in, 2 * P.nema_mount_r, rise
        )
        body += leg

        # Bolt path: open-back U-slot down the column (Ø well + a slot
        # out the back face — no thin outer skin), stopping on the flat
        # head seat; M3 clearance continues through to the insert. The
        # seat prints as a small flat bridge over the slot — fine at
        # this size.
        x_screw = side * P.nema_screw_x_off
        chan_top = P.nema_flange_t + 1  # punch past the deck top
        chan_h = chan_top - z_seat
        chan = Pos(x_screw, 0, (z_seat + chan_top) / 2) * Cylinder(
            P.nema_seat_well_d / 2, chan_h
        )
        chan += Pos(
            side * (abs(x_screw) + P.nema_foot_len) , 0, (z_seat + chan_top) / 2
        ) * Box(2 * P.nema_foot_len, P.nema_seat_well_d, chan_h)
        body -= chan
        body -= Pos(x_screw, 0, -drop + P.nema_foot_h / 2) * Cylinder(
            P.screw_hole_d / 2, P.nema_foot_h * 3
        )

    # Clip the whole plan to the mount cylinder: outer edges concentric
    # with the drum, inside the barrel wall sweep.
    body &= Pos(0, 0, -drop) * extrude(
        Circle(P.nema_mount_r), amount=drop + P.nema_flange_t
    )

    # Homing: pocket for a bare hall head in the deck top, centred on
    # the drum's magnet sweep circle. The leads drop straight DOWN
    # through the deck beside it — NOT out to the rim, where the 1.0 gap
    # to the barrel wall would pinch them against the turning drum. The
    # hole is offset tangentially at the same radius: outboard would
    # leave 0.7 of rim wall, inboard is the motor body's top face.
    body -= Rot(0, 0, P.nema_hall_az) * (
        Pos(P.drum_magnet_r, 0, P.nema_flange_t - P.nema_hall_pocket_d / 2)
        * Box(P.nema_hall_pocket_l, P.nema_hall_pocket_w, P.nema_hall_pocket_d)
    )
    body -= Rot(0, 0, P.nema_hall_az + P.nema_hall_lead_az_off) * Pos(
        P.drum_magnet_r, 0, 0
    ) * Cylinder(P.nema_hall_lead_d / 2, P.nema_flange_t * 3)
    return body


def m3_button(length):
    """Scene mock of an M3 button-head bolt: head + shank, tip at z=0,
    head seat plane at z=length (local, pointing up)."""
    from build123d import Sphere

    shank = Pos(0, 0, length / 2) * Cylinder(P.motor_screw_d / 2, length)
    head = Pos(0, 0, length) * (
        Pos(0, 0, -P.bolt_head_d / 2 + P.bolt_head_h)
        * Sphere(P.bolt_head_d / 2)
        & Pos(0, 0, P.bolt_head_h / 2) * Cylinder(P.bolt_head_d / 2, P.bolt_head_h)
    )
    return shank + head


def posed_foot_bolts():
    """Both M3x8 foot bolts posed in unit coords: head seated in the
    well on the foot top, shank down through foot + insert, tip 0.5
    inside the plate."""
    tip_z = P.unit_plate_thick + P.nema_foot_h - P.nema_foot_bolt_l
    bolts = None
    for side in (-1, +1):
        b = Pos(
            P.mount_x + side * P.nema_screw_x_off, P.byj_shaft_y, tip_z
        ) * m3_button(P.nema_foot_bolt_l)
        bolts = b if bolts is None else bolts + b
    return bolts


def full_unit_nema():
    """The printable NEMA unit: parametric body + interconnect fins."""
    return with_fins(nema_plate())


def scene():
    """NEMA unit: plate + fins, bridge posed, motor ghost face-up, foot
    bolts, drum ghost around it (NEMA-bore inner; same axial pose as the
    28BYJ build)."""
    from .drum import posed_drum_parts
    from .frames import NEMA_FACE_IN_UNIT
    from .motor import motor
    from .viewer import Scene

    u = full_unit_nema()
    drum_o, drum_i = posed_drum_parts("nema")
    return (
        Scene()
        .add(u, "unit_nema", "orange")
        .add(NEMA_FACE_IN_UNIT * nema_bridge(), "bridge", "violet")
        .add(NEMA_FACE_IN_UNIT * motor(), "motor", "steelblue", alpha=0.5)
        .add(posed_foot_bolts(), "foot_bolts_m3x8", "silver")
        .add(drum_o, "drum_outer", "gray", alpha=0.3)
        .add(drum_i, "drum_inner", "hotpink", alpha=0.3)
    )


def bridge_scene():
    from .viewer import Scene

    return Scene().add(nema_bridge(), "bridge_nema")


def plate_scene():
    from .viewer import Scene

    return Scene().add(nema_plate(), "plate_nema")
