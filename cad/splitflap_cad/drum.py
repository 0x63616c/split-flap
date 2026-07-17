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
    Cone,
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

from .geo import polar, polar_locs, radial_plate, slot0_marker
from .params import P
from .select import (
    bottom_edges,
    diametral_edges_at_z,
    reach_over,
    reach_under,
    vertical_edges_near_radius,
)


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
    for c in polar(_slot_cutter(), P.drum_flap_count):
        part -= c
    return part


def _ring():
    """A flap ring: annulus with drum_flap_count elongated radial pin
    slots — pins pivot and get ~1mm radial float to self-align."""
    ring = Cylinder(P.drum_ring_od / 2, P.drum_ring_t) - Cylinder(
        P.drum_ring_id / 2, P.drum_ring_t * 2
    )
    return _cut_slots(Pos(0, 0, P.drum_ring_t / 2) * ring)


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

    def _lip_profile(z_lo, rib_h):
        return Polygon(
            (r_embed, z_butt),
            (P.drum_wall_r_in - rib_h, z_butt),
            (P.drum_wall_r_in - rib_h, z_lo + rib_h),
            (P.drum_wall_r_in, z_lo),
            (r_embed, z_lo),
            align=None,
        )

    body += revolve(Rot(90, 0, 0) * _lip_profile(z_ring, P.drum_guide_rib_h), Axis.Z)

    # Notches through the ring: one per fin, width = fin thickness +
    # clearance per side.
    # cutter stops flush at the wall face — overshooting radially dents
    # a step into the barrel wall behind the notch
    notch_x = (r_face - 0.5 + P.drum_wall_r_in) / 2
    notch_dx = P.drum_wall_r_in - (r_face - 0.5)
    for a, loc in enumerate(polar_locs(P.drum_fin_count)):
        fin_t = P.drum_fin_t_key if a == 0 else P.drum_fin_t
        body -= loc * Pos(notch_x, 0, (z_butt + z_ring) / 2) * Box(
            notch_dx,
            fin_t + 2 * P.drum_fin_clear,
            P.drum_guide_ring_len + 2 * P.drum_guide_rib_h + 1,
        )

    # Below the ring, rail pairs flank each notch down to drum_guide_len
    # so the fins stay side-supported over their whole travel; same
    # 45-deg ramp at the lower end. Rails reach deeper radially than the
    # ring (drum_guide_rail_h) to grab more of the fin's flank.
    z_bot = z_butt - P.drum_guide_len
    rib = radial_plate(_lip_profile(z_bot, P.drum_guide_rail_h), P.drum_guide_rib_w)
    for a, loc in enumerate(polar_locs(P.drum_fin_count)):
        fin_t = P.drum_fin_t_key if a == 0 else P.drum_fin_t
        gap = fin_t / 2 + P.drum_fin_clear
        for side in (+1, -1):
            body += loc * Pos(0, side * (gap + P.drum_guide_rib_w / 2), 0) * rib

    # Lock-screw rib: a wide rib inside the wall (solid web quadrant,
    # beside the 90-deg fin's rails), top flush with the butt joint —
    # the inner part's boss lands on it. An M3x3 heat-set insert
    # presses into the rib's top face; the screw drops in from the
    # drum's outer (web) face through the inner part and threads in.
    z_rib = z_butt  # flush with the lip / butt plane
    # The rib reaches inward only as far as the bore column needs
    # (bore edge + wall margin) — a flat vertical inner face, no point.
    # The 45-deg ramp underneath still originates at the (virtual)
    # drum_screw_rib_r_in so the bore keeps its floor; the wedge tip
    # inward of the truncation held nothing.
    r_rib_in = P.drum_screw_rib_r_in
    r_trunc = P.drum_screw_r - P.byj_insert_d / 2 - P.drum_screw_rib_bore_wall
    rib_prof = Polygon(
        (r_trunc, z_rib),
        (r_embed, z_rib),
        (r_embed, z_rib - (r_embed - r_rib_in)),
        (r_trunc, z_rib - (r_trunc - r_rib_in)),
        align=None,
    )
    screw_rib = radial_plate(rib_prof, P.drum_screw_boss_w)
    # Break the two sharp corners jutting into the drum: the vertical
    # edges of the inner face. The outer-face edges must stay sharp —
    # they sit just 0.2 into the wall, so a chamfer there opens a slit
    # between the rib and the wall face.
    screw_rib = chamfer(screw_rib.edges().filter_by(Axis.Z).sort_by(Axis.X)[:2], 0.6)
    # Two ribs on opposite quadrants (drum_screw_ang and +180): one M3
    # each, beside fin 0 and fin 180's rails — a bolt per side clamps
    # the butt joint shut evenly.
    # Insert bore in each rib top: ONE cylinder at insert diameter (same
    # idiom as the motor mount, unit.py) — insert seats in the top, the
    # screw tip runs on down the same bore. Depth = drum_screw_len minus
    # the inner-part stack past the butt plane, plus slack (0.5 free +
    # 0.25 the head sinks into the cone seat). Opens upward — no
    # overhang, no membrane, no step.
    bore_depth = P.drum_screw_len + 0.75 - (
        P.drum_ring_t - P.drum_screw_recess_t + P.drum_barrel_len_inner
    )
    for sa in (P.drum_screw_ang, P.drum_screw_ang + 180):
        body += Rot(0, 0, sa) * screw_rib
        body -= Rot(0, 0, sa) * Pos(
            P.drum_screw_r, 0, z_rib - bore_depth / 2
        ) * Cylinder(P.byj_insert_d / 2, bore_depth)

    # First-slot indicator: triangle debossed into the ring's outside
    # (bottom) face, on the key-notch line pointing at slot 0.
    body -= slot0_marker(P.drum_slot_r_in_inner - 0.5, 0, cut="up")
    return body


