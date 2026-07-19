# split-flap driver board v2 — NEMA 14 / TMC2209

Single-module driver for the split-flap: a socketed **Seeed XIAO ESP32-C6**
drives a socketed **TMC2209 SilentStepStick**, which drives a 4-lead bipolar
**NEMA 14** (0.6 A/phase, 1.8°). The whole module — motor, logic and hall
sensor — runs from **one 12 V barrel jack**.

62 × 76 mm, 2-layer, 1.6 mm FR4. Fits behind a module with room to spare
(the unit plate is 95 × 118 mm).

v1 (`../driver-board/`) is the 28BYJ-48 board and is untouched — it drove a
ULN2003 off USB 5 V. This is a separate design, not a revision of it.

![top](render/top.png)

## Pinout

XIAO pin assignment is the one `firmware/micropython-spike/tmc_spin.py`
already uses, and the hall wiring is carried over unchanged from the v1 bench.

| XIAO | Signal | Goes to |
|---|---|---|
| D0 | STEP | StepStick pin 10 |
| D1 | DIR | StepStick pin 9 |
| D2 | EN | StepStick pin 16 (active **low**; the module pulls it up, so the driver is off until firmware drives it) |
| D6 | PDN_UART | StepStick pin 11, through a 1 kΩ series resistor |
| D8 | HALL DO | J1 pin 3 (open collector — enable the internal pull-up) |
| 5V | +5 V in | fed **by the on-board buck**, not by USB |
| 3V3 | +3.3 V out | StepStick VIO — this is what sets the driver's logic level |

D3/D4/D5/D7/D9/D10 are socketed but unrouted.

### StepStick socket (J5 = pins 9–16, J4 = pins 1–8)

Pin numbering follows the Trinamic *TMC2209 SilentStepStick* hardware manual
(doc rev 1.20). Note this is **not** the naive A4988 column order — the coils
are on the same side as VM, and the header does not carry DIAG or INDEX (those
are module pads 17/18).

```
J4 (pins 1-8)   GND  VIO  M1B  M1A  M2A  M2B  GND  VM
J5 (pins 9-16)  DIR  STEP PDN  UART SPRD MS2  MS1  EN
```

MS1, MS2 and SPREAD are tied to GND: UART address 0 and StealthChop.
Microstepping and run current are set over UART, not by jumpers.
Pin 12 (UART) is left unconnected — we supply our own 1 kΩ on PDN, and the
module has its own series resistor on that pin, so strapping both would put
2 kΩ in the single-wire UART path.

### Connectors

| Ref | Type | Pinout (left → right as silkscreened) |
|---|---|---|
| J3 | 5.5 × 2.1 mm barrel | **centre positive**, 12 V |
| J2 | JST-XH 4-pin, right angle | `B2 B1 A2 A1` — the connector is rotated, hence the reversed order |
| J1 | JST-XH 3-pin, vertical | `5V GND DO` |

## Power

```
12V jack ──> Q1 (P-FET reverse-polarity gate) ──> +12V rail
                                                   ├─> StepStick VM  (C6 470uF + C7 22uF)
                                                   └─> U1 TPS563201 ──> +5V ──> XIAO 5V pin
                                                                               └─> hall sensor
XIAO 3V3 out ──> StepStick VIO
```

**Budget** — a 12 V ≥ 2 A brick covers it with margin:

| Load | Draw |
|---|---|
| Motor, 2 phases × 0.6 A into the coils | ~6–9 W → **0.5–0.75 A** at 12 V (coil resistance not in the listing; assumed 8–12 Ω — measure it) |
| XIAO ESP32-C6 (WiFi peaks) | ~0.5 A at 5 V → ~0.25 A at 12 V |
| Hall module | ~20 mA at 5 V |
| **Total** | **~1.0–1.3 A at 12 V** |

**VM bulk.** C6 is 470 µF / 25 V with 80 mΩ ESR and an 850 mA ripple rating,
sitting directly beside the StepStick's VM pin, with a 22 µF ceramic (C7)
alongside it for the high-frequency edge. The TMC2209 chops the full coil
current out of VM; undersizing this is the classic way to kill the driver.

**Reverse polarity.** Worth it — barrel bricks vary and the TMC2209 does not
survive reverse VM. A high-side P-FET rather than a series Schottky: the diode
would drop ~0.4 V and burn ~0.4 W at 1 A, and eat the buck's headroom, where
the FET is ~50 mΩ (≈50 mV). The gate is **not** tied to GND — the AO3401A is
only rated V<sub>GS</sub> ±12 V, which a 12 V brick sits right on. R5/R6
(100 k/56 k) park the gate at 0.64 × V<sub>in</sub> below the source: −7.7 V at
12 V in, −9.6 V even at a 15 V brick. Fully enhanced, safely inside the rating.

