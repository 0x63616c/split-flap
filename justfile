# split-flap task runner.
#
# Bench recipes (wayfinder #11 / bring-up #9) are live now. The ESP-IDF
# `flash` / `ota` recipes from #5 land when that firmware exists.

# Serial port of the board — auto-picks the first USB modem; override:
#   just up port=/dev/cu.usbmodem511RMQK2R3403
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

# run the ctl TUI / CLI (Go; recompiles automatically via the build cache)
ctl *args:
    cd tools/ctl && go run . {{args}}

# --- CAD (build123d, in cad/) ---
# `just cad` = interactive menu. Direct: view [model] | export [model] | list
cad cmd="" *args:
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{cmd}}" in
    test)    cd cad && uv run python -m pytest {{args}} ;;
    install) uv sync --project cad ;;
    *)       cd tools/ctl && go run . cad {{cmd}} {{args}} ;;
    esac

# list attached USB serial ports
ports:
    @ls -1 /dev/cu.usbmodem* 2>/dev/null || echo "no USB modem attached"

# which port the recipes will use
whichport:
    @echo "{{port}}"
