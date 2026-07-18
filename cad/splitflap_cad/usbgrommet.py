"""USB wall-hole grommet — side quest, not part of the split-flap.

Plugs the 38mm hole drilled through the drywall for the USB-C run: a
face flange with a USB-C-shaped stadium slot in the middle (the small
molded plug threads straight through — no side slit needed) and a
hollow locating ring behind it that sits in the bore. Triangle ribs on
the ring OD bite the gypsum; both rib faces slope well under 45 deg so
the part prints flange-down with no overhang. Local frame: axis Z,
flange back face at z=0, ring running +Z (into the wall).

View: `just cad view usb-grommet`. Print: usb-grommet.
"""

from build123d import Cone, Cylinder, Pos, SlotOverall, extrude

from .params import P
from .viewer import Scene


def usb_grommet():
    ft, bl = P.ugrom_flange_t, P.ugrom_barrel_l
    r = P.ugrom_barrel_d / 2
    g = Pos(0, 0, ft / 2) * Cylinder(P.ugrom_flange_d / 2, ft)
    g += Pos(0, 0, ft + bl / 2) * Cylinder(r, bl)
    # triangle ribs: cone up to the crest, cone back down — printable
    # flange-down, still bites the gypsum
    for i in range(P.ugrom_rib_n):
        zc = ft + (i + 1) * bl / (P.ugrom_rib_n + 1)
        h = P.ugrom_rib_l / 2
        crest = r + P.ugrom_rib_proud
        g += Pos(0, 0, zc - h / 2) * Cone(r, crest, h)
        g += Pos(0, 0, zc + h / 2) * Cone(crest, r, h)
    g -= Pos(0, 0, ft + bl / 2) * Cylinder(r - P.ugrom_barrel_wall, bl)
    slot = extrude(
        SlotOverall(P.ugrom_slot_w, P.ugrom_slot_h),
        amount=P.ugrom_flange_t,
    )
    return g - slot


def scene() -> Scene:
    return Scene().add(usb_grommet(), "usb-grommet")
