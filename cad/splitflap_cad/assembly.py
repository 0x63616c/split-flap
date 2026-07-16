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
    """The hall sensor PCB posed flat on the pedestal top: centre on the
    shaft X line, screw holes off-centre on the hall hole line."""
    pcb = Box(P.hall_pcb_w, P.hall_pcb_l, P.hall_pcb_t)
    for dy in (-P.hall_hole_pitch / 2, P.hall_hole_pitch / 2):
        pcb -= Pos(P.hall_x - P.hall_pcb_x, dy, 0) * Cylinder(1.1, P.hall_pcb_t * 2)
    return Pos(P.hall_pcb_x, P.hall_y, P.hall_seat + P.hall_pcb_t / 2) * pcb


def assembly_show_args():
    """Everything posed in unit coords, as kwargs for ocp_vscode.show().
    Vendor ghost included when the STEP is on disk, skipped otherwise."""
    from .drum import posed_drum_parts
    from .unit import full_unit, unit_plate
    from .vendor import REF_STEP, reference

    have_step = REF_STEP.exists()
    drum_o, drum_i = posed_drum_parts()
    plate = full_unit() if have_step else unit_plate()
    objects = [plate, posed_motor(), posed_hall_pcb(), drum_o, drum_i]
    names = ["unit_plate", "motor", "hall_pcb", "drum_outer", "drum_inner"]
    colors = ["orange", "steelblue", "green", "violet", "hotpink"]
    alphas = [1.0, 1.0, 1.0, 0.8, 0.8]
    if have_step:
        objects.append(reference())
        names.append("reference")
        colors.append("gray")
        alphas.append(0.4)
    return dict(objects=objects, names=names, colors=colors, alphas=alphas)
