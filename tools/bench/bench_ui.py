#!/usr/bin/env python3
"""Bench control UI — THROWAWAY prototype (wayfinder #11).

A tiny terminal harness to drive the single breadboard split-flap module during
#9 bring-up. Type a glyph, the module homes (once) then drives forward to that
glyph's slot. The slot maths live in slotplan.py (the keeper); this file is the
disposable shell around it.

TWO transports:
  --sim     (default) fake motor in memory. Answers the LOGIC question with no
            hardware: watch the step counter, forward wrap, and per-rev hall
            resync. Zero dependencies.
  --serial /dev/tty.usbmodemXXXX   drive the real board over USB. Needs pyserial
            and the firmware command loop (firmware/micropython-spike/bench_board.py)
            running on the board.

Run:
    python tools/bench/bench_ui.py                 # sim
    python tools/bench/bench_ui.py --serial /dev/tty.usbmodem1101

Type at the prompt (commands start with /; anything else is glyphs to display):
    A  1  m           -> drive to one glyph (lowercase auto-caps)
    HELLO  123123     -> drive through a STRING, 1s dwell per glyph
    (empty / _)       -> blank slot
    up-arrow          -> recall previous input (readline history)
    /help             -> full help screen
    /home             -> re-home on the hall magnet, then settle on blank
    /homecal          -> re-home but STOP on the home flap (to read + calibrate it)
    /zero             -> declare here = home, no seek (no magnet mounted)
    /pos              -> re-query position
    /hall             -> read hall DO pin (0 = magnet present, 1 = clear)
    /speed <1-16>     -> set motor RPM (firmware cap 16)
    /nudge <±n>       -> calibrate home: move n half-steps (min ±10), into offset
    /sethome <g>      -> declare which glyph the home flap shows (rotates the map)
    /reset            -> wipe calibration: offset 0 + home glyph blank
    /quit  /  q       -> exit

Calibrating a module once (do it in this order):
    /reset            offset 0, home glyph blank
    /homecal          seek the magnet and STOP on the home flap
    /nudge 20         centre the char in the window (may roll onto the next flap)
    /sethome 2        READ the flap and declare it — whatever it physically shows
Now typing 'C' drives to C; /home re-homes and settles on blank. Nudge lives on
the board (survives reboot/reflash); the home glyph is saved beside this script.

The UI glyph is a MODEL (home glyph + step count), not a camera — if it disagrees
with the real drum, the home glyph is set wrong. Fix with /homecal + /sethome.
"""

import os
import sys
import time

try:
    import readline  # noqa: F401  — enables up-arrow history + line editing in input()
except ImportError:
    pass

import slotplan as sp

PAUSE_S = 1.0    # dwell between glyphs when a whole string is typed
MAX_RPM = 16     # firmware cap (bench-measured stall margin); integer RPM only
MIN_NUDGE = 10   # smallest nudge that reliably moves the drum; below this the
                 # 28BYJ backlash eats it, so we reject it rather than pretend

# The home glyph (which flap the magnet sits opposite) is a per-module fact set
# at calibration. It's pure planning maths, so we keep it host-side (unlike the
# mechanical nudge offset, which lives on the board). Saved next to this script.
HOME_GLYPH_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "home_glyph.txt")


def load_home_glyph():
    try:
        with open(HOME_GLYPH_FILE) as f:
            sp.set_home_glyph(f.read().strip("\n") or " ")
    except (OSError, sp.NotOnDrum):
        pass


def save_home_glyph(g):
    with open(HOME_GLYPH_FILE, "w") as f:
        f.write(g)

BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RED = "\x1b[31m"
GRN = "\x1b[32m"
YEL = "\x1b[33m"
RST = "\x1b[0m"
CLEAR = "\x1b[2J\x1b[H"


