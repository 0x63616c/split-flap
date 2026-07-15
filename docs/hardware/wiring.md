# Breadboard wiring — single-module prototype

Confirmed working 2026-07-14. Board: **Seeed XIAO ESP32-C6**. This is the
breadboard bring-up config (wayfinder ticket #9); pins may change as the design
firms up.

## Pin map

| From (XIAO) | GPIO | To | Purpose |
|---|---|---|---|
| D0 | GPIO0 | ULN2003 **IN1** | stepper coil 1 |
| D1 | GPIO1 | ULN2003 **IN2** | stepper coil 2 |
| D2 | GPIO2 | ULN2003 **IN3** | stepper coil 3 |
| D3 | GPIO21 | ULN2003 **IN4** | stepper coil 4 |
| D8 | GPIO19 | A3144 **OUT** | hall homing (internal pull-up, 0 = magnet) |
| VBUS | 5V | ULN2003 **+**, A3144 **VCC** | 5V power |
| GND | — | ULN2003 **−**, A3144 **GND** | shared ground |

Motor plugs into the ULN2003's white JST socket (keyed, one way).

## Diagram

```
                XIAO ESP32-C6
              ┌───────────────┐
   USB-C ═════╡               │
              │           D0  ├──────────► IN1 ┐
              │           D1  ├──────────► IN2 │   ULN2003
              │           D2  ├──────────► IN3 │   driver board
              │           D3  ├──────────► IN4 ┘      │
              │               │                   JST │ (5-wire)
              │           D8  ◄───── OUT           ┌───┴────┐
              │               │       │            │28BYJ-48│
              │  VBUS(5V) ●───┼───┬───┤ VCC        │ stepper│
              │               │   │   │ (A3144     └────────┘
              │  GND      ●───┼─┐ │   │  hall)
              └───────────────┘ │ │   └─ GND ─┐
                                │ │           │
             5V rail  ●─────────┼─┴───► ULN2003 (+)
             GND rail ●─────────┴─────► ULN2003 (−)  + A3144 GND
```

## Notes / gotchas

- **A3144 VCC must be on 5V (VBUS), not 3.3V** — sensor needs ≥4.5V. Output is
  open-collector, only sinks to GND, so the ESP32 internal pull-up to 3.3V keeps
  the GPIO safe (never sees 5V). **No external resistor needed.**
- Getting VCC on the `−` rail instead of `+` = silent sensor; the GPIO still
  reads 1 via pull-up (floating OUT looks like idle). Verify VCC↔GND ≈ 5V at the
  sensor legs with a multimeter before suspecting the pin or magnet.
- Hall sensor is a **HW-477 module** (marking HW477V02), not a bare A3144 chip:
  A3144 + onboard LED(s) (the red light = output-activated indicator, normal),
  often an LM393 comparator + sensitivity potentiometer. Use the **DO** (digital
  out) pin → D8.
- **LATCHING behavior confirmed** (2026-07-14, measured on D8): one magnet pole
  latches output LOW and it HOLDS after the magnet leaves; the opposite pole
  resets it HIGH. NOT a plain unipolar switch. (The 60s pause-demo *looked* like
  a switch only because waving a disc magnet sweeps both poles through the field,
  causing repeated set/reset.)
- **Homing implication**: a single one-pole magnet on the drum will latch on the
  first pass and never reset = broken homing. Use **two magnets at the home mark
  with opposite poles side-by-side** (sensor sees SET-then-RESET = one clean
  pulse/rev), or N and S 180° apart (toggle every half-rev). Latch index is
  actually more noise-immune than a switch once set up right.
- All 10 FORIOT "A3144" units are these same HW-477 modules and all latch
  (the "A3144" stamp is misleading — genuine A3144 is a switch; this is a latch
  clone). Swapping units won't change behavior. For a true single-magnet switch,
  buy a known-good unipolar part (Allegro A3144, US5881, AH1815, SS443).
- Hall reads **1 = clear, 0 = magnet present**.
- If the module has a **potentiometer** (brass screw), it tunes trigger
  distance — useful for setting the magnet-to-sensor gap on the drum.
- Motor shares ground with the board — required.
- Pin D8 (SPI_SCK) choice is weak; revisit if SPI is needed for multi-module
  scaling. D0–D3 keep I2C/UART/other-SPI free.
- Speed: 4096 half-steps/rev; clean to ~18–22 RPM unloaded, stalls ~29 RPM.

See `firmware/micropython-spike/main.py` for the matching pin definitions.
