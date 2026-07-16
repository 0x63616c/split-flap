# split-flap

## CAD dev loop (build123d + ocp_vscode)

One command: `just cad`. Idempotent — starts two viewer daemons
(:3939 = full assembly, :3940 = focus model), points the two cmux
browser panes at them, and runs a save-watcher that rebuilds + re-pushes
both viewers on every `.py` save in `cad/splitflap_cad/`. The focus pane
auto-follows whichever part file was last saved.

- `just cad list` — model catalog (the menu)
- `just cad <model>` — pin the focus pane to one model (`just cad`
  clears the pin, back to auto-follow)
- `just cad down` — stop watcher + viewers
- `just export <part>` — STL to `cad/export/`

The registry is `cad/splitflap_cad/catalog.py` — single source of truth
for viewable models, printable parts, and the save→model focus map.
Adding a part = builder fn + one `MODELS` entry there (no `__main__`
blocks in part files, no new justfile recipes).

Viewer gotcha: pushes are websocket-streamed, never replayed — a freshly
(re)loaded page is blank until the next push (the OCP logo splash =
"no push received yet"). With the watcher running, any save fixes it;
or run `just cad` again.

## CAD conventions

- All dimensions live in `cad/splitflap_cad/params.py` — raw measurements
  are named constants, positions are derived properties. No magic numbers
  in part files.
- `cad/reference/Unit.stp` (gitignored, license unclear) is the vendor
  unit from Printables #805853, used as a ghost overlay + measurement
  source. `splitflap_cad/reference.py` aligns it onto our centered frame.
- Vendor motor is a 28BYJ-48 (`stepper28byj.py`); a NEMA 14 model
  (`motor.py`) exists for a possible later swap.
