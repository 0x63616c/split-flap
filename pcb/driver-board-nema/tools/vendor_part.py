"""Vendor an LCSC part into parts/ without atopile's (dead) cloud registry.

    ~/.local/share/uv/tools/atopile/bin/python tools/vendor_part.py C116592 TPS563201

Pipeline: easyeda2kicad pulls the EasyEDA symbol/footprint as KiCad v5, then
faebryk's kicad.convert() lifts them to the modern format atopile parses.
Three gotchas are handled here because they are silent failures otherwise:
  * the footprint's internal name must be `<PART_DIR>:<basename>`
  * every footprint property needs an `(at ...)` or rotate_fp crashes at place
  * symbol (circle)/(arc) graphics choke atopile's parser -> dropped
"""

import subprocess
import sys
from pathlib import Path

from faebryk.libs.kicad.fileformats import kicad

ROOT = Path(__file__).parent.parent
RAW = ROOT / "parts_raw"
PARTS = ROOT / "parts"
EASYEDA = Path.home() / ".local/share/uv/tools/atopile/bin/easyeda2kicad"


def strip_sexpr(text: str, tokens: tuple[str, ...]) -> str:
    """Delete whole `(token ...)` forms. EasyEDA emits KiCad-5 style circles
    (`(radius ...)`) and arcs that the modern symbol parser rejects outright;
    they are decoration only, so drop them rather than translate them."""
    out, i = [], 0
    while i < len(text):
        if text[i] == "(" and any(
            text[i + 1 :].startswith(t) and text[i + 1 + len(t)] in " \t\n(" for t in tokens
        ):
            depth = 0
            while i < len(text):
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def fetch(lcsc: str) -> Path:
    out = RAW / lcsc
    if not (out.with_suffix(".kicad_sym")).exists() and not (RAW / lcsc / f"{lcsc}.kicad_sym").exists():
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [str(EASYEDA), "--full", f"--lcsc_id={lcsc}", "--output", str(out / lcsc)],
            check=True,
        )
    return out


def vendor(lcsc: str, part_dir: str) -> None:
    raw = fetch(lcsc)
    dst = PARTS / part_dir
    dst.mkdir(parents=True, exist_ok=True)

    # --- footprint: v5 -> modern, renamed into this part's namespace
    (mod,) = (raw / f"{lcsc}.pretty").glob("*.kicad_mod")
    fp_file = kicad.convert(kicad.loads(kicad.footprint_v5.FootprintFile, mod.read_text()))
    base = fp_file.footprint.name.split(":")[-1]
    fp_file.footprint.name = f"{part_dir}:{base}"
    for p in fp_file.footprint.propertys:
        if p.at is None:
            p.at = kicad.pcb.Xyr(x=0, y=0, r=0)
        elif p.at.r is None:
            p.at.r = 0
    kicad.dumps(fp_file, dst / f"{base}.kicad_mod")

    # --- symbol: reformat through faebryk, graphics stripped
    text = strip_sexpr((raw / f"{lcsc}.kicad_sym").read_text(), ("circle", "arc"))
    sym_file = kicad.loads(kicad.symbol.SymbolFile, text)
    name = sym_file.kicad_sym.symbols[0].name
    kicad.dumps(sym_file, dst / f"{name}.kicad_sym")

    print(f"{part_dir}: footprint={base}.kicad_mod symbol={name}.kicad_sym")
    print(f"  pins: {[p.name for p in fp_file.footprint.pads]}")


if __name__ == "__main__":
    vendor(sys.argv[1], sys.argv[2])
