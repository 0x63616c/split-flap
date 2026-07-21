"""Placement jigs for the mirror backlight spacers (mirrorlight.py).

Bonding 21 spacers to the back of a mirror by tape measure is a way to get
21 near-misses. Instead: flat templates that hook the glass edge and hold a
window exactly where the next spacer goes.

How they work — mirror face-down on a table, back face up:
1. Corner jig seats into a bottom corner (a rail down each edge); its window
   lands the corner spacer. Do both corners first: they anchor everything.
2. A chain jig has TWO windows a segment's gap apart. Drop the small catch
   window over the spacer you just stuck, push the edge rail against the
   glass, and the big window is where the next spacer goes. Stick it, step
   the jig along, repeat.
Every window is the spacer's own footprint plus jig_clear, so the jig lifts
straight off afterwards.

One jig per segment, because the gaps differ slightly (bottom / side / arch
each solve to their own). Labels are engraved so they can't be mixed up.

Local frame = AS PRINTED: plate on the bed, z=0 the bed face, the edge rail
standing proud on top. FLIP IT OVER to use — then the rail hangs over the
glass edge and the labels read the right way up. Nothing overhangs, so no
supports; that is the whole reason the rail is modelled on the far side.

Straight jigs: x = 0 at the mirror edge, +X inboard, Y along the contour.
Swept jigs: same, wrapped about their arc centre at (-radius, 0).

View: `just cad view mirror-jigs`. Prints: mirror-jig-{bottom,side,arch,corner}.
"""

import math

from build123d import (
    Align,
    Axis,
    Box,
    Plane,
    Pos,
    Rectangle,
    Rot,
    Text,
    TextAlign,
    extrude,
    mirror,
    revolve,
)

from .mirrorlight import layout
from .params import P
from .viewer import Scene

CATCH = 24.0  # how much of the placed spacer the catch window grabs
CLEAR = 0.4  # window clearance around the spacer footprint
RAIL_W = 6.0  # edge rail thickness, outboard of the glass edge
MARGIN = 8.0  # plate material past a window
LABEL_BAND = 22.0  # solid band kept for the engraved segment label
FONT = "GeistMono-SemiBold.ttf"


def _label(text: str, loc):
    """Engraved label on the bed face, mirrored so it reads once the jig is
    flipped over for use. `loc` poses it — the swept jigs hand in a location
    on their arc, so the label follows the plate."""
    from pathlib import Path

    font = Path(__file__).resolve().parent.parent / "fonts" / FONT
    glyphs = Text(
        text,
        font_size=P.ml_jig_text_h / 0.7,
        font_path=str(font),
        align=(Align.CENTER, Align.CENTER),
        text_align=(TextAlign.CENTER, TextAlign.CENTER),
    )
    # mirror the GLYPHS about their own centre, then pose — mirroring after
    # posing would fling the label off the plate
    return extrude(loc * mirror(glyphs, about=Plane.XZ), amount=P.ml_jig_text_depth)


def _sector(r0: float, r1: float, z0: float, z1: float, sweep: float):
    """Annular sector solid: radii r0..r1, heights z0..z1, 0..sweep deg."""
    sec = Plane.XZ * Pos(r0, z0) * Rectangle(
        r1 - r0, z1 - z0, align=(Align.MIN, Align.MIN)
    )
    return revolve(sec, axis=Axis.Z, revolution_arc=sweep)


