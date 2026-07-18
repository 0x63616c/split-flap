# split-flap

Auto-commit each coherent step, silently. Good trace > big commits.

## CAD

- `just ctl` = tooling TUI (namespaces; cad for now). `just cad` = cad menu.
  Direct: `just cad view [model]` (live viewer in CURRENT cmux pane — tab 1
  logs, tab 2 viewer; no model = follow last-saved; Ctrl-C = full teardown),
  `just cad export [part]`, `just cad list`, `just cad test|install`.
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
- No vendor geometry: every printable is ours. Motor = 28BYJ-48.
