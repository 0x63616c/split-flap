# split-flap task runner.
#
# The bench (wayfinder #11 / bring-up #9) lives in ctl now — `just bench`.
# The ESP-IDF `flash` / `ota` recipes from #5 land when that firmware exists.

# list recipes
default:
    @just --list

# drive the breadboard module — menu, or `just bench <port> | --no-flash`
bench *args:
    cd tools/ctl && go run . bench {{args}}

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
