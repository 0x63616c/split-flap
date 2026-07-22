"""Single source of truth for every dimension. Millimetres.

Rule: raw measurements are named constants; anything positional is *derived*
from them (see `pin_y`). Change a base dim -> dependents follow. No magic
numbers in the part files — one blessed exception: cosmetic edge breaks
(chamfers/fillets <= 1mm that only knock a sharp corner off) may inline.

Most flap/drum numbers are PLACEHOLDERS until drum geometry is settled
(issue #7). They exist so the model renders and tests have something to
assert; treat them as TODO, not final.
"""

import math
from dataclasses import dataclass

IN = 25.4  # mm per inch — imperial inputs convert HERE, never downstream
FT = 12 * IN


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

    # --- interconnect fins (5 tabs outboard of the back wall) ---
    # Five disconnected tabs, no frame between them: 4 corner tabs (a flat
    # pair on the z=0 mating face, a ramped pair on z=53) plus one stacking
    # tab per +-Y edge on the y=+-59 faces. Each carries one M3 joint.
    #
    # The screw axes and the mating faces they open onto are the INTERFACE
    # — they decide whether two modules bolt together, so they never get
    # rounded. Everything else is ours to draw. fin_depth doubles as the
    # corner tabs' Y width, which puts every hole dead-centre in an 8.78
    # square footprint.
    #
    # Modules are identical prints, so a site cannot be both halves of a
    # joint: the pattern is ANTISYMMETRIC. The z=0 face and the y=-59 face
    # take the screw (clearance + counterbore); the z=53 face and the y=+59
    # face take the heat-set insert. A unit stacked on another always
    # presents z=0 to a z=53, and +59 to a -59, so screw always meets
    # insert whichever way round the pair goes.
    fin_depth: float = 8.78        # how far the tabs stand off the wall face
    fin_top_tab_h: float = 10.0    # top corner tab height at the wall face;
                                   # ramps down to fin_flat_t at the outer edge
    fin_stack_z_top: float = 30.5  # stack tab top face
    fin_stack_h: float = 14.0469   # stack tab height at the wall face; the
                                   # ramp below it is 45 deg (= fin_depth run)
    # M3x6 button head into an M3x3 heat-set insert. Both halves of the
    # joint have to fit in the SAME tab thickness (the tabs are one
    # geometry, only the cuts differ), and they balance at 5.0:
    #   insert side: 4.0 bore + 1.0 floor
    #   screw side:  2.0 counterbore + 3.0 shank, then 3.0 into the insert
    fin_insert_d: float = 4.2      # M3 heat-set insert bore (repo idiom)
    fin_insert_len: float = 3.0    # M3x3 heat-set, flush with the face
    fin_insert_depth: float = 4.0  # blind bore: the insert + screw-tip room
    fin_joint_floor: float = 1.0   # solid material behind the insert bore
    fin_cbore_d: float = 6.0       # button head 5.7 + clearance
    fin_cbore_depth: float = 2.0   # head 1.65 sunk 0.35 below the tab's
                                   # FAR face. Not the mating face: that
                                   # one is pressed against the
                                   # neighbour, so a head sunk there
                                   # would be sealed inside the joint
                                   # line with no way to turn it. The
                                   # screw goes in from outside.
    fin_screw_len: float = 6.0     # M3x6 = 3.0 shank + 3.0 insert engagement

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
    # The pancake motor sits face-UP on the plate, sunk nema_recess into
    # a pocket that also locates it laterally (the bridge walls used to
    # do that alone), body inside the drum barrel's interior, shaft on
    # the same axis as the 28BYJ variant (mount_x, byj_shaft_y). Its
    # tapped holes open upward, so a printed BRIDGE drops over it: ring deck
    # (pilot bore + 4 M3 — the motor's own screws clamp deck to face),
    # a wall down each ±X body flat ending in a foot on the plate, each
    # held by an M3x8 from above into a flush heat-set insert. Ø7 well
    # channels through deck rim/wall give the bolts + hex key a
    # straight vertical drop onto spot-faced seats. Prints deck-down,
    # no overhangs (feet topped by 45° back wedges). The whole plan is
    # clipped to ONE cylinder about the shaft (nema_mount_r) — deck, legs
    # and feet all share it, so the plan is a single arc with no ledge
    # and no lens-tip points where a wider leg overhung a narrower deck.
    # Envelope (plate top z=3): motor face z 22.8 (recessed); deck top z
    # 25.43, which is what lets the deck out to r 25.5 — the drum guide
    # rails only sweep r>=23.15 from z 26.3, so at 25.43 the deck passes
    # under them with 0.87 to spare, and stays inside the barrel wall
    # sweep (r 26.5). The four screw bosses do reach 26.3, but they sit
    # at r 18.4 (hole pitch 26 diagonal /2), nowhere near the rails.
    # Web fins bottom out at z 28.3 at the rim, magnet boss face at
    # 28.96 — the hall head lives in that gap, on the deck top.
    nema_body_clear: float = 0.25    # gap per side around the body
    nema_recess: float = 0.4         # how far the body sinks into the
                                     # plate. Locates the motor laterally
                                     # and drops the whole bridge with it
                                     # (everything keys off nema_face_z)
    nema_recess_clear: float = 0.3   # pocket oversize per side on the
                                     # body square — print tolerance, the
                                     # pocket locates, it does not press
    nema_leg_t: float = 3.0          # wall thickness along X
    nema_flange_t: float = 3.5       # deck thickness, flat — no local
                                     # bosses. The motor taps are only
                                     # 2.5 MIN deep, so an M3x6 engages
                                     # exactly 6 - 3.5 = 2.5; thinning
                                     # the deck would make the screw
                                     # bottom out before it clamped.
    # Wire route. The pancake's leads leave the body edge flush, so the
    # motor is rotated to present them at -Y — the only free azimuth,
    # since the bridge legs and feet own +-X out to r 25.35. The buried
    # channel centreline has to clear the legs' widest Y reach (18.2
    # about the shaft, at the leg's inner face) plus half the channel
    # width and a margin.
    nema_wire_y: float = -29.5       # buried channel centreline
    nema_wire_entry_bite: float = 1.0  # how far the open feed trench
                                     # reaches back UNDER the body edge,
                                     # so the leads turn down instead of
                                     # being pinched at the corner
    nema_wire_entry_w: float = 16.0  # feed trench width — wider than the
                                     # buried channel it feeds. Both the
                                     # motor leads and the hall leads land
                                     # in here, so it is sized to swallow
                                     # two bundles side by side, not to
                                     # hold one. Sized for HOUSINGS, not
                                     # bare wire: a 4-pin Dupont (10.2)
                                     # beside a 3-pin (7.6) is 17.8, so
                                     # they go in staggered, not abreast —
                                     # 11.0 could not pass either one
                                     # without stripping the crimp.
                                     # Clear either way: the bridge feet
                                     # stop at y -17.5 and this trench
                                     # starts at -22.6; the legs only
                                     # exist at |dx| > 17.6 from the shaft
                                     # and this reaches 8.0
    # --- NEMA homing: bare hall head on the deck top ---
    # No PCB in this variant — a bare TO-92 head drops into a pocket in
    # the bridge deck's top face, on the drum's magnet sweep circle. The
    # deck is a full disc over r <= mount_r, so it is the only solid
    # thing that reaches the sweep; a post up from the plate cannot,
    # the deck is in the way. Magnet boss face sits at z 28.96 and the
    # deck top at 25.43, so the head's 1.5 body leaves a ~2.0 air gap.
    nema_hall_az: float = -90.0      # azimuth about the shaft, degrees
                                     # (-90 = -Y, same side as the wires)
    nema_hall_pocket_w: float = 5.0  # across the head
    nema_hall_pocket_l: float = 4.0  # along the leads
    nema_hall_pocket_d: float = 1.5  # sunk the head's full body depth, so
                                     # it seats flush with the deck top
                                     # instead of perching on it. THIS is
                                     # the air-gap knob: deeper = bigger
                                     # gap = weaker signal. Flush leaves
                                     # 2.66 to the magnet face. Bench-
                                     # verify with the real magnet before
                                     # trusting it.
    # Leads drop straight DOWN through the deck, they do not run out to
    # the rim: the deck edge is r 25.5 and the barrel wall sweeps 26.5,
    # so a rim exit would pinch the wires against the turning drum in a
    # 1.0 gap. The hole sits at the sweep radius, offset tangentially
    # from the pocket — outboard of it would leave only 0.7 of rim wall,
    # and inboard of r 17.6 is the motor body's top face, blocked. At
    # the sweep radius there is open air all the way down to the plate
    # (the legs are +-X only), so the leads fall clear to the trench.
    # The hole OVERLAPS the pocket — one connected cavity, so the leads
    # bend from the head straight down without threading a separate
    # opening. Offset 9 deg at r 20.5 is a 3.22 arc, against a 2.5 + 2.25
    # half-width sum, so they merge with ~1.5 to spare.
    nema_hall_lead_d: float = 4.5    # lead hole through the deck
    nema_hall_lead_az_off: float = 9.0  # degrees from the pocket centre
    nema_mount_r: float = 25.5       # wall/foot plan clip radius about
                                     # the shaft (barrel wall sweeps
                                     # r 26.5 from z 6.3; 1.0 gap)
    nema_foot_len: float = 4.5       # foot run along X past the wall
                                     # face; outer face lands ON the
                                     # clip arc at y0
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
    def fin_flat_t(self) -> float:
        """Tab thickness — every tab is at least this. One thickness has
        to serve both halves of the joint, so it's whichever half needs
        more: insert bore + floor, or counterbore + shank. Derived."""
        return max(
            self.fin_insert_depth + self.fin_joint_floor,
            self.fin_cbore_depth + self.fin_shank_len,
        )

    @property
    def fin_shank_len(self) -> float:
        """How much screw is left to cross the clearance tab once the
        insert has its engagement. Derived."""
        return self.fin_screw_len - self.fin_insert_len

    @property
    def fin_wall_face(self) -> float:
        """Back wall outer face — where the fins root. Derived."""
        return -self.unit_plate_w / 2

    @property
    def fin_x_out(self) -> float:
        """Fin outer face, the module's most -X surface. Derived."""
        return self.fin_wall_face - self.fin_depth

    @property
    def fin_hole_x(self) -> float:
        """Screw axis X, shared by all five tabs — centred across the
        fin depth. INTERFACE: mates against the neighbour. Derived."""
        return self.fin_wall_face - self.fin_depth / 2

    @property
    def fin_hole_y(self) -> float:
        """Corner screw axis |Y| — centred across the corner tabs' Y
        width. INTERFACE. Derived."""
        return self.unit_plate_h / 2 - self.fin_depth / 2

    @property
    def fin_stack_hole_z(self) -> float:
        """Stack screw axis Z — mid back height, so a stacked pair meets
        symmetrically. INTERFACE. Derived."""
        return self.unit_back_height / 2

    @property
    def nema_screw_x_off(self) -> float:
        """Foot screw axis |X - shaft|. Derived."""
        return (
            self.motor_body_w / 2 + self.nema_body_clear
            + self.nema_leg_t + self.nema_foot_len - self.nema_screw_inset
        )

    @property
    def nema_face_z(self) -> float:
        """Motor mounting face height: body seated in the plate pocket,
        so nema_recess lower than a body sat flat on top. Every bridge
        dimension keys off this, so the recess propagates on its own.
        Derived."""
        return self.unit_plate_thick + self.motor_body_len - self.nema_recess

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
    # heat-set inserts); the board cantilevers from it over the pad's wire-slot
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
    hall_insert_d: float = 2.9     # M2 heat-set insert bore — insert is
                                   # 3.0 OD x 3.0 tall, 0.1 undersize so
                                   # the melt grips
    hall_insert_depth: float = 8.0  # bore depth from the post top: 3 of
                                    # insert + screw-tip clearance

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
    drum_bore_clear: float = 0.25  # shaft bore clearance (dia and flats).
                                   # 0.2 pressed on but fought back; this
                                   # is one printer-noise step looser, no
                                   # more — the fit must stay a press.
    drum_bore_vent_d: float = 2.0  # coaxial vent from the bore floor up
                                   # through web top face. The byj bore is
                                   # blind (depth < hub_len + ring_t), so
                                   # without this the shaft pistons against
                                   # trapped air. NEMA bore is already
                                   # through, so the cut is a no-op there.
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
    ibkt_tab_w: float = 16.0       # screw tab width per side
    ibkt_screw_d: float = 4.5      # drywall screw shank clearance
    ibkt_screw_head_d: float = 9.0  # pan-head counterbore diameter
    ibkt_screw_head_depth: float = 4.0  # heads fully sunk
    ibkt_lid_t: float = 6.0        # two-piece lid thickness (leaves 2mm
                                   # web under the 4mm head recesses)

    # --- USB grommet (plugs the 38mm drilled USB-cable hole) ---
    ugrom_barrel_d: float = 37.75  # barrel OD — near-net in the 38mm
                                   # bore (v1 37.0 test-fit loose)
    ugrom_barrel_l: float = 15.0   # through 1/2" drywall + a little proud
    ugrom_barrel_wall: float = 2.0  # hollow barrel — a ring, not a slug
    ugrom_flange_d: float = 46.0   # face flange OD — 4mm cover past the hole
    ugrom_flange_t: float = 2.0
    ugrom_slot_w: float = 11.0     # USB-C-shaped stadium slot: the molded
    ugrom_slot_h: float = 6.5      # plug threads straight through, no slit
    ugrom_rib_n: int = 4           # rib rings gripping the gypsum
    ugrom_rib_proud: float = 1.0   # crest past barrel OD — 0.75/side bite
    ugrom_rib_l: float = 2.5       # ramp length; step faces the flange

    # --- P2S poop bucket (side quest — Bambu P2S waste-chute catcher) ---
    # Remodel of a downloaded vase-mode bucket, enlarged. Solid body;
    # the slicer's spiral-vase mode hollows it (outer contour only), so
    # internal geometry is irrelevant — every surface slope stays
    # <= 45 deg so the single wall always lands on the layer below.
    # Local frame: X left-right (facing the logo: +X = viewer's right,
    # the cramped side), Y=0 at the printer-side face (bucket extends
    # -Y, spout +Y over the chute), Z=0 at the bed. Chute-fit geometry
    # (spout, notch, body width at the top) is measured off the
    # original mesh — don't tweak without a test fit.
    pb_h: float = 187.0            # overall height (unchanged)
    pb_body_w: float = 80.0        # original body width — the top must
                                   # keep this to fit around the chute
    pb_body_d: float = 50.0        # original body depth (measured)
    pb_d: float = 75.0             # new depth: 1.5x toward the wall
    pb_ext_l: float = 80.0         # left wing reach past the body (roomy side)
    pb_ext_r: float = 19.05        # right wing reach — old edge + 1in,
                                   # then trimmed 25% (space check)
    pb_wing_top_l: float = 163.5   # left wing chamfer meets the body here
    pb_notch_z: float = 140.0      # notch ramp base = right wing top (45 deg
                                   # up-inward from here, measured)
    pb_notch_x: float = 20.0       # wall position left of the chute door
    pb_corner_r: float = 3.0       # vertical corner rounds (measured)
    pb_spout_x0: float = -33.75    # spout tube left face (measured)
    pb_spout_x1: float = 13.75     # spout tube right face (measured)
    pb_spout_reach: float = 28.0   # spout past the printer-side face at
                                   # the top rim
    pb_spout_z0: float = 160.0     # spout crosses the printer-side face
                                   # here — slant is 28 over 27 (46 deg,
                                   # measured; still vase-printable)
    pb_text_h: float = 15.0        # engraved P2S logo cap height
    pb_text_depth: float = 0.4     # engrave depth (measured)
    pb_text_z: float = 94.5        # logo centreline height
    pb_tag_h: float = 8.0          # maker-tag cap height (printer-side face)

    # --- mirror backlight (side quest — arched hall mirror halo) ---
    # Printed spacers screw to the wall and hold the mirror off it; a Hue
    # Solo lightstrip lies in a groove on their OUTER face, firing radially
    # outward so the light escapes the wall/mirror gap. Mirror inputs are
    # the three imperial numbers off the tape measure; the arch radius and
    # centre are DERIVED (see the properties below).
    # World frame: wall = XY plane at z=0, +Z out of the wall, +Y up the
    # wall, X across, origin on the mirror's bottom centreline.
    ml_mirror_w: float = 34 * IN      # overall width (= arch chord)
    ml_mirror_side_h: float = 60 * IN  # straight vertical side, bottom to springline
    ml_mirror_h: float = 76 * IN      # overall height at the apex
    ml_mirror_t: float = 6.0          # ASSUMED glass thickness — ghost only
    ml_standoff: float = 1.5 * IN     # wall face -> mirror back face
    ml_inset: float = 4 * IN          # spacer outer face inset from the mirror edge
    ml_corner_r: float = 2 * IN       # bottom-corner turn radius on the inset
                                      # contour — the strip cannot turn square

    # Hue Solo lightstrip, silicone sleeve: 14.0 x 4.5mm (Philips spec),
    # 5m nominal. Never cut: the loop is sized to swallow the whole roll.
    ml_strip_w: float = 14.0          # sleeve width -> groove width (along Z)
    ml_strip_t: float = 4.5           # sleeve height -> groove depth (radial)
    ml_strip_len: float = 5000.0      # 16.4 ft roll, uncut
    ml_groove_clear: float = 0.4      # per side, FDM slip fit
    ml_groove_depth: float = 1.5      # LOCATING REBATE only, about a third
                                      # of the sleeve: it says where the
                                      # strip goes, it does not swallow it.
                                      # The strip stands proud and the
                                      # adhesive does the holding
    ml_groove_wall: float = 4.0       # material between the MIRROR face and
                                      # the channel — the groove rides tight
                                      # to the glass, not centred in the gap:
                                      # the emitter hides deeper behind the
                                      # edge and the wash leaves the wall
                                      # softer. 4mm keeps the bond face stiff

    # spacer block: section is ml_spacer_t (radial) x ml_standoff (Z).
    # With the screws gone the only radial demand is the rebate plus a wall,
    # so the block is half what it was — 20 spacers of solid plastic add up.
    ml_spacer_t: float = 10.0         # radial thickness: rebate + backing
    ml_spacer_len: float = 3 * IN     # length along the contour
    ml_gap: float = 6 * IN            # target gap between spacers

    # finish: edge breaks and the part label. Every spacer prints
    # mirror-face-down, so these are the only features on the wall face.
    ml_break: float = 0.8             # edge break on the bed/wall faces
    ml_mouth_flare: float = 0.6       # rebate mouth flare, per side
    ml_part_text_h: float = 6.0       # engraved part label cap height
    ml_part_text_depth: float = 0.6

    # No fasteners: the spacers glue to the back of the mirror frame and
    # the mirror rests against the wall on them, so there is nothing to
    # drive and nothing to counterbore. The mirror face (z=0) is the bond
    # face — flat, bed-finished, unbroken.

    # --- storage-box lid clip (side quest — stiffens a flimsy lid) ---
    # Inverted-U that springs onto the lid's 3mm side wall. The channel
    # is wider at the closed end than at the mouth, so the two legs
    # splay open going on and pinch the wall as they relax. Test coupon
    # first: a short section to check the grip before running the full
    # lid length.
    lclip_ch_base: float = 4.0     # channel width at the closed end
    lclip_ch_mouth: float = 2.5    # channel width at the mouth — under
                                   # the 3mm wall, that's the grip
    lclip_h: float = 14.0          # overall height, closed end to tips
                                   # (v1 10.0 — arms too short to hold)
    lclip_wall: float = 2.0        # leg thickness (and the cap's)
    lclip_len: float = 50.0        # coupon run along the lid edge

    # Stack post: a column standing on the closed end, so the box above
    # lands on the posts instead of on the flexy lid. Height is measured
    # from the INNER cap face — the face the lid wall's top edge butts
    # against — so it's the real clearance over the lid, cap included.
    # Post runs the clip's own footprint: a slim rib was tried and
    # dropped, the load path wants the full section.
    lclip_post_h: float = 27.5     # inner cap face -> top of the post

    # --- storage-box corner brace (side quest, same boxes) ---
    # Three square plates meeting at one vertex — the bottom, back and
    # left faces of a cube with the rest thrown away. Wraps a box corner
    # so the walls can't splay. Local frame: the corner sits at the
    # origin, plates run +X/+Y/+Z.
    bcnr_size: float = 30.0        # leg reach along each axis
    bcnr_t: float = 2.0            # plate thickness


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

    # --- mirror backlight: everything below is DERIVED from the three
    # measured mirror numbers. Nothing here is a measurement.

    @property
    def ml_arch_rise(self) -> float:
        """Arch sag: apex above the springline where the sides stop."""
        return self.ml_mirror_h - self.ml_mirror_side_h

    @property
    def ml_arch_r(self) -> float:
        """Radius of the circular arch through both top corners and the
        apex: R = (half-chord² + rise²) / (2·rise)."""
        a, f = self.ml_mirror_w / 2, self.ml_arch_rise
        return (a * a + f * f) / (2 * f)

    @property
    def ml_arch_cy(self) -> float:
        """Arch centre height. Sits BELOW the springline whenever the
        rise is under half the width — so the arc is a touch over a
        semicircle and meets the side with a small kink, not tangent."""
        return self.ml_mirror_h - self.ml_arch_r

    @property
    def ml_path_r(self) -> float:
        """Arch radius on the inset (spacer/strip) contour."""
        return self.ml_arch_r - self.ml_inset

    @property
    def ml_path_x(self) -> float:
        """Inset contour of the straight sides, |x|."""
        return self.ml_mirror_w / 2 - self.ml_inset

    @property
    def ml_path_phi(self) -> float:
        """Polar angle (deg from +X) where the inset arc meets the inset
        side line. The arc runs phi .. 180-phi."""
        return math.degrees(math.acos(self.ml_path_x / self.ml_path_r))

    @property
    def ml_path_junction_y(self) -> float:
        """Height where the inset side line meets the inset arc."""
        r, x = self.ml_path_r, self.ml_path_x
        return self.ml_arch_cy + math.sqrt(r * r - x * x)

    @property
    def ml_corner_cx(self) -> float:
        """Bottom-corner turn centre, |x|: inboard of the side contour."""
        return self.ml_path_x - self.ml_corner_r

    @property
    def ml_corner_cy(self) -> float:
        """Bottom-corner turn centre height: above the bottom contour."""
        return self.ml_inset + self.ml_corner_r

    @property
    def ml_side_run(self) -> float:
        """Lit length of one straight side: corner tangent to arch junction."""
        return self.ml_path_junction_y - self.ml_corner_cy

    @property
    def ml_bottom_run(self) -> float:
        """Lit length of the bottom, between the two corner tangents."""
        return 2 * self.ml_corner_cx

    @property
    def ml_corner_run(self) -> float:
        """Arc length of one bottom corner (a quarter turn)."""
        return math.pi / 2 * self.ml_corner_r

    @property
    def ml_arch_run(self) -> float:
        """Lit arc length over the top."""
        return self.ml_path_r * math.radians(180 - 2 * self.ml_path_phi)

    @property
    def ml_path_len(self) -> float:
        """The whole loop: bottom, both corners, both sides, arch."""
        return (
            self.ml_bottom_run
            + 2 * self.ml_corner_run
            + 2 * self.ml_side_run
            + self.ml_arch_run
        )

    @property
    def ml_slack(self) -> float:
        """Strip left over once the loop is closed. Tucks behind the glass
        at the feed; too short to be worth cutting (cut marks are 330mm)."""
        return self.ml_strip_len - self.ml_path_len

    @property
    def ml_groove_w(self) -> float:
        """Groove width along Z = sleeve + clearance both sides."""
        return self.ml_strip_w + 2 * self.ml_groove_clear

    @property
    def ml_strip_proud(self) -> float:
        """How far the sleeve stands out of the rebate."""
        return self.ml_strip_t - self.ml_groove_depth

    @property
    def ml_groove_z0(self) -> float:
        """Groove's mirror-side edge, from the MIRROR face (z=0, the print
        bed). Set by ml_groove_wall, NOT centred — the strip rides tight to
        the glass."""
        return self.ml_groove_wall

    @property
    def ml_groove_wall_far(self) -> float:
        """Material left between the channel (roof chamfer included) and the
        WALL face. The chamfer is what eats into it, so check it."""
        return self.ml_standoff - self.ml_groove_z0 - self.ml_groove_w - self.ml_groove_depth

    @property
    def ml_emitter_hide_deg(self) -> float:
        """How far off the wall plane your eye has to get before the emitting
        face itself comes into view past the mirror edge."""
        return math.degrees(
            math.atan((self.ml_groove_z0 + self.ml_groove_clear) / self.ml_inset)
        )

    @property
    def ml_spacer_dphi(self) -> float:
        """Angular span of one arch spacer at the inset radius, deg."""
        return math.degrees(self.ml_spacer_len / self.ml_path_r)

    @property
    def flap_pin_w(self) -> float:
        """Pin tab reach past the card body, per side. Derived."""
        return (self.flap_w_over_pins - self.flap_w) / 2


P = Params()
