# ctl: Go TUI replacing the cad shell tooling

Date: 2026-07-16
Status: approved pending user review

## Goal

Replace `tools/cad/up.sh` and the shell-dispatched `just cad` subcommands
(`dev`, `down`, `list`, `export`) with one Go program at `tools/ctl` —
an interactive bubbletea/lipgloss TUI plus direct CLI args. `tools/ctl`
is the future home for other project tooling (e.g. the python REPL
helper later); for now it has a single `cad` command namespace.

Core new capability: `just cad view [model]` runs *in any cmux pane* and
turns that pane into a live-updating viewer for one model — no shared
watcher, no registry, no pane orchestration.

## Layout

- `tools/ctl/` — Go module (`go.mod`), deps: bubbletea, lipgloss (+
  bubbles for the list picker), fsnotify.
- Justfile:
  - `ctl *args:` → `cd tools/ctl && go run . {{args}}` — runs the ctl
    (bare = root TUI menu). `go run` recompiles via the build cache, so
    Go source changes are picked up automatically.
  - `cad cmd="" *args:` keeps `test`/`install` as uv dispatch (they
    manage the python env, not cad workflow) and forwards everything
    else to `just ctl cad {{cmd}} {{args}}`.
- Go builds no geometry ever — it shells out to
  `uv run --project cad python -m splitflap_cad …` for list/push/export.
- `tools/cad/up.sh` deleted.

## Commands

Root TUI menu is a namespace list from day one: `cad` (built now);
`bench` (sim UI, flash+drive, serial-port utils — planned, NOT built in
this pass); python REPL later. `test`/`install` may appear as cad menu
items running the same uv commands.

- `just cad` (no args) → TUI menu, `cad` section:
  - **view** → pick "watch a specific model" (list from catalog) or
    "watch last saved model", then runs view mode in place.
  - **export** → "all" or a specific model.
- Direct args skip the TUI (scripting / agents):
  - `just cad view [model]` — no model = follow-last-saved.
  - `just cad export [model]` — no model = all printables.
  - `just cad list` — print catalog.
- Model list comes from the python side (`python -m splitflap_cad list`,
  machine-readable) so the catalog stays single-source-of-truth.

## `view` behavior

Foreground, fully self-contained; N panes = N independent processes.

1. Pick a free port (scan upward from 3939).
2. Spawn child `uv run --project cad python -m ocp_vscode --port N`.
3. `cmux identify` → caller's pane; open a browser tab in that pane at
   the viewer URL and select it (tab 1 = this command's logs, tab 2 =
   viewer). If cmux is unavailable, print the URL and continue.
4. Initial push, then fsnotify-watch `cad/splitflap_cad/*.py`. Any .py
   save → rebuild + push. This is the dependency answer: params.py /
   catalog.py edits re-render every open view because the whole package
   is watched, not just the model's file. Over-triggering is accepted.
   - pinned mode: always push the chosen model.
   - follow mode: push the model belonging to the last-saved file
     (python side resolves file → model, as `sync` does today).
5. Push = new python subcommand:
   `python -m splitflap_cad push <model> --port N` and
   `python -m splitflap_cad push --file <saved.py> --port N` (follow).
   One model, one port, exit code reports build failure.
6. Build failure: log in-pane (timestamped, as the old watch log did)
   and `cmux notify`; viewer keeps last good render.
7. Ctrl-C / pane close → SIGTERM child viewer, close the browser tab it
   opened. No /tmp state, no pidfiles, nothing leaks.

## Python-side changes (`cad/splitflap_cad/__main__.py`)

- Add `push` (single model → single port, plus `--file` resolution).
- Keep `list`, `export`.
- Remove `pin`, `sync` (multi-port push) once nothing calls them.

## Removed

- `tools/cad/up.sh` (watcher, viewer lifecycle, cmux pane/log/cmd-split
  orchestration, 3:3:1 sizing) — pane layout is now the user's job;
  the tool only adds the viewer tab to the pane it's run in.
- `just cad dev|down|list|export` shell dispatch (`list`/`export` return
  as ctl subcommands).
- Stray-viewer escape hatch documented instead of `down`:
  `pkill -f ocp_vscode`.

## Docs

- CLAUDE.md CAD section rewritten: `just cad` TUI, direct args, view
  workflow, "assembly is just a model you view".

## Testing

- Go: unit-test port scan + model-list parsing; TUI smoke via
  `go run . cad list`.
- Manual: `just cad view holder` in a pane (tab created, live update on
  params.py save, Ctrl-C cleanup); `just cad view` follow mode; two
  simultaneous view panes; `just cad export holder`; build-failure path
  (syntax error → in-pane error + notify, viewer keeps last good).
