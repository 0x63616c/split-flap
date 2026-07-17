"""iPad wall mount — side quest, not part of the split-flap.

The iPad carries a seamless magnetic charging mount with a flat-iron
bar off its back; the bar's wall end is a 50 x 75 x 5 plate sitting
16 deg off the wall plane (the swivel's default). A printed bracket
screws to drywall and swallows the bar's wall end in a matching 16 deg
pocket, where it gets epoxied.

World frame: wall = YZ plane at x=0, +X out of the wall, +Z up. The
bar's wall end is DOWN (nearest the wall); it runs up-and-out at the
tilt angle, swivel + iPad at its top end. So the bracket's pocket
opens on its TOP face — the bar drops in, gravity seats it, epoxy
holds it.

View: `just cad view ipad-wall` (full viz) or `ipad-bracket` (part).
"""

import math

from build123d import Box, Cylinder, Polygon, Pos, Rot, extrude

from .params import P
from .viewer import Scene


def _pocket_frame():
    """(xb, zb): world position of the pocket/bar bottom-end centre.

    xb keeps ibkt_back_wall of printed skin between the pocket's back
    face and the wall; zb leaves ibkt_wall of floor under the bar, and
    the pocket mouth lands on the bracket's top face.
    """
    t = math.radians(P.ibar_tilt_deg)
    half = P.ibar_thick / 2 + P.ibkt_clear
    xb = P.ibkt_back_wall + half * math.cos(t)
    zb = P.ibkt_wall
    return xb, zb


def _bar_pose():
    """Location posing a bar (local: bottom-end centre at origin,
    running +Z) into the world at the swivel tilt (leaning out going
    up)."""
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


def bracket():
    """Printable wall bracket: screw-tab base plate + wedge boss whose
    front face parallels the bar, minus the tilted epoxy pocket and two
    counterbored drywall-screw holes."""
    t = math.radians(P.ibar_tilt_deg)
    half = P.ibar_thick / 2 + P.ibkt_clear
    xb, zb = _pocket_frame()
    h = zb + P.ibkt_embed * math.cos(t)  # floor + embedded bar rise

    def xc(z):  # bar centreline X at height z
        return xb + (z - zb) * math.tan(t)

    # wedge boss: side profile extruded across the pocket width
    face_off = half / math.cos(t) + P.ibkt_wall  # centreline -> front face
    profile = Polygon(
        (0, 0),
        (xc(0) + face_off, 0),
        (xc(h) + face_off, h),
        (0, h),
        align=None,
    )
    bw = P.ibar_w + 2 * P.ibkt_clear + 2 * P.ibkt_wall
    boss = Pos(0, bw / 2, 0) * Rot(90, 0, 0) * extrude(profile, amount=bw)

    plate_w = bw + 2 * P.ibkt_tab_w
    plate = Pos(P.ibkt_plate_thick / 2, 0, h / 2) * Box(
        P.ibkt_plate_thick, plate_w, h
    )
    body = boss + plate

    # epoxy pocket: bar cross-section + clearance, punched out past the
    # top face along the tilted axis
    cut_len = P.ibkt_embed + 20
    pocket = (
        _bar_pose()
        * Pos(0, 0, cut_len / 2)
        * Box(2 * half, P.ibar_w + 2 * P.ibkt_clear, cut_len)
    )
    body -= pocket

    # centre lock screw: normal to the bar (so at the 16 deg tilt),
    # through front wall + bar + back skin — clamps the bar mechanically,
    # epoxy optional. Head recessed into the wedge's front face, which
    # parallels the bar, so the head seats flat.
    mid = _bar_pose() * Pos(0, 0, P.ibkt_embed / 2)
    body -= mid * Rot(0, 90, 0) * Cylinder(P.ibkt_screw_d / 2, 80)
    d_face = half + P.ibkt_wall * math.cos(t)  # bar centreline -> front face
    cb_len = P.ibkt_screw_head_depth + 10  # recess + overshoot clear of the face
    body -= (
        mid
        * Pos(d_face - P.ibkt_screw_head_depth + cb_len / 2, 0, 0)
        * Rot(0, 90, 0)
        * Cylinder(P.ibkt_screw_head_d / 2, cb_len)
    )

    # counterbored drywall-screw holes through the tabs: 2 per tab
    # (#8 x 1"/1.25" — Ø4.5 clears the 4.17 shank)
    y_screw = (bw + P.ibkt_tab_w) / 2
    for ys in (-y_screw, y_screw):
        for zs in (0.25 * h, 0.75 * h):
            body -= Pos(P.ibkt_plate_thick / 2, ys, zs) * Rot(0, 90, 0) * Cylinder(
                P.ibkt_screw_d / 2, 2 * P.ibkt_plate_thick
            )
            body -= Pos(
                P.ibkt_plate_thick - P.ibkt_screw_head_depth / 2, ys, zs
            ) * Rot(0, 90, 0) * Cylinder(
                P.ibkt_screw_head_d / 2, P.ibkt_screw_head_depth
            )
    return body


def scene() -> Scene:
    """Full viz: wall ghost, bracket, bar in its pocket, swivel hinge
    at the bar's far end, iPad hanging off it VERTICAL (the swivel lets
    it tilt back/forth independent of the bar's 16 deg)."""
    t = math.radians(P.ibar_tilt_deg)
    xb, zb = _pocket_frame()
    wall = Pos(-1.5, 0, 80) * Box(3.0, 420, 420)
    # swivel axis: horizontal (Y) at the bar's outer (top) end
    hx = xb + P.ibar_len * math.sin(t)
    hz = zb + P.ibar_len * math.cos(t)
    swivel_r = 6.0
    swivel = Pos(hx, 0, hz) * Rot(90, 0, 0) * Cylinder(swivel_r, 30)
    # iPad neutral: vertical, back face kissing the swivel body
    ipad_loc = Pos(hx + swivel_r + P.ipad_thick / 2, 0, hz)
    return (
        Scene()
        .add(wall, "wall", color="lightgray", alpha=0.15)
        .add(bracket(), "bracket", color="orange", alpha=0.8)
        .add(bar(), "bar", color="gray", loc=_bar_pose())
        .add(swivel, "swivel", color="dimgray")
        .add(ipad(), "ipad", color="black", alpha=0.5, loc=ipad_loc)
    )


def bracket_scene() -> Scene:
    return Scene().add(bracket(), "bracket")
