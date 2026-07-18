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
	d := &demoModel{rng: rand.New(rand.NewSource(seed))}
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
		return renderCube(w, h, d.ang, s.wire)
	}
	if !s.loaded {
		s.mesh, s.err = loadSTL(s.path)
		s.loaded = true
	}
	if s.err != nil {
		return centred(w, h, "cannot read "+filepath.Base(s.path), s.err.Error())
	}
	return renderMesh(s.mesh, w, h, d.ang, s.wire)
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
