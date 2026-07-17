# tools/ctl Go TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `tools/cad/up.sh` and the shell `just cad` dispatch with one Go program at `tools/ctl` — bubbletea/lipgloss TUI + direct CLI args — whose core feature is `just cad view [model]`: turn the current cmux pane into a live-updating viewer.

**Architecture:** Go binary orchestrates only (TUI, port pick, viewer child process, cmux tab, fsnotify watch, cleanup); all geometry stays in python (`uv run --project cad python -m splitflap_cad …`). Each `view` process is fully self-contained: own viewer server on its own port, own watch loop, Ctrl-C tears everything down. No registry, no /tmp state, no daemon.

**Tech Stack:** Go 1.26, bubbletea + lipgloss (TUI), fsnotify (watch), existing python CLI (`splitflap_cad`), cmux CLI (optional — degrade to printing the URL).

**Spec:** `docs/superpowers/specs/2026-07-16-ctl-cad-tui-design.md`

## Global Constraints

- Go module path: `github.com/0x63616c/split-flap/tools/ctl`; flat `package main` (small tool — no internal/ packages).
- Python invocations always: `uv run --project cad python -m splitflap_cad …` with cwd = repo root.
- The existing python `show NAME --port N` subcommand IS the spec's "push" — do not add a new subcommand.
- Ports: scan upward from 3939 for a free TCP port.
- cmux absent/unreachable → print viewer URL, keep working; never fail because of cmux.
- Watch scope: every `*.py` under `cad/splitflap_cad/` (this is what makes params.py edits re-render).
- Log lines from rebuild/push output get a `[HH:MM:SS]` local-time prefix.
- Commit after each task (project rule: auto-commit each coherent step, silently).

## File Structure

```
tools/ctl/
  go.mod            module github.com/0x63616c/split-flap/tools/ctl
  main.go           arg dispatch: bare → root TUI; "cad" → cad dispatch
  cad.go            cad subcommand dispatch: list | export | view | (bare → cad menu)
  python.go         repo-root discovery, uv command builder, catalog JSON parse
  python_test.go    catalog parse unit tests
  port.go           free-port scan
  port_test.go      port scan unit tests
  cmux.go           cmux exec helpers: caller pane, open/close browser tab, notify
  view.go           view command: viewer child, tab, fsnotify loop, cleanup
  tui.go            bubbletea root menu, cad menu, model picker
cad/splitflap_cad/__main__.py   add `list --json`; later remove pin/sync
cad/tests/test_cli.py           new: list --json contract test
justfile                        ctl recipe; cad recipe forwards to ctl
CLAUDE.md                       CAD section rewrite
tools/cad/up.sh                 DELETED
```

---

### Task 1: `list --json` on the python CLI

**Files:**
- Modify: `cad/splitflap_cad/__main__.py:58-64` (cmd_list) and the `list` parser at `:132`
- Test: `cad/tests/test_cli.py` (create)

**Interfaces:**
- Produces: `python -m splitflap_cad list --json` prints one JSON object:
  `{"models": {"<name>": "<help>", …}, "printable": ["<name>", …], "src_to_model": {"<file-stem>": "<model>", …}}`
  Go's `loadCatalog` (Task 3) parses exactly this.

- [ ] **Step 1: Write the failing test**

```python
# cad/tests/test_cli.py
import json

from splitflap_cad.__main__ import main


def test_list_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["splitflap_cad", "list", "--json"])
    main()
    data = json.loads(capsys.readouterr().out)
    assert "assembly" in data["models"]
    assert set(data["printable"]) <= set(data["models"]) | set(data["printable"])
    assert all(isinstance(v, str) for v in data["src_to_model"].values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project cad python -m pytest tests/test_cli.py -v` (cwd `cad/`)
Expected: FAIL — `SystemExit` (argparse rejects `--json`)

- [ ] **Step 3: Implement**

In `cmd_list`:

```python
def cmd_list(args):
    if args.json:
        print(json.dumps({
            "models": {name: m.help for name, m in MODELS.items()},
            "printable": list(PRINTABLE),
            "src_to_model": SRC_TO_MODEL,
        }))
        return
    print("models (just cad view NAME):")
    for name, m in MODELS.items():
        print(f"  {name:<12} {m.help}")
    print("printable (just cad export NAME):")
    for name in PRINTABLE:
        print(f"  {name}")
```

