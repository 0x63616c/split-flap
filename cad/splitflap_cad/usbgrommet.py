"""USB wall-hole grommet — side quest, not part of the split-flap.

Plugs the 38mm hole drilled through the drywall for the USB-C run:
same flange + slit-barrel scheme as the iPad grommet (geo.slit_grommet),
sized up. The centre hole passes the bare cable; the open side slit
lets it snap in sideways past the molded connector. Print flange down.

View: `just cad view usb-grommet`. Print: usb-grommet.
"""

from .geo import slit_grommet
from .params import P
from .viewer import Scene


def usb_grommet():
    return slit_grommet(
        P.ugrom_barrel_d,
        P.ugrom_barrel_l,
        P.ugrom_flange_d,
        P.ugrom_flange_t,
        P.ugrom_cable_d,
        P.ugrom_slit_w,
    )


def scene() -> Scene:
    return Scene().add(usb_grommet(), "usb-grommet")
