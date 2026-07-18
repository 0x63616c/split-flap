package main

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestDemoScenesListCubeThenUnitFirst(t *testing.T) {
	root, err := repoRoot()
	if err != nil {
		t.Skip("not in a repo")
	}
	d := newDemoModel(1, root)
	if len(d.scenes) < 2 {
		t.Skip("no exports on disk — run: just cad export")
	}
	if d.scenes[0].label != "cube" {
		t.Fatalf("scene 0 is %q, want the cube", d.scenes[0].label)
	}
	if d.scenes[1].label != "unit" {
		t.Fatalf("scene 1 is %q, want unit promoted to the front", d.scenes[1].label)
	}
}

func TestDemoNextWrapsAndRenders(t *testing.T) {
	root, _ := repoRoot()
	d := newDemoModel(1, root)
	seen := map[string]bool{}
	for i := 0; i < len(d.scenes); i++ {
		lines := d.render(70, 25)
		if len(lines) != 25 {
			t.Fatalf("scene %q gave %d rows, want 25", d.scene().label, len(lines))
		}
		if nonBlank(lines) == 0 {
			t.Fatalf("scene %q drew nothing", d.scene().label)
		}
		seen[d.scene().label] = true
		d.next()
	}
	if d.idx != 0 {
		t.Fatalf("next() did not wrap: idx %d", d.idx)
	}
	if len(seen) != len(d.scenes) {
		t.Fatalf("visited %d distinct scenes, want %d", len(seen), len(d.scenes))
	}
}

// A missing STL must not blank the screen or panic — the demo keeps its
// shape and says what went wrong.
func TestDemoRendersLoadFailure(t *testing.T) {
	d := &demoModel{scenes: []demoScene{{label: "gone", path: filepath.Join(t.TempDir(), "nope.stl")}}}
	lines := d.render(60, 21)
	if len(lines) != 21 {
		t.Fatalf("got %d rows, want 21", len(lines))
	}
	if !strings.Contains(strings.Join(lines, "\n"), "cannot read") {
		t.Fatalf("no error shown: %q", lines)
	}
}
