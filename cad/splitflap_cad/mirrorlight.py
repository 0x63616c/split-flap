"""Arched-mirror LED backlight — side quest, not part of the split-flap.

A 34 x 76in tombstone mirror hangs flat on the wall. Printed spacers glue to
the back of its frame and hold it off the wall by ml_standoff; a Hue Solo lightstrip lies in a groove on their OUTER
face, firing radially OUTWARD, so light leaves through the wall/mirror gap
and washes the wall — a halo, no fixture in sight. The spacers sit ml_inset
in from the mirror edge, hidden behind the glass.

The strip runs the WHOLE way round — bottom, both corners, both sides, the
arch — because the 16.4ft roll is longer than the three-sided path and it
cannot be usefully cut (Philips' cut marks are 330mm apart). Closing the
loop leaves ~8.8in, which tucks behind the glass at the feed.

Why the groove faces out and the strip's width runs along Z: a strip only
bends about its width axis. Following the contour curves the strip in the
mirror plane, so the width MUST lie along the wall normal — which is exactly
the pose that aims the emitting face radially outward. The bottom corners
get a ml_corner_r turn for the same reason: the strip cannot go square.

Arch geometry is derived, not measured: params holds width / side height /
overall height, and P.ml_arch_r + P.ml_arch_cy fall out of them.

World frame: wall = XY plane at z=0, +Z out of the wall, +Y up, X across,
origin on the mirror's bottom centreline.

Parts. Local frame for all three: MIRROR face at z=0 (the print bed — it is
the bonding face and wants a bed-quality finish), wall face at z=standoff,
outer face the x=0 plane facing +X, body to -X, length along Y.
- `spacer_straight` — sides and bottom.
- `spacer_arch` — swept about the inset arch radius; all identical.
- `spacer_corner` — the quarter turn at each bottom corner.
The swept pair keep a curved OUTER face (the strip needs it) but their inner
face is FLAT — the chord — so they print as stable blocks.

No fasteners anywhere: the z=0 face glues to the back of the mirror frame and
the mirror rests on the spacers against the wall. That is why z=0 is the bed
face — it is the bond face, and it stays unbroken.

View: `just cad view mirror-light` (also mirror-spacer). Jigs: mirrorjig.py.
"""

import math
from dataclasses import dataclass
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Circle,
    Compound,
    Cylinder,
    Plane,
    Polygon,
    Pos,
    Rectangle,
    Rot,
    extrude,
    revolve,
)

from build123d import Text, TextAlign, chamfer

from .params import IN, P
from .viewer import Scene

# ---------------------------------------------------------------- layout


@dataclass(frozen=True)
class Run:
    """One segment of the loop with its spacers laid out along it.

    End reserves are expressed as MULTIPLES of the gap, not fixed lengths:
    `lead_k`/`tail_k` of 0.5 means "half a gap" (shared with a neighbouring
    run that also reserves half), 1.0 means "a whole gap" (the neighbour is
    a corner spacer, which reserves nothing). Solving for the gap with the
    reserves in the equation is what keeps every gap in the family — the
    junctions read the same as everywhere else.
    """

    name: str
    length: float
    lead_k: float
    tail_k: float
    n: int
    gap: float

    @property
    def lead(self) -> float:
        return self.lead_k * self.gap

    @property
    def at(self) -> list[float]:
        """Each spacer's centre, as arc length from the segment start."""
        pitch = P.ml_spacer_len + self.gap
        return [self.lead + P.ml_spacer_len / 2 + i * pitch for i in range(self.n)]


def _fit(name: str, length: float, lead_k: float, tail_k: float) -> Run:
    """Pick the spacer count whose resulting gap lands nearest P.ml_gap.

    length = n·spacer + (n - 1 + lead_k + tail_k)·gap, so the count alone
    sets the gap: there is no free phase for a spacer to slide into a
    junction, and no way for one to overhang the segment end."""
    def gap(n: int) -> float:
        return (length - n * P.ml_spacer_len) / (n - 1 + lead_k + tail_k)

    best = min(
        (n for n in range(1, 40) if n * P.ml_spacer_len < length and gap(n) > 0),
        key=lambda n: abs(gap(n) - P.ml_gap),
    )
    return Run(name, length, lead_k, tail_k, best, gap(best))


