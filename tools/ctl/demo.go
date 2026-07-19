package main

import (
	"math"
	"math/rand"
	"path/filepath"
	"sort"
)

// demoModel is the demo screen's state: one tumble shared across scenes, so
// tabbing from the cube to a part keeps the motion continuous instead of
// snapping back to rest.
type demoModel struct {
	ang, vel, target [3]float64
	zoom             float64
	ticks            int
	paused           bool
	rng              *rand.Rand
	scenes           []demoScene
	idx              int
}

// demoScene is one thing to look at. path == "" is the parametric cube;
// anything else is an STL, loaded on first view so opening the demo does not
// pay for every export on disk.
type demoScene struct {
	label  string
	path   string
	wire   bool
	mesh   *mesh
	err    error
	loaded bool
}

const (
	cubeFPS      = 20
	cubeRerollAt = 5 * cubeFPS // ticks between spin-target re-rolls
	cubeEase     = 0.02        // how fast the spin drifts to its target
	cubeSpinMax  = 0.06        // rad per tick
)

// newDemoModel builds the scene list: the cube first, then every export,
// with unit.stl promoted to the front since it is the whole assembly.
func newDemoModel(seed int64, root string) *demoModel {
	d := &demoModel{rng: rand.New(rand.NewSource(seed)), zoom: 1}
	// Wireframe suits the cube — twelve edges read as a shape. A mesh has
	// thousands, which reads as noise, so parts open shaded.
	d.scenes = append(d.scenes, demoScene{label: "cube", wire: true})

	paths := findSTLs(root)
	sort.Slice(paths, func(i, j int) bool {
		bi, bj := filepath.Base(paths[i]), filepath.Base(paths[j])
		if (bi == "unit.stl") != (bj == "unit.stl") {
			return bi == "unit.stl"
		}
		return bi < bj
	})
	for _, p := range paths {
		d.scenes = append(d.scenes, demoScene{label: stlName(p), path: p})
	}

	d.reroll()
	d.vel = d.target
	return d
}

func (d *demoModel) reroll() {
	for i := range d.target {
		d.target[i] = (d.rng.Float64()*2 - 1) * cubeSpinMax
	}
}

// step advances one frame. A paused demo holds its pose but stays live, so
// wireframe and scene changes still redraw.
func (d *demoModel) step() {
	if d.paused {
		return
	}
	d.ticks++
	if d.ticks%cubeRerollAt == 0 {
		d.reroll()
	}
	for i := range d.ang {
		d.vel[i] += (d.target[i] - d.vel[i]) * cubeEase
		d.ang[i] = math.Mod(d.ang[i]+d.vel[i], 2*math.Pi)
	}
}

// Manual view control. Taking hold of the model stops the tumble — otherwise
// the drift fights every nudge — so every orbit/roll key pauses first.

const (
	demoStep    = 0.12 // radians per orbit keypress
	demoZoomIn  = 1.12 // zoom multiplier per keypress
	demoZoomMin = 0.25
	demoZoomMax = 8.0
)

// orbit turns the model: dPitch about screen-x, dYaw about screen-y,
// dRoll about the line of sight.
func (d *demoModel) orbit(dPitch, dYaw, dRoll float64) {
	d.paused = true
	d.ang[0] += dPitch
	d.ang[1] += dYaw
	d.ang[2] += dRoll
	for i := range d.ang {
		d.ang[i] = math.Mod(d.ang[i], 2*math.Pi)
	}
}

// zoomBy scales the view, clamped so the model can neither vanish nor blow up
// into a wall of one character.
func (d *demoModel) zoomBy(f float64) {
	d.zoom = math.Min(math.Max(d.zoom*f, demoZoomMin), demoZoomMax)
}

