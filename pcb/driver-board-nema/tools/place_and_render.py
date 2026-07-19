"""Place, route and render the NEMA/TMC2209 driver board.

Run with atopile's interpreter (it bundles faebryk):
    ~/.local/share/uv/tools/atopile/bin/python tools/place_and_render.py

Same shape as the v1 board's tooling: placement and routing are data tables
keyed by atopile_address, so they survive `ato build` designator reshuffles.
Adds a geometric self-check (body overlap, off-board, pad-to-pad) that runs
before anything is written — KiCad's DRC catches copper rule violations but is
happy to let two component *bodies* occupy the same space.
"""

import math
import re
from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad

ROOT = Path(__file__).parent.parent
PCB = ROOT / "layouts/default/default.kicad_pcb"

BOARD_W, BOARD_H = 62.0, 76.0

# address -> (x, y, rot_deg). Origin top-left, y down, mm.
#
# Regions, roughly:
#   top-left      XIAO socket, USB pointing off the top edge
#   top-right     12V barrel jack + reverse-polarity P-FET
#   mid-right     the 12V -> 5V buck
#   centre-bottom TMC2209 StepStick socket (signal row up, motor row down)
#   bottom        motor + hall connectors, cables exiting the bottom edge
#   right-bottom  VM bulk, hard up against the StepStick's VM pin
#
# Socket row spacing is load-bearing and is asserted in check_socket_pitch():
#   XIAO       15.24mm  (0.6in) -- the module's pin rows ARE 0.6in apart
#   StepStick  12.70mm  (0.5in) -- NOT 0.6in. The 0.6x0.8in figure quoted for a
#              StepStick is its BOARD OUTLINE; the pin rows are inset 1.27mm
#              from each long edge, so centre-to-centre is 15.24 - 2*1.27.
#              (Pololu A4988 dimension drawing; Watterott
#              SilentStepStick-TMC2209_v20 has its rows at x=1.27 and x=13.97.)
PLACEMENT = {
    # XIAO socket: rows 15.24mm apart, pin 1 at the top (rot 270).
    "xiao_left": (12.0, 16.0, 270),    # D0..D6
    "xiao_right": (27.24, 16.0, 270),  # 5V/GND/3V3/D10..D7
    # 5V -> XIAO blocking Schottky, on the 5V run just before the socket
    "d_usb": (30.5, 6.4, 0),
    # 12V input + reverse-polarity gate
    "j_pwr": (56.0, 13.0, 0),          # barrel faces the right edge
    "q_rev": (42.0, 10.5, 0),          # pin3=D (west, jack side), pin2=S (east, rail)
    "r_gate_hi": (37.5, 8.0, 0),
    "r_gate_lo": (37.5, 12.6, 0),
    # 12V -> 5V buck
    "r_en_hi": (38.8, 20.0, 0),
    "u_buck": (46.0, 24.0, 0),
    "c_bin": (51.2, 24.0, 270),
    "c_bst": (46.0, 27.2, 0),
    "l_buck": (53.5, 29.5, 0),
    "c_bout1": (48.5, 34.5, 0),
    "c_bout2": (53.5, 34.5, 0),
    "c_bout3": (44.0, 34.5, 0),
    # Feedback divider, parked hard against the VFB pin at (44.65, 23.05).
    # VFB is the one high-impedance node on the buck; the old placement had it
    # ~10mm and ~20mm of trace away, running alongside the switch node.
    # It sits NORTH of the buck rather than west: west is where VBST and its
    # bootstrap cap live, and crowding those two nets together is how you get
    # a switcher that oscillates.
    "r_fb_hi": (44.65, 20.6, 270),  # pin1 = 5V (north), pin2 = VFB (south)
    "c_ff": (42.3, 20.6, 270),      # feedforward cap, parallel with r_fb_hi
    "r_fb_lo": (47.2, 21.35, 0),    # pin1 = VFB (west), pin2 = GND (east)
    "c_5v": (58.0, 34.5, 0),
    "r_led": (55.0, 18.0, 0),
    "d_pwr": (55.0, 21.0, 0),
    # signal conditioning
    "r_uart": (19.0, 30.0, 0),
    "r_hall": (16.5, 63.0, 0),     # pin1 = connector (west), pin2 = D8 (east)
    # TMC2209 StepStick socket -- rows 12.70mm apart, NOT 15.24mm
    "ss_right": (31.0, 44.54, 0),  # pins 9..16  DIR STEP PDN UART SPRD MS2 MS1 EN
    "ss_left": (31.0, 57.24, 0),   # pins 1..8   GND VIO M1B M1A M2A M2B GND VM
    # VM bulk, right beside ss_left.8 (VM)
    "c_bulk": (50.0, 57.24, 0),
    "c_vm": (40.5, 62.0, 0),
    "c_vm_hf": (39.89, 54.0, 90),  # pin1 (v12) faces south, onto ss_left.8
    # connectors, cables off the bottom edge
    "j_motor": (30.0, 68.0, 180),
    "j_hall": (11.0, 66.5, 0),
}

# Socket row pitches that must hold exactly, in mm. Asserted numerically at
# place time -- these are the dimensions that decide whether the two modules
# physically drop into the board at all.
SOCKET_PITCH = [
    ("XIAO", "xiao_left", "xiao_right", 15.24),
    ("StepStick", "ss_right", "ss_left", 12.70),
]

# M3 clearance holes, one per corner.
MOUNT_HOLES = [(3.5, 3.5), (58.5, 3.5), (3.5, 72.5), (58.5, 72.5)]
MOUNT_DIA = 3.2

