package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/fsnotify/fsnotify"
)

// runPcbView is the CLI entrypoint: pcbViewJob with stdout logging and Ctrl-C
// as the stop signal.
func runPcbView() error {
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	stop := make(chan struct{})
	go func() { <-sig; close(stop) }()
	return pcbViewJob(func(s string) { fmt.Println(s) }, stop)
}

// pcbViewJob turns the current pane into a live 3D board viewer: a static
// server on a free port serving tools/viewer/ plus a freshly exported
// board.glb, a browser tab here (tab 2), and a re-place + re-export on every
// save of the placement script or main.ato. The page polls /rev and reloads
// itself when the revision moves.
//
// Mirrors viewJob (the CAD viewer) deliberately — same port/tab/teardown
// shape, so both viewers behave identically from the user's side.
func pcbViewJob(emit func(string), stop <-chan struct{}) error {
	logf := func(format string, a ...any) {
		emit(fmt.Sprintf("[%s] "+format, append([]any{time.Now().Format("15:04:05")}, a...)...))
	}

	root, err := repoRoot()
	if err != nil {
		return err
	}
	if _, err := kicadCLI(); err != nil {
		return err
	}

	viewerDir := filepath.Join(pcbDir(root), "tools", "viewer")
	if _, err := os.Stat(filepath.Join(viewerDir, "index.html")); err != nil {
		return fmt.Errorf("viewer assets missing at %s", viewerDir)
	}
	glbPath := filepath.Join(viewerDir, "board.glb")

	logf("exporting board.glb…")
	if err := exportGLB(root, glbPath); err != nil {
		return err
	}

	port, err := freePort(3950)
	if err != nil {
		return err
	}
	url := fmt.Sprintf("http://127.0.0.1:%d/", port)

	// rev is bumped on every successful rebuild; the page polls it and reloads.
	var rev atomic.Int64
	mux := http.NewServeMux()
	mux.HandleFunc("/rev", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		fmt.Fprint(w, rev.Load())
	})
	mux.Handle("/", noCache(http.FileServer(http.Dir(viewerDir))))
	srv := &http.Server{Addr: fmt.Sprintf("127.0.0.1:%d", port), Handler: mux}
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			emit("server: " + err.Error())
		}
	}()
	logf("viewer serving %s on :%d", viewerDir, port)

	tab := ""
	cleanup := func() {
		if tab != "" {
			cmuxCloseSurface(tab)
		}
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_ = srv.Shutdown(ctx)
	}
	defer cleanup()

	if !waitHTTP(url, 15*time.Second, stop) {
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

	// rebuild: re-place, then re-export the GLB. A failure keeps the last good
	// model on screen, same as the CAD viewer.
	rebuild := func(trigger string) {
		logf("--- %s", trigger)
		out, err := pcbPlace(root).CombinedOutput()
		for _, line := range strings.Split(strings.TrimRight(string(out), "\n"), "\n") {
			if line != "" {
				logf("%s", line)
			}
		}
		if err != nil {
			logf("PLACE FAILED — viewer keeps last good model")
			cmuxNotify("PCB place failed", "see view pane log")
			return
		}
		if err := exportGLB(root, glbPath); err != nil {
			logf("%v", err)
			logf("GLB EXPORT FAILED — viewer keeps last good model")
			cmuxNotify("PCB glb export failed", "see view pane log")
			return
		}
		rev.Add(1)
		logf("reloaded (rev %d)", rev.Load())
	}

	w, err := fsnotify.NewWatcher()
	if err != nil {
		return err
	}
	defer w.Close()
	// watch the SOURCES, not the .kicad_pcb — placement rewrites that file, so
	// watching it would retrigger this loop forever
	watched := []string{filepath.Join(pcbDir(root), "tools"), pcbDir(root)}
	for _, d := range watched {
		if err := w.Add(d); err != nil {
			return err
		}
	}
	logf("watching place_and_render.py + main.ato")

	interesting := func(name string) bool {
		switch filepath.Base(name) {
		case "place_and_render.py", "main.ato":
			return true
		}
		return false
	}

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
			if !interesting(ev.Name) || !ev.Has(fsnotify.Write|fsnotify.Create) {
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
			rebuild(filepath.Base(pending))
		case err := <-w.Errors:
			logf("watch error: %v", err)
		case <-stop:
			logf("shutting down")
			return nil
		}
	}
}

// noCache keeps the browser from serving a stale board.glb after a rebuild.
func noCache(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store, must-revalidate")
		h.ServeHTTP(w, r)
	})
}
