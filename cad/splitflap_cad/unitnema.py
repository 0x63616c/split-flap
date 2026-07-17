"""The NEMA unit side plate + bridge — pancake motor variant.

The pancake NEMA 14 sits face-UP flat on the base plate, body inside
the drum barrel's interior, shaft coaxial with the 28BYJ variant's
(mount_x, byj_shaft_y). Its tapped mount holes open upward, so a
printed BRIDGE drops over it: a ring deck on the face (pilot bore +
4 M3 clearance holes — the motor's own screws clamp deck to face) with
a wall down each ±X body flat ending in a foot on the plate, each held
by an M3x8 from above into a flush heat-set insert. Full-height well
channels through the deck rim and wall faces give the bolts + hex key
a straight vertical drop onto spot-faced seats.

Printability: print deck-face down. Walls rise vertically; each foot
is topped by a 45° back wedge (no flat ceiling in print). The whole
plan is clipped to a cylinder about the shaft so every outer edge runs
concentric with the drum, inside the barrel wall sweep.

Hall/homing mount: OPEN. The 28BYJ hall post spot is buried under the
motor body and a horizontal board above the face would cross the shaft;
candidates are a vertical-board mast or TMC2209 sensorless homing —
decide when the motor is in hand.

Bridge local frame: shaft axis at the motor MOUNTING FACE plane, +Z up
(same convention as motor.py); frames.py poses it at nema_face_z.

View it: `just cad unit-nema` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Box, Circle, Cylinder, Polygon, Pos, Rot, extrude

from .geo import radial_plate
from .params import P
from .shell import (
    back_wall,
    base_chamfers,
    base_plate,
    cap_walls,
    flap_guard,
    front_lip,
    stop_rod,
    with_vendor_fins,
)


def nema_plate():
    """Return the NEMA unit side plate Part: shell + bridge-foot
    inserts. No motor pocket — the body sits flat, located by the
    bridge walls."""
    plate = base_plate()

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
    bore + all 4 M3 clearance holes) joining a wall + foot + back wedge
    down each ±X body flat. Every outer edge is clipped concentric with
    the drum. Each foot bolt gets a full-height Ø well channel cut
    through deck rim, wall face and wedge — the bolt + hex key drop
    straight in from above onto a spot-faced seat."""
    wall_in = P.motor_body_w / 2 + P.nema_body_clear
    wall_out = wall_in + P.nema_leg_t
    drop = P.nema_face_z - P.unit_plate_thick  # face plane -> plate top

    # Deck: full ring on the face — clipped tighter than the rest (its
    # top grazes the guide-rail sweep band), pilot-boss bore, 4 M3.
    deck = extrude(Circle(P.nema_flange_r), amount=P.nema_flange_t)
    deck -= Cylinder(P.pilot_hole_d / 2, P.nema_flange_t * 3)
    half = P.motor_hole_pitch / 2
    for x in (-half, half):
        for y in (-half, half):
            deck -= Pos(x, y, 0) * Cylinder(
                P.screw_hole_d / 2, P.nema_flange_t * 3
            )

    body = deck
    foot_out = wall_out + P.nema_foot_len
    z_foot_top = -drop + P.nema_foot_h
    for side in (-1, +1):
        # Wall: up the body flat, plate top to the face plane — plan
        # clipped to the DECK's radius so the side profile follows the
        # deck contour exactly (only feet + wedges run wider).
        wall = Pos(side * (wall_in + wall_out) / 2, 0, -drop / 2) * Box(
            P.nema_leg_t, P.nema_wall_w, drop
        )
        wall &= Pos(0, 0, -drop) * extrude(Circle(P.nema_flange_r), amount=drop)
        # Foot + 45° back wedge (no flat ceiling printed deck-down).
        foot = Pos(
            side * (wall_in + foot_out) / 2, 0, (-drop + z_foot_top) / 2
        ) * Box(foot_out - wall_in, P.nema_foot_w, P.nema_foot_h)
        wedge = radial_plate(
            Polygon(
                (wall_out, z_foot_top),
                (foot_out, z_foot_top),
                (wall_out, z_foot_top + P.nema_foot_len),
                align=None,
            ),
            P.nema_foot_w,
        )
        if side < 0:
            wedge = Rot(0, 0, 180) * wedge
        body += wall + foot + wedge

        # Foot bolt path: full-height well channel from above the deck
        # down to the spot-faced head seat on the foot top, then M3
        # clearance on through the foot.
        x_screw = side * P.nema_screw_x_off
        chan_top = P.nema_flange_t + 1  # punch past the deck top
        body -= Pos(x_screw, 0, (z_foot_top + chan_top) / 2) * Cylinder(
            P.nema_seat_well_d / 2, chan_top - z_foot_top
        )
        body -= Pos(x_screw, 0, -drop + P.nema_foot_h / 2) * Cylinder(
            P.screw_hole_d / 2, P.nema_foot_h * 3
        )

    # Clip the whole plan to the mount cylinder: outer edges concentric
    # with the drum, inside the barrel wall sweep.
    body &= Pos(0, 0, -drop) * extrude(
        Circle(P.nema_mount_r), amount=drop + P.nema_flange_t
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
    """The printable NEMA unit: parametric body + verbatim vendor
    interconnect fins with magnet-pocket mods. Needs the STEP on disk."""
    return with_vendor_fins(nema_plate())


def scene():
    """NEMA unit: plate (+ fins when the STEP is on disk), bridge
    posed, motor ghost face-up, foot bolts, drum ghost around it
    (NEMA-bore inner; same axial pose as the 28BYJ build)."""
    from .drum import posed_drum_parts
    from .frames import NEMA_FACE_IN_UNIT
    from .motor import motor
    from .viewer import Scene

    try:
        u = full_unit_nema()
    except FileNotFoundError:
        u = nema_plate()
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