Parser: `sub.add_parser("list", help="every model + printable part").add_argument("--json", action="store_true")`
(keep the parser in a variable to add the argument).

- [ ] **Step 4: Run tests**

Run: `uv run --project cad python -m pytest tests/test_cli.py -v` (cwd `cad/`)
Expected: PASS. Also eyeball: `just cad list` still prints the human table.

- [ ] **Step 5: Commit** — `feat(cad): machine-readable list --json for ctl`

---

### Task 2: Go module scaffold + cad dispatch + passthrough commands

**Files:**
- Create: `tools/ctl/go.mod`, `tools/ctl/main.go`, `tools/ctl/cad.go`, `tools/ctl/python.go`

**Interfaces:**
- Produces: `go run . cad list` / `go run . cad export [name]` work (exec python, inherit stdio). `repoRoot() (string, error)` — walks up from cwd to the dir containing `justfile`. `pyCmd(root string, args ...string) *exec.Cmd` — builds the uv invocation with `Dir: root`.
- Consumes: Task 1's CLI (passthrough only here).

- [ ] **Step 1: Scaffold module**

```bash
cd tools/ctl && go mod init github.com/0x63616c/split-flap/tools/ctl
```

- [ ] **Step 2: Write main.go**

```go
package main

import (
	"fmt"
	"os"
)

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		if err := runRootMenu(); err != nil {
			fmt.Fprintln(os.Stderr, "ctl:", err)
			os.Exit(1)
		}
		return
	}
	var err error
	switch args[0] {
	case "cad":
		err = runCad(args[1:])
	default:
		err = fmt.Errorf("unknown namespace %q (have: cad)", args[0])
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "ctl:", err)
		os.Exit(1)
	}
}
```

- [ ] **Step 3: Write python.go**

```go
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

// repoRoot walks up from cwd to the directory containing `justfile`.
func repoRoot() (string, error) {
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "justfile")); err == nil {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("not inside the split-flap repo (no justfile found)")
		}
		dir = parent
	}
}

// pyCmd builds a splitflap_cad CLI invocation rooted at the repo.
func pyCmd(root string, args ...string) *exec.Cmd {
	full := append([]string{"run", "--project", "cad", "python", "-m", "splitflap_cad"}, args...)
	cmd := exec.Command("uv", full...)
	cmd.Dir = root
	return cmd
}
```

- [ ] **Step 4: Write cad.go**

```go
package main

import (
	"fmt"
	"os"
)

func runCad(args []string) error {
	// just's `cad cmd=""` default passes an empty string — treat as no args
	if len(args) == 0 || args[0] == "" {
		return runCadMenu()
	}
	switch args[0] {
	case "list", "export":
		root, err := repoRoot()
		if err != nil {
			return err
		}
		cmd := pyCmd(root, args...)
		cmd.Stdout, cmd.Stderr, cmd.Stdin = os.Stdout, os.Stderr, os.Stdin
		return cmd.Run()
	case "view":
		model := ""
		if len(args) > 1 {
			model = args[1]
		}
		return runView(model)
	default:
		return fmt.Errorf("unknown cad command %q (have: view, export, list)", args[0])
	}
}
```

Add temporary stubs so it compiles (replaced in Tasks 5/6):

```go
// in view.go (create)
package main

import "fmt"

func runView(model string) error { return fmt.Errorf("view: not implemented yet") }
```

```go
// in tui.go (create)
package main

import "fmt"

func runRootMenu() error { return fmt.Errorf("menu: not implemented yet") }
func runCadMenu() error  { return fmt.Errorf("menu: not implemented yet") }
```

- [ ] **Step 5: Verify**

Run (from `tools/ctl`): `go run . cad list`
Expected: the human model table (same as `just cad list`).
Run: `go run . cad bogus` → exits 1 with `unknown cad command "bogus"`.

- [ ] **Step 6: Commit** — `feat(ctl): Go module scaffold, cad dispatch, list/export passthrough`

---

### Task 3: catalog parsing + free-port scan (unit tested)

**Files:**
- Create: `tools/ctl/port.go`, `tools/ctl/port_test.go`, `tools/ctl/python_test.go`
- Modify: `tools/ctl/python.go` (add catalog)