# Board-level silk: (text, x, y, size, rot). Per-footprint refdes/polarity/pin-1
# marks come from the footprints; this is the stuff that makes the board
# self-documenting while you are plugging things into it.
SILK = [
    ("SPLIT-FLAP DRIVER v2", 17.0, 31.8, 1.1, 0),
    ("NEMA 14 / TMC2209", 17.0, 33.6, 0.9, 0),
    ("XIAO ESP32-C6", 19.6, 3.0, 1.0, 0),
    ("USB ^", 19.6, 5.0, 0.8, 0),
    ("STEP=D0 DIR=D1 EN=D2", 15.0, 36.4, 0.8, 0),
    ("PDN=D6 (1k)  HALL DO=D8", 15.0, 38.2, 0.8, 0),
    ("12V IN", 50.5, 4.4, 1.0, 0),
    ("+ CENTRE", 50.5, 2.6, 0.8, 0),
    ("5V", 58.0, 24.0, 0.8, 0),
    ("TMC2209 StepStick", 31.0, 40.2, 1.0, 0),
    # Pin 1 and pin 9 are at the -x end (x=22.11), so the arrow points -x. It
    # used to read "THIS END >" while pointing at pin 8/16 -- and since both
    # rows are identical 1x8 headers, this marking is the only thing standing
    # between the builder and a 180-degree insertion. Belt and braces: each row
    # is also labelled with what it carries.
    ("< PIN 1 / PIN 9 THIS END", 31.0, 47.9, 0.8, 0),
    ("J5 LOGIC (9-16)", 31.0, 49.7, 0.8, 0),
    ("MS1 MS2 SPRD = GND", 31.0, 51.5, 0.8, 0),
    ("J4 VM + COILS (1-8)", 31.0, 53.3, 0.8, 0),
    ("VM BULK 470u  + = WEST END", 50.0, 49.4, 0.8, 0),
    # C6 is polarised and its footprint chamfer marks the POSITIVE end, which
    # is the opposite of what a builder reading the can's stripe expects. Say
    # it in words, beside pad 1.
    ("+", 41.8, 57.6, 1.4, 0),
    ("MOTOR", 30.0, 64.0, 1.0, 0),
    # Coil labels follow the DRIVER's internal naming, not the connector's:
    # on a SilentStepStick M1 is coil B and M2 is coil A (Watterott). The
    # wiring was already right; only these four labels were back to front.
    ("A2", 26.25, 65.9, 0.8, 0),
    ("A1", 28.75, 65.9, 0.8, 0),
    ("B2", 31.25, 65.9, 0.8, 0),
    ("B1", 33.75, 65.9, 0.8, 0),
    ("HALL", 11.0, 61.5, 1.0, 0),
    ("5V GND DO", 11.0, 63.3, 0.8, 0),
    ("Designed by 0x63616c", 14.0, 74.6, 0.9, 0),
]

# Footprint-local refdes overrides, for the ones whose stock position lands on
# their own pad or a neighbour's. Local coords, applied pre-rotation.
# Which way the auto-placed refdes should sit relative to its part.
REFDES_DIR = {
    "r_gate_hi": (0.0, -1.0), "r_gate_lo": (0.0, 1.0),
    "r_en_hi": (-1.0, 0.0), "r_en_lo": (-1.0, 0.0),
    "r_fb_hi": (-1.0, 0.0), "r_fb_lo": (-1.0, 0.0),
    "c_bout1": (0.0, 1.0), "c_bout2": (0.0, -1.0), "c_5v": (0.0, 1.0),
    "d_pwr": (-1.0, 0.0), "r_led": (-1.0, 0.0), "c_bst": (0.0, 1.0),
    "u_buck": (-1.0, 0.0), "q_rev": (0.0, -1.0), "c_vm": (0.0, 1.0),
    "c_bin": (1.0, 0.0), "r_uart": (0.0, 1.0),
}

REFDES_LOCAL = {
    "xiao_left": (-10.4, 0.0),
    "xiao_right": (10.4, 0.0),
    "ss_left": (0.0, 2.6),
    "ss_right": (-11.5, 0.0),
    "c_bulk": (0.0, -6.2),
    "j_pwr": (-11.5, -6.0),
    "l_buck": (0.0, -3.4),
    "j_motor": (7.5, 2.0),
    "j_hall": (-6.0, -3.2),
    "c_bin": (2.4, 0.0),
    "c_bout2": (0.0, 3.4),
    "r_uart": (-2.6, 0.0),
    # feedback block -- four parts inside ~4mm, so every refdes is placed by
    # hand. r_fb_hi and c_ff are rotated 270, hence the swapped axes.
    "r_fb_hi": (-2.6, 0.0),    # board: 2.6mm above the part
    "c_ff": (2.9, 2.0),        # board: below and west, clear of U1's refdes
    "r_fb_lo": (0.0, -2.2),
    "c_bout3": (-3.4, -3.2),
}

# PCBWay's stated minimum silkscreen line width is 0.15mm; anything thinner is
# "may not be legible" territory and they reserve the right to drop it. The
# vendored footprints are full of 0.06mm pin-1 dots and 0.10mm outlines, and
# the refdes text used to be stamped at 0.12mm, so widths are normalised here
# rather than trusted from the libraries.
MIN_SILK_W = 0.15
REFDES_H = 1.0

SIG, PWR, MOT = 0.4, 0.8, 1.0
VIA_SIZE, VIA_DRILL = 0.6, 0.3
LAYERS = {"F": "F.Cu", "B": "B.Cu"}

