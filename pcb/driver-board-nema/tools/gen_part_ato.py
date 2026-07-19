"""Emit the per-part .ato drivers for the vendored footprints/symbols.

Kept as a generator rather than hand-written files because the footprint and
symbol filenames come straight off disk — typo'ing one of those is a silent
`ato build` failure that looks like a parser bug.

    ~/.local/share/uv/tools/atopile/bin/python tools/gen_part_ato.py
"""

from pathlib import Path

PARTS = Path(__file__).parent.parent / "parts"

# dir -> (component, manufacturer, mpn, lcsc, designator prefix, docstring, pins)
# pins: list of (declaration, comment) — declaration is a full ato pin line.
SPEC = {
    "TPS563201": (
        "TPS563201_package", "Texas Instruments", "TPS563201DDCR", "C116592", "U",
        "4.5-17V 3A synchronous buck, SOT-23-6. Makes the 5V rail for the XIAO\n"
        "from the 12V motor supply. D-CAP2 control: stable on all-ceramic output,\n"
        "no external compensation and no catch diode (both FETs are internal).",
        [("signal GND ~ pin 1", ""), ("signal SW ~ pin 2", ""), ("signal VIN ~ pin 3", ""),
         ("signal VFB ~ pin 4", "0.768V reference"), ("signal EN ~ pin 5", "abs max 6V — never tie to 12V"),
         ("signal VBST ~ pin 6", "bootstrap, 100nF to SW")],
    ),
    "AO3401A": (
        "AO3401A_package", "Alpha & Omega Semiconductor", "AO3401A", "C15127", "Q",
        "-30V -4A P-channel MOSFET, SOT-23. High-side reverse-polarity gate for\n"
        "the 12V input. Vgs is rated +/-12V only, so the gate is driven from a\n"
        "divider rather than tied to GND — see the divider in main.ato.",
        [("signal G ~ pin 1", ""), ("signal S ~ pin 2", ""), ("signal D ~ pin 3", "")],
    ),
    "DC_005": (
        "DC_005_package", "BOOMELE(Boom Precision Elec)", "DC-005 2.0", "C16214", "J",
        "5.5x2.1mm barrel jack (2.0mm centre post), THT, switched.\n"
        "Pin functions read off the EasyEDA schematic symbol, NOT guessed from pad\n"
        "geometry: pin 4 = centre/tip (+12V), pin 3 = sleeve (GND), pin 2 = the\n"
        "normally-closed switch contact, which shorts to the SLEEVE when no plug is\n"
        "inserted. Pin 2 must therefore never touch +12V; it is tied to GND here,\n"
        "purely as a third mechanical anchor for the jack.",
        [("signal SWITCH ~ pin 2", "NC to sleeve when unplugged"),
         ("signal SLEEVE ~ pin 3", "GND"), ("signal TIP ~ pin 4", "+12V")],
    ),
    "LED_0603_GREEN": (
        "LED_0603_GREEN_package", "Hubei KENTO Elec", "KT-0603G", "C12624", "D",
        "0603 green LED, ~3.1Vf. Power-good indicator on the 5V rail.",
        [("signal K ~ pin 1", "cathode"), ("signal A ~ pin 2", "anode")],
    ),
    "IND_4U7_3A": (
        "IND_4U7_3A_package", "CENKER", "CKCS5040-4.7uH/M", "C354606", "L",
        "4.7uH 3A shielded power inductor, 5x5mm, 32mOhm, 3.5A saturation.\n"
        "Buck output inductor — ~1.1A ripple at 12V in / 5V out, and saturation is\n"
        "~5x the 0.7A this rail actually draws.",
        [("pin 1", ""), ("pin 2", "")],
    ),
    "CAP_470UF_25V": (
        "CAP_470UF_25V_package", "SamYoung Electronics", "BXJ25V470M10*10 10.0TP", "C3002464", "C",
        "470uF 25V low-ESR SMD aluminium electrolytic, D10xL10mm.\n"
        "80mOhm ESR / 850mA ripple — the bulk reservoir on VM. POLARIZED:\n"
        "pin 1 = + (POS), pin 2 = - (NEG); the silk hatched half marks the negative\n"
        "side, same convention as the v1 board's 220uF part.",
        [("signal POS ~ pin 1", ""), ("signal NEG ~ pin 2", "")],
    ),
    "CAP0805_22UF_25V": (
        "CAP0805_22UF_25V_package", "YAGEO", "CC0805MKX5R8BB226", "C784585", "C",
        "22uF 25V X5R 0805 MLCC. Used on both the 12V and 5V rails; the 25V rating\n"
        "is deliberate so one part number covers both, and it keeps a usable ~10uF\n"
        "of effective capacitance after DC bias derating at 12V.",
        [("pin 1", ""), ("pin 2", "")],
    ),
    "R0603_1K": ("R0603_1K_package", "YAGEO", "RC0603FR-071KL", "C22548", "R",
                 "1k 1% 0603 thick-film resistor.", [("pin 1", ""), ("pin 2", "")]),
    "R0603_10K": ("R0603_10K_package", "YAGEO", "RC0603FR-0710KL", "C98220", "R",
                  "10k 1% 0603 thick-film resistor.", [("pin 1", ""), ("pin 2", "")]),
    "R0603_56K": ("R0603_56K_package", "UNI-ROYAL(Uniroyal Elec)", "0603WAF5602T5E", "C23206", "R",
                  "56k 1% 0603 thick-film resistor.", [("pin 1", ""), ("pin 2", "")]),
    "R0603_100K": ("R0603_100K_package", "UNI-ROYAL(Uniroyal Elec)", "0603WAF1003T5E", "C25803", "R",
                   "100k 1% 0603 thick-film resistor.", [("pin 1", ""), ("pin 2", "")]),
    "KH_2_54_1X8_FEMALE": (
        "KH_2_54_1X8_FEMALE_package", "Shenzhen Kinghelm Elec", "KH-2.54PH180-1X8P-L11.5", "C2905487", "J",
        "1x8 2.54mm female socket header — one row of the TMC2209 StepStick socket.\n"
        "Two of these, 15.24mm apart, accept a standard 2x8 SilentStepStick.",
        [(f"pin {i}", "") for i in range(1, 9)],
    ),
    "XH_4AW": (
        "XH_4AW_package", "BOOMELE(Boom Precision Elec)", "XH-4AW", "C21273", "J",
        "XH 2.54mm 4-pin right-angle shrouded header (JST XH compatible).\n"
        "Bipolar stepper: 1 = A1, 2 = A2, 3 = B1, 4 = B2.",
        [(f"pin {i}", "") for i in range(1, 5)],
    ),
}

