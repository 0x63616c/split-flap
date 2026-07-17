package main

import (
	"fmt"
	"sort"
	"time"

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
)

const footerHelp = "  ↑↓ / move · esc / go back · enter / select · ctrl+c / quit"

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
}

type disarmMsg struct{ gen int }

type appModel struct {
	stack    []screen
	cat      catalog
	root     string
	width    int
	height   int
	run      *runState // non-nil while a run screen is on the stack
	quitting bool      // confirmed quit, waiting for the run to stop
	armed    bool      // first ctrl+c pressed, waiting for confirm
	gen      int       // invalidates stale disarm ticks
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
	case tea.KeyMsg:
		return m.key(msg.String())
	}
	return m, nil
}

func (m *appModel) key(key string) (tea.Model, tea.Cmd) {
	if key == "ctrl+c" {
		if m.armed {
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
	s := m.top()
	switch key {
	case "up", "k":
		for i := s.cursor - 1; i >= 0; i-- {
			if !s.items[i].disabled {
				s.cursor = i
				break
			}
		}
	case "down", "j":
		for i := s.cursor + 1; i < len(s.items); i++ {
			if !s.items[i].disabled {
				s.cursor = i
				break
			}
		}
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

// select_ handles enter on the top screen: push a submenu or start a run.
func (m *appModel) select_() (tea.Model, tea.Cmd) {
	s := m.top()
	switch s.id {
	case "root":
		if s.cursor == 0 {
			m.stack = append(m.stack, cadScreen())
		}
	case "cad":
		switch s.cursor {
		case 0:
			m.stack = append(m.stack, viewScreen())
		case 1:
			m.stack = append(m.stack, exportScreen())
		case 2:
			m.stack = append(m.stack, listScreen(m.cat))
		}
	case "view":
		switch s.cursor {
		case 0:
			m.stack = append(m.stack, pickScreen("pick-view", m.cat, false))
		case 1:
			return m.startRun("view (follow)", startView(""))
		}
	case "export":
		switch s.cursor {
		case 0:
			return m.startRun("export all", startExport(m.root, ""))
		case 1:
			m.stack = append(m.stack, pickScreen("pick-export", m.cat, true))
		}
	case "pick-view":
		return m.startRun("view "+s.names[s.cursor], startView(s.names[s.cursor]))
	case "pick-export":
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
	header := titleStyle.Render("ctl — split-flap tooling") + "\n" +
		crumbStyle.Render(m.breadcrumb()) + "\n\n"
	if m.top().id == "run" {
		return header + m.runView()
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
		line := "  " + it.label
		if it.disabled {
			line = dimStyle.Render(line)
		} else if i == s.cursor {
			line = selStyle.Render("> " + it.label)
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
	footer := dimStyle.Render(footerHelp)
	if m.armed {
		footer = warnStyle.Render("  press ctrl+c again to quit")
	}
	return out + "\n" + footer + "\n"
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
		return errStyle.Render(fmt.Sprintf("  ✗ failed: %v", r.err)) + dimStyle.Render(" · esc / back")
	case r.done:
		return okStyle.Render("  ✓ done") + dimStyle.Render(" · esc / back")
	default:
		return "  ↑↓ / scroll · esc / stop & back · ctrl+c / quit"
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

func rootScreen() screen {
	return screen{id: "root", title: "home", items: []menuItem{
		{label: "cad", help: "viewers & exports"},
		{label: "bench", help: "(coming soon)", inert: true},
	}}
}

func cadScreen() screen {
	return screen{id: "cad", title: "cad", items: []menuItem{
		{label: "view", help: "live viewer in this pane, re-renders on save"},
		{label: "export", help: "write STLs to cad/export/"},
		{label: "list models", help: "the model catalog"},
	}}
}

func viewScreen() screen {
	return screen{id: "view", title: "view", items: []menuItem{
		{label: "specific model", help: "pin one model to this pane"},
		{label: "last saved model", help: "follow whichever file you save"},
	}}
}

func exportScreen() screen {
	return screen{id: "export", title: "export", items: []menuItem{
		{label: "all printables", help: "every STL + flap 3MFs/plates"},
		{label: "one model", help: "single STL"},
	}}
}

func pickScreen(id string, cat catalog, printable bool) screen {
	var names []string
	if printable {
		names = append(names, cat.Printable...)
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
	return screen{id: id, title: "pick a model", items: items, names: names}
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

func runRootMenu() error { return runTUI(false) }
func runCadMenu() error  { return runTUI(true) }

func runTUI(startAtCad bool) error {
	root, err := repoRoot()
	if err != nil {
		return err
	}
	cat, err := loadCatalog(root)
	if err != nil {
		return err
	}
	m := &appModel{cat: cat, root: root, stack: []screen{rootScreen()}}
	if startAtCad {
		m.stack = append(m.stack, cadScreen())
	}
	_, err = tea.NewProgram(m, tea.WithAltScreen()).Run()
	return err
}