def drum_inner(shaft: str = "byj"):
    """Inner drum (short side): ring + web disc, shaft hub, two screw
    bosses, its share of the barrel wall. Own frame: web underside at
    z=0, hub and barrel pointing -Z (toward the motor once assembled).

    Everything is shared between motor variants except the hub bore:
    shaft="byj" -> double-D, drum_bore_depth deep (28BYJ 8mm shaft);
    shaft="nema" -> single-D, drum_bore_depth_nema deep (the pancake's
    20.5mm shaft parks its extra length in the deeper bore, so the drum
    sits at the same axial spot in both variants)."""
    # Ring + web are one 1.6 disc: full circle out to the ring OD, slots
    # in the ring band, four lightening holes in the web.
    body = Pos(0, 0, P.drum_ring_t / 2) * Cylinder(P.drum_ring_od / 2, P.drum_ring_t)
    # Elongated radial pin slots, matching the outer ring.
    body = _cut_slots(body)
    # Only 2 lightening windows: the 45-deg quadrant stays solid (homing
    # magnet + one lock screw), the opposite 225-deg quadrant stays solid
    # for the second lock screw. Pie-quadrant shaped: annular sector with
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
    for ang in (90, 270):  # windows at 135/315; 45 + 225 solid (both screws)
        body -= Rot(0, 0, ang) * cutter

    # First-slot indicator: triangle debossed into the web's outside
    # (top) face, on the key-fin line pointing at slot 0.
    body -= slot0_marker(P.drum_slot_r_in_inner - 0.5, P.drum_ring_t, cut="down")

    # This part's share of the barrel wall, reaching down to butt against
    # the outer part's share mid-drum.
    body += Pos(0, 0, -P.drum_barrel_len_inner) * _barrel(P.drum_barrel_len_inner)

    # Connector fins: thin radial plates from the hub outward, hanging
    # below the web. Fin-shaped profile: bottom edge slopes from shallow
    # at the hub to full depth at the rim, where the tips land in the
    # outer part's guide-ring slots. Outer edge is STEPPED: over this
    # part's own barrel length the fin reaches into the wall and fuses
    # with it (same part — strength, no clearance needed); past the butt
    # plane it steps back drum_fin_clear so the free length slides into
    # the outer part's notches and rails.
    fin_r_in = P.drum_hub_d / 2 - 1
    fin_r_out = P.drum_wall_r_in - P.drum_fin_clear
    fin_r_wall = P.drum_wall_r_in + 0.2  # embed into the own wall
    profile = Polygon(
        (fin_r_in, 0),
        (fin_r_wall, 0),
        (fin_r_wall, -P.drum_barrel_len_inner),
        (fin_r_out, -P.drum_barrel_len_inner),
        (fin_r_out, -P.drum_fin_len),
        (fin_r_in, -P.drum_fin_len_hub),
        align=None,
    )
    # round the tip corner (where the sloped bottom edge meets the rim)
    # so the fin docks into the guide channels easily
    profile = fillet(profile.vertices().sort_by(Axis.Y)[0], P.drum_fin_tip_fillet)
    # Fin 0 is thicker (the key): only fits channel 0, so there's one
    # assembly orientation.
    for a, loc in enumerate(polar_locs(P.drum_fin_count)):
        fin_t = P.drum_fin_t_key if a == 0 else P.drum_fin_t
        body += loc * radial_plate(profile, fin_t)

    # Hub: down from the web, shaft bore opening at the bottom.
    hub = Pos(0, 0, -P.drum_hub_len / 2) * Cylinder(P.drum_hub_d / 2, P.drum_hub_len)
    # Bore = cylinder clipped by a slab across the flat(s), opening at
    # the hub's bottom face. byj: slab centred = double-D. nema: one
    # flat — slab shifted so its far face is the flat plane, its near
    # face outside the bore circle.
    if shaft == "byj":
        shaft_d, flat_across, depth = P.byj_shaft_d, P.byj_flat_across, P.drum_bore_depth
    else:
        shaft_d, flat_across, depth = (
            P.motor_shaft_d,
            P.motor_flat_across,
            P.drum_bore_depth_nema,
        )
    bore_r = (shaft_d + P.drum_bore_clear) / 2
    flat_w = flat_across + P.drum_bore_clear
    slab_y = 0 if shaft == "byj" else flat_w / 2 - bore_r
    bore_z = -P.drum_hub_len + depth / 2
    hub -= Pos(0, 0, bore_z) * Cylinder(bore_r, depth) & Pos(
        0, slab_y, bore_z
    ) * Box(bore_r * 2, flat_w, depth)
    # lead-in chamfer around the bore mouth so the shaft self-centres on
    # insertion: the bore-opening edge loop on the hub's bottom face
    hub = chamfer(reach_under(bottom_edges(hub), bore_r + 1), P.drum_bore_chamfer)
    # outer rim of the bottom face: break the sharp edge
    hub = chamfer(
        reach_over(bottom_edges(hub), P.drum_hub_d / 2 - 1), P.drum_hub_edge_chamfer
    )
    body += hub

    # Reinforce the fin junctions in ONE fillet call so OCC blends the
    # shared corners (sequential fillets fail where they meet):
    # - vertical edges where each fin plate meets the hub wall
    # - the long radial roots where each fin face meets the web
    #   underside (straight z=0 edges within a fin half-thickness of a
    #   diametral plane are exactly those; window borders run
    #   drum_web_window_fin_gap further out, the barrel ring is curved)
    # (r_max = wall_r_in keeps the flap slots' near-diametral side edges
    # out in the ring band from being rounded — that explodes the mesh)
    junction = vertical_edges_near_radius(body, P.drum_hub_d / 2, z_below=-0.1)
    roots = diametral_edges_at_z(
        body,
        0,
        half_t=P.drum_fin_t_key / 2 + P.drum_fin_clear + 0.1,
        r_max=P.drum_wall_r_in,
    )
    body = fillet(junction + roots, P.drum_fin_hub_fillet)

    # Homing magnet: boss under the web's solid 45-deg quadrant drops the
    # magnet drum_magnet_standoff toward the hall sensor; blind pocket
    # opens at the boss's bottom face (magnet axis perpendicular to the
    # web), sweeping over the sensor once per revolution.
    boss_d = P.drum_magnet_d + P.drum_magnet_clear + 2 * P.drum_magnet_boss_wall
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
    # Lock-screw bosses: one per solid quadrant (drum_screw_ang and
    # +180), each hangs off the web underside beside a fin, lands on the
    # outer part's matching rib at the butt joint; its edge fuses into
    # this part's own barrel wall for strength. The M3 drops from the
    # web's outer face: head recess there (narrower than the boss, so the
    # seat is fully backed), clearance bore straight through web + boss,
    # threads into the rib's heat-set insert to clamp the parts shut.
    sboss = Pos(0, 0, -P.drum_barrel_len_inner / 2) * Cylinder(
        P.drum_screw_boss_d / 2, P.drum_barrel_len_inner
    )
    # rim break at the bottom face
    sboss = chamfer(sboss.edges().group_by(Axis.Z)[0], 0.5)
    bore_l = P.drum_ring_t + P.drum_barrel_len_inner + 1
    # Sloped seat: below the cylindrical recess the bottom is a 45-deg
    # cone tapering to the screw bore. The part prints web-face down, so
    # a flat recess bottom would be a ceiling bridged over air; the cone
    # self-supports. The button head (Ø5.7) bears on the cone's rim and
    # sinks ~0.25 below the cylinder's end.
    cone_h = (P.drum_screw_recess_d - P.screw_hole_d) / 2
    z_seat = P.drum_ring_t - P.drum_screw_recess_t  # cone top
    for sa in (P.drum_screw_ang, P.drum_screw_ang + 180):
        body += Rot(0, 0, sa) * Pos(P.drum_screw_r, 0, 0) * sboss
        body -= Rot(0, 0, sa) * Pos(
            P.drum_screw_r, 0, P.drum_ring_t + 0.5 - bore_l / 2
        ) * Cylinder(P.screw_hole_d / 2, bore_l)
        body -= Rot(0, 0, sa) * Pos(
            P.drum_screw_r, 0, P.drum_ring_t - P.drum_screw_recess_t / 2
        ) * Cylinder(P.drum_screw_recess_d / 2, P.drum_screw_recess_t)
        body -= Rot(0, 0, sa) * Pos(
            P.drum_screw_r, 0, z_seat - cone_h / 2
        ) * Cone(P.screw_hole_d / 2, P.drum_screw_recess_d / 2, cone_h)
    return body


