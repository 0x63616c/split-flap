"""The full-unit assembly: our plate + motor + hall PCB + drum, with the
vendor unit as a semi-transparent ghost overlay for comparison.

Composes parts from the other modules; owns the posed_* helpers that place
bought parts (motor, hall PCB) in unit coordinates. No geometry of its own
beyond the hall PCB mock.

View it: `just cad assembly` (or `just cad list` for the full menu).
"""

from build123d import Box, Cylinder, Pos, Rot

from .params import P
from .stepper28byj import stepper28byj


def posed_motor():
    """The 28BYJ posed in the harness: shaft at the mount axis, flange
    seated on the tower tops."""
    # Positioned by SHAFT axis; the 180 about it puts the can on +Y so the
    # can centre lands on the mount/ear line.
    return Pos(P.mount_x, P.byj_shaft_y, P.byj_flange_z) * Rot(0, 0, 180) * stepper28byj()


def posed_hall_pcb():
    """The hall sensor PCB posed flat on its posts, in the crescent
    between the motor can and the flap circle. Screw holes on the hall
    hole line (-X edge); the hall element hangs off that same edge on
    bent legs, its centre on the magnet sweep circle, face up."""
    pcb = Box(P.hall_pcb_w, P.hall_pcb_l, P.hall_pcb_t)
    for dy in (-P.hall_hole_pitch / 2, P.hall_hole_pitch / 2):
        pcb -= Pos(P.hall_x - P.hall_pcb_x, dy, 0) * Cylinder(
            P.hall_hole_d / 2, P.hall_pcb_t * 2
        )
    # element body past the -X edge, top face level with the PCB top
    elem_dx = P.hall_elem_x - P.hall_pcb_x
    elem_dy = P.hall_elem_y - P.hall_y
    elem = Pos(elem_dx, elem_dy, P.hall_pcb_t / 2 - P.hall_elem_t / 2) * Box(
        P.hall_elem_l, P.hall_elem_w, P.hall_elem_t
    )
    # legs: thin ribbon bridging the -X edge to the element body
    edge = -P.hall_pcb_w / 2
    span = edge - (elem_dx + P.hall_elem_l / 2)
    legs = Pos(edge - span / 2, elem_dy, P.hall_pcb_t / 2 - 0.2) * Box(
        span, P.hall_elem_w, 0.4
    )
    return Pos(P.hall_pcb_x, P.hall_y, P.hall_seat + P.hall_pcb_t / 2) * (
        pcb + elem + legs
    )


def scene():
    """Everything posed in unit coords. Vendor ghost included when the
    STEP is on disk, skipped otherwise."""
    from .drum import posed_drum_parts
    from .unit import full_unit, unit_plate
    from .vendor import REF_STEP, reference
    from .viewer import Scene

    have_step = REF_STEP.exists()
    drum_o, drum_i = posed_drum_parts()
    s = (
        Scene()
        .add(full_unit() if have_step else unit_plate(), "unit_plate", "orange")
        .add(posed_motor(), "motor", "steelblue")
        .add(posed_hall_pcb(), "hall_pcb", "green")
        .add(drum_o, "drum_outer", "violet", alpha=0.8)
        .add(drum_i, "drum_inner", "hotpink", alpha=0.8)
    )
    if have_step:
        s.add(reference(), "reference", "gray", alpha=0.4)
    return s
