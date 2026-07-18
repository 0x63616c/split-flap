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
    """The widest bore shell.py cuts at this site, since it's the wide
    bore that runs off a tapering tab first. Note the faces they open
    onto are opposite: the insert bore opens at the mating face (local
    z=0), the head counterbore at the far one."""
    if kind == "insert":
        return loc * Pos(0, 0, P.fin_insert_depth / 2) * Cylinder(
            P.fin_insert_d / 2, P.fin_insert_depth
        )
    return loc * Pos(0, 0, P.fin_flat_t - P.fin_cbore_depth / 2) * Cylinder(
        P.fin_cbore_d / 2, P.fin_cbore_depth
    )


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


@pytest.fixture(scope="module")
def jointed():
    """A unit with the joints actually cut — the bare tabs above carry no
    holes, so face-side questions can only be asked here."""
    from golden_registry import ALL_PARTS

    return ALL_PARTS["unit-full"]()


@pytest.mark.parametrize("name,i", CASES)
def test_head_is_reachable(name, i, jointed):
    """The counterbore must open on the tab's FAR face, never the mating
    one.

    Sink the head at the mating face and it ends up sealed in the joint
    line the moment the modules are pushed together: no driver can reach
    it, so it can only ever be tightened before assembly, when it is
    clamping nothing. Cut it the wrong way round and every dimension
    still checks out — this is the only test that notices.

    Probed as a ring: the annulus between the clearance hole and the
    counterbore has to be SOLID at the mating face (the head isn't there)
    and AIR at the far face (the head is).
    """
    loc, kind = joint_locs()[i]
    if kind != "screw":
        pytest.skip("insert site — no head at either face")

    def ring(z):
        outer = loc * Pos(0, 0, z) * Cylinder(P.fin_cbore_d / 2, 0.4)
        inner = loc * Pos(0, 0, z) * Cylinder(P.screw_hole_d / 2, 0.6)
        return outer - inner

    at_joint = ring(0.2) & jointed
    assert at_joint is not None and at_joint.volume > TOL, (
        f"{name}: mating face is counterbored — the head would be buried "
        f"in the joint with nothing able to turn it"
    )
    at_far = ring(P.fin_flat_t - 0.2) & jointed
    v = 0.0 if at_far is None else at_far.volume
    assert v < TOL, f"{name}: {v:.4f} mm³ of solid where the head has to sit"


def test_screw_reaches_its_insert():
    """The M3x6 has to cross the clearance tab and still bury itself in
    the insert. Shank left over after the counterbore must be at least
    the tab it crosses, and the rest must fit the insert."""
    assert P.fin_cbore_depth + P.fin_shank_len >= P.fin_flat_t
    assert P.fin_screw_len - P.fin_shank_len <= P.fin_insert_depth
