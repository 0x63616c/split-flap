package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
	"unicode"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle = lipgloss.NewStyle().Bold(true).Padding(0, 1)
	selStyle   = lipgloss.NewStyle().Reverse(true)
	dimStyle   = lipgloss.NewStyle().Faint(true)
	warnStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("3"))
	okStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("2"))
	errStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("1"))
	crumbStyle = lipgloss.NewStyle().Italic(true).Faint(true).Padding(0, 1)
	boldStyle  = lipgloss.NewStyle().Bold(true)
)

const footerHelp = "  [↑↓] move · [esc] go back · [enter] select · [h] help · [ctrl+c] quit"

type menuItem struct {
	label    string
	help     string // dim text shown right of the label
	disabled bool   // unselectable (cursor skips it)
	inert    bool   // selectable but enter does nothing (coming-soon items)
}

// screen is one level of the menu stack. id "run" renders the active
// runState's log instead of items.
type screen struct {
	id     string // routes enter-key handling
	title  string
	items  []menuItem
	names  []string // pick-* screens: model name per item
	cursor int

	// `/` fuzzy filter (pick-* screens): items/names hold the filtered view,
	// allItems/allNames the full set.
	canFilter bool
	filtering bool
	query     string
	allItems  []menuItem
	allNames  []string

	// multi-select (pick-export): space marks rows, enter exports the
	// marked set (or just the cursor row when nothing is marked).
	// Keyed by name so marks survive filtering.
	multi    bool
	selected map[string]bool
}

// toggle flips the mark on the cursor row of a multi screen.
func (s *screen) toggle() {
	if !s.multi || len(s.names) == 0 {
		return
	}
	n := s.names[s.cursor]
	if s.selected[n] {
		delete(s.selected, n)
	} else {
		s.selected[n] = true
	}
}

// marked returns the marked names in list order (the full, unfiltered order).
func (s *screen) marked() []string {
	var out []string
	for _, n := range s.allNames {
		if s.selected[n] {
			out = append(out, n)
		}
	}
	return out
}

// fuzzyMatch reports whether pattern is a case-insensitive subsequence of s.
// Patterns of 4+ runes tolerate one wrong character ("frap" matches "flap").
func fuzzyMatch(pattern, s string) bool {
	p := []rune(strings.ToLower(pattern))
	if subseq(p, s) {
		return true
	}
	if len(p) < 4 {
		return false
	}
	for i := range p {
		dropped := append(append([]rune{}, p[:i]...), p[i+1:]...)
		if subseq(dropped, s) {
			return true
		}
	}
	return false
}

func subseq(p []rune, s string) bool {
	if len(p) == 0 {
		return true
	}
	i := 0
	for _, r := range strings.ToLower(s) {
		if r == p[i] {
			i++
			if i == len(p) {
				return true
			}
		}
	}
	return false
}

// killWord chops the trailing word off the query (option/alt+delete, ctrl+w).
func killWord(q string) string {
	rs := []rune(q)
	i := len(rs)
	for i > 0 && !isWordRune(rs[i-1]) {
		i--
	}
	for i > 0 && isWordRune(rs[i-1]) {
		i--
	}
	return string(rs[:i])
}

func isWordRune(r rune) bool { return unicode.IsLetter(r) || unicode.IsDigit(r) }

// applyFilter rebuilds the visible items from the query and resets the cursor.
func (s *screen) applyFilter() {
	s.items = s.items[:0:0]
	s.names = s.names[:0:0]
	for i, n := range s.allNames {
		if fuzzyMatch(s.query, n) {
			s.items = append(s.items, s.allItems[i])
			s.names = append(s.names, n)
		}
	}
	s.cursor = 0
}

type disarmMsg struct{ gen int }

type appModel struct {
	stack    []screen
	cat      catalog
	root     string
	width    int
	height   int
	run      *runState   // non-nil while a run screen is on the stack
	quitting bool        // confirmed quit, waiting for the run to stop
	armed    bool        // first ctrl+c pressed, waiting for confirm
	gen      int         // invalidates stale disarm ticks
	cube     *demoModel  // non-nil while the demo screen is on the stack
	bench    *benchModel // non-nil while the bench screen is on the stack
	credits  *creditsModel
}

func (m *appModel) top() *screen { return &m.stack[len(m.stack)-1] }

func (m *appModel) Init() tea.Cmd { return nil }