# --------------------------------------------------------------------------
# Transports: same tiny surface (home / goto absolute step / pos). The UI is
# blind to which one it's driving.
# --------------------------------------------------------------------------
class SimTransport:
    """In-memory fake 28BYJ-48 + drum. Models the ONE thing worth seeing:
    the geartrain slips a little each rev, and the hall magnet corrects it on
    re-home. If it didn't, absolute-step targeting would still slowly lie."""

    name = "SIM (no hardware)"

    def __init__(self):
        self.cur_step = 0
        self.homed = False
        self.slip = 0           # accumulated geartrain slip, in steps
        self.homes_missed = 0   # home crossings passed without re-homing
        self.rpm = 12
        self.offset = 0         # saved home offset (steps from hall edge to flap)
        self.log = []

    def speed(self, rpm):
        self.rpm = max(1, min(MAX_RPM, rpm))
        self.log.append(f"{GRN}speed{RST}: {self.rpm} RPM")

    def home(self):
        # Seeking the magnet zeroes the counter AND the real slip.
        self.cur_step = 0
        self.slip = 0
        self.homes_missed = 0
        self.homed = True
        self.log.append(f"{GRN}homed{RST}: hall found, counter := 0")

    def zero(self):
        self.cur_step = 0
        self.homed = True
        self.log.append(f"{GRN}zeroed{RST}: declared here = home (no seek)")

    def nudge(self, n):
        # No real drum in sim; just track the offset so the flow is testable.
        self.offset = (self.offset + n) % sp.STEPS_PER_REV
        self.log.append(f"{GRN}nudge{RST}: {n:+d} -> offset {self.offset} (saved)")

    def reset(self):
        self.offset = 0
        self.log.append(f"{GRN}reset{RST}: offset -> 0")

    def goto(self, tgt_step, steps_forward, crosses_home, slow=False):
        # Deterministic 'slip': each time the drum sweeps past the hall magnet
        # without stopping to re-home, assume the geartrain lost a step. Watch it
        # build across moves, and see /home wipe it. (No RNG — must replay same.)
        if crosses_home:
            self.homes_missed += 1
            self.slip += 1
            self.log.append(f"{YEL}passed home{RST} x{self.homes_missed}: "
                            f"+1 slip (re-home to clear)")
        self.cur_step = tgt_step
        return self.cur_step, self.slip

    def pos(self):
        return self.cur_step, self.slip

    def hall(self):
        # No real sensor in sim — fake it: magnet "present" (0) when the drum
        # sits within half a slot of home (step 0), else clear (1).
        window = sp.STEPS_PER_REV / sp.N_SLOTS / 2
        near = min(self.cur_step, sp.STEPS_PER_REV - self.cur_step) < window
        return 0 if near else 1


class SerialTransport:
    """Talks to firmware/micropython-spike/bench_board.py over USB serial.

    Protocol (newline-delimited, ASCII):
        host -> board:   HOME              GOTO <abs_step>            POS
        board -> host:   OK slot=<s> step=<n>   |   ERR <msg>
    """

    def __init__(self, port, baud=115200):
        try:
            import serial  # pyserial, lazy so sim needs no deps
        except ImportError:
            sys.exit("pyserial not installed. `pip install pyserial` "
                     "(or use --sim).")
        self.name = f"SERIAL {port}"
        self.ser = serial.Serial(port, baud, timeout=25)  # HOME can sweep ~10s
        self.slip = 0
        self.homed = False
        self.cur_step = 0
        self.rpm = 12
        self.offset = 0
        self.log = []
        # Opening the CDC port can auto-reset the ESP32-C6 (DTR/RTS), so the
        # board may be mid-reboot. Wait it out, drain the boot banner, then
        # handshake with PING until it answers.
        time.sleep(1.5)
        self.ser.reset_input_buffer()
        for _ in range(6):
            self.ser.write(b"PING\n")
            reply = self.ser.readline().decode(errors="replace").strip()
            if "pong" in reply:
                self.rpm = self._parse_rpm(reply, self.rpm)
                self.log.append(f"{GRN}board up{RST}: {reply}")
                break
            time.sleep(0.5)
        else:
            sys.exit(f"no response from board on {port}. "
                     "Use `just up` (flashes + drives). Is the port right "
                     "(`just ports`)?")

    def _cmd(self, line):
        self.ser.write((line + "\n").encode())
        reply = self.ser.readline().decode(errors="replace").strip()
        self.log.append(f"{DIM}{line} -> {reply}{RST}")
        if reply.startswith("ERR"):
            raise RuntimeError(reply)
        return reply

    def _parse_step(self, reply):
        for tok in reply.split():
            if tok.startswith("step="):
                return int(tok[5:])
        return 0

    def _parse_rpm(self, reply, default):
        for tok in reply.split():
            if tok.startswith("rpm="):
                return int(tok[4:])
        return default

    def speed(self, rpm):
        rpm = max(1, min(MAX_RPM, rpm))
        self.rpm = self._parse_rpm(self._cmd(f"SPEED {rpm}"), rpm)

    def home(self):
        self.cur_step = self._parse_step(self._cmd("HOME"))
        self.homed = True

    def zero(self):
        self.cur_step = self._parse_step(self._cmd("ZERO"))
        self.homed = True

    def nudge(self, n):
        reply = self._cmd(f"NUDGE {n}")
        for tok in reply.split():
            if tok.startswith("offset="):
                self.offset = int(tok[7:])
        self.cur_step = self._parse_step(reply)

    def reset(self):
        reply = self._cmd("RESET")
        for tok in reply.split():
            if tok.startswith("offset="):
                self.offset = int(tok[7:])

    def goto(self, tgt_step, steps_forward, crosses_home, slow=False):
        cmd = f"GOTO {tgt_step} slow" if slow else f"GOTO {tgt_step}"
        self.cur_step = self._parse_step(self._cmd(cmd))
        return self.cur_step, self.slip

    def pos(self):
        self.cur_step = self._parse_step(self._cmd("POS"))
        return self.cur_step, self.slip

    def hall(self):
        reply = self._cmd("HALL")
        for tok in reply.split():
            if tok.startswith("hall="):
                return int(tok[5:])
        return None


