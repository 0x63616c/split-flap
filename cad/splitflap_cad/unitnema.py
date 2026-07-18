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
wider leg used to overhang a narrower deck. The deck is thin
(nema_flange_t) except for a local boss at each screw hole holding the
full nema_screw_boss_t, because the motor's taps are only 2.5 deep and
an M3x6 through thinner material would bottom out before it clamped.

Printability: print deck-face down. Walls and bolt bosses rise
vertically; the only ceiling is each bolt seat, a small flat bridge
over its U-slot. The plan is clipped to a cylinder about the shaft so
every outer edge runs concentric with the drum, inside the barrel
wall sweep.

Homing: a BARE hall head (no PCB) drops into a pocket in the deck's
top face, on the drum's magnet sweep circle (drum_magnet_r) at the -Y
azimuth, leads grooved radially out to the deck edge. The deck is a
full disc over r <= mount_r, so it is the only solid thing that
reaches the sweep — a post up from the plate cannot, the deck is in
the way. Magnet boss face 28.96, deck top 25.43: the head sits in that
gap. Motor wires leave the body edge flush at -Y, drop into an open
trench in the plate and run out the buried wire_tunnel to the -X edge,
clear of the ±X legs and feet.

Bridge local frame: shaft axis at the motor MOUNTING FACE plane, +Z up
(same convention as motor.py); frames.py poses it at nema_face_z.

View it: `just cad unit-nema` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Align, Box, Circle, Cylinder, Pos, Rot, extrude

from .params import P
from .shell import (
    back_wall,
    base_chamfers,
    base_plate,
    cap_walls,
    flap_guard,
    front_lip,
    stop_rod,
    wire_tunnel,
    with_fins,
)


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
    # Feed trench: roof open from just under the body edge to the
    # channel, so the leads drop straight in. It runs under the barrel
    # sweep, but the drum's lowest feature clears the plate top by 3.3,
    # and nothing here rises above it.
    y_hi = P.byj_shaft_y - P.motor_body_w / 2 + P.nema_wire_entry_bite
    y_lo = P.nema_wire_y + P.wire_chan_w / 2
    plate -= Pos(
        P.mount_x, (y_lo + y_hi) / 2,
        P.unit_plate_thick - (P.unit_plate_thick - P.wire_chan_skin) / 2
    ) * Box(
        P.wire_chan_w, y_hi - y_lo, P.unit_plate_thick - P.wire_chan_skin
    )

    # Bridge foot inserts: M3x3 heat-set straight into the plate from
    # the top, flush — screws come down through the feet, module's
    # outer (bottom) face stays untouched.
    for side in (-1, +1):
        x = P.mount_x + side * P.nema_screw_x_off
        plate -= Pos(
            x, P.byj_shaft_y, P.unit_plate_thick - P.nema_insert_depth / 2
        ) * Cylinder(P.byj_insert_d / 2, P.nema_insert_depth)

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

    # Deck: full ring on the face, clipped to the SAME radius as the legs
    # so the plan is one arc — no ledge, no lens tips. Thin everywhere
    # except a local boss at each screw hole, which keeps the full
    # nema_screw_boss_t so an M3x6 still engages exactly the 2.5 the
    # motor's tapped hole gives (thinning under the head would only make
    # the screw bottom out early). Pilot-boss bore + 4 M3 through.
    deck = extrude(Circle(P.nema_mount_r), amount=P.nema_flange_t)
    half = P.motor_hole_pitch / 2
    screw_xy = [(x, y) for x in (-half, half) for y in (-half, half)]
    for x, y in screw_xy:
        deck += Pos(x, y, 0) * Cylinder(
            P.nema_screw_boss_d / 2, P.nema_screw_boss_t, align=(
                Align.CENTER, Align.CENTER, Align.MIN
            )
        )
    bore_h = P.nema_screw_boss_t * 3
    deck -= Cylinder(P.pilot_hole_d / 2, bore_h)
    for x, y in screw_xy:
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
        Circle(P.nema_mount_r), amount=drop + P.nema_screw_boss_t
    )

    # Homing: pocket for a bare hall head in the deck top, centred on
    # the drum's magnet sweep circle, plus a lead groove running
    # radially out to the deck edge. Cut after the clip so the groove
    # opens at the arc.
    body -= Rot(0, 0, P.nema_hall_az) * (
        Pos(P.drum_magnet_r, 0, P.nema_flange_t - P.nema_hall_pocket_d / 2)
        * Box(P.nema_hall_pocket_l, P.nema_hall_pocket_w, P.nema_hall_pocket_d)
        + Pos(
            (P.drum_magnet_r + P.nema_mount_r) / 2, 0,
            P.nema_flange_t - P.nema_hall_wire_d / 2,
        )
        * Box(
            P.nema_mount_r - P.drum_magnet_r, P.nema_hall_wire_w,
            P.nema_hall_wire_d,
        )
    )
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
