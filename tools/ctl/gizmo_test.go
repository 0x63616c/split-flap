package main

import (
	"math"
	"strings"
	"testing"
)

// All three axes are labelled at every orientation, including the ones where
// an axis points straight at the camera and collapses onto the origin.
func TestGizmoAlwaysLabelsEveryAxis(t *testing.T) {
	for _, ang := range [][3]float64{
		{}, {0, math.Pi / 2, 0}, {math.Pi / 2, 0, 0}, {0.6, 0.4, 0.2}, {math.Pi, math.Pi, math.Pi},
	} {
		flat := strings.ToLower(gizmoString(gizmo(ang)))
		for _, axis := range "xyz" {
			if !strings.ContainsRune(flat, axis) {
				t.Errorf("ang %v: no %c label in\n%s", ang, axis, gizmoString(gizmo(ang)))
			}
		}
	}
}

// An axis pointing towards the camera is upper-cased, so you can tell which
// end of it you are looking down.
func TestGizmoMarksAxesFacingTheCamera(t *testing.T) {
	// The camera looks along +z, so at rest +z points away: lower case.
	if got := gizmoString(gizmo([3]float64{})); !strings.Contains(got, "z") || strings.Contains(got, "Z") {
		t.Errorf("+z away from the camera should be lower case:\n%s", got)
	}
	// Turned half around, the same axis points at the camera.
	if got := gizmoString(gizmo([3]float64{0, math.Pi, 0})); !strings.Contains(got, "Z") {
		t.Errorf("+z towards the camera should be upper case:\n%s", got)
	}
}

func gizmoString(g [][]rune) string {
	rows := make([]string, len(g))
	for i, r := range g {
		rows[i] = string(r)
	}
	return strings.Join(rows, "\n")
}

// The triad lands in the bottom-left of the frame and leaves the rest alone.
func TestOverlayGizmoBlitsIntoTheCorner(t *testing.T) {
	const w, h = 60, 20
	lines := make([]string, h)
	for i := range lines {
		lines[i] = strings.Repeat("#", w)
	}
	out := overlayGizmo(lines, [3]float64{0.6, 0.4, 0.2}, w)

	top := h - gizmoH - gizmoPad
	for y, line := range out {
		box := y >= top && y < top+gizmoH
		if !box && line != strings.Repeat("#", w) {
			t.Fatalf("row %d outside the box was touched: %q", y, line)
		}
		if box && strings.HasPrefix(line[gizmoPad:], strings.Repeat("#", gizmoW)) {
			t.Fatalf("row %d inside the box was not cleared: %q", y, line)
		}
	}
}

// Too small a pane keeps the model rather than the decoration.
func TestOverlayGizmoSkipsTinyPanes(t *testing.T) {
	lines := []string{"##", "##"}
	if got := overlayGizmo(lines, [3]float64{}, 2); got[0] != "##" || got[1] != "##" {
		t.Errorf("tiny pane was overwritten: %q", got)
	}
}
