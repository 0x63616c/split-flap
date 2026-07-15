# BOM — single split-flap module (prototype)

Starter BOM for one module. Status: **have** = on hand (see `docs/inventory.md`), **need** = must buy/decide, **print** = self-designed 3D print, **tbd** = depends on an open design decision.

## Electronics

| # | Item | Qty/module | Status | Notes |
|---|---|---|---|---|
| 1 | Seeed XIAO ESP32-C6 | 1 | have | Controller (prototype: one per module; multi-module topology TBD) |
| 2 | 28BYJ-48 5V stepper | 1 | have | Drum drive |
| 3 | ULN2003 driver board | 1 | have | Prototype uses breakout; final wiring TBD |
| 4 | Hall sensor (FORIOT "A3144" = HW-477 module) | 1 | have | Homing; unipolar switch (self-releases when magnet moves away). Use DO pin, 5V VCC. See `docs/hardware/wiring.md` |
| 5 | 6×3 mm magnet (homing) | 1 | have | Single magnet on drum, one pulse/rev. **Don't oversize / keep sensible air gap** — a too-strong/too-close magnet won't drop below the sensor's release threshold and looks stuck-on. On a rotating drum it releases fine as the magnet sweeps away |
| 6 | 400-pt breadboard | 1 | have | Prototype wiring only |
| 7 | Hookup wire / jumpers | — | need | Not confirmed in inventory |
| 8 | 5V power supply | 1 | tbd | Prototype ran fine on USB **VBUS** (board + one 28BYJ-48 via ULN2003, no brownout) 2026-07-14. Actual stepper current still un-measured with MM420. Shared PSU sizing is a multi-module (out-of-map) question |

## Fasteners

| # | Item | Qty/module | Status | Notes |
|---|---|---|---|---|
| 9 | M3 heat-set inserts | tbd | have | Count set by mechanism geometry (#7) |
| 10 | M3 button-head screws | tbd | have | Lengths set by mechanism geometry (#7) |

## Printed parts (self-designed, build123d → 3MF → Bambu Studio)

| # | Item | Qty/module | Status | Notes |
|---|---|---|---|---|
| 11 | Drum halves / spool | 1 set | print | Geometry TBD (#7) |
| 12 | Flaps | 37+ | print/tbd | 37 glyph positions; flap count = 2× positions if split-card style — depends on drum geometry (#7). Glyph application method open (#8) |
| 13 | Side plates / frame | 1 set | print | Geometry TBD (#7) |
| 14 | Motor mount | 1 | print | 28BYJ-48 bolt pattern |
| 15 | Hall sensor mount | 1 | print | Position depends on drum geometry (#7) |

## Open items feeding this BOM

- Module mechanism geometry — [#7](https://github.com/0x63616c/split-flap/issues/7): fixes printed-part list, fastener counts/lengths, flap count.
- Charset artwork / glyph application — [#8](https://github.com/0x63616c/split-flap/issues/8): may add materials (stickers, second filament use).
- Firmware stack — [#5](https://github.com/0x63616c/split-flap/issues/5): no BOM impact expected.

## Bench-verified (2026-07-14)

Breadboard bring-up (#9) proven: XIAO flashes over USB, 28BYJ-48 spins both dirs
(~18–22 RPM clean unloaded, stalls ~29), hall homing signal reads on D8, closed
loop demoed. Wiring + pinout in `docs/hardware/wiring.md`; spike firmware in
`firmware/micropython-spike/`. Printer confirmed **P2S with AMS** → per-object
multi-color flap inlays viable (affects #8 glyph method).
