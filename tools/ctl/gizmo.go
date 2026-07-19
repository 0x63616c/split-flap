package main

import (
	"math"
	"strings"
)

// A corner triad showing which way the model's X/Y/Z point at the current
// orientation. Drawn flat (no perspective): at this size the foreshortening
// of a real projection is a sub-cell effect, and orthographic keeps the arms
// the same length whichever way they face, which is what makes it readable.

const (
	gizmoW   = 13
	gizmoH   = 7
	gizmoPad = 1
)

var gizmoAxes = [3]struct {
	dir   [3]float64
	label rune
}{
	{[3]float64{1, 0, 0}, 'x'},
	{[3]float64{0, 1, 0}, 'y'},
	{[3]float64{0, 0, 1}, 'z'},
}

// gizmo draws the triad into its own small grid of runes.
func gizmo(ang [3]float64) [][]rune {
	g := make([][]rune, gizmoH)
	for y := range g {
		g[y] = []rune(strings.Repeat(" ", gizmoW))
	}
	cx, cy := gizmoW/2, gizmoH/2
	gizmoSet(g, cx, cy, '+') // origin, drawn first so a head-on axis's label wins it
	// Arms reach to the edge of the box; the x radius is halved again by
	// cubeCellW, since a cell is about twice as tall as it is wide.
	rx, ry := float64(cx-1), float64(cy)

	// Arms first, labels after: an arm crossing another axis's tip would
	// otherwise rub out its label and leave the triad unreadable.
	var tip [3][2]int
	for i, a := range gizmoAxes {
		v := rot(a.dir, ang)
		ex, ey := float64(cx)+rx*v[0], float64(cy)-ry*v[1]
		tip[i] = [2]int{int(math.Round(ex)), int(math.Round(ey))}
		steps := int(math.Max(math.Abs(ex-float64(cx)), math.Abs(ey-float64(cy))))
		for j := 1; j < steps; j++ {
			t := float64(j) / float64(steps)
			x := int(math.Round(float64(cx) + t*(ex-float64(cx))))
			y := int(math.Round(float64(cy) + t*(ey-float64(cy))))
			gizmoSet(g, x, y, gizmoArm(ex-float64(cx), ey-float64(cy)))
		}
	}
	// An axis pointing at the camera collapses onto the origin — its label
	// still gets written there, so no axis ever silently disappears.
	for i, a := range gizmoAxes {
		v := rot(a.dir, ang)
		gizmoSet(g, tip[i][0], tip[i][1], gizmoLabel(a.label, v[2]))
	}
	return g
}

// gizmoArm picks a line char by slope, so an arm reads as a direction rather
// than a dotted stagger.
func gizmoArm(dx, dy float64) rune {
	switch {
	case math.Abs(dy) < 0.4*math.Abs(dx):
		return '-'
	case math.Abs(dx) < 0.4*math.Abs(dy):
		return '|'
	case dx*dy < 0:
		return '/'
	default:
		return '\\'
	}
}

// gizmoLabel upper-cases an axis pointing towards the camera, so you can tell
// +x from -x when the arm is edge-on.
func gizmoLabel(label rune, z float64) rune {
	if z < 0 { // camera looks along +z, so negative z is nearer
		return label - ('a' - 'A')
	}
	return label
}

func gizmoSet(g [][]rune, x, y int, ch rune) {
	if y < 0 || y >= len(g) || x < 0 || x >= len(g[y]) {
		return
	}
	g[y][x] = ch
}

// overlayGizmo blits the triad into the bottom-left of a rendered frame,
// padding short lines so the box always sits in the same place.
func overlayGizmo(lines []string, ang [3]float64, w int) []string {
	if len(lines) < gizmoH+gizmoPad || w < gizmoW+2*gizmoPad {
		return lines // pane too small: the model needs the room more
	}
	g := gizmo(ang)
	top := len(lines) - gizmoH - gizmoPad
	for i, row := range g {
		y := top + i
		line := []rune(lines[y])
		for len(line) < gizmoPad+gizmoW {
			line = append(line, ' ')
		}
		// Punch a hole for the whole box rather than letting the model show
		// through the blanks: over a densely shaded part the triad is
		// otherwise lost in the fill, which defeats the point of it.
		for x, ch := range row {
			line[gizmoPad+x] = ch
		}
		lines[y] = strings.TrimRight(string(line), " ")
	}
	return lines
}
