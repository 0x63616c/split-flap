#!/usr/bin/env bash
# Place, check and export everything for the driver board in one go.
#
#   tools/build_outputs.sh            # place + DRC + renders + fab
#   tools/build_outputs.sh --quick    # place + DRC only (skips the raytracer)
#
# DRC failures stop the run — no point rendering or shipping gerbers for a
# board that doesn't pass.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PCB="$ROOT/layouts/default/default.kicad_pcb"
KICAD="/Applications/KiCad.app/Contents/MacOS/kicad-cli"
ATO_PY="$HOME/.local/share/uv/tools/atopile/bin/python"
RENDER="$ROOT/render"
FAB="$ROOT/fab"
ZIP="$ROOT/fab-splitflap-driver-v1.zip"

[ -x "$KICAD" ] || { echo "kicad-cli not found at $KICAD"; exit 1; }
[ -x "$ATO_PY" ] || { echo "atopile python not found at $ATO_PY"; exit 1; }

echo "==> place + route + preview.svg"
"$ATO_PY" "$ROOT/tools/place_and_render.py"

echo "==> DRC"
"$KICAD" pcb drc --severity-error --severity-warning \
    --exit-code-violations -o /tmp/splitflap-drc.rpt "$PCB" >/tmp/splitflap-drc.log 2>&1 || {
    echo "DRC FAILED:"
    sed -n '5,60p' /tmp/splitflap-drc.rpt
    exit 1
}
grep -E "violations|unconnected" /tmp/splitflap-drc.log || true

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
render iso2   --rotate '-30,0,-35' -w 1800 -h 1400 --floor --perspective
render front  --rotate '-75,0,0'   -w 1800 -h 1000 --floor

echo "==> gerbers + drill -> fab/"
rm -rf "$FAB" "$ZIP"
mkdir -p "$FAB"
"$KICAD" pcb export gerbers -o "$FAB/" "$PCB" >/dev/null
"$KICAD" pcb export drill -o "$FAB/" --format excellon --excellon-separate-th "$PCB" >/dev/null
(cd "$FAB" && zip -q "$ZIP" ./*)
echo "    $(basename "$ZIP") ($(unzip -l "$ZIP" | tail -1 | awk '{print $2}') files)"

echo "==> done"
