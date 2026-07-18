"""The fins have to actually take an M3 joint.

These are invariants, not frozen shapes. The golden guard freezes
whatever geometry it is given: when a bore was cut into thin air, or a
boss floated detached from the tab it was meant to sit on, the goldens
recorded it and every run passed. Volume matching yesterday's volume
says nothing about whether the part works.

So assert the things that make a tab a tab: material around every bore,
a floor behind every insert, and nothing floating loose. Plus the one
invariant the screws added that the magnets never needed — the pattern
has to be antisymmetric, or two identical prints meet insert-to-insert
and there is nothing to tighten.
"""

import pytest
from build123d import Cylinder, Pos

from splitflap_cad.fins import fins, joint_locs
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

CASES = [(n, i) for i, n in enumerate(SITES)]


@pytest.fixture(scope="module")
def fin_solid():
    return fins()


def _bore(loc, kind):
    """The bore shell.py cuts at this site — the widest one, since it's
    the wide bore that runs off a tapering tab first."""
    d = P.fin_insert_d if kind == "insert" else P.fin_cbore_d
    h = P.fin_insert_depth if kind == "insert" else P.fin_cbore_depth
    return loc * Pos(0, 0, h / 2) * Cylinder(d / 2, h)


def _floor(loc):
    """The slab that has to sit behind an insert bore, so the insert
    can't be pushed straight through when it's heated in."""
    return (
        loc
        * Pos(0, 0, P.fin_insert_depth + P.fin_joint_floor / 2)
        * Cylinder(P.fin_insert_d / 2, P.fin_joint_floor)
    )


def test_six_tabs(fin_solid):
    """One per joint, none fused, none floating loose. A stray solid
    means something was placed where no tab is."""
    assert len(fin_solid.solids()) == len(joint_locs()) == 6


def test_joint_pattern_is_antisymmetric():
    """Modules are identical prints. The faces that meet when two units
    are stacked (z=0 against z=53, y=+59 against y=-59) must present
    opposite kinds, or the joint has two screws and no thread — or two
    inserts and no screw."""
    kinds = [k for _, k in joint_locs()]
    for i in range(0, 6, 3):  # per Y side: bottom, top, stack
        bottom, top, stack = kinds[i : i + 3]
        assert bottom != top, "z=0 and z=53 must not match"
    stack_pos = kinds[2]
    stack_neg = kinds[5]
    assert stack_pos != stack_neg, "y=+59 and y=-59 must not match"


@pytest.mark.parametrize("name,i", CASES)
def test_bore_lands_in_material(name, i, fin_solid):
    """Every bore must be cut entirely out of a tab. A bore hanging off
    an edge removes nothing and leaves the fastener unsupported."""
    loc, kind = joint_locs()[i]
    stray = _bore(loc, kind) - fin_solid
    v = 0.0 if stray is None else stray.volume
    assert v < TOL, f"{name}: {v:.4f} mm³ of the {kind} bore falls outside any tab"


@pytest.mark.parametrize("name,i", [c for c in CASES])
def test_insert_has_a_floor(name, i, fin_solid):
    """fin_joint_floor of solid material behind every insert bore.

    This is the one the top corner tabs failed back when these were
    magnet pockets: they ramp, so the axis is deep enough while the
    outer lip of the bore is not. Probing the full bore width catches
    it. Screw sites are through-drilled, so they're skipped."""
    loc, kind = joint_locs()[i]
    if kind != "insert":
        pytest.skip("screw site — hole goes through by design")
    missing = _floor(loc) - fin_solid
    v = 0.0 if missing is None else missing.volume
    assert v < TOL, f"{name}: {v:.4f} mm³ of the insert floor is air"


def test_screw_reaches_its_insert():
    """The M3x6 has to cross the clearance tab and still bury itself in
    the insert. Shank left over after the counterbore must be at least
    the tab it crosses, and the rest must fit the insert."""
    assert P.fin_cbore_depth + P.fin_shank_len >= P.fin_flat_t
    assert P.fin_screw_len - P.fin_shank_len <= P.fin_insert_depth