# --------------------------------------------------------------------------
# Shell
# --------------------------------------------------------------------------
def render(t, queue=None):
    cur_step, slip = t.pos()
    slot = sp.nearest_slot(cur_step)
    glyph = sp.slot_to_glyph(slot)
    shown = glyph if glyph != sp.BLANK else "␣"   # make blank visible
    homed = getattr(t, "homed", True)

    out = [CLEAR]
    out.append(f"{BOLD}split-flap bench UI{RST}  {DIM}[{t.name}]{RST}")
    out.append("")
    # queue: glyphs still to drive when a whole string is playing (only if >1 left)
    if queue and len(queue) > 1:
        upcoming = "".join(g if g != " " else "␣" for g in queue)
        out.append(f"  {BOLD}queue{RST}       {YEL}{upcoming[0]}{RST}"
                   f"{DIM}{upcoming[1:]}{RST}   {DIM}({len(queue)} left){RST}")
        out.append("")
    blank_tag = f"   {DIM}(blank){RST}" if glyph == sp.BLANK else ""
    out.append(f"  {BOLD}showing{RST}     {GRN}{BOLD} {shown} {RST}"
               f"   {DIM}(slot {slot}/{sp.N_SLOTS}){RST}{blank_tag}")
    out.append(f"  {BOLD}step{RST}        {cur_step} / {sp.STEPS_PER_REV}"
               f"   {DIM}({sp.STEPS_PER_REV / sp.N_SLOTS:.2f} steps/slot){RST}")
    homed_txt = f"{GRN}yes{RST}" if homed else f"{RED}NO — home first{RST}"
    out.append(f"  {BOLD}homed{RST}       {homed_txt}")
    rpm = getattr(t, "rpm", None)
    if rpm is not None:
        out.append(f"  {BOLD}speed{RST}       {rpm} RPM   {DIM}(/speed 1-{MAX_RPM}){RST}")
    offset = getattr(t, "offset", None)
    if offset is not None:
        out.append(f"  {BOLD}home offset{RST}  {offset} steps   "
                   f"{DIM}(/nudge ±n; min ±{MIN_NUDGE}, backlash eats less){RST}")
    out.append(f"  {BOLD}home glyph{RST}   '{sp.home_glyph()}'   "
               f"{DIM}(/sethome <g> = the flap at home; saved){RST}")
    missed = getattr(t, "homes_missed", 0)
    if slip:
        drift = f"{RED}{slip} steps{RST}  {DIM}over {missed} missed home(s){RST}"
    else:
        drift = f"{DIM}0{RST}"
    out.append(f"  {BOLD}slip{RST}        {drift}   {DIM}(cleared by /home){RST}")
    out.append("")
    # slot ring — GLYPHS is the physical drum order, so highlight the glyph now
    # in the window: index (slot + HOME_INDEX), NOT the raw slot (which is
    # slots-from-home and only equals the index when home glyph is blank).
    here = (slot + sp.HOME_INDEX) % sp.N_SLOTS
    ring = "".join(
        (f"{GRN}{BOLD}{sp.GLYPHS[i]}{RST}" if i == here else f"{DIM}{sp.GLYPHS[i]}{RST}")
        for i in range(sp.N_SLOTS)
    )
    out.append(f"  {ring}")
    out.append("")
    if t.log:
        out.append(f"  {BOLD}log{RST}")
        for line in t.log[-7:]:
            out.append(f"    {line}")
        out.append("")
    out.append(f"  {DIM}type glyphs (A-Z 0-9, e.g. HELLO or 123123 — "
               f"{PAUSE_S:g}s each)   ↑ history{RST}")
    out.append(f"  {DIM}/home  /homecal  /zero  /pos  /hall  /speed <1-{MAX_RPM}>  "
               f"/nudge <±n>  /sethome <g>  /reset  /help  /quit{RST}")
    print("\n".join(out))