**Interfaces:**
- Produces:
  - `type catalog struct { Models map[string]string; Printable []string; SrcToModel map[string]string }` (JSON tags `models`, `printable`, `src_to_model`)
  - `parseCatalog(data []byte) (catalog, error)`
  - `loadCatalog(root string) (catalog, error)` — runs `pyCmd(root, "list", "--json")` and parses
  - `freePort(from int) (int, error)` — first port ≥ from that `net.Listen("tcp", "127.0.0.1:N")` accepts

- [ ] **Step 1: Write failing tests**

```go
// python_test.go
package main

import "testing"

func TestParseCatalog(t *testing.T) {
	data := []byte(`{"models":{"assembly":"full unit","holder":"flap jig"},` +
		`"printable":["holder"],"src_to_model":{"holder":"holder","params":""}}`)
	c, err := parseCatalog(data)
	if err != nil {
		t.Fatal(err)
	}
	if c.Models["holder"] != "flap jig" || c.Printable[0] != "holder" || c.SrcToModel["holder"] != "holder" {
		t.Fatalf("bad parse: %+v", c)
	}
}

func TestParseCatalogGarbage(t *testing.T) {
	if _, err := parseCatalog([]byte("not json")); err == nil {
		t.Fatal("want error on garbage")
	}
}
```

```go
// port_test.go
package main

import (
	"fmt"
	"net"
	"testing"
)

func TestFreePortSkipsBusy(t *testing.T) {
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	busy := l.Addr().(*net.TCPAddr).Port
	got, err := freePort(busy)
	if err != nil {
		t.Fatal(err)
	}
	if got == busy {
		t.Fatalf("returned busy port %d", busy)
	}
	if got < busy {
		t.Fatalf("scanned backwards: %d < %d", got, busy)
	}
	l2, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", got))
	if err != nil {
		t.Fatalf("returned port not actually free: %v", err)
	}
	l2.Close()
}
```

- [ ] **Step 2: Run to verify failure**

Run: `go test ./...` (from `tools/ctl`) — Expected: compile FAIL (undefined `parseCatalog`, `freePort`).

- [ ] **Step 3: Implement**

Append to `python.go`:

```go
import ( "encoding/json"; "fmt" )  // merge into existing import block

type catalog struct {
	Models     map[string]string `json:"models"`
	Printable  []string          `json:"printable"`
	SrcToModel map[string]string `json:"src_to_model"`
}

func parseCatalog(data []byte) (catalog, error) {
	var c catalog
	if err := json.Unmarshal(data, &c); err != nil {
		return c, fmt.Errorf("parse model catalog: %w", err)
	}
	return c, nil
}

func loadCatalog(root string) (catalog, error) {
	out, err := pyCmd(root, "list", "--json").Output()
	if err != nil {
		return catalog{}, fmt.Errorf("load model catalog: %w", err)
	}
	return parseCatalog(out)
}
```

```go
// port.go
package main

import (
	"fmt"
	"net"
)

// freePort returns the first free TCP port on 127.0.0.1 at or above `from`.
func freePort(from int) (int, error) {
	for p := from; p < from+100; p++ {
		l, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", p))
		if err != nil {
			continue
		}
		l.Close()
		return p, nil
	}
	return 0, fmt.Errorf("no free port in %d-%d", from, from+99)
}
```

- [ ] **Step 4: Run tests** — `go test ./...` Expected: PASS.

- [ ] **Step 5: Commit** — `feat(ctl): catalog parsing + free-port scan`

---

### Task 4: cmux helpers

**Files:**
- Create: `tools/ctl/cmux.go`

**Interfaces:**
- Produces:
  - `cmuxCallerPane() (string, bool)` — pane ref of the terminal this process runs in (`cmux identify --json` → `caller.pane_ref`); false if cmux missing/unreachable
  - `cmuxOpenViewerTab(pane, url string) (surfaceRef string, ok bool)` — browser tab in that pane, focused (tab 2 = viewer)
  - `cmuxCloseSurface(surface string)`
  - `cmuxNotify(title, body string)`
- No unit tests (thin exec wrappers, cmux-dependent) — exercised by Task 7 manual verification.

- [ ] **Step 1: Implement**

