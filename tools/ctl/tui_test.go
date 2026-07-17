package main

import "testing"

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
