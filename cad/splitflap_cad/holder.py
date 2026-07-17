"""PROTOTYPE — flap-loading holder (jig).

A ring that slips around the drum's flap ring, with one radial spike per
flap slot. During assembly you drop the drum into the ring, rest each
flap on the spike that lines up with its slot, and thread the flap's
side-pins into the ring slots without it flopping while you load the
rest. An up-turned lip at each spike tip stops a resting flap sliding
off.

Frame: drum axis = Z, base-ring underside at z=0. Prints flat, ring-down.

View it: `just cad dev holder`.
"""

from build123d import Axis, Box, Cylinder, Pos, Rot, chamfer, fillet

from .params import P


def _spike():
    """One radial spike: a beam from the base-ring OD outward, with an
    up-turned lip at the tip. Built along +X, base at z=0."""
    r_in = P.holder_ring_id / 2  # start at the bore so it ties into the ring
    r_out = P.holder_ring_id / 2 + P.holder_ring_w + P.holder_spike_len
    beam = Pos((r_in + r_out) / 2, 0, P.holder_spike_h / 2) * Box(
        r_out - r_in, P.holder_spike_w, P.holder_spike_h
    )
    lip = Pos(
        r_out - P.holder_lip_t / 2, 0, P.holder_lip_h / 2
    ) * Box(P.holder_lip_t, P.holder_spike_w, P.holder_lip_h)
    return beam + lip


def holder():
    """The loading jig: base ring + one spike per flap slot."""
    r_id = P.holder_ring_id / 2
    r_od = r_id + P.holder_ring_w
    ring = Pos(0, 0, P.holder_ring_t / 2) * (
        Cylinder(r_od, P.holder_ring_t) - Cylinder(r_id, P.holder_ring_t * 2)
    )
    body = ring
    for i in range(P.drum_flap_count):
        body += Rot(0, 0, i * P.holder_spike_pitch) * _spike()
    # break the sharp outer corners of the ring and spike tips
    body = chamfer(
        body.edges().filter_by(Axis.Z).group_by(Axis.Z)[-1], 0.6
    )
    return body


def holder_show_args() -> dict:
    """holder alone; drum ghost overlaid when the outer part is buildable."""
    objects, names, colors, alphas = [holder()], ["holder"], ["seagreen"], [1.0]
    try:
        from .drum import drum_outer

        objects.append(drum_outer())
        names.append("drum_outer")
        colors.append("orange")
        alphas.append(0.4)
    except Exception:
        pass
    return dict(objects=objects, names=names, colors=colors, alphas=alphas)