**Buck.** TPS563201, 4.5–17 V in, 3 A, D-CAP2 — stable on all-ceramic output
with no external compensation and no catch diode. V<sub>out</sub> = 0.768 ×
(1 + 56 k/10 k) = **5.07 V**. Its EN pin is abs-max 6 V so it gets its own
divider off the 12 V rail (4.3 V at 12 V in, 5.4 V at 15 V) rather than a
pull-up to V<sub>in</sub>.

**Trace widths.** Motor coils, the 12 V spine and VM run at 1.0 mm; 5 V and
the buck power nets at 0.8 mm (0.6 mm where they escape the SOT-23-6); logic
at 0.4 mm. 1.0 mm on 1 oz outer copper carries ~2.5 A at a 10 °C rise, against
a ~0.85 A peak coil current.

> **Do not feed 12 V and USB at once** without thinking about it. The XIAO's
> 5V pin is its VBUS rail, so the buck back-feeds it. For flashing, unplug the
> barrel jack and let USB power the XIAO alone (the motor will not run).

## What to order

`fab-splitflap-driver-nema-v2.zip` → PCBWay, 2-layer, 1.6 mm FR4, HASL or ENIG,
any colour. It conforms comfortably to their standard 2-layer capability:

| Constraint | PCBWay standard | This board |
|---|---|---|
| Min trace / space | 6 mil (0.152 mm) | **15.7 mil (0.4 mm)** trace, 0.2 mm space |
| Min drill | 0.3 mm | **0.3 mm** (vias); smallest THT 0.8 mm |
| Min annular ring | 0.13 mm | **0.15 mm** |
| Board thickness | 1.6 mm | 1.6 mm |
| Layers | 2 | 2 |
| Outline | — | 62 × 76 mm, four 3.2 mm M3 holes |

The M3 mounting holes are cut as inner Edge.Cuts circles (routed, not drilled),
which is how the fab will treat them.

Components: `bom.csv` — every part is LCSC-stocked and pinned by part number.
The three items under *not fitted* (StepStick, XIAO, 12 V PSU) are ordered
separately; the XIAO and StepStick plug into sockets and are not soldered down.

## Assembly notes

Everything is hand-solderable: 0603/0805 passives, SOT-23 and SOT-23-6, and
through-hole connectors. Suggested order — SMD first, tallest THT last:

1. **U1 (TPS563201)** and **Q1** — easiest with nothing else in the way.
2. 0603/0805 passives. **C6 (470 µF) is polarised**: pin 1 is +, and the silk
   marks the negative half. **D1** is polarised too.
3. Sockets J4–J7. Seat them square — a tilted socket makes the modules sit
   crooked. Rows are 15.24 mm apart for both the XIAO and the StepStick.
4. Connectors J1, J2, J3 last.

Then, before plugging anything in:

- Apply 12 V and check **D1 lights** and the XIAO's 5V pin reads ~5.05 V.
- Confirm 3V3 is live on the socket before inserting the StepStick — VIO comes
  from the XIAO, so the driver must never be powered without the XIAO fitted.
- **Set the StepStick's V<sub>ref</sub> pot before running the motor.** The
  board does not break V<sub>ref</sub> out; use the module's own trim pot and
  creep the current up from minimum, per the note in `tmc_spin.py`. On a Watterott-style
  module (0.11 Ω sense, 1.77 A RMS at full scale) 0.6 A/phase RMS works out at
  V<sub>ref</sub> ≈ 0.85 V — but clones vary in sense resistor, so verify
  against your module before trusting that number.
- Insert the StepStick with **pin 1 / pin 9 at the end marked on the silk**.

## Building this from source

```
ato build                                    # twice after adding a component
tools/build_outputs.sh                       # place, route, DRC, renders, fab
tools/build_outputs.sh --quick               # place + DRC only
```

Placement and routing are address-keyed data tables in
`tools/place_and_render.py`, so they survive designator reshuffles. It also
self-checks placement numerically (body overlap, off-board, pad-to-pad) before
writing anything.

atopile's cloud registry was down, so all parts are vendored locally:
`tools/vendor_part.py <LCSC> <DIR>` (easyeda2kicad → faebryk `kicad.convert`),
then `tools/trim_lib_silk.py` clips silkscreen out of pads. Run the trim once
per vendoring — it is not idempotent across repeated runs.

### DRC status

**0 errors, 0 unconnected items, 0 footprint errors.** One warning remains:

```
[silk_overlap] @(53.5, 37.9): Reference field of C4
               @(55.385, 35.325): Segment of C4 on F.Silkscreen
```

This one is spurious. The two items are 3.1 mm apart, and the warning persists
unchanged when C4's reference is moved to 7.25 mm away, and follows the part
when C4 is rotated 180° — i.e. it does not track the actual geometry. It is the
same KiCad text-extent mis-attribution recorded on the v1 board, where DRC
blames the wrong field. Nothing on the silkscreen actually collides; compare
`render/top.png`.