# Hand-routed, 2 layers. Each route: (from_pad, width, [(layer, x, y), ...])
# with ("via",) switching layer at the previous point. Pads are "addr.pin".
#
# Layer discipline: B.Cu carries the long north-south runs, F.Cu the local
# fan-out inside each block. Motor coils and the 12V/GND spines are MOT/PWR
# width; only true logic signals run at SIG.
ROUTES = [
    # ---- 12V input, before protection (v12_raw) -----------------------------
    # The jack sits east and the FET's DRAIN is its west pad, so v12_raw has to
    # get past the FET. It ducks onto B.Cu to do it, which also keeps the whole
    # unprotected net off the top layer where the gate divider lives.
    # y=7.00, not 6.20: at 6.20 this run passed 0.60mm from the M3 hole at
    # (58.5, 3.5), which is not enough margin for a routed-tolerance hole with
    # a metal screw head sitting in it and 12V on the trace. 7.00 gives 1.40mm.
    ("j_pwr.1", MOT, [("F", 59.33, 10.65), ("F", 59.33, 7.00), ("F", 46.50, 7.00), ("via",),
                      ("B", 46.50, 7.00), ("B", 39.50, 7.00), ("B", 39.50, 10.50), ("via",),
                      ("F", 39.50, 10.50), ("F", 40.85, 10.50)]),

    # ---- P-FET gate divider -------------------------------------------------
    # r_gate_hi now hangs off the SOURCE (v12), not the jack -- the gate is
    # referenced to the source, so the divider's top follows the source pin.
    ("r_gate_hi.2", SIG, [("F", 38.25, 8.00), ("F", 43.15, 8.00), ("F", 43.15, 9.55)]),
    # Hops to B.Cu to duck under the drain escape, then back up into the gate.
    ("r_gate_hi.1", SIG, [("F", 36.75, 8.00), ("F", 35.40, 8.00), ("via",),
                          ("B", 35.40, 13.60), ("B", 43.80, 13.60), ("via",),
                          ("F", 43.80, 11.45), ("F", 43.15, 11.45)]),
    ("r_gate_lo.1", SIG, [("F", 36.75, 12.60), ("F", 34.40, 12.60), ("F", 34.40, 8.00), ("F", 35.40, 8.00)]),

    # ---- protected 12V rail (v12): one B.Cu spine down x=45.5 ---------------
    # Starts at the FET's SOURCE (pin 2, east pad) now that D and S are the
    # right way round.
    ("q_rev.2", MOT, [("F", 43.15, 9.55), ("F", 45.00, 9.55), ("F", 45.00, 16.60), ("via",),
                      ("B", 45.00, 16.60), ("B", 45.50, 17.50), ("B", 45.50, 57.24), ("B", 39.89, 57.24)]),
    ("r_en_hi.1", SIG, [("F", 38.05, 20.00), ("F", 37.00, 20.00), ("F", 37.00, 18.60), ("via",),
                        ("B", 37.00, 18.60), ("B", 45.50, 18.60)]),
    ("c_bin.1", PWR, [("F", 51.20, 23.00), ("F", 51.20, 21.00), ("via",),
                      ("B", 51.20, 21.00), ("B", 45.50, 21.00)]),
    ("u_buck.3", 0.6, [("F", 47.35, 23.05), ("F", 47.35, 22.60), ("F", 51.20, 22.60), ("F", 51.20, 23.00)]),
    # bulk + VM ceramic hang off the same spine, as close to ss_left.8 as the
    # 10mm can body allows
    ("c_bulk.1", MOT, [("F", 45.50, 57.24), ("F", 45.50, 54.00), ("via",), ("B", 45.50, 54.00)]),
    # c_vm used to reach VM the long way round -- ~11mm and a via for a 4.8mm
    # straight-line gap, which threw away most of the point of a ceramic.
    ("c_vm.1", PWR, [("F", 39.50, 62.00), ("F", 39.50, 58.50), ("F", 39.89, 58.10),
                     ("F", 39.89, 57.24)]),
    # 100nF straight onto the VM pad
    ("c_vm_hf.1", SIG, [("F", 39.89, 54.70), ("F", 39.89, 57.24)]),

    # ---- buck GND escape ----------------------------------------------------
    # U1's own pad ring fences off a pocket of F.Cu GND that has no path to the
    # B.Cu pour, and the v12 spine running underneath at x=45.5 leaves nowhere
    # legal to drop a stitching via inside it. So the return is routed out of
    # the pad instead -- which is what a switcher wants anyway: a via on the
    # GND pin, not somewhere across the pour.
    ("u_buck.1", 0.6, [("F", 47.35, 24.95), ("F", 48.50, 24.95), ("via",)]),

    # ---- buck switching node ------------------------------------------------
    ("u_buck.2", 0.6, [("F", 47.35, 24.00), ("F", 49.40, 24.00), ("F", 49.40, 29.50), ("F", 51.50, 29.50)]),
    ("c_bst.2", SIG, [("F", 46.70, 27.20), ("F", 49.40, 27.20)]),
    ("u_buck.6", SIG, [("F", 44.65, 24.95), ("F", 43.60, 24.95), ("F", 43.60, 27.20), ("F", 45.30, 27.20)]),

    # ---- buck enable: plain 100k pull-up to v12 ------------------------------
    # Ducks under the feedback block on B.Cu -- EN is a static DC node, so a
    # couple of vias cost nothing, and it keeps the VFB area clear.
    ("u_buck.5", SIG, [("F", 44.65, 24.00), ("F", 44.20, 24.00), ("via",),
                       ("B", 44.20, 24.00), ("B", 44.20, 21.50), ("B", 39.55, 21.50), ("via",),
                       ("F", 39.55, 21.50), ("F", 39.55, 20.00)]),

    # ---- buck feedback: 0.768V ref, 54.9k/10k -> 4.99V, with Cff ------------
    # The whole divider now sits within ~2mm of the VFB pin. VFB is the only
    # high-Z node on the buck and it used to run ~10mm alongside the switch
    # node before reaching its resistors.
    ("u_buck.4", SIG, [("F", 44.65, 23.05), ("F", 44.65, 21.35)]),   # VFB -> r_fb_hi.2
    ("r_fb_lo.1", SIG, [("F", 46.45, 21.35), ("F", 44.65, 21.35)]),  # VFB -> r_fb_lo
    ("c_ff.2", SIG, [("F", 42.30, 21.30), ("F", 43.90, 21.35), ("F", 44.65, 21.35)]),  # Cff -> VFB
    ("c_ff.1", SIG, [("F", 42.30, 19.90), ("F", 43.90, 19.85), ("F", 44.65, 19.85)]),  # Cff -> 5V

    # ---- 5V rail ------------------------------------------------------------
    ("l_buck.1", PWR, [("F", 55.50, 29.50), ("F", 57.60, 29.50), ("F", 57.60, 33.00),
                       ("F", 57.30, 33.00), ("F", 57.30, 34.50)]),
    ("c_bout2.1", PWR, [("F", 52.50, 34.50), ("F", 52.50, 33.00), ("F", 57.30, 33.00)]),
    ("c_bout1.1", PWR, [("F", 47.50, 34.50), ("F", 47.50, 33.00), ("F", 52.50, 33.00)]),
    # third output cap, extending the bank westward
    ("c_bout3.1", PWR, [("F", 43.00, 34.50), ("F", 43.00, 33.00), ("F", 47.50, 33.00)]),
    # 5V up to the feedback divider and the Cff, which now live by the VFB pin.
    # Sense point is the output cap bank, not the inductor -- that is the node
    # the load actually sees.
    ("c_ff.1", PWR, [("F", 42.30, 19.90), ("F", 41.00, 19.90), ("F", 41.00, 32.00),
                     ("F", 43.00, 33.00)]),
    ("r_led.1", SIG, [("F", 54.25, 18.00), ("F", 54.25, 17.00), ("F", 57.60, 17.00), ("F", 57.60, 29.50)]),

    # ---- 5V up to the XIAO, through the blocking Schottky --------------------
    # The B.Cu corridor at x=34 carries the *undropped* buck rail: the hall
    # connector taps it, and only the very last hop goes through d_usb into the
    # XIAO's 5V pad. Everything upstream of d_usb is still a full 5V.
    ("c_bout3.1", PWR, [("F", 43.00, 34.50), ("F", 41.00, 34.50), ("F", 41.00, 31.00), ("via",),
                        ("B", 41.00, 31.00), ("B", 41.00, 29.00), ("B", 34.00, 29.00),
                        ("B", 34.00, 6.40), ("via",), ("F", 34.00, 6.40), ("F", 32.20, 6.40)]),
    ("j_hall.1", PWR, [("B", 8.50, 66.50), ("B", 4.50, 66.50), ("B", 4.50, 6.40), ("B", 34.00, 6.40)]),
    # cathode side -> the XIAO socket's 5V pin, and nothing else on the board
    ("d_usb.1", PWR, [("F", 28.80, 6.40), ("F", 27.24, 6.40), ("F", 27.24, 8.38)]),

    # ---- 5V power LED -------------------------------------------------------
    ("r_led.2", SIG, [("F", 55.75, 18.00), ("F", 55.75, 21.00)]),

    # ---- logic: XIAO -> StepStick ------------------------------------------
    # These three leave the XIAO top-to-bottom (step, dir, en_n) but have to
    # arrive left-to-right as dir, step, en_n, so the lane order reverses
    # between the top of the board and the bottom — there is no single-layer
    # ordering that avoids a crossing. Each therefore takes its westward stub on
    # F.Cu and drops down its own B.Cu lane, so the stubs cross the lanes on the
    # opposite layer. Eastward runs are stacked y=36 / 37.4 / 39, each starting
    # from its own lane, which keeps them mutually clear.
    ("xiao_left.1", SIG, [("F", 12.00, 8.38), ("F", 9.40, 8.38), ("via",),
                          ("B", 9.40, 8.38), ("B", 9.40, 36.00), ("B", 24.65, 36.00), ("via",),
                          ("F", 24.65, 36.00), ("F", 24.65, 44.54)]),
    ("xiao_left.2", SIG, [("F", 12.00, 10.92), ("F", 8.00, 10.92), ("via",),
                          ("B", 8.00, 10.92), ("B", 8.00, 37.40), ("B", 22.11, 37.40), ("via",),
                          ("F", 22.11, 37.40), ("F", 22.11, 44.54)]),
    ("xiao_left.3", SIG, [("F", 12.00, 13.46), ("F", 6.60, 13.46), ("via",),
                          ("B", 6.60, 13.46), ("B", 6.60, 39.00), ("B", 39.89, 39.00),
                          ("B", 39.89, 44.54)]),
    # PDN: D6 -> 1k -> StepStick pin 11
    ("xiao_left.7", SIG, [("B", 12.00, 23.62), ("B", 12.00, 27.60), ("B", 18.25, 27.60), ("via",),
                          ("F", 18.25, 27.60), ("F", 18.25, 30.00)]),
    ("r_uart.2", SIG, [("F", 19.75, 30.00), ("F", 27.19, 30.00), ("F", 27.19, 44.54)]),
    # D7 = GPIO17 = U0RXD onto the same PDN net, so the UART can be read back.
    # Drops onto B.Cu to clear the hall run, which crosses on F at y=25.
    ("xiao_right.7", SIG, [("F", 27.24, 23.62), ("F", 29.00, 23.62), ("via",),
                           ("B", 29.00, 23.62), ("B", 29.00, 31.50), ("via",),
                           ("F", 29.00, 31.50), ("F", 27.19, 31.50)]),
    # VIO: the XIAO's own 3V3 regulator sets the StepStick's logic level
    ("xiao_right.3", SIG, [("F", 27.24, 13.46), ("F", 31.60, 13.46), ("F", 31.60, 26.00),
                           ("F", 16.00, 26.00), ("F", 16.00, 53.00), ("F", 24.65, 53.00),
                           ("F", 24.65, 57.24)]),
    # hall DO -> 1k -> D8. r_hall bounds the fault current if the user's hall
    # module turns out to have a pull-up to its own 5V rather than being the
    # open-collector part we assume.
    ("xiao_right.6", SIG, [("F", 27.24, 21.08), ("F", 30.60, 21.08), ("F", 30.60, 25.00),
                           ("F", 10.60, 25.00), ("F", 10.60, 59.00), ("F", 19.00, 59.00),
                           ("F", 19.00, 63.00), ("F", 17.25, 63.00)]),
    ("r_hall.1", SIG, [("F", 15.75, 63.00), ("F", 13.50, 63.00), ("F", 13.50, 66.50)]),

    # ---- motor coils --------------------------------------------------------
    # The StepStick coil order (M1B M1A M2A M2B) is the reverse of the
    # connector's (A1 A2 B1 B2), so coil 1 goes out on F.Cu and coil 2 on B.Cu
    # rather than trying to untangle them on one layer.
    ("ss_left.4", MOT, [("F", 29.73, 57.24), ("F", 29.73, 60.00), ("F", 33.75, 63.00), ("F", 33.75, 68.00)]),
    ("ss_left.3", MOT, [("F", 27.19, 57.24), ("F", 27.19, 61.00), ("F", 31.21, 64.50), ("F", 31.21, 68.00)]),
    ("ss_left.5", MOT, [("B", 32.27, 57.24), ("B", 32.27, 62.00), ("B", 28.67, 65.00), ("B", 28.67, 68.00)]),
    ("ss_left.6", MOT, [("B", 34.81, 57.24), ("B", 37.50, 60.00), ("B", 37.50, 70.50),
                        ("B", 26.13, 70.50), ("B", 26.13, 68.00)]),
]

