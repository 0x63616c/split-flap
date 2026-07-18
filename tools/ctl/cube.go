package main

import (
	"math"
	"math/rand"
)

// The demo screen: a shaded ASCII cube tumbling under its own drifting spin.
// Rendering is a pure function of (size, angles, wireframe) so it can be
// tested without a terminal; the model below only owns the animation state.

const (
	cubeDist    = 5.0           // camera distance from the cube's centre
	cubeHalf    = 1.0           // half edge length
	cubeCellW   = 2.0           // terminal cells are ~twice as tall as wide
	cubeRamp    = ".,-~:;=!*$@" // dark → bright
	cubeWire    = '#'           // edge char, kept out of the ramp
	cubeLight   = 0.9           // light comes from over the viewer's shoulder
	cubeAmbient = 0.12          // shade floor, so a face is never blank
)

// faces holds, per cube face, the origin corner and the two in-plane edge
// vectors; sweeping u,v over [0,1] covers the face, and their cross product
// (precomputed as the outward normal) gives the shading.
var cubeFaces = [6]struct{ o, a, b, n [3]float64 }{
	{o: [3]float64{-1, -1, 1}, a: [3]float64{2, 0, 0}, b: [3]float64{0, 2, 0}, n: [3]float64{0, 0, 1}},
	{o: [3]float64{-1, -1, -1}, a: [3]float64{0, 2, 0}, b: [3]float64{2, 0, 0}, n: [3]float64{0, 0, -1}},
	{o: [3]float64{1, -1, -1}, a: [3]float64{0, 2, 0}, b: [3]float64{0, 0, 2}, n: [3]float64{1, 0, 0}},
	{o: [3]float64{-1, -1, -1}, a: [3]float64{0, 0, 2}, b: [3]float64{0, 2, 0}, n: [3]float64{-1, 0, 0}},
	{o: [3]float64{-1, 1, -1}, a: [3]float64{2, 0, 0}, b: [3]float64{0, 0, 2}, n: [3]float64{0, 1, 0}},
	{o: [3]float64{-1, -1, -1}, a: [3]float64{0, 0, 2}, b: [3]float64{2, 0, 0}, n: [3]float64{0, -1, 0}},
}

// cubeEdges lists the 12 edges as corner-index pairs into the 8 corners
// enumerated by bit (x, y, z) = (bit0, bit1, bit2).
var cubeEdges = [12][2]int{
	{0, 1}, {2, 3}, {4, 5}, {6, 7}, // along x
	{0, 2}, {1, 3}, {4, 6}, {5, 7}, // along y
	{0, 4}, {1, 5}, {2, 6}, {3, 7}, // along z
}

func cubeCorner(i int) [3]float64 {
	sign := func(bit int) float64 {
		if i&(1<<bit) != 0 {
			return cubeHalf
		}
		return -cubeHalf
	}
	return [3]float64{sign(0), sign(1), sign(2)}
}

// rot applies an X→Y→Z Euler rotation.
func rot(p [3]float64, ang [3]float64) [3]float64 {
	sx, cx := math.Sincos(ang[0])
	sy, cy := math.Sincos(ang[1])
	sz, cz := math.Sincos(ang[2])
	x, y, z := p[0], p[1], p[2]
	y, z = y*cx-z*sx, y*sx+z*cx
	x, z = x*cy+z*sy, -x*sy+z*cy
	x, y = x*cz-y*sz, x*sz+y*cz
	return [3]float64{x, y, z}
}

// cubeCanvas is a char grid with a 1/z depth buffer, so nearer samples win.
type cubeCanvas struct {
	w, h  int
	cells []rune
	depth []float64
	scale float64
}

func newCubeCanvas(w, h int) *cubeCanvas {
	c := &cubeCanvas{w: w, h: h, cells: make([]rune, w*h), depth: make([]float64, w*h)}
	for i := range c.cells {
		c.cells[i] = ' '
	}
	// Scale so no corner can leave the grid at any orientation. A corner sits
	// at radius r from the centre, so its largest possible projected offset
	// over all rotations is r/sqrt(dist²-r²) — the tangent point of the line
	// of sight on the sphere it sweeps.
	r := cubeHalf * math.Sqrt(3)
	ratio := r / math.Sqrt(cubeDist*cubeDist-r*r)
	c.scale = math.Min(float64(h)/2/ratio, float64(w)/2/ratio/cubeCellW) * 0.95
	return c
}

