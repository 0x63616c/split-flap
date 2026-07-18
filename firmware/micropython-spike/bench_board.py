# Self-contained bench command loop — THROWAWAY firmware (wayfinder #11).
#
# Upload this to the board as main.py so it boots STANDALONE into a serial
# command loop. The host (ctl's bench screen) is then the SOLE owner of the USB
# serial port.
#
#   just bench   # menu -> "flash & connect": free port, cp this to :main.py,
#                # reset, then drive it
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
#   GOTO <step> [slow] -> OK slot=<s> step=<n> [resync=<c>]  (forward-only to abs
#                                            step; ramped, or flat SLOW_US if the
#                                            'slow' arg is given; resync=<c> present
#                                            when the move swept the magnet and
#                                            snapped the counter to the hall edge)
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
N_SLOTS = 45          # Kingsman drum (non-umlaut) — must match ctl's benchGlyphs length

# Speed is settable at runtime via `SPEED <rpm>`, integer, 1..MAX_RPM.
# Bench-measured: clean to ~18-22 RPM, stalls ~29 -> cap at 16 for margin.
MAX_RPM = 16
DEFAULT_RPM = 12

# Accuracy: the 28BYJ-48 is open-loop, so any step it silently drops is lost
# until the next home. Two guards below fight that:
#   - SLOW_US / RAMP_STEPS: ease every move in and out of speed. The motor skips
#     steps if slammed straight to cruise from standstill (and on abrupt stops),
#     so we ramp SLOW_US -> cruise -> SLOW_US over RAMP_STEPS at each end.
#   - resync-on-pass (see _forward_to): whenever a move sweeps past the hall
#     magnet, snap the step counter back to the known edge — free re-zeroing that
#     stops drift accumulating between explicit HOMEs.
SLOW_US = 2600          # start/stop + homing crawl (~5.6 RPM): crisp, no skips
RAMP_STEPS = 400        # half-steps to ramp up / down at each end of a move
CLEAR_MARGIN = 120      # when homing FROM inside the field, back off this far past
                        # its edge before seeking — a clean run-up, no in-place
                        # buzz from re-entering the same wide magnet field

_cur_step = 0            # absolute half-step from home, 0..STEPS_PER_REV-1
_homed = False
_rpm = DEFAULT_RPM

# The hall trips at a repeatable edge, but that edge is NOT where the home flap
# reads cleanly — fixed mechanical gap. HOME_OFFSET = extra half-steps to step
# forward past the edge onto the home flap. Persisted so it survives reboot and
# a reflash. Calibrate live with NUDGE.
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
    return 60_000_000 // (STEPS_PER_REV * _rpm)   # per half-step, from RPM (cruise)


def _ramp_delay(k, n, cruise):
    """Trapezoidal speed profile: delay for step k of an n-step move.
    Eases SLOW_US -> cruise -> SLOW_US. Short moves stay slow throughout."""
    if cruise >= SLOW_US:               # already slow -> nothing to ramp
        return cruise
    ramp = min(RAMP_STEPS, n // 2)
    if ramp <= 0:
        return SLOW_US
    edge = min(k, n - 1 - k)            # steps from the nearer end
    if edge >= ramp:
        return cruise
    return SLOW_US + (cruise - SLOW_US) * edge // ramp


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

    Runs at SLOW_US throughout: homing is infrequent and a slow approach makes
    the hall trip crisp and repeatable (no detection latency at speed), which is
    what every other move's absolute targeting is measured against.

    `ph` is a single continuous phase counter so back-off -> seek never jumps the
    coil phase (that jump is a jerk/buzz). If we START inside the field we back
    off past it by CLEAR_MARGIN, so the forward seek gets a clean single approach
    instead of oscillating on the same edge.
    Returns steps-to-edge, or -1 if the magnet was never found."""
    ph = 0
    if HALL.value() == 0:                           # started inside the field
        steps = 0
        while HALL.value() == 0 and steps < max_steps:
            ph -= 1; _apply(ph); time.sleep_us(SLOW_US); steps += 1
        if steps >= max_steps:
            _off(); return -1
        for _ in range(CLEAR_MARGIN):               # back off clear of the field
            ph -= 1; _apply(ph); time.sleep_us(SLOW_US)
    for j in range(max_steps):                      # seek the magnet, forward
        ph += 1; _apply(ph); time.sleep_us(SLOW_US)
        if HALL.value() == 0:
            for _ in range(_offset):                # walk edge -> home flap
                ph += 1; _apply(ph); time.sleep_us(SLOW_US)
            _off(); return j + 1
    _off(); return -1


def _forward_to(target, slow=False):
    """Drive forward to an absolute step. Ramps speed in/out, and resyncs the
    counter to the hall edge whenever the move sweeps past the magnet.

    slow=True holds SLOW_US flat the whole way (no ramp) — used for the home
    settle so a .home is one constant slow speed end to end.

    Returns the net counter correction (steps) applied by any resync, for logging.
    `ph` is a CONTINUOUS phase counter for _apply so a resync never phase-jumps
    the coils; `pos` is the absolute step that resync corrects."""
    global _cur_step
    n = (target - _cur_step) % STEPS_PER_REV
    cruise = SLOW_US if slow else _delay_us()      # cruise==SLOW_US -> _ramp_delay stays flat
    edge_abs = (STEPS_PER_REV - _offset) % STEPS_PER_REV  # counter value at the hall edge
    ph = _cur_step
    pos = _cur_step
    prev_hall = HALL.value()
    correction = 0
    for k in range(n):
        ph += 1
        pos = (pos + 1) % STEPS_PER_REV
        _apply(ph)
        time.sleep_us(_ramp_delay(k, n, cruise))
        h = HALL.value()
        if prev_hall == 1 and h == 0:      # just entered the field -> at the edge
            correction += (edge_abs - pos) % STEPS_PER_REV
            pos = edge_abs
        prev_hall = h
    _off()
    _cur_step = pos
    return correction


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
        elif op == "GOTO" and len(parts) >= 2:
            if not _homed:
                _err("not-homed"); continue
            try:
                target = int(parts[1]) % STEPS_PER_REV
            except ValueError:
                _err("bad-arg"); continue
            slow = len(parts) >= 3 and parts[2].lower() == "slow"
            corr = _forward_to(target, slow)
            _ok("resync={}".format(corr) if corr else "")
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
