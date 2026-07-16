#!/usr/bin/env bash
# `just cad dev [model]` — the one-command CAD dev loop (dispatched from the
# justfile; also re-execs itself for the watcher loop and for down/list).
#
#   just cad dev           ensure viewers + cmux panes + watcher; focus follows saves
#   just cad dev <model>   same, but pin the focus pane to <model>
#   just cad list          print the model catalog
#   just cad down          stop watcher + both viewers
#
# Two viewers: :3939 = full assembly (top pane), :3940 = focus model
# (bottom pane). The watcher rebuilds + re-pushes both on every .py save
# in cad/splitflap_cad/; focus = pinned model, else the saved file's model.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CAD_DIR="$ROOT/cad"
SRC_DIR="$CAD_DIR/splitflap_cad"
CLI() { uv run --project "$CAD_DIR" python -m splitflap_cad "$@"; }

A_PORT=3939
F_PORT=3940
A_URL="http://127.0.0.1:$A_PORT/viewer"
F_URL="http://127.0.0.1:$F_PORT/viewer"
WATCH_PID=/tmp/splitflap-cad-watch.pid
WATCH_LOG=/tmp/splitflap-cad-watch.log

target="${1:-auto}"

# --- watcher internals -------------------------------------------------

watch_loop() {
    # fswatch batches events (-o); on each batch, sync using the most
    # recently modified source file for auto-focus. Excluding everything
    # but *.py keeps __pycache__ writes from re-triggering the loop.
    fswatch -o -l 0.5 -e '.*' -i '\.py$' "$SRC_DIR" | while read -r _; do
        f=$(ls -t "$SRC_DIR"/*.py | head -1)
        echo "--- $(date '+%H:%M:%S') $(basename "$f")"
        out=$(CLI sync "$f" 2>&1) && rc=0 || rc=$?
        echo "$out"
        if [ "$rc" != 0 ]; then
            # loud failure: panes keep the LAST GOOD model, so tell the user
            err=$(echo "$out" | grep -E '^[A-Za-z_.]*(Error|Exception)' | tail -1)
            command -v cmux >/dev/null 2>&1 && cmux notify \
                --title "CAD build failed: $(basename "$f")" \
                --body "${err:-see $WATCH_LOG}" 2>/dev/null || true
        fi
    done
}

watch_running() {
    [ -f "$WATCH_PID" ] && kill -0 "$(cat "$WATCH_PID")" 2>/dev/null
}

# --- modes -------------------------------------------------------------

case "$target" in
list)
    CLI list
    exit 0
    ;;
down)
    if watch_running; then
        pkill -P "$(cat "$WATCH_PID")" 2>/dev/null || true
        kill "$(cat "$WATCH_PID")" 2>/dev/null || true
        echo "watcher stopped"
    else
        echo "watcher not running"
    fi
    rm -f "$WATCH_PID"
    pkill -f "python -m ocp_vscode" 2>/dev/null && echo "viewers stopped" || echo "viewers not running"
    exit 0
    ;;
_watch-loop)
    watch_loop
    exit 0
    ;;
esac

# --- 1. viewers --------------------------------------------------------

ensure_viewer() {
    local port=$1
    if curl -s -o /dev/null --max-time 1 "http://127.0.0.1:$port/viewer"; then
        echo "viewer :$port up"
    else
        nohup uv run --project "$CAD_DIR" python -m ocp_vscode --port "$port" \
            > "/tmp/ocp-viewer-$port.log" 2>&1 &
        echo "viewer :$port starting"
        started_viewer=1
    fi
}

started_viewer=0
ensure_viewer $A_PORT
ensure_viewer $F_PORT
[ "$started_viewer" = 1 ] && sleep 3

# --- 2. cmux panes -----------------------------------------------------
# Idempotent: find browser surfaces already on a /viewer URL; first one
# keeps :3939, second is (re)pointed at :3940; create what's missing.

browser_surfaces() {
    # every surface id in the workspace, one per line
    cmux list-panes 2>/dev/null | grep -o 'pane:[0-9]*' | while read -r pane; do
        cmux list-pane-surfaces --pane "$pane" 2>/dev/null | grep -o 'surface:[0-9]*'
    done
}

viewer_surfaces() {
    # "surface:N URL" for surfaces already showing an ocp viewer
    browser_surfaces | while read -r s; do
        url=$(cmux browser --surface "$s" get-url 2>/dev/null) || continue
        case "$url" in
        *127.0.0.1:39*/viewer*) echo "$s $url" ;;
        esac
    done
}

ensure_panes() {
    command -v cmux >/dev/null 2>&1 || {
        echo "no cmux — open $A_URL and $F_URL yourself"
        return
    }
    cmux ping >/dev/null 2>&1 || {
        echo "cmux not reachable — open $A_URL and $F_URL yourself"
        return
    }

    local found top="" bottom=""
    found=$(viewer_surfaces)
    top=$(echo "$found" | awk -v u="$A_URL" '$2==u {print $1; exit}')
    bottom=$(echo "$found" | awk -v u="$F_URL" '$2==u {print $1; exit}')

    # no dedicated :3940 surface yet — repoint a spare :3939 one
    if [ -z "$bottom" ]; then
        bottom=$(echo "$found" | awk -v skip="$top" '$1!=skip {print $1; exit}')
        if [ -n "$bottom" ]; then
            cmux browser --surface "$bottom" open "$F_URL" >/dev/null
            echo "pane $bottom -> :$F_PORT"
        fi
    fi

    # still nothing? create surfaces (first ever run in this workspace)
    if [ -z "$top" ] && [ -z "$bottom" ]; then
        cmux browser open "$A_URL" >/dev/null
        sleep 1
        top=$(viewer_surfaces | awk -v u="$A_URL" '$2==u {print $1; exit}')
    fi
    if [ -z "$bottom" ] && [ -n "$top" ]; then
        local pane
        pane=$(cmux list-panes 2>/dev/null | grep -o 'pane:[0-9]*' | while read -r p; do
            cmux list-pane-surfaces --pane "$p" 2>/dev/null | grep -q "^\*\? *$top " && echo "$p" && break
        done || true)
        cmux new-surface --type browser --pane "${pane:-}" --url "$F_URL" --focus false >/dev/null 2>&1 || true
        sleep 1
        bottom=$(viewer_surfaces | awk -v u="$F_URL" '$2==u {print $1; exit}')
        [ -n "$bottom" ] && cmux split-off --surface "$bottom" down --focus false >/dev/null 2>&1 || true
    fi

    echo "panes: assembly=$([ -n "$top" ] && echo "$top" || echo '?') focus=$([ -n "$bottom" ] && echo "$bottom" || echo '?')"
}

ensure_panes

# --- 3. pin ------------------------------------------------------------

if [ "$target" = auto ]; then
    CLI pin --clear
else
    CLI pin "$target" # validates the name; dies on typos before we daemonize
fi

# --- 4. initial push + watcher ----------------------------------------

CLI sync

if watch_running; then
    echo "watcher already running (pid $(cat "$WATCH_PID"))"
else
    command -v fswatch >/dev/null 2>&1 || {
        echo "fswatch missing (brew install fswatch) — no auto-rebuild"
        exit 0
    }
    nohup "${BASH_SOURCE[0]}" _watch-loop > "$WATCH_LOG" 2>&1 &
    echo $! > "$WATCH_PID"
    echo "watcher started (pid $!, log $WATCH_LOG)"
fi