def _corner_run() -> Run:
    """The corner spacer IS its segment — a fixed quarter turn, no gap to
    solve and no reserves (its neighbours reserve a whole gap each)."""
    return Run("corner", P.ml_corner_run, 0.0, 0.0, 1, 0.0)


def layout() -> list[Run]:
    """The loop's segments, in path order from the bottom-centre seam:
    bottom, corner, side, arch, side, corner (back to the seam).

    The bottom run is symmetric with an odd gap count, so its middle gap
    lands on the centreline — that is the seam, where the strip's two ends
    meet and the lead wire drops away."""
    bottom = _fit("bottom", P.ml_bottom_run, 1.0, 1.0)
    side = _fit("side", P.ml_side_run, 1.0, 0.5)
    arch = _fit("arch", P.ml_arch_run, 0.5, 0.5)
    corner = _corner_run()
    return [bottom, corner, side, arch, side, corner]


# ---------------------------------------------------------------- parts


def _groove_profile(r: float):
    """Rebate section in the XZ plane at radius r (r=0 for a straight
    spacer): a plain rectangle, only ml_groove_depth deep. It is a placement
    guide, not a pocket — the strip sits proud and its own adhesive holds
    it. Shallow also means the roof overhang is trivial to print."""
    d, z0, f = P.ml_groove_depth, P.ml_groove_z0, P.ml_mouth_flare
    z1 = z0 + P.ml_groove_w
    # mouth flares both sides: no sharp lip to fight when laying the strip
    return Plane.XZ * Polygon(
        (r, z0 - f), (r - d, z0), (r - d, z1), (r, z1 + f), align=None
    )


def _finish(part, label: str, depth: float | None = None):
    """House style for every spacer: break the bed and wall-face edges so
    the first layer lays flat and nothing is sharp in the hand, then engrave
    the part name on the WALL face — visible while you place them, hidden
    once the mirror is up."""
    # re-query between the two: chamfer returns a NEW shape, and edges from
    # the old one no longer belong to it
    part = chamfer(part.edges().group_by(Axis.Z)[0], P.ml_break)
    part = chamfer(part.edges().group_by(Axis.Z)[-1], P.ml_break)
    font = Path(__file__).resolve().parent.parent / "fonts" / P.glyph_font
    glyphs = Text(
        label,
        font_size=P.ml_part_text_h / 0.7,
        font_path=str(font),
        align=(Align.CENTER, Align.CENTER),
        text_align=(TextAlign.CENTER, TextAlign.CENTER),
    )
    # `depth` is how far in from the outer face the label sits — swept parts
    # thin out toward their ends, so their label rides deeper to stay on
    # material for its whole length
    x = -(P.ml_spacer_t / 2 if depth is None else depth)
    cut = Pos(x, 0, P.ml_standoff - P.ml_part_text_depth) * Rot(0, 0, 90) * extrude(
        glyphs, amount=2 * P.ml_part_text_depth
    )
    return part - cut


def spacer_straight():
    """Straight spacer — the sides and the bottom run."""
    t, L = P.ml_spacer_t, P.ml_spacer_len
    body = Pos(-t / 2, 0, P.ml_standoff / 2) * Box(t, L, P.ml_standoff)
    body -= extrude(_groove_profile(0), amount=L, both=True)
    return _finish(body, "STRAIGHT")


def _chord_sag(r: float, sweep: float) -> float:
    """How far the flat inner face sits behind the inner arc at mid-span."""
    return (r - P.ml_spacer_t) * (1 - math.cos(math.radians(sweep / 2)))