# GND is a two-layer pour, not a routed net. These vias stitch the F.Cu and
# B.Cu pours together in the open areas, which matters most around the buck's
# return path.
GND_REF_PAD = ("ss_left", "1")  # StepStick pin 1 is GND — used to resolve the net
GND_STITCH = [(17.5, 20.0), (7.0, 50.0), (36.0, 20.0), (36.0, 50.0),
              (52.0, 45.0), (52.0, 20.0), (20.0, 72.0), (44.0, 72.0),
              # Inside the buck's own pad ring. The VIN/VFB/EN/VBST escapes
              # fence off a ~17mm^2 pocket of F.Cu GND around U1 that has no
              # other path to the B.Cu pour -- it showed up as a zone-to-zone
              # unconnected item. It is also exactly where the buck's return
              # current wants a via, so this one is doing real work.
              # The 1.0mm v12 spine runs ~40mm down B.Cu at x=45.5, straight
              # between the StepStick's GND pins and C6's negative terminal,
              # so the VM return current cannot cross it on B.Cu. These pairs
              # let it hop to the F.Cu pour and back around the slit.
              (42.5, 50.0), (48.5, 52.5), (42.5, 60.0)]


def fp_extent(fp, board_rot):
    """Half-width/half-height of a footprint's pads+silk, in board space."""
    xs, ys = [], []
    for pad in fp.pads:
        px, py = rot(pad.at.x, pad.at.y, board_rot)
        w, h = pad.size.w, (pad.size.h or pad.size.w)
        if round(((pad.at.r or 0)) % 180) == 90:
            w, h = h, w
        xs += [px - w / 2, px + w / 2]
        ys += [py - h / 2, py + h / 2]
    for ln in fp.fp_lines:
        if "SilkS" not in str(ln.layer):
            continue
        for lx, ly in (rot(ln.start.x, ln.start.y, board_rot),
                       rot(ln.end.x, ln.end.y, board_rot)):
            xs.append(lx)
            ys.append(ly)
    return max(abs(min(xs)), abs(max(xs))), max(abs(min(ys)), abs(max(ys)))