TEMPLATE = '''#pragma experiment("TRAITS")
import has_designator_prefix
import has_part_picked
import is_atomic_part

component {component}:
    """
{doc}
    """
    trait is_atomic_part<manufacturer="{mfr}", partnumber="{mpn}", footprint="{fp}", symbol="{sym}">
    trait has_part_picked::by_supplier<supplier_id="lcsc", supplier_partno="{lcsc}", manufacturer="{mfr}", partno="{mpn}">
    trait has_designator_prefix<prefix="{prefix}">

    # pins
{pins}
'''


def main() -> None:
    for part_dir, (comp, mfr, mpn, lcsc, prefix, doc, pins) in SPEC.items():
        d = PARTS / part_dir
        (fp,) = d.glob("*.kicad_mod")
        (sym,) = d.glob("*.kicad_sym")
        body = "\n".join(
            f"    {decl}" + (f"  # {c}" if c else "") for decl, c in pins
        )
        text = TEMPLATE.format(
            component=comp, mfr=mfr, mpn=mpn, lcsc=lcsc, prefix=prefix,
            fp=fp.name, sym=sym.name,
            doc="\n".join("    " + ln for ln in doc.splitlines()),
            pins=body,
        )
        (d / f"{part_dir}.ato").write_text(text)
        print(f"wrote {part_dir}/{part_dir}.ato")


if __name__ == "__main__":
    main()