def _swept_spacer(r: float, sweep: float):
    """A spacer swept about radius r through `sweep` degrees: curved outer
    face (the strip demands it), FLAT inner face on the chord (a stable,
    print-friendly block, and it wastes nothing worth keeping).

    Local frame: outer face midpoint at the origin, +X radially out,
    curvature centre at (-r, 0)."""
    t = P.ml_spacer_t
    half = math.radians(sweep / 2)
    sag = _chord_sag(r, sweep)  # chord depth past the inner arc
    sec = Plane.XZ * Pos(r - t - sag, 0) * Rectangle(
        t + sag, P.ml_standoff, align=(Align.MIN, Align.MIN)
    )
    body = revolve(sec, axis=Axis.Z, revolution_arc=sweep)
    body -= revolve(_groove_profile(r), axis=Axis.Z, revolution_arc=360)
    body = Pos(-r, 0, 0) * Rot(0, 0, -sweep / 2) * body
    # trim the inner arc back to its chord — the flat face
    chord = Pos(-(t + sag) - r, 0, P.ml_standoff / 2) * Box(
        2 * r, 4 * r, 2 * P.ml_standoff
    )
    return body - chord


def spacer_arch():
    """Arch spacer. One part for the whole arch: it is a single circular
    arc, so every spacer on it is identical."""
    r, sweep = P.ml_path_r, P.ml_spacer_dphi
    depth = (P.ml_spacer_t + _chord_sag(r, sweep)) / 2
    return _finish(_swept_spacer(r, sweep), "ARCH", depth)


def spacer_corner():
    """Bottom-corner spacer: a quarter turn at ml_corner_r. The strip
    cannot turn square, so the corner is a part, not a mitre."""
    depth = (P.ml_spacer_t + _chord_sag(P.ml_corner_r, 90)) / 2
    return _finish(_swept_spacer(P.ml_corner_r, 90), "CORNER", depth)


# ------------------------------------------------------------- placement


def _seat():
    """Local -> world: the parts are modelled bond-face-down (z=0 on the
    print bed, the face that glues to the mirror). On the wall that face is
    the TOP one, so every pose flips them over onto the glass — which is
    what puts the strip channel ml_groove_wall off the MIRROR, not the wall."""
    return Pos(0, 0, P.ml_standoff) * Rot(180, 0, 0)


def bottom_poses() -> list:
    """Bottom run: outer face down (-Y), length along X."""
    run = layout()[0]
    return [
        Pos(-P.ml_corner_cx + s, P.ml_inset, 0) * Rot(0, 0, -90) * _seat()
        for s in run.at
    ]


def corner_poses() -> list:
    """The two bottom corners, right first (the seam runs bottom-centre ->
    right -> up -> over -> down -> back)."""
    out = []
    for sign, mid in ((1, -45.0), (-1, 225.0)):
        out.append(
            Pos(sign * P.ml_corner_cx, P.ml_corner_cy, 0)
            * Rot(0, 0, mid)
            * Pos(P.ml_corner_r, 0, 0)
            * _seat()
        )
    return out


def side_poses(sign: int) -> list:
    """One straight side. sign=+1 is the right side (+X); the left is the
    same part turned 180 about Z."""
    run = layout()[2]
    rot = Rot(0, 0, 0) if sign > 0 else Rot(0, 0, 180)
    return [
        Pos(sign * P.ml_path_x, P.ml_corner_cy + s, 0) * rot * _seat()
        for s in run.at
    ]


def arch_angles() -> list[float]:
    """Polar angle (deg from +X, about the arch centre) of each arch
    spacer's mid-point, walking from the LEFT junction over the top."""
    run = layout()[3]
    return [
        180 - P.ml_path_phi - math.degrees(s / P.ml_path_r) for s in run.at
    ]


def arch_poses() -> list:
    return [
        Pos(0, P.ml_arch_cy, 0) * Rot(0, 0, a) * Pos(P.ml_path_r, 0, 0) * _seat()
        for a in arch_angles()
    ]


