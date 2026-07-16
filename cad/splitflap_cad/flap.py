"""The flap card — a flat 1mm print, dimensions measured off the vendor
Flap_blank.step. One outline, no separate pin parts: the pivot "pins"
are flat side tabs near the bottom (pivot) edge, and the top section
widens to the same overall span.

Local frame: x centred on the card, y=0 at the pivot edge, z=0 at the
card's back face.

View it: `just cad flap` (see cad/splitflap_cad/catalog.py).
"""

from build123d import Polygon, extrude

from .params import P


def flap():
    """Return the flap Part: one extruded outline, flap_thick thick."""
    xb = P.flap_w / 2               # body half-width
    xp = P.flap_w_over_pins / 2     # half-width over the pin tabs / wings
    y0 = P.flap_pin_y0
    y1 = P.flap_pin_y0 + P.flap_pin_h
    yw = P.flap_wide_y0
    outline = Polygon(
        (-xb, 0),
        (xb, 0),
        (xb, y0),
        (xp, y0),
        (xp, y1),
        (xb, y1),
        (xb, yw),
        (xp, yw),
        (xp, P.flap_h),
        (-xp, P.flap_h),
        (-xp, yw),
        (-xb, yw),
        (-xb, y1),
        (-xp, y1),
        (-xp, y0),
        (-xb, y0),
        align=None,
    )
    return extrude(outline, amount=P.flap_thick)
