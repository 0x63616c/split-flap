"""Single source of truth for every dimension. Millimetres.

Rule: raw measurements are named constants; anything positional is *derived*
from them (see `pin_y`). Change a base dim -> dependents follow. No magic
numbers in the part files — one blessed exception: cosmetic edge breaks
(chamfers/fillets <= 1mm that only knock a sharp corner off) may inline.

Most flap/drum numbers are PLACEHOLDERS until drum geometry is settled
(issue #7). They exist so the model renders and tests have something to
assert; treat them as TODO, not final.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    # --- flap card (measured off vendor Flap_blank.step; printed 1mm) ---
    # Local frame: x centred, y=0 at the pivot (bottom) edge. Flat side
    # tabs near the pivot edge are the pins that ride the drum's ring
    # holes; the top section widens to the same overall span.
    flap_w: float = 39.0          # card body width
    flap_w_over_pins: float = 43.0  # overall width over pin tabs / wings
    flap_h: float = 35.0          # card height
    flap_thick: float = 1.0       # printed card thickness
    flap_pin_y0: float = 1.2      # pin tab bottom edge, from card bottom
    flap_pin_h: float = 1.2       # pin tab height
    flap_wide_y0: float = 18.0    # top wide section starts here

    # --- flap glyphs (two-tone AMS inlay; docs/research/charset-artwork.md) ---
    # A character spans two flaps: top half on the FRONT of flap N, bottom
    # half on the BACK of flap N+1 rotated 180° about X. Artwork runs
    # flush to the card's pivot edge; the physical hinge gap is what
    # separates the halves on the display. Gap/keepout are scottbez1
    # starting values — PLACEHOLDERS until drum geometry pins them (#7).
    glyph_font: str = "GeistMono-SemiBold.ttf"  # file in cad/fonts/
    glyph_half_h: float = 24.5     # half-character cap height per flap (0.7 * flap_h)
    glyph_w_max: float = 33.0      # max glyph width; wider glyphs squeeze to fit
    glyph_gap_comp: float = 1.0    # half the physical hinge gap (preview pose only;
                                   # artwork always runs flush to the card edge)
    glyph_top_keepout: float = 3.7  # flap tip hidden behind the resting stack
    glyph_inlay_depth: float = 0.4  # white inlay depth per face (2 layers @ 0.2)

    # --- unit side plate (holds motor, wires, drum, hall sensor) ---
    # Module is assembled lying on its left side; this plate is the base.
    unit_plate_w: float = 95.0    # plate width
    unit_plate_h: float = 118.0   # plate height
    unit_plate_thick: float = 3.0  # plate thickness

    # back wall: runs the full long (Y) edge, outer face flush with the
    # plate edge. Height is measured from the plate BOTTOM (total 40mm),
    # so the part above the plate is derived.
    unit_wall_thick: float = 3.0   # back wall thickness
    unit_back_height: float = 53.0  # total height from plate bottom (matches vendor ref)

    # --- NEMA 14 pancake stepper (ordered: YEJMKJ 35x21mm 7Ncm 0.6A
    # bipolar, 1.8deg, 4-lead). Dims from the vendor's product drawing;
    # body length carries ±0.8 so MEASURE the real unit before printing
    # the bridge (wall height must match the actual body, or deck and
    # feet can't both seat — the joint is overconstrained by design).
    motor_body_w: float = 35.2      # square faceplate side (MAX)
    motor_body_len: float = 20.2    # body length, face to face (drawing
                                    # says ±0.8 — MEASURE the real one;
                                    # bridge wall height keys off this)
    motor_boss_d: float = 22.0      # pilot boss diameter (22.0 -0.05)
    motor_boss_len: float = 1.6     # boss protrusion past mounting face (drawing)
    motor_shaft_d: float = 5.0      # shaft diameter (5.0 -0.012)
    motor_shaft_len: float = 20.5   # shaft length past mounting face
    motor_flat_len: float = 16.5    # D-flat length, from shaft tip (drawing)
    motor_flat_across: float = 4.5  # remaining thickness across the flat (drawing)
    motor_hole_pitch: float = 26.0  # M3 mount holes, square pattern
    motor_screw_d: float = 3.0      # M3 nominal (tapped in motor)
    motor_screw_depth: float = 2.5  # tapped depth MIN (drawing) — shallow!
    pilot_clearance: float = 0.3  # radial gap around the Ø22 pilot boss
    screw_clearance: float = 0.2  # radial gap around M3 screws

    # --- NEMA harness (one printed bridge) ---
    # The pancake motor sits face-UP flat on the plate (no pocket), body
    # inside the drum barrel's interior, shaft on the same axis as the
    # 28BYJ variant (mount_x, byj_shaft_y). Its tapped holes open
    # upward, so a printed BRIDGE drops over it: ring deck on the face
    # (pilot bore + 4 M3 — the motor's own screws clamp deck to face),
    # a wall down each ±X body flat ending in a foot on the plate, each
    # held by an M3x8 from above into a flush heat-set insert. Ø7 well
    # channels through deck rim/wall give the bolts + hex key a
    # straight vertical drop onto spot-faced seats. Prints deck-down,
    # no overhangs (feet topped by 45° back wedges). The whole plan is
    # clipped to a cylinder about the shaft (nema_mount_r) so every
    # outer edge runs concentric with the drum.
    # Envelope (plate top z=3): body top/face z 24; flange top z 26 —
    # under the drum guide rails (sweep r>=23.15 from z~26.3; flange
    # kept inside r 22.9) and the web fins (bottom z 28.3 at the rim).
    # Everything inside the barrel wall sweep, r 26.5 about the shaft.
    nema_body_clear: float = 0.25    # gap per side around the body
    nema_leg_t: float = 3.0          # wall thickness along X
    nema_wall_w: float = 18.0        # wall width along Y — kept inside
                                     # the deck contour (corners r 22.7
                                     # < 22.9) so the arc clip never
                                     # tapers the wall ends to knife
                                     # edges; the deck carries the motor
                                     # screw seats, not the walls
    nema_flange_t: float = 3.5       # deck thickness: motor taps are
                                     # only 2.5 MIN deep, so M3x6 must
                                     # engage exactly 6 - 3.5 = 2.5.
                                     # Deck top clears the rails
                                     # radially (r 22.9 < sweep 23.15)
    nema_flange_in: float = 10.0     # flange inner edge |X - shaft|
                                     # (hole line 13 minus head + slack)
    nema_flange_r: float = 22.9      # flange plan clip radius — tighter
                                     # than the body clip: flange top z26
                                     # grazes the rail-sweep band (r
                                     # 23.15 from z 26.3), so it stays
                                     # inside it with 0.25
    nema_mount_r: float = 25.5       # wall/foot plan clip radius about
                                     # the shaft (barrel wall sweeps
                                     # r 26.5 from z 6.3; 1.0 gap)
    nema_foot_len: float = 4.5       # foot run along X past the wall
                                     # face; outer face lands ON the
                                     # clip arc at y0
    nema_foot_w: float = 12.0        # foot width along Y
    nema_foot_h: float = 5.5         # foot height (screw passes through:
                                     # M3x8 = 5.5 foot + 2.5 into the
                                     # flush insert, tip 0.5 shy of the
                                     # module's outer face)
    nema_screw_inset: float = 2.6    # foot screw axis inset from the
                                     # foot's outer face — as far out as
                                     # the button head seats (Ø5.7 lands
                                     # ~flush), so the hex key clears
                                     # the wall face (0.65)
    nema_seat_well_d: float = 7.0    # spot-faced well down the 45° back
                                     # wedge onto the foot top: flat
                                     # seat for the bolt head, hex key
                                     # drops straight in
    nema_insert_depth: float = 3.0   # M3x3 heat-set insert straight into
                                     # the plate from the top, flush —
                                     # the plate IS the boss; module
                                     # outer face stays untouched.
    # scene-mock bolt dims (button head M3, matching the assortment)
    bolt_head_d: float = 5.7
    bolt_head_h: float = 1.65
    nema_foot_bolt_l: float = 8.0    # M3x8 in the foot joint

    @property
    def nema_screw_x_off(self) -> float:
        """Foot screw axis |X - shaft|. Derived."""
        return (
            self.motor_body_w / 2 + self.nema_body_clear
            + self.nema_leg_t + self.nema_foot_len - self.nema_screw_inset
        )

    @property
    def nema_face_z(self) -> float:
        """Motor mounting face height: body flat on the plate. Derived."""
        return self.unit_plate_thick + self.motor_body_len

    @property
    def pilot_hole_d(self) -> float:
        """Through-hole for the motor's pilot boss. Derived."""
        return self.motor_boss_d + 2 * self.pilot_clearance

    @property
    def screw_hole_d(self) -> float:
        """M3 clearance hole diameter. Derived."""
        return self.motor_screw_d + 2 * self.screw_clearance

    # --- 28BYJ-48 stepper (vendor part, standard datasheet dims) ---
    # The ghost unit is designed around this motor: its 35mm ear pitch and
    # 8mm shaft offset match the vendor STEP's mount exactly.
    byj_can_d: float = 28.0       # motor can diameter
    byj_can_h: float = 19.0       # can depth, flange face to back (18 measured from ear underside + 1 flange)
    byj_flange_t: float = 1.0     # ear flange thickness
    byj_ear_pitch: float = 35.0   # ear hole spacing
    byj_ear_hole_d: float = 4.2   # ear hole diameter
    byj_ear_w: float = 7.0        # ear tab width
    byj_boss_d: float = 9.0       # pilot boss around the shaft
    byj_boss_h: float = 1.5       # boss protrusion past the flange
    byj_shaft_d: float = 5.0      # shaft diameter
    byj_shaft_len: float = 10.0   # shaft length past the flange face
    byj_flat_len: float = 6.0     # D-flat length, from shaft tip
    byj_flat_across: float = 3.0  # remaining thickness across the flat
    byj_shaft_offset: float = 8.0  # shaft axis offset from the can centre
    byj_wirebox_w: float = 14.75  # wire housing width (measured)
    byj_wirebox_d: float = 2.75   # wire housing radial protrusion (30.75mm outer span − 28 can dia)
    byj_wirebox_h: float = 16.5   # wire housing height (approx)

    # motor mount anchor: the CAN centre / ear line (vendor screw line).
    # The shaft is offset from here toward the drum zone (-Y).
    mount_x: float = 11.5         # can axis X (from vendor ref)
    mount_y: float = 2.0          # can axis Y = ear line (from vendor ref)

    # --- 28BYJ harness (support pad + screw towers) ---
    # Motor sits ears-up: can end rests on the pad, ears rest on the
    # tower tops, M4 screws through the ears clamp it down. The flange
    # height is the vendor's (sets shaft/drum position); everything under
    # the motor is derived from it.
    byj_flange_seat: float = 25.0  # ear underside, from plate bottom (vendor)
    byj_can_clear: float = 0.4     # radial clearance scooped around the can
    byj_pad_hole_r: float = 8.0    # hole through the pad centre
    # wire channel: enclosed tunnel INSIDE the plate, from the pad hole
    # out to the -X edge, so the motor wires leave the module flat.
    # Kingsman-style: skin-thick roof and floor (two print layers each)
    # with the cavity between, plus a narrower slit through the floor —
    # wires push in past the slit and the floor lips hold them there.
    wire_chan_w: float = 8.0       # cavity width
    wire_chan_skin: float = 0.4    # roof/floor thickness (2 x 0.2 layers)
    wire_chan_slit_w: float = 3.2  # push-in slit width through the floor
    wire_chan_flare: float = 3.0   # 45-deg mouth flare at the -X exit,
                                   # per side — opens the outlet so the
                                   # wires leave without a sharp corner
    byj_pad_slot_chamfer: float = 1.0  # edge break on the pad's wire-slot cuts
    # Screw towers (ours, remodeled from the vendor STEP): one curved
    # arm per motor ear. Footprint = rectangular bound ∩ the flap-swing
    # arc (about the shaft axis) − the can relief circle.
    tower_x_in_off: float = 12.5   # inner face |X - mount_x|
    tower_x_out_off: float = 24.5  # outer bound |X - mount_x|
    tower_y_lo: float = -11.9      # footprint Y bounds (absolute)
    tower_y_hi: float = 13.6
    tower_flap_relief_r: float = 24.0  # flap-swing clearance arc radius,
                                   # centred on the shaft axis (vendor)
    tower_corner_fillet: float = 1.0
    byj_insert_d: float = 4.2      # M3 heat-set insert bore
    byj_insert_depth: float = 8.0  # bore depth from the flange seat

    @property
    def byj_can_x(self) -> float:
        """Can axis X = mount anchor. Derived."""
        return self.mount_x

    @property
    def byj_can_y(self) -> float:
        """Can axis Y = mount anchor (ears are centred on the can). Derived."""
        return self.mount_y

    @property
    def byj_shaft_y(self) -> float:
        """Shaft axis Y: offset from the can toward the drum zone (-Y).
        Matches the vendor drum clearance centred at y=-6. Derived."""
        return self.mount_y - self.byj_shaft_offset

    @property
    def byj_flange_z(self) -> float:
        """Motor flange FACE height: ear underside (the seat) plus the
        flange thickness. This is where the motor model's z=0 poses."""
        return self.byj_flange_seat + self.byj_flange_t

    @property
    def byj_pad_h(self) -> float:
        """Support pad height: from plate top up to the can's end face,
        which hangs byj_can_h below the flange face. Derived."""
        return self.byj_flange_z - self.byj_can_h - self.unit_plate_thick

    # --- hall sensor mount ---
    # Sensor breakout (KY-003 style, measured off listing photos):
    # 18.83 x 15.0, two Ø3 mount holes on one 15.0 edge — 10.21 pitch,
    # hole line inset 2.53 from that edge. The TO-92 hall element hangs
    # off the SAME (hole-line) edge on bent legs, face up, its centre
    # ~4mm past the edge; the 3-pin header exits past that edge too, so
    # wires leave toward the back (-X) wall.
    # Pose: PCB flat in the free crescent between the motor can
    # (r 14.4 about the can axis) and the flap swing circle
    # (tower_flap_relief_r about the shaft) — long side across X,
    # centred on the shaft X line (best corner margins), hole/element
    # edge at -X. The element's legs bend sideways along the edge so the
    # element centre lands on the magnet sweep circle (drum_magnet_r).
    # The crescent is 17.6 deep for a 15-wide board: corner/can margins
    # are a few tenths — check both when touching anything here.
    # Support: one narrow post block spans both screw holes (M2
    # self-tap); the board cantilevers from it over the pad's wire-slot
    # corridor (wire_chan_w about mount_x, toward -Y), which must stay
    # open so the motor wires can slide under the board into the pad
    # hole.
    # Height cap: the outer drum's guide-rail bottoms sweep at
    # z = drum_z0 + ring_t + barrel_len_outer - guide_len ≈ 26.3 down to
    # r 22, so hall_seat + PCB must stay below that.
    hall_pcb_w: float = 18.83      # PCB size across X (long side)
    hall_pcb_l: float = 15.0       # PCB size along Y (hole-line side)
    hall_pcb_t: float = 1.6        # PCB thickness
    hall_hole_pitch: float = 10.21  # Ø3 mount holes, along Y
    hall_hole_inset: float = 2.53  # hole-line (-X) edge -> hole centres
    hall_hole_d: float = 3.0       # PCB mount hole (M3 screw)
    hall_elem_overhang: float = 4.0  # -X edge -> element centre (legs
                                   # bent to suit)
    hall_y: float = -20.4          # PCB centre Y: bottom corners inside
                                   # the flap circle, top edge off the can
    hall_seat: float = 23.5        # PCB seat height (raw; capped by the
                                   # guide rails, see note above)
    # element mock (TO-92 flat pack on bent legs, face up to the magnet)
    hall_elem_w: float = 4.0       # element body width (along Y)
    hall_elem_l: float = 3.0       # element body length (along legs, X)
    hall_elem_t: float = 1.5       # element body thickness
    hall_post_chamfer: float = 1.0  # edge break on the posts
    hall_post_w: float = 7.5       # screw post width across X
    hall_pilot_d: float = 1.6      # M2 self-tap pilot bore
    hall_pilot_depth: float = 8.0  # pilot depth from the post top

    @property
    def hall_post_l(self) -> float:
        """Screw post length along Y: one block spanning both holes plus
        post-width meat past each. Derived."""
        return self.hall_hole_pitch + self.hall_post_w

    @property
    def hall_pcb_x(self) -> float:
        """PCB centre X: on the shaft axis. Derived."""
        return self.mount_x

    @property
    def hall_x(self) -> float:
        """Hole line X: inset from the PCB's -X long edge. Derived."""
        return self.hall_pcb_x - self.hall_pcb_w / 2 + self.hall_hole_inset

    @property
    def hall_elem_x(self) -> float:
        """Hall element centre X: hall_elem_overhang past the -X edge.
        Derived."""
        return self.hall_pcb_x - self.hall_pcb_w / 2 - self.hall_elem_overhang

    @property
    def hall_elem_y(self) -> float:
        """Hall element centre Y: legs bend along the edge until the
        element sits on the magnet sweep circle (-Y branch). Follows
        drum_magnet_r. Derived."""
        dx = self.mount_x - self.hall_elem_x
        return self.byj_shaft_y - (self.drum_magnet_r**2 - dx**2) ** 0.5

    # --- drum (two parts: outer can + inner disc, measured off the
    # Kingsman FlapDrum{Outer,Inner}.stl) ---
    # Outer = pringles can: flap ring + its share of the barrel wall.
    # Inner = shorter side: ring/web disc + shaft hub + the rest of the
    # barrel, faces the motor. Parts join by radial fins on the inner
    # web dropping into a slotted guide ring inside the outer barrel.
    drum_ring_od: float = 69.3     # flap ring outer diameter (both rings)
    drum_ring_t: float = 1.6       # ring / web / lip thickness
    drum_flap_count: int = 52      # flap pin slots per ring (scottbez1-v2-size charset)
    drum_slot_w: float = 1.9       # slot width (tangential)
    drum_slot_r_out: float = 33.35   # slot outer reach (both rings)
    drum_slot_r_in_inner: float = 31.3   # slot inner reach, inner ring
    drum_wall_r_in: float = 26.5   # barrel wall inner radius
    drum_wall_r_out: float = 27.65  # barrel wall outer radius
    drum_barrel_len: float = 40.0  # total barrel length, ring to ring
    drum_barrel_len_inner: float = 8.0   # barrel share on the inner part;
                                   # the outer part carries the rest
    # Connector fins: thin radial plates on the inner web (hub to rim,
    # like impeller spokes) reaching into the drum; their tips slide into
    # axial guide-rail channels on the outer barrel wall, which index
    # rotation and align the parts.
    drum_fin_count: int = 4
    drum_fin_t: float = 2.0        # fin thickness
    drum_fin_t_key: float = 3.0    # thickness of fin 0 (the key): only
                                   # fits its own wide notch, so the
                                   # parts assemble one way only
    drum_fin_len: float = 18.0     # fin depth below the web, at the rim
    drum_fin_len_hub: float = 8.0  # fin depth at the hub end (bottom
                                   # edge slopes rim-deep to hub-shallow)
    drum_fin_clear: float = 0.2    # fin-to-wall / notch clearance
    drum_fin_tip_fillet: float = 1.0  # fin tip corner round (dock lead-in)
    drum_fin_hub_fillet: float = 0.8  # fillet where fins meet the hub
                                   # wall AND along the fin roots at the
                                   # web underside (one radius: OCC needs
                                   # a single fillet call to blend the
                                   # shared corners)
    drum_guide_ring_len: float = 3.0  # full guide ring (lip) length: just
                                   # enough to block an off-angle drum —
                                   # fins can ONLY enter at the notches,
                                   # so rotation is indexed at any angle
    drum_guide_len: float = 12.0   # total fin support length down from
                                   # the butt joint: below the ring,
                                   # rail pairs flank each notch so the
                                   # fins stay side-supported
    drum_guide_rib_w: float = 1.5  # rail width (tangential)
    drum_guide_rib_h: float = 1.5  # guide ring protrusion off the wall
                                   # (radial); kept short — deeper and it
                                   # hits the magnet boss (sweeps r 22.1)
    drum_guide_rail_h: float = 4.5  # rail protrusion off the wall
                                   # (radial): 3x the ring, grabs more of
                                   # the fin's flank toward the centre;
                                   # rails sit at the fin angles so the
                                   # 45-deg magnet boss clears them
    drum_hub_d: float = 16.8       # shaft hub outer diameter
    drum_hub_len: float = 15.8     # hub length below the web underside
    drum_bore_depth: float = 9.0   # double-D shaft bore depth (28BYJ)
    drum_bore_depth_nema: float = 17.5  # single-D bore, NEMA variant:
                                   # >= hub_len + ring_t so it punches
                                   # OPEN through hub and web — the
                                   # shaft can slide in as deep as
                                   # needed and the drum still sits at
                                   # the same axial spot as the 28BYJ
                                   # build. Bore must only see the
                                   # shaft's flat zone: flat >= ~14
                                   # long — VERIFY with motor in hand.
    drum_bore_clear: float = 0.2   # shaft bore clearance (dia and flats)
    drum_flat_clear: float = 0.5   # hub bore bottom above the shaft's
                                   # round section (bore is double-D; only
                                   # the flat zone may enter it)
    drum_bore_chamfer: float = 0.5  # lead-in chamfer at the bore mouth
    drum_hub_edge_chamfer: float = 0.8  # hub bottom outer rim chamfer
    # Web lightening windows: pie-quadrant shaped (x3; the magnet
    # quadrant stays solid), uniform margins to hub/wall and fins.
    drum_web_window_edge: float = 2.0   # radial margin to hub / barrel wall
    drum_web_window_fin_gap: float = 3.0  # margin to the fin faces
    drum_web_window_fillet: float = 1.5   # window corner round
    # Homing magnet: pocket in a boss under the inner web's solid
    # quadrant; sweeps over the hall sensor once per revolution.
    drum_magnet_d: float = 6.0     # magnet diameter (rhinocats 6x3mm)
    drum_magnet_t: float = 3.0     # magnet thickness
    drum_magnet_r: float = 20.5    # boss centre radius; hall element
                                   # must sit at this radius. Max at this
                                   # standoff: boss bottom rides inside
                                   # the outer part's guide-ring band
                                   # (face r 25.0), so boss outer edge
                                   # must stay <= 24.6
    drum_magnet_clear: float = 0.2  # hole diametral clearance
    drum_magnet_boss_wall: float = 1.0  # boss wall around the pocket,
                                   # per side; thin so the boss squeezes
                                   # under the guide ring
    drum_magnet_standoff: float = 13.0  # boss under the web dropping the
                                   # magnet toward the hall sensor
    drum_poke_d: float = 2.2       # magnet eject hole (toothpick) through
                                   # the web into the pocket's blind end
    # Lock screw: one M3 down from the drum's outer (web) face clamps
    # the two parts together so they can't pull apart. Boss hangs off
    # the inner web (solid quadrant, beside the 90-deg fin's rails) and
    # lands on a rib inside the outer wall at the butt joint; the screw
    # drops through a clearance bore in web + boss into an M3x3
    # heat-set insert pressed into the rib's top face. Head sits in a
    # recess in the web's outer face — the recess is narrower than the
    # boss, so the seat is backed by the full boss and the web isn't
    # effectively thinned. Rib top is flush with the butt plane (user
    # pick over a preload gap), so the boss bears directly on it.
    # Clearance box (screw sits between magnet boss @45 and the key
    # fin @0; exact centre 22.5 kisses the magnet boss, so it's nudged
    # 1.5 deg finward): rib flank -> magnet boss 0.5, screw boss ->
    # magnet boss ~0.45 (fatter and they'd merge), rib corner clears
    # the key-fin rails by ~1mm,
    # rib base ≈ drum z 21.4 clears the hall board sweep (board top
    # unit z 25.1 ≈ drum z 20.4, and the board sits at ~270 deg anyway).
    drum_screw_ang: float = 21.0   # bore axis angle from the key fin
    drum_screw_r: float = 22.75    # bore axis radius
    drum_screw_boss_d: float = 9.4  # boss dia; edge (r 27.45) reaches
                                   # past the wall face and fuses into
                                   # the inner part's own barrel wall
                                   # for strength (stays inside r_out).
                                   # Wall around the Ø6.2 recess = 1.6.
    drum_screw_boss_w: float = 7.5  # rib width (tangential)
    drum_screw_rib_r_in: float = 14.5  # rib inner radius: deep enough
                                   # that the single insert/tip bore
                                   # keeps ~1mm wall above the 45-deg
                                   # base ramp
    drum_screw_rib_bore_wall: float = 1.0  # wall kept around the bore at
                                   # the rib's flat inner face — the rib
                                   # is truncated there (the wedge tip
                                   # inward of the bore held nothing)
    drum_screw_len: float = 12.0   # M3x12 button head
    drum_screw_recess_d: float = 6.2  # head recess dia (button head
                                   # Ø5.7); head (h 1.65) sits fully
                                   # below the web face
    drum_screw_recess_t: float = 2.0  # head recess depth (cylindrical
                                   # part); below it the seat is a 45-deg
                                   # cone down to the screw bore, so the
                                   # print (web-face down) has no flat
                                   # ceiling over air and the recess wall
                                   # is backed by the Ø9 boss
    # First-slot indicator: debossed triangle next to flap slot 0 (the
    # slot on the key fin / key notch line) on both parts' outside faces.
    drum_mark_depth: float = 0.6
    drum_mark_len: float = 3.0     # triangle length (radial)
    drum_mark_w: float = 3.0       # triangle base width (tangential)

    # --- flap-loading holder (jig; PROTOTYPE) ---
    # A ring that slips around the drum's flap ring, with one radial SLOT
    # per flap position cut into its top face. Each flap drops edge-first
    # into the slot aligned with its drum slot, standing upright so it
    # can't flop while you thread the side-pins in and load the rest.
    # Slot plane is radial (flap faces tangentially, like on the drum).
    holder_clear: float = 0.6      # radial slip clearance over the drum ring OD
    holder_ring_w: float = 22.0    # ring radial width (holds the slots)
    holder_slot_depth: float = 6.0  # how deep a flap edge drops in
    holder_slot_floor: float = 3.0  # material left under a slot
    holder_slot_clear: float = 0.4  # slot width over flap thickness (slip fit)
    # slots run the full ring width, bore to OD, open at both ends
    holder_rim_w: float = 2.0      # bottom rim: inward flange the drum
                                   # ring rests on; rim height = the slot
                                   # floor, so the drum ring underside
                                   # sits flush with the slot floors

    @property
    def holder_ring_id(self) -> float:
        """Bore that slips over the drum flap ring. Derived."""
        return self.drum_ring_od + 2 * self.holder_clear

    @property
    def holder_ring_t(self) -> float:
        """Ring thickness = slot depth + floor beneath it. Derived."""
        return self.holder_slot_depth + self.holder_slot_floor

    @property
    def holder_slot_w(self) -> float:
        """Slot width = flap thickness + slip clearance. Derived."""
        return self.flap_thick + self.holder_slot_clear

    @property
    def drum_barrel_len_outer(self) -> float:
        """Barrel share on the outer part. Derived."""
        return self.drum_barrel_len - self.drum_barrel_len_inner

    @property
    def drum_ring_id(self) -> float:
        """Flap ring inner diameter: flush with the barrel wall's inner
        face (vendor part had it at the wall's OUTER face, leaving a
        1.15 step). Derived."""
        return 2 * self.drum_wall_r_in

    @property
    def drum_width(self) -> float:
        """Assembled drum width: outer ring + barrel + inner ring seated
        on the lip. Derived."""
        return self.drum_ring_t + self.drum_barrel_len + self.drum_ring_t

    @property
    def drum_hub_bottom(self) -> float:
        """Hub underside in the drum frame: web underside minus hub
        length. Derived."""
        return self.drum_ring_t + self.drum_barrel_len - self.drum_hub_len

    @property
    def drum_z0(self) -> float:
        """Outer ring underside height in unit coords: positioned so the
        hub's double-D bore only ever sees the shaft's D-flat zone (the
        round section below would jam it). Derived."""
        flat_start = self.byj_flange_z + self.byj_shaft_len - self.byj_flat_len
        return flat_start + self.drum_flat_clear - self.drum_hub_bottom

    # flap stop rod: free-standing pillar at the front (+Y) edge; the top
    # flap rests against it. Position/size measured off the vendor STEP.
    rod_r: float = 3.9            # rod radius
    rod_x: float = 19.89          # rod axis X
    rod_y: float = 55.1           # rod axis Y (tangent to the +Y plate edge)

    # flap guard: thin angled wall hugging the front (+X/-Y) plate corner,
    # keeps the flaps from falling forward. Constant cross-section prism,
    # plate top to wall top. Profile points measured off the vendor STEP,
    # expressed relative to the plate corner (dx from +X edge, dy from -Y
    # edge) so the guard follows the plate if it resizes.
    guard_profile: tuple = (
        (0.0, 0.0),        # plate corner
        (-11.83, 0.0),     # run along the front edge
        (-11.83, 2.0),     # inner face start
        (-6.8, 6.22),      # diagonal up
        (-3.8, 6.22),      # notch flat
        (-1.98, 13.41),    # diagonal continues
        (-1.6, 19.0),      # inner end
        (0.0, 19.0),       # back to the +X edge
    )

    # front lip: short wall on the front (+X) edge at the bottom (+Y)
    # corner — mirrors the guard's front blade at the other end of the
    # flap opening, frames the bottom flap. Same thickness as the blade.
    unit_front_lip: float = 5.0    # lip run along the +Y edge

    unit_base_chamfer: float = 2.0  # 45° wedge where the plate top meets
                                    # the wall inner faces (inside corners)

    @property
    def unit_top_thick(self) -> float:
        """Top (-Y) wall thickness: matches the guard's front blade,
        which is the profile's second point's dy. Derived."""
        return self.guard_profile[2][1]

    # two rectangular windows cut into the back wall, [][] side by side,
    # 5mm frame left at every edge and between them
    unit_window_margin: float = 8.0
    unit_window_chamfer: float = 3.75  # 45° corner cut on window outlines
    plate_web: float = 4.0  # min web between a plate window and any feature

    # screw-tower complex Y extent (bounds the plate windows around the
    # tower zone; the towers themselves are motor_towers in unit.py)
    tower_zone_y: float = 0.8        # zone centre
    tower_zone_half_y: float = 13.25  # zone half-extent

    # --- iPad wall mount (side quest — not part of the split-flap) ---
    # iPad on a magnetic swivel mount whose flat-iron bar ends in a
    # 50 x 75 x 5 plate that sits 16 deg off the wall plane by default.
    # A printed bracket screws to drywall and swallows the bar's wall
    # end in an angled pocket; the bar gets epoxied in. iPad dims are
    # an 11" iPad Pro (M4) PLACEHOLDER — measure the real device.
    ipad_w: float = 249.7          # landscape width
    ipad_h: float = 177.5          # landscape height
    ipad_thick: float = 5.3
    ibar_w: float = 50.0           # bar plate width
    ibar_len: float = 75.0         # bar plate length
    ibar_thick: float = 5.0
    ipad_gap: float = 14.0         # bar front face -> iPad back (rigid
                                   # mount stack; swivel locked)
    ibar_tilt_deg: float = 0.0     # bar plane off the wall (pocket sets
                                   # this; iPad swivel compensates)
    ibkt_embed: float = 45.0       # bar length swallowed by the pocket
    ibkt_wall: float = 4.0         # printed wall around the pocket
    ibkt_back_wall: float = 1.5    # printed skin between pocket and wall
                                   # face — thin is fine, drywall backs it
    ibkt_clear: float = 0.15       # pocket gap per face — snug for screw-lock
    ibkt_plate_thick: float = 6.0  # screw-tab base plate thickness
    ibkt_tab_w: float = 16.0       # screw tab width per side
    ibkt_screw_d: float = 4.5      # drywall screw shank clearance
    ibkt_screw_head_d: float = 9.0  # pan-head counterbore diameter
    ibkt_screw_head_depth: float = 4.0  # heads fully sunk
    ibkt_nose_r: float = 3.5       # top-front edge round (iPad swings past
                                   # here) — must stay < ibkt_wall
    ibkt_lid_t: float = 6.0        # two-piece lid thickness (leaves 2mm
                                   # web under the 4mm head recesses)

    @property
    def unit_back_rise(self) -> float:
        """Back wall height above the plate top. Derived, not raw."""
        return self.unit_back_height - self.unit_plate_thick

    @property
    def unit_window_w(self) -> float:
        """Window width along Y: wall length minus 3 margins, halved."""
        return (self.unit_plate_h - 3 * self.unit_window_margin) / 2

    @property
    def unit_window_h(self) -> float:
        """Window height along Z: wall rise minus top+bottom margins."""
        return self.unit_back_rise - 2 * self.unit_window_margin

    @property
    def unit_cap_window_w(self) -> float:
        """Top/bottom wall window width along X: wall length minus 3
        margins, halved (same [][] scheme as the back wall)."""
        return (self.unit_plate_w - 3 * self.unit_window_margin) / 2

    @property
    def flap_pin_w(self) -> float:
        """Pin tab reach past the card body, per side. Derived."""
        return (self.flap_w_over_pins - self.flap_w) / 2


P = Params()
