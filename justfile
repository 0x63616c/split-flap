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

# --- CAD (build123d, in cad/) ---
# Everything lives under `just cad <cmd>`. Bare `just cad` prints this help.

cad cmd="help" *args:
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{cmd}}" in
    help|-h|--help)
        cat <<'EOF'
    just cad dev [model]    dev loop: 2 viewers + cmux panes + save watcher
                            (optional model pins the focus pane)
    just cad down           stop watcher + both viewers
    just cad list           list every model + printable part
    just cad export [part]  write STL(s) to cad/export/ — no part = all printables
    just cad test           dimensional tests (volume, bbox, clearances)
    just cad install        sync the cad uv env (python 3.12 + build123d)
    EOF
        ;;
    dev)     ./tools/cad/up.sh {{args}} ;;
    down)    ./tools/cad/up.sh down ;;
    list)    ./tools/cad/up.sh list ;;
    export)  uv run --project cad python -m splitflap_cad export {{args}} ;;
    test)    uv run --project cad python -m pytest {{args}} ;;
    install) uv sync --project cad ;;
    *) echo "unknown cad cmd: {{cmd}} — try 'just cad help'" >&2; exit 2 ;;
    esac

# list attached USB serial ports
ports:
    @ls -1 /dev/cu.usbmodem* 2>/dev/null || echo "no USB modem attached"

# which port the recipes will use
whichport:
    @echo "{{port}}"
