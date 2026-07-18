# Bench bring-up — what the harness has told us

Notes from driving the single breadboard module ([#11](https://github.com/0x63616c/split-flap/issues/11)
wayfinder, [#9](https://github.com/0x63616c/split-flap/issues/9) bring-up). The
harness itself is `just bench` (ctl's bench screen); the board-side command loop
is `firmware/micropython-spike/bench_board.py`.

## The question

Does *"type a glyph → home once → drive forward to its slot"* feel right when
driving the module — given a 28BYJ-48's awkward maths (**4096 half-steps ÷ 45
slots = 91.02 steps/slot**, not integer), forward-only motion, and a
per-revolution hall re-sync (decision [#3](https://github.com/0x63616c/split-flap/issues/3))?

And, secondarily: what should the control surface be, and what firmware command
surface does it need?

## Findings

- Absolute-step targeting (not relative slot hops) keeps rounding bounded to
  ±0.5 slot and never accumulates — this is the design choice to keep. It lives
  in `tools/ctl/slotplan.go`.
- Even so, the geartrain slips, so the drum must re-home on the hall magnet.
  The per-rev re-sync from #3 is mandatory, not optional.
- The 28BYJ-48 skips steps if slammed from standstill to cruise, so every move
  ramps in and out (`SLOW_US` / `RAMP_STEPS` in the firmware). Bench-measured:
  clean to ~18-22 RPM, stalls ~29 → capped at 16 for margin.
- The hall trips at a repeatable edge, but that edge is *not* where the home
  flap reads cleanly — a fixed mechanical gap. Hence the `NUDGE`-calibrated
  home offset, persisted on the board.
- Nudges below ~10 half-steps get eaten by backlash, so the bench refuses them
  rather than pretending they moved something.
- **Open (needs the bench + Calum):** how often must it re-home in practice?

## Control surface

Answered: a terminal harness, now `ctl bench`. The firmware command surface it
settled on — `HOME` / `ZERO` / `GOTO` / `POS` / `HALL` / `SPEED` / `NUDGE` /
`OFFSET` / `RESET` / `PING` — is documented in the firmware file's header.