```go
// cmux.go
package main

import (
	"encoding/json"
	"os/exec"
	"regexp"
)

func cmuxCallerPane() (string, bool) {
	out, err := exec.Command("cmux", "identify", "--json").Output()
	if err != nil {
		return "", false
	}
	var id struct {
		Caller struct {
			PaneRef string `json:"pane_ref"`
		} `json:"caller"`
	}
	if json.Unmarshal(out, &id) != nil || id.Caller.PaneRef == "" {
		return "", false
	}
	return id.Caller.PaneRef, true
}

var surfaceRe = regexp.MustCompile(`surface:[0-9]+`)

// cmuxOpenViewerTab adds a focused browser tab to pane (tab 1 stays this
// command's logs, tab 2 becomes the viewer).
func cmuxOpenViewerTab(pane, url string) (string, bool) {
	out, err := exec.Command("cmux", "new-surface", "--type", "browser",
		"--pane", pane, "--url", url, "--focus", "true").Output()
	if err != nil {
		return "", false
	}
	s := surfaceRe.FindString(string(out))
	return s, s != ""
}

func cmuxCloseSurface(surface string) {
	_ = exec.Command("cmux", "close-surface", "--surface", surface).Run()
}

func cmuxNotify(title, body string) {
	_ = exec.Command("cmux", "notify", "--title", title, "--body", body).Run()
}
```

- [ ] **Step 2: Verify compile** — `go build ./...` Expected: clean.

- [ ] **Step 3: Commit** — `feat(ctl): cmux pane/tab/notify helpers`

---

### Task 5: the `view` command

**Files:**
- Modify: `tools/ctl/view.go` (replace stub)

**Interfaces:**
- Consumes: `repoRoot`, `pyCmd`, `loadCatalog`, `freePort`, `cmuxCallerPane`, `cmuxOpenViewerTab`, `cmuxCloseSurface`, `cmuxNotify` — exactly as defined in Tasks 2–4.
- Produces: `runView(model string) error` — model `""` = follow-last-saved. Called by `cad.go` (already wired) and the TUI (Task 6).

Behavior (from spec): free port → spawn `uv run --project cad python -m ocp_vscode --port N` → wait until `GET /viewer` responds → cmux browser tab in caller pane (else print URL) → initial `show` → fsnotify on `cad/splitflap_cad`, 500ms debounce, `.py` only → per save resolve model (pinned, or `src_to_model[stem]` falling back to last shown, initially `assembly`) → `show NAME --port N` with `[HH:MM:SS]`-prefixed output; failure → in-pane log + `cmuxNotify`, viewer keeps last good. Ctrl-C/SIGTERM → close tab, SIGTERM viewer child.

- [ ] **Step 1: Implement**