def posed_spacers() -> list:
    straight, arch, corner = spacer_straight(), spacer_arch(), spacer_corner()
    out = [loc * straight for loc in bottom_poses() + side_poses(1) + side_poses(-1)]
    out += [loc * arch for loc in arch_poses()]
    return out + [loc * corner for loc in corner_poses()]


def spacer_count() -> dict:
    bottom, corner, side, arch, *_ = layout()
    return {
        "straight": bottom.n + 2 * side.n,
        "arch": arch.n,
        "corner": 2,
        "total": bottom.n + 2 * side.n + arch.n + 2,
    }


# ------------------------------------------------------------- reference


def mirror_profile():
    """The tombstone outline as a 2D face: rectangle up to the springline,
    plus the arch circle's cap above it."""
    w, h = P.ml_mirror_w, P.ml_mirror_side_h
    face = Pos(0, h / 2) * Rectangle(w, h)
    cap = Pos(0, P.ml_arch_cy) * Circle(P.ml_arch_r)
    cap &= Pos(0, h + P.ml_arch_rise / 2) * Rectangle(w, P.ml_arch_rise)
    return face + cap


def mirror_ghost():
    """The glass itself: tombstone outline, back face on the spacer tops."""
    return Pos(0, 0, P.ml_standoff) * extrude(mirror_profile(), amount=P.ml_mirror_t)


def _band(r: float, cx: float, cy: float, a0: float, sweep: float):
    """Strip ghost following an arc of radius r about (cx, cy)."""
    w, t = P.ml_strip_w, P.ml_strip_t
    z = P.ml_standoff - P.ml_groove_z0 - w  # measured DOWN from the glass
    up = (Align.CENTER, Align.CENTER, Align.MIN)
    ring = Pos(0, 0, z) * (
        Cylinder(r + t, w, align=up) - Cylinder(r, w, align=up)
    )
    wedge = revolve(
        Plane.XZ * Pos(0, z) * Rectangle(r + t, w, align=(Align.MIN, Align.MIN)),
        axis=Axis.Z,
        revolution_arc=sweep,
    )
    return Pos(cx, cy, 0) * Rot(0, 0, a0) * (ring & wedge)


def strip_solids() -> list:
    """The lightstrip as laid, one solid per segment: bottom, two corners,
    two sides, arch. Sitting on the groove floors."""
    w, t = P.ml_strip_w, P.ml_strip_t
    z = P.ml_standoff - P.ml_groove_z0 - w / 2  # channel hangs off the glass
    d = P.ml_groove_depth
    # the rebate floor is INBOARD of the outer face, and the strip stands
    # proud outward from it — outward is -Y along the bottom run
    out = [
        Pos(0, P.ml_inset + d - t / 2, z) * Box(P.ml_bottom_run, t, w),
    ]
    for sign in (1, -1):
        out.append(
            Pos(
                sign * (P.ml_path_x - d + t / 2),
                P.ml_corner_cy + P.ml_side_run / 2,
                z,
            )
            * Box(t, P.ml_side_run, w)
        )
        a0 = -90.0 if sign > 0 else 180.0
        out.append(
            _band(P.ml_corner_r - d, sign * P.ml_corner_cx, P.ml_corner_cy, a0, 90)
        )
    out.append(
        _band(
            P.ml_path_r - d, 0, P.ml_arch_cy, P.ml_path_phi, 180 - 2 * P.ml_path_phi
        )
    )
    return out


def assembly():
    """Everything, posed, as one compound — this is what goes to STEP."""
    return Compound(children=posed_spacers() + strip_solids() + [mirror_ghost()])


# ---------------------------------------------------------------- scenes


