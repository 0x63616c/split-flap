"""Turn atopile's BOM into an orderable one.

    ~/.local/share/uv/tools/atopile/bin/python tools/make_bom.py

atopile emits designator/footprint/qty/mfr/MPN/LCSC already, but leaves Value
empty (these are atomic parts, so there is no solved parameter to print) and
has no room for what a part is actually doing. Both matter when you are hand
stuffing the board, so they are filled in here from a table keyed on MPN.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "build/builds/default/default.bom.csv"
OUT = ROOT / "bom.csv"

# MPN -> (value, what it does)
INFO = {
    "CC0603KRX7R9BB104": ("100nF 50V X7R 0603", "HF decoupling (buck bootstrap, 5V rail)"),
    "CC0805MKX5R8BB226": ("22uF 25V X5R 0805", "buck input/output + VM ceramic"),
    "BXJ25V470M10*10 10.0TP": ("470uF 25V, 80mOhm ESR", "VM bulk reservoir for the motor"),
    "TPS563201DDCR": ("12V->5V 3A buck", "makes the 5V rail for the XIAO"),
    "AO3401A": ("-30V -4A P-MOSFET", "reverse-polarity gate on the 12V input"),
    "CKCS5040-4.7uH/M": ("4.7uH 3A shielded", "buck output inductor"),
    "KT-0603G": ("green LED 0603", "5V power-good indicator"),
    "RC0603FR-071KL": ("1k 1% 0603", "PDN_UART series + LED ballast"),
    "RC0603FR-0710KL": ("10k 1% 0603", "buck feedback divider, low side"),
    "0603WAF5602T5E": ("56k 1% 0603", "feedback / enable / gate dividers"),
    "0603WAF1003T5E": ("100k 1% 0603", "enable + gate dividers, high side"),
    "KH-2.54PH180-1X7P-L11.5": ("1x7 2.54mm socket", "XIAO ESP32-C6 socket row"),
    "KH-2.54PH180-1X8P-L11.5": ("1x8 2.54mm socket", "TMC2209 StepStick socket row"),
    "XH-4AW": ("JST-XH 4P right-angle", "stepper motor; pads run B2 B1 A2 A1 left to right"),
    "XY-B3B-XH-A": ("JST-XH 3P vertical", "hall sensor: 5V GND DO"),
    "DC-005 2.0": ("5.5x2.1mm barrel jack", "12V input, centre positive"),
}

# Not fitted to the board, but you cannot build a module without them.
EXTRA = [
    ("-", "-", "1", "TMC2209 SilentStepStick", "Trinamic/clone", "TMC2209 SilentStepStick",
     "-", "socketed stepper driver, 2x8 header"),
    ("-", "-", "1", "Seeed XIAO ESP32-C6", "Seeed Studio", "XIAO ESP32-C6",
     "-", "socketed controller, on 2x 1x7 pin headers"),
    ("-", "-", "1", "12V >=2A PSU, 5.5x2.1 barrel", "-", "-",
     "-", "centre positive; ~1.0A typical draw"),
]


def main():
    rows = list(csv.DictReader(SRC.open()))
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Footprint", "Quantity", "Value",
                    "Manufacturer", "Partnumber", "LCSC Part #", "Function"])
        for r in rows:
            mpn = r["Partnumber"]
            value, func = INFO.get(mpn, ("", ""))
            if not value:
                raise SystemExit(f"no value/function recorded for MPN {mpn!r}")
            w.writerow([r["Designator"], r["Footprint"], r["Quantity"], value,
                        r["Manufacturer"], mpn, r["LCSC Part #"], func])
        w.writerow([])
        w.writerow(["# not fitted — order separately"])
        for row in EXTRA:
            w.writerow(row)

    fitted = sum(int(r["Quantity"]) for r in rows)
    print(f"wrote {OUT} — {len(rows)} line items, {fitted} placed components")


if __name__ == "__main__":
    main()
