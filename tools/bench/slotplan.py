"""Split-flap slot planner — the PORTABLE bit of the bench prototype.

This is the one part worth keeping: pure functions, no I/O, no serial, no
terminal. The TUI shell (bench_ui.py) and, later, the real firmware call into
this; nothing flows the other way. Lift it into the firmware command loop once
the model feels right.

THE QUESTION (wayfinder #11): does "type a glyph -> home -> drive forward to its
slot" feel right on real hardware, given a 28BYJ-48's awkward numbers?

The awkward number that makes this non-trivial:

    4096 half-steps / rev  /  45 slots  =  91.02...  steps/slot   (NOT integer)

So a slot boundary almost never lands on a whole step. Two ways to cope:

  (a) move RELATIVE, slot-by-slot, rounding each hop  -> error accumulates,
      the drum walks off over many moves.
  (b) always compute the ABSOLUTE target step from home  -> rounding is bounded
      to +/-0.5 slot forever, never accumulates.  <-- we do this.

Even with (b), the gear train slips, so per the conventions decision (#3) the
drum RE-HOMES on the hall magnet every revolution and snaps its step counter
back to 0. That resync is modelled here as a pure fact (home is step 0); the
shell decides when to actually re-home.

28BYJ-48 is driven forward-only (reversing loses steps to backlash), so a move
is always the forward distance around the ring, mod one rev.
"""

# David Kingsman drum order, non-umlaut variant: blank, A-Z, $ & #, 0-9, : . - ? !
# ($ & # take the umlaut slots.) This is the FIXED physical flap order round the
# drum — the sequence the window shows as the drum turns forward.
GLYPHS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ$&#0123456789:.-?!"
N_SLOTS = len(GLYPHS)          # 45
STEPS_PER_REV = 4096           # 28BYJ-48 half-step, matches the spike firmware
BLANK = " "

# WHICH flap the hall magnet sits opposite = which glyph the drum shows at home
# (step 0). Set by assembly, not software — so you DECLARE it here (or live, via
# set_home_glyph / the UI's .homeglyph). Default 0 = blank. Everything the module
# plans is measured in "slots forward from home", so this one number rotates the
# whole glyph<->slot mapping without moving the motor.
HOME_INDEX = 0

# Chars the UI lets you type that are NOT on this drum. '$' '#' '.' ARE on it
# now; only '£' stays off.
OFF_DRUM = set("£")


class NotOnDrum(Exception):
    """Typed glyph is valid input but has no slot on the current 45-drum."""


def normalise(ch):
    """Fold user input to a drum glyph: upper-case; '' / '_' mean blank."""
    if ch in ("", "_", " "):
        return BLANK
    return ch.upper()


def set_home_glyph(ch):
    """Declare which glyph the drum shows when homed. Rotates the whole
    glyph<->slot mapping; moves no motor. Returns the glyph. Raises NotOnDrum."""
    global HOME_INDEX
    g = normalise(ch)
    if g in OFF_DRUM:
        raise NotOnDrum(g)
    i = GLYPHS.find(g)
    if i < 0:
        raise NotOnDrum(ch)
    HOME_INDEX = i
    return g


def home_glyph():
    return GLYPHS[HOME_INDEX]


def glyph_to_slot(ch):
    """Glyph char -> slot index (slots FORWARD FROM HOME). Raises NotOnDrum."""
    g = normalise(ch)
    if g in OFF_DRUM:
        raise NotOnDrum(g)
    i = GLYPHS.find(g)
    if i < 0:
        raise NotOnDrum(ch)
    return (i - HOME_INDEX) % N_SLOTS


def slot_to_glyph(slot):
    """Slot (slots forward from home) -> glyph now in the window."""
    return GLYPHS[(slot + HOME_INDEX) % N_SLOTS]


def target_step(slot):
    """Absolute half-step from home for a slot's centre (bounded rounding)."""
    return round(slot * STEPS_PER_REV / N_SLOTS) % STEPS_PER_REV


def forward_steps(cur_step, tgt_step):
    """Forward-only distance (half-steps) from cur_step to tgt_step, mod 1 rev."""
    return (tgt_step - cur_step) % STEPS_PER_REV


def nearest_slot(cur_step):
    """Which slot the drum is closest to, given an absolute step position."""
    return round(cur_step * N_SLOTS / STEPS_PER_REV) % N_SLOTS


def plan(cur_step, ch):
    """Plan a move to glyph `ch` from absolute position `cur_step`.

    Returns (target_slot, target_step, steps_forward, crosses_home).
    `crosses_home` is True when the forward path passes step 0 -> a chance to
    re-home and resync the counter mid-move.
    """
    slot = glyph_to_slot(ch)
    tgt = target_step(slot)
    fwd = forward_steps(cur_step, tgt)
    crosses_home = cur_step != 0 and (cur_step + fwd) >= STEPS_PER_REV
    return slot, tgt, fwd, crosses_home