func (m *appModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		return m, nil
	case disarmMsg:
		if msg.gen == m.gen {
			m.armed = false
		}
		return m, nil
	case logMsg:
		if m.run == nil {
			return m, nil
		}
		m.run.lines = append(m.run.lines, msg.line)
		if len(m.run.lines) > maxLogLines {
			m.run.lines = m.run.lines[len(m.run.lines)-maxLogLines:]
		}
		return m, listenRun(m.run.ch)
	case runDoneMsg:
		if m.run == nil {
			return m, nil
		}
		m.run.done = true
		m.run.err = msg.err
		if m.quitting {
			return m, tea.Quit
		}
		if m.run.stopping {
			m.popRun()
		}
		return m, nil
	case benchLogMsg:
		if m.bench == nil {
			return m, nil
		}
		m.bench.logf("%s", msg.line)
		return m, listenBench(m.bench.w.msgs)
	case benchSnapMsg:
		if m.bench == nil {
			return m, nil
		}
		m.bench.snap = benchSnapshot(msg)
		return m, listenBench(m.bench.w.msgs)
	case benchDoneMsg:
		if m.bench == nil {
			return m, nil
		}
		m.bench.snap.connected = false
		m.bench.snap.busy = false
		return m, nil
	case cubeFrameMsg:
		if m.cube == nil || m.top().id != "demo" {
			return m, nil // left the demo — let the frame loop die
		}
		m.cube.step()
		return m, cubeTick()
	case creditsFrameMsg:
		if m.credits == nil || m.top().id != "credits" {
			return m, nil // left the crawl — let the frame loop die
		}
		m.credits.step()
		return m, creditsTick()
	case tea.KeyMsg:
		return m.key(msg)
	}
	return m, nil
}

// cursorMove steps the cursor to the previous/next enabled item, wrapping
// around the ends of the list.
func (m *appModel) cursorMove(s *screen, up bool) {
	n := len(s.items)
	if n == 0 {
		return
	}
	step := 1
	if up {
		step = -1
	}
	for i := 1; i <= n; i++ {
		j := ((s.cursor+step*i)%n + n) % n
		if !s.items[j].disabled {
			s.cursor = j
			return
		}
	}
}

func (m *appModel) key(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	key := msg.String()
	if key == "ctrl+c" {
		if m.armed {
			if m.bench != nil {
				m.bench.w.stop()
			}
			if m.run != nil && !m.run.done {
				m.run.stop()
				m.quitting = true
				return m, nil // quit once runDoneMsg lands
			}
			return m, tea.Quit
		}
		m.armed = true
		m.gen++
		gen := m.gen
		return m, tea.Tick(5*time.Second, func(time.Time) tea.Msg { return disarmMsg{gen} })
	}
	m.armed = false // any other key clears the confirm prompt
	if m.top().id == "run" {
		return m.runKey(key)
	}
	if m.top().id == "demo" {
		return m.demoKey(msg)
	}
	if m.top().id == "bench" {
		return m.benchKey(msg)
	}
	if m.top().id == "credits" {
		return m.creditsKey(msg)
	}
	s := m.top()
	if s.filtering {
		return m.filterKey(msg)
	}
	if s.canFilter && msg.Type == tea.KeyRunes && msg.Runes[0] == '/' {
		s.filtering = true
		s.query = string(msg.Runes[1:]) // batched input: "/dru" pasted at once
		s.applyFilter()
		return m, nil
	}
	if key == "h" {
		if s.id == "help" {
			m.stack = m.stack[:len(m.stack)-1]
		} else {
			m.stack = append(m.stack, helpScreen())
		}
		return m, nil
	}
	switch key {
	case "up", "k":
		m.cursorMove(s, true)
	case "down", "j":
		m.cursorMove(s, false)
	case " ":
		s.toggle()
	case "esc":
		if len(m.stack) > 1 {
			m.stack = m.stack[:len(m.stack)-1]
		}
	case "enter":
		if s.items[s.cursor].disabled || s.items[s.cursor].inert {
			return m, nil
		}
		return m.select_()
	}
	return m, nil
}

// filterKey handles keys while the top screen's `/` filter is active:
// printable keys type, arrows move, enter selects, esc clears.
func (m *appModel) filterKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	s := m.top()
	if s.multi && msg.String() == " " { // model names never contain spaces
		s.toggle()
		return m, nil
	}
	if msg.Type == tea.KeyRunes { // typed text (possibly batched runes)
		s.query += string(msg.Runes)
		s.applyFilter()
		return m, nil
	}
	switch msg.String() {
	case "esc":
		s.filtering = false
		s.query = ""
		s.applyFilter()
	case "backspace":
		if s.query == "" {
			s.filtering = false
			return m, nil
		}
		rs := []rune(s.query)
		s.query = string(rs[:len(rs)-1])
		s.applyFilter()
	case "alt+backspace", "ctrl+w":
		s.query = killWord(s.query)
		s.applyFilter()
	case "enter":
		if len(s.items) == 0 {
			return m, nil
		}
		return m.select_()
	case "up":
		m.cursorMove(s, true)
	case "down":
		m.cursorMove(s, false)
	}
	return m, nil
}

