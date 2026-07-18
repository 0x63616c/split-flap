"""The full-unit assembly: the plate + motor + hall PCB + drum.

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
    from .frames import MOTOR_IN_UNIT

    return MOTOR_IN_UNIT * stepper28byj()


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
    from .frames import HALL_PCB_IN_UNIT

    return HALL_PCB_IN_UNIT * (pcb + elem + legs)


def scene():
    """Everything posed in unit coords."""
    from .drum import posed_drum_parts
    from .unit import full_unit
    from .viewer import Scene

    drum_o, drum_i = posed_drum_parts()
    return (
        Scene()
        .add(full_unit(), "unit_plate", "orange")
        .add(posed_motor(), "motor", "steelblue")
        .add(posed_hall_pcb(), "hall_pcb", "green")
        .add(drum_o, "drum_outer", "violet", alpha=0.8)
        .add(drum_i, "drum_inner", "hotpink", alpha=0.8)
    )