def drum_assembly():
    """Both parts mated in the drum frame: outer ring at z=0, inner disc
    seated on the barrel's open end, hub reaching down toward z=0."""
    return drum_outer() + drum_inner_mated()


def drum_inner_mated(shaft: str = "byj"):
    """The inner disc in the drum frame (web on the barrel's open end)."""
    return Pos(0, 0, P.drum_ring_t + P.drum_barrel_len) * drum_inner(shaft)


def drum_inner_nema():
    """The NEMA-bore inner disc (see drum_inner)."""
    return drum_inner("nema")


def drum_inner_print():
    """drum_inner flipped for printing: its own frame hangs hub, barrel
    and fins into -Z (below the bed); flip so the web sits flat on the
    bed and the barrel points up."""
    return Rot(180, 0, 0) * drum_inner()


def drum_inner_nema_print():
    """drum_inner_nema flipped for printing (see drum_inner_print)."""
    return Rot(180, 0, 0) * drum_inner("nema")


def scene():
    from .viewer import Scene

    return (
        Scene()
        .add(drum_outer(), "drum_outer", "orange")
        .add(drum_inner(), "drum_inner", "steelblue", loc=Pos(90, 0, 0) * Rot(180, 0, 0))
    )


def nema_scene():
    """Same layout, NEMA-bore inner (open single-D; outer is shared)."""
    from .viewer import Scene

    return (
        Scene()
        .add(drum_outer(), "drum_outer", "orange")
        .add(
            drum_inner("nema"),
            "drum_inner_nema",
            "steelblue",
            loc=Pos(90, 0, 0) * Rot(180, 0, 0),
        )
    )


def posed_drum():
    """The assembled drum posed in unit coords on the motor shaft axis."""
    from .frames import DRUM_IN_UNIT

    return DRUM_IN_UNIT * drum_assembly()


def posed_drum_parts(shaft: str = "byj"):
    """(outer, inner) posed separately in unit coords, for display. The
    outer part is identical across motor variants; DRUM_IN_UNIT holds
    for both (the NEMA bore is deepened precisely so the drum sits at
    the same axial spot)."""
    from .frames import DRUM_IN_UNIT

    return (
        DRUM_IN_UNIT * Rot(0, 0, 180) * drum_outer(),
        DRUM_IN_UNIT * Rot(0, 0, 180) * drum_inner_mated(shaft),
    )
