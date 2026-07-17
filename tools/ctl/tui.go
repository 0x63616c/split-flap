package main

import (
	"fmt"
	"sort"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	titleStyle = lipgloss.NewStyle().Bold(true).Padding(0, 1)
	selStyle   = lipgloss.NewStyle().Reverse(true)
	dimStyle   = lipgloss.NewStyle().Faint(true)
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
// Returns "" when the user backs out.
func pickModel(root string, printable bool) (string, error) {
	cat, err := loadCatalog(root)
	if err != nil {
		return "", err
	}
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
	i, err := pick("pick a model", items)
	if err != nil || i == -1 {
		return "", err
	}
	return names[i], nil
}
