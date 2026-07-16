"""Verbatim geometry lifted from the vendor STEP (Printables #805853).

The STEP lives in cad/reference/ — gitignored, license unclear; download it
yourself. Everything here is boolean-extracted from the aligned solid and
deliberately NON-parametric: exact vendor shapes, kept because they solve
problems we don't want to re-engineer (fin gussets, tower nut slots, drum
corner relief). If the surrounding parametric geometry moves, re-measure.
"""

from pathlib import Path

from build123d import Box, Pos, import_step

from .params import P

REF_STEP = Path(__file__).parent.parent / "reference" / "Unit.stp"


def reference():
    """The vendor unit Solid, aligned onto our coordinate frame.

    The STEP is corner-origin (plate spans 0..95 in X, 0..118 in Y); ours
    is centred at the origin. Shift so the plates coincide.
    """
    return Pos(-P.unit_plate_w / 2, -P.unit_plate_h / 2, 0) * import_step(str(REF_STEP))


def vendor_fins():
    """Interconnect fins: everything outboard of the back wall's outer
    face (x < -wall face) is fin geometry."""
    wall_face = -P.unit_plate_w / 2
    region = Pos(wall_face - 10, 0, 26.5) * Box(20, P.unit_plate_h + 10, 53)
    return reference() & region


def vendor_plate_cutouts():
    """The vendor plate's lightening cutouts, as solids to subtract:
    plate-footprint slab minus the vendor plate = the holes."""
    slab = Pos(0, 0, P.unit_plate_thick / 2) * Box(
        P.unit_plate_w, P.unit_plate_h, P.unit_plate_thick
    )
    return slab - (reference() & slab)


def vendor_towers():
    """The motor screw towers with their bridges, trapped-nut slots and
    drum-corner relief — one region box per tower complex."""
    towers = None
    # z clipped flat at the flange seat — the vendor has 0.2mm nubs above
    # it that would dig into our motor's ears.
    for x_lo, x_hi in ((-13.0, -0.8), (23.8, 36.0)):
        region = Pos(
            (x_lo + x_hi) / 2, P.tower_zone_y, (2.95 + P.byj_flange_seat) / 2
        ) * Box(x_hi - x_lo, 2 * P.tower_zone_half_y, P.byj_flange_seat - 2.95)
        t = reference() & region
        towers = t if towers is None else towers + t
    return towers
