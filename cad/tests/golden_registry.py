"""Registry of parts under golden-geometry guard (see test_geometry.py).

Two tiers:
- BREP + fingerprint: fully-ours parts — exact geometry committed to
  golden/, XOR-diffable.
- fingerprint only: parts embedding vendor geometry (full_unit carries
  verbatim STEP fins; the STEP is gitignored, license unclear, so its
  shape must not be committed) — volume/area/bbox/COM guard only.

Builders are lazy; importing this module builds nothing.
"""

GOLDEN_DIR_NAME = "golden"
FINGERPRINTS_NAME = "fingerprints.json"

# relative tolerance for volume/area, absolute mm for bbox/COM coords
REL_TOL = 1e-6
ABS_TOL = 1e-4
# residual mm^3 allowed in each direction of the XOR test
XOR_TOL = 1e-3


def _flap():
    from splitflap_cad.flap import flap

    return flap()


def _holder():
    from splitflap_cad.holder import holder

    return holder()


def _drum_outer():
    from splitflap_cad.drum import drum_outer

    return drum_outer()


def _drum_inner():
    from splitflap_cad.drum import drum_inner

    return drum_inner()


def _motor_byj():
    from splitflap_cad.stepper28byj import stepper28byj

    return stepper28byj()


def _hall_pcb():
    from splitflap_cad.assembly import posed_hall_pcb

    return posed_hall_pcb()


def _unit_plate():
    from splitflap_cad.unit import unit_plate

    return unit_plate()


def _full_unit():
    from splitflap_cad.unit import full_unit

    return full_unit()


# name -> builder. All in their own local frames.
BREP_PARTS = {
    "flap": _flap,
    "holder": _holder,
    "drum-outer": _drum_outer,
    "drum-inner": _drum_inner,
    "motor-byj": _motor_byj,
    "hall-pcb": _hall_pcb,
    "unit-plate": _unit_plate,
}

FINGERPRINT_ONLY = {
    "unit-full": _full_unit,  # vendor fins embedded — no BREP committed
}

ALL_PARTS = {**BREP_PARTS, **FINGERPRINT_ONLY}


def fingerprint(part) -> dict:
    """Geometry invariants: cheap to compare, catch ~all accidents."""
    bb = part.bounding_box()
    com = part.center()
    return {
        "volume": part.volume,
        "area": part.area,
        "bbox_min": [bb.min.X, bb.min.Y, bb.min.Z],
        "bbox_max": [bb.max.X, bb.max.Y, bb.max.Z],
        "com": [com.X, com.Y, com.Z],
    }
