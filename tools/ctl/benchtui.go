package main

// The bench screen — type a glyph, the module homes (once) then drives forward
// to that glyph's slot. Replaces the python REPL that used to live in
// tools/bench/bench_ui.py; the slot maths are in slotplan.go, the serial
// transport in bench.go, and this file is the shell around them.
//
// Calibrating a module once (do it in this order):
//
//	/reset      offset 0, home glyph blank
//	/homecal    seek the magnet and STOP on the home flap
//	/nudge 20   centre the char in the window (may roll onto the next flap)
//	/sethome 2  READ the flap and declare it — whatever it physically shows
//
// Then typing 'C' drives to C and /home re-homes and settles on blank. The
// nudge lives on the board (survives reboot/reflash); the home glyph is saved
// in .bench/.
//
// The glyph shown is a MODEL (home glyph + step count), not a camera — if it
// disagrees with the real drum, the home glyph is set wrong.

import (
	"fmt"
	"strconv"
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

const benchMaxLog = 200

type benchModel struct {
	w    *benchWorker
	snap benchSnapshot
	log  []string

	input   string
	history []string
	hist    int // index into history while browsing; len(history) = editing
	help    bool
}

// listenBench forwards the worker's next message to Update; re-issued per
// message, exactly like listenRun does for the run screen.
func listenBench(ch chan tea.Msg) tea.Cmd {
	return func() tea.Msg { return <-ch }
}

// startBenchScreen pushes the bench screen and starts the worker.
func (m *appModel) startBenchScreen(port string, flash bool) (tea.Model, tea.Cmd) {
	if port == "" {
		port = defaultBenchPort()
	}
	w := startBench(m.root, port, flash)
	// Seed the first frame from the saved calibration so the screen doesn't
	// flash a blank home glyph while the board is still handshaking.
	var d drum
	loadHomeGlyph(m.root, &d)
	m.bench = &benchModel{w: w, snap: benchSnapshot{
		port: port, rpm: 12, busy: true, homeGlyph: d.homeGlyph()}}
	title := "bench"
	if port != "" {
		title = "bench " + trimPort(port)
	}
	m.stack = append(m.stack, screen{id: "bench", title: title})
	return m, listenBench(w.msgs)
}

func (m *appModel) popBench() {
	if m.bench != nil {
		m.bench.w.stop()
		m.bench = nil
	}
	if len(m.stack) > 1 {
		m.stack = m.stack[:len(m.stack)-1]
	}
}

// trimPort shortens /dev/cu.usbmodem511RMQK2R3403 for a breadcrumb.
func trimPort(p string) string {
	return strings.TrimPrefix(p, "/dev/cu.")
}

// benchKey handles keys while the bench screen is on top. Esc is layered:
// it closes the help, then cancels a running sequence, then leaves.
func (m *appModel) benchKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	b := m.bench
	switch msg.Type {
	case tea.KeyRunes:
		b.input += string(msg.Runes)
		return m, nil
	case tea.KeySpace:
		b.input += " "
		return m, nil
	}
	switch msg.String() {
	case "esc":
		switch {
		case b.help:
			b.help = false
		case b.snap.busy:
			b.w.abort()
		default:
			m.popBench()
		}
	case "enter":
		return m.benchSubmit()
	case "backspace":
		if rs := []rune(b.input); len(rs) > 0 {
			b.input = string(rs[:len(rs)-1])
		}
	case "alt+backspace", "ctrl+w":
		b.input = killWord(b.input)
	case "up":
		b.recall(-1)
	case "down":
		b.recall(+1)
	}
	return m, nil
}

// recall walks the input history, the way readline's up-arrow did.
func (b *benchModel) recall(delta int) {
	if len(b.history) == 0 {
		return
	}
	i := b.hist + delta
	if i < 0 {
		i = 0
	}
	if i > len(b.history) {
		i = len(b.history)
	}
	b.hist = i
	if i == len(b.history) {
		b.input = ""
		return
	}
	b.input = b.history[i]
}

func (b *benchModel) logf(format string, a ...any) {
	b.log = append(b.log, fmt.Sprintf(format, a...))
	if len(b.log) > benchMaxLog {
		b.log = b.log[len(b.log)-benchMaxLog:]
	}
}

