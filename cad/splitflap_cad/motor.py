"""NEMA 14 pancake stepper — reference model of the ordered vendor part
(YEJMKJ 35x21mm 7Ncm; dims from the listing, flat/boss marked VERIFY in
params.py until measured).

Not printed; exists so mounts can be designed and fit-checked against it.
Origin is the shaft axis at the mounting face, shaft pointing +Z.

View it: `just cad motor-nema` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Box, Cylinder, Pos, Rectangle, extrude, fillet

from .params import P


def motor():
    """Return the stepper Part: body, pilot boss, D-flat shaft, M3 holes."""
    # Body hangs below the mounting face (z=0), corners rounded like the
    # real can. Radius is eyeballed off the drawing, not a datasheet dim.
    body = extrude(Rectangle(P.motor_body_w, P.motor_body_w), amount=-P.motor_body_len)
    body = fillet(body.edges().filter_by(lambda e: e.length == P.motor_body_len), radius=4.5)

    # Pilot boss + shaft stick up past the mounting face.
    boss = Pos(0, 0, P.motor_boss_len / 2) * Cylinder(P.motor_boss_d / 2, P.motor_boss_len)
    shaft = Pos(0, 0, P.motor_shaft_len / 2) * Cylinder(P.motor_shaft_d / 2, P.motor_shaft_len)

    # D-flat: from the tip down motor_flat_len, milled so motor_flat_across
    # remains. Cut box is oversized except the flat plane itself.
    flat_z = P.motor_shaft_len - P.motor_flat_len / 2
    cut_x = P.motor_flat_across - P.motor_shaft_d / 2  # flat plane offset from axis
    flat_cut = Pos(cut_x + P.motor_shaft_d / 2, 0, flat_z) * Box(
        P.motor_shaft_d, P.motor_shaft_d * 2, P.motor_flat_len
    )
    shaft -= flat_cut

    # 4-M3 tapped holes in the mounting face, square pattern.
    half = P.motor_hole_pitch / 2
    for x in (-half, half):
        for y in (-half, half):
            body -= Pos(x, y, -P.motor_screw_depth / 2) * Cylinder(
                P.motor_screw_d / 2, P.motor_screw_depth
            )

    return body + boss + shaft


def scene():
    from .viewer import Scene

    return Scene().add(motor(), "motor_nema14")
