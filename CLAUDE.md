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
- New part: builder + MODELS entry in `catalog.py`. All dims in `params.py`. No `__main__` blocks or justfile recipes per part.
- `cad/reference/Unit.stp` = vendor ghost, gitignored. Motor = 28BYJ-48.
