"""The flap drum — two printed parts, dimensions measured off the Kingsman
FlapDrum{Outer,Inner}.stl (Printables #69464).

Outer: flap ring + barrel wall like a pringles can. Inner (the short side,
faces the motor): flap ring + web disc + shaft hub; its ring seats on the
barrel's open end.

Drum frame: z=0 at the outer ring's underside, axis = +Z. In the unit the
drum sits at (mount_x, byj_shaft_y), outer ring toward the plate.

View it: `just cad drum` (see cad/splitflap_cad/catalog.py).
"""

from build123d import (
    Axis,
    Box,
    Circle,
    Cylinder,
    Polygon,
    Pos,
    Rectangle,
    Rot,
    SlotCenterToCenter,
    chamfer,
    extrude,
    fillet,
    revolve,
)

from .params import P


def _slot_cutter():
    """Elongated radial pin-slot cutter (Kingsman style): drum_slot_w wide
    with round ends, spanning drum_slot_r_in_inner..drum_slot_r_out. Long
    axis along +X; z spans -ring_t..+ring_t so it cuts a ring centered at
    z=0 or sitting on z=0 alike."""
    r_in, r_out = P.drum_slot_r_in_inner, P.drum_slot_r_out
    slot2d = SlotCenterToCenter((r_out - r_in) - P.drum_slot_w, P.drum_slot_w)
    cutter = extrude(slot2d, amount=P.drum_ring_t * 2)
    return Pos((r_in + r_out) / 2, 0, -P.drum_ring_t) * cutter


def _cut_slots(part):
    """Cut drum_flap_count radial pin slots into part (around z=0..ring_t)."""
    cutter = _slot_cutter()
    for i in range(P.drum_flap_count):
        part -= Rot(0, 0, i * 360 / P.drum_flap_count) * cutter
    return part


def _ring():
    """A flap ring: annulus with drum_flap_count elongated radial pin
    slots — pins pivot and get ~1mm radial float to self-align."""
    ring = Cylinder(P.drum_ring_od / 2, P.drum_ring_t) - Cylinder(
        P.drum_ring_id / 2, P.drum_ring_t * 2
    )
    return _cut_slots(Pos(0, 0, P.drum_ring_t / 2) * ring)


def _slot0_marker(z_face, depth_sign):
    """Debossed triangle pointing (radially outward) at flap slot 0, cut
    into a horizontal face at z_face. depth_sign=-1 cuts down into a top
    face, +1 cuts up into a bottom face."""
    apex_r = P.drum_slot_r_in_inner - 0.5
    base_r = apex_r - P.drum_mark_len
    tri = Polygon(
        (apex_r, 0),
        (base_r, P.drum_mark_w / 2),
        (base_r, -P.drum_mark_w / 2),
        align=None,
    )
    return Pos(0, 0, z_face - (P.drum_mark_depth if depth_sign < 0 else 0)) * extrude(
        tri, amount=P.drum_mark_depth
    )


def _barrel(length):
    """A stub of the barrel wall, base at z=0."""
    return Pos(0, 0, length / 2) * (
        Cylinder(P.drum_wall_r_out, length) - Cylinder(P.drum_wall_r_in, length * 2)
    )


