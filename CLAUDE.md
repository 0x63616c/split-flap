# split-flap

Auto-commit each coherent step, silently. Good trace > big commits.

## CAD

- `just ctl` = tooling TUI (namespaces: cad, pcb, bench). `just cad` = cad menu.
  Direct: `just cad view [model]` (live viewer in CURRENT cmux pane — tab 1
  logs, tab 2 viewer; no model = follow last-saved; Ctrl-C = full teardown),
  `just cad export [part]`, `just cad render [drawing]`, `just cad list`,
  `just cad test|install`.
- Views are self-contained: own port (3939+), own watcher; any .py save in
  cad/splitflap_cad/ re-renders every open view (params.py included). Build
  fail → in-pane log + cmux notify, viewer keeps last good. Assembly is just
  a model — `just cad view assembly`. Strays: `pkill -f ocp_vscode`.
- New part: module with part builder(s) + `scene()` (returns `viewer.Scene`),
  one `Model` entry in `catalog.py` (+ `Printable` if it prints). All dims in
  `params.py` (edge breaks ≤1mm may inline); local→unit poses in `frames.py`;
  shared idioms in `geo.py` (polar arrays, radial plates, slot-0 marker) and
  `select.py` (named edge selectors). No `__main__` blocks or justfile recipes
  per part.
- Geometry is golden-guarded: fast fingerprint tests every run; `pytest -m
  slow` = XOR vs `cad/tests/golden/*.brep` + full catalog build. Intended
  shape change ⇒ `uv run python tests/regen_goldens.py` in the SAME commit.
  Exports are byte-deterministic — a dirty `cad/export/` means geometry moved.
- `export` writes STL for every `Printable`; `render` writes the `Render`
  registry's PNG drawings to `cad/export/renders/` (matplotlib, dev group —
  drawings only, never geometry). STL only: no STEP, by request.
- No vendor geometry: every printable is ours. Motor = 28BYJ-48.

## Bench

- `just bench` = ctl's bench screen (menu: flash & connect / connect / pick
  port). Direct: `just bench <port>` or `just bench --no-flash`. It owns the
  serial port outright — nothing else may hold it.
- "flash & connect" is the old `just up`: pkill stale mpremote, mpremote-copy
  `firmware/micropython-spike/bench_board.py` to `:main.py`, reset, connect.
- Type glyphs to drive (a whole string steps through, 1s dwell); `/help` lists
  the rest. Calibrate once: `/reset` → `/homecal` → `/nudge ±n` → `/sethome <g>`.
  Nudge offset persists on the board; home glyph in `.bench/` (gitignored).
- Slot maths in `tools/ctl/slotplan.go` (absolute-step targeting, forward-only)
  — the keeper, destined for real firmware. Findings:
  `docs/research/bench-findings.md`.

## PCB

- `just pcb` = ctl's pcb menu. Direct: `just pcb view|drc|build|place`.
  `view` = live 3D board in the CURRENT pane (tab 1 logs, tab 2 GLB viewer;
  Ctrl-C = full teardown) — same shape as `just cad view`, own port (3950+),
  own watcher. Saving `place_and_render.py` or `main.ato` re-places, re-exports
  the GLB and reloads the page; a failure keeps the last good model on screen.
  `drc` = place + KiCad DRC (fast loop), `build` = `tools/build_outputs.sh`
  (place → DRC → 5 renders → gerbers+zip; DRC failure aborts the rest).
- `pcb/driver-board/` = atopile project (ato 0.15.7 via uv tool, needs py3.14).
  Circuit in `main.ato` (module SplitFlapDriver); parts vendored in `parts/`
  (atomic parts: .ato + kicad_mod + kicad_sym, LCSC-pinned). Skills for the
  ato language live in `.claude/skills/` — use them when touching .ato files.
- Loop: edit `main.ato` → `ato build` (run twice after adding a component —
  nets stamp one build late) → `tools/place_and_render.py` (atopile's python:
  `~/.local/share/uv/tools/atopile/bin/python`) → `preview.svg`. Placement AND
  routing are data tables in that script (address-keyed, survives rebuilds).
  KiCad 10 IS installed (cask half-failed on a sudo step, but the binary
  works): `/Applications/KiCad.app/Contents/MacOS/kicad-cli` — use it for
  real DRC (`pcb drc`), 3D renders (`pcb render --side/--rotate`), and fab
  output (`pcb export gerbers|drill`). `preview.svg` is still ours, for a
  fast look without the raytracer. `ato validate` broken upstream.
- atopile cloud (registry/part-picker/autolayout) was down 2026-07-18 —
  workarounds + gotchas in auto-memory `pcb-workflow`. New parts: easyeda2kicad
  → `kicad.convert()` v5→modern → hand-write the .ato (footprint name must be
  `<PART_DIR>:<basename>`; every property needs an `(at)`; strip circle/arc
  from symbols). Verify LCSC stock via jlcpcb.com search API first.
- Bench-proven pinout is law: IN1-4 = D0-D3, hall DO = D8 (internal pull-up).
  Don't reassign without updating firmware + bench-setup memory.
