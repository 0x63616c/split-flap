"""28BYJ-48 stepper — reference model of the vendor part, standard dims.

Not printed; exists so the mount can be designed and fit-checked against it.
Origin is the SHAFT axis at the mounting-flange face, shaft pointing +Z.
The can centre sits byj_shaft_offset away in -Y (matches the ghost unit,
whose drum-side clearance arc is centred 8mm off the screw line).

Wire housing is approximate — good for clearance checks, not exact.

View it: `just cad motor-byj` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Box, Cylinder, Pos, Rectangle, extrude, fillet

from .params import P


def stepper28byj():
    """Return the 28BYJ-48 Part: can, ear flange, boss, D-flat shaft, wire box."""
    can_c = Pos(0, -P.byj_shaft_offset)  # can centre, shaft frame

    # Can hangs below the flange face (z=0).
    can = can_c * Pos(0, 0, -P.byj_can_h / 2) * Cylinder(P.byj_can_d / 2, P.byj_can_h)

    # Ear flange: bar across the can + rounded ear ends, holes at the pitch.
    # THIS motor (measured): ear line runs through the CAN centre; the
    # shaft is the offset thing. (Some datasheets show ears on the shaft
    # line — ours aren't.)
    half_pitch = P.byj_ear_pitch / 2
    # Bar extends half an ear-width past each hole so the rounded ends
    # wrap the holes instead of the holes breaking out.
    bar = Rectangle(P.byj_ear_pitch + P.byj_ear_w, P.byj_ear_w)
    ears = can_c * extrude(bar, amount=-P.byj_flange_t)
    ears = fillet(ears.edges().filter_by(lambda e: abs(e.length - P.byj_flange_t) < 1e-6), radius=P.byj_ear_w / 2 - 0.01)
    for x in (-half_pitch, half_pitch):
        ears -= can_c * Pos(x, 0, -P.byj_flange_t / 2) * Cylinder(P.byj_ear_hole_d / 2, P.byj_flange_t * 2)

    # Pilot boss + shaft on the origin axis.
    boss = Pos(0, 0, P.byj_boss_h / 2) * Cylinder(P.byj_boss_d / 2, P.byj_boss_h)
    shaft = Pos(0, 0, P.byj_shaft_len / 2) * Cylinder(P.byj_shaft_d / 2, P.byj_shaft_len)

    # Double-D flat: byj_flat_across remains across two parallel flats,
    # cut over the top byj_flat_len of the shaft.
    flat_z = P.byj_shaft_len - P.byj_flat_len / 2
    gap = P.byj_flat_across / 2
    for side in (1, -1):
        cut_c = side * (gap + P.byj_shaft_d / 2)
        shaft -= Pos(0, cut_c, flat_z) * Box(P.byj_shaft_d * 2, P.byj_shaft_d, P.byj_flat_len)

    # Wire housing: rough box on the can side OPPOSITE the shaft offset.
    wire_y = -P.byj_shaft_offset - P.byj_can_d / 2 - P.byj_wirebox_d / 2
    wirebox = Pos(0, wire_y, -P.byj_wirebox_h / 2) * Box(
        P.byj_wirebox_w, P.byj_wirebox_d, P.byj_wirebox_h
    )

    return can + ears + boss + shaft + wirebox
