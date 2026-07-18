# TMC2209 + NEMA 14 spin test (XIAO ESP32-C6).
#
# Standalone-mode driver: current limit is the trim pot, not software. Run this
# between pot turns while creeping the current up from minimum -- see the
# empirical Vref procedure (this board doesn't break Vref out to a header).
#
# Wiring: STEP=D0(GPIO0), DIR=D1(GPIO1), EN=D2(GPIO2), MS1/MS2 -> GND (1/8 step).
# NOTE: these pins are the old ULN2003 IN1-3 from the 28BYJ-48 bench.

from machine import Pin
import time

STEP = Pin(0, Pin.OUT)
DIR = Pin(1, Pin.OUT)
EN = Pin(2, Pin.OUT)

FULL_STEPS_PER_REV = 200
MICROSTEPS = 8


def spin(revs=1, direction=1, delay_us=500):
    """One rev in ~1.6s at the default delay -- slow enough to watch and abort."""
    EN.value(1)  # keep disabled until direction is settled
    DIR.value(direction)
    time.sleep_ms(10)
    EN.value(0)  # active low
    try:
        for _ in range(int(revs * FULL_STEPS_PER_REV * MICROSTEPS)):
            STEP.value(1)
            time.sleep_us(delay_us)
            STEP.value(0)
            time.sleep_us(delay_us)
    finally:
        EN.value(1)  # de-energise -- coils idling at current limit is what cooks them


spin()