// startDemo pushes the spinning-model screen, opening on scene `label`
// ("" = the cube). Either way the ←→ keys still walk the whole scene list.
func (m *appModel) startDemo(title, label string) (tea.Model, tea.Cmd) {
	m.cube = newDemoModel(time.Now().UnixNano(), m.root)
	if label != "" {
		m.cube.jumpTo(label)
	}
	m.stack = append(m.stack, screen{id: "demo", title: title})
	return m, cubeTick()
}

// demoKey handles keys while the demo screen is on top: w toggles the
// wireframe overlay, esc drops back to the menu and stops the frame loop.
func (m *appModel) demoKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// Runes arrive batched when keys land in the same read, so "wp" is one
	// message, not two. Apply each in turn rather than matching the whole.
	if msg.Type == tea.KeyRunes {
		for _, r := range msg.Runes {
			m.demoRune(r)
		}
		return m, nil
	}
	switch msg.String() {
	case "right":
		m.cube.next()
	case "left":
		m.cube.prev()
	case "esc":
		m.stack = m.stack[:len(m.stack)-1]
		m.cube = nil
	}
	return m, nil
}

func (m *appModel) demoRune(r rune) {
	switch r {
	case 'w':
		s := m.cube.scene()
		s.wire = !s.wire
	case 'p':
		m.cube.paused = !m.cube.paused
	case 'l':
		m.cube.next()
	case 'h':
		m.cube.prev()
	}
}

// startCredits pushes the crawl and starts its frame loop.
func (m *appModel) startCredits() (tea.Model, tea.Cmd) {
	m.credits = newCreditsModel()
	m.stack = append(m.stack, screen{id: "credits", title: "credits"})
	return m, creditsTick()
}

// creditsKey handles keys while the crawl is on top: p pauses, r rewinds,
// esc drops back to the menu and stops the frame loop.
func (m *appModel) creditsKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	switch msg.String() {
	case "p", " ":
		m.credits.paused = !m.credits.paused
	case "r":
		m.credits.t = 0
	case "esc":
		m.stack = m.stack[:len(m.stack)-1]
		m.credits = nil
	}
	return m, nil
}

// runKey handles keys while the run screen is on top.
func (m *appModel) runKey(key string) (tea.Model, tea.Cmd) {
	r := m.run
	switch key {
	case "esc":
		if r.done {
			m.popRun()
		} else if !r.stopping {
			r.stopping = true
			r.stop()
		}
	case "up", "k":
		if r.scroll < len(r.lines)-m.logAvail() {
			r.scroll++
		}
	case "down", "j":
		if r.scroll > 0 {
			r.scroll--
		}
	}
	return m, nil
}

func (m *appModel) popRun() {
	m.stack = m.stack[:len(m.stack)-1]
	m.run = nil
}

// startRun pushes the run screen and starts pumping its messages.
func (m *appModel) startRun(title string, r *runState) (tea.Model, tea.Cmd) {
	m.run = r
	m.stack = append(m.stack, screen{id: "run", title: title})
	return m, listenRun(r.ch)
}

// catalog re-reads the model catalog so a catalog.py edit shows up without a
// restart. A failed reload keeps the last good copy — a broken catalog.py
// shouldn't empty the menus.
func (m *appModel) catalog() catalog {
	if cat, err := loadCatalog(m.root); err == nil {
		m.cat = cat
	}
	return m.cat
}

