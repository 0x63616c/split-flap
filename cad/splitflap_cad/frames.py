"""Named frames: where each part's local frame sits in UNIT coordinates.

Part modules build in their own local frame (documented in each module
docstring); every transform between a local frame and the unit frame is
named here — nowhere else. assembly.py composes the posed parts.

Naming: X_IN_UNIT maps X-local coords into unit coords.
"""

from build123d import Pos, Rot

from .params import P

# Drum frame (z=0 at the outer ring's underside, axis +Z) onto the motor
# shaft axis, at the height where the hub's double-D bore only ever sees
# the shaft's flat zone.
DRUM_IN_UNIT = Pos(P.mount_x, P.byj_shaft_y, P.drum_z0)

# Motor frame (origin = shaft axis at the flange face, can offset -Y)
# onto the shaft axis at the flange seat; the 180 about Z puts the can
# on +Y so the can centre lands on the mount/ear line.
MOTOR_IN_UNIT = Pos(P.mount_x, P.byj_shaft_y, P.byj_flange_z) * Rot(0, 0, 180)

# Hall PCB frame (board centre, top face up) flat onto its posts in the
# crescent between the motor can and the flap circle.
HALL_PCB_IN_UNIT = Pos(P.hall_pcb_x, P.hall_y, P.hall_seat + P.hall_pcb_t / 2)
