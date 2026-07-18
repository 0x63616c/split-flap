"""Shared geometry idioms for the part builders.

Everything here is frame-agnostic build123d plumbing: no dimensions, no
part knowledge beyond the slot-0 marker style (which is deliberately
one style everywhere).
"""

from build123d import Box, Cylinder, Polygon, Pos, Rot, extrude

from .params import P


def polar_locs(n: int, start: float = 0.0) -> list:
    """The n rotations of a full polar array about +Z: start, start+360/n, …"""
    return [Rot(0, 0, start + i * 360 / n) for i in range(n)]


def polar(shape, n: int, start: float = 0.0) -> list:
    """`shape` repeated n times around +Z. Subtract or add the copies:
    `for c in polar(cutter, n): body -= c`."""
    return [loc * shape for loc in polar_locs(n, start)]


def radial_plate(profile, thickness: float):
    """Stand a radial-section profile up as a plate.

    `profile` is sketched as radial(x) × axial(y); the result is that
    section in the XZ plane (x radial, y up became +Z), `thickness`
    thick, CENTRED across Y. Symmetric extrusion — the profile's winding
    direction cannot flip which side the material lands on, so no
    per-site recentring shifts.
    """
    return Rot(90, 0, 0) * extrude(profile, amount=thickness / 2, both=True)


def slot0_marker(apex_r: float, z_face: float, cut: str = "down", point: str = "out"):
    """The first-slot indicator: a debossed triangle on the +X (slot 0)
    line, one style for every part. Returns the solid to subtract.

    apex_r: radius of the triangle's point. point='out' aims the apex
    radially outward (base drum_mark_len further in), 'in' the reverse.
    cut='down' cuts drum_mark_depth into a top face at z_face, 'up' into
    a bottom face.
    """
    s = 1 if point == "out" else -1
    base_r = apex_r - s * P.drum_mark_len
    tri = Polygon(
        (apex_r, 0),
        (base_r, P.drum_mark_w / 2),
        (base_r, -P.drum_mark_w / 2),
        align=None,
    )
    z0 = z_face - P.drum_mark_depth if cut == "down" else z_face
    return Pos(0, 0, z0) * extrude(tri, amount=P.drum_mark_depth)


def slit_grommet(
    barrel_d: float,
    barrel_l: float,
    flange_d: float,
    flange_t: float,
    cable_d: float,
    slit_w: float,
):
    """Wall-hole cable grommet: flange + barrel, centre cable hole, open
    side slit so a molded connector never has to thread through — the
    cable snaps in sideways. Local frame: axis Z, flange back face at
    z=0, barrel running +Z (into the wall). Print flange down."""
    g = Pos(0, 0, flange_t / 2) * Cylinder(flange_d / 2, flange_t)
    g += Pos(0, 0, flange_t + barrel_l / 2) * Cylinder(barrel_d / 2, barrel_l)
    total = flange_t + barrel_l
    g -= Pos(0, 0, total / 2) * Cylinder(cable_d / 2, 2 * total)
    g -= Pos(flange_d / 2, 0, total / 2) * Box(flange_d, slit_w, 2 * total)
    return g
