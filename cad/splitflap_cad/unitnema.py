"""The NEMA unit side plate + bridge — pancake motor variant.

The pancake NEMA 14 sits face-UP in a shallow pocket in the base plate,
body inside the drum barrel's interior, shaft coaxial with the 28BYJ
variant's (mount_x, byj_shaft_y). Its tapped mount holes open upward,
so a printed BRIDGE drops over the face: a deck with the pilot-boss
bore and 4 M3 clearance holes (the motor's own screws clamp deck to
face), legs down the body's ±X flats, and feet on the plate held by M3
screws from below the plate into heat-set inserts. The hall board
mounts on M2 bosses on the deck (the 28BYJ hall post spot is buried
under the motor body); the drum magnet scheme is unchanged.

Plate lightening windows: none yet — layout first, windows once the
NEMA furniture settles.

Envelope notes (plate top z=3): body top/face z 23, deck top z 25.5 —
under the drum guide rails (sweep r≥23.15 from z≈26.3) and the
inner-web fins (bottom edge z 28.3 at the rim). Feet stay under z 4.2
(outer ring underside sweeps z≈4.7 from r 26.5). Everything inside the
barrel wall, r < 26.5 about the shaft.

Bridge local frame: shaft axis at the motor MOUNTING FACE plane, +Z up
(same convention as motor.py); frames.py poses it at nema_face_z.

View it: `just cad unit-nema` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Box, Cylinder, Pos, Rectangle, chamfer, extrude, fillet

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
    """Return the NEMA unit side plate Part: shell + pocket + foot inserts."""
    plate = base_plate()

    # Body pocket: square recess in the plate top locating the motor
    # body (XY register + anti-rotation); corners rounded to the can's
    # own corner radius so the body drops in without filing.
    pocket_w = P.motor_body_w + 2 * P.nema_pocket_clear
    fp = Rectangle(pocket_w, pocket_w)
    fp = fillet(fp.vertices(), 4.5 + P.nema_pocket_clear)
    plate -= Pos(P.mount_x, P.byj_shaft_y, P.unit_plate_thick) * extrude(
        fp, amount=-P.nema_pocket_depth
    )

    # Bridge foot inserts: M3x3 heat-set straight into the plate from
    # the top, flush — the screws come down through the feet, so the
    # module's outer (bottom) face stays untouched.
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
    """Return the bridge Part (local frame: shaft axis at the motor face,
    +Z up): deck + legs + feet + hall bosses."""
    # Deck: disc on the motor face — bore clears the pilot boss, 4 M3
    # clearance holes on the motor's square hole pattern.
    deck = Pos(0, 0, P.nema_bridge_t / 2) * Cylinder(P.nema_bridge_r, P.nema_bridge_t)
    deck -= Cylinder(P.pilot_hole_d / 2, P.nema_bridge_t * 3)
    half = P.motor_hole_pitch / 2
    for x in (-half, half):
        for y in (-half, half):
            deck -= Pos(x, y, 0) * Cylinder(P.screw_hole_d / 2, P.nema_bridge_t * 3)

    # Legs: down the body's ±X flats to the plate top (the face sits
    # nema_face_z - plate_thick above it), hugging the body with the
    # pocket clearance. Each leg bottoms out in a foot block the screw
    # passes through; the block stays compact so its corners keep clear
    # of the barrel wall sweep (r 26.5 about the shaft from z 6.3 up) —
    # plan-chamfered outer corners buy the last bit of gap.
    leg_in = P.motor_body_w / 2 + P.nema_pocket_clear
    drop = P.nema_face_z - P.unit_plate_thick  # face plane -> plate top
    legs_feet = None
    for side in (-1, +1):
        leg = Pos(
            side * (leg_in + P.nema_leg_t / 2), 0, -drop / 2
        ) * Box(P.nema_leg_t, P.nema_leg_w, drop)
        # foot block: leg thickness + the extra run, one solid
        foot_span = P.nema_leg_t + P.nema_foot_len
        fp = Rectangle(foot_span, P.nema_leg_w)
        fp = chamfer(  # the two outer corners only
            [v for v in fp.vertices() if v.X * side > 0], P.nema_foot_corner
        )
        foot = Pos(side * (leg_in + foot_span / 2), 0, -drop) * extrude(
            fp, amount=P.nema_foot_h
        )
        # M3 clearance through-hole — screw drops in from above into the
        # flush insert in the plate; axis sits as far outboard as the
        # button head seats, so the hex key clears the leg face
        foot -= Pos(
            side * P.nema_screw_x_off, 0, -drop + P.nema_foot_h / 2
        ) * Cylinder(P.screw_hole_d / 2, P.nema_foot_h * 2)
        lf = leg + foot
        legs_feet = lf if legs_feet is None else legs_feet + lf

    # Hall bosses: the board points -Y from the shaft, element centre on
    # the magnet sweep circle; its two M2 holes land on the deck.
    edge_y = P.nema_hall_elem_y + P.hall_elem_overhang  # board's -Y edge
    hole_y = edge_y + P.hall_hole_inset
    hole_y_local = hole_y - P.byj_shaft_y
    bosses = None
    for dx in (-P.hall_hole_pitch / 2, P.hall_hole_pitch / 2):
        b = Pos(dx, hole_y_local, P.nema_bridge_t + P.nema_hall_boss_h / 2) * Cylinder(
            5.0 / 2, P.nema_hall_boss_h
        )
        b -= Pos(
            dx,
            hole_y_local,
            P.nema_bridge_t + P.nema_hall_boss_h - P.nema_hall_pilot_depth / 2,
        ) * Cylinder(P.hall_pilot_d / 2, P.nema_hall_pilot_depth)
        bosses = b if bosses is None else bosses + b

    return deck + legs_feet + bosses


def full_unit_nema():
    """The printable NEMA unit: parametric body + verbatim vendor
    interconnect fins with magnet-pocket mods. Needs the STEP on disk."""
    return with_vendor_fins(nema_plate())


def scene():
    """NEMA unit: plate (+ fins when the STEP is on disk), bridge posed,
    motor ghost face-up in the pocket, drum ghost around it.

    Drum pose is the 28BYJ-derived one for now — right axial spot in the
    box; the NEMA drum (deeper bore for the 20.5 shaft) is future work."""
    from .drum import posed_drum_parts
    from .frames import NEMA_FACE_IN_UNIT
    from .motor import motor
    from .viewer import Scene

    try:
        u = full_unit_nema()
    except FileNotFoundError:
        u = nema_plate()
    drum_o, drum_i = posed_drum_parts()
    return (
        Scene()
        .add(u, "unit_nema", "orange")
        .add(NEMA_FACE_IN_UNIT * nema_bridge(), "bridge", "violet")
        .add(NEMA_FACE_IN_UNIT * motor(), "motor", "steelblue", alpha=0.5)
        .add(drum_o, "drum_outer", "gray", alpha=0.3)
        .add(drum_i, "drum_inner", "hotpink", alpha=0.3)
    )


def bridge_scene():
    from .viewer import Scene

    return Scene().add(nema_bridge(), "bridge_nema")


def plate_scene():
    from .viewer import Scene

    return Scene().add(nema_plate(), "plate_nema")