def rot(x, y, deg):
    a = math.radians(-deg)  # kicad rotation is CCW in a y-down world
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def fp_boxes(k):
    """(addr, pad_boxes, body_box) in board coords, honouring pad rotation."""
    out = []
    for fp in k.footprints:
        addr = next(p.value for p in fp.propertys if p.name == "atopile_address").split(".")[-1]
        fx, fy, fr = fp.at.x, fp.at.y, fp.at.r or 0
        pads, xs, ys = [], [], []
        for pad in fp.pads:
            px, py = rot(pad.at.x, pad.at.y, fr)
            w, h = pad.size.w, (pad.size.h or pad.size.w)
            if round(((pad.at.r or 0) + fr) % 180) == 90:
                w, h = h, w
            box = (fx + px - w / 2, fy + py - h / 2, fx + px + w / 2, fy + py + h / 2)
            pads.append((pad.name, box))
            xs += [box[0], box[2]]
            ys += [box[1], box[3]]
        for ln in list(fp.fp_lines) + list(fp.fp_rects):
            if "SilkS" not in str(ln.layer) and "CrtYd" not in str(ln.layer):
                continue
            for px, py in (rot(ln.start.x, ln.start.y, fr), rot(ln.end.x, ln.end.y, fr)):
                xs.append(fx + px)
                ys.append(fy + py)
        out.append((addr, pads, (min(xs), min(ys), max(xs), max(ys))))
    return out


def thicken_silk(k):
    """Raise every footprint silk stroke and text to at least MIN_SILK_W.

    The vendored EasyEDA footprints draw their pin-1 dots as 0.06mm circles and
    most of their outlines at 0.10mm, both under PCBWay's 0.15mm minimum. A
    0.06mm dot is the marking that says which way round a polarised part goes,
    so losing it in production is not cosmetic.
    """
    bumped = 0
    for fp in k.footprints:
        graphics = (list(fp.fp_lines) + list(fp.fp_rects)
                    + list(fp.fp_circles) + list(fp.fp_arcs) + list(fp.fp_poly))
        for g in graphics:
            if "SilkS" not in str(getattr(g, "layer", "")):
                continue
            if g.stroke and g.stroke.width < MIN_SILK_W:
                g.stroke.width = MIN_SILK_W
                bumped += 1
        for t in list(fp.fp_texts) + list(fp.propertys):
            if "SilkS" not in str(getattr(t, "layer", "")):
                continue
            if t.effects and t.effects.font and (t.effects.font.thickness or 0) < MIN_SILK_W:
                t.effects.font.thickness = MIN_SILK_W
                bumped += 1
    print(f"silk: raised {bumped} strokes/texts to >= {MIN_SILK_W}mm")


def check_socket_pitch():
    """Assert the two module sockets are exactly the right distance apart.

    This is the failure that does not show up in DRC, in the renders, or in any
    electrical check -- the board builds and passes everything, and then the
    module physically will not seat. v2 shipped a first spin with the StepStick
    rows at 15.24mm because the 0.6x0.8in figure on a StepStick is its board
    outline, not its pin pitch.
    """
    errs = []
    for name, a, b, want in SOCKET_PITCH:
        (ax, ay, _), (bx, by, _) = PLACEMENT[a], PLACEMENT[b]
        got = math.dist((ax, ay), (bx, by))
        if abs(got - want) > 1e-9:
            errs.append(f"{name} socket rows ({a}/{b}): {got:.4f}mm, want {want}mm")
        # rows must also be parallel -- same rotation, and offset on one axis only
        if abs(ax - bx) > 1e-9 and abs(ay - by) > 1e-9:
            errs.append(f"{name} socket rows ({a}/{b}) are diagonal, not parallel")
        if PLACEMENT[a][2] != PLACEMENT[b][2]:
            errs.append(f"{name} socket rows ({a}/{b}) have different rotations")
    if errs:
        raise SystemExit("SOCKET PITCH CHECK FAILED:\n  " + "\n  ".join(errs))
    print("socket pitch ok: " + ", ".join(f"{n} {w}mm" for n, _, _, w in SOCKET_PITCH))


