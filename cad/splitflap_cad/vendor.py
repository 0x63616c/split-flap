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


def scene():
    from .viewer import Scene

    return Scene().add(reference(), "vendor_unit", alpha=0.6)


# (the motor screw towers used to be cropped out of the STEP here too;
# they're modeled parametrically now — unit.motor_towers)
