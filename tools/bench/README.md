# Bench control UI — throwaway prototype (wayfinder #11)

**Throwaway.** Answers one question, then most of it gets deleted. See
[#11](https://github.com/0x63616c/split-flap/issues/11).

## The question

Does *"type a glyph → home once → drive forward to its slot"* feel right when
driving the single breadboard module — given a 28BYJ-48's awkward maths
(**4096 half-steps ÷ 37 slots = 110.7 steps/slot**, not integer), forward-only
motion, and a per-revolution hall re-sync (decision [#3](https://github.com/0x63616c/split-flap/issues/3))?

And, secondarily: what should the control surface be (terminal vs web), and what
firmware command surface does it need?

## What's here

- **`slotplan.py`** — the *keeper*. Pure slot maths: glyph → absolute
  step-from-home, forward-only distance, off-drum detection. No I/O. This lifts
  into the real firmware once the model feels right.
- **`bench_ui.py`** — the *throwaway* terminal shell. Type a glyph, watch state.
- **`../../firmware/micropython-spike/bench_board.py`** — throwaway firmware
  command loop so the board is driveable. `just board` copies it onto the board
  as `:main.py`; the board then boots straight into the serial command loop.

## Run

Sim (no hardware — answers the logic question now):

```
python tools/bench/bench_ui.py
```

Real board at the bench (recipes pull pyserial/mpremote via `uv run --with`):

```
just board     # terminal 1: load the command loop onto the board
just drive      # terminal 2: drive it
```

Port auto-picks the first `cu.usbmodem*`; override with `just drive port=/dev/cu.usbmodemXXXX`.

Then type: a glyph (`A`–`Z`, `0`–`9`, empty = blank) to drive there;
`.home` to re-home and zero the counter; `.pos`; `.quit`/`q`.

`$ £ .` are accepted as input but reported off-drum — the 37-vs-40 glyph-set is
a separate decision; `slotplan.GLYPHS` is the one line to change when it lands.

## Findings so far (sim)

- Absolute-step targeting (not relative slot hops) keeps rounding bounded to
  ±0.5 slot and never accumulates — this is the design choice to keep.
- Even so, the geartrain slips; the harness shows `slip` climbing each time the
  drum sweeps past home without re-homing, and `.home` wiping it. Confirms the
  per-rev re-sync from #3 is mandatory, not optional.
- **Open (needs the bench + Calum):** does open-loop forward positioning land
  cleanly on real hardware, and how often must it re-home in practice?
