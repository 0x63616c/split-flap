# split-flap

## Commits

Auto-commit very often (each coherent step), without mentioning it. Good trace > big commits. Normal commit-message quality.

## CAD (build123d + ocp_vscode)

- `just cad` — whole dev loop, idempotent: viewers :3939 (assembly) + :3940 (focus), cmux panes, save-watcher. Focus pane follows last-saved part file; `just cad <model>` pins, `just cad` unpins, `just cad list` menu, `just cad down` stops.
- Registry = `cad/splitflap_cad/catalog.py`. New part → builder + one MODELS entry. No `__main__` blocks, no new justfile recipes. All dims in `params.py`, no magic numbers in part files.
- Pushes stream live, never replayed: reloaded page = blank/OCP splash until next push (any save fixes). Build failure → cmux notification; panes keep last good model. Log: `/tmp/splitflap-cad-watch.log`.
- `cad/reference/Unit.stp` = vendor ghost (gitignored). Vendor motor 28BYJ-48 (`stepper28byj.py`); NEMA 14 (`motor.py`) possible swap.
