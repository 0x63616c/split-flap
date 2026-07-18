package main

// Bench transport — the host half of the breadboard bring-up rig.
//
// Talks to firmware/micropython-spike/bench_board.py over USB serial, one
// ASCII line per command:
//
//	host -> board:   HOME | ZERO | GOTO <step> [slow] | POS | HALL |
//	                 SPEED <rpm> | NUDGE <n> | RESET | PING
//	board -> host:   OK <key>=<val> ...   |   ERR <msg>
//
// Every call blocks for as long as the drum takes to move (HOME can sweep
// ~10s), so all of it runs on a worker goroutine — see benchWorker. The TUI
// only ever reads the snapshots the worker pushes at it.

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"go.bug.st/serial"
)

const (
	benchBaud = 115200
	maxRPM    = 16 // firmware cap (bench-measured stall margin)
	// minNudge is the smallest nudge that reliably moves the drum; below this
	// the 28BYJ backlash eats it, so we refuse rather than pretend.
	minNudge     = 10
	benchDwell   = time.Second      // pause between glyphs when a string is typed
	benchTimeout = 25 * time.Second // HOME can sweep most of a rev
)

// --- ports & flashing ----------------------------------------------------

// benchPorts lists the attached USB serial devices, newest-looking first by
// name. Replaces the justfile's `ls /dev/cu.usbmodem*`.
func benchPorts() []string {
	paths, err := filepath.Glob("/dev/cu.usbmodem*")
	if err != nil {
		return nil
	}
	sort.Strings(paths)
	return paths
}

// defaultBenchPort is the port the bench opens when none was named.
func defaultBenchPort() string {
	if p := benchPorts(); len(p) > 0 {
		return p[0]
	}
	return ""
}

// freeBenchPort kills any stale mpremote holding the port. Only one process
// can own the CDC device, so a leftover session blocks the whole bench.
func freeBenchPort() {
	_ = exec.Command("pkill", "-f", "mpremote connect").Run()
	time.Sleep(time.Second)
}

// flashBench copies the bench command loop onto the board as :main.py and
// resets it, so the board boots standalone into the serial protocol. This is
// the old `just up` flash half; output goes to emit line by line.
func flashBench(root, port string, emit func(string)) error {
	freeBenchPort()
	cmd := exec.Command("uv", "run", "--with", "mpremote",
		"python3", "-m", "mpremote", "connect", port,
		"cp", "firmware/micropython-spike/bench_board.py", ":main.py", "+", "reset")
	cmd.Dir = root
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	out, err := cmd.CombinedOutput()
	for _, line := range strings.Split(strings.TrimRight(string(out), "\n"), "\n") {
		if line != "" {
			emit(line)
		}
	}
	if err != nil {
		return fmt.Errorf("flash: %w", err)
	}
	return nil
}

// --- home glyph persistence ----------------------------------------------

// The home glyph (which flap the magnet sits opposite) is a per-module fact
// set at calibration. It's pure planning maths, so we keep it host-side
// (unlike the mechanical nudge offset, which lives on the board).
func homeGlyphPath(root string) string {
	return filepath.Join(root, ".bench", "home_glyph.txt")
}

func loadHomeGlyph(root string, d *drum) {
	b, err := os.ReadFile(homeGlyphPath(root))
	if err != nil {
		return
	}
	rs := []rune(strings.TrimRight(string(b), "\r\n"))
	if len(rs) == 0 {
		rs = []rune{blank}
	}
	_, _ = d.setHomeGlyph(rs[0])
}

func saveHomeGlyph(root string, g rune) error {
	p := homeGlyphPath(root)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	return os.WriteFile(p, []byte(string(g)), 0o644)
}

func clearHomeGlyph(root string) {
	_ = os.Remove(homeGlyphPath(root))
}

// --- connection ----------------------------------------------------------

type benchConn struct {
	port serial.Port
}