// select_ handles enter on the top screen: push a submenu or start a run.
func (m *appModel) select_() (tea.Model, tea.Cmd) {
	s := m.top()
	switch s.id {
	case "root":
		switch s.cursor {
		case 0:
			m.stack = append(m.stack, cadScreen())
		case 1:
			m.stack = append(m.stack, benchScreen())
		case 2:
			return m.startDemo("demo", "")
		case 3:
			return m.startCredits()
		}
	case "cad":
		switch s.cursor {
		case 0:
			m.stack = append(m.stack, viewScreen())
		case 1:
			m.stack = append(m.stack, pickScreen("pick-export", m.catalog(), true))
		case 2:
			m.stack = append(m.stack, pickRenderScreen(m.root))
		case 3:
			m.stack = append(m.stack, listScreen(m.catalog()))
		case 4:
			return m.startRun("golden test", startGoldenTest(m.root))
		}
	case "bench-menu":
		switch s.cursor {
		case 0:
			return m.startBenchScreen("", true)
		case 1:
			return m.startBenchScreen("", false)
		case 2:
			m.stack = append(m.stack, benchPortScreen())
		}
	case "bench-port":
		return m.startBenchScreen(s.names[s.cursor], true)
	case "pick-render":
		return m.startDemo("render "+s.names[s.cursor], s.names[s.cursor])
	case "view":
		switch s.cursor {
		case 0:
			m.stack = append(m.stack, pickScreen("pick-view", m.catalog(), false))
		case 1:
			return m.startRun("view (follow)", startView(""))
		}
	case "pick-view":
		return m.startRun("view "+s.names[s.cursor], startView(s.names[s.cursor]))
	case "pick-export":
		if marked := s.marked(); len(marked) > 0 {
			title := fmt.Sprintf("export %d models", len(marked))
			if len(marked) == 1 {
				title = "export " + marked[0]
			}
			return m.startRun(title, startExport(m.root, marked...))
		}
		return m.startRun("export "+s.names[s.cursor], startExport(m.root, s.names[s.cursor]))
	}
	return m, nil
}

func (m *appModel) breadcrumb() string {
	out := ""
	for i, s := range m.stack {
		if i > 0 {
			out += " › "
		}
		out += s.title
	}
	return out
}

func (m *appModel) View() string {
	crumb := m.breadcrumb()
	if m.top().id == "help" {
		crumb = "help"
	}
	header := titleStyle.Render("ctl — split-flap tooling") + "\n" +
		crumbStyle.Render(crumb) + "\n\n"
	if m.top().id == "run" {
		return header + m.runView()
	}
	if m.top().id == "demo" {
		return header + m.demoView()
	}
	if m.top().id == "bench" {
		return header + m.benchView()
	}
	if m.top().id == "credits" {
		return header + m.creditsView()
	}
	s := m.top()
	out := header
	maxw := 0
	for _, it := range s.items {
		if it.help != "" && len([]rune(it.label)) > maxw {
			maxw = len([]rune(it.label))
		}
	}
	for i, it := range s.items {
		label := it.label
		marked := false
		if s.multi {
			mark := "[ ] "
			if s.selected[s.names[i]] {
				mark, marked = "[x] ", true
			}
			label = mark + label
		}
		line := "  " + label
		switch {
		case it.disabled:
			line = dimStyle.Render(line)
		case i == s.cursor && marked:
			line = okStyle.Reverse(true).Render("> " + label)
		case i == s.cursor:
			line = selStyle.Render("> " + label)
		case marked:
			line = okStyle.Render(line)
		}
		if it.help != "" {
			pad := maxw - len([]rune(it.label)) + 3
			for j := 0; j < pad; j++ {
				line += " "
			}
			line += dimStyle.Render(it.help)
		}
		out += line + "\n"
	}
	if s.filtering && len(s.items) == 0 {
		out += dimStyle.Render("  (no matches)") + "\n"
	}
	help := footerHelp
	if s.canFilter {
		help = "  [↑↓] move · [/] filter · [esc] go back · [enter] select · [ctrl+c] quit"
	}
	if s.multi {
		help = "  [↑↓] move · [space] mark · [/] filter · [enter] export marked (or row) · [esc] back"
	}
	if s.id == "help" {
		help = "  [esc] go back · [ctrl+c] quit"
	}
	if s.filtering {
		out += "\n  /" + s.query + "▌" +
			dimStyle.Render(fmt.Sprintf("   %d/%d", len(s.items), len(s.allItems)))
		help = "  type to filter · [↑↓] move · [enter] select · [esc] clear"
		if s.multi {
			help = "  type to filter · [↑↓] move · [space] mark · [enter] export · [esc] clear"
		}
	}
	footer := dimStyle.Render(help)
	if m.armed {
		footer = warnStyle.Render("  press ctrl+c again to quit")
	}
	return out + "\n" + footer + "\n"
}

type creditsFrameMsg struct{}

func creditsTick() tea.Cmd {
	return tea.Tick(time.Second/creditsFPS, func(time.Time) tea.Msg { return creditsFrameMsg{} })
}

