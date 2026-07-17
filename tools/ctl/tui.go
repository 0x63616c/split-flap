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
)

const footerHelp = "  ↑↓ / move · esc / go back · enter / select · ctrl+c / quit"

// action is what the TUI resolves to; executed after the program exits the
// alt screen (so view/export output lands in the normal terminal).
type action struct {
	kind  string // "view" | "export" | "" (plain quit)
	model string // "" = view follow-mode / export all
}

type menuItem struct {
	label    string
	disabled bool
}

// screen is one level of the menu stack.
type screen struct {
	id     string // routes enter-key handling
	title  string
	items  []menuItem
	names  []string // pick-* screens: model name per item
	cursor int
}

type disarmMsg struct{ gen int }

type appModel struct {
	stack  []screen
	cat    catalog
	armed  bool // first ctrl+c pressed, waiting for confirm
	gen    int  // invalidates stale disarm ticks
	result action
}

func (m *appModel) top() *screen { return &m.stack[len(m.stack)-1] }

func (m *appModel) Init() tea.Cmd { return nil }

func (m *appModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case disarmMsg:
		if msg.gen == m.gen {
			m.armed = false
		}
		return m, nil
	case tea.KeyMsg:
		key := msg.String()
		if key == "ctrl+c" {
			if m.armed {
				m.result = action{}
				return m, tea.Quit
			}
			m.armed = true
			m.gen++
			gen := m.gen
			return m, tea.Tick(5*time.Second, func(time.Time) tea.Msg { return disarmMsg{gen} })
		}
		m.armed = false // any other key clears the confirm prompt
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
			if s.items[s.cursor].disabled {
				return m, nil
			}
			return m.select_()
		}
	}
	return m, nil
}

// select_ handles enter on the top screen: push a submenu or resolve an action.
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
			m.result = action{kind: "view"}
			return m, tea.Quit
		}
	case "export":
		switch s.cursor {
		case 0:
			m.result = action{kind: "export"}
			return m, tea.Quit
		case 1:
			m.stack = append(m.stack, pickScreen("pick-export", m.cat, true))
		}
	case "pick-view":
		m.result = action{kind: "view", model: s.names[s.cursor]}
		return m, tea.Quit
	case "pick-export":
		m.result = action{kind: "export", model: s.names[s.cursor]}
		return m, tea.Quit
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
	s := m.top()
	out := titleStyle.Render(m.breadcrumb()) + "\n\n"
	for i, it := range s.items {
		line := "  " + it.label
		if it.disabled {
			line = dimStyle.Render(line)
		} else if i == s.cursor {
			line = selStyle.Render("> " + it.label)
		}
		out += line + "\n"
	}
	footer := dimStyle.Render(footerHelp)
	if m.armed {
		footer = warnStyle.Render("  press ctrl+c again to quit")
	}
	return out + "\n" + footer + "\n"
}

// --- screens -----------------------------------------------------------

func rootScreen() screen {
	return screen{id: "root", title: "ctl", items: []menuItem{
		{label: "cad — viewers & exports"},
		{label: "bench (coming soon)", disabled: true},
	}}
}

func cadScreen() screen {
	return screen{id: "cad", title: "cad", items: []menuItem{
		{label: "view"},
		{label: "export"},
		{label: "list models"},
	}}
}

func viewScreen() screen {
	return screen{id: "view", title: "view", items: []menuItem{
		{label: "specific model"},
		{label: "last saved model"},
	}}
}

func exportScreen() screen {
	return screen{id: "export", title: "export", items: []menuItem{
		{label: "all printables"},
		{label: "one model"},
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
	m := &appModel{cat: cat, stack: []screen{rootScreen()}}
	if startAtCad {
		m.stack = append(m.stack, cadScreen())
	}
	res, err := tea.NewProgram(m, tea.WithAltScreen()).Run()
	if err != nil {
		return err
	}
	a := res.(*appModel).result
	switch a.kind {
	case "view":
		return runView(a.model)
	case "export":
		args := []string{"export"}
		if a.model != "" {
			args = append(args, a.model)
		}
		return runCad(args)
	}
	return nil
}
