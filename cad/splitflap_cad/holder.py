"""PROTOTYPE — flap-loading holder (jig).

A ring that slips around the drum's flap ring, with one radial SLOT per
flap position cut into its top face. Drop the drum into the ring, then
drop each flap edge-first into the slot that lines up with its drum slot
so it stands upright and can't flop while you thread the side-pins in
and load the rest. The slot plane is radial — the flap faces
tangentially, the same as when mounted on the drum.

Frame: drum axis = Z, ring underside at z=0. Prints flat, ring-down.

View it: `just cad dev holder`.
"""

from build123d import Axis, Box, Cylinder, Pos, Rot, chamfer

from .params import P


def _slot_cutter():
    """One radial slot cutter: a thin box open at the top face, cut
    holder_slot_depth deep. Built along +X."""
    r_in = P.holder_ring_id / 2 + P.holder_slot_inset
    r_mid = r_in + P.holder_slot_len / 2
    z_top = P.holder_ring_t
    return Pos(r_mid, 0, z_top - P.holder_slot_depth / 2) * Box(
        P.holder_slot_len, P.holder_slot_w, P.holder_slot_depth + 0.02
    )


def holder():
    """The loading jig: a ring with one radial flap-slot per drum slot."""
    r_id = P.holder_ring_id / 2
    r_od = r_id + P.holder_ring_w
    body = Pos(0, 0, P.holder_ring_t / 2) * (
        Cylinder(r_od, P.holder_ring_t) - Cylinder(r_id, P.holder_ring_t * 2)
    )
    cutter = _slot_cutter()
    for i in range(P.drum_flap_count):
        body -= Rot(0, 0, i * P.holder_slot_pitch) * cutter
    # break the top outer edge (print/handling)
    body = chamfer(body.edges().filter_by(Axis.Z).group_by(Axis.Z)[-1], 0.6)
    return body


def _flap_in_slot():
    """A flap posed in slot 0: width (the pin-to-pin span) along the drum
    axis = vertical, height radial. Pivot edge faces the bore so the
    lower pin hangs over the drum ring's slot span; the body's lower
    side edge sits on the slot floor."""
    from .flap import flap

    # flap local: x = width, y = height (0 at the pivot edge), z =
    # thickness. Rot(90,0,0) then Rot(0,90,0): x -> -Z, y -> +X, z -> -Y.
    r_pin_mid = (P.drum_slot_r_in_inner + P.drum_slot_r_out) / 2
    x_pivot = r_pin_mid - (P.flap_pin_y0 + P.flap_pin_h / 2)
    z_floor = P.holder_ring_t - P.holder_slot_depth
    pose = Pos(x_pivot, P.flap_thick / 2, z_floor + P.flap_w / 2)
    return pose * Rot(0, 90, 0) * Rot(90, 0, 0) * flap()


def holder_show_args() -> dict:
    """holder + a flap posed in slot 0; drum ghost overlaid when the
    outer part is buildable."""
    objects, names, colors, alphas = [holder()], ["holder"], ["seagreen"], [1.0]
    try:
        objects.append(_flap_in_slot())
        names.append("flap")
        colors.append("white")
        alphas.append(0.9)
    except Exception:
        pass
    try:
        from .drum import drum_outer

        objects.append(drum_outer())
        names.append("drum_outer")
        colors.append("orange")
        alphas.append(0.4)
    except Exception:
        pass
    return dict(objects=objects, names=names, colors=colors, alphas=alphas)