def scene() -> Scene:
    """Full wall view: glass ghost, every spacer, the closed strip loop."""
    s = Scene()
    s.add(mirror_ghost(), "mirror", "lightblue", 0.25)
    for i, sp in enumerate(posed_spacers()):
        s.add(sp, f"spacer{i:02d}", "orange")
    for i, st in enumerate(strip_solids()):
        s.add(st, f"strip{i}", "yellow")
    return s


def spacer_scene() -> Scene:
    """The three printable spacers in a row, strip ghost in each groove."""
    w, t = P.ml_strip_w, P.ml_strip_t
    z = P.ml_groove_z0 + w / 2
    strip = Pos(-P.ml_groove_depth + t / 2, 0, z) * Box(t, P.ml_spacer_len, w)
    s = Scene()
    s.add(spacer_straight(), "spacer-straight", "orange")
    s.add(strip, "strip-straight", "yellow", 0.6)
    for i, (part, name, colour) in enumerate(
        ((spacer_arch(), "spacer-arch", "steelblue"),
         (spacer_corner(), "spacer-corner", "seagreen")),
        start=1,
    ):
        off = Pos(0, i * 2.2 * P.ml_spacer_len, 0)
        s.add(off * part, name, colour)
        s.add(off * strip, f"strip-{name}", "yellow", 0.6)
    return s


# ---------------------------------------------------------------- report


def report() -> list[str]:
    """The numbers worth reading before ordering screws or hanging glass."""
    bottom, corner, side, arch, *_ = layout()
    n = spacer_count()
    return [
        f"arch: R {P.ml_arch_r:.1f}mm ({P.ml_arch_r / IN:.3f}in), centre "
        f"{P.ml_arch_cy:.1f}mm up ({P.ml_arch_cy / IN:.2f}in), "
        f"sweep {180 - 2 * P.ml_path_phi:.2f}deg",
        f"inset contour: sides x=+-{P.ml_path_x:.1f}mm, arch R "
        f"{P.ml_path_r:.1f}mm, corners R {P.ml_corner_r:.1f}mm",
        f"loop: bottom {P.ml_bottom_run / IN:.1f} + corners "
        f"{P.ml_corner_run / IN:.1f}x2 + sides {P.ml_side_run / IN:.1f}x2 + "
        f"arch {P.ml_arch_run / IN:.1f} = {P.ml_path_len / IN:.1f}in "
        f"({P.ml_path_len / IN / 12:.2f}ft)",
        f"strip {P.ml_strip_len / IN / 12:.2f}ft -> {P.ml_slack / IN:.1f}in "
        f"spare, tucks behind the glass at the bottom-centre seam",
        f"  (cut marks are {330 / IN:.0f}in apart — too coarse to trim)",
        f"spacers: {n['straight']} straight + {n['arch']} arch + "
        f"{n['corner']} corner = {n['total']} total",
        f"gaps: bottom {bottom.gap / IN:.2f}in, side {side.gap / IN:.2f}in, "
        f"arch {arch.gap / IN:.2f}in, corner-to-side {side.lead / IN:.2f}in, "
        f"arch junction {(0.5 * side.gap + arch.lead) / IN:.2f}in",
        f"rebate: {P.ml_groove_w:.1f} wide x {P.ml_groove_depth:.1f} deep — "
        f"a {P.ml_strip_w:.1f} x {P.ml_strip_t:.1f}mm sleeve sits in it "
        f"{P.ml_strip_proud:.1f}mm proud, held by its own adhesive",
        f"  channel rides {P.ml_groove_wall:.1f}mm off the GLASS "
        f"({P.ml_groove_wall_far:.1f}mm left wall-side) -> emitter stays "
        f"hidden until {P.ml_emitter_hide_deg:.0f}deg off the wall plane",
        f"no fasteners: {P.ml_spacer_len / IN:.0f}in x {P.ml_spacer_t:.0f}mm "
        f"bond face per spacer glues to the frame back "
        f"({n['total'] * P.ml_spacer_len * P.ml_spacer_t / 100:.0f}cm2 total)",
        "  the mirror then rests on them against the wall",
    ]
