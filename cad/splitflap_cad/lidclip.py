"""Storage-box lid clip — side quest, not part of the split-flap.

The box lids are floppy because their side wall is a bare 3mm skirt.
This is an inverted-U that presses down over that skirt: the channel is
4mm wide at the closed end and only 2.5mm at the mouth, so the legs
splay going on and squeeze the wall as they relax. No fasteners, no
glue — friction and the legs' spring.

Local frame: X across the wall, Z up (z=0 at the leg tips, +Z toward
the closed end), Y along the lid edge. The cross-section is constant,
so the part is one extrusion — print it standing on a tip face with the
run vertical and the layers lie in the plane the legs flex in.

This is the test coupon: `lclip_len` of it, to check the grip before
cutting the full lid length.

View: `just cad view lid-clip`.
"""

from build123d import Axis, Box, Plane, Polygon, Pos, extrude, fillet

from .params import P
from .viewer import Scene


def _profile_halves():
    """(mouth half-width, base half-width, channel top z) of the channel."""
    return P.lclip_ch_mouth / 2, P.lclip_ch_base / 2, P.lclip_h - P.lclip_wall


def _break_edges(part):
    """Break every corner of the profile (its edges run along Y): kinder
    to print, and the rounded tips lead the clip onto the wall. Always
    the LAST step — filleting a fillet fails."""
    return fillet(part.edges().filter_by(Axis.Y), 0.5)


def _clip_raw():
    """The channel section, sharp — the base for every variant.

    Bottom up: a parallel skirt at the mouth width, then the tapering U,
    then the cap. z=0 is the leg tips."""
    m, b, top = _profile_halves()
    w, h, s = P.lclip_wall, P.lclip_h, P.lclip_skirt
    # Outer is a plain rectangle at the widest section, run all the way
    # down: the silhouette stays a clean block and the arms thicken
    # toward the mouth, where the channel narrows away from it.
    x, z = b + w, s + h
    outer = Polygon((-x, 0), (x, 0), (x, z), (-x, z), align=None)
    channel = Polygon(
        (-m, 0), (m, 0), (m, s), (b, s + top), (-b, s + top), (-m, s),
        align=None,
    )
    plane = Plane.XZ
    return extrude(plane * outer, P.lclip_len) - extrude(plane * channel, P.lclip_len)


def lid_clip():
    """The clip alone: channel-shaped extrusion, mouth down."""
    return _break_edges(_clip_raw())


def lid_clip_post():
    """Clip + stack post: a column on the closed end at the clip's own
    footprint, `lclip_post_h` tall measured from the inner cap face (so
    the stand-off above the clip is that minus the cap). The box above
    lands on these instead of on the lid."""
    proud = P.lclip_post_h - P.lclip_wall
    post = Pos(0, -P.lclip_len / 2, P.lclip_skirt + P.lclip_h + proud / 2) * Box(
        P.lclip_ch_base + 2 * P.lclip_wall, P.lclip_len, proud
    )
    return _break_edges(_clip_raw() + post)


def scene() -> Scene:
    """Bare coupon beside the posted one."""
    pitch = 2 * (P.lclip_ch_base + 2 * P.lclip_wall)
    return (
        Scene()
        .add(lid_clip(), "clip-only", loc=Pos(-pitch, 0, 0))
        .add(lid_clip_post(), "clip-post")
    )