// openBench opens the port and handshakes. Opening the CDC port can auto-reset
// the ESP32-C6 (DTR/RTS), so the board may be mid-reboot: wait it out, drain
// the boot banner, then PING until it answers. Returns the board's reply so
// the caller can read the RPM out of it.
func openBench(path string) (*benchConn, string, error) {
	p, err := serial.Open(path, &serial.Mode{BaudRate: benchBaud})
	if err != nil {
		return nil, "", err
	}
	// Short per-read timeout, long per-LINE deadline: readLine loops on the
	// empty reads so it can give up on a mute board without blocking for the
	// whole 25s on every byte.
	if err := p.SetReadTimeout(500 * time.Millisecond); err != nil {
		p.Close()
		return nil, "", err
	}
	c := &benchConn{port: p}
	time.Sleep(1500 * time.Millisecond)
	_ = p.ResetInputBuffer()
	for i := 0; i < 6; i++ {
		if _, err := p.Write([]byte("PING\n")); err != nil {
			c.Close()
			return nil, "", err
		}
		line, err := c.readLineWithin(2 * time.Second)
		if err == nil && strings.Contains(line, "pong") {
			return c, line, nil
		}
		time.Sleep(500 * time.Millisecond)
	}
	c.Close()
	return nil, "", fmt.Errorf("no response from board on %s — is it flashed? (bench › flash & connect)", path)
}

func (c *benchConn) Close() { _ = c.port.Close() }

// readLine reads one newline-terminated reply, waiting up to benchTimeout for
// the board to finish moving.
func (c *benchConn) readLine() (string, error) {
	return c.readLineWithin(benchTimeout)
}

// readLineWithin reads a line, giving up after d. A serial read timeout comes
// back as (0, nil), so an empty read is just a tick of the clock, not an error.
func (c *benchConn) readLineWithin(d time.Duration) (string, error) {
	deadline := time.Now().Add(d)
	var line []byte
	buf := make([]byte, 1)
	for time.Now().Before(deadline) {
		n, err := c.port.Read(buf)
		if err != nil {
			return "", err
		}
		if n == 0 {
			continue
		}
		if buf[0] == '\n' {
			if s := strings.TrimSpace(string(line)); s != "" {
				return s, nil
			}
			line = line[:0] // bare newline (boot banner) — keep reading
			continue
		}
		line = append(line, buf[0])
	}
	return "", fmt.Errorf("board went quiet (timeout)")
}

// cmd sends one line and returns the reply, turning an ERR reply into an error.
func (c *benchConn) cmd(line string) (string, error) {
	if _, err := c.port.Write([]byte(line + "\n")); err != nil {
		return "", err
	}
	reply, err := c.readLine()
	if err != nil {
		return "", err
	}
	if strings.HasPrefix(reply, "ERR") {
		return reply, fmt.Errorf("%s", reply)
	}
	return reply, nil
}

// field pulls `key=<int>` out of an OK reply, or returns def.
func field(reply, key string, def int) int {
	for _, tok := range strings.Fields(reply) {
		if strings.HasPrefix(tok, key+"=") {
			if n, err := strconv.Atoi(tok[len(key)+1:]); err == nil {
				return n
			}
		}
	}
	return def
}

// --- worker --------------------------------------------------------------

// benchSnapshot is everything the screen draws. The worker owns the truth and
// pushes a fresh copy after every command; the TUI never touches the port.
type benchSnapshot struct {
	port      string
	connected bool
	curStep   int
	slip      int
	rpm       int
	offset    int
	homed     bool
	homeGlyph rune
	queue     []rune // glyphs still to drive (first is the one just driven)
	busy      bool
}

type benchSnapMsg benchSnapshot
type benchLogMsg struct{ line string }
type benchDoneMsg struct{ err error } // connection gone for good

// benchReq is one unit of work for the worker.
type benchReq struct {
	kind   string // home homecal zero pos hall speed nudge reset sethome glyphs
	n      int    // speed rpm / nudge steps
	glyphs []rune
}

type benchWorker struct {
	reqs chan benchReq
	msgs chan tea.Msg
	quit chan struct{}

	// cancel aborts an in-flight glyph sequence. Replaced per sequence by the
	// worker and closed by the UI goroutine, so it takes the mutex.
	mu     sync.Mutex
	cancel chan struct{}

	root string
	conn *benchConn
	d    *drum
	snap benchSnapshot
}

