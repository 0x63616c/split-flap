#!/usr/bin/env bash
# Place, check and export everything for the NEMA/TMC2209 driver board.
#
#   tools/build_outputs.sh            # place + DRC + renders + fab
#   tools/build_outputs.sh --quick    # place + DRC only (skips the raytracer)
#
# DRC failures stop the run — no point rendering or shipping gerbers for a
# board that doesn't pass.
#
# NOTE: the GND pour has to be filled before DRC or gerbers mean anything, and
# `kicad-cli --save-board` rewrites the file in a dialect faebryk's parser
# rejects (it re-quotes pad nets and adds `(tenting ...)`). So the fill happens
# on a DERIVED copy: layouts/ stays atopile's, build/filled.kicad_pcb is
# KiCad's, and every output below comes from the filled copy.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/layouts/default/default.kicad_pcb"
PCB="$ROOT/build/filled.kicad_pcb"
KICAD="/Applications/KiCad.app/Contents/MacOS/kicad-cli"
ATO_PY="$HOME/.local/share/uv/tools/atopile/bin/python"
RENDER="$ROOT/render"
FAB="$ROOT/fab"
ZIP="$ROOT/fab-splitflap-driver-nema-v2.zip"

[ -x "$KICAD" ] || { echo "kicad-cli not found at $KICAD"; exit 1; }
[ -x "$ATO_PY" ] || { echo "atopile python not found at $ATO_PY"; exit 1; }

echo "==> place + route + preview.svg"
"$ATO_PY" "$ROOT/tools/place_and_render.py"

echo "==> fill zones -> build/filled.kicad_pcb"
mkdir -p "$ROOT/build"
cp "$SRC" "$PCB"
# let KiCad resolve the project-local part libraries during DRC
cp "$ROOT/fp-lib-table" "$ROOT/build/fp-lib-table"
ln -sfn "$ROOT/parts" "$ROOT/build/parts"

echo "==> DRC"
"$KICAD" pcb drc --severity-error --severity-warning --refill-zones --save-board \
    --units mm -o "$ROOT/build/drc.rpt" "$PCB" >/dev/null 2>&1 || {
    echo "DRC FAILED:"
    grep -E "^\*\* Found|^\[" "$ROOT/build/drc.rpt" | head -40
    exit 1
}
grep -E "^\*\* Found" "$ROOT/build/drc.rpt"

if [ "${1:-}" = "--quick" ]; then
    echo "==> --quick: skipping renders and fab output"
    exit 0
fi

echo "==> 3D renders -> render/"
mkdir -p "$RENDER"
render() {  # name, then kicad-cli render args
    local name="$1"; shift
    "$KICAD" pcb render -o "$RENDER/$name.png" --quality high \
        --background opaque "$@" "$PCB" >/dev/null 2>&1
    echo "    $name.png"
}
render top    --side top    -w 1600 -h 2000
render bottom --side bottom -w 1600 -h 2000
render iso    --rotate '-30,0,35'  -w 1800 -h 1400 --floor --perspective
render front  --rotate '-75,0,0'   -w 1800 -h 1000 --floor

echo "==> gerbers + drill + BOM + placement -> fab/"
rm -rf "$FAB" "$ZIP"
mkdir -p "$FAB"
# only the layers a 2-layer fab actually needs — the default export also emits
# Adhesive/Paste/Courtyard/Fab/User_* which just confuse the order desk
"$KICAD" pcb export gerbers -o "$FAB/" \
    --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts \
    "$PCB" >/dev/null
"$KICAD" pcb export drill -o "$FAB/" --format excellon --excellon-separate-th "$PCB" >/dev/null
"$KICAD" pcb export pos -o "$FAB/placement.csv" --format csv --units mm --side both "$PCB" >/dev/null
"$ATO_PY" "$ROOT/tools/make_bom.py"
cp "$ROOT/bom.csv" "$FAB/bom.csv"
(cd "$FAB" && zip -q "$ZIP" ./*)
echo "    $(basename "$ZIP") ($(unzip -l "$ZIP" | tail -1 | awk '{print $1}') bytes)"

echo "==> done"