// creditsView renders the crawl in the same slot the demo uses.
func (m *appModel) creditsView() string {
	w, h := m.width, m.demoAvail()
	if w == 0 {
		w = 80
	}
	out := ""
	for _, line := range m.credits.render(w, h) {
		out += line + "\n"
	}
	roll := "rolling"
	if m.credits.paused {
		roll = warnStyle.Render("paused")
	}
	return out + "\n  " + dimStyle.Render("[p] ") + roll +
		dimStyle.Render(" · [r] rewind · [esc] back")
}

type cubeFrameMsg struct{}

func cubeTick() tea.Cmd {
	return tea.Tick(time.Second/cubeFPS, func(time.Time) tea.Msg { return cubeFrameMsg{} })
}

// demoView renders the tumbling cube centred between the header and footer.
func (m *appModel) demoView() string {
	w, h := m.width, m.demoAvail()
	if w == 0 {
		w = 80
	}
	out := ""
	for _, line := range m.cube.render(w, h) {
		out += line + "\n"
	}
	wire := "off"
	if m.cube.scene().wire {
		wire = "on"
	}
	spin := "spinning"
	if m.cube.paused {
		spin = warnStyle.Render("paused")
	}
	s := m.cube.scene()
	name := okStyle.Render(s.label)
	if len(m.cube.scenes) > 1 {
		name += dimStyle.Render(fmt.Sprintf(" (%d/%d)", m.cube.idx+1, len(m.cube.scenes)))
	}
	return out + "\n  " + name + dimStyle.Render("  ·  [←→] model · [w] wireframe: "+wire+" · [p] ") +
		spin + dimStyle.Render(" · [esc] back")
}

// demoAvail is how many rows the model gets: everything between the header
// and a footer pinned to the last row. header(3) + model + gap(1) + footer(1)
// fills the terminal exactly, so the model takes all the space going.
func (m *appModel) demoAvail() int {
	height := m.height
	if height == 0 {
		height = 24
	}
	return max(height-5, 1)
}

// logAvail is how many log lines fit between the header and the footer.
func (m *appModel) logAvail() int {
	height := m.height
	if height == 0 {
		height = 24
	}
	avail := height - 6 // header(1) crumb(1) blank(1) blank(1) footer(1) slack(1)
	if avail < 1 {
		avail = 1
	}
	return avail
}

// runView renders the log tail of the active run under the shared header.
func (m *appModel) runView() string {
	r := m.run
	avail := m.logAvail()
	if r.scroll > len(r.lines)-avail {
		r.scroll = max(0, len(r.lines)-avail)
	}
	end := len(r.lines) - r.scroll
	start := max(0, end-avail)
	out := ""
	for _, line := range r.lines[start:end] {
		out += truncLine(line, m.width) + "\n"
	}
	for i := end - start; i < avail; i++ {
		out += "\n"
	}
	return out + "\n" + dimStyle.Render(m.runFooter()) + "\n"
}

func (m *appModel) runFooter() string {
	r := m.run
	switch {
	case m.armed:
		return warnStyle.Render("  press ctrl+c again to quit")
	case m.quitting:
		return warnStyle.Render("  shutting down…")
	case r.stopping && !r.done:
		return warnStyle.Render("  stopping…")
	case r.done && r.err != nil:
		return errStyle.Render(fmt.Sprintf("  ✗ failed: %v", r.err)) + dimStyle.Render(" · [esc] back")
	case r.done:
		return okStyle.Render("  ✓ done") + dimStyle.Render(" · [esc] back")
	default:
		return "  [↑↓] scroll · [esc] stop & back · [ctrl+c] quit"
	}
}

// truncLine clips a log line to the terminal width (0 = unknown, no clip).
func truncLine(s string, width int) string {
	if width <= 0 {
		return s
	}
	rs := []rune(s)
	if len(rs) <= width {
		return s
	}
	return string(rs[:width-1]) + "…"
}

// --- screens -----------------------------------------------------------

func helpScreen() screen {
	row := func(key, what string) menuItem {
		return menuItem{label: fmt.Sprintf("%-24s %s", key, what), disabled: true}
	}
	return screen{id: "help", title: "help", items: []menuItem{
		row("↑↓ / j k", "move · scroll a run log"),
		row("enter", "select"),
		row("esc", "back · stop a run · clear the filter"),
		row("/", "fuzzy filter on pick-a-model screens"),
		row("space", "mark rows on the export picker; enter exports the set"),
		row("  opt+delete / ctrl+w", "delete a word from the filter"),
		row("h", "this help (h or esc closes)"),
		row("ctrl+c", "quit — a running job is shut down first"),
		{label: "", disabled: true},
		row("runs", "export/view stream their logs right here;"),
		row("", "view keeps re-rendering on every .py save"),
	}}
}