// benchSubmit interprets the typed line: a slash command, or a string of
// glyphs to drive through.
func (m *appModel) benchSubmit() (tea.Model, tea.Cmd) {
	b := m.bench
	raw := strings.TrimSpace(b.input)
	b.input = ""
	if raw != "" {
		b.history = append(b.history, raw)
	}
	b.hist = len(b.history)
	b.help = false

	bits := strings.Fields(raw)
	cmd := strings.ToLower(raw)
	if len(bits) > 0 {
		cmd = strings.ToLower(bits[0])
	}

	// Commands that never touch the board.
	switch cmd {
	case "/quit", "q":
		m.popBench()
		return m, nil
	case "/help":
		b.help = true
		return m, nil
	}
	if !b.snap.connected {
		b.logf("%s: not connected to a board", errStyle.Render("refused"))
		return m, nil
	}

	switch {
	case cmd == "/home", cmd == "/homecal":
		b.w.send(benchReq{kind: strings.TrimPrefix(cmd, "/")})
	case cmd == "/zero":
		b.w.send(benchReq{kind: "zero"})
	case cmd == "/pos":
		b.w.send(benchReq{kind: "pos"})
	case cmd == "/hall":
		b.w.send(benchReq{kind: "hall"})
	case cmd == "/reset":
		b.w.send(benchReq{kind: "reset"})
	case cmd == "/speed":
		n, err := strconv.Atoi(lastArg(bits))
		if err != nil || n < 1 || n > maxRPM {
			b.logf(errStyle.Render("usage")+": /speed <integer 1-%d>", maxRPM)
			return m, nil
		}
		b.w.send(benchReq{kind: "speed", n: n})
	case cmd == "/nudge":
		n, err := strconv.Atoi(strings.TrimPrefix(lastArg(bits), "+"))
		if err != nil {
			b.logf(errStyle.Render("usage")+": /nudge <±n half-steps>   %s",
				dimStyle.Render(fmt.Sprintf("(min ±%d; smaller gets eaten by backlash)", minNudge)))
			return m, nil
		}
		if abs(n) < minNudge {
			b.logf(errStyle.Render("refused")+": /nudge min ±%d   %s", minNudge,
				dimStyle.Render(fmt.Sprintf("(%+d is sub-visible — backlash eats it)", n)))
			return m, nil
		}
		if !b.snap.homed {
			b.logf("%s: not homed — /home or /zero first", errStyle.Render("refused"))
			return m, nil
		}
		b.w.send(benchReq{kind: "nudge", n: n})
	case cmd == "/sethome":
		if len(bits) != 2 || len([]rune(bits[1])) != 1 {
			b.logf(errStyle.Render("usage")+": /sethome <glyph>   %s",
				dimStyle.Render("(the flap showing at home right now)"))
			return m, nil
		}
		b.w.send(benchReq{kind: "sethome", glyphs: []rune(bits[1])})
	case strings.HasPrefix(cmd, "/"):
		b.logf(errStyle.Render("unknown command")+": %s   %s", raw, dimStyle.Render("(/help)"))
	default:
		if !b.snap.homed {
			b.logf("%s: not homed — run /home or /zero first", errStyle.Render("refused"))
			return m, nil
		}
		seq := []rune(raw)
		if len(seq) == 0 {
			seq = []rune{blank} // bare enter = one blank
		}
		b.w.send(benchReq{kind: "glyphs", glyphs: seq})
	}
	return m, nil
}

func lastArg(bits []string) string {
	if len(bits) < 2 {
		return ""
	}
	return bits[1]
}

// --- render --------------------------------------------------------------