```go
// view.go
package main

import (
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/fsnotify/fsnotify"
)

func logf(format string, a ...any) {
	fmt.Printf("[%s] "+format+"\n", append([]any{time.Now().Format("15:04:05")}, a...)...)
}

func runView(model string) error {
	root, err := repoRoot()
	if err != nil {
		return err
	}
	cat, err := loadCatalog(root)
	if err != nil {
		return err
	}
	if model != "" {
		if _, ok := cat.Models[model]; !ok {
			return fmt.Errorf("unknown model %q — try: just cad list", model)
		}
	}

	port, err := freePort(3939)
	if err != nil {
		return err
	}
	url := fmt.Sprintf("http://127.0.0.1:%d/viewer", port)

	// viewer child — its output streams into this pane (tab 1)
	viewer := exec.Command("uv", "run", "--project", "cad",
		"python", "-m", "ocp_vscode", "--port", strconv.Itoa(port))
	viewer.Dir = root
	viewer.Stdout, viewer.Stderr = os.Stdout, os.Stderr
	if err := viewer.Start(); err != nil {
		return fmt.Errorf("start viewer: %w", err)
	}
	logf("viewer starting on :%d", port)

	tab := ""
	cleanup := func() {
		if tab != "" {
			cmuxCloseSurface(tab)
		}
		_ = viewer.Process.Signal(syscall.SIGTERM)
		_, _ = viewer.Process.Wait()
	}
	defer cleanup()
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)

	if !waitHTTP(url, 30*time.Second, sig) {
		return fmt.Errorf("viewer on :%d never came up", port)
	}
	if pane, ok := cmuxCallerPane(); ok {
		if s, ok := cmuxOpenViewerTab(pane, url); ok {
			tab = s
			logf("viewer tab %s -> %s", s, url)
		}
	}
	if tab == "" {
		logf("open %s yourself (no cmux)", url)
	}

	// initial + per-save pushes
	last := "assembly"
	if model != "" {
		last = model
	}
	push := func(name string) {
		last = name
		out, err := pyCmd(root, "show", name, "--port", strconv.Itoa(port)).CombinedOutput()
		for _, line := range strings.Split(strings.TrimRight(string(out), "\n"), "\n") {
			logf("%s", line)
		}
		if err != nil {
			logf("BUILD FAILED — viewer keeps last good render")
			cmuxNotify("CAD build failed: "+name, "see view pane log")
		}
	}
	push(last)

	w, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}
	defer w.Close()
	srcDir := filepath.Join(root, "cad", "splitflap_cad")
	if err := w.Add(srcDir); err != nil {
		return err
	}
	if model == "" {
		logf("watching %s (follow last-saved model)", srcDir)
	} else {
		logf("watching %s (pinned: %s)", srcDir, model)
	}

	// debounce: collect events for 500ms after the first, then push once
	var pending string
	var timer *time.Timer
	timerC := func() <-chan time.Time {
		if timer == nil {
			return nil
		}
		return timer.C
	}
	for {
		select {
		case ev := <-w.Events:
			if filepath.Ext(ev.Name) != ".py" || !ev.Has(fsnotify.Write|fsnotify.Create) {
				continue
			}
			pending = ev.Name
			if timer == nil {
				timer = time.NewTimer(500 * time.Millisecond)
			} else {
				timer.Reset(500 * time.Millisecond)
			}
		case <-timerC():
			timer = nil
			name := model
			if name == "" {
				stem := strings.TrimSuffix(filepath.Base(pending), ".py")
				if m, ok := cat.SrcToModel[stem]; ok && m != "" {
					name = m
				} else {
					name = last
				}
			}
			logf("--- %s", filepath.Base(pending))
			push(name)
		case err := <-w.Errors:
			logf("watch error: %v", err)
		case <-sig:
			fmt.Println()
			logf("shutting down")
			return nil
		}
	}
}

// waitHTTP polls url until it responds, times out, or a signal arrives.
func waitHTTP(url string, timeout time.Duration, sig <-chan os.Signal) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		resp, err := http.Get(url)
		if err == nil {
			resp.Body.Close()
			return true
		}
		select {
		case <-sig:
			return false
		case <-time.After(500 * time.Millisecond):
		}
	}
	return false
}
```

Implementer note: import list above includes only what's used — run `go vet ./...` after any edits.

- [ ] **Step 2: Add dependency**

```bash
cd tools/ctl && go get github.com/fsnotify/fsnotify@latest && go mod tidy
```

- [ ] **Step 3: Build + unit tests still green** — `go build ./... && go test ./...` Expected: clean/PASS.

- [ ] **Step 4: Manual smoke (in a cmux pane)**

Run: `cd tools/ctl && go run . cad view holder`
Expected: viewer tab appears in THIS pane showing holder; `touch ../../cad/splitflap_cad/params.py` → `--- params.py` + `pushed holder -> :39xx` in log; Ctrl-C → tab closes, `pgrep -f "ocp_vscode --port 39xx"` empty.

- [ ] **Step 5: Commit** — `feat(ctl): cad view — self-contained live viewer per pane`

---

### Task 6: bubbletea TUI (root menu, cad menu, model picker)

**Files:**
- Modify: `tools/ctl/tui.go` (replace stubs)

**Interfaces:**
- Consumes: `runView(model string)`, `runCad([]string)` passthrough behavior, `loadCatalog`, `repoRoot`.
- Produces: `runRootMenu() error`, `runCadMenu() error` (used by main.go/cad.go — already wired).

Design: minimal hand-rolled list model (no bubbles dependency) — arrow/j/k to move, enter to select, q/esc to back/quit. lipgloss for title + selection highlight. Menus *return a decision*, then run the action AFTER the TUI exits (so `view` logs stream normally in the terminal).

- [ ] **Step 1: Implement**

