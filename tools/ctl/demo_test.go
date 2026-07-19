package main

import (
	"math"
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

func TestDemoPauseHoldsPose(t *testing.T) {
	d := newDemoModel(3, "")
	for i := 0; i < 5; i++ {
		d.step()
	}
	d.paused = true
	held := d.ang
	for i := 0; i < 50; i++ {
		d.step()
	}
	if d.ang != held {
		t.Fatalf("paused demo moved: %v -> %v", held, d.ang)
	}
	d.paused = false
	d.step()
	if d.ang == held {
		t.Fatal("unpausing did not resume the tumble")
	}
}

func TestDemoPrevWrapsBackwards(t *testing.T) {
	root, _ := repoRoot()
	d := newDemoModel(1, root)
	if len(d.scenes) < 2 {
		t.Skip("no exports on disk")
	}
	d.prev()
	if d.idx != len(d.scenes)-1 {
		t.Fatalf("prev from 0 gave idx %d, want %d", d.idx, len(d.scenes)-1)
	}
	d.next()
	if d.idx != 0 {
		t.Fatalf("next did not return to 0, got %d", d.idx)
	}
}

func TestDemoJumpTo(t *testing.T) {
	root, _ := repoRoot()
	d := newDemoModel(1, root)
	if len(d.scenes) < 2 {
		t.Skip("no exports on disk")
	}
	want := d.scenes[len(d.scenes)-1].label
	if !d.jumpTo(want) {
		t.Fatalf("jumpTo(%q) reported missing", want)
	}
	if d.scene().label != want {
		t.Fatalf("landed on %q, want %q", d.scene().label, want)
	}
	if d.jumpTo("no-such-model") {
		t.Fatal("jumpTo accepted a label that does not exist")
	}
}

// Taking hold of the model stops the tumble: otherwise the drift fights
// every keypress.
func TestOrbitPausesAndTurns(t *testing.T) {
	d := newDemoModel(1, "")
	if d.paused {
		t.Fatal("the demo should open spinning")
	}
	d.orbit(demoStep, 0, 0)
	if !d.paused {
		t.Error("orbiting did not pause the tumble")
	}
	if d.ang[0] == 0 {
		t.Error("orbiting did not turn the model")
	}
	before := d.ang
	d.step()
	if d.ang != before {
		t.Error("a held model kept drifting")
	}
}

func TestZoomClamps(t *testing.T) {
	d := newDemoModel(1, "")
	for i := 0; i < 200; i++ {
		d.zoomBy(demoZoomIn)
	}
	if d.zoom != demoZoomMax {
		t.Errorf("zoom in ran to %v, want the %v ceiling", d.zoom, demoZoomMax)
	}
	for i := 0; i < 400; i++ {
		d.zoomBy(1 / demoZoomIn)
	}
	if d.zoom != demoZoomMin {
		t.Errorf("zoom out ran to %v, want the %v floor", d.zoom, demoZoomMin)
	}
}

// Snapping to an axis holds the model still at a right angle, and the shift
// (upper case) form looks from the other side.
func TestSnapToAxis(t *testing.T) {
	d := newDemoModel(1, "")
	d.snap('y')
	if !d.paused || d.vel != [3]float64{} {
		t.Error("snap did not stop the tumble")
	}
	if d.ang != [3]float64{math.Pi / 2, 0, 0} {
		t.Errorf("snap('y') = %v", d.ang)
	}
	d.snap('X')
	if d.ang != [3]float64{0, -math.Pi / 2, 0} {
		t.Errorf("snap('X') = %v, want the far side of snap('x')", d.ang)
	}
}

func TestResetRestoresTheOpeningView(t *testing.T) {
	d := newDemoModel(1, "")
	d.orbit(1, 1, 1)
	d.zoomBy(demoZoomIn)
	d.reset()
	if d.ang != [3]float64{} || d.zoom != 1 || d.paused {
		t.Errorf("reset left ang=%v zoom=%v paused=%v", d.ang, d.zoom, d.paused)
	}
}

// fit fills the pane without spilling out of it: the worst-case default fit
// leaves most orientations small, which is the whole point of the key.
func TestFitFillsThePaneWithoutClipping(t *testing.T) {
	const w, h = 80, 30
	d := newDemoModel(1, "")
	d.snap('z') // face on: the cube's smallest silhouette, so fit has work to do
	d.fit(w, h)
	if d.zoom <= 1 {
		t.Errorf("fit did not zoom in on a face-on cube: %v", d.zoom)
	}
	lines := d.render(w, h)
	filled := 0
	for _, l := range lines {
		if strings.TrimSpace(l) != "" {
			filled++
		}
	}
	if filled < h-2 {
		t.Errorf("fitted model covers %d of %d rows", filled, h)
	}
	for _, l := range lines {
		if len([]rune(l)) > w {
			t.Fatalf("fitted model overflows the pane: %d cells", len([]rune(l)))
		}
	}
}
