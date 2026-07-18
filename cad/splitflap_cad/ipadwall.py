"""iPad wall mount — side quest, not part of the split-flap.

The iPad carries a seamless magnetic charging mount with a flat-iron
bar off its back; the bar's wall end is a 50 x 75 x 5 plate. The mount
is a flat two-piece printed sandwich: a wall body with an open channel
the bar lies into, and a full-footprint lid clamped by the same four
#8 screws that hold the whole thing to the drywall. A centre lock
screw pins the bar itself. No epoxy needed, both parts print flat
(body wall-face down — the channel opens up, no bridging; lid
front-face down).

World frame: wall = YZ plane at x=0, +X out of the wall, +Z up. The
bar's wall end is DOWN; it runs up at ibar_tilt_deg off the wall
(currently 0 = parallel), iPad rigid on its top end.

View: `just cad view ipad-wall` (full viz) or `ipad-bracket`
(exploded parts). Prints: ipad-body, ipad-lid.
"""

import math

from build123d import Box, Cylinder, Pos, RectangleRounded, Rot, extrude

from .geo import slit_grommet
from .params import P
from .viewer import Scene


def _pocket_frame():
    """(xb, zb): world position of the pocket/bar bottom-end centre.

    xb keeps ibkt_back_wall of printed skin between the pocket's back
    face and the wall; zb leaves ibkt_wall of floor under the bar."""
    t = math.radians(P.ibar_tilt_deg)
    half = P.ibar_thick / 2 + P.ibkt_clear
    xb = P.ibkt_back_wall + half * math.cos(t)
    zb = P.ibkt_wall
    return xb, zb


def _bar_pose():
    """Location posing a bar (local: bottom-end centre at origin,
    running +Z) into the world at the pocket tilt."""
    xb, zb = _pocket_frame()
    return Pos(xb, 0, zb) * Rot(0, P.ibar_tilt_deg, 0)


def bar():
    """The mount's flat-iron wall plate, local frame: bottom-end centre
    at origin, length running +Z, thickness along X. Carries the lock
    screw's through-hole (drill guide for the real steel bar): centred
    widthwise, halfway up the embedded length."""
    b = Pos(0, 0, P.ibar_len / 2) * Box(P.ibar_thick, P.ibar_w, P.ibar_len)
    b -= Pos(0, 0, P.ibkt_embed / 2) * Rot(0, 90, 0) * Cylinder(
        P.ibkt_screw_d / 2, 4 * P.ibar_thick
    )
    return b


def ipad():
    """iPad slab, local frame: centred, thickness along X."""
    return Box(P.ipad_thick, P.ipad_w, P.ipad_h)


def _sandwich_frame():
    """Shared bracket numbers: (h, bw, plate_w, x_part, y_screw)."""
    half = P.ibar_thick / 2 + P.ibkt_clear
    xb, zb = _pocket_frame()
    h = zb + P.ibkt_embed  # tilt 0: embedded rise = embed
    bw = P.ibar_w + 2 * P.ibkt_clear + 2 * P.ibkt_wall
    plate_w = bw + 2 * P.ibkt_tab_w
    x_part = xb + half  # parting plane: pocket front face
    y_screw = (bw + P.ibkt_tab_w) / 2
    return h, bw, plate_w, x_part, y_screw


def _rounded_slab(h, w, thick):
    """Wall-parallel slab, rounded corners, y centred, z in [0, h],
    x in [0, thick]."""
    return (
        Pos(0, 0, h / 2)
        * Rot(0, 90, 0)
        * extrude(RectangleRounded(h, w, 8), amount=thick)
    )


def _screw_grid(h, y_screw):
    """The four wall-screw (y, z) centres."""
    return [(ys, zs) for ys in (-y_screw, y_screw) for zs in (0.25 * h, 0.75 * h)]


