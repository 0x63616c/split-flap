"""iPad wall mount — side quest, not part of the split-flap.

The iPad carries a seamless magnetic charging mount with a flat-iron
bar off its back; the bar's wall end is a 50 x 75 x 5 plate sitting
16 deg off the wall plane (the swivel's default). A printed bracket
screws to drywall and swallows the bar's wall end in a matching 16 deg
pocket, where it gets epoxied.

World frame: wall = YZ plane at x=0, +X out of the wall, +Z up. The
bar's wall end is UP (nearest the wall); it runs down-and-out at the
tilt angle, iPad hanging off its far end. So the bracket's pocket
opens on its BOTTOM face — the bar slides up into it, epoxy + screws
hold it.

View: `just cad view ipad-wall` (full viz) or `ipad-bracket` (part).
"""

import math

from build123d import Box, Cylinder, Polygon, Pos, Rot, extrude

from .params import P
from .viewer import Scene


def _pocket_frame():
    """(xt, zt): world position of the pocket/bar top-end centre.

    xt keeps ibkt_back_wall of printed skin between the pocket's back
    face and the wall; zt puts ibkt_embed of bar inside the bracket
    with the pocket mouth at z=0 (the bracket's bottom face).
    """
    t = math.radians(P.ibar_tilt_deg)
    half = P.ibar_thick / 2 + P.ibkt_clear
    xt = P.ibkt_back_wall + half * math.cos(t)
    zt = P.ibkt_embed * math.cos(t)
    return xt, zt


def _bar_pose():
    """Location posing a bar (local: top-end centre at origin, running
    -Z) into the world at the swivel tilt."""
    xt, zt = _pocket_frame()
    return Pos(xt, 0, zt) * Rot(0, -P.ibar_tilt_deg, 0)


def bar():
    """The mount's flat-iron wall plate, local frame: top-end centre at
    origin, length running -Z, thickness along X."""
    return Pos(0, 0, -P.ibar_len / 2) * Box(P.ibar_thick, P.ibar_w, P.ibar_len)


def ipad():
    """iPad slab, local frame: centred, thickness along X."""
    return Box(P.ipad_thick, P.ipad_w, P.ipad_h)


def bracket():
    """Printable wall bracket: screw-tab base plate + wedge boss whose
    front face parallels the bar, minus the tilted epoxy pocket and two
    counterbored drywall-screw holes."""
    t = math.radians(P.ibar_tilt_deg)
    half = P.ibar_thick / 2 + P.ibkt_clear
    xt, zt = _pocket_frame()
    h = zt + P.ibkt_wall  # body height: pocket end + skin above

    def xc(z):  # bar centreline X at height z
        return xt + (zt - z) * math.tan(t)

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
    # bottom face along the tilted axis
    cut_len = P.ibkt_embed + 20
    pocket = (
        _bar_pose()
        * Pos(0, 0, -cut_len / 2)
        * Box(2 * half, P.ibar_w + 2 * P.ibkt_clear, cut_len)
    )
    body -= pocket

    # counterbored drywall-screw holes through the tabs
    y_screw = (bw + P.ibkt_tab_w) / 2
    for ys in (-y_screw, y_screw):
        body -= Pos(P.ibkt_plate_thick / 2, ys, h / 2) * Rot(0, 90, 0) * Cylinder(
            P.ibkt_screw_d / 2, 2 * P.ibkt_plate_thick
        )
        body -= Pos(
            P.ibkt_plate_thick - P.ibkt_screw_head_depth / 2, ys, h / 2
        ) * Rot(0, 90, 0) * Cylinder(
            P.ibkt_screw_head_d / 2, P.ibkt_screw_head_depth
        )
    return body


def scene() -> Scene:
    """Full viz: wall ghost, bracket, bar in its pocket, swivel hinge
    at the bar's far end, iPad hanging off it VERTICAL (the swivel lets
    it tilt back/forth independent of the bar's 16 deg)."""
    t = math.radians(P.ibar_tilt_deg)
    xt, zt = _pocket_frame()
    wall = Pos(-1.5, 0, -60) * Box(3.0, 420, 420)
    # swivel axis: horizontal (Y) at the bar's outer end
    hx = xt + P.ibar_len * math.sin(t)
    hz = zt - P.ibar_len * math.cos(t)
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