```go
// tui.go
package main

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle  = lipgloss.NewStyle().Bold(true).Padding(0, 1)
	selStyle    = lipgloss.NewStyle().Reverse(true)
	dimStyle    = lipgloss.NewStyle().Faint(true)
)

type menuItem struct {
	label    string
	disabled bool
}

type menuModel struct {
	title  string
	items  []menuItem
	cursor int
	choice int // -1 = quit/back
}

func newMenu(title string, items []menuItem) menuModel {
	return menuModel{title: title, items: items, choice: -1}
}

func (m menuModel) Init() tea.Cmd { return nil }

func (m menuModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	key, ok := msg.(tea.KeyMsg)
	if !ok {
		return m, nil
	}
	switch key.String() {
	case "up", "k":
		for i := m.cursor - 1; i >= 0; i-- {
			if !m.items[i].disabled {
				m.cursor = i
				break
			}
		}
	case "down", "j":
		for i := m.cursor + 1; i < len(m.items); i++ {
			if !m.items[i].disabled {
				m.cursor = i
				break
			}
		}
	case "enter":
		m.choice = m.cursor
		return m, tea.Quit
	case "q", "esc", "ctrl+c":
		m.choice = -1
		return m, tea.Quit
	}
	return m, nil
}

func (m menuModel) View() string {
	s := titleStyle.Render(m.title) + "\n\n"
	for i, it := range m.items {
		line := "  " + it.label
		if it.disabled {
			line = dimStyle.Render(line)
		} else if i == m.cursor {
			line = selStyle.Render("> " + it.label)
		}
		s += line + "\n"
	}
	return s + "\n" + dimStyle.Render("  ↑/↓ move · enter select · q back") + "\n"
}

// pick runs a menu and returns the chosen index, -1 on quit/back.
func pick(title string, items []menuItem) (int, error) {
	res, err := tea.NewProgram(newMenu(title, items)).Run()
	if err != nil {
		return -1, err
	}
	return res.(menuModel).choice, nil
}

func runRootMenu() error {
	for {
		i, err := pick("ctl — split-flap tooling", []menuItem{
			{label: "cad — viewers & exports"},
			{label: "bench (planned)", disabled: true},
		})
		if err != nil || i == -1 {
			return err
		}
		if err := runCadMenu(); err != nil {
			return err
		}
	}
}

func runCadMenu() error {
	root, err := repoRoot()
	if err != nil {
		return err
	}
	for {
		i, err := pick("cad", []menuItem{
			{label: "view — watch a specific model"},
			{label: "view — watch last saved model"},
			{label: "export — all printables"},
			{label: "export — one model"},
			{label: "list models"},
		})
		if err != nil || i == -1 {
			return err
		}
		switch i {
		case 0:
			name, err := pickModel(root, false)
			if err != nil {
				return err
			}
			if name != "" {
				return runView(name) // foreground until Ctrl-C
			}
		case 1:
			return runView("")
		case 2:
			if err := runCad([]string{"export"}); err != nil {
				return err
			}
		case 3:
			name, err := pickModel(root, true)
			if err != nil {
				return err
			}
			if name != "" {
				if err := runCad([]string{"export", name}); err != nil {
					return err
				}
			}
		case 4:
			if err := runCad([]string{"list"}); err != nil {
				return err
			}
		}
	}
}

// pickModel lists the catalog (printable-only when printable=true).
func pickModel(root string, printable bool) (string, error) {
	cat, err := loadCatalog(root)
	if err != nil {
		return "", err
	}
	var names []string
	var items []menuItem
	if printable {
		for _, n := range cat.Printable {
			names = append(names, n)
			items = append(items, menuItem{label: n})
		}
	} else {
		for n, help := range cat.Models {
			names = append(names, n)
			items = append(items, menuItem{label: fmt.Sprintf("%-12s %s", n, help)})
		}
	}
	i, err := pick("pick a model", items)
	if err != nil || i == -1 {
		return "", err
	}
	return names[i], nil
}
```

Implementer note: map iteration order is random — sort `cat.Models` keys (`sort.Strings`) before building `names`/`items` so the picker is stable.

- [ ] **Step 2: Add dependencies**

```bash
cd tools/ctl && go get github.com/charmbracelet/bubbletea@latest github.com/charmbracelet/lipgloss@latest && go mod tidy
```

- [ ] **Step 3: Build + tests** — `go build ./... && go test ./... && go vet ./...` Expected: clean.

- [ ] **Step 4: Manual smoke**

Run: `go run .` → root menu, `bench` dimmed/unselectable; `cad` → menu; `list models` prints table and returns to menu; `q` twice exits. `view — watch a specific model` → picker → selecting a model starts the live view (Ctrl-C to exit).

- [ ] **Step 5: Commit** — `feat(ctl): bubbletea root/cad menus + model picker`

---

### Task 7: justfile + cleanup + docs

