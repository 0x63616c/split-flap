package main

import (
	"bufio"
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

// runView is the CLI entrypoint: viewJob with stdout logging and Ctrl-C as
// the stop signal.
func runView(model string) error {
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	stop := make(chan struct{})
	go func() { <-sig; close(stop) }()
	return viewJob(model, func(s string) { fmt.Println(s) }, stop)
}

// viewJob turns the current pane into a live viewer: own viewer server on a
// free port, browser tab here (tab 2), rebuild+push on every .py save.
// model "" = follow the last-saved file's model. Log lines go to emit;
// closing stop tears it all down. Shared by the CLI path and the TUI run
// screen.
func viewJob(model string, emit func(string), stop <-chan struct{}) error {
	logf := func(format string, a ...any) {
		emit(fmt.Sprintf("[%s] "+format, append([]any{time.Now().Format("15:04:05")}, a...)...))
	}

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

	// viewer child — its output streams into the log
	viewer := exec.Command("uv", "run", "--project", "cad",
		"python", "-m", "ocp_vscode", "--port", strconv.Itoa(port))
	viewer.Dir = root
	viewer.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	vout, vw, err := os.Pipe()
	if err != nil {
		return err
	}
	viewer.Stdout, viewer.Stderr = vw, vw
	if err := viewer.Start(); err != nil {
		vout.Close()
		vw.Close()
		return fmt.Errorf("start viewer: %w", err)
	}
	vw.Close() // child holds the write end
	go func() {
		sc := bufio.NewScanner(vout)
		for sc.Scan() {
			emit(sc.Text())
		}
		vout.Close()
	}()
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

	if !waitHTTP(url, 30*time.Second, stop) {
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
		case <-stop:
			logf("shutting down")
			return nil
		}
	}
}

// waitHTTP polls url until it responds, times out, or stop closes.
func waitHTTP(url string, timeout time.Duration, stop <-chan struct{}) bool {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		resp, err := http.Get(url)
		if err == nil {
			resp.Body.Close()
			return true
		}
		select {
		case <-stop:
			return false
		case <-time.After(500 * time.Millisecond):
		}
	}
	return false
}