// startBench spins the worker up: it flashes (optionally), connects, then
// serves requests until quit. Everything it wants to say arrives on msgs.
func startBench(root, port string, flash bool) *benchWorker {
	w := &benchWorker{
		reqs:   make(chan benchReq, 8),
		msgs:   make(chan tea.Msg, 64),
		cancel: make(chan struct{}),
		quit:   make(chan struct{}),
		root:   root,
		d:      &drum{},
		snap:   benchSnapshot{port: port, rpm: 12, busy: true},
	}
	loadHomeGlyph(root, w.d)
	go w.run(flash)
	return w
}

// emit posts a message, but never blocks a teardown: if the UI has stopped
// draining and we're quitting, the message is dropped.
func (w *benchWorker) emit(msg tea.Msg) {
	select {
	case w.msgs <- msg:
	case <-w.quit:
	}
}

func (w *benchWorker) log(format string, a ...any) {
	w.emit(benchLogMsg{fmt.Sprintf(format, a...)})
}

func (w *benchWorker) push() {
	w.snap.homeGlyph = w.d.homeGlyph()
	w.emit(benchSnapMsg(w.snap))
}

// stop tears the worker down; safe to call twice.
func (w *benchWorker) stop() {
	select {
	case <-w.quit:
	default:
		close(w.quit)
	}
}

// abort cancels an in-flight glyph sequence without killing the connection.
func (w *benchWorker) abort() {
	w.mu.Lock()
	defer w.mu.Unlock()
	select {
	case <-w.cancel:
	default:
		close(w.cancel)
	}
}

// newCancel arms a fresh cancel channel for the sequence about to start.
func (w *benchWorker) newCancel() chan struct{} {
	w.mu.Lock()
	defer w.mu.Unlock()
	w.cancel = make(chan struct{})
	return w.cancel
}

// send queues a request, dropping it if the worker is gone or swamped.
func (w *benchWorker) send(r benchReq) {
	select {
	case w.reqs <- r:
	case <-w.quit:
	default:
	}
}

func (w *benchWorker) run(flash bool) {
	defer func() {
		if w.conn != nil {
			w.conn.Close()
		}
		w.msgs <- benchDoneMsg{}
	}()

	if w.snap.port == "" {
		w.log("no USB modem attached — plug the board in, then esc and retry")
		w.snap.busy = false
		w.push()
		<-w.quit
		return
	}
	if flash {
		w.log("flashing %s …", filepath.Base(w.snap.port))
		if err := flashBench(w.root, w.snap.port, func(s string) { w.log("%s", s) }); err != nil {
			w.log("error: %v", err)
			w.snap.busy = false
			w.push()
			<-w.quit
			return
		}
	}
	w.log("opening %s …", w.snap.port)
	conn, banner, err := openBench(w.snap.port)
	if err != nil {
		w.log("error: %v", err)
		w.snap.busy = false
		w.push()
		<-w.quit
		return
	}
	w.conn = conn
	w.snap.connected = true
	w.snap.rpm = field(banner, "rpm", w.snap.rpm)
	w.log("board up: %s", banner)
	// The board keeps its nudge offset across reboots — read it back so the
	// screen shows the real calibration, not a fresh zero.
	if reply, err := w.cmd("OFFSET"); err == nil {
		w.snap.offset = field(reply, "offset", 0)
	}
	w.snap.busy = false
	w.push()

	for {
		select {
		case <-w.quit:
			return
		case r := <-w.reqs:
			w.snap.busy = true
			w.push()
			w.handle(r)
			w.snap.busy = false
			w.snap.queue = nil
			w.push()
		}
	}
}

// cmd runs a board command and logs the exchange, mirroring the python
// transport's dim `CMD -> reply` trace.
func (w *benchWorker) cmd(line string) (string, error) {
	reply, err := w.conn.cmd(line)
	w.log("%s -> %s", line, reply)
	if err != nil {
		return reply, err
	}
	return reply, nil
}