def check(k):
    """Body overlap / off-board / pad clearance, numerically. Raises on failure."""
    boxes = fp_boxes(k)
    errs = []

    def overlap(a, b, gap=0.0):
        return (a[0] < b[2] - gap and b[0] < a[2] - gap
                and a[1] < b[3] - gap and b[1] < a[3] - gap)

    for addr, pads, body in boxes:
        if body[0] < 0 or body[1] < 0 or body[2] > BOARD_W or body[3] > BOARD_H:
            errs.append(f"{addr}: body off-board {tuple(round(v, 2) for v in body)}")
        for hx, hy in MOUNT_HOLES:
            hole = (hx - MOUNT_DIA / 2, hy - MOUNT_DIA / 2, hx + MOUNT_DIA / 2, hy + MOUNT_DIA / 2)
            if overlap(body, hole):
                errs.append(f"{addr}: body over mount hole at ({hx}, {hy})")

    for i, (a_addr, a_pads, a_body) in enumerate(boxes):
        for b_addr, b_pads, b_body in boxes[i + 1:]:
            if overlap(a_body, b_body, gap=0.01):
                errs.append(f"{a_addr} <-> {b_addr}: bodies overlap")
            for an, ab in a_pads:
                for bn, bb in b_pads:
                    if overlap(ab, bb, gap=-0.2):  # 0.2mm pad-to-pad minimum
                        errs.append(f"{a_addr}.{an} <-> {b_addr}.{bn}: pads < 0.2mm apart")

    if errs:
        raise SystemExit("PLACEMENT CHECK FAILED:\n  " + "\n  ".join(sorted(set(errs))))
    print(f"placement check ok: {len(boxes)} footprints, none overlapping or off-board")


def main():
    check_socket_pitch()
    pcb = kicad.loads(kicad.pcb.PcbFile, strip_mount_holes(PCB.read_text()))
    k = pcb.kicad_pcb

    for fp in k.footprints:
        # faebryk's rotate_fp chokes on propertys/texts without an `at`
        for p in fp.propertys:
            if p.effects:
                p.effects.justify = None
            if p.at is None:
                p.at = kicad.pcb.Xyr(x=0, y=0, r=0)
            elif p.at.r is None:
                p.at.r = 0
        for t in fp.fp_texts:
            if t.at.r is None:
                t.at.r = 0

        addr = next(p.value for p in fp.propertys if p.name == "atopile_address").split(".")[-1]
        if addr not in PLACEMENT:
            continue
        x, y, r = PLACEMENT[addr]
        cur = fp.at.r or 0
        fp.at.x, fp.at.y = x, y
        fp.at.r = r
        delta = (r - cur) % 360
        if delta:
            for obj in list(fp.pads) + list(fp.fp_texts) + list(fp.propertys):
                obj.at.r = ((obj.at.r or 0) + delta) % 360

        ref = next(p for p in fp.propertys if p.name == "Reference")
        # Park the refdes clear of the part rather than trusting the vendored
        # footprint's own position — on most of these it lands on a pad.
        # REFDES_LOCAL wins where a neighbour makes the default spot bad.
        if addr in REFDES_LOCAL:
            ref.at.x, ref.at.y = REFDES_LOCAL[addr]
        else:
            dx, dy = REFDES_DIR.get(addr, (0.0, -1.0))
            half = fp_extent(fp, r)
            off = (dx * (half[0] + 1.3), dy * (half[1] + 1.3))
            ref.at.x, ref.at.y = rot(off[0], off[1], -r)
        if ref.effects and ref.effects.font:
            ref.effects.font.size = kicad.pcb.Wh(w=REFDES_H, h=REFDES_H)
            ref.effects.font.thickness = MIN_SILK_W
        # these fields ship right-justified; with the footprint rotated that
        # throws KiCad's text-extent calc off, so centre them
        if ref.effects:
            ref.effects.justify = None
        ref.at.r = 0
        # Park the Value field on F.Fab at the footprint origin. Left where the
        # vendored footprints put it, it can land exactly on top of the refdes,
        # and KiCad's silk checker then reports phantom clearance errors against
        # whichever field it resolves first.
        for p in fp.propertys:
            if p.name == "Value":
                p.layer = "F.Fab"
                p.at.x, p.at.y = 0.0, 0.0

    thicken_silk(k)
    check(k)

    # drop the previous run's GND pour; add_gnd_zones() re-appends it
    while len(k.zones):
        k.zones.pop(len(k.zones) - 1)

    # board outline
    while len(k.gr_lines):
        k.gr_lines.pop(len(k.gr_lines) - 1)
    for (x1, y1), (x2, y2) in [
        ((0, 0), (BOARD_W, 0)),
        ((BOARD_W, 0), (BOARD_W, BOARD_H)),
        ((BOARD_W, BOARD_H), (0, BOARD_H)),
        ((0, BOARD_H), (0, 0)),
    ]:
        k.gr_lines.append(kicad.pcb.Line(
            start=kicad.pcb.Xy(x=x1, y=y1),
            end=kicad.pcb.Xy(x=x2, y=y2),
            stroke=kicad.pcb.Stroke(width=0.1, type="default"),
            layer="Edge.Cuts",
        ))

    # M3 mounting holes. These used to be Edge.Cuts circles, i.e. routed inner
    # contours. That "works" -- a fab will cut them -- but it leaves the NPTH
    # drill file completely empty, so nothing in the fab package actually says
    # "these are four 3.2mm holes". They are emitted as real NPTH pads below
    # (see add_mount_holes), which puts them in the drill file where a hole
    # belongs and gets them drilled to tolerance rather than routed to one.
    while len(k.gr_circles):
        k.gr_circles.pop(len(k.gr_circles) - 1)

    # board-level silkscreen
    while len(k.gr_texts):
        k.gr_texts.pop(len(k.gr_texts) - 1)
    for text, tx, ty, size, r in SILK:
        k.gr_texts.append(kicad.pcb.Text(
            text=text,
            at=kicad.pcb.Xyr(x=tx, y=ty, r=r),
            layer=kicad.pcb.TextLayer(layer="F.SilkS"),
            effects=kicad.pcb.Effects(
                font=kicad.pcb.Font(size=kicad.pcb.Wh(w=size, h=size),
                                    thickness=max(MIN_SILK_W, round(size * 0.15, 3))),
            ),
        ))

    route(k)
    kicad.dumps(pcb, PCB)
    add_mount_holes()
    set_mask_expansion()
    add_gnd_zones(k)
    render(pcb)


