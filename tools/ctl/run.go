package main

import (
	"bufio"
	"os"
	"os/exec"
	"path/filepath"
	"sync"
	"syscall"

	tea "github.com/charmbracelet/bubbletea"
)

// A run is a job executing inside the TUI's run screen: log lines stream in
// as messages, esc stops it, and the menu stays underneath. Modal — one at a
// time.

type logMsg struct{ line string }
type runDoneMsg struct{ err error }

const maxLogLines = 4000

type runState struct {
	ch       chan tea.Msg
	stop     func() // idempotent cancel
	lines    []string
	scroll   int // lines scrolled up from the tail; 0 = follow
	done     bool
	err      error
	stopping bool // esc pressed while running → pop as soon as it finishes
}

// listenRun forwards the next job message to Update; re-issued per message.
func listenRun(ch chan tea.Msg) tea.Cmd {
	return func() tea.Msg { return <-ch }
}

// startExport streams `splitflap_cad export [model...]` into the run screen.
func startExport(root string, models ...string) *runState {
	args := append([]string{"export"}, models...)
	return streamCmd(pyCmd(root, args...))
}

// startGoldenTest streams the slow suite: full catalog build + BREP XOR against
// cad/tests/golden/. Lives outside splitflap_cad, so it's pytest directly.
func startGoldenTest(root string) *runState {
	cmd := exec.Command("uv", "run", "python", "-m", "pytest", "-m", "slow")
	cmd.Dir = filepath.Join(root, "cad")
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	return streamCmd(cmd)
}

// streamCmd runs cmd with stdout+stderr merged into a run screen's log; stop()
// SIGTERMs it.
func streamCmd(cmd *exec.Cmd) *runState {
	ch := make(chan tea.Msg, 64)
	r := &runState{ch: ch, stop: func() {}}

	pr, pw, err := os.Pipe()
	if err != nil {
		go func() { ch <- runDoneMsg{err} }()
		return r
	}
	cmd.Stdout, cmd.Stderr = pw, pw
	if err := cmd.Start(); err != nil {
		pr.Close()
		pw.Close()
		go func() { ch <- runDoneMsg{err} }()
		return r
	}
	pw.Close() // child holds the write end; EOF on pr when it exits
	var once sync.Once
	r.stop = func() { once.Do(func() { _ = cmd.Process.Signal(syscall.SIGTERM) }) }
	go func() {
		sc := bufio.NewScanner(pr)
		sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
		for sc.Scan() {
			ch <- logMsg{sc.Text()}
		}
		pr.Close()
		ch <- runDoneMsg{cmd.Wait()}
	}()
	return r
}

// startView runs the live-viewer flow (viewer child, browser tab, fsnotify
// pushes) with its log routed into the run screen; stop() tears it down.
func startView(model string) *runState {
	ch := make(chan tea.Msg, 256)
	stopc := make(chan struct{})
	var once sync.Once
	r := &runState{
		ch:   ch,
		stop: func() { once.Do(func() { close(stopc) }) },
	}
	go func() {
		err := viewJob(model, func(s string) { ch <- logMsg{s} }, stopc)
		ch <- runDoneMsg{err}
	}()
	return r
}
