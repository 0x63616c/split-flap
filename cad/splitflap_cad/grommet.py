"""Wall-hole grommets — side quest, not part of the split-flap.

Plugs a 38mm hole drilled through the drywall: a face flange with a
hollow locating ring behind it that sits in the bore. Triangle ribs on
the ring OD bite the gypsum; both rib faces slope well under 45 deg so
the part prints flange-down with no overhang. Local frame: axis Z,
flange back face at z=0, ring running +Z (into the wall).

Two variants share one body:
- `grommet_usb` — USB-C-shaped stadium slot through the flange (the
  small molded plug threads straight through, no side slit needed).
- `grommet_bathroom` — blank flange, no slot: a plain hole cover.

View: `just cad view grommet-usb` / `grommet-bathroom`.
"""

from build123d import Cone, Cylinder, Pos, SlotOverall, extrude

from .params import P
from .viewer import Scene


def _grommet_body():
    """Flange + ribbed hollow barrel, no flange cutout."""
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
    return g - Pos(0, 0, ft + bl / 2) * Cylinder(r - P.ugrom_barrel_wall, bl)


def grommet_usb():
    slot = extrude(
        SlotOverall(P.ugrom_slot_w, P.ugrom_slot_h),
        amount=P.ugrom_flange_t,
    )
    return _grommet_body() - slot


def grommet_bathroom():
    return _grommet_body()


def scene() -> Scene:
    return Scene().add(grommet_usb(), "grommet-usb")


def bathroom_scene() -> Scene:
    return Scene().add(grommet_bathroom(), "grommet-bathroom")
