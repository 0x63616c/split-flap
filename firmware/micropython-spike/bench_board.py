# Self-contained bench command loop — THROWAWAY firmware (wayfinder #11).
#
# Upload this to the board as main.py so it boots STANDALONE into a serial
# command loop. The host (tools/bench/bench_ui.py, via `just drive`) is then the
# SOLE owner of the USB serial port.
#
#   just board     # cp this -> :main.py, reset, disconnect (frees the port)
#   just drive     # pyserial opens the now-free port and drives it
#   just unboard   # delete :main.py to get a plain REPL back
#
# Why self-contained (no `import main`): mpremote can only hold the port OR the
# host can — not both. So the board runs alone; nothing else touches the port.
#
# Protocol (ASCII, one command per line, replies newline-terminated):
#   HOME          -> OK slot=0 step=0        | ERR no-magnet
#                                            (seek hall edge, then step the saved
#                                            offset onto the home flap = step 0)
#   ZERO          -> OK slot=0 step=0        (declare here = home, NO seek —
#                                            lets you drive with no magnet mounted)
#   GOTO <step>   -> OK slot=<s> step=<n>    (forward-only to absolute step)
#   POS           -> OK slot=<s> step=<n>
#   HALL          -> OK hall=<0|1>          (raw DO pin: 0 = magnet present)
#   SPEED <rpm>   -> OK rpm=<n>              (integer 1..16; sets motor speed)
#   NUDGE <n>     -> OK slot=0 step=0 offset=<o>  (calibrate: move n half-steps,
#                                            signed, and bake into the saved home
#                                            offset. here stays = home.)
#   OFFSET        -> OK offset=<o>           (report saved home offset)
#   RESET         -> OK offset=0              (wipe saved offset back to 0)
#   PING          -> OK pong rpm=<n>         (liveness, moves nothing)
#   other         -> ERR bad-cmd

import sys
import time
from machine import Pin

# --- hardware (matches main.py spike + docs/hardware/wiring.md) ---
COILS = [Pin(n, Pin.OUT, value=0) for n in (0, 1, 2, 21)]   # ULN2003 IN1..IN4
HALL = Pin(19, Pin.IN, Pin.PULL_UP)                         # 0 = magnet present

# Half-step sequence. If the drum spins the WRONG way, reverse this list
# ([::-1]) — the whole board is forward-only, so this just redefines which
# physical direction "forward" is; homing + GOTO follow automatically.
SEQ = [(1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
       (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1)][::-1]
STEPS_PER_REV = 4096
N_SLOTS = 45          # Kingsman drum (non-umlaut) — must match slotplan.GLYPHS length

# Speed is settable at runtime via `SPEED <rpm>`, integer, 1..MAX_RPM.
# Bench-measured: clean to ~18-22 RPM, stalls ~29 -> cap at 16 for margin.
MAX_RPM = 16
DEFAULT_RPM = 12

_cur_step = 0            # absolute half-step from home, 0..STEPS_PER_REV-1
_homed = False
_rpm = DEFAULT_RPM

# The hall trips at a repeatable edge, but that edge is NOT where the home flap
# reads cleanly — fixed mechanical gap. HOME_OFFSET = extra half-steps to step
# forward past the edge onto the home flap. Persisted so it survives reboot and
# `just board` reflashes. Calibrate live with NUDGE.
OFFSET_FILE = "home_offset.txt"


def _load_offset():
    try:
        with open(OFFSET_FILE) as f:
            return int(f.read().strip()) % STEPS_PER_REV
    except (OSError, ValueError):
        return 0


def _save_offset(n):
    with open(OFFSET_FILE, "w") as f:
        f.write(str(n))


_offset = _load_offset()


def _delay_us():
    return 60_000_000 // (STEPS_PER_REV * _rpm)   # per half-step, from RPM


def _apply(i):
    for p, v in zip(COILS, SEQ[i % 8]):
        p.value(v)


def _off():
    for p in COILS:
        p.value(0)


def _slot(step):
    return round(step * N_SLOTS / STEPS_PER_REV) % N_SLOTS


def home(max_steps=STEPS_PER_REV * 2):
    """Clear the magnet field, seek it, then step _offset onto the home flap.

    Returns steps-to-edge, or -1 if the magnet was never found."""
    i = 0
    while HALL.value() == 0 and i < max_steps:     # back off if starting on it
        _apply(-i); time.sleep_us(_delay_us()); i += 1
    if i >= max_steps:
        _off(); return -1
    for j in range(max_steps):                     # seek the magnet
        _apply(j); time.sleep_us(_delay_us())
        if HALL.value() == 0:
            for k in range(_offset):               # walk edge -> home flap
                _apply(j + 1 + k); time.sleep_us(_delay_us())
            _off(); return j + 1
    _off(); return -1


def _forward_to(target):
    global _cur_step
    n = (target - _cur_step) % STEPS_PER_REV
    base = _cur_step
    for k in range(1, n + 1):
        _apply(base + k); time.sleep_us(_delay_us())
    _off()
    _cur_step = target % STEPS_PER_REV


def _ok(extra=""):
    print("OK slot={} step={}{}".format(_slot(_cur_step), _cur_step,
                                         (" " + extra) if extra else ""))


def _err(msg):
    print("ERR " + msg)


def _nudge(n):
    """Move n half-steps (signed) and fold it into the saved home offset.
    'Here' stays home (_cur_step unchanged) — you're correcting where home IS."""
    global _offset
    base = _cur_step
    for k in range(1, abs(n) + 1):
        _apply(base + (-k if n < 0 else k)); time.sleep_us(_delay_us())
    _off()
    _offset = (_offset + n) % STEPS_PER_REV
    _save_offset(_offset)


def loop():
    global _cur_step, _homed, _rpm, _offset
    print("bench_board ready")
    while True:
        line = sys.stdin.readline()
        if not line:
            continue
        parts = line.strip().split()
        if not parts:
            continue
        op = parts[0].upper()
        if op == "PING":
            print("OK pong rpm={}".format(_rpm))
        elif op == "SPEED" and len(parts) == 2:
            try:
                r = int(parts[1])
            except ValueError:
                _err("bad-arg"); continue
            if r < 1 or r > MAX_RPM:
                _err("range-1-{}".format(MAX_RPM)); continue
            _rpm = r
            print("OK rpm={}".format(_rpm))
        elif op == "HOME":
            if home() < 0:
                _err("no-magnet")
            else:
                _cur_step = 0; _homed = True; _ok()
        elif op == "ZERO":
            _cur_step = 0; _homed = True; _ok()
        elif op == "GOTO" and len(parts) == 2:
            if not _homed:
                _err("not-homed"); continue
            try:
                target = int(parts[1]) % STEPS_PER_REV
            except ValueError:
                _err("bad-arg"); continue
            _forward_to(target); _ok()
        elif op == "POS":
            _ok()
        elif op == "NUDGE" and len(parts) == 2:
            if not _homed:
                _err("not-homed"); continue
            try:
                n = int(parts[1])
            except ValueError:
                _err("bad-arg"); continue
            _nudge(n); _ok("offset={}".format(_offset))
        elif op == "OFFSET":
            print("OK offset={}".format(_offset))
        elif op == "RESET":
            _offset = 0; _save_offset(0)
            print("OK offset=0")
        elif op == "HALL":
            print("OK hall={}".format(HALL.value()))
        else:
            _err("bad-cmd")


if __name__ == "__main__":
    loop()