MOUNT_FP_LIB = "SPLITFLAP_MOUNT"

MOUNT_FP = """
	(footprint "{lib}:M3_NPTH"
		(layer "F.Cu")
		(uuid "{uuid}")
		(at {x} {y})
		(attr exclude_from_pos_files exclude_from_bom allow_missing_courtyard)
		(pad "" np_thru_hole circle
			(at 0 0)
			(size {d} {d})
			(drill {d})
			(layers "F&B.Cu" "F.Mask" "B.Mask")
			(uuid "{puid}")
		)
	)
"""


def strip_mount_holes(text):
    """Remove mount-hole footprints from a previous run, by paren matching.

    They are spliced in as raw s-expressions after the dump, so they carry no
    atopile_address and would otherwise trip fp_boxes() on the next run.
    """
    while True:
        i = text.find(f'"{MOUNT_FP_LIB}:')
        if i == -1:
            return text
        start = text.rindex("(footprint", 0, i)
        depth, j = 0, start
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        ls = text.rindex("\n", 0, start)
        text = text[:ls] + text[j:]


def add_mount_holes():
    """Emit the four M3 holes as real NPTH pads.

    As Edge.Cuts circles they were routed inner contours: the fab cuts them,
    but `kicad-cli export drill` produced an EMPTY non-plated drill file, so
    the fab package never actually declared them as holes. A routed 3.2mm
    contour also carries router tolerance rather than drill tolerance, which
    matters when an M3 screw head lands next to a 12V trace.
    """
    text = PCB.read_text().rstrip()
    assert text.endswith(")")
    block = "".join(
        MOUNT_FP.format(lib=MOUNT_FP_LIB, uuid=kicad.gen_uuid(), puid=kicad.gen_uuid(),
                        x=hx, y=hy, d=MOUNT_DIA)
        for hx, hy in MOUNT_HOLES
    )
    PCB.write_text(text[:-1] + block + ")\n")
    print(f"added {len(MOUNT_HOLES)} M3 NPTH pads ({MOUNT_DIA}mm)")


def set_mask_expansion():
    """Solder mask expansion, globally.

    pad_to_mask_clearance 0 makes every mask aperture exactly equal to its
    copper, so any registration error at all leaves mask creeping onto the
    pad. 0.05mm is the usual house value and is what the fabs assume.
    """
    want = 0.05
    text = PCB.read_text()
    new, n = re.subn(r"\(pad_to_mask_clearance [\d.]+\)",
                     f"(pad_to_mask_clearance {want})", text, count=1)
    assert n == 1, "pad_to_mask_clearance not found in the board setup block"
    PCB.write_text(new)
    print(f"set pad_to_mask_clearance to {want}mm")


ZONE = """
	(zone
		(net {net})
		(net_name "{name}")
		(layers "F.Cu" "B.Cu")
		(uuid "{uuid}")
		(name "GND")
		(hatch edge 0.5)
		(priority 0)
		(connect_pads thru_hole_only
			(clearance 0.4)
		)
		(min_thickness 0.3)
		(filled_areas_thickness no)
		(fill yes
			(thermal_gap 0.4)
			(thermal_bridge_width 0.5)
			(island_removal_mode 0)
		)
		(polygon
			(pts
{pts}
			)
		)
	)
"""


def add_gnd_zones(k):
    """Append a two-layer GND pour, written as raw s-expression.

    faebryk's Zone type is awkward to build by hand, and the zone syntax is
    stable, so this splices the block in after the dump. The pour is inset 0.3mm
    from the board edge; KiCad fills it (and honours every clearance) when
    build_outputs.sh runs `kicad-cli pcb drc --refill-zones --save-board`.
    """
    # atopile auto-names the big nets, so resolve GND by a pad we know is on it
    # (StepStick pin 1) rather than by a name that can change between builds.
    gnd = None
    for fp in k.footprints:
        addr = next(x.value for x in fp.propertys if x.name == "atopile_address").split(".")[-1]
        if addr != GND_REF_PAD[0]:
            continue
        gnd = next(pad.net for pad in fp.pads if pad.name == GND_REF_PAD[1])
    assert gnd is not None, "could not resolve the GND net"
    inset = 0.3
    corners = [(inset, inset), (BOARD_W - inset, inset),
               (BOARD_W - inset, BOARD_H - inset), (inset, BOARD_H - inset)]
    pts = "\n".join(f"\t\t\t\t\t(xy {x} {y})" for x, y in corners)
    text = PCB.read_text()
    block = ZONE.format(net=gnd.number, name=gnd.name, uuid=kicad.gen_uuid(), pts=pts)
    assert text.rstrip().endswith(")")
    text = text.rstrip()[:-1] + block + ")\n"
    PCB.write_text(text)
    print(f"added GND pour (net {gnd.number} '{gnd.name}') on F.Cu + B.Cu")