def drum_outer():
    """Outer drum: flap ring + its share of the barrel wall, plus a full
    guide ring (annular lip on the wall's inner face) notched at the fin
    positions. Fins can only enter at the notches, so the parts index at
    ANY approach angle; notch 0 is wider for the key fin: one assembly
    orientation."""
    body = _ring() + Pos(0, 0, P.drum_ring_t) * _barrel(P.drum_barrel_len_outer)

    # Short full guide ring at the butt joint; its lower end ramps back
    # into the wall at 45 deg so the lip prints without overhangs (part
    # prints flap-ring-down, axis vertical).
    z_butt = P.drum_ring_t + P.drum_barrel_len_outer
    z_ring = z_butt - P.drum_guide_ring_len
    r_embed = P.drum_wall_r_in + 0.2
    r_face = P.drum_wall_r_in - P.drum_guide_rib_h

    def _lip_profile(z_lo):
        return Polygon(
            (r_embed, z_butt),
            (r_face, z_butt),
            (r_face, z_lo + P.drum_guide_rib_h),
            (P.drum_wall_r_in, z_lo),
            (r_embed, z_lo),
            align=None,
        )

    body += revolve(Rot(90, 0, 0) * _lip_profile(z_ring), Axis.Z)

    # Notches through the ring: one per fin, width = fin thickness +
    # clearance per side.
    # cutter stops flush at the wall face — overshooting radially dents
    # a step into the barrel wall behind the notch
    notch_x = (r_face - 0.5 + P.drum_wall_r_in) / 2
    notch_dx = P.drum_wall_r_in - (r_face - 0.5)
    for a in range(P.drum_fin_count):
        fin_t = P.drum_fin_t_key if a == 0 else P.drum_fin_t
        body -= Rot(0, 0, a * 360 / P.drum_fin_count) * Pos(
            notch_x, 0, (z_butt + z_ring) / 2
        ) * Box(
            notch_dx,
            fin_t + 2 * P.drum_fin_clear,
            P.drum_guide_ring_len + 2 * P.drum_guide_rib_h + 1,
        )

    # Below the ring, rail pairs flank each notch down to drum_guide_len
    # so the fins stay side-supported over their whole travel; same
    # 45-deg ramp at the lower end.
    z_bot = z_butt - P.drum_guide_len
    # (this polygon winds opposite to the fin's, so it extrudes -Y and
    # needs the opposite recentring shift)
    rib = Pos(0, P.drum_guide_rib_w / 2, 0) * Rot(90, 0, 0) * extrude(
        _lip_profile(z_bot), amount=P.drum_guide_rib_w
    )
    for a in range(P.drum_fin_count):
        fin_t = P.drum_fin_t_key if a == 0 else P.drum_fin_t
        gap = fin_t / 2 + P.drum_fin_clear
        for side in (+1, -1):
            body += Rot(0, 0, a * 360 / P.drum_fin_count) * Pos(
                0, side * (gap + P.drum_guide_rib_w / 2), 0
            ) * rib

    # First-slot indicator: triangle debossed into the ring's outside
    # (bottom) face, on the key-notch line pointing at slot 0.
    body -= _slot0_marker(0, +1)
    return body


