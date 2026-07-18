"""The fins have to actually hold magnets.

These are invariants, not frozen shapes. The golden guard freezes
whatever geometry it is given: when a magnet pocket was cut into thin
air, or a boss floated detached from the tab it was meant to sit on, the
goldens recorded it and every run passed. Volume matching yesterday's
volume says nothing about whether the part works.

So assert the things that make a tab a tab: material behind every
pocket, a floor to hold the magnet in, and nothing floating loose.
"""

import pytest
from build123d import Cylinder, Pos

from splitflap_cad.fins import fins, magnet_locs
from splitflap_cad.params import P

TOL = 1e-6  # mm³ — these are exact containment checks, not fits

SITES = [
    "bottom-corner(+Y)",
    "top-corner(+Y)",
    "stack(+Y)",
    "bottom-corner(-Y)",
    "top-corner(-Y)",
    "stack(-Y)",
]


@pytest.fixture(scope="module")
def fin_solid():
    return fins()


def _pocket(loc):
    """The bore a magnet drops into, as shell.py cuts it."""
    return (
        loc
        * Pos(0, 0, P.fin_pocket_h / 2)
        * Cylinder((P.drum_magnet_d + P.drum_magnet_clear) / 2, P.fin_pocket_h)
    )


def _floor(loc):
    """The slab that has to sit behind the magnet so it can't push
    through — the poke hole pierces it, but the rest must be solid."""
    return (
        loc
        * Pos(0, 0, P.fin_pocket_h + P.fin_magnet_floor / 2)
        * Cylinder((P.drum_magnet_d + P.drum_magnet_clear) / 2, P.fin_magnet_floor)
    )


def test_six_tabs(fin_solid):
    """One per magnet, none fused, none floating loose. A stray solid
    means something was placed where no tab is."""
    assert len(fin_solid.solids()) == len(magnet_locs()) == 6


@pytest.mark.parametrize("name,i", [(n, i) for i, n in enumerate(SITES)])
def test_pocket_lands_in_material(name, i, fin_solid):
    """Every pocket must be cut entirely out of a tab. A pocket hanging
    off an edge removes nothing and leaves the magnet unsupported."""
    stray = _pocket(magnet_locs()[i]) - fin_solid
    v = 0.0 if stray is None else stray.volume
    assert v < TOL, f"{name}: {v:.4f} mm³ of pocket falls outside any tab"


@pytest.mark.parametrize("name,i", [(n, i) for i, n in enumerate(SITES)])
def test_magnet_has_a_floor(name, i, fin_solid):
    """fin_magnet_floor of solid material behind every pocket.

    This is the one the top corner tabs failed: they ramp, so the axis
    is deep enough while the outer lip of the bore is not. Probing the
    full bore width is what catches it."""
    missing = _floor(magnet_locs()[i]) - fin_solid
    v = 0.0 if missing is None else missing.volume
    assert v < TOL, f"{name}: {v:.4f} mm³ of the magnet floor is air"