def bracket_body():
    """Body: one flush slab out to the bar's front face, open channel
    the bar lies into. Plain through-holes — heads recess in the lid,
    screws run on into the wall."""
    half = P.ibar_thick / 2 + P.ibkt_clear
    xb, zb = _pocket_frame()
    h, bw, plate_w, x_part, y_screw = _sandwich_frame()

    body = _rounded_slab(h, plate_w, x_part)
    # the channel: pocket cut, open at the front (lid closes it)
    cut_len = P.ibkt_embed + 20
    body -= (
        _bar_pose()
        * Pos(0, 0, cut_len / 2)
        * Box(2 * half, P.ibar_w + 2 * P.ibkt_clear, cut_len)
    )
    # four wall-screw shanks + centre lock-screw shank, all plain
    for ys, zs in _screw_grid(h, y_screw):
        body -= Pos(0, ys, zs) * Rot(0, 90, 0) * Cylinder(P.ibkt_screw_d / 2, 60)
    body -= Pos(xb, 0, zb + P.ibkt_embed / 2) * Rot(0, 90, 0) * Cylinder(
        P.ibkt_screw_d / 2, 60
    )
    return body


def bracket_lid():
    """Lid: full-footprint front plate, same rounded outline as the
    body. Recessed heads for the four wall screws + the centre lock
    screw."""
    xb, zb = _pocket_frame()
    h, bw, plate_w, x_part, y_screw = _sandwich_frame()

    lid = Pos(x_part, 0, 0) * _rounded_slab(h, plate_w, P.ibkt_lid_t)
    x_front = x_part + P.ibkt_lid_t
    holes = _screw_grid(h, y_screw)
    holes.append((0, zb + P.ibkt_embed / 2))  # centre lock screw
    for ys, zs in holes:
        lid -= Pos(0, ys, zs) * Rot(0, 90, 0) * Cylinder(P.ibkt_screw_d / 2, 60)
        lid -= Pos(
            x_front - P.ibkt_screw_head_depth / 2, ys, zs
        ) * Rot(0, 90, 0) * Cylinder(
            P.ibkt_screw_head_d / 2, P.ibkt_screw_head_depth
        )
    return lid


def scene() -> Scene:
    """Full viz: wall ghost, assembled sandwich, bar, iPad rigid on the
    bar's top end — back face ipad_gap off the bar front (the mount
    stack; swivel locked), parallel to the bar."""
    pose = _bar_pose()
    wall = Pos(-1.5, 0, 80) * Box(3.0, 420, 420)
    ipad_loc = pose * Pos(
        P.ibar_thick / 2 + P.ipad_gap + P.ipad_thick / 2, 0, P.ibar_len
    )
    return (
        Scene()
        .add(wall, "wall", color="lightgray", alpha=0.15)
        .add(bracket_body(), "body", color="orange", alpha=0.8)
        .add(bracket_lid(), "lid", color="steelblue", alpha=0.8)
        .add(bar(), "bar", color="gray", loc=pose)
        .add(ipad(), "ipad", color="black", alpha=0.5, loc=ipad_loc)
    )


def grommet():
    """Cable grommet for the 1" wall hole — see geo.slit_grommet for the
    frame and slit rationale."""
    return slit_grommet(
        P.igrom_barrel_d,
        P.igrom_barrel_l,
        P.igrom_flange_d,
        P.igrom_flange_t,
        P.igrom_cable_d,
        P.igrom_slit_w,
    )


def grommet_scene() -> Scene:
    return Scene().add(grommet(), "grommet")


def two_piece_scene() -> Scene:
    """The sandwich exploded: body + bar in the open channel, lid
    floated out front."""
    return (
        Scene()
        .add(bracket_body(), "body", color="orange", alpha=0.9)
        .add(bar(), "bar", color="gray", loc=_bar_pose())
        .add(bracket_lid(), "lid", color="steelblue", alpha=0.9, loc=Pos(25, 0, 0))
    )