func rootScreen() screen {
	return screen{id: "root", title: "home", items: []menuItem{
		{label: "cad", help: "viewers & exports"},
		{label: "bench", help: "drive the breadboard module over serial"},
		{label: "demo", help: "a cube, tumbling, for no reason at all"},
		{label: "credits", help: "a long time ago, on a breadboard far, far away"},
	}}
}

func cadScreen() screen {
	return screen{id: "cad", title: "cad", items: []menuItem{
		{label: "view", help: "live viewer in this pane, re-renders on save"},
		{label: "export", help: "write STLs to cad/export/"},
		{label: "render", help: "spin an exported part in ASCII, right here"},
		{label: "list models", help: "the model catalog"},
		{label: "golden test", help: "pytest -m slow — XOR every model against cad/tests/golden/"},
	}}
}

func viewScreen() screen {
	return screen{id: "view", title: "view", items: []menuItem{
		{label: "specific model", help: "pin one model to this pane"},
		{label: "last saved model", help: "follow whichever file you save"},
	}}
}

func pickScreen(id string, cat catalog, printable bool) screen {
	var names []string
	if printable {
		names = append(names, cat.Printable...)
		names = append(names, "flaps") // glyph artwork: 3MFs + plates
	} else {
		for n := range cat.Models {
			names = append(names, n)
		}
	}
	sort.Strings(names)
	items := make([]menuItem, len(names))
	for i, n := range names {
		label := n
		if !printable {
			label = fmt.Sprintf("%-12s %s", n, cat.Models[n])
		}
		items[i] = menuItem{label: label}
	}
	s := screen{id: id, title: "pick a model", items: items, names: names,
		canFilter: true, allItems: items, allNames: names}
	if printable { // export picker: space marks rows, enter runs the set
		s.multi = true
		s.selected = map[string]bool{}
		s.title = "pick a model(s)"
	}
	return s
}

// pickRenderScreen lists what can actually be drawn: the STLs on disk, not
// the catalog, since a model with no export has no geometry to render.
func pickRenderScreen(root string) screen {
	paths := findSTLs(root)
	if len(paths) == 0 {
		return screen{id: "render-empty", title: "render", items: []menuItem{
			{label: "no exports found", disabled: true},
			{label: "run: just cad export", disabled: true},
		}}
	}
	names := make([]string, len(paths))
	for i, p := range paths {
		names[i] = stlName(p)
	}
	sort.Strings(names)
	items := make([]menuItem, len(names))
	for i, n := range names {
		items[i] = menuItem{label: n}
	}
	return screen{id: "pick-render", title: "render", items: items, names: names,
		canFilter: true, allItems: items, allNames: names}
}

func listScreen(cat catalog) screen {
	var names []string
	for n := range cat.Models {
		names = append(names, n)
	}
	sort.Strings(names)
	items := []menuItem{{label: "models:", disabled: true}}
	for _, n := range names {
		items = append(items, menuItem{label: fmt.Sprintf("  %-12s %s", n, cat.Models[n]), disabled: true})
	}
	items = append(items, menuItem{label: "printable:", disabled: true})
	for _, n := range cat.Printable {
		items = append(items, menuItem{label: "  " + n, disabled: true})
	}
	return screen{id: "list", title: "models", items: items}
}

// --- entrypoints -------------------------------------------------------

func runRootMenu() error { return runTUI(nil) }
func runCadMenu() error {
	return runTUI(func(m *appModel) tea.Cmd { m.stack = append(m.stack, cadScreen()); return nil })
}

// runTUI boots the menu. open, if given, pushes a deeper starting screen (and
// may return a command to kick it off) so `ctl cad` / `ctl bench` land where
// you asked rather than at the root.
func runTUI(open func(*appModel) tea.Cmd) error {
	root, err := repoRoot()
	if err != nil {
		return err
	}
	cat, err := loadCatalog(root)
	if err != nil {
		return err
	}
	m := &appModel{cat: cat, root: root, stack: []screen{rootScreen()}}
	var cmd tea.Cmd
	if open != nil {
		cmd = open(m)
	}
	p := tea.NewProgram(m, tea.WithAltScreen())
	if cmd != nil {
		go func() { p.Send(cmd()) }()
	}
	_, err = p.Run()
	return err
}