**Files:**
- Modify: `justfile:29-53` (cad recipe), add `ctl` recipe
- Delete: `tools/cad/up.sh` (and the now-empty `tools/cad/`)
- Modify: `cad/splitflap_cad/__main__.py` — remove `pin`, `sync`, `_state`, `_save_state`, `STATE_FILE`, `ASSEMBLY_PORT`; keep `FOCUS_PORT` as `show`'s default port; rewrite module docstring
- Modify: `CLAUDE.md` CAD section
- Test: `cad/tests/test_cli.py` still passes; `just cad list|export|view` work

- [ ] **Step 1: Rewrite justfile recipes**

```make
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
```

(`go run . cad` with empty `cmd` passes no extra args → cad menu. Verify `just cad` opens the menu; if just passes an empty-string arg, guard in `runCad`: treat `args[0] == ""` as no args.)

- [ ] **Step 2: Delete up.sh**

```bash
git rm tools/cad/up.sh
```

- [ ] **Step 3: Trim python CLI**

Remove `cmd_pin`, `cmd_sync`, `_state`, `_save_state`, `STATE_FILE`, `ASSEMBLY_PORT`, the `pin`/`sync` parsers and dispatch entries, and the `pin` arg validation in `main()`. New docstring:

```python
"""splitflap_cad CLI — geometry side of the `just cad` tooling.

    python -m splitflap_cad list [--json]       # catalog: models + printables
    python -m splitflap_cad show NAME [--port]  # build + push one model to a viewer
    python -m splitflap_cad export [NAME]       # write STL(s); no NAME = all
                                                # + flap 3MFs/Bambu plates;
                                                # NAME "flaps" = artwork only

Driven by tools/ctl (Go): `just cad view [model]` runs a viewer + save
watcher in the current pane and calls `show` on every source change.
"""
```

Also delete `cad/.viewer-state.json` if present (untracked state file).

- [ ] **Step 4: Rewrite CLAUDE.md CAD section**

```markdown
## CAD

- `just ctl` = tooling TUI (namespaces; cad for now). `just cad` = cad menu.
  Direct: `just cad view [model]` (live viewer in CURRENT cmux pane — tab 1
  logs, tab 2 viewer; no model = follow last-saved; Ctrl-C = full teardown),
  `just cad export [part]`, `just cad list`, `just cad test|install`.
- Views are self-contained: own port (3939+), own watcher; any .py save in
  cad/splitflap_cad/ re-renders every open view (params.py included).
  Assembly is just a model — `just cad view assembly`. Strays: `pkill -f ocp_vscode`.
- New part: builder + MODELS entry in `catalog.py`. All dims in `params.py`.
  No `__main__` blocks or justfile recipes per part.
- `cad/reference/Unit.stp` = vendor ghost, gitignored. Motor = 28BYJ-48.
```

- [ ] **Step 5: Verify**

Run: `cd cad && uv run python -m pytest` — PASS (test_cli.py included).
Run: `just cad list`, `just cad export holder`, `just ctl` (menu opens), `just cad` (cad menu opens).
Expected: all work; `python -m splitflap_cad pin x` now errors (removed).

- [ ] **Step 6: Commit** — `feat(ctl)!: justfile → ctl, delete up.sh, trim python CLI, docs`

---

### Task 8: end-to-end manual verification

**Files:** none (verification only; fix-forward anything found, commit fixes)

- [ ] **Step 1: Two simultaneous views**

In pane A: `just cad view assembly`. In pane B: `just cad view` (follow). Expected: two viewer tabs, different ports (3939-range), both render.

- [ ] **Step 2: Live update incl. dependency file**

Edit a value in `cad/splitflap_cad/params.py`, save. Expected: BOTH panes log `--- params.py` and re-push (assembly pane pushes assembly; follow pane pushes params' fallback = its last model).
Save `holder.py`. Expected: follow pane switches to holder; assembly pane still pushes assembly.

- [ ] **Step 3: Build failure path**

Introduce a syntax error in `params.py`, save. Expected: `BUILD FAILED` log lines in-pane + cmux notification; viewers keep last good render. Revert; next save recovers.

- [ ] **Step 4: Teardown**

Ctrl-C both. Expected: tabs close, `pgrep -f ocp_vscode` empty, no state files created anywhere (`git status` clean apart from intended changes).

- [ ] **Step 5: Commit any fixes** — `fix(ctl): <what verification found>`
