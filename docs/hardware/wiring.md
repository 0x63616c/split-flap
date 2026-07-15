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
- **Unipolar switch confirmed** (2026-07-14, measured on D8): output goes LOW
  near one magnet pole and self-releases to HIGH when the magnet moves away —
  verified by it reading 1 steadily with magnets removed. Behaves as a proper
  switch; single-magnet homing works.
- **Earlier "latch" scare was a magnet-size artifact**: a too-large/too-close
  magnet keeps the field above the sensor's release threshold, so hand-pulling it
  "away" never releases and flipping to the opposite pole is what trips it —
  looks exactly like a latch but isn't. Also had runs stuck at 0 because a magnet
  was still in range. Lesson: for homing, **don't oversize the home magnet and
  keep a sensible air gap** so the field clears the release threshold between
  passes. On a rotating drum the magnet sweeps away on its own = clean release
  each rev.
- Hall reads **1 = clear, 0 = magnet present**.
- If the module has a **potentiometer** (brass screw), it tunes trigger
  distance — useful for setting the magnet-to-sensor gap on the drum.
- Motor shares ground with the board — required.
- Pin D8 (SPI_SCK) choice is weak; revisit if SPI is needed for multi-module
  scaling. D0–D3 keep I2C/UART/other-SPI free.
- Speed: 4096 half-steps/rev; clean to ~18–22 RPM unloaded, stalls ~29 RPM.

See `firmware/micropython-spike/main.py` for the matching pin definitions.