def drum_inner():
    """Inner drum (short side): ring + web disc, shaft hub with double-D
    bore, two screw bosses, its share of the barrel wall. Own frame: web
    underside at z=0, hub and barrel pointing -Z (toward the motor once
    assembled)."""
    # Ring + web are one 1.6 disc: full circle out to the ring OD, slots
    # in the ring band, four lightening holes in the web.
    body = Pos(0, 0, P.drum_ring_t / 2) * Cylinder(P.drum_ring_od / 2, P.drum_ring_t)
    # Elongated radial pin slots, matching the outer ring.
    body = _cut_slots(body)
    # Only 3 lightening windows: the 45-deg quadrant stays solid to
    # carry the homing magnet. Pie-quadrant shaped: annular sector with
    # uniform margins to the hub, barrel wall and fin faces, rounded
    # corners.
    w_r_in = P.drum_hub_d / 2 + P.drum_web_window_edge
    w_r_out = P.drum_wall_r_in - P.drum_web_window_edge
    fin_off = P.drum_web_window_fin_gap + P.drum_fin_t_key / 2
    quad = Pos(fin_off + w_r_out / 2, fin_off + w_r_out / 2) * Rectangle(
        w_r_out, w_r_out
    )
    window = (Circle(w_r_out) - Circle(w_r_in)) & quad
    window = fillet(window.vertices(), P.drum_web_window_fillet)
    cutter = extrude(window, amount=P.drum_ring_t * 2)
    for ang in (90, 180, 270):  # window centres 135/225/315; 45 solid
        body -= Rot(0, 0, ang) * cutter

    # First-slot indicator: triangle debossed into the web's outside
    # (top) face, on the key-fin line pointing at slot 0.
    body -= _slot0_marker(P.drum_ring_t, -1)

    # This part's share of the barrel wall, reaching down to butt against
    # the outer part's share mid-drum.
    body += Pos(0, 0, -P.drum_barrel_len_inner) * _barrel(P.drum_barrel_len_inner)

    # Connector fins: thin radial plates from the hub out to just shy of
    # the barrel's inner face, hanging below the web. Fin-shaped profile:
    # bottom edge slopes from shallow at the hub to full depth at the
    # rim, where the tips land in the outer part's guide-ring slots.
    fin_r_in = P.drum_hub_d / 2 - 1
    fin_r_out = P.drum_wall_r_in - P.drum_fin_clear
    profile = Polygon(
        (fin_r_in, 0),
        (fin_r_out, 0),
        (fin_r_out, -P.drum_fin_len),
        (fin_r_in, -P.drum_fin_len_hub),
        align=None,
    )
    # round the tip corner (where the sloped bottom edge meets the rim)
    # so the fin docks into the guide channels easily
    profile = fillet(profile.vertices().sort_by(Axis.Y)[0], P.drum_fin_tip_fillet)
    # profile is radial(x) x axial(y); extrude the thickness and stand
    # it up so the built y becomes the drum's -Z. Fin 0 is thicker (the
    # key): only fits channel 0, so there's one assembly orientation.
    for a in range(P.drum_fin_count):
        fin_t = P.drum_fin_t_key if a == 0 else P.drum_fin_t
        fin = Pos(0, -fin_t / 2, 0) * Rot(90, 0, 0) * extrude(profile, amount=fin_t)
        body += Rot(0, 0, a * 360 / P.drum_fin_count) * fin

    # Hub: down from the web, double-D bore opening at the bottom.
    hub = Pos(0, 0, -P.drum_hub_len / 2) * Cylinder(P.drum_hub_d / 2, P.drum_hub_len)
    # Double-D bore = cylinder clipped by a slab across the flats. Bore
    # opens at the hub's bottom face, drum_bore_depth deep.
    bore_r = (P.byj_shaft_d + P.drum_bore_clear) / 2
    flat_w = P.byj_flat_across + P.drum_bore_clear
    bore_z = -P.drum_hub_len + P.drum_bore_depth / 2
    hub -= Pos(0, 0, bore_z) * Cylinder(bore_r, P.drum_bore_depth) & Pos(
        0, 0, bore_z
    ) * Box(bore_r * 2, flat_w, P.drum_bore_depth)
    # lead-in chamfer around the bore mouth so the shaft self-centres on
    # insertion: the bore-opening edge loop on the hub's bottom face
    mouth = [
        e
        for e in hub.edges().group_by(Axis.Z)[0]
        if e.bounding_box().max.X < bore_r + 1
    ]
    hub = chamfer(mouth, P.drum_bore_chamfer)
    # outer rim of the bottom face: break the sharp edge
    rim = [
        e
        for e in hub.edges().group_by(Axis.Z)[0]
        if e.bounding_box().max.X > P.drum_hub_d / 2 - 1
    ]
    hub = chamfer(rim, P.drum_hub_edge_chamfer)
    body += hub

    # Soften the hard corner where each fin plate meets the hub wall:
    # fillet the vertical junction edges at the hub radius.
    hub_r = P.drum_hub_d / 2
    junction = [
        e
        for e in body.edges().filter_by(Axis.Z)
        if abs((e.center().X**2 + e.center().Y**2) ** 0.5 - hub_r) < 0.3
        and e.center().Z < -0.1
    ]
    body = fillet(junction, P.drum_fin_hub_fillet)

    # Homing magnet: boss under the web's solid 45-deg quadrant drops the
    # magnet drum_magnet_standoff toward the hall sensor; blind pocket
    # opens at the boss's bottom face (magnet axis perpendicular to the
    # web), sweeping over the sensor once per revolution.
    boss_d = P.drum_magnet_d + P.drum_magnet_clear + 3.0
    boss = Pos(0, 0, -P.drum_magnet_standoff / 2) * Cylinder(
        boss_d / 2, P.drum_magnet_standoff
    )
    pocket_h = P.drum_magnet_t + 0.3
    boss -= Pos(0, 0, -P.drum_magnet_standoff + pocket_h / 2) * Cylinder(
        (P.drum_magnet_d + P.drum_magnet_clear) / 2, pocket_h
    )
    body += Rot(0, 0, 45) * Pos(P.drum_magnet_r, 0, 0) * boss
    # Eject hole: poke a toothpick through from the web's top face to
    # push the magnet out of its blind pocket.
    body -= Rot(0, 0, 45) * Pos(P.drum_magnet_r, 0, 0) * Cylinder(
        P.drum_poke_d / 2, 4 * P.drum_magnet_standoff
    )
    return body


def drum_assembly():
    """Both parts mated in the drum frame: outer ring at z=0, inner disc
    seated on the barrel's open end, hub reaching down toward z=0."""
    return drum_outer() + drum_inner_mated()


def drum_inner_mated():
    """The inner disc in the drum frame (web on the barrel's open end)."""
    return Pos(0, 0, P.drum_ring_t + P.drum_barrel_len) * drum_inner()


def _pose(part):
    return Pos(P.mount_x, P.byj_shaft_y, P.drum_z0) * part


def posed_drum():
    """The assembled drum posed in unit coords on the motor shaft axis."""
    return _pose(drum_assembly())


def posed_drum_parts():
    """(outer, inner) posed separately in unit coords, for display."""
    return _pose(drum_outer()), _pose(drum_inner_mated())
