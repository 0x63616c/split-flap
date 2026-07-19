"""P2S poop bucket XL — side quest, not part of the split-flap.

Waste-chute catcher for the Bambu P2S, remodelled from a downloaded
vase-mode bucket and enlarged: depth 1.5x toward the wall, left side
extended 80mm, right side (cramped against the chute door) capped at
the old edge + 1 inch. The chute-fit geometry — spout tube, door
notch, 80mm body width at the top — is measured off the original mesh
and unchanged.

Built as a SOLID: spiral-vase slicing keeps only the outer contour per
layer, so the print is a hollow single-wall bucket regardless. Every
transition is a 45 deg planar chamfer (wing tops, notch ramp, spout
underside) so the spiral wall always lands on the layer below.

Local frame: X left-right (facing the engraved logo: +X = viewer's
right), Y=0 at the printer-side face (body extends -Y, spout +Y over
the chute), Z=0 at the bed.

View: `just cad view poop-bucket` (ghost = original-size bucket).
"""

from build123d import (
    FontStyle,
    Plane,
    Polyline,
    Pos,
    RectangleRounded,
    Text,
    extrude,
    make_face,
)

from .params import P
from .viewer import Scene


def _wedge_cut(profile_pts, y_depth):
    """Prism through the full Y depth from an XZ polygon."""
    face = make_face(Plane.XZ * Polyline(*profile_pts, close=True))
    return extrude(face, amount=y_depth, both=True, dir=(0, 1, 0))


def poop_bucket(ext_l: float | None = None, ext_r: float | None = None,
                depth: float | None = None):
    """The bucket solid. Zero the extensions / pass the original depth
    to rebuild the original-size bucket from the same geometry."""
    ext_l = P.pb_ext_l if ext_l is None else ext_l
    ext_r = P.pb_ext_r if ext_r is None else ext_r
    d = P.pb_d if depth is None else depth
    hw = P.pb_body_w / 2
    h, r = P.pb_h, P.pb_corner_r

    # slab: full footprint, printer-side face at y=0
    w = P.pb_body_w + ext_l + ext_r
    cx = (ext_r - ext_l) / 2
    slab = extrude(
        Pos(cx, -d / 2, 0) * RectangleRounded(w, d, r), amount=h
    )

    big = w + 2 * r  # anything safely past the widest face
    if ext_l:
        # 45 deg chamfer from the body wall down-left over the wing
        zt = P.pb_wing_top_l
        slab -= _wedge_cut(
            [(-hw, zt), (-hw - big, zt - big), (-hw - big, h + big), (-hw, h + big)],
            d + big,
        )
    if ext_r:
        # right wing top meets the wall where the notch ramp begins
        zt = P.pb_notch_z
        slab -= _wedge_cut(
            [(hw, zt), (hw + big, zt - big), (hw + big, h + big), (hw, h + big)],
            d + big,
        )

    # chute-door notch: 45 deg ramp from the right wall in to pb_notch_x
    nz = P.pb_notch_z
    ramp = nz + (hw - P.pb_notch_x)
    slab -= _wedge_cut(
        [(P.pb_notch_x, ramp), (hw, nz), (hw + big, nz), (hw + big, h + big),
         (P.pb_notch_x, h + big)],
        d + big,
    )

    # spout: rounded-rect tube swept down-back at 45 deg from the top
    # rim; only the part past y=0 shows — the tail buries in the body
    sw = P.pb_spout_x1 - P.pb_spout_x0
    scx = (P.pb_spout_x0 + P.pb_spout_x1) / 2
    reach = P.pb_spout_reach
    prof = Plane.XY.offset(h) * Pos(scx, reach / 2, 0) * RectangleRounded(
        sw, reach, r
    )
    # 50mm of drop buries the tail inside the body without ever
    # poking the back wall (y stays > -75); slant = reach over
    # (h - z0), the measured 46 deg
    drop = h - P.pb_spout_z0
    dvec = (0, -reach, -drop)
    dlen = (reach**2 + drop**2) ** 0.5
    spout = extrude(prof, amount=50 * dlen / drop, dir=dvec)
    slab += spout

    # engraved logo on the wall-side face, aligned with the body centre
    txt = Plane(
        origin=(0, -d, P.pb_text_z), x_dir=(1, 0, 0), z_dir=(0, -1, 0)
    ) * Text("P2S", font_size=P.pb_text_h, font_style=FontStyle.BOLD)
    slab -= extrude(txt, amount=-P.pb_text_depth)

    return slab


def poop_bucket_original():
    """Original-size bucket from the same generator (fit reference)."""
    return poop_bucket(ext_l=0.0, ext_r=0.0, depth=P.pb_body_d)


def scene() -> Scene:
    return (
        Scene()
        .add(poop_bucket(), "poop-bucket", color="orange")
        .add(poop_bucket_original(), "original (ghost)", color="grey", alpha=0.25)
    )
