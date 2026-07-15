# Split-flap breadboard spike — XIAO ESP32-C6 + ULN2003 + 28BYJ-48 + A3144 hall
#
# THROWAWAY prototype firmware (MicroPython v1.26). Not the final stack —
# firmware-stack decision is wayfinder ticket #5. This just proves the bench
# hardware works: flash, spin, home, beep.
#
# Wiring (see project memory / docs):
#   ULN2003 IN1..IN4 -> D0,D1,D2,D3  (GPIO 0,1,2,21)
#   ULN2003 +/-      -> VBUS(5V)/GND (shared ground with board)
#   A3144 hall: VCC->VBUS(5V), GND->GND, OUT->D8 (GPIO19), internal pull-up
#
# Homing needs the magnet to move WITH the motor (mounted on shaft/drum).
# A stationary hand-held magnet cannot be homed against.

import time
from machine import Pin

# --- pins ---
LED = Pin(15, Pin.OUT)                                   # user LED (active-low)
COILS = [Pin(n, Pin.OUT, value=0) for n in (0, 1, 2, 21)]  # IN1..IN4
HALL = Pin(19, Pin.IN, Pin.PULL_UP)                      # 0 = magnet present

# 8-phase half-step sequence, 4096 half-steps / output rev
SEQ = [(1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
       (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1)]
STEPS_PER_REV = 4096

# Measured on the bench (unloaded): clean up to ~18-22 RPM, stalls by ~29 RPM.
# delay_us between half-steps sets speed; rpm = 60 / (STEPS_PER_REV * delay_us/1e6)
DEFAULT_DELAY_US = 1200  # ~12 RPM, comfortable margin


def _off():
    for p in COILS:
        p.value(0)


def _apply(i):
    for p, v in zip(COILS, SEQ[i % 8]):
        p.value(v)


def spin(revs=1.0, delay_us=DEFAULT_DELAY_US, reverse=False):
    """Open-loop rotate. Positive = one dir, reverse=True = other."""
    n = int(STEPS_PER_REV * revs)
    for i in range(n):
        _apply(-i if reverse else i)
        time.sleep_us(delay_us)
    _off()  # never leave coils energized (heat + power)


def home(delay_us=DEFAULT_DELAY_US, max_steps=STEPS_PER_REV * 2):
    """Rotate until the hall sensor sees the magnet (reads 0).

    If we start already inside the magnet field, first back off until it
    clears, so we land on a repeatable edge. Returns step count to home,
    or -1 if the magnet was never seen (missed / not mounted / too far).
    """
    i = 0
    while HALL.value() == 0 and i < max_steps:   # clear the field first
        _apply(-i)
        time.sleep_us(delay_us)
        i += 1
    if i >= max_steps:
        _off()
        return -1  # never cleared -> magnet stuck in view (e.g. not moving with motor)
    for j in range(max_steps):                   # then seek the magnet
        _apply(j)
        time.sleep_us(delay_us)
        if HALL.value() == 0:
            _off()
            return j + 1
    _off()
    return -1


def beep(freq=2500, ms=120):
    """No buzzer on hand: vibrate one coil pair as a tone. No net rotation."""
    half = int(500000 / freq)
    for _ in range(int(ms * 1000 / (2 * half))):
        COILS[0].value(1); COILS[2].value(0); time.sleep_us(half)
        COILS[0].value(0); COILS[2].value(1); time.sleep_us(half)
    _off()


def heartbeat():
    """Triple-blink forever = this firmware is loaded and running."""
    while True:
        for _ in range(3):
            LED.value(0); time.sleep_ms(120)
            LED.value(1); time.sleep_ms(120)
        time.sleep_ms(1200)


if __name__ == "__main__":
    # Default boot behaviour: heartbeat. Call spin()/home()/beep() from the REPL.
    heartbeat()
