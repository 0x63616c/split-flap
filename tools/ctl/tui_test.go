package main

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func TestFuzzyMatch(t *testing.T) {
	cases := []struct {
		pattern, s string
		want       bool
	}{
		{"", "drum-inner", true},
		{"drum", "drum-inner", true},
		{"din", "drum-inner", true},
		{"DIN", "drum-inner", true},
		{"nid", "drum-inner", false},
		{"flap", "holder", false},
		{"hldr", "holder", true},
		{"frap", "flap", true}, // one wrong char forgiven at 4+ runes
		{"fr", "flap", false},  // short patterns stay strict
		{"xyz", "flap", false},
	}
	for _, c := range cases {
		if got := fuzzyMatch(c.pattern, c.s); got != c.want {
			t.Errorf("fuzzyMatch(%q, %q) = %v, want %v", c.pattern, c.s, got, c.want)
		}
	}
}

func TestKillWord(t *testing.T) {
	cases := []struct{ in, want string }{
		{"drum-in", "drum-"},
		{"drum-", ""},
		{"fg", ""},
		{"", ""},
	}
	for _, c := range cases {
		if got := killWord(c.in); got != c.want {
			t.Errorf("killWord(%q) = %q, want %q", c.in, got, c.want)
		}
	}
}

func TestApplyFilter(t *testing.T) {
	names := []string{"drum-inner", "drum-outer", "flap", "holder", "unit"}
	items := make([]menuItem, len(names))
	for i, n := range names {
		items[i] = menuItem{label: n}
	}
	s := screen{items: items, names: names, canFilter: true,
		allItems: items, allNames: names, cursor: 3}

	s.query = "dru"
	s.applyFilter()
	if len(s.names) != 2 || s.names[0] != "drum-inner" || s.names[1] != "drum-outer" {
		t.Fatalf("filter 'dru': got %v", s.names)
	}
	if s.cursor != 0 {
		t.Fatalf("cursor not reset: %d", s.cursor)
	}

	s.query = "zzz"
	s.applyFilter()
	if len(s.items) != 0 {
		t.Fatalf("filter 'zzz': got %v", s.names)
	}

	s.query = ""
	s.applyFilter()
	if len(s.items) != len(names) {
		t.Fatalf("clear filter: got %v", s.names)
	}
}

func TestMultiSelectToggleAndMarked(t *testing.T) {
	s := screen{
		multi:    true,
		selected: map[string]bool{},
		names:    []string{"drum-outer", "flap"},
		allNames: []string{"drum-outer", "drum-inner-byj", "flap"},
	}
	s.toggle() // mark drum-outer
	s.cursor = 1
	s.toggle() // mark flap
	got := s.marked()
	if len(got) != 2 || got[0] != "drum-outer" || got[1] != "flap" {
		t.Fatalf("marked() = %v, want [drum-outer flap] in allNames order", got)
	}
	s.toggle() // unmark flap
	if got := s.marked(); len(got) != 1 || got[0] != "drum-outer" {
		t.Fatalf("after unmark, marked() = %v", got)
	}
	empty := screen{} // space on non-multi screens is a no-op
	empty.toggle()
}

func TestPickRenderListsExports(t *testing.T) {
	root, err := repoRoot()
	if err != nil {
		t.Skip("not in a repo")
	}
	s := pickRenderScreen(root)
	if len(findSTLs(root)) == 0 {
		if s.id != "render-empty" {
			t.Fatalf("no exports should give the empty screen, got id %q", s.id)
		}
		return
	}
	if s.id != "pick-render" {
		t.Fatalf("id %q, want pick-render", s.id)
	}
	if !s.canFilter {
		t.Fatal("render picker should be fuzzy-filterable like the other pickers")
	}
	if len(s.names) != len(s.items) || len(s.names) == 0 {
		t.Fatalf("%d names vs %d items", len(s.names), len(s.items))
	}
	for _, n := range s.names {
		if strings.HasSuffix(n, ".stl") {
			t.Fatalf("name %q should be the model name, not a filename", n)
		}
	}
}

// Picking a model from the render list must open the demo on that scene.
func TestStartDemoOpensChosenScene(t *testing.T) {
	root, err := repoRoot()
	if err != nil || len(findSTLs(root)) == 0 {
		t.Skip("no exports on disk")
	}
	m := &appModel{stack: []screen{rootScreen()}, root: root}
	want := pickRenderScreen(root).names[0]
	m.startDemo("render "+want, want)
	if m.top().id != "demo" {
		t.Fatalf("top screen is %q, want demo", m.top().id)
	}
	if got := m.cube.scene().label; got != want {
		t.Fatalf("opened on %q, want %q", got, want)
	}
}

// Keys pressed together arrive as one batched rune message; each must still
// take effect.
func TestDemoKeyHandlesBatchedRunes(t *testing.T) {
	m := &appModel{stack: []screen{rootScreen(), {id: "demo"}}, cube: newDemoModel(1, "")}
	wireWas := m.cube.scene().wire
	m.demoKey(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("wp")})
	if m.cube.scene().wire == wireWas {
		t.Fatal("w in a batched message did not toggle wireframe")
	}
	if !m.cube.paused {
		t.Fatal("p in a batched message did not pause")
	}
}

// The cube reads well as a skeleton; a mesh has thousands of edges and does
// not, so parts open shaded.
func TestSceneWireframeDefaults(t *testing.T) {
	root, err := repoRoot()
	if err != nil || len(findSTLs(root)) == 0 {
		t.Skip("no exports on disk")
	}
	d := newDemoModel(1, root)
	if !d.scenes[0].wire {
		t.Fatal("cube should open as a wireframe")
	}
	for _, s := range d.scenes[1:] {
		if s.wire {
			t.Fatalf("mesh scene %q should open shaded", s.label)
		}
	}
}

// Wireframe is per scene: toggling one part must not change another.
func TestWireframeIsPerScene(t *testing.T) {
	root, err := repoRoot()
	if err != nil || len(findSTLs(root)) == 0 {
		t.Skip("no exports on disk")
	}
	m := &appModel{stack: []screen{rootScreen(), {id: "demo"}}, cube: newDemoModel(1, root)}
	m.cube.jumpTo("unit")
	m.demoRune('w')
	if !m.cube.scenes[m.cube.idx].wire {
		t.Fatal("w did not enable wireframe on the current scene")
	}
	if m.cube.scenes[0].wire != true {
		t.Fatal("the cube's own wireframe state changed")
	}
	m.cube.next()
	if m.cube.scene().wire {
		t.Fatalf("scene %q inherited the neighbour's wireframe", m.cube.scene().label)
	}
}
