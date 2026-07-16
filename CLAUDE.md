# split-flap

Auto-commit each coherent step, silently. Good trace > big commits.

## CAD

- `just cad` = whole dev loop (viewers :3939 assembly / :3940 focus, cmux panes, save-watcher). `just cad list|<model>|down` = menu | pin focus | stop.
- New part: builder + MODELS entry in `catalog.py`. All dims in `params.py`. No `__main__` blocks or justfile recipes per part.
- Pushes never replayed — reloaded page blank until next save. Build fail → cmux notify, panes keep last good; log `/tmp/splitflap-cad-watch.log`.
- `cad/reference/Unit.stp` = vendor ghost, gitignored. Motor = 28BYJ-48.