def route(k):
    for coll in (k.segments, k.vias):
        while len(coll):
            coll.pop(len(coll) - 1)

    padnet = {}
    for fp in k.footprints:
        addr = next(p.value for p in fp.propertys if p.name == "atopile_address").split(".")[-1]
        for pad in fp.pads:
            if pad.net:
                padnet[f"{addr}.{pad.name}"] = pad.net.number

    gnd_net = padnet["ss_left.1"]
    for sx, sy in GND_STITCH:
        k.vias.append(kicad.pcb.Via(
            at=kicad.pcb.Xy(x=sx, y=sy), size=VIA_SIZE, drill=VIA_DRILL,
            layers=["F.Cu", "B.Cu"], net=gnd_net,
        ))

    for start_pad, width, path in ROUTES:
        net = padnet[start_pad]
        prev = None
        for step in path:
            if step[0] == "via":
                k.vias.append(kicad.pcb.Via(
                    at=kicad.pcb.Xy(x=prev[0], y=prev[1]),
                    size=VIA_SIZE, drill=VIA_DRILL,
                    layers=["F.Cu", "B.Cu"], net=net,
                ))
                continue
            layer, x, y = LAYERS[step[0]], step[1], step[2]
            if prev is not None and (prev[0], prev[1]) != (x, y):
                k.segments.append(kicad.pcb.Segment(
                    start=kicad.pcb.Xy(x=prev[0], y=prev[1]),
                    end=kicad.pcb.Xy(x=x, y=y),
                    width=width, layer=layer, net=net,
                ))
            prev = (x, y)


def render(pcb):
    k = pcb.kicad_pcb
    S = 12  # px per mm
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="-40 -40 {BOARD_W * S + 80} {BOARD_H * S + 80}" font-family="monospace">',
        f'<rect x="-40" y="-40" width="{BOARD_W * S + 80}" height="{BOARD_H * S + 80}" fill="#10141a"/>',
        f'<rect x="0" y="0" width="{BOARD_W * S}" height="{BOARD_H * S}" rx="8" '
        f'fill="#173425" stroke="#c8a038" stroke-width="2"/>',
    ]
    for hx, hy in MOUNT_HOLES:
        out.append(f'<circle cx="{hx * S}" cy="{hy * S}" r="{MOUNT_DIA * S / 2}" fill="#10141a"/>')

    for want, color in (("B.Cu", "#3b6ea5"), ("F.Cu", "#b0433b")):
        for seg in k.segments:
            if str(seg.layer) != want:
                continue
            out.append(
                f'<line x1="{seg.start.x * S:.1f}" y1="{seg.start.y * S:.1f}" '
                f'x2="{seg.end.x * S:.1f}" y2="{seg.end.y * S:.1f}" stroke="{color}" '
                f'stroke-width="{seg.width * S:.1f}" stroke-linecap="round" opacity="0.9"/>'
            )

    net_pads = {}
    routed_nets = {seg.net for seg in k.segments}
    for fp in k.footprints:
        fx, fy, fr = fp.at.x, fp.at.y, fp.at.r or 0
        ref = next(p.value for p in fp.propertys if p.name == "Reference")
        for ln in fp.fp_lines:
            if "SilkS" not in str(ln.layer):
                continue
            x1, y1 = rot(ln.start.x, ln.start.y, fr)
            x2, y2 = rot(ln.end.x, ln.end.y, fr)
            out.append(
                f'<line x1="{(fx + x1) * S:.1f}" y1="{(fy + y1) * S:.1f}" '
                f'x2="{(fx + x2) * S:.1f}" y2="{(fy + y2) * S:.1f}" stroke="#8fa3b8" stroke-width="1"/>'
            )
        for pad in fp.pads:
            lx, ly = rot(pad.at.x, pad.at.y, fr)
            px, py = (fx + lx) * S, (fy + ly) * S
            w, h = pad.size.w * S, (pad.size.h or pad.size.w) * S
            if round(((pad.at.r or 0) + fr) % 180) == 90:
                w, h = h, w
            tht = str(pad.type) == "thru_hole"
            color = "#d4b03c" if tht else "#c87533"
            if str(pad.shape) == "circle":
                out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{w / 2:.1f}" fill="{color}"/>')
            else:
                rx = 2 if str(pad.shape) in ("roundrect", "oval") else 0
                out.append(
                    f'<rect x="{px - w / 2:.1f}" y="{py - h / 2:.1f}" width="{w:.1f}" '
                    f'height="{h:.1f}" rx="{rx}" fill="{color}"/>'
                )
            if tht and pad.drill and pad.drill.size_x:
                out.append(
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pad.drill.size_x * S / 2:.1f}" fill="#10141a"/>'
                )
            if pad.net and pad.net.number and pad.net.number not in routed_nets:
                net_pads.setdefault(pad.net.name, []).append((px, py))
        out.append(
            f'<text x="{fx * S:.1f}" y="{fy * S - 3:.1f}" fill="#e8e0d0" font-size="9" '
            f'text-anchor="middle">{ref}</text>'
        )

    for via in k.vias:
        out.append(
            f'<circle cx="{via.at.x * S:.1f}" cy="{via.at.y * S:.1f}" r="{via.size * S / 2:.1f}" fill="#d4b03c"/>'
            f'<circle cx="{via.at.x * S:.1f}" cy="{via.at.y * S:.1f}" r="{via.drill * S / 2:.1f}" fill="#10141a"/>'
        )

    for name, pads in net_pads.items():
        for (x1, y1), (x2, y2) in zip(pads, pads[1:]):
            out.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                f'stroke="#4fd1c5" stroke-width="0.8" opacity="0.6"/>'
            )

    for text, tx, ty, size, r in SILK:
        out.append(
            f'<text x="{tx * S:.1f}" y="{ty * S:.1f}" fill="#dfe7ef" font-size="{size * S * 0.7:.1f}" '
            f'text-anchor="middle" opacity="0.75">{text}</text>'
        )

    out.append(
        f'<text x="{BOARD_W * S / 2}" y="-14" fill="#e8e0d0" font-size="14" text-anchor="middle">'
        f'split-flap driver v2 — {BOARD_W:.0f}x{BOARD_H:.0f}mm — red=F.Cu blue=B.Cu</text>'
    )
    out.append("</svg>")
    (ROOT / "preview.svg").write_text("\n".join(out))
    print("wrote", ROOT / "preview.svg")


if __name__ == "__main__":
    main()