// plot projects a rotated point and writes ch if it is the nearest sample
// yet for that cell. bias nudges a sample towards the camera so wireframe
// edges beat the faces they sit on.
func (c *cubeCanvas) plot(p [3]float64, ch rune, bias float64) {
	z := p[2] + cubeDist
	if z <= 0.1 {
		return
	}
	ooz := 1/z + bias
	sx := c.w/2 + int(math.Round(c.scale*cubeCellW*p[0]/z))
	sy := c.h/2 - int(math.Round(c.scale*p[1]/z))
	if sx < 0 || sx >= c.w || sy < 0 || sy >= c.h {
		return
	}
	i := sy*c.w + sx
	if ooz > c.depth[i] {
		c.depth[i], c.cells[i] = ooz, ch
	}
}

func (c *cubeCanvas) lines() []string {
	out := make([]string, c.h)
	for y := 0; y < c.h; y++ {
		out[y] = string(c.cells[y*c.w : (y+1)*c.w])
	}
	return out
}

// renderCube draws the cube at the given orientation into a w×h char grid.
func renderCube(w, h int, ang [3]float64, wire bool) []string {
	c := renderCubeCanvas(w, h, ang, wire)
	if c == nil {
		return nil
	}
	return c.lines()
}

// renderCubeCanvas is renderCube's guts, kept separate so tests can inspect
// the depth buffer and not just the chars.
func renderCubeCanvas(w, h int, ang [3]float64, wire bool) *cubeCanvas {
	if w < 1 || h < 1 {
		return nil
	}
	c := newCubeCanvas(w, h)
	light := [3]float64{0, cubeLight, -1} // towards the viewer, slightly above
	steps := 2 * max(w, h)

	if wire {
		// See-through skeleton: no faces, so every edge shows including the
		// ones round the back. Nothing to occlude, hence no depth bias.
		for _, e := range cubeEdges {
			p0, p1 := rot(cubeCorner(e[0]), ang), rot(cubeCorner(e[1]), ang)
			for i := 0; i <= steps; i++ {
				t := float64(i) / float64(steps)
				c.plot([3]float64{
					p0[0] + t*(p1[0]-p0[0]),
					p0[1] + t*(p1[1]-p0[1]),
					p0[2] + t*(p1[2]-p0[2]),
				}, cubeWire, 0)
			}
		}
		return c
	}

	// Faces: sample densely enough that no cell is missed at this size.
	for _, f := range cubeFaces {
		n := rot(f.n, ang)
		if n[2] >= 0 {
			continue // back face: the camera sits at -z looking towards +z
		}
		lum := (n[0]*light[0] + n[1]*light[1] + n[2]*light[2]) /
			math.Sqrt(light[0]*light[0]+light[1]*light[1]+light[2]*light[2])
		lum = math.Max(lum, cubeAmbient) // a grazing face stays dim, never a hole
		ch := rune(cubeRamp[min(int(lum*float64(len(cubeRamp))), len(cubeRamp)-1)])
		for i := 0; i <= steps; i++ {
			u := float64(i) / float64(steps)
			for j := 0; j <= steps; j++ {
				v := float64(j) / float64(steps)
				p := [3]float64{
					cubeHalf * (f.o[0] + u*f.a[0] + v*f.b[0]),
					cubeHalf * (f.o[1] + u*f.a[1] + v*f.b[1]),
					cubeHalf * (f.o[2] + u*f.a[2] + v*f.b[2]),
				}
				c.plot(rot(p, ang), ch, 0)
			}
		}
	}

	return c
}

// cubeModel is the demo screen's animation state: an angle per axis plus a
// spin rate that drifts towards a fresh random target every few seconds, so
// the tumble never settles into a visible loop.
type cubeModel struct {
	ang, vel, target [3]float64
	ticks            int
	wire             bool
	rng              *rand.Rand
}

const (
	cubeFPS      = 20
	cubeRerollAt = 5 * cubeFPS // ticks between spin-target re-rolls
	cubeEase     = 0.02        // how fast the spin drifts to its target
	cubeSpinMax  = 0.06        // rad per tick
)

func newCubeModel(seed int64) *cubeModel {
	c := &cubeModel{wire: true, rng: rand.New(rand.NewSource(seed))}
	c.reroll()
	c.vel = c.target
	return c
}

func (c *cubeModel) reroll() {
	for i := range c.target {
		c.target[i] = (c.rng.Float64()*2 - 1) * cubeSpinMax
	}
}

// step advances one frame.
func (c *cubeModel) step() {
	c.ticks++
	if c.ticks%cubeRerollAt == 0 {
		c.reroll()
	}
	for i := range c.ang {
		c.vel[i] += (c.target[i] - c.vel[i]) * cubeEase
		c.ang[i] = math.Mod(c.ang[i]+c.vel[i], 2*math.Pi)
	}
}
