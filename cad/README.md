# split-flap CAD

Code-first CAD: [build123d](https://build123d.readthedocs.io/) builds the
models, [ocp_vscode](https://github.com/bernhard-42/vscode-ocp-cad-viewer)
renders them in the browser. No mouse modeling — edit Python, save, look.

## Quickstart

```sh
just cad install   # once: uv env, python 3.12, build123d
just cad dev       # the dev loop — leave it running
```

`just cad` alone prints the command menu. `just cad dev` is idempotent and
starts everything:

- viewer **:3939** — always the **full assembly** (top cmux pane)
- viewer **:3940** — the **focus model** (bottom pane), auto-follows
  whichever part file you last saved
- a save-watcher: any `.py` save in `splitflap_cad/` rebuilds and
  re-pushes both panes (~10s)

```sh
just cad list        # what models exist (the menu)
just cad dev drum    # pin the focus pane to one model
just cad dev         # unpin — back to follow-my-saves
just cad down        # stop watcher + viewers
just cad export      # every printable STL -> cad/export/
just cad export flap # just one
just cad test        # dimensional tests
```

No panes / blank page? Pushes are live-streamed, never replayed — a
reloaded page shows the OCP splash until the next push. Save any file or
re-run `just cad dev`.

## Layout

| file | what |
|---|---|
| `splitflap_cad/params.py` | ALL dimensions. Raw measurements = named constants, positions = derived properties. No magic numbers in part files. |
| `splitflap_cad/catalog.py` | THE registry: viewable models, printable parts, save→model focus map. **Add a part here** (builder fn + one `MODELS` entry). |
| `splitflap_cad/<part>.py` | geometry only (`flap`, `drum`, `unit`, `motor`, `stepper28byj`) — no `__main__` blocks |
| `splitflap_cad/assembly.py` | full-unit compose + posed bought-parts |
| `splitflap_cad/fins.py` | interconnect fins: the five magnet tabs that latch modules together |
| `splitflap_cad/__main__.py` | the CLI behind `just cad` (`list/show/pin/sync/export`) — `export` with no name writes every printable |
| `tools/cad/up.sh` (repo root) | orchestrator: viewers + cmux panes + watcher |

Watcher log: `/tmp/splitflap-cad-watch.log`.
