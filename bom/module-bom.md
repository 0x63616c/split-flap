# BOM — single split-flap module (prototype)

Starter BOM for one module. Status: **have** = on hand (see `docs/inventory.md`), **need** = must buy/decide, **print** = self-designed 3D print, **tbd** = depends on an open design decision.

## Electronics

| # | Item | Qty/module | Status | Notes |
|---|---|---|---|---|
| 1 | Seeed XIAO ESP32-C6 | 1 | have | Controller (prototype: one per module; multi-module topology TBD) |
| 2 | 28BYJ-48 5V stepper | 1 | have | Drum drive |
| 3 | ULN2003 driver board | 1 | have | Prototype uses breakout; final wiring TBD |
| 4 | A3144 Hall-effect sensor | 1 | have | Homing; senses drum magnet once per rev |
| 5 | 6×3 mm magnet (homing) | 1 | have | Mounts in/on drum |
| 6 | 400-pt breadboard | 1 | have | Prototype wiring only |
| 7 | Hookup wire / jumpers | — | need | Not confirmed in inventory |
| 8 | 5V power supply | 1 | tbd | USB VBUS may suffice for one module; measure stepper current draw. Shared PSU sizing is a multi-module (out-of-map) question |

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
