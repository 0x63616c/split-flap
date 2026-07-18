"""USB wall-hole grommet — side quest, not part of the split-flap.

Plugs the 38mm hole drilled through the drywall for the USB-C run: a
face flange with a USB-C-shaped stadium slot in the middle (the small
molded plug threads straight through — no side slit needed) and a
hollow locating ring behind it that sits in the bore. Local frame:
axis Z, flange back face at z=0, ring running +Z (into the wall).
Print flange down.

View: `just cad view usb-grommet`. Print: usb-grommet.
"""

from build123d import Cylinder, Pos, SlotOverall, extrude

from .params import P
from .viewer import Scene


def usb_grommet():
    g = Pos(0, 0, P.ugrom_flange_t / 2) * Cylinder(
        P.ugrom_flange_d / 2, P.ugrom_flange_t
    )
    ring = Cylinder(P.ugrom_barrel_d / 2, P.ugrom_barrel_l) - Cylinder(
        P.ugrom_barrel_d / 2 - P.ugrom_barrel_wall, P.ugrom_barrel_l
    )
    g += Pos(0, 0, P.ugrom_flange_t + P.ugrom_barrel_l / 2) * ring
    slot = extrude(
        SlotOverall(P.ugrom_slot_w, P.ugrom_slot_h),
        amount=P.ugrom_flange_t,
    )
    return g - slot


def scene() -> Scene:
    return Scene().add(usb_grommet(), "usb-grommet")