def _chain_jig(run_name: str, label: str, radius: float | None = None):
    """Template for one segment: catch window, then the segment's gap, then
    the window for the next spacer. `radius` (the segment's contour radius)
    curves the whole thing; None keeps it straight."""
    gap = next(r for r in layout() if r.name == run_name).gap
    t, ins, jt = P.ml_spacer_t, P.ml_inset, P.ml_jig_t
    x_in = ins + t + MARGIN  # inboard edge of the plate
    y0, y1 = -CATCH - MARGIN, gap + P.ml_spacer_len + MARGIN

    def place(x, y, rot):
        """Plate-space (x inboard, y along the contour) -> a Location."""
        if radius is None:
            return Pos(x, y) * Rot(0, 0, rot)
        r = radius + P.ml_inset
        return (
            Pos(-r, 0, 0) * Rot(0, 0, math.degrees(y / radius))
            * Pos(r - x, 0, 0) * Rot(0, 0, rot)
        )

    def block(x0, x1, z0, z1, ya, yb):
        """Plate-space box, wrapped onto the arc when radius is set."""
        if radius is None:
            return Pos((x0 + x1) / 2, (ya + yb) / 2, (z0 + z1) / 2) * Box(
                x1 - x0, yb - ya, z1 - z0
            )
        r = radius + ins  # mirror edge radius (x=0 sits on the glass edge)
        a0, a1 = math.degrees(ya / radius), math.degrees(yb / radius)
        return Pos(-r, 0, 0) * Rot(0, 0, a0) * _sector(
            r - x1, r - x0, z0, z1, a1 - a0
        )

    jig = block(0, x_in, 0, jt, y0, y1)
    jig += block(-RAIL_W, 0, 0, jt + P.ml_jig_lip_drop, y0, y1)
    # catch: an open-ended NOTCH, not a window — the placed spacer runs on
    # past the end of the jig, so the plate must not cover it
    jig -= block(ins - CLEAR, ins + t + CLEAR, -1, jt + 1, y0 - 1, CLEAR)
    jig -= block(
        ins - CLEAR, ins + t + CLEAR, -1, jt + 1,
        gap - CLEAR, gap + P.ml_spacer_len + CLEAR,
    )
    # lighten: the plate only has to reach the glass edge and hold the
    # windows square — the field between them is dead weight
    if gap > 4 * MARGIN:
        jig -= block(MARGIN, ins - LABEL_BAND, -1, jt + 1, MARGIN, gap - MARGIN)
    jig -= block(
        MARGIN, ins - LABEL_BAND, -1, jt + 1,
        gap + MARGIN, gap + P.ml_spacer_len - MARGIN,
    )
    jig -= _label(label, place(ins - LABEL_BAND / 2, gap / 2, 90))
    return jig


def jig_bottom():
    """Bottom run — the longest gap of the three."""
    return _chain_jig("bottom", "BOTTOM")


def jig_side():
    """Both straight sides."""
    return _chain_jig("side", "SIDE")


def jig_arch():
    """The arch: same idea, swept about the inset arch radius."""
    return _chain_jig("arch", "ARCH", radius=P.ml_path_r)


def jig_corner():
    """Bottom corner: rails down BOTH mirror edges, one window for the
    corner spacer. Start here — the corners anchor every chain."""
    r, t, ins, jt = P.ml_corner_r, P.ml_spacer_t, P.ml_inset, P.ml_jig_t
    cx = ins + r  # turn centre, from either edge
    span = cx + MARGIN + 10  # far enough to carry the arc's endpoints
    rail_h = jt + P.ml_jig_lip_drop
    jig = Pos(span / 2, span / 2, jt / 2) * Box(span, span, jt)
    jig += Pos(-RAIL_W / 2, (span - RAIL_W) / 2, rail_h / 2) * Box(
        RAIL_W, span + RAIL_W, rail_h
    )
    jig += Pos((span - RAIL_W) / 2, -RAIL_W / 2, rail_h / 2) * Box(
        span + RAIL_W, RAIL_W, rail_h
    )
    # window: the corner spacer's footprint, quarter turn about the centre
    sag = (r - t) * (1 - math.cos(math.radians(45)))
    jig -= Pos(cx, cx, 0) * Rot(0, 0, 180) * _sector(
        r - t - sag - CLEAR, r + CLEAR, -1, jt + 1, 90
    )
    jig -= _label("CORNER", Pos(cx * 0.5, cx * 0.5) * Rot(0, 0, 45))
    return jig


def scene() -> Scene:
    """All four jigs laid out side by side, as printed."""
    s = Scene()
    x = 0.0
    for part, name, colour in (
        (jig_bottom(), "jig-bottom", "orange"),
        (jig_side(), "jig-side", "steelblue"),
        (jig_arch(), "jig-arch", "seagreen"),
        (jig_corner(), "jig-corner", "orchid"),
    ):
        bb = part.bounding_box()
        s.add(Pos(x - bb.min.X, 0, 0) * part, name, colour)
        x += bb.max.X - bb.min.X + 20
    return s