func (w *benchWorker) handle(r benchReq) {
	switch r.kind {
	case "home", "homecal":
		reply, err := w.cmd("HOME")
		if err != nil {
			w.log("error: %v", err)
			return
		}
		w.snap.curStep = field(reply, "step", 0)
		w.snap.slip = 0
		w.snap.homed = true
		if r.kind == "homecal" {
			// /homecal STOPS on the home flap so you can read what's physically
			// there and declare it with /sethome.
			w.log("homed on the home flap — read it, then /sethome <that glyph>")
			return
		}
		// Normal /home settles to blank: the home flap is a calibration anchor,
		// not a rest state.
		_, tgt, fwd, crosses, err := w.d.plan(w.snap.curStep, blank)
		if err != nil || fwd == 0 {
			return
		}
		w.log("homed on '%c', settling to blank (+%d, slow)", w.d.homeGlyph(), fwd)
		w.moveTo(tgt, crosses, true)
	case "zero":
		reply, err := w.cmd("ZERO")
		if err != nil {
			w.log("error: %v", err)
			return
		}
		w.snap.curStep = field(reply, "step", 0)
		w.snap.homed = true
	case "pos":
		w.pos()
	case "hall":
		reply, err := w.cmd("HALL")
		if err != nil {
			w.log("error: %v", err)
			return
		}
		v := field(reply, "hall", -1)
		state := "clear"
		if v == 0 {
			state = "magnet present"
		}
		w.log("hall=%d  %s", v, state)
	case "speed":
		reply, err := w.cmd(fmt.Sprintf("SPEED %d", r.n))
		if err != nil {
			w.log("error: %v   (board may need a reflash)", err)
			return
		}
		w.snap.rpm = field(reply, "rpm", r.n)
	case "nudge":
		reply, err := w.cmd(fmt.Sprintf("NUDGE %d", r.n))
		if err != nil {
			w.log("error: %v   (board may need a reflash)", err)
			return
		}
		w.snap.offset = field(reply, "offset", w.snap.offset)
		w.snap.curStep = field(reply, "step", w.snap.curStep)
		deg := float64(abs(r.n)) * 360 / stepsPerRev
		flap := float64(abs(r.n)) * float64(nSlots) / stepsPerRev
		w.log("  %+d steps = %.2f° = %.2f flap", r.n, deg, flap)
	case "reset":
		reply, err := w.cmd("RESET")
		if err != nil {
			w.log("error: %v", err)
			return
		}
		w.snap.offset = field(reply, "offset", 0)
		_, _ = w.d.setHomeGlyph(blank)
		clearHomeGlyph(w.root)
		w.log("reset: offset 0, home glyph blank (re-home + re-calibrate)")
	case "sethome":
		g, err := w.d.setHomeGlyph(r.glyphs[0])
		if err != nil {
			w.log("%v", err)
			return
		}
		if err := saveHomeGlyph(w.root, g); err != nil {
			w.log("error saving home glyph: %v", err)
			return
		}
		w.log("home glyph: home flap = '%c' (saved)", g)
	case "glyphs":
		w.driveString(r.glyphs)
	}
}

// pos re-queries the board's absolute position.
func (w *benchWorker) pos() {
	reply, err := w.cmd("POS")
	if err != nil {
		w.log("error: %v", err)
		return
	}
	w.snap.curStep = field(reply, "step", w.snap.curStep)
}

// moveTo drives forward to an absolute step. crosses is only for the log —
// the board resyncs on the magnet by itself when a move sweeps it.
func (w *benchWorker) moveTo(tgt int, crosses, slow bool) {
	line := fmt.Sprintf("GOTO %d", tgt)
	if slow {
		line += " slow"
	}
	reply, err := w.cmd(line)
	if err != nil {
		w.log("error: %v", err)
		return
	}
	w.snap.curStep = field(reply, "step", tgt)
	if crosses {
		w.log("passed home: counter resynced on the magnet")
	}
}

// driveString steps through a whole typed string, dwelling between glyphs, so
// "123123" drives 1, pause, 2, pause, 3, … Esc cancels between glyphs.
func (w *benchWorker) driveString(seq []rune) {
	cancel := w.newCancel()
	for i, ch := range seq {
		w.snap.queue = seq[i:]
		w.push()
		w.pos()
		slot, tgt, fwd, crosses, err := w.d.plan(w.snap.curStep, ch)
		if err != nil {
			w.log("%v", err)
		} else {
			w.log("goto %c slot %d: +%d steps -> step %d", w.d.slotToGlyph(slot), slot, fwd, tgt)
			w.moveTo(tgt, crosses, false)
		}
		w.push()
		if i == len(seq)-1 {
			continue
		}
		select {
		case <-time.After(benchDwell):
		case <-cancel:
			w.log("cancelled — %d glyph(s) dropped", len(seq)-i-1)
			return
		case <-w.quit:
			return
		}
	}
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