func (m *appModel) benchView() string {
	b := m.bench
	if b.help {
		return m.benchHelpView()
	}
	s := b.snap
	d := drum{}
	if s.homeGlyph != 0 {
		_, _ = d.setHomeGlyph(s.homeGlyph)
	}
	slot := nearestSlot(s.curStep)
	glyph := d.slotToGlyph(slot)
	shown := string(glyph)
	blankTag := ""
	if glyph == blank {
		shown = "␣" // make blank visible
		blankTag = "   " + dimStyle.Render("(blank)")
	}

	var out []string
	if len(s.queue) > 1 {
		upcoming := []rune(strings.ReplaceAll(string(s.queue), " ", "␣"))
		out = append(out, fmt.Sprintf("  %s       %s%s   %s",
			boldStyle.Render("queue"),
			warnStyle.Render(string(upcoming[0])),
			dimStyle.Render(string(upcoming[1:])),
			dimStyle.Render(fmt.Sprintf("(%d left)", len(s.queue)))))
		out = append(out, "")
	}
	out = append(out, fmt.Sprintf("  %s     %s   %s%s",
		boldStyle.Render("showing"),
		okStyle.Bold(true).Render(" "+shown+" "),
		dimStyle.Render(fmt.Sprintf("(slot %d/%d)", slot, nSlots)), blankTag))
	out = append(out, fmt.Sprintf("  %s        %d / %d   %s",
		boldStyle.Render("step"), s.curStep, stepsPerRev,
		dimStyle.Render(fmt.Sprintf("(%.2f steps/slot)", float64(stepsPerRev)/float64(nSlots)))))
	homedTxt := errStyle.Render("NO — home first")
	if s.homed {
		homedTxt = okStyle.Render("yes")
	}
	out = append(out, fmt.Sprintf("  %s       %s", boldStyle.Render("homed"), homedTxt))
	out = append(out, fmt.Sprintf("  %s       %d RPM   %s",
		boldStyle.Render("speed"), s.rpm, dimStyle.Render(fmt.Sprintf("(/speed 1-%d)", maxRPM))))
	out = append(out, fmt.Sprintf("  %s  %d steps   %s",
		boldStyle.Render("home offset"), s.offset,
		dimStyle.Render(fmt.Sprintf("(/nudge ±n; min ±%d, backlash eats less)", minNudge))))
	out = append(out, fmt.Sprintf("  %s   '%c'   %s",
		boldStyle.Render("home glyph"), d.homeGlyph(),
		dimStyle.Render("(/sethome <g> = the flap at home; saved)")))
	out = append(out, "")

	// slot ring — benchGlyphs is the physical drum order, so highlight the
	// glyph now in the window: index (slot + homeIndex), NOT the raw slot
	// (which is slots-from-home and only matches when home glyph is blank).
	here := (slot + d.homeIndex) % nSlots
	ring := ""
	for i, g := range benchGlyphs {
		if i == here {
			ring += okStyle.Bold(true).Render(string(g))
		} else {
			ring += dimStyle.Render(string(g))
		}
	}
	out = append(out, "  "+ring, "")

	// log tail — whatever's left after the fixed rows above
	avail := m.logAvail() - len(out) - 3 // prompt + two footer lines
	if avail < 1 {
		avail = 1
	}
	tail := b.log
	if len(tail) > avail {
		tail = tail[len(tail)-avail:]
	}
	for _, line := range tail {
		out = append(out, "    "+truncLine(line, m.width-4))
	}

	prompt := "  > " + b.input + "▌"
	if s.busy {
		prompt = "  " + warnStyle.Render("… working") + dimStyle.Render("   [esc] cancel")
	}
	if !s.connected {
		prompt = "  " + dimStyle.Render("(not connected)")
	}
	footer := dimStyle.Render(fmt.Sprintf(
		"  type glyphs (A-Z 0-9, e.g. HELLO or 123123 — %gs each)   ↑ history   [esc] back",
		benchDwell.Seconds())) + "\n" + dimStyle.Render(fmt.Sprintf(
		"  /home  /homecal  /zero  /pos  /hall  /speed <1-%d>  /nudge <±n>  /sethome <g>  /reset  /help  /quit", maxRPM))
	if m.armed {
		footer = warnStyle.Render("  press ctrl+c again to quit")
	}
	return strings.Join(out, "\n") + "\n\n" + prompt + "\n" + footer + "\n"
}

