"""The NEMA plate's lightening windows have to leave a plate behind.

Windows are the one cut that is pure subtraction with nothing to seat
against, so nothing pushes back when one runs somewhere it shouldn't.
The golden guard is no help — it freezes whatever it is handed, and a
window merged into its neighbour has a perfectly stable volume.

Two failure modes, both seen: a window laid against a keepout it was
meant to clear, and two windows sharing an edge so they fuse into one
opening with a knife-edge web between them (the -X strip did exactly
this — its top edge sat on the +Y band's bottom edge).
"""

import pytest
from build123d import Box, Cylinder, Pos

from splitflap_cad.params import P
from splitflap_cad.unitnema import plate_windows

TOL = 1e-6  # mm³ — containment checks, not fits

N_WINDOWS = 5  # a pair above the bridge, the -X strip, a pair below
T = P.unit_plate_thick


@pytest.fixture(scope="module")
def windows():
    return plate_windows()


def _keepouts():
    """Everything the plate has to keep, grown by plate_web. Same list
    the window bounds are derived from — stated here independently so
    the test isn't just replaying the builder's arithmetic."""
    g = P.plate_web
    y_hi = P.byj_shaft_y - P.motor_body_w / 2 + P.nema_wire_entry_bite
    out = {
        "bridge disc": Pos(P.mount_x, P.byj_shaft_y, T / 2)
        * Cylinder(P.nema_mount_r + g, T),
        "wire channel": Pos((P.mount_x - P.unit_plate_w / 2) / 2, P.nema_wire_y, T / 2)
        * Box(P.mount_x + P.unit_plate_w / 2, P.wire_chan_w + 2 * g, T),
        "feed trench": Pos(P.mount_x, (P.nema_wire_y + y_hi) / 2, T / 2)
        * Box(
            P.nema_wire_entry_w + 2 * g,
            y_hi - P.nema_wire_y + 2 * g,
            T,
        ),
        "stop rod": Pos(P.rod_x, P.rod_y, T / 2) * Cylinder(P.rod_r + g, T),
    }
    for side in (-1, +1):
        x = P.mount_x + side * P.nema_screw_x_off
        out[f"foot insert x{side:+d}"] = Pos(x, P.byj_shaft_y, T / 2) * Cylinder(
            P.byj_insert_d / 2 + g, T
        )
    return out


def test_windows_stay_separate(windows):
    """Each window is its own opening. Two that share an edge fuse into
    one solid, so the count drops — which is the whole tell, because
    every other measure of the fused pair still looks reasonable."""
    assert len(windows.solids()) == N_WINDOWS


@pytest.mark.parametrize("name", sorted(_keepouts()))
def test_window_clears(name, windows):
    """No window may eat into a keepout, web included."""
    hit = windows & _keepouts()[name]
    v = 0.0 if hit is None else hit.volume
    assert v < TOL, f"{name}: window overlaps it by {v:.4f} mm³"


def test_windows_stay_on_the_plate(windows):
    """Inboard of the back wall, inside the plate footprint."""
    x_in = -P.unit_plate_w / 2 + P.unit_wall_thick
    legal = Pos((x_in + P.unit_plate_w / 2) / 2, 0, 0) * Box(
        P.unit_plate_w / 2 - x_in, P.unit_plate_h, 4 * T
    )
    stray = windows - legal
    v = 0.0 if stray is None else stray.volume
    assert v < TOL, f"{v:.4f} mm³ of window hangs off the plate"


def test_plate_is_one_piece():
    """Windows lighten the plate; they must not cut a piece off it."""
    from golden_registry import ALL_PARTS

    assert len(ALL_PARTS["unit-nema-full"]().solids()) == 1
