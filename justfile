# split-flap task runner.
#
# Bench recipes (wayfinder #11 / bring-up #9) are live now. The ESP-IDF
# `flash` / `ota` recipes from #5 land when that firmware exists.

# Serial port of the board — auto-picks the first USB modem; override:
#   just drive port=/dev/cu.usbmodem511RMQK2R3403
port := `ls /dev/cu.usbmodem* 2>/dev/null | head -1`

# list recipes
default:
    @just --list

# bench control UI in sim mode — no hardware, no deps
bench:
    python3 tools/bench/bench_ui.py

# free the serial port from any stale holder (old mpremote / bench UI / monitor)
free:
    -@pkill -f 'mpremote connect' 2>/dev/null || true
    -@pkill -f 'bench_ui.py' 2>/dev/null || true
    -@sleep 1

# ONE COMMAND: free port -> flash command loop -> reset -> drive it. Use this.
up: free
    uv run --with mpremote python3 -m mpremote connect {{port}} cp firmware/micropython-spike/bench_board.py :main.py + reset
    uv run --with pyserial python3 tools/bench/bench_ui.py --serial {{port}}

# just flash the command loop onto the board (no drive). uv pulls mpremote.
board: free
    uv run --with mpremote python3 -m mpremote connect {{port}} cp firmware/micropython-spike/bench_board.py :main.py + reset
    @echo "board running standalone. now: just drive"

# drive an already-flashed board over serial. uv pulls pyserial.
drive: free
    uv run --with pyserial python3 tools/bench/bench_ui.py --serial {{port}}

# remove the boot program -> board returns to a bare REPL
unboard:
    uv run --with mpremote python3 -m mpremote connect {{port}} rm :main.py reset

# open a raw REPL on the board (Ctrl-] to exit) — needs the port free
repl:
    uv run --with mpremote python3 -m mpremote connect {{port}} repl

# --- CAD (build123d, in cad/) ---

# CAD dev loop: 2 viewers + cmux panes + save watcher. `just cad list` = menu, `just cad <model>` = pin focus, `just cad down` = stop
cad target="auto":
    @./tools/cad/up.sh {{target}}

# export a printable part to cad/export/<part>.stl (`just cad list` shows names)
export part="unit":
    uv run --project cad python -m splitflap_cad export {{part}}

# sync the cad env (uv creates .venv, pins python 3.12, installs build123d)
cad-install:
    uv sync --project cad

# dimensional tests (volume, bbox, clearances)
cad-test:
    uv run --project cad python -m pytest

# list attached USB serial ports
ports:
    @ls -1 /dev/cu.usbmodem* 2>/dev/null || echo "no USB modem attached"

# which port the recipes will use
whichport:
    @echo "{{port}}"
