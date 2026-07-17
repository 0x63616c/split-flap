"""PROTOTYPE — flap-loading holder (jig).

A ring that slips around the drum's flap ring, with one radial SLOT per
flap position cut into its top face, running the full ring width — open
at the bore and at the OD. A small rim (inward flange, slot-floor high)
at the bore bottom catches the drum ring so its underside sits flush
with the slot floors. Drop the drum onto the rim, then drop each flap
edge-first into the slot that lines up with its drum slot so it stands
upright and can't flop while you thread the side-pins in and load the
rest. The slot plane is radial — the flap faces tangentially, the same
as when mounted on the drum.

Frame: drum axis = Z, ring underside at z=0. Prints flat, ring-down.

View it: `just cad dev holder`.
"""

from build123d import Axis, Box, Cylinder, Pos, Rot, chamfer

from .geo import polar, slot0_marker
from .params import P


def _slot_cutter():
    """One radial slot cutter: a thin box open at the top face, cut
    holder_slot_depth deep, spanning the full ring width (overshoots the
    bore and the OD so both ends are open). Built along +X."""
    r_in = P.holder_ring_id / 2 - 1.0
    r_out = P.holder_ring_id / 2 + P.holder_ring_w + 1.0
    z_top = P.holder_ring_t
    return Pos((r_in + r_out) / 2, 0, z_top - P.holder_slot_depth / 2) * Box(
        r_out - r_in, P.holder_slot_w, P.holder_slot_depth + 0.02
    )


def holder():
    """The loading jig: a ring with one radial flap-slot per drum slot
    and a bottom rim the drum ring rests on."""
    r_id = P.holder_ring_id / 2
    r_od = r_id + P.holder_ring_w
    body = Pos(0, 0, P.holder_ring_t / 2) * (
        Cylinder(r_od, P.holder_ring_t) - Cylinder(r_id, P.holder_ring_t * 2)
    )
    # bottom rim: inward flange, slot-floor high, catches the drum ring
    rim_h = P.holder_slot_floor
    body += Pos(0, 0, rim_h / 2) * (
        Cylinder(r_id + 0.01, rim_h) - Cylinder(r_id - P.holder_rim_w, rim_h * 2)
    )
    for c in polar(_slot_cutter(), P.drum_flap_count):
        body -= c
    # break the top outer edge (print/handling); before the marker cut,
    # whose shallow vertical edges would land in the topmost edge group
    body = chamfer(body.edges().filter_by(Axis.Z).group_by(Axis.Z)[-1], 0.6)
    # slot-0 indicator on the top face, apex in at the bore — slot 0's
    # slit splits it down the middle, which still reads fine
    body -= slot0_marker(P.holder_ring_id / 2 + 1.0, P.holder_ring_t, point="in")
    return body


def _flap_in_slot():
    """A flap posed in slot 0: width (the pin-to-pin span) along the drum
    axis = vertical, height radial. Pivot edge faces the bore, the lower
    pin drops through the drum ring's slot, and the body's lower side
    edge rests on the drum ring's top face (the drum sits on the rim,
    ring underside flush with the slot floors)."""
    from .flap import flap

    # flap local: x = width, y = height (0 at the pivot edge), z =
    # thickness. Rot(90,0,0) then Rot(0,90,0): x -> -Z, y -> +X, z -> -Y.
    r_pin_mid = (P.drum_slot_r_in_inner + P.drum_slot_r_out) / 2
    x_pivot = r_pin_mid - (P.flap_pin_y0 + P.flap_pin_h / 2)
    z_ring_top = P.holder_slot_floor + P.drum_ring_t  # drum sits on the rim
    pose = Pos(x_pivot, P.flap_thick / 2, z_ring_top + P.flap_w / 2)
    return pose * Rot(0, 90, 0) * Rot(90, 0, 0) * flap()


def scene():
    """holder + a flap posed in slot 0; drum ghost overlaid when the
    outer part is buildable."""
    from .viewer import Scene

    s = Scene().add(holder(), "holder", "seagreen")
    try:
        s.add(_flap_in_slot(), "flap", "white", alpha=0.9)
    except Exception:
        pass
    try:
        from .drum import drum_outer

        s.add(drum_outer(), "drum_outer", "orange", alpha=0.4, loc=Pos(0, 0, P.holder_slot_floor))
    except Exception:
        pass
    return s
