"""Single source of truth for every dimension. Millimetres.

Rule: raw measurements are named constants; anything positional is *derived*
from them (see `pin_y`). Change a base dim -> dependents follow. No magic
numbers in the part files.

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

    # --- NEMA 14 stepper (vendor part, from datasheet drawing) ---
    motor_body_w: float = 35.2      # square faceplate side (MAX)
    motor_body_len: float = 34.0    # body length, face to face
    motor_boss_d: float = 22.0      # pilot boss diameter (22.0 -0.05)
    motor_boss_len: float = 2.0     # boss protrusion past mounting face
    motor_shaft_d: float = 5.0      # shaft diameter (5.0 -0.012)
    motor_shaft_len: float = 24.0   # shaft length past mounting face
    motor_flat_len: float = 16.5    # D-flat length, from shaft tip
    motor_flat_across: float = 4.5  # remaining thickness across the flat
    motor_hole_pitch: float = 26.0  # M3 mount holes, square pattern
    motor_screw_d: float = 3.0      # M3 nominal (tapped in motor)
    motor_screw_depth: float = 4.5  # tapped depth MIN

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
    byj_wirebox_w: float = 14.5   # wire housing width (approx)
    byj_wirebox_d: float = 5.0    # wire housing radial protrusion (approx)
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
    # wire channel: groove in the plate UNDERSIDE, from the pad hole out
    # to the -X edge, so the motor wires can leave the module flat.
    wire_chan_w: float = 8.0       # channel width
    wire_chan_d: float = 1.6       # channel depth into the underside
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
    tower_top_chamfer: float = 0.8
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
    pilot_clearance: float = 0.3  # radial gap around the Ø22 pilot boss
    screw_clearance: float = 0.2  # radial gap around M3 screws

    @property
    def pilot_hole_d(self) -> float:
        """Through-hole for the motor's pilot boss. Derived."""
        return self.motor_boss_d + 2 * self.pilot_clearance

    @property
    def screw_hole_d(self) -> float:
        """M3 clearance hole diameter. Derived."""
        return self.motor_screw_d + 2 * self.screw_clearance

    # --- hall sensor mount (Kingsman-style) ---
    # Sensor PCB screws flat onto a pedestal whose top is level with the
    # motor ear seat. Two M2 self-tap holes share the same X, 10mm apart
    # along Y. Position anchored near the vendor ghost's bracket.
    # Sensor PCB (measured): 19 x 15, holes along the 15 side inset 2.5
    # from each end (-> 10 pitch), hole line inset 2.5 from one long edge
    # (-> 7 off the PCB centreline). PCB centre sits on the shaft X line;
    # the hole line is therefore off-centre from the shaft.
    hall_pcb_w: float = 19.0       # PCB size across X
    hall_pcb_l: float = 15.0       # PCB size along Y (hole line side)
    hall_pcb_t: float = 1.6        # PCB thickness
    hall_hole_inset: float = 2.5   # edge -> hole centre, both axes
    hall_near_gap: float = 11.0    # shaft axis -> nearest hole centre
    hall_pilot_d: float = 1.6      # M2 self-tap pilot bore
    hall_pilot_depth: float = 8.0  # pilot depth from the pedestal top
    hall_post_chamfer: float = 1.0  # edge break on the pedestal
    hall_post_frac: float = 0.75   # fraction of PCB width the pedestal backs
    hall_post_l: float = 16.0      # pedestal footprint Y (pitch + edge meat)

    @property
    def hall_post_w(self) -> float:
        """Pedestal footprint X: backs hall_post_frac of the PCB width,
        growing from the PCB's -X (hole line) edge inward. Derived."""
        return self.hall_post_frac * self.hall_pcb_w

    @property
    def hall_post_x(self) -> float:
        """Pedestal centre X: flush with the PCB's -X edge. Derived."""
        return self.hall_pcb_x - self.hall_pcb_w / 2 + self.hall_post_w / 2

    @property
    def hall_hole_pitch(self) -> float:
        """M2 hole spacing along Y: PCB length minus an inset each end."""
        return self.hall_pcb_l - 2 * self.hall_hole_inset

    @property
    def hall_pcb_x(self) -> float:
        """PCB centre X: on the shaft axis. Derived."""
        return self.mount_x

    @property
    def hall_x(self) -> float:
        """Hole line X: inset from the PCB's -X long edge. Derived."""
        return self.hall_pcb_x - (self.hall_pcb_w / 2 - self.hall_hole_inset)

    @property
    def hall_y(self) -> float:
        """PCB centre Y = midpoint between the two holes: nearest hole sits
        hall_near_gap below the shaft axis (toward -Y)."""
        return self.byj_shaft_y - self.hall_near_gap - self.hall_hole_pitch / 2

    @property
    def hall_seat(self) -> float:
        """Hall PCB seat height: same as the motor ear seat. Derived."""
        return self.byj_flange_seat

    # --- drum (two parts: outer can + inner disc, measured off the
    # Kingsman FlapDrum{Outer,Inner}.stl) ---
    # Outer = pringles can: flap ring + its share of the barrel wall.
    # Inner = shorter side: ring/web disc + shaft hub + the rest of the
    # barrel, faces the motor. Parts join by radial fins on the inner
    # web dropping into a slotted guide ring inside the outer barrel.
    drum_ring_od: float = 69.3     # flap ring outer diameter (both rings)
    drum_ring_t: float = 1.6       # ring / web / lip thickness
    drum_flap_count: int = 45      # flap pin slots per ring
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
    drum_fin_t: float = 1.2        # fin thickness
    drum_fin_t_key: float = 2.7    # thickness of fin 0 (the key): only
                                   # fits its own wide notch, so the
                                   # parts assemble one way only
    drum_fin_len: float = 18.0     # fin depth below the web, at the rim
    drum_fin_len_hub: float = 8.0  # fin depth at the hub end (bottom
                                   # edge slopes rim-deep to hub-shallow)
    drum_fin_clear: float = 0.2    # fin-to-wall / notch clearance
    drum_fin_tip_fillet: float = 1.0  # fin tip corner round (dock lead-in)
    drum_fin_hub_fillet: float = 0.8  # fillet where fins meet the hub wall
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
    drum_bore_depth: float = 9.0   # double-D shaft bore depth
    drum_bore_clear: float = 0.2   # shaft bore clearance (dia and flats)
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
    drum_magnet_r: float = 21.5    # boss centre radius; hall element
                                   # must sit at this radius
    drum_magnet_clear: float = 0.2  # hole diametral clearance
    drum_magnet_standoff: float = 7.5  # boss under the web dropping the
                                   # magnet toward the hall sensor. Capped
                                   # ~7.7 at this radius: any longer and
                                   # the boss bottom reaches the outer
                                   # part's guide-ring band (face r 25.0,
                                   # top at the butt joint)
    drum_poke_d: float = 2.2       # magnet eject hole (toothpick) through
                                   # the web into the pocket's blind end
    # First-slot indicator: debossed triangle next to flap slot 0 (the
    # slot on the key fin / key notch line) on both parts' outside faces.
    drum_mark_depth: float = 0.6
    drum_mark_len: float = 3.0     # triangle length (radial)
    drum_mark_w: float = 3.0       # triangle base width (tangential)
    drum_flat_clear: float = 0.5   # hub bore bottom above the shaft's
                                   # round section (bore is double-D; only
                                   # the flat zone may enter it)

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
    def drum_slot_pitch(self) -> float:
        """Angular pitch between flap slots. Derived."""
        return 360.0 / self.drum_flap_count

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

    # vendor screw-tower complex Y extent (measured off the STEP; also
    # crops the tower regions in vendor.vendor_towers)
    tower_zone_y: float = 0.8        # zone centre
    tower_zone_half_y: float = 13.25  # zone half-extent

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