func (m *appModel) benchHelpView() string {
	g := okStyle.Render
	d := dimStyle.Render
	lines := []string{
		boldStyle.Render("Drive the drum"),
		"  " + g("A") + "  " + g("7") + "  " + g("m") + "        one glyph (lower-case auto-caps)",
		"  " + g("HELLO") + "         a whole string — steps through it, " +
			fmt.Sprintf("%gs", benchDwell.Seconds()) + " per glyph",
		"  " + d("(empty)") + " / " + g("_") + "    a blank flap",
		"  " + d("↑") + "             recall previous input (history)",
		"",
		boldStyle.Render("Home & rest"),
		"  " + g("/home") + "         seek the hall magnet, then settle on blank. one slow speed.",
		"  " + g("/homecal") + "      seek but STOP on the home flap — to read + calibrate it",
		"  " + g("/zero") + "         declare 'here = home' with no seek (for a magnet-less bench)",
		"",
		boldStyle.Render("Calibrate a module (once), in order"),
		"  1. " + g("/reset") + "                offset 0, home glyph blank",
		"  2. " + g("/homecal") + "              land on the home flap and stay",
		"  3. " + g("/nudge") + " " + d("±n") + "             centre it in the window " +
			fmt.Sprintf("(min ±%d; may roll to next flap)", minNudge),
		"  4. " + g("/sethome") + " " + d("<glyph>") + "      READ the flap, declare what it physically shows",
		"  Then " + g("/home") + " rests on blank and typed glyphs land right.",
		"  " + d("nudge offset lives on the board; home glyph is saved in .bench/."),
		"",
		boldStyle.Render("Inspect"),
		"  " + g("/pos") + "          re-query position       " + g("/hall") + "   read the hall pin (0 = magnet)",
		"  " + g("/speed") + " " + d(fmt.Sprintf("<1-%d>", maxRPM)) + "  set motor RPM (not persisted; resets on reboot)",
		"",
		boldStyle.Render("Other"),
		"  " + g("/reset") + "  wipe calibration    " + g("/help") + "  this screen    " + g("/quit") + " (or " + g("q") + ")  exit",
		"",
		d("The 'showing' glyph is a MODEL (home glyph + step count), not a camera. If it"),
		d("disagrees with the real drum, the home glyph is wrong — fix with /homecal + /sethome."),
	}
	return strings.Join(lines, "\n") + "\n\n" + dimStyle.Render("  [esc] back to the bench") + "\n"
}

// --- entrypoint ----------------------------------------------------------

// runBenchCLI is `ctl bench [port] [--no-flash]`: no port = the bench menu,
// a port (or `--no-flash`) drops straight onto the board.
func runBenchCLI(args []string) error {
	port, flash, direct := "", true, false
	for _, a := range args {
		switch {
		case a == "":
		case a == "--no-flash":
			flash, direct = false, true
		case strings.HasPrefix(a, "-"):
			return fmt.Errorf("unknown bench flag %q (have: --no-flash)", a)
		default:
			port, direct = a, true
		}
	}
	return runTUI(func(m *appModel) tea.Cmd {
		if !direct {
			m.stack = append(m.stack, benchScreen())
			return nil
		}
		_, cmd := m.startBenchScreen(port, flash)
		return cmd
	})
}

// --- menu screens --------------------------------------------------------

func benchScreen() screen {
	ports := benchPorts()
	items := []menuItem{
		{label: "flash & connect", help: "copy the command loop to the board, reset, then drive it"},
		{label: "connect", help: "skip the flash — the board is already running it"},
	}
	if len(ports) == 0 {
		items[0].disabled = true
		items[1].disabled = true
		items = append(items, menuItem{label: "no USB modem attached", disabled: true})
		return screen{id: "bench-menu", title: "bench", items: items, cursor: 2}
	}
	items = append(items, menuItem{label: "pick port", help: "default: " + trimPort(ports[0])})
	return screen{id: "bench-menu", title: "bench", items: items}
}

func benchPortScreen() screen {
	ports := benchPorts()
	items := make([]menuItem, len(ports))
	for i, p := range ports {
		items[i] = menuItem{label: trimPort(p)}
	}
	return screen{id: "bench-port", title: "port", items: items, names: ports}
}