def print_help():
    """A full, friendly help screen. Printed WITHOUT a render() clear so it stays
    on screen until the next command."""
    h = f"""
{BOLD}split-flap bench UI — help{RST}

{BOLD}Drive the drum{RST}
  {GRN}A{RST}  {GRN}7{RST}  {GRN}m{RST}        one glyph (lower-case auto-caps)
  {GRN}HELLO{RST}         a whole string — steps through it, {PAUSE_S:g}s per glyph
  {DIM}(empty){RST} / {GRN}_{RST}    a blank flap
  {DIM}↑{RST}             recall previous input (history)

{BOLD}Home & rest{RST}
  {GRN}/home{RST}         seek the hall magnet, then settle on blank. one slow speed.
  {GRN}/homecal{RST}      seek but STOP on the home flap — to read + calibrate it
  {GRN}/zero{RST}         declare 'here = home' with no seek (for a magnet-less bench)

{BOLD}Calibrate a module (once), in order{RST}
  1. {GRN}/reset{RST}                offset 0, home glyph blank
  2. {GRN}/homecal{RST}              land on the home flap and stay
  3. {GRN}/nudge{RST} {DIM}±n{RST}             centre it in the window (min ±{MIN_NUDGE}; may roll to next flap)
  4. {GRN}/sethome{RST} {DIM}<glyph>{RST}      READ the flap, declare what it physically shows
  Then {GRN}/home{RST} rests on blank and typed glyphs land right.
  {DIM}nudge offset lives on the board; home glyph is saved beside this script.{RST}

{BOLD}Inspect{RST}
  {GRN}/pos{RST}          re-query position       {GRN}/hall{RST}   read the hall pin (0 = magnet)
  {GRN}/speed{RST} {DIM}<1-{MAX_RPM}>{RST}  set motor RPM (not persisted; resets on reboot)

{BOLD}Other{RST}
  {GRN}/reset{RST}  wipe calibration    {GRN}/help{RST}  this screen    {GRN}/quit{RST} (or {GRN}q{RST})  exit

{DIM}The 'showing' glyph is a MODEL (home glyph + step count), not a camera. If it
disagrees with the real drum, the home glyph is wrong — fix with /homecal + /sethome.{RST}
"""
    print(h)