// snap points the camera down an axis: 'x' looks along +x, 'y' down from
// above, 'z' straight on. Upper case looks from the opposite side.
func (d *demoModel) snap(axis rune) {
	back := axis >= 'X' && axis <= 'Z'
	half := math.Pi / 2
	if back {
		half = -half
		axis += 'x' - 'X'
	}
	d.paused = true
	d.vel = [3]float64{}
	switch axis {
	case 'x':
		d.ang = [3]float64{0, half, 0}
	case 'y':
		d.ang = [3]float64{half, 0, 0}
	case 'z':
		d.ang = [3]float64{0, 0, 0}
		if back {
			d.ang = [3]float64{0, math.Pi, 0}
		}
	}
}

// reset returns to the opening view and lets the tumble go again.
func (d *demoModel) reset() {
	d.ang = [3]float64{}
	d.zoom = 1
	d.paused = false
}

// fit zooms so the model's silhouette at this orientation just fills the
// pane. viewFill is the worst-case fit — big enough for any orientation —
// which leaves most orientations looking small, so measure this one.
func (d *demoModel) fit(w, h int) {
	pts := d.points()
	if len(pts) == 0 || w < 2 || h < 2 {
		return
	}
	c := newCanvas(w, h, d.radius(), viewFill)
	cx, cy := float64(w/2), float64(h/2)
	worst := 0.0
	for _, p := range pts {
		x, y, z := c.project(rot(p, d.ang))
		if z <= 0.1 {
			continue
		}
		worst = math.Max(worst, math.Abs(x-cx)/(cx-1))
		worst = math.Max(worst, math.Abs(y-cy)/(cy-1))
	}
	if worst > 0 {
		d.zoom = math.Min(math.Max(d.zoom/worst, demoZoomMin), demoZoomMax)
	}
}

// points returns the current scene's vertices in model space (the cube's
// eight corners, or every mesh vertex) for fit to measure. An unloaded or
// broken scene has none.
func (d *demoModel) points() [][3]float64 {
	s := d.scene()
	if s.path == "" {
		pts := make([][3]float64, 8)
		for i := range pts {
			pts[i] = cubeCorner(i)
		}
		return pts
	}
	if s.mesh == nil {
		return nil
	}
	pts := make([][3]float64, 0, len(s.mesh.tris)*3)
	s.mesh.each(func(p [3]float64) { pts = append(pts, p) })
	return pts
}

// radius is the bounding sphere the canvas is sized against: the cube's
// corner distance, or 1 for a mesh (normalise put it there).
func (d *demoModel) radius() float64 {
	if d.scene().path == "" {
		return cubeHalf * math.Sqrt(3)
	}
	return 1
}

func (d *demoModel) next() { d.idx = (d.idx + 1) % len(d.scenes) }

func (d *demoModel) prev() { d.idx = (d.idx - 1 + len(d.scenes)) % len(d.scenes) }

// jumpTo selects a scene by label, reporting whether it existed.
func (d *demoModel) jumpTo(label string) bool {
	for i, s := range d.scenes {
		if s.label == label {
			d.idx = i
			return true
		}
	}
	return false
}

func (d *demoModel) scene() *demoScene { return &d.scenes[d.idx] }

// render draws the current scene, loading its mesh if this is its first view.
func (d *demoModel) render(w, h int) []string {
	s := d.scene()
	if s.path == "" {
		return renderCube(w, h, d.ang, d.zoom, s.wire)
	}
	if !s.loaded {
		s.mesh, s.err = loadSTL(s.path)
		s.loaded = true
	}
	if s.err != nil {
		return centred(w, h, "cannot read "+filepath.Base(s.path), s.err.Error())
	}
	return renderMesh(s.mesh, w, h, d.ang, d.zoom, s.wire)
}

// centred lays out message lines in the middle of an otherwise blank grid,
// so a load failure keeps the screen's shape instead of collapsing it.
func centred(w, h int, msgs ...string) []string {
	out := make([]string, h)
	top := (h - len(msgs)) / 2
	for y := range out {
		out[y] = ""
		if y >= top && y-top < len(msgs) {
			m := msgs[y-top]
			if len(m) > w {
				m = m[:w]
			}
			pad := (w - len(m)) / 2
			out[y] = string(make([]byte, 0, w))
			for i := 0; i < pad; i++ {
				out[y] += " "
			}
			out[y] += m
		}
	}
	return out
}