def main():
    load_home_glyph()
    args = sys.argv[1:]
    if "--serial" in args:
        port = args[args.index("--serial") + 1]
        t = SerialTransport(port)
    else:
        t = SimTransport()

    render(t)
    while True:
        try:
            # NB: keep the blank line OUT of the readline prompt. A newline in
            # the prompt makes readline miscount the prompt width, so up-arrow
            # history recall redraws one column off and leaves a phantom char.
            print()
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        cmd = raw.lower()
        if cmd in ("/quit", "q"):
            return
        if cmd == "/help":
            print_help()          # NO render() — leave help on screen till next cmd
            continue
        # Transport calls can raise on a serial ERR (e.g. ERR no-magnet, or a
        # board flashed before SPEED existed -> ERR bad-cmd). Surface it in the
        # log instead of crashing the whole UI. `just up` reflashes.
        if cmd in ("/home", "/homecal"):
            try:
                t.home()
                # /homecal STOPS on the home flap so you can read what's physically
                # there and declare it with /sethome. Normal /home then settles to
                # blank (the home flap is only a calibration anchor, not rest state).
                if cmd == "/homecal":
                    t.log.append(f"{YEL}homed on the home flap{RST} — read it, "
                                 f"then {BOLD}/sethome <that glyph>{RST}")
                else:
                    cur_step, _ = t.pos()
                    slot, tgt, fwd, crosses = sp.plan(cur_step, sp.BLANK)
                    if fwd:
                        t.log.append(f"{DIM}homed on '{sp.home_glyph()}', "
                                     f"settling to blank (+{fwd}, slow){RST}")
                        t.goto(tgt, fwd, crosses, slow=True)   # keep /home one speed
            except Exception as e:
                t.log.append(f"{RED}error{RST}: {e}")
            render(t)
            continue
        if cmd == "/zero":
            try:
                t.zero()
            except Exception as e:
                t.log.append(f"{RED}error{RST}: {e}")
            render(t)
            continue
        if cmd == "/pos":
            render(t)
            continue
        if cmd == "/hall":
            try:
                v = t.hall()
                state = (f"{GRN}magnet present{RST}" if v == 0
                         else f"{DIM}clear{RST}")
                t.log.append(f"{BOLD}hall{RST}={v}  {state}")
            except Exception as e:
                t.log.append(f"{RED}error{RST}: {e}")
            render(t)
            continue
        if cmd.startswith("/nudge"):
            bits = raw.split()
            try:
                n = int(bits[1])
            except (IndexError, ValueError):
                t.log.append(f"{RED}usage{RST}: /nudge <±n half-steps>   "
                             f"{DIM}(min ±{MIN_NUDGE}; smaller gets eaten by backlash){RST}")
                render(t); continue
            if abs(n) < MIN_NUDGE:
                t.log.append(f"{RED}refused{RST}: /nudge min ±{MIN_NUDGE} "
                             f"{DIM}({n:+d} is sub-visible — backlash eats it){RST}")
                render(t); continue
            if not getattr(t, "homed", True):
                t.log.append(f"{RED}refused{RST}: not homed — /home or /zero first")
                render(t); continue
            try:
                t.nudge(n)
                deg = abs(n) * 360 / sp.STEPS_PER_REV
                flap = abs(n) * sp.N_SLOTS / sp.STEPS_PER_REV
                t.log.append(f"{DIM}  {n:+d} steps = {deg:.2f}° = {flap:.2f} flap{RST}")
            except Exception as e:
                t.log.append(f"{RED}error{RST}: {e}   "
                             f"{DIM}(board may need `just up` reflash){RST}")
            render(t); continue
        if cmd == "/reset":
            try:
                t.reset()                       # offset -> 0 (board or sim)
                sp.set_home_glyph(" ")          # home glyph -> blank
                try:
                    os.remove(HOME_GLYPH_FILE)
                except OSError:
                    pass
                t.log.append(f"{GRN}reset{RST}: offset 0, home glyph blank "
                             f"{DIM}(re-home + re-calibrate){RST}")
            except Exception as e:
                t.log.append(f"{RED}error{RST}: {e}")
            render(t); continue
        if cmd.startswith("/sethome"):
            bits = raw.split()
            if len(bits) != 2:
                t.log.append(f"{RED}usage{RST}: /sethome <glyph>   "
                             f"{DIM}(the flap showing at home right now){RST}")
                render(t); continue
            try:
                g = sp.set_home_glyph(bits[1])
                save_home_glyph(g)
                t.log.append(f"{GRN}home glyph{RST}: home flap = '{g}' (saved)")
            except sp.NotOnDrum:
                t.log.append(f"{YEL}'{bits[1]}' not on the drum{RST}")
            render(t); continue
        if cmd.startswith("/speed"):
            bits = cmd.split()
            if len(bits) == 2 and bits[1].isdigit() and 1 <= int(bits[1]) <= MAX_RPM:
                try:
                    t.speed(int(bits[1]))
                except Exception as e:
                    t.log.append(f"{RED}error{RST}: {e}   "
                                 f"{DIM}(board may need `just up` reflash){RST}")
            else:
                t.log.append(f"{RED}usage{RST}: /speed <integer 1-{MAX_RPM}>")
            render(t)
            continue
        if cmd.startswith("/"):
            t.log.append(f"{RED}unknown command{RST}: {raw}   {DIM}(/help){RST}")
            render(t)
            continue

        # otherwise: treat the whole input as a STRING of glyphs and step
        # through them one at a time, dwelling PAUSE_S between each — so
        # "123123" drives 1, pause, 2, pause, 3, pause, 1, ...
        if not getattr(t, "homed", True):
            t.log.append(f"{RED}refused{RST}: not homed — run /home or /zero first")
            render(t)
            continue
        seq = list(raw) if raw else [" "]   # bare Enter = one blank
        for idx, ch in enumerate(seq):
            try:
                cur_step, _ = t.pos()
                slot, tgt, fwd, crosses = sp.plan(cur_step, ch)
                t.log.append(
                    f"goto {GRN}{sp.slot_to_glyph(slot)}{RST} "
                    f"slot {slot}: +{fwd} steps -> step {tgt}"
                )
                t.goto(tgt, fwd, crosses)
            except sp.NotOnDrum:
                t.log.append(
                    f"{YEL}'{ch}' not on {sp.N_SLOTS}-slot drum{RST} "
                    f"{DIM}(Kingsman glyph set){RST}"
                )
            except Exception as e:  # serial hiccup etc — prototype, surface it
                t.log.append(f"{RED}error{RST}: {e}")
            render(t, queue=seq[idx:])   # current + everything still to come
            if idx < len(seq) - 1:
                time.sleep(PAUSE_S)


if __name__ == "__main__":
    main()
